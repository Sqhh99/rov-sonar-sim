#!/usr/bin/env python3
"""Render POSIM's range-major dB samples as a calibrated sonar fan image."""
import math
import time

import cv2
import numpy as np
from marine_acoustic_msgs.msg import ProjectedSonarImage
from PIL import Image as PilImage, ImageDraw, ImageFont
import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

# Amber/Gold colour map: black -> brown -> amber -> gold -> pale yellow.
AMBER_STOPS = (
    (0.00, (0, 0, 0)),
    (0.20, (38, 16, 0)),
    (0.45, (150, 70, 0)),
    (0.70, (236, 150, 22)),
    (0.88, (255, 205, 84)),
    (1.00, (255, 246, 206)),
)
PAGE = (32, 32, 32)  # Dark gray page; the empty fan itself is black.
INK = (236, 236, 236)
INK_SECONDARY = (176, 176, 176)
OUTLINE = (120, 120, 120)
GRID_ALPHA = 0.28  # White range arcs and sector lines over the fan.


def palette_lut(palette):
    v = np.linspace(0, 1, 256)
    if palette == "gray":
        return np.repeat(np.round(v * 255).astype(np.uint8)[:, None], 3, axis=1)
    stops = np.array([s for s, _ in AMBER_STOPS])
    colours = np.array([c for _, c in AMBER_STOPS], float)
    return np.stack([np.interp(v, stops, colours[:, i]) for i in range(3)], axis=1).round().astype(np.uint8)


def font(size, bold=False):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


def ring_step(maximum):
    """A round range-ring spacing giving four to six rings."""
    exponent = 10 ** math.floor(math.log10(maximum / 5))
    for factor in (1, 2, 2.5, 5, 10):
        if maximum / (factor * exponent) <= 6:
            return factor * exponent
    return 10 * exponent


def metres(value):
    return f"{value:g} m"


class FanRenderer:
    def __init__(self, width=640, height=400):
        self.width, self.height = width, height
        self.key = None
        self.reference = None
        self.last_time = None
        self.text_key = None
        self.luts = {name: palette_lut(name) for name in ("amber", "gray")}
        self.title_font, self.text_font, self.label_font = font(14, True), font(12), font(11)

    def render(self, db, ranges, bearings, gain=0.0, dynamic_range=35.0, palette="amber", frequency=0.0):
        ranges, bearings = np.asarray(ranges), np.asarray(bearings)
        if (db.shape != (len(ranges), len(bearings)) or len(ranges) < 2 or
                len(bearings) < 2 or not np.all(np.isfinite(ranges)) or
                not np.all(np.isfinite(bearings)) or np.any(np.diff(ranges) <= 0) or
                np.any(np.diff(bearings) <= 0) or ranges[-1] <= 0 or
                np.max(np.abs(bearings)) >= np.pi / 2):
            raise ValueError("Invalid sonar range/bearing geometry")
        if not np.isfinite(gain) or not 20 <= dynamic_range <= 100 or palette not in self.luts:
            raise ValueError("Invalid display settings")
        key = (ranges.tobytes(), bearings.tobytes())
        if self.key != key:
            self.key, self.reference, self.last_time = key, None, None
            self.layout(ranges, bearings)
        finite = np.isfinite(db)
        now = time.monotonic()
        if np.any(finite):
            peak = float(np.max(db[finite]))
            alpha = 1.0 if self.last_time is None else 1 - np.exp(-(now - self.last_time) / 0.8)
            self.reference = peak if self.reference is None else self.reference + alpha * (peak - self.reference)
        self.last_time = now
        values = np.zeros(db.shape, np.float32)
        if self.reference is not None:
            values[finite] = np.clip((db[finite] - self.reference + gain + dynamic_range) / dynamic_range, 0, 1)
        # Interpolate only the display raster; acoustic samples remain unchanged.
        fan = cv2.remap(values, self.map_x, self.map_y, cv2.INTER_LINEAR)
        pixels = np.empty((self.height, self.width, 3), np.float32)
        pixels[:] = PAGE
        pixels[self.mask] = self.luts[palette][np.clip(fan[self.mask] * 255, 0, 255).astype(np.uint8)]
        pixels += self.grid[..., None] * (255 - pixels)  # White grid lines over the fan.
        pixels = pixels * (1 - self.ink_alpha) + self.ink
        text_alpha, text = self.readout(len(bearings), gain, dynamic_range, frequency, np.any(finite))
        pixels = pixels * (1 - text_alpha) + text
        return np.clip(pixels, 0, 255).astype(np.uint8)

    def layout(self, ranges, bearings):
        """Fan geometry, colour remap tables and the static annotation layers."""
        self.maximum = float(ranges[-1])
        self.angle_min, self.angle_max = float(bearings[0]), float(bearings[-1])
        half = max(abs(self.angle_min), abs(self.angle_max))
        side, top, bottom = 58, 70, 22
        self.scale = min((self.width - 2 * side) / (2 * self.maximum * np.sin(half)),
                         (self.height - top - bottom) / self.maximum)
        self.origin = (self.width // 2, self.height - bottom)
        yy, xx = np.indices((self.height, self.width), dtype=np.float32)
        lateral = (xx - self.origin[0]) / self.scale
        forward = (self.origin[1] - yy) / self.scale
        distance = np.hypot(lateral, forward)
        # POSIM publishes positive bearing toward vehicle-left.
        bearing = np.arctan2(-lateral, forward)
        self.mask = ((forward >= 0) & (distance >= ranges[0]) & (distance <= ranges[-1]) &
                     (bearing >= self.angle_min) & (bearing <= self.angle_max))
        self.map_x = np.interp(bearing, bearings, np.arange(len(bearings))).astype(np.float32)
        self.map_y = np.interp(distance, ranges, np.arange(len(ranges))).astype(np.float32)

        step = ring_step(self.maximum)
        self.rings = [r for r in np.arange(step, self.maximum + step * 1e-6, step)]
        if self.maximum - self.rings[-1] > step * 0.25:
            self.rings.append(self.maximum)
        # Sector lines every 30 degrees, clear of the fan edges.
        self.sectors = [np.deg2rad(d) for d in range(-90, 91, 30)
                        if self.angle_min + 0.12 < np.deg2rad(d) < self.angle_max - 0.12]

        grid = np.zeros((self.height, self.width), np.uint8)
        for radius in (r for r in self.rings if r < self.maximum - 1e-6):
            cv2.polylines(grid, [self.arc(radius)], False, 255, 1, cv2.LINE_AA)
        for angle in self.sectors:
            cv2.line(grid, self.origin, self.point(self.maximum, angle), 255, 1, cv2.LINE_AA)
        self.grid = np.where(self.mask, grid.astype(np.float32) / 255 * GRID_ALPHA, 0)

        # Premultiplied RGBA: fan outline and range labels.
        layer = np.zeros((self.height, self.width, 4), np.uint8)
        outline = np.vstack([[self.origin], self.arc(self.maximum)[::-1]])
        cv2.polylines(layer, [outline], True, (*OUTLINE, 255), 1, cv2.LINE_AA)
        image = PilImage.fromarray(layer, "RGBA")
        draw = ImageDraw.Draw(image)
        edge = np.subtract(self.point(self.maximum, self.angle_min), self.origin).astype(float)
        normal = np.array([-edge[1], edge[0]]) / np.hypot(*edge)
        if normal[0] < 0:
            normal = -normal
        for radius in self.rings:
            x, y = np.add(self.point(radius, self.angle_min), normal * 7)
            draw.text((x, y), metres(round(radius, 2)), font=self.label_font,
                      fill=(*INK_SECONDARY, 255), anchor="lm")
        self.ink, self.ink_alpha = self.split(image)
        self.text_key = None

    def readout(self, beams, gain, dynamic_range, frequency, returns):
        """Plain sonar data text in the top-left corner (cached)."""
        key = (beams, gain, dynamic_range, frequency, returns)
        if key != self.text_key:
            fov = np.rad2deg(self.angle_max - self.angle_min)
            lines = [(f"Range {self.maximum:.1f} m  ·  {beams} beams  ·  {fov:.0f}° FOV"
                      + (f"  ·  {frequency / 1e3:.0f} kHz" if frequency > 0 else ""), INK_SECONDARY),
                     (f"Gain {gain:+.0f} dB  ·  Dynamic range {dynamic_range:.0f} dB", INK_SECONDARY)]
            if not returns:
                lines.append(("No returns", (130, 130, 130)))
            image = PilImage.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.text((14, 11), "Forward-looking sonar", font=self.title_font, fill=(*INK, 255))
            for i, (line, colour) in enumerate(lines):
                draw.text((14, 32 + 17 * i), line, font=self.text_font, fill=(*colour, 255))
            self.text_key = key
            self.text, self.text_alpha = self.split(image)
        return self.text_alpha, self.text

    @staticmethod
    def split(image):
        """Premultiplied colour and alpha planes of an RGBA image."""
        rgba = np.asarray(image, np.float32)
        alpha = rgba[..., 3:] / 255
        return rgba[..., :3] * alpha, alpha

    def arc(self, radius):
        return np.array([self.point(radius, a) for a in np.linspace(self.angle_min, self.angle_max, 200)])

    def point(self, radius, bearing):
        return (round(self.origin[0] - radius*self.scale*np.sin(bearing)),
                round(self.origin[1] - radius*self.scale*np.cos(bearing)))


class SonarView(Node):
    def __init__(self):
        super().__init__("sonar_view")
        for name, value in [("gain_db", 0.0), ("dynamic_range_db", 35.0), ("palette", "amber")]:
            self.declare_parameter(name, value)
        self.add_on_set_parameters_callback(self.validate)
        self.renderer = FanRenderer()
        self.publisher = self.create_publisher(Image, "sonar_rgb", 1)
        self.subscription = self.create_subscription(
            ProjectedSonarImage, "sonar_raw", self.convert, qos_profile_sensor_data)

    def validate(self, parameters):
        for p in parameters:
            if ((p.name == "gain_db" and not -30 <= p.value <= 30) or
                    (p.name == "dynamic_range_db" and not 20 <= p.value <= 100) or
                    (p.name == "palette" and p.value not in ("amber", "gray"))):
                return SetParametersResult(
                    successful=False, reason="Gain: -30..30 dB; dynamic range: 20..100 dB; palette: amber/gray")
        return SetParametersResult(successful=True)

    def convert(self, message):
        try:
            # POSIM's publisher packs range rows with beam index varying fastest.
            if message.image.dtype != message.image.DTYPE_FLOAT32:
                raise ValueError("Expected POSIM float32 dB samples")
            dtype = ">f4" if message.image.is_bigendian else "<f4"
            db = np.frombuffer(message.image.data, dtype=dtype).reshape(
                len(message.ranges), message.image.beam_count)
            bearings = np.arctan2([b.y for b in message.beam_directions], [b.x for b in message.beam_directions])
            pixels = self.renderer.render(
                db, message.ranges, bearings,
                self.get_parameter("gain_db").value, self.get_parameter("dynamic_range_db").value,
                self.get_parameter("palette").value, float(message.ping_info.frequency))
        except (ValueError, TypeError) as error:
            self.get_logger().error(str(error), throttle_duration_sec=5)
            return
        output = Image()
        output.header = message.header
        output.height, output.width = pixels.shape[:2]
        output.encoding, output.step = "rgb8", pixels.shape[1]*3
        output.data = pixels.tobytes()
        self.publisher.publish(output)


def main():
    rclpy.init()
    node = SonarView()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()

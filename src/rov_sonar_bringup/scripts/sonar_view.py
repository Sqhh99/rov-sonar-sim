#!/usr/bin/env python3
"""Render POSIM's range-major dB samples as a calibrated sonar preview."""
import time

import cv2
import numpy as np
import rclpy
from marine_acoustic_msgs.msg import ProjectedSonarImage
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class FanRenderer:
    def __init__(self, width=640, height=440):
        self.width, self.height = width, height
        self.key = None
        self.reference = None
        self.last_time = None

    def render(self, db, ranges, bearings, gain=0.0, dynamic_range=35.0, palette="amber"):
        ranges, bearings = np.asarray(ranges), np.asarray(bearings)
        if (db.shape != (len(ranges), len(bearings)) or len(ranges) < 2 or
                len(bearings) < 2 or not np.all(np.isfinite(ranges)) or
                not np.all(np.isfinite(bearings)) or np.any(np.diff(ranges) <= 0) or
                np.any(np.diff(bearings) <= 0) or ranges[-1] <= 0 or
                np.max(np.abs(bearings)) >= np.pi / 2):
            raise ValueError("Invalid sonar range/bearing geometry")
        if not np.isfinite(gain) or not 20 <= dynamic_range <= 100 or palette not in ("amber", "gray"):
            raise ValueError("Invalid display settings")
        key = (ranges.tobytes(), bearings.tobytes())
        if self.key != key:
            self.key, self.reference, self.last_time = key, None, None
            self.origin = (self.width // 2, self.height - 40)
            self.maximum = float(ranges[-1])
            angle = float(np.max(np.abs(bearings)))
            self.scale = min((self.width - 80) / (2 * self.maximum * np.sin(angle)),
                             (self.height - 100) / self.maximum)
            yy, xx = np.indices((self.height, self.width), dtype=np.float32)
            lateral = (xx - self.origin[0]) / self.scale
            forward = (self.origin[1] - yy) / self.scale
            distance = np.hypot(lateral, forward)
            # POSIM publishes positive bearing toward vehicle-left.
            bearing = np.arctan2(-lateral, forward)
            self.mask = ((forward >= 0) & (distance >= ranges[0]) &
                         (distance <= ranges[-1]) & (bearing >= bearings[0]) &
                         (bearing <= bearings[-1]))
            self.map_x = np.interp(bearing, bearings, np.arange(len(bearings))).astype(np.float32)
            self.map_y = np.interp(distance, ranges, np.arange(len(ranges))).astype(np.float32)
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
        v = np.arange(256, dtype=np.float32) / 255
        if palette == "gray":
            lut = np.repeat((v * 255).astype(np.uint8)[:, None], 3, axis=1)
        else:
            lut = (255 * np.clip(np.stack((1.9*v, 1.25*v, (v-.65)/.35), axis=1), 0, 1)).astype(np.uint8)
        pixels = lut[np.clip(fan * 255, 0, 255).astype(np.uint8)]
        pixels[~self.mask] = (12, 17, 23)
        grid = pixels.copy()
        color = (65, 83, 94)
        font = cv2.FONT_HERSHEY_SIMPLEX
        angle_min, angle_max = float(bearings[0]), float(bearings[-1])
        for radius in np.linspace(self.maximum/5, self.maximum, 5):
            pts = np.array([self.point(radius, a) for a in np.linspace(angle_min, angle_max, 160)])
            cv2.polylines(grid, [pts], False, color, 1, cv2.LINE_AA)
        for degrees in (-60, -30, 0, 30, 60):
            angle = np.deg2rad(degrees)
            if angle_min <= angle <= angle_max:
                cv2.line(grid, self.origin, self.point(self.maximum, angle), color, 1, cv2.LINE_AA)
        pixels = cv2.addWeighted(pixels, .65, grid, .35, 0)
        ink = (170, 193, 201)
        for radius in np.linspace(self.maximum/5, self.maximum, 5):
            x, y = self.point(radius, angle_max)
            cv2.putText(pixels, f"{radius:.0f}m", (max(2, x-28), y+4), font, .34, ink, 1, cv2.LINE_AA)
        for degrees in (-60, -30, 0, 30, 60):
            angle = np.deg2rad(degrees)
            if angle_min <= angle <= angle_max:
                x, y = self.point(self.maximum, angle)
                label = "0" if degrees == 0 else f"{'L' if degrees > 0 else 'R'}{abs(degrees)}"
                cv2.putText(pixels, label, (x-10, max(55, y-8)), font, .35, ink, 1, cv2.LINE_AA)
        cv2.putText(pixels, "FORWARD SONAR", (16, 23), font, .55, (218, 230, 232), 1, cv2.LINE_AA)
        cv2.putText(pixels, f"{self.maximum:.1f} m  |  {len(bearings)} beams", (16, 43), font, .38, ink, 1, cv2.LINE_AA)
        cv2.putText(pixels, f"Gain {gain:+.0f} dB   |   DR {dynamic_range:.0f} dB   |   Auto reference",
                    (16, self.height-12), font, .39, ink, 1, cv2.LINE_AA)
        if not np.any(finite):
            cv2.putText(pixels, "NO RETURNS", (self.width//2-60, self.height//2), font, .5, ink, 1, cv2.LINE_AA)
        return pixels

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
        self.subscription = self.create_subscription(ProjectedSonarImage, "sonar_raw", self.convert, qos_profile_sensor_data)

    def validate(self, parameters):
        for p in parameters:
            if ((p.name == "gain_db" and not -30 <= p.value <= 30) or
                    (p.name == "dynamic_range_db" and not 20 <= p.value <= 100) or
                    (p.name == "palette" and p.value not in ("amber", "gray"))):
                return SetParametersResult(successful=False, reason="Gain: -30..30 dB; dynamic range: 20..100 dB; palette: amber/gray")
        return SetParametersResult(successful=True)

    def convert(self, message):
        try:
            # POSIM's publisher packs range rows with beam index varying fastest.
            if message.image.dtype != message.image.DTYPE_FLOAT32:
                raise ValueError("Expected POSIM float32 dB samples")
            dtype = ">f4" if message.image.is_bigendian else "<f4"
            db = np.frombuffer(message.image.data, dtype=dtype).reshape(len(message.ranges), message.image.beam_count)
            bearings = np.arctan2([b.y for b in message.beam_directions], [b.x for b in message.beam_directions])
            pixels = self.renderer.render(db, message.ranges, bearings,
                self.get_parameter("gain_db").value, self.get_parameter("dynamic_range_db").value,
                self.get_parameter("palette").value)
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

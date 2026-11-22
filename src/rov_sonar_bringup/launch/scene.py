"""Build the simulation world: the shallow inspection site plus the sonar ROV.

The robot model is embedded in the generated world, so the simulation needs no
spawn service. Only this generated copy is changed; the installed model and
world files stay as shipped.
"""

import copy
from pathlib import Path
import xml.etree.ElementTree as ET

GZ_NS = "http://gazebosim.org"
ET.register_namespace("gz", GZ_NS)

ROBOT = "bluerov2_heavy_multibeam_sonar"
WORLD = "shallow_underwater"
CAMERA_TOPIC = "/rov/camera/image"
SONAR_FAN_TOPIC = "/rov/sonar/fan_image"


def sonar_topic(name):
    """ROS topics published directly by the multibeam sonar plugin."""
    return f"/model/{ROBOT}/multibeam_sonar/{name}"


# (horizontal beams, vertical rays, bandwidth Hz). "full" is the sensor's
# shipped configuration and is expensive on the CPU backend.
SONAR_PROFILES = {
    "preview": (128, 64, 15000),
    "balanced": (192, 96, 29900),
    "full": (512, 300, 29900),
}


def model_file(description_share):
    return Path(description_share) / "models" / ROBOT / "model.sdf"


def world_file(description_share):
    return Path(description_share) / "worlds" / f"{WORLD}.world"


def robot_model(
    description_share,
    sonar_quality="balanced",
    sonar_rate=5.0,
    camera_stream=False,
    camera_stream_port=5600,
):
    """Return the configured <model> element."""
    if sonar_quality not in SONAR_PROFILES:
        raise ValueError(f"Unknown sonar_quality {sonar_quality!r}")
    if not float(sonar_rate) > 0:
        raise ValueError("sonar_rate must be positive")
    model = ET.parse(model_file(description_share)).getroot().find("model")

    # Neutral trim: the collision box displaces exactly the vehicle's total mass,
    # so an unarmed vehicle hovers beside the inspection targets.
    base = model.find("link[@name='base_link']")
    volume = 1.0
    for length in base.findtext("collision/geometry/box/size").split():
        volume *= float(length)
    other_mass = sum(
        float(link.findtext("inertial/mass", "0"))
        for link in model.findall("link")
        if link is not base
    )
    base.find("inertial/mass").text = repr(1025.0 * volume - other_mass)

    camera = model.find(".//sensor[@type='camera']")
    camera.find("always_on").text = "true"
    camera.find("topic").text = CAMERA_TOPIC
    # Let underwater haze reach its background colour before clipping the
    # seabed; independent of the sonar's 10 m acoustic range.
    camera.find("camera/clip/far").text = "100"
    if camera_stream:
        add_camera_stream(camera, camera_stream_port)

    sensor = model.find(".//sensor[@name='multibeam_sonar']")
    sensor.find("update_rate").text = str(sonar_rate)
    sensor.find("visualize").text = "false"
    config = sensor.find(f"{{{GZ_NS}}}multibeam_sonar")
    beams, rays, bandwidth = SONAR_PROFILES[sonar_quality]
    config.find("ray/scan/horizontal/beams").text = str(beams)
    config.find("ray/scan/vertical/rays").text = str(rays)
    config.find("spec/bandwidth").text = str(bandwidth)
    config.find("spec/writeLog").text = "false"
    config.find("spec/debugFlag").text = "false"
    return model


def add_camera_stream(camera, port):
    """H.264/UDP stream of the camera for QGroundControl (ardupilot_gazebo)."""
    port = int(port)
    if not 1 <= port <= 65535:
        raise ValueError("camera_stream_port must be between 1 and 65535")
    stream = ET.SubElement(camera, "plugin", name="GstCameraPlugin", filename="GstCameraPlugin")
    for name, value in [
        ("udp_host", "127.0.0.1"),
        ("udp_port", str(port)),
        ("use_basic_pipeline", "true"),
        ("use_cuda", "false"),
        # Each low-rate frame must be independently decodable.
        ("keyframe_interval", "1"),
    ]:
        ET.SubElement(stream, name).text = value


def build_world(description_share, output, model, pose=(0.0, 0.0, -3.1, 0.0)):
    """Write the world with the configured robot placed at (x, y, z, yaw)."""
    tree = ET.parse(world_file(description_share))
    world = tree.find("world")
    model = copy.deepcopy(model)
    x, y, z, yaw = (float(v) for v in pose)
    model.find("pose").text = f"{x} {y} {z} 0 0 {yaw}"
    world.append(model)
    ET.indent(tree)
    tree.write(output, encoding="utf-8", xml_declaration=True)
    return output


# Gazebo GUI theme (gz-gui <window><style>): white panels, Gazebo's orange top
# bar and light-blue panel title bars. gz-gui uses the toolbar colours only
# when both the light and dark variants are given.
WINDOW_STYLE = {
    "material_theme": "Light",
    "material_primary": "#2F2F2F",
    "material_accent": "#03A9F4",
    **{f"toolbar_{k}_{theme}": v for theme in ("light", "dark")
       for k, v in (("color", "#FF5722"), ("text_color", "#FFFFFF"))},
    **{f"plugin_toolbar_{k}_{theme}": v for theme in ("light", "dark")
       for k, v in (("color", "#03A9F4"), ("text_color", "#FFFFFF"))},
}
WINDOW_SIZE = (1280, 900)


def gui_config(description_share, output, engine="ogre"):
    """Gazebo GUI configuration: the world's panels plus the window theme.

    engine "ogre" is the Parallels hybrid display: the Ogre 1 view cannot load
    the Ogre 2 underwater optics panel (sensor cameras keep those optics
    because they render on the server), so it is dropped; a display-only
    underwater look (fog, water colours) and anti-aliasing are added instead.
    """
    gui = ET.parse(world_file(description_share)).find("world/gui")
    plugins = []
    for plugin in gui:
        if engine == "ogre" and plugin.get("filename") == "posim_underwater_gui":
            continue
        plugin_engine = plugin.find("engine")
        if plugin_engine is not None:
            plugin_engine.text = engine
        plugins.append(plugin)
    if engine == "ogre":
        # GPU view: multisample anti-aliasing and the underwater look (fog,
        # water colours) from extras/parallels; both are cheap on the GPU.
        scene_plugin = next(p for p in plugins if p.get("filename") == "MinimalScene")
        ET.SubElement(scene_plugin, "anti_aliasing").text = "4"
        view = ET.SubElement(ET.Element("root"), "plugin", filename="RovUnderwaterView", name="Underwater view")
        properties = ET.SubElement(view, "gz-gui")
        for key, kind, value in [
            ("state", "string", "floating"),
            ("showTitleBar", "bool", "false"),
            ("resizable", "bool", "false"),
            ("width", "double", "0"),
            ("height", "double", "0"),
        ]:
            ET.SubElement(properties, "property", type=kind, key=key).text = value
        ET.SubElement(view, "water_visual").text = "waves::base_link::visual"
        plugins.append(view)
    window = ET.Element("window")
    ET.SubElement(window, "width").text = str(WINDOW_SIZE[0])
    ET.SubElement(window, "height").text = str(WINDOW_SIZE[1])
    ET.SubElement(window, "style", WINDOW_STYLE)
    Path(output).write_text(
        "\n".join(ET.tostring(e, encoding="unicode") for e in [window] + plugins) + "\n"
    )
    return output


def vehicle_description(model, mesh_roots):
    """SDF for robot_state_publisher/RViz: meshes and mounting poses only.

    Joints become fixed (propellers at rest); the simulation keeps the original.
    """
    model = copy.deepcopy(model)
    pose = model.find("pose")
    if pose is not None:
        model.remove(pose)
    for plugin in list(model.findall("plugin")):
        model.remove(plugin)
    for link in model.findall("link"):
        for sensor in list(link.findall("sensor")):
            link.remove(sensor)
    for joint in model.findall("joint"):
        joint.set("type", "fixed")
        axis = joint.find("axis")
        if axis is not None:
            joint.remove(axis)
    for uri in model.findall(".//mesh/uri"):
        if uri.text.startswith("model://"):
            relative = uri.text.removeprefix("model://")
            mesh = next(
                (Path(r) / relative for r in mesh_roots if (Path(r) / relative).is_file()),
                None,
            )
            if mesh is None:
                raise FileNotFoundError(f"Vehicle mesh not found: {uri.text}")
            uri.text = mesh.resolve().as_uri()
    sdf = ET.Element("sdf", version="1.7")
    sdf.append(model)
    return ET.tostring(sdf, encoding="unicode")

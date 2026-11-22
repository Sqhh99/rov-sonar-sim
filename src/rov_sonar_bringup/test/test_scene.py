"""The generated world embeds a correctly configured sonar ROV."""

import importlib.util
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

LAUNCH = Path(__file__).parents[1] / "launch"
DESCRIPTION = Path(
    os.environ.get("ROV_SONAR_DESCRIPTION_SRC", Path(__file__).parents[2] / "rov_sonar_description")
)

spec = importlib.util.spec_from_file_location("scene", LAUNCH / "scene.py")
scene = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scene)
GZ = "{http://gazebosim.org}"


def sonar_config(model):
    return model.find(f".//sensor[@name='multibeam_sonar']/{GZ}multibeam_sonar")


@pytest.mark.parametrize("quality", sorted(scene.SONAR_PROFILES))
def test_sonar_profiles(quality):
    model = scene.robot_model(DESCRIPTION, quality, sonar_rate=4)
    beams, rays, bandwidth = scene.SONAR_PROFILES[quality]
    config = sonar_config(model)
    assert config.findtext("ray/scan/horizontal/beams") == str(beams)
    assert config.findtext("ray/scan/vertical/rays") == str(rays)
    assert float(config.findtext("spec/bandwidth")) == bandwidth
    assert config.findtext("spec/writeLog") == "false"
    sensor = model.find(".//sensor[@name='multibeam_sonar']")
    assert float(sensor.findtext("update_rate")) == 4
    assert sensor.findtext("visualize") == "false"


def test_invalid_settings_are_rejected():
    with pytest.raises(ValueError):
        scene.robot_model(DESCRIPTION, "ultra")
    with pytest.raises(ValueError):
        scene.robot_model(DESCRIPTION, sonar_rate=0)
    with pytest.raises(ValueError):
        scene.robot_model(DESCRIPTION, camera_stream=True, camera_stream_port=70000)


def test_neutral_buoyancy_trim():
    model = scene.robot_model(DESCRIPTION)
    volume = 1.0
    for length in model.findtext(
        "link[@name='base_link']/collision/geometry/box/size"
    ).split():
        volume *= float(length)
    total = sum(float(link.findtext("inertial/mass", "0")) for link in model.findall("link"))
    assert total == pytest.approx(1025.0 * volume)


def test_camera_and_optional_stream():
    camera = scene.robot_model(DESCRIPTION).find(".//sensor[@type='camera']")
    assert camera.findtext("topic") == scene.CAMERA_TOPIC
    assert camera.find("plugin[@filename='GstCameraPlugin']") is None
    streamed = scene.robot_model(DESCRIPTION, camera_stream=True, camera_stream_port=5601)
    plugin = streamed.find(".//sensor[@type='camera']/plugin[@filename='GstCameraPlugin']")
    assert plugin.findtext("udp_port") == "5601"


def test_world_embeds_robot_at_pose(tmp_path):
    output = scene.build_world(
        DESCRIPTION, tmp_path / "world.sdf", scene.robot_model(DESCRIPTION), (1, 2, -3, 0.5)
    )
    world = ET.parse(output).find("world")
    assert world.get("name") == scene.WORLD
    robots = world.findall(f"model[@name='{scene.ROBOT}']")
    assert len(robots) == 1
    assert [float(v) for v in robots[0].findtext("pose").split()] == [1, 2, -3, 0, 0, 0.5]
    assert world.find("plugin[@name='custom::MultibeamSonarSystem']") is not None
    # The custom sensor type keeps its namespace through re-serialisation.
    assert robots[0].find(f".//sensor[@{GZ}type='multibeam_sonar']") is not None
    topics = {p.findtext("topic") for p in world.findall("gui/plugin[@filename='ImageDisplay']")}
    assert topics == {scene.CAMERA_TOPIC, scene.SONAR_FAN_TOPIC}


def test_gui_config_for_ogre1_display(tmp_path):
    text = scene.gui_config(DESCRIPTION, tmp_path / "gui.config").read_text()
    root = ET.fromstring(f"<root>{text}</root>")
    filenames = [p.get("filename") for p in root.findall("plugin")]
    assert "posim_underwater_gui" not in filenames
    assert "MinimalScene" in filenames
    assert root.find("plugin[@filename='MinimalScene']/engine").text == "ogre"


def test_vehicle_description_resolves_meshes():
    sdf = scene.vehicle_description(scene.robot_model(DESCRIPTION), [DESCRIPTION])
    root = ET.fromstring(sdf)
    uris = [u.text for u in root.iter("uri")]
    assert uris and all(u.startswith("file://") for u in uris)
    assert not list(root.iter("sensor")) and not list(root.iter("plugin"))
    assert {j.get("type") for j in root.iter("joint")} == {"fixed"}

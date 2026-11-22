"""The vehicle bridge must provide sim time and the sonar point cloud, and
must not bridge thruster commands that ArduPilotPlugin already owns."""

import importlib.util
from pathlib import Path

LAUNCH = Path(__file__).parents[1] / "launch"


def load(name):
    spec = importlib.util.spec_from_file_location(name, LAUNCH / f"{name}.launch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vehicle_bridge_topics():
    vehicle = load("vehicle")
    imu = "/world/w/model/rov/link/base_link/sensor/imu_sensor/imu"
    arguments = vehicle.bridge_arguments("rov", imu)
    assert arguments.count("/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock") == 1
    assert any(a.startswith(imu + "@") for a in arguments)
    assert any(a.startswith("/model/rov/multibeam_sonar/point_cloud@") for a in arguments)
    assert not any("cmd_thrust" in a for a in arguments)
    # Gazebo -> ROS only.
    assert all("]" not in a for a in arguments)


def test_launch_descriptions_build():
    for name in ("vehicle", "teleop"):
        assert load(name).generate_launch_description().entities

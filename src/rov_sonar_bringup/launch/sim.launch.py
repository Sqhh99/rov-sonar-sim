"""BlueROV2 Heavy with forward-looking multibeam sonar in a 4 m shallow site.

Starts Gazebo (server, optionally with its own GUI), the vehicle stack
(ArduSub SITL + MAVROS), the camera bridge, the sonar fan viewer and,
optionally, RViz and a standalone sonar window.
"""

import os
from pathlib import Path
import sys
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene  # noqa: E402


def setup(context):
    def arg(name):
        return LaunchConfiguration(name).perform(context)

    description = Path(get_package_share_directory("rov_sonar_description"))
    share = Path(get_package_share_directory("rov_sonar_bringup"))
    temporary = tempfile.TemporaryDirectory(prefix="rov-sonar-sim-")
    folder = Path(temporary.name)

    model = scene.robot_model(
        description,
        sonar_quality=arg("sonar_quality"),
        sonar_rate=arg("sonar_rate"),
        camera_stream=arg("camera_stream") == "true",
        camera_stream_port=arg("camera_stream_port"),
    )
    world = scene.build_world(
        description,
        folder / "world.sdf",
        model,
        pose=(arg("x"), arg("y"), arg("z"), arg("yaw")),
    )
    rviz_file = share / "rviz" / "rov_sonar.rviz"

    partition = arg("gz_partition") or f"rov_sonar_{os.getpid()}"
    gz = ["gz", "sim", "-v", arg("verbose")]
    if arg("gui") != "true":
        gz.append("-s")
    if arg("paused") != "true":
        gz.append("-r")
    gazebo = ExecuteProcess(cmd=gz + [str(world)], name="gazebo", output="screen")

    vehicle = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(Path(get_package_share_directory("rov_sonar_control")) / "launch/vehicle.launch.py")
        ),
        launch_arguments={
            "namespace": scene.ROBOT,
            "world_name": scene.WORLD,
            "use_ardusub": LaunchConfiguration("ardusub"),
        }.items(),
    )

    camera_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="camera_bridge",
        arguments=[f"{scene.CAMERA_TOPIC}@sensor_msgs/msg/Image[gz.msgs.Image"],
        parameters=[{"use_sim_time": True}],
    )

    robot_state = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[
            {
                "robot_description": scene.vehicle_description(model, [description]),
                "frame_prefix": scene.ROBOT + "/",
                "use_sim_time": True,
            }
        ],
    )

    sonar_view = Node(
        package="rov_sonar_bringup",
        executable="sonar_view.py",
        name="sonar_view",
        remappings=[
            ("sonar_raw", scene.sonar_topic("sonar_image_raw")),
            ("sonar_rgb", scene.SONAR_FAN_TOPIC),
        ],
        parameters=[
            {
                "use_sim_time": True,
                "gain_db": float(arg("sonar_gain_db")),
                "dynamic_range_db": float(arg("sonar_dynamic_range_db")),
                "palette": arg("sonar_palette"),
            }
        ],
    )

    # ROS -> Gazebo, for the "Sonar" panel of the Gazebo GUI.
    sonar_panel_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="sonar_panel_bridge",
        arguments=[f"{scene.SONAR_FAN_TOPIC}@sensor_msgs/msg/Image]gz.msgs.Image"],
    )

    sonar_window = Node(
        package="rqt_image_view",
        executable="rqt_image_view",
        arguments=[scene.SONAR_FAN_TOPIC],
        additional_env={"QT_QPA_PLATFORM": "xcb"},
        condition=IfCondition(LaunchConfiguration("sonar_window")),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", str(rviz_file)],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(LaunchConfiguration("rviz")),
    )

    return [
        RegisterEventHandler(
            OnShutdown(on_shutdown=[OpaqueFunction(function=lambda _c: temporary.cleanup())])
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=gazebo,
                on_exit=[EmitEvent(event=Shutdown(reason="Gazebo exited"))],
            )
        ),
        SetEnvironmentVariable("GZ_PARTITION", partition),
        SetEnvironmentVariable("POSIM_SONAR_COMPUTE_BACKEND", LaunchConfiguration("compute_backend")),
        gazebo,
        vehicle,
        camera_bridge,
        robot_state,
        sonar_view,
        sonar_panel_bridge,
        sonar_window,
        rviz,
    ]


# name: (default, choices or None, description)
ARGUMENTS = {
    "sonar_quality": (
        "balanced",
        sorted(scene.SONAR_PROFILES),
        "preview 128x64 @15 kHz | balanced 192x96 @29.9 kHz | full 512x300 @29.9 kHz",
    ),
    "sonar_rate": ("5", None, "Sonar update rate (Hz)"),
    "compute_backend": ("cpu", ["auto", "cpu", "wgpu", "cuda"], "Sonar beamforming backend"),
    "sonar_gain_db": ("3.0", None, "Display gain (dB), -30..30"),
    "sonar_dynamic_range_db": ("35.0", None, "Display dynamic range (dB), 20..100"),
    "sonar_palette": ("amber", ["amber", "gray"], "Sonar fan colour map"),
    "sonar_window": ("false", ["true", "false"], "Open an rqt_image_view window on the fan image"),
    "gui": ("true", ["true", "false"], "Run the Gazebo GUI in-process (false: server only)"),
    "rviz": ("false", ["true", "false"], "Open RViz"),
    "ardusub": ("true", ["true", "false"], "Run ArduSub SITL and MAVROS"),
    "camera_stream": ("false", ["true", "false"], "Send the camera to QGroundControl (H.264/UDP)"),
    "camera_stream_port": ("5600", None, "UDP port of the camera stream"),
    "paused": ("false", ["true", "false"], "Start the simulation paused"),
    "verbose": ("1", None, "Gazebo verbosity 0-4"),
    "x": ("0.0", None, "Initial x (m)"),
    "y": ("0.0", None, "Initial y (m)"),
    "z": ("-3.1", None, "Initial z (m); the seabed top is at -4.0"),
    "yaw": ("0.0", None, "Initial yaw (rad)"),
    "gz_partition": ("", None, "Gazebo transport partition (default: unique per launch)"),
}


def arguments(skip=(), **defaults):
    """Launch arguments, optionally without some names or with other defaults."""
    return [
        DeclareLaunchArgument(
            name,
            default_value=defaults.get(name, default),
            choices=choices,
            description=description,
        )
        for name, (default, choices, description) in ARGUMENTS.items()
        if name not in skip
    ]


def generate_launch_description():
    return LaunchDescription(arguments() + [OpaqueFunction(function=setup)])

"""Keyboard (and optional web joystick) teleoperation through MAVROS.

Run this in its own interactive terminal while the simulation is running.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    namespace = LaunchConfiguration("namespace")
    use_web_joystick = LaunchConfiguration("use_web_joystick")
    joystick_ws_port = LaunchConfiguration("joystick_ws_port")
    joystick_topic = LaunchConfiguration("joystick_topic")
    keyboard_topic = LaunchConfiguration("keyboard_topic")

    args = [
        DeclareLaunchArgument(
            "namespace",
            default_value="bluerov2_heavy_multibeam_sonar",
            description="Gazebo model name",
        ),
        DeclareLaunchArgument(
            "use_keyboard",
            default_value="true",
            choices=["true", "false"],
            description="Read keyboard input from this terminal",
        ),
        DeclareLaunchArgument(
            "use_web_joystick",
            default_value="false",
            choices=["true", "false"],
            description="Launch the websocket bridge for web/virtual_joystick.html",
        ),
        DeclareLaunchArgument("joystick_ws_host", default_value="0.0.0.0"),
        DeclareLaunchArgument("joystick_ws_port", default_value="8765"),
        DeclareLaunchArgument("joystick_topic", default_value="/joy"),
        DeclareLaunchArgument("keyboard_topic", default_value="/keyboard/joy"),
        DeclareLaunchArgument("mavros_namespace", default_value="mavros"),
    ]

    keyboard = Node(
        package="rov_sonar_control",
        executable="keyboard_publisher.py",
        output="screen",
        emulate_tty=True,
        parameters=[{"output_topic": keyboard_topic}],
        condition=IfCondition(LaunchConfiguration("use_keyboard")),
    )

    websocket = Node(
        package="rov_sonar_control",
        executable="ws_to_joy.py",
        output="screen",
        parameters=[
            {
                "ws_host": LaunchConfiguration("joystick_ws_host"),
                "ws_port": joystick_ws_port,
                "output_topic": joystick_topic,
            }
        ],
        condition=IfCondition(use_web_joystick),
    )

    manual_control = Node(
        package="rov_sonar_control",
        executable="ardusub_manual_control.py",
        output="screen",
        parameters=[
            {
                "model_name": namespace,
                "joystick_topic": joystick_topic,
                "keyboard_topic": keyboard_topic,
                "mavros_namespace": LaunchConfiguration("mavros_namespace"),
            }
        ],
    )

    web_hint = LogInfo(
        msg=[
            "Web joystick enabled. Open ",
            PathJoinSubstitution(
                [FindPackageShare("rov_sonar_control"), "web", "virtual_joystick.html"]
            ),
            " and connect to ws://127.0.0.1:",
            joystick_ws_port,
        ],
        condition=IfCondition(use_web_joystick),
    )

    return LaunchDescription(args + [keyboard, websocket, manual_control, web_hint])

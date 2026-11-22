"""Vehicle stack: Gazebo bridges, ArduSub SITL, MAVROS and marine GNSS input.

ArduSub starts only after the Gazebo IMU topic exists, and MAVROS only after
ArduSub starts. Teleoperation is a separate launch (teleop.launch.py) because
the keyboard node needs its own interactive terminal.
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def bridge_arguments(namespace, imu_gz_topic):
    # ArduPilotPlugin already publishes the thruster command topics on Gazebo
    # transport; bridging them would add a second publisher with no ROS source.
    return [
        "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        f"/model/{namespace}/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
        (
            f"/model/{namespace}/odometry_with_covariance@"
            "nav_msgs/msg/Odometry[gz.msgs.OdometryWithCovariance"
        ),
        f"/model/{namespace}/pose@geometry_msgs/msg/PoseArray[gz.msgs.Pose_V",
        f"{imu_gz_topic}@sensor_msgs/msg/Imu[gz.msgs.IMU",
        f"/model/{namespace}/magnetometer@sensor_msgs/msg/MagneticField[gz.msgs.Magnetometer",
        (
            f"/model/{namespace}/multibeam_sonar/point_cloud@"
            "sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked"
        ),
    ]


def launch_setup(context, *args, **kwargs):
    namespace = LaunchConfiguration("namespace").perform(context)
    world_name = LaunchConfiguration("world_name").perform(context)
    imu_gz_topic = f"/world/{world_name}/model/{namespace}/link/base_link/sensor/imu_sensor/imu"
    use_ardusub = LaunchConfiguration("use_ardusub")

    sonar_frame = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=[
            "--frame-id",
            f"{namespace}/sonar_link",
            "--child-frame-id",
            f"{namespace}/sonar_link/multibeam_sonar",
        ],
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="vehicle_bridge",
        arguments=bridge_arguments(namespace, imu_gz_topic),
        remappings=[(imu_gz_topic, f"/model/{namespace}/imu")],
        output="screen",
    )

    wait_for_imu = ExecuteProcess(
        cmd=[
            "/usr/bin/env",
            "bash",
            "-c",
            "while true; do "
            f"if timeout 2 gz topic -e -t '{imu_gz_topic}' -n 1 >/dev/null 2>&1; "
            "then exit 0; fi; done",
        ],
        name="wait_for_gazebo_imu",
        output="screen",
        condition=IfCondition(use_ardusub),
    )

    ardusub = ExecuteProcess(
        cmd=[
            "ardusub",
            "--speedup",
            "1",
            "-w",
            "--model",
            LaunchConfiguration("ardusub_model"),
            "--defaults",
            LaunchConfiguration("ardusub_params"),
            "-IO",
            "--home",
            LaunchConfiguration("ardusub_home"),
        ],
        name="ardusub",
        output="screen",
        condition=IfCondition(use_ardusub),
    )

    mavros = Node(
        package="mavros",
        executable="mavros_node",
        output="screen",
        parameters=[{"use_sim_time": True}, LaunchConfiguration("mavros_file")],
        condition=IfCondition(use_ardusub),
    )

    marine_gnss = Node(
        package="rov_sonar_control",
        executable="marine_gnss_input",
        parameters=[{"use_sim_time": True, "gz_topic": f"/model/{namespace}/gnss"}],
        output="screen",
        condition=IfCondition(use_ardusub),
    )

    return [
        sonar_frame,
        bridge,
        marine_gnss,
        RegisterEventHandler(OnProcessStart(target_action=bridge, on_start=[wait_for_imu])),
        RegisterEventHandler(
            OnProcessExit(
                target_action=wait_for_imu,
                on_exit=[LogInfo(msg="Gazebo IMU topic detected, launching ArduSub"), ardusub],
            )
        ),
        RegisterEventHandler(
            OnProcessStart(
                target_action=ardusub,
                on_start=[LogInfo(msg="ArduSub started, launching MAVROS"), mavros],
            )
        ),
    ]


def generate_launch_description():
    share = FindPackageShare("rov_sonar_control")
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "namespace",
                default_value="bluerov2_heavy_multibeam_sonar",
                description="Gazebo model name",
            ),
            DeclareLaunchArgument(
                "world_name", default_value="shallow_underwater", description="Gazebo world name"
            ),
            DeclareLaunchArgument(
                "use_ardusub",
                default_value="true",
                choices=["true", "false"],
                description="Launch ArduSub SITL, MAVROS and the GNSS input bridge",
            ),
            DeclareLaunchArgument(
                "mavros_file",
                default_value=PathJoinSubstitution([share, "config", "mavros.yaml"]),
                description="MAVROS parameter file",
            ),
            DeclareLaunchArgument(
                "ardusub_params",
                default_value=PathJoinSubstitution([share, "config", "ardusub.parm"]),
                description="ArduSub default parameter file",
            ),
            DeclareLaunchArgument(
                "ardusub_model",
                default_value="JSON:127.0.0.1",
                description="ArduSub SITL physics backend",
            ),
            DeclareLaunchArgument(
                "ardusub_home",
                default_value="35.074823,129.084798,0.0,270.0",
                description="ArduSub HOME (lat,lon,alt,heading)",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )

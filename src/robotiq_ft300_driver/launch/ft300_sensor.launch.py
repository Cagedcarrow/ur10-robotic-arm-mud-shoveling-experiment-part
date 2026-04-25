from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_params_file = PathJoinSubstitution(
        [FindPackageShare("robotiq_ft300_driver"), "config", "ft300_params.yaml"]
    )

    params_file = LaunchConfiguration("params_file")
    use_mock = LaunchConfiguration("use_mock")
    port = LaunchConfiguration("port")
    baudrate = LaunchConfiguration("baudrate")
    timeout = LaunchConfiguration("timeout")
    frame_id = LaunchConfiguration("frame_id")
    publish_rate = LaunchConfiguration("publish_rate")
    comm_mode = LaunchConfiguration("comm_mode")
    slave_id = LaunchConfiguration("slave_id")
    validate_crc = LaunchConfiguration("validate_crc")

    sensor_node = Node(
        package="robotiq_ft300_driver",
        executable="ft300_sensor_node",
        name="ft300_sensor_node",
        output="screen",
        parameters=[
            params_file,
            {
                "use_mock": use_mock,
                "port": port,
                "baudrate": baudrate,
                "timeout": timeout,
                "frame_id": frame_id,
                "publish_rate": publish_rate,
                "comm_mode": comm_mode,
                "slave_id": slave_id,
                "validate_crc": validate_crc,
            },
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("params_file", default_value=default_params_file),
            DeclareLaunchArgument("use_mock", default_value="true"),
            DeclareLaunchArgument("port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("baudrate", default_value="19200"),
            DeclareLaunchArgument("timeout", default_value="0.1"),
            DeclareLaunchArgument("frame_id", default_value="ft300_sensor_link"),
            DeclareLaunchArgument("publish_rate", default_value="100.0"),
            DeclareLaunchArgument("comm_mode", default_value="datastream"),
            DeclareLaunchArgument("slave_id", default_value="9"),
            DeclareLaunchArgument("validate_crc", default_value="true"),
            sensor_node,
        ]
    )

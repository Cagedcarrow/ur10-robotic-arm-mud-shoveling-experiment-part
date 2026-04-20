import os
import subprocess
import sys
import time

import rclpy

from ur10_examples_py.env_bootstrap import bootstrap_ros_python_environment


bootstrap_ros_python_environment()


def run_command(command):
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}")


def main():
    rclpy.init(args=sys.argv)
    node = rclpy.create_node("capture_and_import_pcd")
    node.declare_parameter("pcd_file", "/root/ur10_ws/data/latest_obstacle.pcd")
    node.declare_parameter("pointcloud_topic", "/overhead_camera/points")
    node.declare_parameter("obstacle_id", "pcd_obstacle_box")

    pcd_file = node.get_parameter("pcd_file").value
    pointcloud_topic = node.get_parameter("pointcloud_topic").value
    obstacle_id = node.get_parameter("obstacle_id").value

    os.makedirs(os.path.dirname(pcd_file), exist_ok=True)
    if os.path.exists(pcd_file):
        os.remove(pcd_file)

    node.get_logger().info(f"Capturing a point cloud frame into {pcd_file}")
    run_command(
        [
            "ros2",
            "run",
            "ur10_perception",
            "pcd_capture_node",
            "--ros-args",
            "-p",
            f"pointcloud_topic:={pointcloud_topic}",
            "-p",
            f"output_file:={pcd_file}",
        ]
    )

    for _ in range(40):
        if os.path.exists(pcd_file) and os.path.getsize(pcd_file) > 0:
            break
        time.sleep(0.25)
    else:
        raise RuntimeError(f"PCD file was not created: {pcd_file}")

    node.get_logger().info(
        f"Importing {pcd_file} as planning-scene obstacle {obstacle_id}"
    )
    run_command(
        [
            "ros2",
            "run",
            "ur10_perception",
            "pcd_to_collision_scene_node",
            "--ros-args",
            "-p",
            f"pcd_file:={pcd_file}",
            "-p",
            f"obstacle_id:={obstacle_id}",
        ]
    )

    node.destroy_node()
    rclpy.shutdown()

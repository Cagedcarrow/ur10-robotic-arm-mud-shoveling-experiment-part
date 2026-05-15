#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import List

import rclpy
from moveit_msgs.msg import AllowedCollisionEntry, AllowedCollisionMatrix, PlanningScene
from moveit_msgs.srv import ApplyPlanningScene


LINK_NAMES: List[str] = [
    "base_jizuo",
    "base_jizuo_base_ur10_with_dizuo",
    "base_link",
    "base_link_inertia",
    "base",
    "shoulder_link",
    "upper_arm_link",
    "forearm_link",
    "wrist_1_link",
    "wrist_2_link",
    "wrist_3_link",
    "ft_frame",
    "flange",
    "tool0",
    "sensor_shovel",
    "sensor_shovel_tcp",
]


def build_scene() -> PlanningScene:
    acm = AllowedCollisionMatrix()
    acm.entry_names = list(LINK_NAMES)
    acm.entry_values = [
        AllowedCollisionEntry(enabled=[True] * len(LINK_NAMES))
        for _ in LINK_NAMES
    ]
    acm.default_entry_names = list(LINK_NAMES)
    acm.default_entry_values = [True] * len(LINK_NAMES)

    scene = PlanningScene()
    scene.is_diff = True
    scene.allowed_collision_matrix = acm
    return scene


def main() -> int:
    rclpy.init()
    node = rclpy.create_node("allow_all_moveit_collisions")
    client = node.create_client(ApplyPlanningScene, "/apply_planning_scene")

    try:
        node.get_logger().info("Waiting for /apply_planning_scene to disable MoveIt collision checks...")
        if not client.wait_for_service(timeout_sec=30.0):
            node.get_logger().error("APPLY_PLANNING_SCENE_UNAVAILABLE")
            return 2

        request = ApplyPlanningScene.Request()
        request.scene = build_scene()
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)

        if not future.done() or future.result() is None:
            node.get_logger().error("MOVEIT_COLLISION_DISABLE_TIMEOUT")
            return 3
        if not future.result().success:
            node.get_logger().error("MOVEIT_COLLISION_DISABLE_REJECTED")
            return 4

        node.get_logger().info(
            f"MOVEIT_ALL_COLLISIONS_ALLOWED links={len(LINK_NAMES)} pairs={len(LINK_NAMES) * (len(LINK_NAMES) - 1) // 2}"
        )
        node.get_logger().warn(
            "MoveIt planning collisions are disabled; real UR safety mode, protective stop, External Control, and RTDE health still apply."
        )
        return 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())

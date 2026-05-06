#!/usr/bin/env python3
from typing import Dict, List

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from sensor_msgs.msg import JointState


class Ur10JointStateRemapNode(Node):
    def __init__(self) -> None:
        super().__init__('ur10_joint_state_remap_node')

        self.declare_parameter('input_topic', '/joint_states')
        self.declare_parameter('output_topic', '/assembly/joint_states')
        self.declare_parameter('source_joint_names', [
            'shoulder_pan_joint',
            'shoulder_lift_joint',
            'elbow_joint',
            'wrist_1_joint',
            'wrist_2_joint',
            'wrist_3_joint',
        ])
        self.declare_parameter('target_joint_names', [
            'ur10_shoulder_pan',
            'ur10_shoulder_lift',
            'ur10_elbow',
            'ur10_wrist_1',
            'ur10_wrist_2',
            'ur10_wrist_3',
        ])
        self.declare_parameter('position_signs', [1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        self.declare_parameter('position_offsets', [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.declare_parameter('first_msg_timeout_sec', 3.0)

        self._input_topic = self.get_parameter('input_topic').value
        self._output_topic = self.get_parameter('output_topic').value
        self._source_joint_names: List[str] = list(self.get_parameter('source_joint_names').value)
        self._target_joint_names: List[str] = list(self.get_parameter('target_joint_names').value)
        self._position_signs: List[float] = [float(v) for v in self.get_parameter('position_signs').value]
        self._position_offsets: List[float] = [float(v) for v in self.get_parameter('position_offsets').value]
        self._first_msg_timeout_sec = float(self.get_parameter('first_msg_timeout_sec').value)

        lengths = [
            len(self._source_joint_names),
            len(self._target_joint_names),
            len(self._position_signs),
            len(self._position_offsets),
        ]
        if len(set(lengths)) != 1:
            raise ValueError(
                'Parameter length mismatch: source_joint_names, target_joint_names, '
                'position_signs, and position_offsets must have identical lengths.'
            )

        self._map_index: Dict[str, int] = {name: idx for idx, name in enumerate(self._source_joint_names)}
        self._received_first_msg = False

        self._pub = self.create_publisher(JointState, self._output_topic, 50)
        self._sub = self.create_subscription(JointState, self._input_topic, self._on_joint_state, 50)

        self._startup_time = self.get_clock().now()
        self._warned_timeout = False
        self._timeout_timer = self.create_timer(0.5, self._check_first_msg_timeout)

        self.get_logger().info(
            f'Started. input_topic={self._input_topic}, output_topic={self._output_topic}, '
            f'joints={len(self._source_joint_names)}'
        )

    def _check_first_msg_timeout(self) -> None:
        if self._received_first_msg or self._warned_timeout:
            return
        elapsed = self.get_clock().now() - self._startup_time
        if elapsed >= Duration(seconds=self._first_msg_timeout_sec):
            self._warned_timeout = True
            self.get_logger().warning(
                f'No JointState received on {self._input_topic} within '
                f'{self._first_msg_timeout_sec:.1f}s. Ensure ur_robot_driver is running.'
            )

    def _on_joint_state(self, msg: JointState) -> None:
        if not self._received_first_msg:
            self._received_first_msg = True
            self.get_logger().info('Received first JointState message.')

        name_to_position = {name: pos for name, pos in zip(msg.name, msg.position)}

        missing = [name for name in self._source_joint_names if name not in name_to_position]
        if missing:
            self.get_logger().warning(
                f'Input JointState missing joints: {missing}. message_joints={msg.name}',
                throttle_duration_sec=2.0,
            )
            return

        out = JointState()
        if msg.header.stamp.sec == 0 and msg.header.stamp.nanosec == 0:
            out.header.stamp = self.get_clock().now().to_msg()
        else:
            out.header.stamp = msg.header.stamp

        out.name = list(self._target_joint_names)
        out.position = []
        for idx, source_name in enumerate(self._source_joint_names):
            source_position = name_to_position[source_name]
            mapped_position = self._position_signs[idx] * source_position + self._position_offsets[idx]
            out.position.append(mapped_position)

        if msg.velocity and len(msg.velocity) == len(msg.name):
            name_to_velocity = {name: vel for name, vel in zip(msg.name, msg.velocity)}
            out.velocity = [
                self._position_signs[idx] * name_to_velocity[source_name]
                for idx, source_name in enumerate(self._source_joint_names)
            ]

        if msg.effort and len(msg.effort) == len(msg.name):
            name_to_effort = {name: eff for name, eff in zip(msg.name, msg.effort)}
            out.effort = [name_to_effort[source_name] for source_name in self._source_joint_names]

        self._pub.publish(out)


def main() -> None:
    rclpy.init()
    node = Ur10JointStateRemapNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

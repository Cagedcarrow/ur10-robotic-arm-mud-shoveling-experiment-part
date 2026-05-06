#!/usr/bin/env python3
from __future__ import annotations

import socket
import struct
import time
from typing import List, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class Ur10JointStateTcpNode(Node):
    def __init__(self) -> None:
        super().__init__('ur10_joint_state_tcp_node')

        self.declare_parameter('ur_ip', '10.160.9.21')
        self.declare_parameter('ur_port', 30003)
        self.declare_parameter('socket_timeout_sec', 3.0)
        self.declare_parameter('reconnect_interval_sec', 1.0)
        self.declare_parameter('output_topic', '/joint_states')
        self.declare_parameter('joint_names', [
            'ur10_shoulder_pan',
            'ur10_shoulder_lift',
            'ur10_elbow',
            'ur10_wrist_1',
            'ur10_wrist_2',
            'ur10_wrist_3',
        ])
        self.declare_parameter('position_signs', [1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        self.declare_parameter('position_offsets', [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        self._ur_ip = str(self.get_parameter('ur_ip').value)
        self._ur_port = int(self.get_parameter('ur_port').value)
        self._socket_timeout_sec = float(self.get_parameter('socket_timeout_sec').value)
        self._reconnect_interval_sec = float(self.get_parameter('reconnect_interval_sec').value)
        self._output_topic = str(self.get_parameter('output_topic').value)
        self._joint_names: List[str] = [str(v) for v in self.get_parameter('joint_names').value]
        self._position_signs: List[float] = [float(v) for v in self.get_parameter('position_signs').value]
        self._position_offsets: List[float] = [float(v) for v in self.get_parameter('position_offsets').value]

        if not (len(self._joint_names) == len(self._position_signs) == len(self._position_offsets) == 6):
            raise ValueError('joint_names/position_signs/position_offsets must all have length 6')

        self._pub = self.create_publisher(JointState, self._output_topic, 50)
        self._sock: Optional[socket.socket] = None
        self._last_reconnect_attempt = 0.0
        self._connected_once = False

        # Moderate rate timer; reads one packet when available.
        self._timer = self.create_timer(0.004, self._spin_once)
        self.get_logger().info(
            f'Started TCP reader: {self._ur_ip}:{self._ur_port} -> {self._output_topic}'
        )

    def _connect(self) -> bool:
        now = time.time()
        if now - self._last_reconnect_attempt < self._reconnect_interval_sec:
            return False
        self._last_reconnect_attempt = now

        self._close_socket()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._socket_timeout_sec)
            sock.connect((self._ur_ip, self._ur_port))
            self._sock = sock
            if not self._connected_once:
                self.get_logger().info('Connected to UR realtime socket.')
                self._connected_once = True
            else:
                self.get_logger().warning('Reconnected to UR realtime socket.')
            return True
        except Exception as exc:
            self.get_logger().warning(
                f'Failed to connect {self._ur_ip}:{self._ur_port}: {exc}',
                throttle_duration_sec=2.0,
            )
            self._sock = None
            return False

    def _close_socket(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _recv_exact(self, nbytes: int) -> Optional[bytes]:
        if self._sock is None:
            return None
        buf = bytearray()
        while len(buf) < nbytes:
            try:
                chunk = self._sock.recv(nbytes - len(buf))
            except socket.timeout:
                return None
            except Exception:
                return None
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    def _read_packet(self) -> Optional[bytes]:
        head = self._recv_exact(4)
        if head is None or len(head) < 4:
            return None
        p_len = struct.unpack('!i', head)[0]
        if p_len <= 4 or p_len > 10000:
            return None
        body = self._recv_exact(p_len - 4)
        if body is None:
            return None
        return head + body

    def _parse_act_q(self, packet: bytes) -> Optional[List[float]]:
        # Reuse same offsets as ur10_ft300_monitor/scripts/ur_reader.py
        if len(packet) < 300:
            return None
        try:
            return list(struct.unpack('!6d', packet[252:300]))
        except Exception:
            return None

    def _spin_once(self) -> None:
        if self._sock is None and not self._connect():
            return

        packet = self._read_packet()
        if packet is None:
            self.get_logger().warning('UR realtime read timeout/disconnect; reconnecting...', throttle_duration_sec=2.0)
            self._close_socket()
            return

        q = self._parse_act_q(packet)
        if q is None:
            self.get_logger().warning('Failed parsing UR realtime packet.', throttle_duration_sec=2.0)
            return

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(self._joint_names)
        msg.position = [
            self._position_signs[i] * q[i] + self._position_offsets[i]
            for i in range(6)
        ]
        self._pub.publish(msg)

    def destroy_node(self) -> bool:
        self._close_socket()
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = Ur10JointStateTcpNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

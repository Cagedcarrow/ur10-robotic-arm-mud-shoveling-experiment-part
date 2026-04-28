#!/usr/bin/env python3
import math
from typing import Optional

import rclpy
from geometry_msgs.msg import Point
from gazebo_msgs.srv import DeleteEntity, SpawnEntity
from rclpy.node import Node
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker
from ur10_trajectory_planner.msg import BucketFeatures


class BucketSceneNode(Node):
    def __init__(self):
        super().__init__('bucket_scene_node')
        self.declare_parameter('use_bucket', True)
        self.declare_parameter('bucket_center_x', 0.8)
        self.declare_parameter('bucket_center_y', 0.0)
        self.declare_parameter('bucket_center_z', 0.0)
        self.declare_parameter('bucket_radius', 0.18)
        self.declare_parameter('bucket_height', 0.30)
        self.declare_parameter('bucket_wall_thickness', 0.005)
        self.declare_parameter('safe_margin', 0.03)
        self.declare_parameter('frame_id', 'world')

        self.spawn_client = self.create_client(SpawnEntity, '/spawn_entity')
        self.delete_client = self.create_client(DeleteEntity, '/delete_entity')
        self.marker_pub = self.create_publisher(Marker, '/bucket/marker', 10)
        self.safe_pub = self.create_publisher(Marker, '/bucket/safe_margin_marker', 10)
        self.feature_pub = self.create_publisher(BucketFeatures, '/bucket/features', 10)

        self._spawned = False
        self._spawn_inflight = False
        self._timer = self.create_timer(0.5, self._tick)
        self._marker_timer = self.create_timer(0.2, self._publish_markers)

    def _params(self):
        return {
            'use_bucket': bool(self.get_parameter('use_bucket').value),
            'x': float(self.get_parameter('bucket_center_x').value),
            'y': float(self.get_parameter('bucket_center_y').value),
            'z': float(self.get_parameter('bucket_center_z').value),
            'r': float(self.get_parameter('bucket_radius').value),
            'h': float(self.get_parameter('bucket_height').value),
            't': float(self.get_parameter('bucket_wall_thickness').value),
            's': float(self.get_parameter('safe_margin').value),
            'frame': str(self.get_parameter('frame_id').value),
        }

    def _bucket_sdf(self, x: float, y: float, z: float, r: float, h: float, t: float) -> str:
        outer_r = max(0.01, r)
        inner_r = max(0.005, outer_r - max(0.001, t))
        return f"""
<sdf version='1.6'>
  <model name='cylinder_bucket'>
    <static>true</static>
    <pose>{x} {y} {z + h / 2.0} 0 0 0</pose>
    <link name='bucket_link'>
      <collision name='bucket_outer_collision'>
        <geometry><cylinder><radius>{outer_r}</radius><length>{h}</length></cylinder></geometry>
      </collision>
      <visual name='bucket_outer_visual'>
        <geometry><cylinder><radius>{outer_r}</radius><length>{h}</length></cylinder></geometry>
        <material><ambient>0.2 0.4 0.8 0.3</ambient><diffuse>0.2 0.4 0.8 0.3</diffuse></material>
      </visual>
      <collision name='bucket_inner_hole_collision'>
        <pose>0 0 0 0 0 0</pose>
        <geometry><cylinder><radius>{inner_r}</radius><length>{h - 0.01}</length></cylinder></geometry>
      </collision>
      <visual name='bucket_inner_visual'>
        <geometry><cylinder><radius>{inner_r}</radius><length>{h - 0.01}</length></cylinder></geometry>
        <material><ambient>0.1 0.1 0.1 0.05</ambient><diffuse>0.1 0.1 0.1 0.05</diffuse></material>
      </visual>
    </link>
  </model>
</sdf>
"""

    def _tick(self):
        p = self._params()
        if not p['use_bucket']:
            return
        if self._spawned:
            return
        if self._spawn_inflight:
            return
        if not self.spawn_client.wait_for_service(timeout_sec=0.1):
            return

        self._spawn_inflight = True
        req = SpawnEntity.Request()
        req.name = 'cylinder_bucket'
        req.xml = self._bucket_sdf(p['x'], p['y'], p['z'], p['r'], p['h'], p['t'])
        req.robot_namespace = ''
        req.reference_frame = p['frame']
        fut = self.spawn_client.call_async(req)

        def done_cb(f):
            try:
                _ = f.result()
                self._spawned = True
                self.get_logger().info('Bucket spawned in Gazebo')
            except Exception as exc:
                self.get_logger().warn(f'Bucket spawn failed: {exc}')
            finally:
                self._spawn_inflight = False

        fut.add_done_callback(done_cb)

    def _publish_markers(self):
        p = self._params()
        if not p['use_bucket']:
            return

        bucket = Marker()
        bucket.header.frame_id = p['frame']
        bucket.header.stamp = self.get_clock().now().to_msg()
        bucket.ns = 'bucket'
        bucket.id = 1
        bucket.type = Marker.CYLINDER
        bucket.action = Marker.ADD
        bucket.pose.position.x = p['x']
        bucket.pose.position.y = p['y']
        bucket.pose.position.z = p['z'] + p['h'] / 2.0
        bucket.pose.orientation.w = 1.0
        bucket.scale.x = 2.0 * p['r']
        bucket.scale.y = 2.0 * p['r']
        bucket.scale.z = p['h']
        bucket.color = ColorRGBA(r=0.2, g=0.5, b=0.9, a=0.35)
        self.marker_pub.publish(bucket)

        safe = Marker()
        safe.header = bucket.header
        safe.ns = 'bucket_safe'
        safe.id = 2
        safe.type = Marker.CYLINDER
        safe.action = Marker.ADD
        safe.pose = bucket.pose
        safe.scale.x = 2.0 * max(0.01, p['r'] - p['s'])
        safe.scale.y = 2.0 * max(0.01, p['r'] - p['s'])
        safe.scale.z = p['h']
        safe.color = ColorRGBA(r=1.0, g=0.6, b=0.1, a=0.15)
        self.safe_pub.publish(safe)

        features = BucketFeatures()
        features.header.frame_id = p['frame']
        features.header.stamp = self.get_clock().now().to_msg()
        features.top_point.x = p['x']
        features.top_point.y = p['y']
        features.top_point.z = p['z'] + p['h']
        features.top_radius = p['r']
        features.bottom_radius = p['r']
        features.depth = p['h']
        features.max_radius = p['r']
        features.dig_direction.x = -1.0
        features.dig_direction.y = 0.0
        features.dig_direction.z = 0.0
        self.feature_pub.publish(features)


def main():
    rclpy.init()
    node = BucketSceneNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

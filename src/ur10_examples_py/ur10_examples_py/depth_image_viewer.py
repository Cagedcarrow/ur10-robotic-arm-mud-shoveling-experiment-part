import os

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

from ur10_examples_py.env_bootstrap import bootstrap_ros_python_environment


bootstrap_ros_python_environment()


def declare_if_missing(node: Node, name: str, default_value):
    if not node.has_parameter(name):
        node.declare_parameter(name, default_value)


class DepthImageViewer(Node):
    def __init__(self):
        super().__init__(
            "gantry_depth_image_viewer", automatically_declare_parameters_from_overrides=True
        )
        declare_if_missing(self, "image_topic", "/gantry_depth_camera/depth/image_raw")
        declare_if_missing(self, "window_name", "Gantry Depth Camera")
        declare_if_missing(self, "min_depth", 0.10)
        declare_if_missing(self, "max_depth", 3.50)
        declare_if_missing(self, "use_sim_time", True)

        self._window_name = str(self.get_parameter("window_name").value)
        self._min_depth = float(self.get_parameter("min_depth").value)
        self._max_depth = float(self.get_parameter("max_depth").value)
        self._bridge = CvBridge()
        self._gui_available = bool(os.environ.get("DISPLAY"))
        self._warned_no_display = False

        self.create_subscription(
            Image,
            str(self.get_parameter("image_topic").value),
            self._image_callback,
            10,
        )

    def _image_callback(self, msg: Image):
        if not self._gui_available:
            if not self._warned_no_display:
                self.get_logger().warning(
                    "DISPLAY is not set. Depth image window will not be shown in this session."
                )
                self._warned_no_display = True
            return

        image = self._bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        depth = np.array(image, dtype=np.float32)
        depth[~np.isfinite(depth)] = self._max_depth
        depth = np.clip(depth, self._min_depth, self._max_depth)
        normalized = ((depth - self._min_depth) / (self._max_depth - self._min_depth) * 255.0)
        normalized = normalized.astype(np.uint8)
        colored = cv2.applyColorMap(255 - normalized, cv2.COLORMAP_JET)
        cv2.imshow(self._window_name, colored)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = DepthImageViewer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

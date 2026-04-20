#include <cmath>
#include <memory>
#include <string>
#include <vector>

#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl_conversions/pcl_conversions.h>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>

class SyntheticOverheadCameraNode : public rclcpp::Node
{
public:
  SyntheticOverheadCameraNode()
  : Node("synthetic_overhead_camera_node")
  {
    topic_name_ = declare_parameter<std::string>("pointcloud_topic", "/overhead_camera/points");
    frame_id_ = declare_parameter<std::string>("frame_id", "world");
    publish_rate_hz_ = declare_parameter<double>("publish_rate_hz", 2.0);

    publisher_ = create_publisher<sensor_msgs::msg::PointCloud2>(topic_name_, rclcpp::QoS(10));
    timer_ = create_wall_timer(
      std::chrono::duration<double>(1.0 / std::max(0.1, publish_rate_hz_)),
      std::bind(&SyntheticOverheadCameraNode::publishPointCloud, this));
  }

private:
  static void addBoxSurface(
    pcl::PointCloud<pcl::PointXYZ> & cloud, double cx, double cy, double cz,
    double sx, double sy, double sz, double spacing)
  {
    const double min_x = cx - sx * 0.5;
    const double max_x = cx + sx * 0.5;
    const double min_y = cy - sy * 0.5;
    const double max_y = cy + sy * 0.5;
    const double min_z = cz - sz * 0.5;
    const double max_z = cz + sz * 0.5;

    for (double x = min_x; x <= max_x + 1e-6; x += spacing) {
      for (double y = min_y; y <= max_y + 1e-6; y += spacing) {
        cloud.emplace_back(static_cast<float>(x), static_cast<float>(y), static_cast<float>(max_z));
      }
    }

    for (double y = min_y; y <= max_y + 1e-6; y += spacing) {
      for (double z = min_z; z <= max_z + 1e-6; z += spacing) {
        cloud.emplace_back(static_cast<float>(min_x), static_cast<float>(y), static_cast<float>(z));
        cloud.emplace_back(static_cast<float>(max_x), static_cast<float>(y), static_cast<float>(z));
      }
    }

    for (double x = min_x; x <= max_x + 1e-6; x += spacing) {
      for (double z = min_z; z <= max_z + 1e-6; z += spacing) {
        cloud.emplace_back(static_cast<float>(x), static_cast<float>(min_y), static_cast<float>(z));
        cloud.emplace_back(static_cast<float>(x), static_cast<float>(max_y), static_cast<float>(z));
      }
    }
  }

  void publishPointCloud()
  {
    pcl::PointCloud<pcl::PointXYZ> cloud;
    cloud.reserve(60000);

    // Thin tabletop matching obstacle_scene.world. The legs are omitted because the
    // overhead camera is only used to recover the support plane and the obstacle.
    addBoxSurface(cloud, 0.95, 0.0, 0.675, 0.70, 1.00, 0.05, 0.03);
    // Obstacle box on top of the table.
    addBoxSurface(cloud, 0.95, 0.0, 0.78, 0.16, 0.22, 0.16, 0.01);

    cloud.width = static_cast<uint32_t>(cloud.size());
    cloud.height = 1;
    cloud.is_dense = true;

    sensor_msgs::msg::PointCloud2 message;
    pcl::toROSMsg(cloud, message);
    message.header.stamp = now();
    message.header.frame_id = frame_id_;
    publisher_->publish(message);
  }

  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  std::string topic_name_;
  std::string frame_id_;
  double publish_rate_hz_{2.0};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<SyntheticOverheadCameraNode>());
  rclcpp::shutdown();
  return 0;
}

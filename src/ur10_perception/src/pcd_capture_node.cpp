#include <chrono>
#include <filesystem>
#include <memory>
#include <string>

#include <pcl/filters/voxel_grid.h>
#include <pcl/io/pcd_io.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl_conversions/pcl_conversions.h>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>

using namespace std::chrono_literals;

class PcdCaptureNode : public rclcpp::Node
{
public:
  PcdCaptureNode()
  : Node("pcd_capture_node")
  {
    topic_name_ = declare_parameter<std::string>("pointcloud_topic", "/overhead_camera/points");
    output_file_ = declare_parameter<std::string>(
      "output_file", "/root/ur10_ws/data/latest_obstacle.pcd");
    voxel_leaf_size_ = declare_parameter<double>("voxel_leaf_size", 0.01);
    timeout_sec_ = declare_parameter<double>("timeout_sec", 20.0);

    subscription_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      topic_name_, rclcpp::SensorDataQoS(),
      std::bind(&PcdCaptureNode::pointCloudCallback, this, std::placeholders::_1));

    timeout_timer_ = create_wall_timer(
      500ms, std::bind(&PcdCaptureNode::timeoutCheck, this));

    start_time_ = now();
    RCLCPP_INFO(get_logger(), "Waiting for a point cloud on %s", topic_name_.c_str());
  }

private:
  void pointCloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg)
  {
    if (captured_) {
      return;
    }

    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZ>());
    pcl::fromROSMsg(*msg, *cloud);
    if (cloud->empty()) {
      RCLCPP_WARN(get_logger(), "Received empty point cloud, waiting for the next frame.");
      return;
    }

    pcl::PointCloud<pcl::PointXYZ>::Ptr downsampled(new pcl::PointCloud<pcl::PointXYZ>());
    pcl::VoxelGrid<pcl::PointXYZ> voxel_grid;
    voxel_grid.setInputCloud(cloud);
    voxel_grid.setLeafSize(voxel_leaf_size_, voxel_leaf_size_, voxel_leaf_size_);
    voxel_grid.filter(*downsampled);

    std::filesystem::create_directories(std::filesystem::path(output_file_).parent_path());
    if (pcl::io::savePCDFileBinary(output_file_, *downsampled) != 0) {
      RCLCPP_ERROR(get_logger(), "Failed to write PCD file to %s", output_file_.c_str());
      rclcpp::shutdown();
      return;
    }

    captured_ = true;
    RCLCPP_INFO(
      get_logger(), "Saved %zu points to %s", downsampled->size(), output_file_.c_str());
    rclcpp::shutdown();
  }

  void timeoutCheck()
  {
    if (captured_) {
      return;
    }

    const auto elapsed = (now() - start_time_).seconds();
    if (elapsed > timeout_sec_) {
      RCLCPP_ERROR(
        get_logger(), "Timed out after %.1f seconds waiting for %s",
        timeout_sec_, topic_name_.c_str());
      rclcpp::shutdown();
    }
  }

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr subscription_;
  rclcpp::TimerBase::SharedPtr timeout_timer_;
  rclcpp::Time start_time_;
  std::string topic_name_;
  std::string output_file_;
  double voxel_leaf_size_{0.01};
  double timeout_sec_{20.0};
  bool captured_{false};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<PcdCaptureNode>());
  if (rclcpp::ok()) {
    rclcpp::shutdown();
  }
  return 0;
}

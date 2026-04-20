#include <chrono>
#include <filesystem>
#include <limits>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include <geometry_msgs/msg/pose.hpp>
#include <moveit/planning_scene_interface/planning_scene_interface.h>
#include <moveit_msgs/msg/collision_object.hpp>
#include <pcl/filters/extract_indices.h>
#include <pcl/filters/passthrough.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/io/pcd_io.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/search/kdtree.h>
#include <pcl/segmentation/extract_clusters.h>
#include <pcl/segmentation/sac_segmentation.h>
#include <rclcpp/rclcpp.hpp>
#include <shape_msgs/msg/solid_primitive.hpp>

using namespace std::chrono_literals;

class PcdToCollisionSceneNode : public rclcpp::Node
{
public:
  PcdToCollisionSceneNode()
  : Node("pcd_to_collision_scene_node")
  {
    pcd_file_ = declare_parameter<std::string>("pcd_file", "/root/ur10_ws/data/latest_obstacle.pcd");
    obstacle_id_ = declare_parameter<std::string>("obstacle_id", "pcd_obstacle_box");
    table_id_ = declare_parameter<std::string>("table_id", "work_table");
    frame_id_ = declare_parameter<std::string>("frame_id", "world");
    timeout_sec_ = declare_parameter<double>("timeout_sec", 20.0);
    padding_ = declare_parameter<double>("padding", 0.03);
    x_min_ = declare_parameter<double>("x_min", 0.30);
    x_max_ = declare_parameter<double>("x_max", 1.20);
    y_min_ = declare_parameter<double>("y_min", -0.60);
    y_max_ = declare_parameter<double>("y_max", 0.60);
    z_min_ = declare_parameter<double>("z_min", 0.68);
    z_max_ = declare_parameter<double>("z_max", 1.25);
    table_center_x_ = declare_parameter<double>("table_center_x", 0.95);
    table_center_y_ = declare_parameter<double>("table_center_y", 0.0);
    table_center_z_ = declare_parameter<double>("table_center_z", 0.675);
    table_size_x_ = declare_parameter<double>("table_size_x", 0.70);
    table_size_y_ = declare_parameter<double>("table_size_y", 1.00);
    table_size_z_ = declare_parameter<double>("table_size_z", 0.05);
  }

  int run()
  {
    if (!waitForPcd()) {
      RCLCPP_ERROR(get_logger(), "PCD file %s did not appear in time.", pcd_file_.c_str());
      return 1;
    }

    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZ>());
    if (pcl::io::loadPCDFile<pcl::PointXYZ>(pcd_file_, *cloud) != 0) {
      RCLCPP_ERROR(get_logger(), "Failed to load PCD file %s", pcd_file_.c_str());
      return 2;
    }
    if (cloud->empty()) {
      RCLCPP_ERROR(get_logger(), "Loaded PCD file is empty.");
      return 3;
    }

    auto filtered = applyWorkspaceRoi(cloud);
    if (filtered->empty()) {
      RCLCPP_ERROR(get_logger(), "No points remained after the workspace ROI filter.");
      return 4;
    }

    filtered = downsample(filtered);
    auto without_plane = removeDominantPlane(filtered);
    auto cluster = largestCluster(without_plane->empty() ? filtered : without_plane);
    if (cluster->empty()) {
      RCLCPP_ERROR(get_logger(), "No obstacle cluster could be extracted from the PCD.");
      return 5;
    }

    moveit_msgs::msg::CollisionObject obstacle = toCollisionObject(cluster);
    moveit_msgs::msg::CollisionObject table = makeTableCollisionObject();
    planning_scene_interface_.removeCollisionObjects({table_id_, obstacle_id_});
    std::this_thread::sleep_for(300ms);
    planning_scene_interface_.applyCollisionObjects({table, obstacle});

    RCLCPP_INFO(
      get_logger(),
      "Injected table %s and collision box %s in frame %s centered at [%.3f, %.3f, %.3f] with size [%.3f, %.3f, %.3f].",
      table_id_.c_str(),
      obstacle_id_.c_str(), frame_id_.c_str(),
      obstacle.primitive_poses[0].position.x,
      obstacle.primitive_poses[0].position.y,
      obstacle.primitive_poses[0].position.z,
      obstacle.primitives[0].dimensions[0],
      obstacle.primitives[0].dimensions[1],
      obstacle.primitives[0].dimensions[2]);
    return 0;
  }

private:
  bool waitForPcd() const
  {
    const auto start = std::chrono::steady_clock::now();
    while (!std::filesystem::exists(pcd_file_)) {
      const auto elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start).count();
      if (elapsed > timeout_sec_) {
        return false;
      }
      std::this_thread::sleep_for(250ms);
    }
    return true;
  }

  pcl::PointCloud<pcl::PointXYZ>::Ptr applyWorkspaceRoi(
    const pcl::PointCloud<pcl::PointXYZ>::Ptr & input) const
  {
    pcl::PointCloud<pcl::PointXYZ>::Ptr x_filtered(new pcl::PointCloud<pcl::PointXYZ>());
    pcl::PassThrough<pcl::PointXYZ> pass;
    pass.setInputCloud(input);
    pass.setFilterFieldName("x");
    pass.setFilterLimits(x_min_, x_max_);
    pass.filter(*x_filtered);

    pcl::PointCloud<pcl::PointXYZ>::Ptr y_filtered(new pcl::PointCloud<pcl::PointXYZ>());
    pass.setInputCloud(x_filtered);
    pass.setFilterFieldName("y");
    pass.setFilterLimits(y_min_, y_max_);
    pass.filter(*y_filtered);

    pcl::PointCloud<pcl::PointXYZ>::Ptr z_filtered(new pcl::PointCloud<pcl::PointXYZ>());
    pass.setInputCloud(y_filtered);
    pass.setFilterFieldName("z");
    pass.setFilterLimits(z_min_, z_max_);
    pass.filter(*z_filtered);
    return z_filtered;
  }

  pcl::PointCloud<pcl::PointXYZ>::Ptr downsample(
    const pcl::PointCloud<pcl::PointXYZ>::Ptr & input) const
  {
    pcl::PointCloud<pcl::PointXYZ>::Ptr output(new pcl::PointCloud<pcl::PointXYZ>());
    pcl::VoxelGrid<pcl::PointXYZ> voxel_grid;
    voxel_grid.setInputCloud(input);
    voxel_grid.setLeafSize(0.01f, 0.01f, 0.01f);
    voxel_grid.filter(*output);
    return output;
  }

  pcl::PointCloud<pcl::PointXYZ>::Ptr removeDominantPlane(
    const pcl::PointCloud<pcl::PointXYZ>::Ptr & input) const
  {
    pcl::SACSegmentation<pcl::PointXYZ> segmentation;
    segmentation.setOptimizeCoefficients(true);
    segmentation.setModelType(pcl::SACMODEL_PLANE);
    segmentation.setMethodType(pcl::SAC_RANSAC);
    segmentation.setDistanceThreshold(0.015);
    segmentation.setInputCloud(input);

    pcl::PointIndices::Ptr inliers(new pcl::PointIndices());
    pcl::ModelCoefficients::Ptr coefficients(new pcl::ModelCoefficients());
    segmentation.segment(*inliers, *coefficients);
    if (inliers->indices.empty()) {
      return input;
    }

    pcl::ExtractIndices<pcl::PointXYZ> extract;
    pcl::PointCloud<pcl::PointXYZ>::Ptr output(new pcl::PointCloud<pcl::PointXYZ>());
    extract.setInputCloud(input);
    extract.setIndices(inliers);
    extract.setNegative(true);
    extract.filter(*output);
    return output;
  }

  pcl::PointCloud<pcl::PointXYZ>::Ptr largestCluster(
    const pcl::PointCloud<pcl::PointXYZ>::Ptr & input) const
  {
    if (input->empty()) {
      return input;
    }

    pcl::search::KdTree<pcl::PointXYZ>::Ptr tree(new pcl::search::KdTree<pcl::PointXYZ>());
    tree->setInputCloud(input);

    std::vector<pcl::PointIndices> cluster_indices;
    pcl::EuclideanClusterExtraction<pcl::PointXYZ> extraction;
    extraction.setClusterTolerance(0.04);
    extraction.setMinClusterSize(40);
    extraction.setMaxClusterSize(250000);
    extraction.setSearchMethod(tree);
    extraction.setInputCloud(input);
    extraction.extract(cluster_indices);

    if (cluster_indices.empty()) {
      return input;
    }

    size_t largest_index = 0;
    for (size_t i = 1; i < cluster_indices.size(); ++i) {
      if (cluster_indices[i].indices.size() > cluster_indices[largest_index].indices.size()) {
        largest_index = i;
      }
    }

    pcl::PointCloud<pcl::PointXYZ>::Ptr cluster(new pcl::PointCloud<pcl::PointXYZ>());
    cluster->reserve(cluster_indices[largest_index].indices.size());
    for (const int index : cluster_indices[largest_index].indices) {
      cluster->push_back((*input)[index]);
    }
    cluster->width = static_cast<uint32_t>(cluster->size());
    cluster->height = 1;
    cluster->is_dense = true;
    return cluster;
  }

  moveit_msgs::msg::CollisionObject toCollisionObject(
    const pcl::PointCloud<pcl::PointXYZ>::Ptr & cloud) const
  {
    double min_x = std::numeric_limits<double>::max();
    double min_y = std::numeric_limits<double>::max();
    double min_z = std::numeric_limits<double>::max();
    double max_x = std::numeric_limits<double>::lowest();
    double max_y = std::numeric_limits<double>::lowest();
    double max_z = std::numeric_limits<double>::lowest();

    for (const auto & point : cloud->points) {
      min_x = std::min(min_x, static_cast<double>(point.x));
      min_y = std::min(min_y, static_cast<double>(point.y));
      min_z = std::min(min_z, static_cast<double>(point.z));
      max_x = std::max(max_x, static_cast<double>(point.x));
      max_y = std::max(max_y, static_cast<double>(point.y));
      max_z = std::max(max_z, static_cast<double>(point.z));
    }

    moveit_msgs::msg::CollisionObject object;
    object.id = obstacle_id_;
    object.header.frame_id = frame_id_;

    shape_msgs::msg::SolidPrimitive primitive;
    primitive.type = shape_msgs::msg::SolidPrimitive::BOX;
    primitive.dimensions.resize(3);
    primitive.dimensions[shape_msgs::msg::SolidPrimitive::BOX_X] =
      std::max(0.02, max_x - min_x + padding_);
    primitive.dimensions[shape_msgs::msg::SolidPrimitive::BOX_Y] =
      std::max(0.02, max_y - min_y + padding_);
    primitive.dimensions[shape_msgs::msg::SolidPrimitive::BOX_Z] =
      std::max(0.02, max_z - min_z + padding_);

    geometry_msgs::msg::Pose pose;
    pose.orientation.w = 1.0;
    pose.position.x = (min_x + max_x) * 0.5;
    pose.position.y = (min_y + max_y) * 0.5;
    pose.position.z = (min_z + max_z) * 0.5;

    object.primitives.push_back(primitive);
    object.primitive_poses.push_back(pose);
    object.operation = moveit_msgs::msg::CollisionObject::ADD;
    return object;
  }

  moveit_msgs::msg::CollisionObject makeTableCollisionObject() const
  {
    moveit_msgs::msg::CollisionObject object;
    object.id = table_id_;
    object.header.frame_id = frame_id_;

    shape_msgs::msg::SolidPrimitive primitive;
    primitive.type = shape_msgs::msg::SolidPrimitive::BOX;
    primitive.dimensions.resize(3);
    primitive.dimensions[shape_msgs::msg::SolidPrimitive::BOX_X] = table_size_x_;
    primitive.dimensions[shape_msgs::msg::SolidPrimitive::BOX_Y] = table_size_y_;
    primitive.dimensions[shape_msgs::msg::SolidPrimitive::BOX_Z] = table_size_z_;

    geometry_msgs::msg::Pose pose;
    pose.orientation.w = 1.0;
    pose.position.x = table_center_x_;
    pose.position.y = table_center_y_;
    pose.position.z = table_center_z_;

    object.primitives.push_back(primitive);
    object.primitive_poses.push_back(pose);
    object.operation = moveit_msgs::msg::CollisionObject::ADD;
    return object;
  }

  moveit::planning_interface::PlanningSceneInterface planning_scene_interface_;
  std::string pcd_file_;
  std::string obstacle_id_;
  std::string table_id_;
  std::string frame_id_;
  double timeout_sec_{20.0};
  double padding_{0.03};
  double x_min_{0.30};
  double x_max_{1.10};
  double y_min_{-0.60};
  double y_max_{0.60};
  double z_min_{0.68};
  double z_max_{1.25};
  double table_center_x_{0.95};
  double table_center_y_{0.0};
  double table_center_z_{0.675};
  double table_size_x_{0.70};
  double table_size_y_{1.00};
  double table_size_z_{0.05};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<PcdToCollisionSceneNode>();
  const int result = node->run();
  rclcpp::shutdown();
  return result;
}

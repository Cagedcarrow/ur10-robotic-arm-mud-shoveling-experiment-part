#include <cmath>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include <geometry_msgs/msg/pose_array.hpp>
#include <rclcpp/rclcpp.hpp>
#include <visualization_msgs/msg/marker_array.hpp>

#include "ur10_trajectory_planner/msg/plan_info.hpp"
#include "ur10_trajectory_planner/msg/target_pose_seq.hpp"
#include "ur10_trajectory_planner/planner_math.hpp"

namespace sb = ur10_trajectory_planner;

class PlannerNode : public rclcpp::Node
{
public:
  PlannerNode()
  : Node("planner_node")
  {
    planner_mode_ = declare_parameter<std::string>("planner_mode", "dp_rrt");
    if (planner_mode_ != "dp_rrt") {
      RCLCPP_WARN(
        get_logger(),
        "planner_mode='%s' is deprecated in planner_node. Fallback to dp_rrt; OMPL should be used via MoveIt/RViz.",
        planner_mode_.c_str());
      planner_mode_ = "dp_rrt";
    }
    planning_waypoint_count_ = declare_parameter<int>("planning.waypoint_count", 8);
    dp_.max_iter = declare_parameter("dp_rrt.max_iter", 2400);
    dp_.goal_radius = declare_parameter("dp_rrt.goal_radius", 0.12);
    dp_.pg_init = declare_parameter("dp_rrt.pg_init", 0.28);
    dp_.pg_min = declare_parameter("dp_rrt.pg_min", 0.03);
    dp_.rho_init = declare_parameter("dp_rrt.rho_init", 0.55);
    dp_.decay_rate = declare_parameter("dp_rrt.decay_rate", 0.5);
    dp_.lambda_min = declare_parameter("dp_rrt.lambda_min", 0.08);
    dp_.lambda_max = declare_parameter("dp_rrt.lambda_max", 0.24);
    dp_.d_safe = declare_parameter("dp_rrt.d_safe", 0.2);

    ws_.x_min = declare_parameter("workspace.x_min", -1.25);
    ws_.x_max = declare_parameter("workspace.x_max", 1.25);
    ws_.y_min = declare_parameter("workspace.y_min", -1.25);
    ws_.y_max = declare_parameter("workspace.y_max", 1.25);
    ws_.z_min = declare_parameter("workspace.z_min", 0.05);
    ws_.z_max = declare_parameter("workspace.z_max", 1.55);

    plan_pub_ = create_publisher<ur10_trajectory_planner::msg::PlanInfo>("/planning/status", 10);
    path_pub_ = create_publisher<geometry_msgs::msg::PoseArray>("/planning/path", 10);
    tree_marker_pub_ =
      create_publisher<visualization_msgs::msg::MarkerArray>("/planning/tree_markers", 10);
    path_marker_pub_ =
      create_publisher<visualization_msgs::msg::MarkerArray>("/planning/markers", 10);

    target_sub_ = create_subscription<ur10_trajectory_planner::msg::TargetPoseSeq>(
      "/trajectory/target_poses", 10,
      std::bind(&PlannerNode::on_target, this, std::placeholders::_1));

    RCLCPP_INFO(get_logger(), "Planner node ready. planner_mode=%s", planner_mode_.c_str());
  }

private:
  std::vector<geometry_msgs::msg::Point> sample_waypoints(
    const std::vector<geometry_msgs::msg::Pose> & poses, int max_count) const
  {
    std::vector<geometry_msgs::msg::Point> wps;
    if (poses.empty()) {
      return wps;
    }
    if (static_cast<int>(poses.size()) <= max_count) {
      wps.reserve(poses.size());
      for (const auto & pose : poses) {
        wps.push_back(pose.position);
      }
      return wps;
    }

    max_count = std::max(2, max_count);
    wps.reserve(static_cast<size_t>(max_count));
    for (int i = 0; i < max_count; ++i) {
      const double t = static_cast<double>(i) / static_cast<double>(max_count - 1);
      const size_t idx = static_cast<size_t>(
        std::round(t * static_cast<double>(poses.size() - 1)));
      wps.push_back(poses[idx].position);
    }
    return wps;
  }

  void publish_markers(
    const std::vector<std::pair<geometry_msgs::msg::Point, geometry_msgs::msg::Point>> & edges,
    const std::vector<geometry_msgs::msg::Point> & path)
  {
    visualization_msgs::msg::MarkerArray tree_arr;
    visualization_msgs::msg::Marker tree;
    tree.header.frame_id = "world";
    tree.header.stamp = now();
    tree.ns = "dp_rrt_tree";
    tree.id = 1;
    tree.type = visualization_msgs::msg::Marker::LINE_LIST;
    tree.action = visualization_msgs::msg::Marker::ADD;
    tree.scale.x = 0.005;
    tree.color.a = 0.7;
    tree.color.r = 0.2;
    tree.color.g = 0.7;
    tree.color.b = 1.0;
    for (const auto & e : edges) {
      tree.points.push_back(e.first);
      tree.points.push_back(e.second);
    }
    tree_arr.markers.push_back(tree);
    tree_marker_pub_->publish(tree_arr);

    visualization_msgs::msg::MarkerArray path_arr;
    visualization_msgs::msg::Marker m;
    m.header = tree.header;
    m.ns = "dp_rrt_path";
    m.id = 2;
    m.type = visualization_msgs::msg::Marker::LINE_STRIP;
    m.action = visualization_msgs::msg::Marker::ADD;
    m.scale.x = 0.012;
    m.color.a = 1.0;
    m.color.r = 1.0;
    m.color.g = 0.4;
    m.color.b = 0.2;
    m.points = path;
    path_arr.markers.push_back(m);
    path_marker_pub_->publish(path_arr);
  }

  void on_target(const ur10_trajectory_planner::msg::TargetPoseSeq::SharedPtr msg)
  {
    if (msg->poses.size() < 2) {
      ur10_trajectory_planner::msg::PlanInfo info;
      info.header.stamp = now();
      info.header.frame_id = "world";
      info.success = false;
      info.algorithm = planner_mode_;
      info.num_nodes = 0;
      info.path_length = 0.0f;
      info.elapsed_sec = 0.0f;
      info.fail_count_final = 0.0f;
      plan_pub_->publish(info);
      return;
    }

    sb::PlannerStats total_stats;
    total_stats.success = true;
    total_stats.algorithm = planner_mode_;
    std::vector<std::pair<geometry_msgs::msg::Point, geometry_msgs::msg::Point>> edges;
    std::vector<geometry_msgs::msg::Point> path;
    const auto waypoints = sample_waypoints(msg->poses, planning_waypoint_count_);

    for (size_t i = 1; i < waypoints.size(); ++i) {
      sb::PlannerStats seg_stats;
      std::vector<geometry_msgs::msg::Point> seg_path;
      seg_path = sb::plan_dp_rrt_path(waypoints[i - 1], waypoints[i], dp_, ws_, &seg_stats, &edges);

      if (seg_path.empty()) {
        total_stats.success = false;
        continue;
      }

      if (!path.empty()) {
        seg_path.erase(seg_path.begin());
      }
      path.insert(path.end(), seg_path.begin(), seg_path.end());

      total_stats.num_nodes += seg_stats.num_nodes;
      total_stats.path_length += seg_stats.path_length;
      total_stats.elapsed_sec += seg_stats.elapsed_sec;
      total_stats.fail_count_final += seg_stats.fail_count_final;
      total_stats.success = total_stats.success && seg_stats.success;
    }

    ur10_trajectory_planner::msg::PlanInfo info;
    info.header.stamp = now();
    info.header.frame_id = "world";
    info.success = total_stats.success;
    info.algorithm = total_stats.algorithm;
    info.num_nodes = total_stats.num_nodes;
    info.path_length = static_cast<float>(total_stats.path_length);
    info.elapsed_sec = static_cast<float>(total_stats.elapsed_sec);
    info.fail_count_final = static_cast<float>(total_stats.fail_count_final);
    plan_pub_->publish(info);

    geometry_msgs::msg::PoseArray arr;
    arr.header = info.header;
    for (const auto & p : path) {
      geometry_msgs::msg::Pose pose;
      pose.position = p;
      pose.orientation.w = 1.0;
      arr.poses.push_back(pose);
    }
    path_pub_->publish(arr);

    if (!edges.empty()) {
      publish_markers(edges, path);
    }
  }

  std::string planner_mode_;
  int planning_waypoint_count_{8};
  sb::DpRrtParams dp_;
  sb::Workspace3D ws_;

  rclcpp::Subscription<ur10_trajectory_planner::msg::TargetPoseSeq>::SharedPtr target_sub_;
  rclcpp::Publisher<ur10_trajectory_planner::msg::PlanInfo>::SharedPtr plan_pub_;
  rclcpp::Publisher<geometry_msgs::msg::PoseArray>::SharedPtr path_pub_;
  rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr tree_marker_pub_;
  rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr path_marker_pub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<PlannerNode>());
  rclcpp::shutdown();
  return 0;
}

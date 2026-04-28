#include <cmath>
#include <memory>
#include <string>
#include <vector>

#include <geometry_msgs/msg/pose_array.hpp>
#include <rclcpp/rclcpp.hpp>

#include "ur10_trajectory_planner/msg/bucket_features.hpp"
#include "ur10_trajectory_planner/msg/target_pose_seq.hpp"
#include "ur10_trajectory_planner/srv/generate_trajectory.hpp"
#include "ur10_trajectory_planner/trajectory_math.hpp"

namespace utp = ur10_trajectory_planner;

class TrajectoryNode : public rclcpp::Node
{
public:
  TrajectoryNode()
  : Node("trajectory_node")
  {
    fit_.entry_span_factor = declare_parameter("entry_span_factor", 1.0);
    fit_.mid_span_factor = declare_parameter("mid_span_factor", 0.35);
    fit_.exit_span_factor = declare_parameter("exit_span_factor", 1.0);
    fit_.entry_depth_ratio = declare_parameter("entry_depth_ratio", 0.20);
    fit_.target_deep_depth_ratio = declare_parameter("target_deep_depth_ratio", 0.15);
    fit_.max_cut_angle_deg = declare_parameter("max_cut_angle_deg", 30.0);
    fit_.top_outer_offset_ratio = declare_parameter("top_outer_offset_ratio", 0.125);
    fit_.start_finish_lift_ratio = declare_parameter("start_finish_lift_ratio", 0.25);
    fit_.exec_first_mode = declare_parameter("exec_first_mode", true);
    fit_.force_base_x_dir = declare_parameter("force_base_x_dir", true);
    fit_.reverse_fit_z_axis = declare_parameter("reverse_fit_z_axis", false);
    fit_.n_pts = declare_parameter("n_pts", 90);

    posture_.attack_deg = declare_parameter("fit.attack_deg", -12.0);
    posture_.assembly_deg = declare_parameter("fit.assembly_deg", 0.0);
    posture_.flip_tool_z = declare_parameter("flip_tool_z", false);

    ws_.r_min = declare_parameter("workspace.r_min", 0.45);
    ws_.r_max = declare_parameter("workspace.r_max", 1.35);
    ws_.z_min = declare_parameter("workspace.z_min", 0.05);
    ws_.z_max = declare_parameter("workspace.z_max", 1.65);

    safe_margin_ = declare_parameter("bucket.safe_margin", 0.03);
    approach_height_ = declare_parameter("bucket.approach_height", 0.20);

    target_pub_ = create_publisher<ur10_trajectory_planner::msg::TargetPoseSeq>(
      "/trajectory/target_poses", 10);
    pose_array_pub_ = create_publisher<geometry_msgs::msg::PoseArray>(
      "/trajectory/target_pose_array", 10);

    srv_ = create_service<ur10_trajectory_planner::srv::GenerateTrajectory>(
      "/trajectory/generate",
      std::bind(&TrajectoryNode::on_generate, this, std::placeholders::_1, std::placeholders::_2));

    feature_sub_ = create_subscription<ur10_trajectory_planner::msg::BucketFeatures>(
      "/bucket/features", 10,
      std::bind(&TrajectoryNode::on_features, this, std::placeholders::_1));

    RCLCPP_INFO(get_logger(), "Trajectory node ready");
  }

private:
  static geometry_msgs::msg::Point make_point(double x, double y, double z)
  {
    geometry_msgs::msg::Point p;
    p.x = x;
    p.y = y;
    p.z = z;
    return p;
  }

  ur10_trajectory_planner::msg::TargetPoseSeq build_bucket_task_seq(
    const ur10_trajectory_planner::msg::BucketFeatures & features,
    const utp::FitParams & fit,
    const utp::PostureParams & posture)
  {
    const double cx = features.top_point.x;
    const double cy = features.top_point.y;
    const double top_z = features.top_point.z;
    const double height = std::max(0.12, static_cast<double>(features.depth));
    const double bottom_z = top_z - height;
    const double radius = std::max(0.05, static_cast<double>(features.top_radius));
    const double safe_margin = std::clamp(safe_margin_, 0.005, radius * 0.6);
    const double work_radius = std::max(0.02, radius - safe_margin);

    std::vector<geometry_msgs::msg::Point> path;
    path.reserve(static_cast<size_t>(fit.n_pts + 20));

    // A: approach bucket top safe point
    path.push_back(make_point(cx + radius + 0.22, cy, top_z + approach_height_));
    path.push_back(make_point(cx + radius + safe_margin, cy, top_z + 0.10));

    // B: entry and descend
    path.push_back(make_point(cx + work_radius, cy, top_z + 0.02));
    path.push_back(make_point(cx + work_radius, cy, bottom_z + 0.45 * height));

    // C: inside bucket working arc
    const int arc_pts = std::max(24, fit.n_pts / 2);
    for (int i = 0; i < arc_pts; ++i) {
      const double t = static_cast<double>(i) / static_cast<double>(arc_pts - 1);
      const double th = -0.15 * M_PI + t * 1.3 * M_PI;
      const double r = work_radius * (0.92 + 0.08 * std::sin(2.0 * th));
      const double z = bottom_z + 0.22 * height + 0.08 * height * std::sin(1.5 * th);
      path.push_back(make_point(cx + r * std::cos(th), cy + r * std::sin(th), z));
    }

    // D: lift and retreat
    path.push_back(make_point(cx - work_radius, cy, top_z + 0.06));
    path.push_back(make_point(cx - radius - 0.22, cy, top_z + approach_height_));

    std::vector<geometry_msgs::msg::Point> filtered;
    filtered.reserve(path.size());
    for (const auto & p : path) {
      if (utp::point_within_workspace(p, ws_)) {
        filtered.push_back(p);
      }
    }
    if (filtered.size() < 8) {
      filtered = path;
    }

    std::vector<double> slopes;
    slopes.reserve(filtered.size());
    for (size_t i = 0; i < filtered.size(); ++i) {
      if (i == 0) {
        const double dx = filtered[i + 1].x - filtered[i].x;
        const double dz = filtered[i + 1].z - filtered[i].z;
        slopes.push_back(dz / std::max(1e-6, dx));
      } else if (i + 1 >= filtered.size()) {
        const double dx = filtered[i].x - filtered[i - 1].x;
        const double dz = filtered[i].z - filtered[i - 1].z;
        slopes.push_back(dz / std::max(1e-6, dx));
      } else {
        const double dx = filtered[i + 1].x - filtered[i - 1].x;
        const double dz = filtered[i + 1].z - filtered[i - 1].z;
        slopes.push_back(dz / std::max(1e-6, dx));
      }
    }

    const auto poses = utp::build_pose_sequence(filtered, slopes, posture, fit.reverse_fit_z_axis);

    ur10_trajectory_planner::msg::TargetPoseSeq seq;
    seq.header.stamp = now();
    seq.header.frame_id = "world";
    seq.poses = poses;
    seq.slope_samples.reserve(slopes.size());
    for (double s : slopes) {
      seq.slope_samples.push_back(static_cast<float>(s));
    }
    seq.flip_tool_z = posture.flip_tool_z;
    seq.attack_deg = static_cast<float>(posture.attack_deg);
    seq.assembly_deg = static_cast<float>(posture.assembly_deg);
    return seq;
  }

  void publish_pose_array(const ur10_trajectory_planner::msg::TargetPoseSeq & seq)
  {
    geometry_msgs::msg::PoseArray arr;
    arr.header = seq.header;
    arr.poses = seq.poses;
    pose_array_pub_->publish(arr);
  }

  void on_features(const ur10_trajectory_planner::msg::BucketFeatures::SharedPtr msg)
  {
    auto seq = build_bucket_task_seq(*msg, fit_, posture_);
    target_pub_->publish(seq);
    publish_pose_array(seq);
  }

  void on_generate(
    const std::shared_ptr<ur10_trajectory_planner::srv::GenerateTrajectory::Request> req,
    std::shared_ptr<ur10_trajectory_planner::srv::GenerateTrajectory::Response> res)
  {
    utp::FitParams fit = fit_;
    fit.entry_span_factor = req->entry_span_factor;
    fit.mid_span_factor = req->mid_span_factor;
    fit.exit_span_factor = req->exit_span_factor;
    fit.entry_depth_ratio = req->entry_depth_ratio;
    fit.target_deep_depth_ratio = req->target_deep_depth_ratio;
    fit.max_cut_angle_deg = req->max_cut_angle_deg;
    fit.top_outer_offset_ratio = req->top_outer_offset_ratio;
    fit.start_finish_lift_ratio = req->start_finish_lift_ratio;
    fit.exec_first_mode = req->exec_first_mode;
    fit.force_base_x_dir = req->force_base_x_dir;
    fit.reverse_fit_z_axis = req->reverse_fit_z_axis;
    fit.n_pts = req->n_pts;

    utp::PostureParams posture = posture_;
    posture.attack_deg = req->attack_deg;
    posture.assembly_deg = req->assembly_deg;
    posture.flip_tool_z = req->flip_tool_z;

    auto seq = build_bucket_task_seq(req->features, fit, posture);
    target_pub_->publish(seq);
    publish_pose_array(seq);

    res->success = !seq.poses.empty();
    res->message = res->success ? "ok" : "trajectory empty";
    res->target_pose_seq = seq;
  }

  utp::FitParams fit_;
  utp::PostureParams posture_;
  utp::WorkspaceLimits ws_;
  double safe_margin_{0.03};
  double approach_height_{0.20};

  rclcpp::Publisher<ur10_trajectory_planner::msg::TargetPoseSeq>::SharedPtr target_pub_;
  rclcpp::Publisher<geometry_msgs::msg::PoseArray>::SharedPtr pose_array_pub_;
  rclcpp::Subscription<ur10_trajectory_planner::msg::BucketFeatures>::SharedPtr feature_sub_;
  rclcpp::Service<ur10_trajectory_planner::srv::GenerateTrajectory>::SharedPtr srv_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TrajectoryNode>());
  rclcpp::shutdown();
  return 0;
}

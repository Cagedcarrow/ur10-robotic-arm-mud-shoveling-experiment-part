#pragma once

#include <array>
#include <vector>

#include <geometry_msgs/msg/point.hpp>
#include <geometry_msgs/msg/pose.hpp>
#include <geometry_msgs/msg/vector3.hpp>

namespace ur10_trajectory_planner
{

struct FitParams
{
  double entry_span_factor{1.0};
  double mid_span_factor{0.35};
  double exit_span_factor{1.0};
  double entry_depth_ratio{0.20};
  double target_deep_depth_ratio{0.15};
  double max_cut_angle_deg{30.0};
  double top_outer_offset_ratio{0.125};
  double start_finish_lift_ratio{0.25};
  bool exec_first_mode{true};
  bool force_base_x_dir{true};
  bool reverse_fit_z_axis{false};
  int n_pts{90};
  double local_y_offset{0.0};
};

struct PostureParams
{
  double attack_deg{-12.0};
  double assembly_deg{0.0};
  bool flip_tool_z{false};
};

struct WorkspaceLimits
{
  double r_min{0.45};
  double r_max{1.28};
  double z_min{0.05};
  double z_max{1.55};
};

struct TrajectoryResult
{
  std::vector<geometry_msgs::msg::Point> points;
  std::vector<double> slopes;
  std::array<geometry_msgs::msg::Point, 4> key_points;
};

TrajectoryResult fit_three_segment_trajectory(
  const geometry_msgs::msg::Point & top_point,
  double top_radius,
  double max_radius,
  double depth,
  const geometry_msgs::msg::Vector3 & dig_direction,
  const FitParams & params);

std::vector<geometry_msgs::msg::Pose> build_pose_sequence(
  const std::vector<geometry_msgs::msg::Point> & path,
  const std::vector<double> & slopes,
  const PostureParams & posture,
  bool reverse_fit_z_axis);

bool point_within_workspace(const geometry_msgs::msg::Point & p, const WorkspaceLimits & limits);

}  // namespace ur10_trajectory_planner

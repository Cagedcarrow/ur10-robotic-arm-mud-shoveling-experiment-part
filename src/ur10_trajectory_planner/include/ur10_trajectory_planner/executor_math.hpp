#pragma once

#include <string>
#include <vector>

#include <geometry_msgs/msg/pose.hpp>
#include <trajectory_msgs/msg/joint_trajectory.hpp>

namespace ur10_trajectory_planner
{

trajectory_msgs::msg::JointTrajectory poses_to_joint_trajectory(
  const std::vector<geometry_msgs::msg::Pose> & poses,
  double max_joint_step_rad,
  double dt,
  uint32_t * fallback_count,
  uint32_t * hold_count,
  std::string * failure_reason);

}  // namespace ur10_trajectory_planner

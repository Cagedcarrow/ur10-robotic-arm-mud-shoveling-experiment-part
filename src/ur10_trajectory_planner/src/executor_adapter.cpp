#include "ur10_trajectory_planner/executor_math.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace ur10_trajectory_planner
{
namespace
{

double clamp_delta(double target, double prev, double max_step, bool * clamped)
{
  const double d = target - prev;
  if (std::abs(d) <= max_step) {
    return target;
  }
  *clamped = true;
  return prev + std::copysign(max_step, d);
}

}  // namespace

trajectory_msgs::msg::JointTrajectory poses_to_joint_trajectory(
  const std::vector<geometry_msgs::msg::Pose> & poses,
  double max_joint_step_rad,
  double dt,
  uint32_t * fallback_count,
  uint32_t * hold_count,
  std::string * failure_reason)
{
  trajectory_msgs::msg::JointTrajectory traj;
  traj.joint_names = {
    "ur10_shoulder_pan", "ur10_shoulder_lift", "ur10_elbow",
    "ur10_wrist_1_joint", "ur10_wrist_2_joint", "ur10_wrist_3_joint"};

  std::array<double, 6> q_prev{0.0, -1.2, 1.8, -1.6, -1.57, 0.0};

  if (fallback_count) {
    *fallback_count = 0;
  }
  if (hold_count) {
    *hold_count = 0;
  }

  for (size_t i = 0; i < poses.size(); ++i) {
    const auto & p = poses[i].position;
    std::array<double, 6> q_target{
      std::atan2(p.y, p.x),
      std::clamp(-0.8 - p.z * 0.9, -2.2, 0.5),
      std::clamp(1.0 + std::hypot(p.x, p.y) * 0.8, -2.2, 2.2),
      std::clamp(-1.2 - p.z * 0.6, -2.5, 0.5),
      std::clamp(-1.57 + 0.3 * p.y, -2.2, 2.2),
      std::clamp(0.25 * p.x, -2.2, 2.2)};

    trajectory_msgs::msg::JointTrajectoryPoint pt;
    pt.positions.resize(6, 0.0);

    bool clamped_any = false;
    for (size_t j = 0; j < 6; ++j) {
      bool clamped = false;
      const double q = clamp_delta(q_target[j], q_prev[j], max_joint_step_rad, &clamped);
      pt.positions[j] = q;
      q_prev[j] = q;
      clamped_any = clamped_any || clamped;
    }

    if (clamped_any && fallback_count) {
      *fallback_count += 1;
    }

    pt.time_from_start.sec = static_cast<int32_t>(std::floor((i + 1) * dt));
    pt.time_from_start.nanosec = static_cast<uint32_t>((((i + 1) * dt) - pt.time_from_start.sec) * 1e9);
    traj.points.push_back(pt);
  }

  if (traj.points.empty()) {
    if (failure_reason) {
      *failure_reason = "empty trajectory";
    }
  }

  return traj;
}

}  // namespace ur10_trajectory_planner

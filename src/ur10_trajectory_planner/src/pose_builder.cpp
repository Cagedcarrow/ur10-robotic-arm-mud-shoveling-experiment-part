#include "ur10_trajectory_planner/trajectory_math.hpp"

#include <array>
#include <cmath>

#include <geometry_msgs/msg/quaternion.hpp>

namespace ur10_trajectory_planner
{
namespace
{

std::array<double, 3> normalize(const std::array<double, 3> & v)
{
  const double n = std::sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
  if (n < 1e-9) {
    return {1.0, 0.0, 0.0};
  }
  return {v[0] / n, v[1] / n, v[2] / n};
}

std::array<double, 3> cross(const std::array<double, 3> & a, const std::array<double, 3> & b)
{
  return {
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0]
  };
}

geometry_msgs::msg::Quaternion quat_from_basis(
  const std::array<double, 3> & x,
  const std::array<double, 3> & y,
  const std::array<double, 3> & z)
{
  const double r00 = x[0];
  const double r01 = y[0];
  const double r02 = z[0];
  const double r10 = x[1];
  const double r11 = y[1];
  const double r12 = z[1];
  const double r20 = x[2];
  const double r21 = y[2];
  const double r22 = z[2];

  geometry_msgs::msg::Quaternion q;
  const double trace = r00 + r11 + r22;
  if (trace > 0.0) {
    const double s = std::sqrt(trace + 1.0) * 2.0;
    q.w = 0.25 * s;
    q.x = (r21 - r12) / s;
    q.y = (r02 - r20) / s;
    q.z = (r10 - r01) / s;
  } else if ((r00 > r11) && (r00 > r22)) {
    const double s = std::sqrt(1.0 + r00 - r11 - r22) * 2.0;
    q.w = (r21 - r12) / s;
    q.x = 0.25 * s;
    q.y = (r01 + r10) / s;
    q.z = (r02 + r20) / s;
  } else if (r11 > r22) {
    const double s = std::sqrt(1.0 + r11 - r00 - r22) * 2.0;
    q.w = (r02 - r20) / s;
    q.x = (r01 + r10) / s;
    q.y = 0.25 * s;
    q.z = (r12 + r21) / s;
  } else {
    const double s = std::sqrt(1.0 + r22 - r00 - r11) * 2.0;
    q.w = (r10 - r01) / s;
    q.x = (r02 + r20) / s;
    q.y = (r12 + r21) / s;
    q.z = 0.25 * s;
  }
  return q;
}

}  // namespace

std::vector<geometry_msgs::msg::Pose> build_pose_sequence(
  const std::vector<geometry_msgs::msg::Point> & path,
  const std::vector<double> &, const PostureParams & posture,
  bool reverse_fit_z_axis)
{
  std::vector<geometry_msgs::msg::Pose> poses;
  if (path.size() < 2) {
    return poses;
  }

  poses.reserve(path.size());
  std::array<double, 3> prev_x{1.0, 0.0, 0.0};
  std::array<double, 3> prev_z{0.0, 0.0, 1.0};
  const std::array<double, 3> x_ref{0.0, 1.0, 0.0};
  const double theta = (posture.attack_deg + posture.assembly_deg) * M_PI / 180.0;

  for (size_t i = 0; i < path.size(); ++i) {
    const geometry_msgs::msg::Point & p_prev = path[(i == 0) ? 0 : i - 1];
    const geometry_msgs::msg::Point & p_next = path[(i + 1 >= path.size()) ? path.size() - 1 : i + 1];

    std::array<double, 3> y_axis = normalize({
      p_next.x - p_prev.x,
      p_next.y - p_prev.y,
      p_next.z - p_prev.z
    });

    std::array<double, 3> z_axis = normalize(cross(x_ref, y_axis));
    if (reverse_fit_z_axis || posture.flip_tool_z) {
      z_axis = {-z_axis[0], -z_axis[1], -z_axis[2]};
    }
    std::array<double, 3> x_axis = normalize(cross(y_axis, z_axis));

    const double dot_x = x_axis[0] * prev_x[0] + x_axis[1] * prev_x[1] + x_axis[2] * prev_x[2];
    const double dot_z = z_axis[0] * prev_z[0] + z_axis[1] * prev_z[1] + z_axis[2] * prev_z[2];
    if (dot_x < 0.0 || dot_z < 0.0) {
      x_axis = {-x_axis[0], -x_axis[1], -x_axis[2]};
      z_axis = {-z_axis[0], -z_axis[1], -z_axis[2]};
    }

    const double c = std::cos(theta);
    const double s = std::sin(theta);
    const std::array<double, 3> x_rot{
      c * x_axis[0] + s * z_axis[0],
      c * x_axis[1] + s * z_axis[1],
      c * x_axis[2] + s * z_axis[2]};
    const std::array<double, 3> z_rot{
      -s * x_axis[0] + c * z_axis[0],
      -s * x_axis[1] + c * z_axis[1],
      -s * x_axis[2] + c * z_axis[2]};

    geometry_msgs::msg::Pose pose;
    pose.position = path[i];
    pose.orientation = quat_from_basis(x_rot, y_axis, z_rot);
    poses.push_back(pose);

    prev_x = x_rot;
    prev_z = z_rot;
  }

  return poses;
}

}  // namespace ur10_trajectory_planner

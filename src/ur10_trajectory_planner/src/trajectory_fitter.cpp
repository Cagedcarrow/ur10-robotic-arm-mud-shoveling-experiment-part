#include "ur10_trajectory_planner/trajectory_math.hpp"

#include <algorithm>
#include <cmath>

namespace ur10_trajectory_planner
{
namespace
{

geometry_msgs::msg::Point make_point(double x, double y, double z)
{
  geometry_msgs::msg::Point p;
  p.x = x;
  p.y = y;
  p.z = z;
  return p;
}

void clamp_slopes(std::vector<double> & z, double x0, double dx, double max_slope, int deep_idx, double z0,
  double z3, double z_deep)
{
  if (z.size() < 3) {
    return;
  }
  for (int pass = 0; pass < 4; ++pass) {
    for (size_t i = 1; i < z.size(); ++i) {
      const double dz = z[i] - z[i - 1];
      const double clamped = std::clamp(dz, -max_slope * dx, max_slope * dx);
      z[i] = z[i - 1] + clamped;
    }
    for (size_t i = z.size() - 1; i > 0; --i) {
      const double dz = z[i - 1] - z[i];
      const double clamped = std::clamp(dz, -max_slope * dx, max_slope * dx);
      z[i - 1] = z[i] + clamped;
    }
    z.front() = z0;
    z.back() = z3;
    z[std::clamp(deep_idx, 0, static_cast<int>(z.size() - 1))] = z_deep;
    (void)x0;
  }
}

}  // namespace

TrajectoryResult fit_three_segment_trajectory(
  const geometry_msgs::msg::Point & top_point,
  double top_radius,
  double max_radius,
  double depth,
  const geometry_msgs::msg::Vector3 & dig_direction,
  const FitParams & params)
{
  TrajectoryResult out;
  const int n = std::max(20, params.n_pts);
  out.points.reserve(static_cast<size_t>(n));
  out.slopes.reserve(static_cast<size_t>(n));

  const double dig_norm = std::hypot(dig_direction.x, dig_direction.y);
  const double dir_x = (params.force_base_x_dir || dig_norm < 1e-6) ? 1.0 : dig_direction.x / dig_norm;
  const double dir_y = (params.force_base_x_dir || dig_norm < 1e-6) ? 0.0 : dig_direction.y / dig_norm;
  const double z_sign = params.reverse_fit_z_axis ? -1.0 : 1.0;

  const double outer_offset = params.top_outer_offset_ratio * std::max(0.05, top_radius);
  const double start_finish_radius = std::max(0.05, top_radius + outer_offset);
  const double x0 = -params.entry_span_factor * start_finish_radius;
  const double x1 = -params.mid_span_factor * std::max(0.05, max_radius);
  const double x2 = 0.0;
  const double x3 = params.exit_span_factor * start_finish_radius;

  const double z_lift = top_point.z + z_sign * params.start_finish_lift_ratio * depth;
  const double z0 = z_lift;
  const double z1 = top_point.z - z_sign * params.entry_depth_ratio * depth;
  const double z2 = top_point.z - z_sign * params.target_deep_depth_ratio * depth;
  const double z3 = z_lift;

  out.key_points[0] = make_point(top_point.x + dir_x * x0, top_point.y + dir_y * x0 + params.local_y_offset, z0);
  out.key_points[1] = make_point(top_point.x + dir_x * x1, top_point.y + dir_y * x1 + params.local_y_offset, z1);
  out.key_points[2] = make_point(top_point.x + dir_x * x2, top_point.y + dir_y * x2 + params.local_y_offset, z2);
  out.key_points[3] = make_point(top_point.x + dir_x * x3, top_point.y + dir_y * x3 + params.local_y_offset, z3);

  const double x_min = x0;
  const double x_max = x3;
  const double dx = (x_max - x_min) / static_cast<double>(n - 1);
  std::vector<double> z(n, z0);
  const double max_slope = std::tan(std::abs(params.max_cut_angle_deg) * M_PI / 180.0);

  const int deep_idx = std::clamp(static_cast<int>(std::round((x2 - x_min) / dx)), 0, n - 1);
  const int knot_idx = std::clamp(static_cast<int>(std::round((x1 - x_min) / dx)), 0, n - 1);

  for (int i = 0; i < n; ++i) {
    const double x = x_min + static_cast<double>(i) * dx;
    if (i <= knot_idx) {
      const double t = (x - x0) / std::max(1e-6, (x1 - x0));
      z[i] = z0 + (z1 - z0) * t + params.mid_span_factor * (z1 - z0) * t * (1.0 - t);
    } else if (i <= deep_idx) {
      const double t = (x - x1) / std::max(1e-6, (x2 - x1));
      if (params.exec_first_mode) {
        z[i] = z1 + (z2 - z1) * t;
      } else {
        z[i] = z1 + (z2 - z1) * (t * t);
      }
    } else {
      const double t = (x - x2) / std::max(1e-6, (x3 - x2));
      z[i] = z2 + (z3 - z2) * t + 0.3 * (z3 - z2) * t * (1.0 - t);
    }
  }

  clamp_slopes(z, x_min, dx, max_slope, deep_idx, z0, z3, z2);

  for (int i = 0; i < n; ++i) {
    const double x = x_min + static_cast<double>(i) * dx;
    geometry_msgs::msg::Point p;
    p.x = top_point.x + dir_x * x;
    p.y = top_point.y + dir_y * x + params.local_y_offset;
    p.z = z[i];
    out.points.push_back(p);

    double slope = 0.0;
    if (i == 0) {
      slope = (z[i + 1] - z[i]) / dx;
    } else if (i == n - 1) {
      slope = (z[i] - z[i - 1]) / dx;
    } else {
      slope = (z[i + 1] - z[i - 1]) / (2.0 * dx);
    }
    out.slopes.push_back(slope);
  }

  return out;
}

bool point_within_workspace(const geometry_msgs::msg::Point & p, const WorkspaceLimits & limits)
{
  const double r = std::hypot(p.x, p.y);
  if (r < limits.r_min || r > limits.r_max) {
    return false;
  }
  if (p.z < limits.z_min || p.z > limits.z_max) {
    return false;
  }
  return true;
}

}  // namespace ur10_trajectory_planner

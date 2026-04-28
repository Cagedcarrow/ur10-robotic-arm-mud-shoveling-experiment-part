#pragma once

#include <string>
#include <vector>

#include <geometry_msgs/msg/point.hpp>

namespace ur10_trajectory_planner
{

struct PlannerStats
{
  bool success{false};
  std::string algorithm{"dp_rrt"};
  uint32_t num_nodes{0};
  double path_length{0.0};
  double elapsed_sec{0.0};
  double fail_count_final{0.0};
};

struct DpRrtParams
{
  int max_iter{2200};
  double goal_radius{0.12};
  double pg_init{0.28};
  double pg_min{0.03};
  double rho_init{0.55};
  double decay_rate{0.5};
  double lambda_min{0.06};
  double lambda_max{0.2};
  double d_safe{0.18};
};

struct Workspace3D
{
  double x_min{-1.25};
  double x_max{1.25};
  double y_min{-1.25};
  double y_max{1.25};
  double z_min{0.05};
  double z_max{1.55};
};

std::vector<geometry_msgs::msg::Point> plan_dp_rrt_path(
  const geometry_msgs::msg::Point & start,
  const geometry_msgs::msg::Point & goal,
  const DpRrtParams & params,
  const Workspace3D & ws,
  PlannerStats * stats,
  std::vector<std::pair<geometry_msgs::msg::Point, geometry_msgs::msg::Point>> * tree_edges);

std::vector<geometry_msgs::msg::Point> plan_linear_path(
  const geometry_msgs::msg::Point & start,
  const geometry_msgs::msg::Point & goal,
  int n,
  PlannerStats * stats);

}  // namespace ur10_trajectory_planner

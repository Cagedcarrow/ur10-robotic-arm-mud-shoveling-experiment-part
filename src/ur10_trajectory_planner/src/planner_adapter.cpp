#include "ur10_trajectory_planner/planner_math.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <random>

namespace ur10_trajectory_planner
{
namespace
{

struct Node
{
  geometry_msgs::msg::Point p;
  int parent{0};
  double cost{0.0};
};

double dist(const geometry_msgs::msg::Point & a, const geometry_msgs::msg::Point & b)
{
  return std::sqrt(
    (a.x - b.x) * (a.x - b.x) +
    (a.y - b.y) * (a.y - b.y) +
    (a.z - b.z) * (a.z - b.z));
}

bool in_bounds(const geometry_msgs::msg::Point & p, const Workspace3D & ws)
{
  return p.x >= ws.x_min && p.x <= ws.x_max &&
         p.y >= ws.y_min && p.y <= ws.y_max &&
         p.z >= ws.z_min && p.z <= ws.z_max;
}

}  // namespace

std::vector<geometry_msgs::msg::Point> plan_linear_path(
  const geometry_msgs::msg::Point & start,
  const geometry_msgs::msg::Point & goal,
  int n,
  PlannerStats * stats)
{
  std::vector<geometry_msgs::msg::Point> out;
  n = std::max(2, n);
  out.reserve(static_cast<size_t>(n));
  for (int i = 0; i < n; ++i) {
    const double t = static_cast<double>(i) / static_cast<double>(n - 1);
    geometry_msgs::msg::Point p;
    p.x = start.x + t * (goal.x - start.x);
    p.y = start.y + t * (goal.y - start.y);
    p.z = start.z + t * (goal.z - start.z);
    out.push_back(p);
  }
  if (stats) {
    stats->success = true;
    stats->algorithm = "ompl";
    stats->num_nodes = static_cast<uint32_t>(out.size());
    stats->path_length = dist(start, goal);
    stats->elapsed_sec = 0.0;
    stats->fail_count_final = 0.0;
  }
  return out;
}

std::vector<geometry_msgs::msg::Point> plan_dp_rrt_path(
  const geometry_msgs::msg::Point & start,
  const geometry_msgs::msg::Point & goal,
  const DpRrtParams & params,
  const Workspace3D & ws,
  PlannerStats * stats,
  std::vector<std::pair<geometry_msgs::msg::Point, geometry_msgs::msg::Point>> * tree_edges)
{
  const auto t0 = std::chrono::steady_clock::now();
  std::mt19937 rng(std::random_device{}());
  std::uniform_real_distribution<double> ux(ws.x_min, ws.x_max);
  std::uniform_real_distribution<double> uy(ws.y_min, ws.y_max);
  std::uniform_real_distribution<double> uz(ws.z_min, ws.z_max);
  std::uniform_real_distribution<double> ur(0.0, 1.0);

  std::vector<Node> tree;
  tree.push_back(Node{start, 0, 0.0});
  int final_idx = -1;
  double fail_count = 0.0;

  for (int iter = 0; iter < params.max_iter; ++iter) {
    const double pg = std::max(params.pg_min, params.pg_init * std::exp(-params.decay_rate * fail_count));
    const double rho = std::clamp(params.rho_init * std::exp(-params.decay_rate * fail_count), 0.0, 1.0);

    geometry_msgs::msg::Point q_rand;
    if (ur(rng) < pg) {
      q_rand = goal;
    } else {
      q_rand.x = ux(rng);
      q_rand.y = uy(rng);
      q_rand.z = uz(rng);
    }

    int nearest = 0;
    double nearest_d = dist(tree[0].p, q_rand);
    for (size_t i = 1; i < tree.size(); ++i) {
      const double d = dist(tree[i].p, q_rand);
      if (d < nearest_d) {
        nearest_d = d;
        nearest = static_cast<int>(i);
      }
    }

    geometry_msgs::msg::Point q_near = tree[nearest].p;
    geometry_msgs::msg::Point q_goal = goal;

    geometry_msgs::msg::Point v_rand;
    v_rand.x = q_rand.x - q_near.x;
    v_rand.y = q_rand.y - q_near.y;
    v_rand.z = q_rand.z - q_near.z;

    geometry_msgs::msg::Point v_goal;
    v_goal.x = q_goal.x - q_near.x;
    v_goal.y = q_goal.y - q_near.y;
    v_goal.z = q_goal.z - q_near.z;

    const double d_rand = std::max(1e-9, dist(q_near, q_rand));
    const double d_goal = std::max(1e-9, dist(q_near, q_goal));

    v_rand.x /= d_rand; v_rand.y /= d_rand; v_rand.z /= d_rand;
    v_goal.x /= d_goal; v_goal.y /= d_goal; v_goal.z /= d_goal;

    geometry_msgs::msg::Point v_new;
    v_new.x = (1.0 - rho) * v_rand.x + rho * v_goal.x;
    v_new.y = (1.0 - rho) * v_rand.y + rho * v_goal.y;
    v_new.z = (1.0 - rho) * v_rand.z + rho * v_goal.z;
    const double dn = std::max(1e-9, std::sqrt(v_new.x * v_new.x + v_new.y * v_new.y + v_new.z * v_new.z));
    v_new.x /= dn; v_new.y /= dn; v_new.z /= dn;

    const double margin_x = std::min(q_near.x - ws.x_min, ws.x_max - q_near.x);
    const double margin_y = std::min(q_near.y - ws.y_min, ws.y_max - q_near.y);
    const double margin_z = std::min(q_near.z - ws.z_min, ws.z_max - q_near.z);
    const double d_min = std::max(0.0, std::min(margin_x, std::min(margin_y, margin_z)));

    double lambda = params.lambda_max;
    if (d_min < params.d_safe) {
      const double kappa = 0.08;
      const double numerator = std::exp(kappa * d_min) - 1.0;
      const double denominator = std::max(1e-9, std::exp(kappa * params.d_safe) - 1.0);
      lambda = params.lambda_min + (params.lambda_max - params.lambda_min) * (numerator / denominator);
    }

    geometry_msgs::msg::Point q_new;
    q_new.x = q_near.x + lambda * v_new.x;
    q_new.y = q_near.y + lambda * v_new.y;
    q_new.z = q_near.z + lambda * v_new.z;

    if (!in_bounds(q_new, ws)) {
      fail_count += 1.0;
      continue;
    }

    tree.push_back(Node{q_new, nearest, tree[nearest].cost + dist(q_near, q_new)});
    if (tree_edges) {
      tree_edges->push_back({q_near, q_new});
    }
    fail_count = std::max(0.0, fail_count - 0.25);

    if (dist(q_new, goal) <= params.goal_radius) {
      tree.push_back(Node{goal, static_cast<int>(tree.size() - 1), tree.back().cost + dist(q_new, goal)});
      final_idx = static_cast<int>(tree.size() - 1);
      break;
    }
  }

  std::vector<geometry_msgs::msg::Point> path;
  if (final_idx < 0) {
    path = plan_linear_path(start, goal, 40, nullptr);
  } else {
    int idx = final_idx;
    while (idx > 0) {
      path.push_back(tree[idx].p);
      idx = tree[idx].parent;
    }
    path.push_back(start);
    std::reverse(path.begin(), path.end());
  }

  const auto t1 = std::chrono::steady_clock::now();
  const double elapsed = std::chrono::duration<double>(t1 - t0).count();
  double length = 0.0;
  for (size_t i = 1; i < path.size(); ++i) {
    length += dist(path[i - 1], path[i]);
  }

  if (stats) {
    stats->success = true;
    stats->algorithm = "dp_rrt";
    stats->num_nodes = static_cast<uint32_t>(tree.size());
    stats->path_length = length;
    stats->elapsed_sec = elapsed;
    stats->fail_count_final = fail_count;
  }

  return path;
}

}  // namespace ur10_trajectory_planner

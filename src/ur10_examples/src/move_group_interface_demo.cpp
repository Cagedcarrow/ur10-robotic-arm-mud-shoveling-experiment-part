#include <chrono>
#include <future>
#include <memory>
#include <set>
#include <string>
#include <thread>
#include <vector>

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit_msgs/action/execute_trajectory.hpp>
#include <moveit_msgs/msg/planning_scene_components.hpp>
#include <moveit_msgs/srv/get_motion_plan.hpp>
#include <moveit_msgs/srv/get_planning_scene.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <rclcpp/parameter_client.hpp>
#include <rclcpp/rclcpp.hpp>

using namespace std::chrono_literals;

namespace
{
bool syncMoveGroupParameters(const rclcpp::Node::SharedPtr & node, double timeout_sec)
{
  auto client =
    std::make_shared<rclcpp::SyncParametersClient>(node, "/move_group");
  if (!client->wait_for_service(std::chrono::duration<double>(timeout_sec))) {
    RCLCPP_WARN(
      node->get_logger(), "Timed out waiting for /move_group parameter services.");
    return false;
  }

  const std::vector<std::string> prefixes = {
    "robot_description",
    "robot_description_semantic",
    "robot_description_kinematics",
    "robot_description_planning",
  };

  std::set<std::string> parameter_names{
    "robot_description",
    "robot_description_semantic",
  };

  auto list_result = client->list_parameters(prefixes, 10);
  parameter_names.insert(list_result.names.begin(), list_result.names.end());

  std::vector<std::string> names(parameter_names.begin(), parameter_names.end());
  if (names.empty()) {
    RCLCPP_WARN(node->get_logger(), "No parameters were discovered on /move_group.");
    return false;
  }

  auto remote_parameters = client->get_parameters(names);
  std::size_t synced_count = 0;
  for (const auto & parameter : remote_parameters) {
    if (parameter.get_type() == rclcpp::ParameterType::PARAMETER_NOT_SET) {
      continue;
    }
    if (!node->has_parameter(parameter.get_name())) {
      node->declare_parameter(parameter.get_name(), parameter.get_parameter_value());
    } else {
      node->set_parameter(parameter);
    }
    ++synced_count;
  }

  RCLCPP_INFO(
    node->get_logger(), "Synchronized %zu MoveIt parameters from /move_group.", synced_count);
  return synced_count > 0;
}

bool waitForSceneObject(
  const rclcpp::Node::SharedPtr & node, const std::string & obstacle_id, double timeout_sec)
{
  if (obstacle_id.empty()) {
    return true;
  }

  auto client = node->create_client<moveit_msgs::srv::GetPlanningScene>("/get_planning_scene");
  if (!client->wait_for_service(std::chrono::duration<double>(timeout_sec))) {
    RCLCPP_WARN(
      node->get_logger(), "Planning scene service was not ready before the timeout.");
    return false;
  }

  const auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(timeout_sec);
  while (std::chrono::steady_clock::now() < deadline && rclcpp::ok()) {
    auto request = std::make_shared<moveit_msgs::srv::GetPlanningScene::Request>();
    request->components.components =
      moveit_msgs::msg::PlanningSceneComponents::WORLD_OBJECT_NAMES;
    auto future = client->async_send_request(request);
    if (future.wait_for(1s) == std::future_status::ready) {
      const auto response = future.get();
      for (const auto & object : response->scene.world.collision_objects) {
        if (object.id == obstacle_id) {
          RCLCPP_INFO(node->get_logger(), "Observed planning-scene object %s.", obstacle_id.c_str());
          return true;
        }
      }
    }
    std::this_thread::sleep_for(500ms);
  }

  RCLCPP_WARN(node->get_logger(), "Obstacle %s was not visible in time.", obstacle_id.c_str());
  return false;
}

bool planAndOptionallyExecute(
  moveit::planning_interface::MoveGroupInterface & move_group,
  const rclcpp::Node::SharedPtr & node, const std::string & label, bool execute)
{
  auto motion_plan_client =
    node->create_client<moveit_msgs::srv::GetMotionPlan>("/plan_kinematic_path");
  if (!motion_plan_client->wait_for_service(10s)) {
    RCLCPP_ERROR(node->get_logger(), "Motion plan service was not available for %s.", label.c_str());
    return false;
  }

  auto request = std::make_shared<moveit_msgs::srv::GetMotionPlan::Request>();
  move_group.constructMotionPlanRequest(request->motion_plan_request);
  auto motion_plan_future = motion_plan_client->async_send_request(request);
  if (motion_plan_future.wait_for(20s) != std::future_status::ready) {
    RCLCPP_ERROR(node->get_logger(), "Timed out waiting for a plan for %s.", label.c_str());
    return false;
  }

  auto motion_plan_response = motion_plan_future.get();
  if (motion_plan_response->motion_plan_response.error_code.val !=
    moveit_msgs::msg::MoveItErrorCodes::SUCCESS)
  {
    RCLCPP_ERROR(node->get_logger(), "Planning failed for %s.", label.c_str());
    return false;
  }

  if (!execute) {
    RCLCPP_INFO(node->get_logger(), "Planning succeeded for %s without execution.", label.c_str());
    return true;
  }

  auto execute_client = rclcpp_action::create_client<moveit_msgs::action::ExecuteTrajectory>(
    node, "/execute_trajectory");
  if (!execute_client->wait_for_action_server(10s)) {
    RCLCPP_ERROR(
      node->get_logger(), "Execute trajectory action server was not available for %s.", label.c_str());
    return false;
  }

  moveit_msgs::action::ExecuteTrajectory::Goal goal;
  goal.trajectory = motion_plan_response->motion_plan_response.trajectory;

  auto goal_handle_future = execute_client->async_send_goal(goal);
  if (goal_handle_future.wait_for(10s) != std::future_status::ready) {
    RCLCPP_ERROR(node->get_logger(), "Timed out sending execution goal for %s.", label.c_str());
    return false;
  }

  auto goal_handle = goal_handle_future.get();
  if (!goal_handle) {
    RCLCPP_ERROR(node->get_logger(), "Execution goal was rejected for %s.", label.c_str());
    return false;
  }

  auto result_future = execute_client->async_get_result(goal_handle);
  if (result_future.wait_for(60s) != std::future_status::ready) {
    RCLCPP_ERROR(node->get_logger(), "Timed out waiting for execution result for %s.", label.c_str());
    return false;
  }

  const auto wrapped_result = result_future.get();
  if (!wrapped_result.result ||
    wrapped_result.result->error_code.val != moveit_msgs::msg::MoveItErrorCodes::SUCCESS)
  {
    RCLCPP_ERROR(node->get_logger(), "Execution failed for %s.", label.c_str());
    return false;
  }

  RCLCPP_INFO(node->get_logger(), "Execution succeeded for %s.", label.c_str());
  return true;
}
}  // namespace

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::NodeOptions node_options;
  node_options.automatically_declare_parameters_from_overrides(true);
  auto node = rclcpp::Node::make_shared("ur10_move_group_interface_demo", node_options);

  const auto planning_group = node->get_parameter_or("planning_group", std::string("ur_manipulator"));
  const auto pose_target_frame = node->get_parameter_or("pose_target_frame", std::string("base_link"));
  const auto execute = node->get_parameter_or("execute", true);
  const auto wait_for_obstacle = node->get_parameter_or("wait_for_obstacle", true);
  const auto obstacle_id = node->get_parameter_or("obstacle_id", std::string("pcd_obstacle_box"));
  const auto use_pose_target = node->get_parameter_or("use_pose_target", false);
  const auto execute_home = node->get_parameter_or("execute_home", false);
  const auto startup_delay_sec = node->get_parameter_or("startup_delay_sec", 2.0);
  const auto obstacle_timeout_sec = node->get_parameter_or("obstacle_timeout_sec", 20.0);
  const auto parameter_sync_timeout_sec = node->get_parameter_or("parameter_sync_timeout_sec", 15.0);
  auto goal_joint_positions = node->get_parameter_or(
    "goal_joint_positions", std::vector<double>{-1.20, -1.70, 2.05, -1.95, -1.57, 0.0});
  auto home_joint_positions = node->get_parameter_or(
    "home_joint_positions", std::vector<double>{-1.20, -1.70, 2.05, -1.95, -1.57, 0.0});

  if (startup_delay_sec > 0.0) {
    std::this_thread::sleep_for(std::chrono::duration<double>(startup_delay_sec));
  }

  syncMoveGroupParameters(node, parameter_sync_timeout_sec);

  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  std::thread spinner([&executor]() { executor.spin(); });

  moveit::planning_interface::MoveGroupInterface move_group(node, planning_group);
  move_group.setPoseReferenceFrame(pose_target_frame);
  move_group.setPlanningTime(10.0);
  move_group.setMaxVelocityScalingFactor(0.05);
  move_group.setMaxAccelerationScalingFactor(0.05);
  move_group.setPlanningPipelineId("ompl");
  move_group.setPlannerId("RRTConnectkConfigDefault");

  if (!move_group.startStateMonitor(5.0)) {
    RCLCPP_ERROR(node->get_logger(), "Failed to start the MoveIt state monitor.");
    executor.cancel();
    spinner.join();
    rclcpp::shutdown();
    return 1;
  }

  auto current_state = move_group.getCurrentState(10.0);
  if (!current_state) {
    RCLCPP_ERROR(node->get_logger(), "Failed to fetch the current robot state.");
    executor.cancel();
    spinner.join();
    rclcpp::shutdown();
    return 2;
  }

  const auto * joint_model_group = current_state->getJointModelGroup(planning_group);
  if (joint_model_group == nullptr) {
    RCLCPP_ERROR(node->get_logger(), "Joint model group %s was not found.", planning_group.c_str());
    executor.cancel();
    spinner.join();
    rclcpp::shutdown();
    return 3;
  }

  if (execute_home) {
    std::vector<double> home_joint_target;
    current_state->copyJointGroupPositions(joint_model_group, home_joint_target);
    if (home_joint_positions.size() == joint_model_group->getVariableCount()) {
      home_joint_target = home_joint_positions;
    }

    RCLCPP_INFO(node->get_logger(), "Planning to the home joint target.");
    move_group.setStartStateToCurrentState();
    move_group.setJointValueTarget(home_joint_target);
    if (!planAndOptionallyExecute(move_group, node, "home joint target", execute)) {
      executor.cancel();
      spinner.join();
      rclcpp::shutdown();
      return 4;
    }

    std::this_thread::sleep_for(1s);
  } else {
    RCLCPP_INFO(
      node->get_logger(),
      "Skipping the intermediate home motion and planning directly to the obstacle-aware goal.");
  }

  if (wait_for_obstacle) {
    waitForSceneObject(node, obstacle_id, obstacle_timeout_sec);
  }

  move_group.setStartStateToCurrentState();

  if (use_pose_target) {
    geometry_msgs::msg::PoseStamped target_pose;
    target_pose.header.frame_id = pose_target_frame;
    target_pose.pose.orientation.x = 0.70710678;
    target_pose.pose.orientation.y = 0.0;
    target_pose.pose.orientation.z = 0.70710678;
    target_pose.pose.orientation.w = 0.0;
    target_pose.pose.position.x = 0.58;
    target_pose.pose.position.y = 0.34;
    target_pose.pose.position.z = 0.82;

    move_group.setPoseTarget(target_pose, "tool0");
    RCLCPP_INFO(node->get_logger(), "Planning to the Cartesian pose target.");
    if (!planAndOptionallyExecute(move_group, node, "Cartesian pose target", execute)) {
      executor.cancel();
      spinner.join();
      rclcpp::shutdown();
      return 5;
    }
  } else {
    if (goal_joint_positions.size() != joint_model_group->getVariableCount()) {
      RCLCPP_ERROR(
        node->get_logger(),
        "goal_joint_positions must contain %u values but received %zu.",
        joint_model_group->getVariableCount(), goal_joint_positions.size());
      executor.cancel();
      spinner.join();
      rclcpp::shutdown();
      return 6;
    }

    move_group.setJointValueTarget(goal_joint_positions);
    RCLCPP_INFO(node->get_logger(), "Planning to the obstacle-aware joint-space goal.");
    if (!planAndOptionallyExecute(move_group, node, "obstacle-aware joint-space goal", execute)) {
      executor.cancel();
      spinner.join();
      rclcpp::shutdown();
      return 7;
    }
  }

  executor.cancel();
  spinner.join();
  rclcpp::shutdown();
  return 0;
}

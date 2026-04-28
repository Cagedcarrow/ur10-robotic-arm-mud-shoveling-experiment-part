#include <chrono>
#include <future>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <control_msgs/action/follow_joint_trajectory.hpp>
#include <geometry_msgs/msg/pose_array.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <std_msgs/msg/string.hpp>
#include <trajectory_msgs/msg/joint_trajectory.hpp>
#include <visualization_msgs/msg/marker.hpp>

#include "ur10_trajectory_planner/action/execute_shovel_task.hpp"
#include "ur10_trajectory_planner/executor_math.hpp"
#include "ur10_trajectory_planner/msg/execution_feedback.hpp"
#include "ur10_trajectory_planner/msg/plan_info.hpp"
#include "ur10_trajectory_planner/msg/target_pose_seq.hpp"

using namespace std::chrono_literals;

class ExecutorNode : public rclcpp::Node
{
public:
  using ExecuteAction = ur10_trajectory_planner::action::ExecuteShovelTask;
  using GoalHandle = rclcpp_action::ServerGoalHandle<ExecuteAction>;
  using FollowTrajectory = control_msgs::action::FollowJointTrajectory;

  ExecutorNode()
  : Node("executor_node")
  {
    execution_mode_ = declare_parameter<std::string>("execution_mode", "demo");
    max_joint_step_ = declare_parameter("max_joint_step_rad", 0.1);
    dt_ = declare_parameter("dt", 0.05);

    traj_pub_ = create_publisher<trajectory_msgs::msg::JointTrajectory>(
      "/joint_trajectory_controller/joint_trajectory", 10);
    fb_pub_ = create_publisher<ur10_trajectory_planner::msg::ExecutionFeedback>(
      "/execution/feedback", 10);
    status_pub_ = create_publisher<std_msgs::msg::String>("/execution/status", 10);
    demo_marker_pub_ = create_publisher<visualization_msgs::msg::Marker>("/execution/demo_marker", 10);

    target_sub_ = create_subscription<ur10_trajectory_planner::msg::TargetPoseSeq>(
      "/trajectory/target_poses", 10,
      std::bind(&ExecutorNode::on_target_seq, this, std::placeholders::_1));

    planned_sub_ = create_subscription<geometry_msgs::msg::PoseArray>(
      "/planning/path", 10,
      std::bind(&ExecutorNode::on_planned_path, this, std::placeholders::_1));

    action_server_ = rclcpp_action::create_server<ExecuteAction>(
      this,
      "/execution/execute_shovel_task",
      std::bind(&ExecutorNode::handle_goal, this, std::placeholders::_1, std::placeholders::_2),
      std::bind(&ExecutorNode::handle_cancel, this, std::placeholders::_1),
      std::bind(&ExecutorNode::handle_accepted, this, std::placeholders::_1));

    controller_client_ = rclcpp_action::create_client<FollowTrajectory>(
      this, "/joint_trajectory_controller/follow_joint_trajectory");

    publish_status("ready");
    RCLCPP_INFO(get_logger(), "Executor node ready. execution_mode=%s", execution_mode_.c_str());
  }

private:
  void publish_status(const std::string & text)
  {
    std_msgs::msg::String msg;
    msg.data = text;
    status_pub_->publish(msg);
  }

  static std::vector<geometry_msgs::msg::Pose> pose_array_to_vector(
    const geometry_msgs::msg::PoseArray & arr)
  {
    return std::vector<geometry_msgs::msg::Pose>(arr.poses.begin(), arr.poses.end());
  }

  std::vector<geometry_msgs::msg::Pose> resolve_execution_poses(
    const std::shared_ptr<const ExecuteAction::Goal> & goal)
  {
    if (goal && !goal->target_pose_seq.poses.empty()) {
      return goal->target_pose_seq.poses;
    }

    std::scoped_lock<std::mutex> lock(data_mutex_);
    if (!latest_target_.poses.empty()) {
      return latest_target_.poses;
    }
    if (!latest_planned_.poses.empty()) {
      return pose_array_to_vector(latest_planned_);
    }
    return {};
  }

  void publish_execution_feedback(size_t idx, size_t total, uint32_t fallback, uint32_t hold, bool timeout,
    const std::string & stage)
  {
    ur10_trajectory_planner::msg::ExecutionFeedback fb;
    fb.header.stamp = now();
    fb.header.frame_id = "world";
    fb.current_index = static_cast<uint32_t>(idx);
    fb.total_index = static_cast<uint32_t>(total);
    fb.pos_err = 0.0f;
    fb.ori_err_deg = 0.0f;
    fb.fallback_count = fallback;
    fb.hold_count = hold;
    fb.timeout = timeout;
    fb.timeout_stage = stage;
    fb_pub_->publish(fb);
  }

  void publish_demo_marker(const std::vector<geometry_msgs::msg::Pose> & poses, size_t upto)
  {
    visualization_msgs::msg::Marker marker;
    marker.header.frame_id = "world";
    marker.header.stamp = now();
    marker.ns = "execution_demo";
    marker.id = 1;
    marker.type = visualization_msgs::msg::Marker::LINE_STRIP;
    marker.action = visualization_msgs::msg::Marker::ADD;
    marker.scale.x = 0.01;
    marker.color.a = 1.0;
    marker.color.r = 0.2;
    marker.color.g = 1.0;
    marker.color.b = 0.3;

    const size_t end_idx = std::min(upto, poses.size());
    marker.points.reserve(end_idx);
    for (size_t i = 0; i < end_idx; ++i) {
      marker.points.push_back(poses[i].position);
    }
    demo_marker_pub_->publish(marker);
  }

  bool execute_demo(
    const std::vector<geometry_msgs::msg::Pose> & poses,
    const std::shared_ptr<GoalHandle> & goal_handle,
    std::string * message)
  {
    publish_status("demo_executing");
    for (size_t i = 0; i < poses.size(); ++i) {
      if (goal_handle->is_canceling()) {
        if (message) {
          *message = "demo canceled";
        }
        publish_status("canceled");
        return false;
      }

      auto feedback = std::make_shared<ExecuteAction::Feedback>();
      feedback->current_index = static_cast<uint32_t>(i + 1);
      feedback->total_index = static_cast<uint32_t>(poses.size());
      feedback->pos_err = 0.0f;
      feedback->ori_err_deg = 0.0f;
      feedback->timeout = false;
      goal_handle->publish_feedback(feedback);

      publish_execution_feedback(i + 1, poses.size(), 0, 0, false, "demo");
      publish_demo_marker(poses, i + 1);
      std::this_thread::sleep_for(std::chrono::duration<double>(dt_));
    }

    if (message) {
      *message = "demo trajectory playback done";
    }
    publish_status("demo_done");
    return true;
  }

  bool execute_moveit_like(
    const std::vector<geometry_msgs::msg::Pose> & poses,
    std::string * message,
    uint32_t * fallback,
    uint32_t * hold)
  {
    publish_status("moveit_preparing");
    std::string reason;
    auto traj = ur10_trajectory_planner::poses_to_joint_trajectory(
      poses, max_joint_step_, dt_, fallback, hold, &reason);

    if (traj.points.empty()) {
      if (message) {
        *message = reason.empty() ? "empty trajectory" : reason;
      }
      publish_status("moveit_failed_empty");
      return false;
    }

    traj.header.stamp = now();
    traj_pub_->publish(traj);

    if (!controller_client_->wait_for_action_server(3s)) {
      if (message) {
        *message = "controller action server unavailable";
      }
      publish_status("moveit_failed_action_unavailable");
      return false;
    }

    FollowTrajectory::Goal goal;
    goal.trajectory = traj;

    auto future_goal = controller_client_->async_send_goal(goal);
    if (future_goal.wait_for(5s) != std::future_status::ready) {
      if (message) {
        *message = "timeout waiting controller goal response";
      }
      publish_status("moveit_failed_goal_timeout");
      return false;
    }

    auto ctrl_goal_handle = future_goal.get();
    if (!ctrl_goal_handle) {
      if (message) {
        *message = "controller rejected trajectory";
      }
      publish_status("moveit_failed_goal_rejected");
      return false;
    }

    publish_status("moveit_executing");
    auto future_result = controller_client_->async_get_result(ctrl_goal_handle);
    if (future_result.wait_for(std::chrono::seconds(
          std::max(8, static_cast<int>(poses.size() * dt_ * 3.0)))) != std::future_status::ready) {
      if (message) {
        *message = "timeout waiting controller result";
      }
      publish_status("moveit_failed_result_timeout");
      return false;
    }

    const auto wrapped = future_result.get();
    const bool ok = wrapped.code == rclcpp_action::ResultCode::SUCCEEDED && wrapped.result &&
      wrapped.result->error_code == control_msgs::action::FollowJointTrajectory::Result::SUCCESSFUL;

    if (!ok) {
      if (message) {
        *message = "controller execution failed";
      }
      publish_status("moveit_failed_execution");
      return false;
    }

    if (message) {
      *message = "moveit execution done";
    }
    publish_status("moveit_done");
    return true;
  }

  void execute_goal(const std::shared_ptr<GoalHandle> & goal_handle)
  {
    const auto goal = goal_handle->get_goal();
    auto poses = resolve_execution_poses(goal);

    auto result = std::make_shared<ExecuteAction::Result>();
    if (poses.empty()) {
      result->success = false;
      result->message = "no poses available for execution";
      result->plan_info.success = false;
      result->plan_info.algorithm = execution_mode_;
      result->plan_info.num_nodes = 0;
      result->plan_info.path_length = 0.0f;
      result->plan_info.elapsed_sec = 0.0f;
      result->plan_info.fail_count_final = 0.0f;
      goal_handle->abort(result);
      publish_status("failed_no_pose");
      return;
    }

    std::string message;
    bool success = false;
    uint32_t fallback = 0;
    uint32_t hold = 0;

    if (execution_mode_ == "moveit") {
      success = execute_moveit_like(poses, &message, &fallback, &hold);
    } else {
      success = execute_demo(poses, goal_handle, &message);
    }

    publish_execution_feedback(poses.size(), poses.size(), fallback, hold, !success, execution_mode_);

    result->success = success;
    result->message = message;
    result->plan_info.header.stamp = now();
    result->plan_info.header.frame_id = "world";
    result->plan_info.success = success;
    result->plan_info.algorithm = execution_mode_;
    result->plan_info.num_nodes = static_cast<uint32_t>(poses.size());
    result->plan_info.path_length = 0.0f;
    result->plan_info.elapsed_sec = 0.0f;
    result->plan_info.fail_count_final = static_cast<float>(fallback);

    if (success) {
      goal_handle->succeed(result);
    } else if (goal_handle->is_canceling()) {
      goal_handle->canceled(result);
    } else {
      goal_handle->abort(result);
    }
  }

  void on_target_seq(const ur10_trajectory_planner::msg::TargetPoseSeq::SharedPtr msg)
  {
    std::scoped_lock<std::mutex> lock(data_mutex_);
    latest_target_ = *msg;
  }

  void on_planned_path(const geometry_msgs::msg::PoseArray::SharedPtr msg)
  {
    std::scoped_lock<std::mutex> lock(data_mutex_);
    latest_planned_ = *msg;
  }

  rclcpp_action::GoalResponse handle_goal(
    const rclcpp_action::GoalUUID &, std::shared_ptr<const ExecuteAction::Goal>)
  {
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse handle_cancel(const std::shared_ptr<GoalHandle>)
  {
    publish_status("cancel_requested");
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void handle_accepted(const std::shared_ptr<GoalHandle> goal_handle)
  {
    std::thread([this, goal_handle]() { execute_goal(goal_handle); }).detach();
  }

  std::string execution_mode_;
  double max_joint_step_{0.1};
  double dt_{0.05};

  std::mutex data_mutex_;
  ur10_trajectory_planner::msg::TargetPoseSeq latest_target_;
  geometry_msgs::msg::PoseArray latest_planned_;

  rclcpp::Subscription<ur10_trajectory_planner::msg::TargetPoseSeq>::SharedPtr target_sub_;
  rclcpp::Subscription<geometry_msgs::msg::PoseArray>::SharedPtr planned_sub_;
  rclcpp::Publisher<trajectory_msgs::msg::JointTrajectory>::SharedPtr traj_pub_;
  rclcpp::Publisher<ur10_trajectory_planner::msg::ExecutionFeedback>::SharedPtr fb_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_pub_;
  rclcpp::Publisher<visualization_msgs::msg::Marker>::SharedPtr demo_marker_pub_;
  rclcpp_action::Server<ExecuteAction>::SharedPtr action_server_;
  rclcpp_action::Client<FollowTrajectory>::SharedPtr controller_client_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ExecutorNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}

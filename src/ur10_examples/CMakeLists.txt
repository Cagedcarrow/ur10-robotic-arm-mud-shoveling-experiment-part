cmake_minimum_required(VERSION 3.8)
project(ur10_examples)

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(moveit_msgs REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)

add_executable(move_group_interface_demo src/move_group_interface_demo.cpp)
ament_target_dependencies(
  move_group_interface_demo
  geometry_msgs
  moveit_msgs
  moveit_ros_planning_interface
  rclcpp
  rclcpp_action
  tf2_geometry_msgs
)

install(TARGETS move_group_interface_demo DESTINATION lib/${PROJECT_NAME})

ament_package()

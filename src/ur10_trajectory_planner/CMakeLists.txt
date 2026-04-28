cmake_minimum_required(VERSION 3.8)
project(ur10_trajectory_planner)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(trajectory_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(control_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/BucketFeatures.msg"
  "msg/TargetPoseSeq.msg"
  "msg/PlanInfo.msg"
  "msg/ExecutionFeedback.msg"
  "srv/GenerateTrajectory.srv"
  "action/ExecuteShovelTask.action"
  DEPENDENCIES std_msgs geometry_msgs builtin_interfaces
)

add_library(trajectory_fitter src/trajectory_fitter.cpp)
target_include_directories(trajectory_fitter PUBLIC include)
ament_target_dependencies(trajectory_fitter rclcpp geometry_msgs)

add_library(pose_builder src/pose_builder.cpp)
target_include_directories(pose_builder PUBLIC include)
ament_target_dependencies(pose_builder rclcpp geometry_msgs)

add_library(planner_adapter src/planner_adapter.cpp)
target_include_directories(planner_adapter PUBLIC include)
ament_target_dependencies(planner_adapter rclcpp geometry_msgs visualization_msgs)

add_library(executor_adapter src/executor_adapter.cpp)
target_include_directories(executor_adapter PUBLIC include)
ament_target_dependencies(executor_adapter rclcpp trajectory_msgs sensor_msgs)

add_executable(trajectory_node src/trajectory_node.cpp)
ament_target_dependencies(trajectory_node rclcpp geometry_msgs std_msgs)
target_link_libraries(trajectory_node trajectory_fitter pose_builder)

add_executable(planner_node src/planner_node.cpp)
ament_target_dependencies(planner_node rclcpp geometry_msgs std_msgs visualization_msgs)
target_link_libraries(planner_node planner_adapter)

add_executable(executor_node src/executor_node.cpp)
ament_target_dependencies(executor_node
  rclcpp
  rclcpp_action
  geometry_msgs
  sensor_msgs
  std_msgs
  trajectory_msgs
  visualization_msgs
  control_msgs)
target_link_libraries(executor_node executor_adapter)

rosidl_get_typesupport_target(cpp_typesupport_target ${PROJECT_NAME} "rosidl_typesupport_cpp")

target_link_libraries(trajectory_node ${cpp_typesupport_target})
target_link_libraries(planner_node ${cpp_typesupport_target})
target_link_libraries(executor_node ${cpp_typesupport_target})

install(TARGETS
  trajectory_fitter pose_builder planner_adapter executor_adapter
  trajectory_node planner_node executor_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

ament_export_include_directories(include)
ament_export_dependencies(rosidl_default_runtime)
ament_package()

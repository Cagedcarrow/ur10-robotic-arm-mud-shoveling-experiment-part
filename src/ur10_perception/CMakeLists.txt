cmake_minimum_required(VERSION 3.8)
project(ur10_perception)

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(moveit_msgs REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(pcl_conversions REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(shape_msgs REQUIRED)

find_package(PCL REQUIRED COMPONENTS common io filters segmentation search)

include_directories(
  include
  ${PCL_INCLUDE_DIRS}
)

add_executable(pcd_capture_node src/pcd_capture_node.cpp)
ament_target_dependencies(
  pcd_capture_node
  pcl_conversions
  rclcpp
  sensor_msgs
)
target_link_libraries(pcd_capture_node ${PCL_LIBRARIES})

add_executable(synthetic_overhead_camera_node src/synthetic_overhead_camera_node.cpp)
ament_target_dependencies(
  synthetic_overhead_camera_node
  pcl_conversions
  rclcpp
  sensor_msgs
)
target_link_libraries(synthetic_overhead_camera_node ${PCL_LIBRARIES})

add_executable(pcd_to_collision_scene_node src/pcd_to_collision_scene_node.cpp)
ament_target_dependencies(
  pcd_to_collision_scene_node
  geometry_msgs
  moveit_msgs
  moveit_ros_planning_interface
  pcl_conversions
  rclcpp
  sensor_msgs
  shape_msgs
)
target_link_libraries(pcd_to_collision_scene_node ${PCL_LIBRARIES})

install(
  TARGETS pcd_capture_node synthetic_overhead_camera_node pcd_to_collision_scene_node
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY config launch urdf worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()

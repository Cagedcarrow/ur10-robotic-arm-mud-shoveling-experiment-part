cmake_minimum_required(VERSION 3.8)
project(my_robot)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch meshes rviz textures urdf
  DESTINATION share/${PROJECT_NAME}
)

install(
  FILES my_robot.urdf.xacro
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/shovel_tcp_slider.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

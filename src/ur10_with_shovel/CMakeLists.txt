cmake_minimum_required(VERSION 3.8)
project(ur10_with_shovel)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf launch config meshes rviz
  DESTINATION share/${PROJECT_NAME}
)

install(
  FILES README.md
  DESTINATION share/${PROJECT_NAME}
)

ament_package()

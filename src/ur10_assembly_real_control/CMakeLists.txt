cmake_minimum_required(VERSION 3.8)
project(ur10_assembly_real_control)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch docs
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/check_real_ur10_ready.sh
  scripts/real_control_gui.py
  scripts/start_real_control_gui.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

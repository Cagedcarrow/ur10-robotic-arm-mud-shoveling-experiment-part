cmake_minimum_required(VERSION 3.8)
project(kdl_inverse_dynamics_solver)

if(CMAKE_COMPILER_IS_GNUCXX
   OR CMAKE_CXX_COMPILER_ID
      MATCHES
      "Clang"
)
  add_compile_options(
    -Wall
    -Wextra
    -Wpedantic
  )
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_ros REQUIRED)
find_package(pluginlib REQUIRED)
find_package(moveit_core REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(inverse_dynamics_solver REQUIRED)
find_package(launch_testing_ament_cmake)

# add library
add_library(kdl_inverse_dynamics_solver
            src/kdl_inverse_dynamics_solver.cpp
)
target_compile_features(
  kdl_inverse_dynamics_solver
  PUBLIC c_std_99 cxx_std_17
) # Require C99 and C++17
target_include_directories(
  kdl_inverse_dynamics_solver
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(
  kdl_inverse_dynamics_solver
  pluginlib
  moveit_core
  moveit_ros_planning_interface
  inverse_dynamics_solver
)

# create plugin
pluginlib_export_plugin_description_file(inverse_dynamics_solver kdl_inverse_dynamics_solver.xml)

# Causes the visibility macros to use dllexport rather than dllimport, which is appropriate when
# building the dll but not consuming it.
target_compile_definitions(
  kdl_inverse_dynamics_solver
  PRIVATE "KDL_INVERSE_DYNAMICS_SOLVER_BUILDING_LIBRARY"
)

# install library
install(DIRECTORY include/
        DESTINATION include
)
install(TARGETS kdl_inverse_dynamics_solver
        EXPORT export_${PROJECT_NAME}
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
        RUNTIME DESTINATION bin
)

# tests
if(BUILD_TESTING)
  # find dependencies
  find_package(ament_cmake_gtest REQUIRED)
  find_package(ros_testing REQUIRED)
  find_package(ros_extensions_utilities REQUIRED)

  # add tests
  set(TEST_NAME
      ${PROJECT_NAME}_test
  )
  ament_add_gtest_executable(${TEST_NAME} test/test_kdl_inverse_dynamics_solver.cpp)
  target_include_directories(
    ${TEST_NAME}
    PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> $<INSTALL_INTERFACE:include>
  )
  ament_target_dependencies(
    ${TEST_NAME}
    pluginlib
    moveit_core
    moveit_ros_planning_interface
    ros_extensions_utilities
    inverse_dynamics_solver
  )
  add_ros_test(launch/test_kdl_inverse_dynamics_solver.py)

  # install test files
  install(DIRECTORY launch
          DESTINATION share/${PROJECT_NAME}
  )
  install(TARGETS ${TEST_NAME}
          RUNTIME DESTINATION lib/${PROJECT_NAME}
  )
endif()

# export plugin library
ament_export_include_directories(include)
ament_export_libraries(kdl_inverse_dynamics_solver)
ament_export_targets(export_${PROJECT_NAME})

# install launch files
install(DIRECTORY launch
        DESTINATION share/${PROJECT_NAME}/
)

# compile the package
ament_package()

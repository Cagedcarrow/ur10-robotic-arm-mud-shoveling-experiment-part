cmake_minimum_required(VERSION 3.8)
project(ur10_inverse_dynamics_solver)

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
find_package(inverse_dynamics_solver REQUIRED)
find_package(launch_testing_ament_cmake)

# add library
add_library(ur10_inverse_dynamics_solver
            src/getCoriolisCurrents.cpp
            src/getCurrents.cpp
            src/getGravityCurrents.cpp
            src/getInertiaCurrents.cpp
            src/getPayloadCoriolisRegressionMatrix.cpp
            src/getPayloadGravityRegressionMatrix.cpp
            src/getPayloadInertiaRegressionMatrix.cpp
            src/getPayloadRegressionMatrix.cpp
            src/ur10_inverse_dynamics_solver.cpp
)
target_compile_features(
  ur10_inverse_dynamics_solver
  PUBLIC c_std_99 cxx_std_17
) # Require C99 and C++17
target_include_directories(
  ur10_inverse_dynamics_solver
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(
  ur10_inverse_dynamics_solver
  pluginlib
  moveit_core
  inverse_dynamics_solver
)

# create plugin
pluginlib_export_plugin_description_file(inverse_dynamics_solver ur10_inverse_dynamics_solver.xml)

# Causes the visibility macros to use dllexport rather than dllimport, which is appropriate when
# building the dll but not consuming it.
target_compile_definitions(
  ur10_inverse_dynamics_solver
  PRIVATE "UR10_INVERSE_DYNAMICS_SOLVER_BUILDING_LIBRARY"
)

# install library
install(DIRECTORY include/
        DESTINATION include
)
install(TARGETS ur10_inverse_dynamics_solver
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
  find_package(rosbag2_cpp REQUIRED)
  find_package(ros_extensions_utilities REQUIRED)

  # add gtests
  set(TEST_NAME
      ${PROJECT_NAME}_test
  )
  ament_add_gtest_executable(${TEST_NAME} test/test_ur10_inverse_dynamics_solver.cpp)
  target_include_directories(
    ${TEST_NAME}
    PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> $<INSTALL_INTERFACE:include>
  )
  ament_target_dependencies(
    ${TEST_NAME}
    rosbag2_cpp
    pluginlib
    ros_extensions_utilities
    inverse_dynamics_solver
  )
  add_ros_test(launch/test_ur10_inverse_dynamics_solver.py)

  # install test files
  install(DIRECTORY config
          DESTINATION share/${PROJECT_NAME}
  )
  install(DIRECTORY launch
          DESTINATION share/${PROJECT_NAME}
  )
  install(DIRECTORY test/bagfiles
          DESTINATION share/${PROJECT_NAME}
  )
  install(TARGETS ${TEST_NAME}
          RUNTIME DESTINATION lib/${PROJECT_NAME}
  )
endif()

# export plugin library
ament_export_include_directories(include)
ament_export_libraries(ur10_inverse_dynamics_solver)
ament_export_targets(export_${PROJECT_NAME})

# install launch files
install(DIRECTORY launch
        DESTINATION share/${PROJECT_NAME}/
)

# compile the package
ament_package()

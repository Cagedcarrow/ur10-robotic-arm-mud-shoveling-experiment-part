#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../../.."
colcon build --packages-select ur10_trajectory_planner
source install/setup.bash
ros2 launch ur10_trajectory_planner shovel_bucket_pipeline.launch.py

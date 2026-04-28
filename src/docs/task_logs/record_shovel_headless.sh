#!/usr/bin/env bash
set -euo pipefail

# Prereq: sudo apt install -y xvfb ffmpeg
if ! command -v Xvfb >/dev/null 2>&1; then
  echo "[ERROR] Xvfb not found. Install it first: sudo apt install -y xvfb"
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[ERROR] ffmpeg not found. Install it first: sudo apt install -y ffmpeg"
  exit 1
fi

export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 >/tmp/xvfb_shovel.log 2>&1 &
XVFB_PID=$!

cleanup() {
  kill ${LAUNCH_PID:-0} >/dev/null 2>&1 || true
  kill ${XVFB_PID:-0} >/dev/null 2>&1 || true
}
trap cleanup EXIT

cd /root/ur10_ws

# ROS2 setup scripts are not strict-nounset safe in some environments.
export AMENT_TRACE_SETUP_FILES="${AMENT_TRACE_SETUP_FILES-}"
export COLCON_TRACE="${COLCON_TRACE-}"
set +u
source install/setup.bash
set -u

ros2 launch ur10_simulation_bringup complete_simulation_with_shovel_trajectory.launch.py \
  start_rviz:=true planner_mode:=dp_rrt >/tmp/complete_with_traj_record.log 2>&1 &
LAUNCH_PID=$!

sleep 12

ffmpeg -y -video_size 1920x1080 -framerate 30 -f x11grab -i :99.0 \
  -t 25 -vcodec libx264 -pix_fmt yuv420p /root/ur10_ws/src/docs/task_logs/shovel_dprrt_execution.mp4

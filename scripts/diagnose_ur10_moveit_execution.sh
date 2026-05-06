#!/usr/bin/env bash
set -eo pipefail

ROBOT_IP="${1:-10.160.9.21}"
WS_DIR="${2:-/root/ur10_ws}"
SRC_SETUP="${WS_DIR}/install/setup.bash"
NOW="$(date '+%F %T')"

echo "[diag] time=${NOW}"
echo "[diag] ROS_DISTRO=${ROS_DISTRO:-unset}"
echo "[diag] workspace=${WS_DIR}"
echo "[diag] robot_ip=${ROBOT_IP}"

if [[ ! -f "${SRC_SETUP}" ]]; then
  echo "[diag] ERROR: setup file not found: ${SRC_SETUP}"
  echo "RESULT=DRIVER_NOT_RUNNING"
  exit 1
fi

# shellcheck source=/dev/null
set +u
source "${SRC_SETUP}"
set -u

run_cmd() {
  local title="$1"
  shift
  echo "\n===== ${title} ====="
  "$@" 2>&1 || true
}

run_cmd "Network ping" ping -c 2 "${ROBOT_IP}"
run_cmd "Port 29999" nc -vz "${ROBOT_IP}" 29999
run_cmd "Port 30001" nc -vz "${ROBOT_IP}" 30001
run_cmd "Port 30002" nc -vz "${ROBOT_IP}" 30002
run_cmd "Port 30003" nc -vz "${ROBOT_IP}" 30003

run_cmd "Processes" bash -lc "ps -ef | grep -E 'ros2 launch ur_robot_driver|ur_ros2_control_node|move_group|controller_manager|rtde|dashboard|external' | grep -v grep"
run_cmd "Nodes" ros2 node list
run_cmd "Topics" ros2 topic list
run_cmd "Actions" ros2 action list
run_cmd "Controller services" bash -lc "ros2 service list | grep controller"

DRIVER_COUNT=$(pgrep -fc "ros2 launch ur_robot_driver ur_control.launch.py" || true)
MOVE_GROUP_COUNT=$(pgrep -fc "moveit_ros_move_group|/move_group" || true)
CM_COUNT=$(pgrep -fc "controller_manager" || true)
DRIVER_COUNT=${DRIVER_COUNT:-0}
MOVE_GROUP_COUNT=${MOVE_GROUP_COUNT:-0}
CM_COUNT=${CM_COUNT:-0}

if (( DRIVER_COUNT > 1 )) || (( MOVE_GROUP_COUNT > 1 )); then
  echo "[diag] WARN: duplicate core processes detected: driver=${DRIVER_COUNT}, move_group=${MOVE_GROUP_COUNT}, controller_manager=${CM_COUNT}"
fi

CTRLS_OUT=$(timeout 8s ros2 control list_controllers 2>&1 || true)
HI_OUT=$(timeout 8s ros2 control list_hardware_interfaces 2>&1 || true)
ACT_OUT=$(ros2 action list 2>/dev/null || true)
JS_ONCE=$(timeout 6s ros2 topic echo /joint_states --once 2>&1 || true)

run_cmd "ros2 control list_controllers" bash -lc "printf '%s\n' \"${CTRLS_OUT}\""
run_cmd "ros2 control list_hardware_interfaces" bash -lc "printf '%s\n' \"${HI_OUT}\""
run_cmd "joint_states once" bash -lc "printf '%s\n' \"${JS_ONCE}\""

RESULT="READY_FOR_RVIZ_EXECUTION"

if ! ros2 node list 2>/dev/null | grep -qE '/ur_robot_state_helper|/dashboard_client|/urscript_interface'; then
  RESULT="DRIVER_NOT_RUNNING"
fi

if [[ "${RESULT}" == "READY_FOR_RVIZ_EXECUTION" ]] && ! grep -q "scaled_joint_trajectory_controller" <<< "${CTRLS_OUT}"; then
  RESULT="CONTROLLER_NOT_ACTIVE"
fi

if [[ "${RESULT}" == "READY_FOR_RVIZ_EXECUTION" ]] && ! grep -q "scaled_joint_trajectory_controller.*active" <<< "${CTRLS_OUT}"; then
  RESULT="CONTROLLER_NOT_ACTIVE"
fi

if [[ "${RESULT}" == "READY_FOR_RVIZ_EXECUTION" ]] && ! grep -q "/scaled_joint_trajectory_controller/follow_joint_trajectory" <<< "${ACT_OUT}"; then
  RESULT="ACTION_NOT_AVAILABLE"
fi

if [[ "${RESULT}" == "READY_FOR_RVIZ_EXECUTION" ]] && grep -q "does not appear to be published\|Could not determine the type" <<< "${JS_ONCE}"; then
  RESULT="JOINT_STATES_MISSING"
fi

# Only treat RTDE occupied as current issue when it appears in the newest launch logs.
LATEST_LOG_DIR="$(ls -dt /root/.ros/log/* 2>/dev/null | head -n1 || true)"
if [[ -n "${LATEST_LOG_DIR}" ]] && grep -R "speed_slider_mask" -n "${LATEST_LOG_DIR}" >/dev/null 2>&1; then
  RESULT="RTDE_OCCUPIED"
fi

# Heuristic mismatch check for current workspace custom chain.
if [[ "${RESULT}" == "READY_FOR_RVIZ_EXECUTION" ]]; then
  if [[ -f "${WS_DIR}/src/ur10_real_pose_sync/config/moveit_controllers_virtual.yaml" ]]; then
    if ! grep -q "joint_trajectory_controller" "${WS_DIR}/src/ur10_real_pose_sync/config/moveit_controllers_virtual.yaml"; then
      RESULT="MOVEIT_CONTROLLER_MISMATCH"
    fi
  fi
fi

echo "\nRESULT=${RESULT}"

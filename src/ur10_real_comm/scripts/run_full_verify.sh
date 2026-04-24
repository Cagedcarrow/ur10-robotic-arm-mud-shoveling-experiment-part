#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [ -f "${SCRIPT_DIR}/../config/real_robot.env.example" ]; then
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/../config/real_robot.env.example"
fi

ROBOT_IP="${ROBOT_IP:-192.168.56.101}"
REVERSE_IP="${REVERSE_IP:-192.168.56.1}"
UR_TYPE="${UR_TYPE:-ur10}"
CONFIRM_EXECUTE="${CONFIRM_EXECUTE:-true}"
LAUNCH_RVIZ="${LAUNCH_RVIZ:-true}"
INITIAL_JOINT_CONTROLLER="${INITIAL_JOINT_CONTROLLER:-scaled_joint_trajectory_controller}"
WRIST3_DELTA_DEG="${WRIST3_DELTA_DEG:-0.5}"
STATUS_TIMEOUT_SEC="${STATUS_TIMEOUT_SEC:-600}"
STATUS_TOPIC="/ur10_real_comm/status"

source /opt/ros/humble/setup.bash
if [ -f "${WS_ROOT}/install/setup.bash" ]; then
  source "${WS_ROOT}/install/setup.bash"
fi

cd "${WS_ROOT}"
set +e
ros2 launch ur10_real_comm real_comm_moveit_verify.launch.py \
  ur_type:="${UR_TYPE}" \
  robot_ip:="${ROBOT_IP}" \
  reverse_ip:="${REVERSE_IP}" \
  confirm_execute:="${CONFIRM_EXECUTE}" \
  launch_rviz:="${LAUNCH_RVIZ}" \
  initial_joint_controller:="${INITIAL_JOINT_CONTROLLER}" \
  wrist3_delta_deg:="${WRIST3_DELTA_DEG}" \
  > /tmp/ur10_real_comm_launch.log 2>&1 &
LAUNCH_PID=$!
set -e

cleanup() {
  if kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill "${LAUNCH_PID}" 2>/dev/null || true
    wait "${LAUNCH_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "[INFO] Launched verify stack (pid=${LAUNCH_PID})."
echo "[INFO] Waiting final status on ${STATUS_TOPIC} (timeout ${STATUS_TIMEOUT_SEC}s)..."

STATUS_LINE="$(timeout "${STATUS_TIMEOUT_SEC}" ros2 topic echo --qos-reliability best_effort --qos-durability volatile "${STATUS_TOPIC}" std_msgs/msg/String 2>/dev/null | awk '
  /data:/ {
    line=$0
    sub(/^data: /, "", line)
    gsub(/^'\''|'\''$/, "", line)
    if (line ~ /"state":\s*"PASS"/ || line ~ /"state":\s*"FAIL"/) {
      print line
      exit
    }
  }
')"
STATUS_ECHO_EXIT=$?

FINAL_STATE="FAIL"
FINAL_REASON="No terminal status received."
if [ "${STATUS_ECHO_EXIT}" -eq 0 ] && [ -n "${STATUS_LINE}" ]; then
  if echo "${STATUS_LINE}" | grep -q '"state": *"PASS"'; then
    FINAL_STATE="PASS"
  else
    FINAL_STATE="FAIL"
  fi
  FINAL_REASON="$(echo "${STATUS_LINE}" | sed -n 's/.*"reason": *"\([^"]*\)".*/\1/p')"
  if [ -z "${FINAL_REASON}" ]; then
    FINAL_REASON="(reason unavailable)"
  fi
elif [ "${STATUS_ECHO_EXIT}" -eq 124 ]; then
  FINAL_REASON="Timed out waiting for terminal status."
else
  FINAL_REASON="Failed to read status topic."
fi

echo "[SUMMARY] state=${FINAL_STATE} reason=${FINAL_REASON} wrist3_delta_deg=${WRIST3_DELTA_DEG} controller=${INITIAL_JOINT_CONTROLLER} robot_ip=${ROBOT_IP} reverse_ip=${REVERSE_IP}"

if [ "${FINAL_STATE}" = "PASS" ]; then
  EXIT_CODE=0
else
  EXIT_CODE=1
fi

cleanup
trap - EXIT INT TERM

if [ "${FINAL_STATE}" = "PASS" ]; then
  echo "[PASS] UR10 real robot + MoveIt micro-move verify completed."
else
  echo "[FAIL] UR10 real robot + MoveIt micro-move verify failed."
  echo "[INFO] Launch log: /tmp/ur10_real_comm_launch.log"
fi
exit "${EXIT_CODE}"

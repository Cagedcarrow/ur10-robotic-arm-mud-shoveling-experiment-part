#!/usr/bin/env bash
set -u

JOINT_OK=0
CTRL_OK=0
ACTION_OK=0
SPEED_OK=0
FAKE_DETECTED=0
RTDE_OK=0

strip_ansi() {
  sed -r 's/\x1B\[[0-9;]*[mK]//g'
}

run_cmd() {
  echo "[CMD] $*"
  "$@"
}

echo "=== UR10 REAL READY CHECK START ==="

run_cmd ros2 topic info /joint_states -v || true
if JS_ONCE=$(timeout 5s ros2 topic echo /joint_states --once 2>/dev/null); then
  echo "$JS_ONCE"
  echo "JOINT_STATES_OK"
  JOINT_OK=1
else
  echo "JOINT_STATES_MISSING"
fi

NODE_LIST=$(timeout 5s ros2 node list 2>/dev/null || true)
TOPIC_LIST=$(timeout 5s ros2 topic list 2>/dev/null || true)
CTRL_LIST=$(timeout 5s ros2 control list_controllers 2>/dev/null || true)
CTRL_LIST_CLEAN=$(printf '%s\n' "$CTRL_LIST" | strip_ansi)
ACTION_LIST=$(timeout 5s ros2 action list 2>/dev/null || true)
SPEED_TOPIC=$(timeout 5s ros2 topic list 2>/dev/null | grep -E '/speed_scaling_state_broadcaster/speed_scaling$|/speed_scaling$' | head -1 || true)

echo "$NODE_LIST"
echo "$TOPIC_LIST" | grep joint_states || true
echo "$CTRL_LIST"
echo "$ACTION_LIST" | grep follow_joint_trajectory || true

if echo "$NODE_LIST" | grep -Eq 'joint_state_publisher|fake_joint_state_publisher'; then
  FAKE_DETECTED=1
fi
if echo "$TOPIC_LIST" | grep -Eq 'fake|mock_joint_states'; then
  FAKE_DETECTED=1
fi
if [ "$FAKE_DETECTED" -eq 1 ]; then
  echo "FAKE_STATE_SOURCE_DETECTED"
fi

if echo "$CTRL_LIST_CLEAN" | grep -Eq '^scaled_joint_trajectory_controller[[:space:]].*[[:space:]]active[[:space:]]*$'; then
  echo "CONTROLLER_ACTIVE"
  CTRL_OK=1
else
  echo "CONTROLLER_NOT_ACTIVE"
fi

if echo "$ACTION_LIST" | grep -qx '/scaled_joint_trajectory_controller/follow_joint_trajectory'; then
  echo "ACTION_ONLINE"
  ACTION_OK=1
else
  echo "ACTION_MISSING"
fi

if [ -n "$SPEED_TOPIC" ]; then
  echo "SPEED_SCALING_TOPIC=$SPEED_TOPIC"
  SPEED_MSG=$(timeout 5s ros2 topic echo "$SPEED_TOPIC" --once 2>/dev/null || true)
  echo "$SPEED_MSG"
  SPEED_VALUE=$(printf '%s\n' "$SPEED_MSG" | awk '/data:/ {print $2; exit}')
  if awk "BEGIN {exit !(${SPEED_VALUE:-0} > 0.01)}"; then
    echo "SPEED_SCALING_NONZERO"
    SPEED_OK=1
  else
    echo "SPEED_SCALING_ZERO_OR_MISSING"
  fi
else
  echo "SPEED_SCALING_TOPIC_MISSING"
fi

echo "=== RTDE OVERFLOW CHECK ==="
RTDE_HITS=$(
  find "$HOME/.ros/log" -maxdepth 3 -type f -name '*.log' -mmin -30 -print0 2>/dev/null \
    | xargs -0 -r grep -IhE 'Pipeline producer overflowed|RTDE Data Pipeline|RTDE.*overflowed|overflowed.*RTDE' 2>/dev/null \
    | tail -n 10
)
if [ -n "$RTDE_HITS" ]; then
  echo "$RTDE_HITS"
  echo "RTDE_OVERFLOW"
else
  echo "RTDE_OK"
  RTDE_OK=1
fi

if [ "$JOINT_OK" -eq 1 ] && [ "$CTRL_OK" -eq 1 ] && [ "$ACTION_OK" -eq 1 ] && [ "$SPEED_OK" -eq 1 ] && [ "$RTDE_OK" -eq 1 ] && [ "$FAKE_DETECTED" -eq 0 ]; then
  echo "READY_FOR_RVIZ2_MOVEIT_EXECUTION"
fi

echo "=== UR10 REAL READY CHECK END ==="

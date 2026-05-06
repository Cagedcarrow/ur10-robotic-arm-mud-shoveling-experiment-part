#!/usr/bin/env bash
set -u

JOINT_OK=0
CTRL_OK=0
ACTION_OK=0
FAKE_DETECTED=0

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
ACTION_LIST=$(timeout 5s ros2 action list 2>/dev/null || true)

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

if echo "$CTRL_LIST" | grep -Eq '^scaled_joint_trajectory_controller[[:space:]].*active'; then
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

if [ "$JOINT_OK" -eq 1 ] && [ "$CTRL_OK" -eq 1 ] && [ "$ACTION_OK" -eq 1 ] && [ "$FAKE_DETECTED" -eq 0 ]; then
  echo "READY_FOR_RVIZ2_MOVEIT_EXECUTION"
fi

echo "=== UR10 REAL READY CHECK END ==="

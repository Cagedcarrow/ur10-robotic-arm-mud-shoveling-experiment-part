#!/usr/bin/env bash
set -u

JOINT_OK=0
CTRL_OK=0
ACTION_OK=0

if timeout 5s ros2 topic echo /joint_states --once >/tmp/ur10_virtual_joint_states_check.txt 2>/dev/null; then
  echo "VIRTUAL_JOINT_STATES_OK"
  JOINT_OK=1
else
  echo "VIRTUAL_JOINT_STATES_MISSING"
fi

CTRL_LIST="$(timeout 5s ros2 control list_controllers 2>/dev/null | sed -r $'s/\x1B\\[[0-9;]*[mK]//g' || true)"
printf '%s\n' "$CTRL_LIST" | grep joint_trajectory_controller || true
if printf '%s\n' "$CTRL_LIST" | grep -Eq '^joint_trajectory_controller[[:space:]].*[[:space:]]active[[:space:]]*$'; then
  echo "VIRTUAL_CONTROLLER_ACTIVE"
  CTRL_OK=1
else
  echo "VIRTUAL_CONTROLLER_NOT_ACTIVE"
fi

ACTION_INFO="$(timeout 5s ros2 action info /joint_trajectory_controller/follow_joint_trajectory 2>/dev/null || true)"
printf '%s\n' "$ACTION_INFO" | grep 'Action:' || true
printf '%s\n' "$ACTION_INFO" | grep 'Action servers:' || true
if printf '%s\n' "$ACTION_INFO" | grep -Eq 'Action servers:[[:space:]]*[1-9]'; then
  echo "VIRTUAL_ACTION_ONLINE"
  ACTION_OK=1
else
  echo "VIRTUAL_ACTION_MISSING"
fi

if [ "$JOINT_OK" -eq 1 ] && [ "$CTRL_OK" -eq 1 ] && [ "$ACTION_OK" -eq 1 ]; then
  echo "READY_FOR_RVIZ2_VIRTUAL_MOVEIT"
else
  echo "NOT_READY_FOR_RVIZ2_VIRTUAL_MOVEIT"
fi

#!/usr/bin/env bash
set -eo pipefail

WORKSPACE="${UR10_WS:-/root/ur10_ws}"
LOG_DIR="${HOME}/.ros/log"
LOG_FILE="${LOG_DIR}/ur10_external_control_gui_launcher.log"

mkdir -p "${LOG_DIR}"

{
  echo "=== UR10 External Control GUI launcher ==="
  date
  echo "WORKSPACE=${WORKSPACE}"

  cd "${WORKSPACE}"
  source /opt/ros/humble/setup.bash

  if [ ! -f install/setup.bash ]; then
    echo "ERROR: ${WORKSPACE}/install/setup.bash does not exist."
    echo "Run: cd ${WORKSPACE} && colcon build --symlink-install --packages-select ur10_assembly_real_control"
    exit 2
  fi

  source install/setup.bash
  exec ros2 launch ur10_assembly_real_control real_control_gui.launch.py "$@"
} >> "${LOG_FILE}" 2>&1

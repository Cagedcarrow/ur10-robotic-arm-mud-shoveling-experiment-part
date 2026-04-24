#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  /root/ur10_ws/src/docs/ur10_real_comm_实机微动验证总结/run_full_verify_wsl.sh [options]

Options:
  --host-ip IP             Windows主机IP（建议为Windows网卡IP）
  --robot-ip IP            UR10机器人IP [默认: 192.168.56.101]
  --robot-subnet CIDR      UR10网段 [默认: 192.168.56.0/24]
  --ws-root PATH           WSL工作空间根路径 [默认: /root/ur10_ws]
  --wrist-delta DEG        wrist3_delta_deg [默认: 0.5]
  --controller NAME        initial_joint_controller [默认: scaled_joint_trajectory_controller]
  --no-rviz                不启动rviz
  --no-confirm             confirm_execute=false
  --status-timeout SEC     监听状态超时秒 [默认: 600]
  --dry-run                仅打印将要执行的环境变量和命令，不实际运行
  -h, --help              帮助

说明：
  本脚本不依赖 PowerShell，仅在 WSL 内执行。
  前提：你已经按你的网络方式确认主机侧网络可达（例如 Windows网卡、路由/NAT/portproxy都已生效）。
USAGE
}

HOST_IP="${UR10_WINDOWS_HOST_IP:-}"
ROBOT_IP="192.168.56.101"
ROBOT_SUBNET="192.168.56.0/24"
WS_ROOT="/root/ur10_ws"
WRIST3_DELTA="0.5"
CONTROLLER="scaled_joint_trajectory_controller"
LAUNCH_RVIZ="true"
CONFIRM_EXECUTE="true"
STATUS_TIMEOUT="600"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host-ip)
      HOST_IP="$2"; shift 2 ;;
    --robot-ip)
      ROBOT_IP="$2"; shift 2 ;;
    --robot-subnet)
      ROBOT_SUBNET="$2"; shift 2 ;;
    --ws-root)
      WS_ROOT="$2"; shift 2 ;;
    --wrist-delta)
      WRIST3_DELTA="$2"; shift 2 ;;
    --controller)
      CONTROLLER="$2"; shift 2 ;;
    --no-rviz)
      LAUNCH_RVIZ="false"; shift ;;
    --no-confirm)
      CONFIRM_EXECUTE="false"; shift ;;
    --status-timeout)
      STATUS_TIMEOUT="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN="true"; shift ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${HOST_IP}" ]]; then
  echo "[ERROR] 未设置 --host-ip。请手工加参数 --host-ip 192.168.56.1（或设置环境变量 UR10_WINDOWS_HOST_IP）。" >&2
  exit 2
fi

if [[ ! -d "${WS_ROOT}" ]]; then
  echo "[ERROR] 找不到工作空间: ${WS_ROOT}" >&2
  exit 2
fi

RUN_SCRIPT="${WS_ROOT}/src/ur10_real_comm/scripts/run_full_verify.sh"
if [[ ! -x "${RUN_SCRIPT}" ]]; then
  echo "[ERROR] 找不到可执行脚本: ${RUN_SCRIPT}" >&2
  exit 2
fi

if [[ ! "${ROBOT_SUBNET}" =~ ^([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/(1?[0-9]|2[0-9]|3[0-2])$ ]]; then
  echo "[ERROR] --robot-subnet 格式错误，如 192.168.56.0/24" >&2
  exit 2
fi

ip_to_int() {
  local ip="$1"
  local a b c d
  IFS='.' read -r a b c d <<<"${ip}"
  if [[ -z "${a}" || -z "${b}" || -z "${c}" || -z "${d}" ]]; then
    return 1
  fi
  echo $(( (a << 24) + (b << 16) + (c << 8) + d ))
}

in_same_subnet() {
  local ip1 ip2 prefix
  local a b mask
  ip1="$1"
  ip2="$2"
  prefix="$3"
  if ! a=$(ip_to_int "$ip1"); then return 1; fi
  if ! b=$(ip_to_int "$ip2"); then return 1; fi
  if (( prefix < 1 || prefix > 32 )); then return 1; fi
  mask=$(( 0xFFFFFFFF << (32 - prefix) ))
  mask=$(( mask & 0xFFFFFFFF ))
  if (( (a & mask) == (b & mask) )); then
    return 0
  fi
  return 1
}

if ! in_same_subnet "${HOST_IP}" "${ROBOT_IP}" "${ROBOT_SUBNET##*/}"; then
  echo "[WARN] HOST_IP=${HOST_IP} 与 ROBOT_IP=${ROBOT_IP} 不在同一网段 ${ROBOT_SUBNET}，请确认你的网络设置。" >&2
fi

WSL_IP=$(hostname -I | awk '{print $1}')
DEFAULT_ROUTE_IFACE=$(ip route | awk '/default/ {print $5; exit}')
DEFAULT_GATEWAY=$(ip route | awk '/default/ {print $3; exit}')

if [[ -z "${WSL_IP}" ]]; then
  echo "[WARN] 获取不到 WSL IP，仍继续（若你为路由/网关模式可忽略）。" >&2
fi

if ! command -v ping >/dev/null 2>&1; then
  echo "[WARN] 缺少 ping 工具，跳过连通性检查。"
else
  if ! ping -c 1 -W 2 "${ROBOT_IP}" >/tmp/ur10_ping_check.log 2>&1; then
    echo "[WARN] ping ${ROBOT_IP} 失败，建议先确认网线/网段/URCap回连状态。" >&2
  fi
fi

echo "[INFO] WSL2环境摘要"
echo "  工作空间: ${WS_ROOT}"
echo "  HOST_IP: ${HOST_IP}"
echo "  ROBOT_IP: ${ROBOT_IP}"
echo "  ROBOT_SUBNET: ${ROBOT_SUBNET}"
echo "  WSL_IP: ${WSL_IP:-<unknown>}"
echo "  WSL默认网关: ${DEFAULT_GATEWAY:-<none>}"
echo "  默认网卡: ${DEFAULT_ROUTE_IFACE:-<none>}"
echo "  WRIST3_DELTA: ${WRIST3_DELTA}"
echo "  CONTROLLER: ${CONTROLLER}"
echo "  LAUNCH_RVIZ: ${LAUNCH_RVIZ}"
echo "  CONFIRM_EXECUTE: ${CONFIRM_EXECUTE}"
echo "  STATUS_TIMEOUT_SEC: ${STATUS_TIMEOUT}"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[INFO] DRY-RUN: 不执行，打印将要运行的命令"
  echo "( cd "${WS_ROOT}/src/ur10_real_comm/scripts" && \
  ROBOT_IP="${ROBOT_IP}" \
  REVERSE_IP="${HOST_IP}" \
  WRIST3_DELTA_DEG="${WRIST3_DELTA}" \
  CONFIRM_EXECUTE="${CONFIRM_EXECUTE}" \
  LAUNCH_RVIZ="${LAUNCH_RVIZ}" \
  INITIAL_JOINT_CONTROLLER="${CONTROLLER}" \
  STATUS_TIMEOUT_SEC="${STATUS_TIMEOUT}" \
  bash ./run_full_verify.sh )"
  exit 0
fi
cd "${WS_ROOT}"
source /opt/ros/humble/setup.bash
if [[ -f "${WS_ROOT}/install/setup.bash" ]]; then
  source "${WS_ROOT}/install/setup.bash"
fi

echo "[INFO] 启动 run_full_verify.sh ..."
( cd "${WS_ROOT}/src/ur10_real_comm/scripts" &&   ROBOT_IP="${ROBOT_IP}"   REVERSE_IP="${HOST_IP}"   WRIST3_DELTA_DEG="${WRIST3_DELTA}"   CONFIRM_EXECUTE="${CONFIRM_EXECUTE}"   LAUNCH_RVIZ="${LAUNCH_RVIZ}"   INITIAL_JOINT_CONTROLLER="${CONTROLLER}"   STATUS_TIMEOUT_SEC="${STATUS_TIMEOUT}"   bash ./run_full_verify.sh )

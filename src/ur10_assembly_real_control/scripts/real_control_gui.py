#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import psutil
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


TOKEN_LABELS = {
    "WSL_50002_LISTENING": "WSL 50002",
    "WSL_MOTION_PORTS_LISTENING": "WSL 运动端口",
    "WINDOWS_PORTPROXY_OK": "Windows portproxy",
    "WINDOWS_50002_LISTENING": "Windows 50002",
    "WINDOWS_MOTION_PORTS_LISTENING": "Windows 运动端口",
    "JOINT_STATES_OK": "/joint_states",
    "CONTROLLER_ACTIVE": "scaled 控制器",
    "ACTION_ONLINE": "执行 action",
    "SPEED_SCALING_NONZERO": "速度缩放",
    "RTDE_OK": "RTDE 链路",
    "READY_FOR_RVIZ2_MOVEIT_EXECUTION": "MoveIt 执行就绪",
}

HARD_REQUIREMENT_TOKENS = (
    "WSL_50002_LISTENING",
    "WSL_MOTION_PORTS_LISTENING",
    "WINDOWS_PORTPROXY_OK",
    "WINDOWS_50002_LISTENING",
    "JOINT_STATES_OK",
    "CONTROLLER_ACTIVE",
    "ACTION_ONLINE",
    "SPEED_SCALING_NONZERO",
    "RTDE_OK",
)

READY_FALLBACK_TOKENS = (
    "JOINT_STATES_OK",
    "CONTROLLER_ACTIVE",
    "ACTION_ONLINE",
    "SPEED_SCALING_NONZERO",
    "RTDE_OK",
    "WINDOWS_PORTPROXY_OK",
    "WINDOWS_50002_LISTENING",
    "WSL_MOTION_PORTS_LISTENING",
)

RTDE_OVERFLOW_MARKERS = (
    "pipeline producer overflowed",
    "rtde data pipeline",
)

WINDOWS_MOTION_WARN_TOKENS = (
    "WINDOWS_MOTION_PORTS_NOT_LISTENING",
    "WINDOWS_PORT_50001_NOT_LISTENING",
    "WINDOWS_PORT_50003_NOT_LISTENING",
    "WINDOWS_PORT_50004_NOT_LISTENING",
)

SCRIPT_SENDER_PORT = 50002
MOTION_PORTS = (50001, 50003, 50004)
REQUIRED_WINDOWS_PORTS = (50001, 50002, 50003, 50004)

QT_CHILD_ENV_KEYS = (
    "QT_PLUGIN_PATH",
    "QT_QPA_PLATFORM_PLUGIN_PATH",
)

KILL_PATTERNS = [
    "ur_ros2_control_node",
    "ur_robot_driver",
    "dashboard_client",
    "controller_stopper_node",
    "robot_state_helper",
    "urscript_interface",
    "trajectory_until_node",
    "controller_manager ros2_control_node",
    "controller_manager/spawner",
    " spawner ",
    "move_group",
    "rviz2",
    "robot_state_publisher",
    "ros2 launch ur_robot_driver",
    "ros2 launch ur10_assembly_real_control ur10_assembly_real.launch.py",
]

EXEC_STATE_IDLE = "IDLE"
EXEC_STATE_EXECUTING = "EXECUTING"
EXEC_STATE_EXECUTION_ERROR = "EXECUTION_ERROR"
EXEC_STATE_EXECUTION_DONE = "EXECUTION_DONE"
SESSION_REPORT_SUFFIX = "session_diagnostics"


def _clean_ros_child_env() -> Dict[str, str]:
    env = os.environ.copy()
    for key in QT_CHILD_ENV_KEYS:
        env.pop(key, None)
    return env


def _contains_rtde_overflow(text: str) -> bool:
    lowered = text.lower()
    return (
        any(marker in lowered for marker in RTDE_OVERFLOW_MARKERS)
        or ("rtde" in lowered and "overflowed" in lowered)
    )


def _qt_plugin_fix() -> None:
    try:
        from PyQt5 import QtCore

        plugins = Path(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.PluginsPath))
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugins))
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(plugins / "platforms"))
    except Exception:
        pass


def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        with open("/proc/version", "r", encoding="utf-8", errors="ignore") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def _configure_qt_platform(args: argparse.Namespace) -> None:
    if args.qt_platform:
        os.environ["QT_QPA_PLATFORM"] = args.qt_platform
        return
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    # Under WSL GUI stacks, forcing xcb is usually more reliable than implicit wayland.
    if _is_wsl() and os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def _cleanup_stale_gui_instances() -> int:
    current = os.getpid()
    killed = 0
    targets = []
    script_name = "real_control_gui.py"
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            pid = proc.info["pid"]
            if pid == current:
                continue
            cmd = proc.info.get("cmdline") or []
            if not cmd:
                continue
            exe = os.path.basename(cmd[0]).lower()
            if "python" not in exe:
                continue
            # Only target real python-script instances, not parent shells containing text snippets.
            if any(os.path.basename(arg) == script_name for arg in cmd[1:]):
                targets.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    for proc in targets:
        try:
            proc.terminate()
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _, alive = psutil.wait_procs(targets, timeout=2.0)
    for proc in alive:
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


class ManagedProcess:
    def __init__(self, name: str, cmd: str, log_queue: "queue.Queue[str]") -> None:
        self.name = name
        self.cmd = cmd
        self.log_queue = log_queue
        self.proc: Optional[subprocess.Popen[str]] = None

    def start(self) -> None:
        if self.is_running():
            self.log_queue.put(f"[{self.name}] already running")
            return
        self.log_queue.put(f"[{self.name}] START")
        self.proc = subprocess.Popen(
            ["bash", "-lc", self.cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=_clean_ros_child_env(),
            preexec_fn=os.setsid,
        )
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        assert self.proc is not None
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self.log_queue.put(f"[{self.name}] {line.rstrip()}")
        code = self.proc.wait()
        self.log_queue.put(f"[{self.name}] EXIT code={code}")

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def terminate(self) -> None:
        if not self.is_running() or self.proc is None:
            return
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
        except Exception:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def kill(self) -> None:
        if not self.is_running() or self.proc is None:
            return
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


class MainWindow(QMainWindow):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()
        self.setWindowTitle("UR10 External Control 实机启动面板")
        self.resize(1180, 760)

        self.workspace = Path(args.workspace).expanduser().resolve()
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.processes: Dict[str, ManagedProcess] = {}
        self.ready = False
        self.moveit_launch_ok = False
        self.token_labels: Dict[str, QLabel] = {}
        self.exec_state = EXEC_STATE_IDLE
        self._exec_diag_stop = threading.Event()
        self._exec_diag_thread: Optional[threading.Thread] = None
        self._last_exec_snapshot_ts = 0.0
        self._tf_tree_split_warned = False
        self.rtde_ok = True
        self._rtde_overflow_warned = False
        self._recent_logs: deque[str] = deque(maxlen=260)
        self._active_exec_report: Optional[Path] = None
        self._capture_lock = threading.Lock()
        self._capture_inflight = False
        self._last_capture_ts: Dict[str, float] = {}
        self.error_logs_dir = self.workspace / "src" / "ur10_assembly_real_control" / "docs" / "error_logs"
        self.error_logs_dir.mkdir(parents=True, exist_ok=True)
        self.session_started_at = datetime.now()
        self._session_report_path = self.error_logs_dir / (
            f"{self.session_started_at.strftime('%Y%m%d_%H%M%S')}_{SESSION_REPORT_SUFFIX}.md"
        )
        self._latest_preflight_output = ""
        self._latest_verify_output = ""
        self._runtime_findings: List[str] = []
        self._runtime_finding_dedup: Dict[str, float] = {}
        self._export_inflight = False

        self._build_ui(args)

        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self._drain_logs)
        self.log_timer.start(100)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._refresh_process_status)
        self.status_timer.start(500)

        self._log("[init] GUI ready. 正式姿态来源: ur_robot_driver /joint_states")
        self._log(f"[init] session report path: {self._session_report_path}")

    def _build_ui(self, args: argparse.Namespace) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        cfg = QGroupBox("连接配置")
        grid = QGridLayout(cfg)
        self.robot_ip = QLineEdit(args.robot_ip)
        self.external_host_ip = QLineEdit(args.external_host_ip)
        self.script_sender_port = QLineEdit(str(args.script_sender_port))
        self.workspace_edit = QLineEdit(str(self.workspace))
        grid.addWidget(QLabel("UR10 IP"), 0, 0)
        grid.addWidget(self.robot_ip, 0, 1)
        grid.addWidget(QLabel("External Host IP"), 0, 2)
        grid.addWidget(self.external_host_ip, 0, 3)
        grid.addWidget(QLabel("External Port"), 1, 0)
        grid.addWidget(self.script_sender_port, 1, 1)
        grid.addWidget(QLabel("Workspace"), 1, 2)
        grid.addWidget(self.workspace_edit, 1, 3)
        root.addWidget(cfg)

        controls = QGroupBox("启动流程")
        h = QHBoxLayout(controls)
        self.btn_preflight = QPushButton("启动前完整检验")
        self.btn_start_driver = QPushButton("1 启动监听节点 / Driver")
        self.btn_verify = QPushButton("验证连接与控制器")
        self.btn_diagnose = QPushButton("诊断执行状态")
        self.btn_start_moveit = QPushButton("2 启动 RViz2 + MoveIt2")
        self.btn_export_report = QPushButton("导出总分析报告")
        self.btn_kill = QPushButton("3 杀死所有相关进程")
        self.btn_preflight.clicked.connect(self.run_preflight)
        self.btn_start_driver.clicked.connect(self.start_driver)
        self.btn_verify.clicked.connect(self.verify_ready)
        self.btn_diagnose.clicked.connect(self.diagnose_execute)
        self.btn_start_moveit.clicked.connect(self.start_moveit)
        self.btn_export_report.clicked.connect(self.export_session_report)
        self.btn_kill.clicked.connect(self.kill_all)
        h.addWidget(self.btn_preflight)
        h.addWidget(self.btn_start_driver)
        h.addWidget(self.btn_verify)
        h.addWidget(self.btn_diagnose)
        h.addWidget(self.btn_start_moveit)
        h.addWidget(self.btn_export_report)
        h.addWidget(self.btn_kill)
        root.addWidget(controls)

        status_box = QGroupBox("就绪状态")
        status_grid = QGridLayout(status_box)
        for col, (token, label) in enumerate(TOKEN_LABELS.items()):
            name = QLabel(label)
            value = QLabel("未验证")
            value.setAlignment(Qt.AlignCenter)
            value.setAutoFillBackground(True)
            self._set_label_color(value, "#777777")
            status_grid.addWidget(name, 0, col)
            status_grid.addWidget(value, 1, col)
            self.token_labels[token] = value
        root.addWidget(status_box)

        self.process_status = QLabel("Driver: stopped | MoveIt/RViz: stopped")
        root.addWidget(self.process_status)

        notes = QLabel(
            "操作顺序: 启动监听节点 -> 示教器点击运行 External Control -> 验证 READY -> 启动 RViz2/MoveIt2 -> 小范围 Plan/Execute。"
            " 若 RTDE_OVERFLOW 但 controller/action/speed 已通过，可启动 RViz2/MoveIt2 做查看和 Plan，但不要 Execute。"
            " 执行“导出总分析报告”后会将本会话总诊断写入 docs/error_logs。"
        )
        notes.setWordWrap(True)
        root.addWidget(notes)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        root.addWidget(self.log_box, stretch=1)

    def _set_label_color(self, label: QLabel, color: str) -> None:
        pal = label.palette()
        pal.setColor(label.backgroundRole(), QColor(color))
        pal.setColor(label.foregroundRole(), QColor("#ffffff"))
        label.setPalette(pal)

    def _source_prefix(self) -> str:
        ws = self.workspace_edit.text().strip() or str(self.workspace)
        return (
            f"cd {self._shell_quote(ws)} && "
            "unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH && "
            "source /opt/ros/humble/setup.bash && "
            "source install/setup.bash"
        )

    @staticmethod
    def _shell_quote(text: str) -> str:
        return "'" + text.replace("'", "'\"'\"'") + "'"

    def _driver_cmd(self) -> str:
        robot_ip = self.robot_ip.text().strip()
        external_host_ip = self.external_host_ip.text().strip()
        return (
            f"{self._source_prefix()} && "
            "driver_prefix=$(ros2 pkg prefix ur_robot_driver) && "
            'echo "DRIVER_PREFIX=${driver_prefix}" && '
            'case "${driver_prefix}" in /opt/ros/humble*) ;; *) '
            'echo "DRIVER_PREFIX_NOT_OPT_ROS_HUMBLE"; exit 42;; esac && '
            "ros2 launch ur_robot_driver ur_control.launch.py "
            "ur_type:=ur10 "
            f"robot_ip:={robot_ip} "
            "use_fake_hardware:=false "
            "launch_rviz:=false "
            "description_package:=ur10_assembly_real_control "
            "description_file:=assembly_real.urdf.xacro "
            "kinematics_params_file:=/root/ur10_ws/src/ur10_assembly_real_control/config/ur10/default_kinematics.yaml "
            "headless_mode:=false "
            "launch_dashboard_client:=true "
            f"reverse_ip:={external_host_ip} "
            "reverse_port:=50001 "
            "script_sender_port:=50002 "
            "trajectory_port:=50003 "
            "script_command_port:=50004 "
            "initial_joint_controller:=scaled_joint_trajectory_controller "
            "activate_joint_controller:=true"
        )

    def _moveit_cmd(self) -> str:
        robot_ip = self.robot_ip.text().strip()
        return (
            f"{self._source_prefix()} && "
            'echo "[moveit] preserving official driver robot_state_publisher; MoveIt uses matching assembly_real robot_description." && '
            'echo "[moveit] official UR joint names are required: shoulder_pan_joint ... wrist_3_joint." && '
            'echo "[moveit] MoveIt collision checks will be disabled through SRDF and /apply_planning_scene ACM; UR controller safety is not bypassed." && '
            'echo "[moveit] current RSP processes:" && '
            "pgrep -a robot_state_publisher 2>/dev/null || echo '(none)' && "
            "ros2 launch ur10_assembly_real_control ur10_assembly_real.launch.py "
            f"robot_ip:={robot_ip} "
            "ur_type:=ur10 "
            "launch_driver:=false "
            "launch_rsp:=false "
            "launch_rviz:=true"
        )

    def _diagnose_execute_cmd(self) -> str:
        script = r'''
set +e
echo "=== 1. JOINT STATES ==="
timeout 5s ros2 topic echo /joint_states --once 2>/dev/null || echo "JOINT_STATES_FAIL"

echo "=== 2. SPEED SCALING ==="
timeout 5s ros2 topic echo /speed_scaling_state_broadcaster/speed_scaling --once 2>/dev/null || echo "SPEED_SCALING_FAIL"

echo "=== 3. CONTROLLER LIST ==="
timeout 5s ros2 control list_controllers 2>/dev/null || echo "CONTROLLER_LIST_FAIL"

echo "=== 4. CONTROLLER STATE ==="
timeout 3s ros2 topic echo /scaled_joint_trajectory_controller/state --once 2>/dev/null || echo "CONTROLLER_STATE_FAIL"

echo "=== 5. ACTION INFO ==="
ros2 action info /scaled_joint_trajectory_controller/follow_joint_trajectory 2>/dev/null || echo "ACTION_INFO_FAIL"

echo "=== 6. TF FRAMES FROM base_jizuo ==="
timeout 3s ros2 run tf2_ros tf2_echo base_jizuo sensor_shovel_tcp 2>/dev/null &
TF_PID=$!
sleep 1
kill $TF_PID 2>/dev/null
wait $TF_PID 2>/dev/null
echo "TF_CHECK_DONE"

echo "=== 7. ROBOT MODE ==="
timeout 5s ros2 service call /dashboard_client/robot_mode ur_dashboard_msgs/srv/GetRobotMode 2>/dev/null || echo "ROBOT_MODE_FAIL"

echo "=== 8. SAFETY MODE ==="
timeout 5s ros2 service call /dashboard_client/safety_mode ur_dashboard_msgs/srv/GetSafetyMode 2>/dev/null || echo "SAFETY_MODE_FAIL"

echo "=== DIAGNOSE_DONE ==="
'''
        return f"{self._source_prefix()} && bash -lc {self._shell_quote(script)}"

    def _runtime_exec_diag_cmd(self) -> str:
        script = r'''
set +e
echo "=== EXEC_RUNTIME_SNAPSHOT ==="
ctrl="$(timeout 2s ros2 control list_controllers 2>/dev/null | sed -r 's/\x1B\[[0-9;]*[mK]//g')"
if echo "$ctrl" | grep -Eq '^scaled_joint_trajectory_controller[[:space:]].*[[:space:]]active[[:space:]]*$'; then
  echo "RUNTIME_CONTROLLER_SCALED=active"
else
  state="$(printf '%s\n' "$ctrl" | awk '/^scaled_joint_trajectory_controller[[:space:]]/ {print $NF; exit}')"
  echo "RUNTIME_CONTROLLER_SCALED=${state:-missing}"
fi
speed_msg="$(timeout 2s ros2 topic echo /speed_scaling_state_broadcaster/speed_scaling --once 2>/dev/null)"
speed_value="$(printf '%s\n' "$speed_msg" | awk '/data:/ {print $2; exit}')"
if [ -n "$speed_value" ]; then
  echo "RUNTIME_SPEED_SCALING=$speed_value"
  if awk "BEGIN {exit !($speed_value > 0.01)}"; then
    echo "SPEED_SCALING_NONZERO"
  else
    echo "SPEED_SCALING_LOW_OR_ZERO"
  fi
else
  echo "RUNTIME_SPEED_SCALING=missing"
  echo "SPEED_SCALING_LOW_OR_ZERO"
fi
action_info="$(timeout 2s ros2 action info /scaled_joint_trajectory_controller/follow_joint_trajectory 2>/dev/null)"
if printf '%s\n' "$action_info" | grep -q 'Action servers:'; then
  echo "RUNTIME_ACTION_ONLINE=true"
else
  echo "RUNTIME_ACTION_ONLINE=false"
fi
'''
        return f"{self._source_prefix()} && bash -lc {self._shell_quote(script)}"

    def _auto_capture_cmd(self) -> str:
        script = r'''
set +e
echo "=== AUTO_EXECUTE_CAPTURE_BEGIN ==="
date -Iseconds
echo "=== ROS2 NODE LIST ==="
timeout 6s ros2 node list 2>/dev/null || echo "NODE_LIST_FAIL"

echo "=== ROS2 TOPIC LIST (key filters) ==="
timeout 6s ros2 topic list 2>/dev/null | grep -E '/joint_states$|/scaled_joint_trajectory_controller|/speed_scaling|/tf$|/tf_static$' || true

echo "=== ROS2 SERVICE LIST (key filters) ==="
timeout 6s ros2 service list 2>/dev/null | grep -E 'controller_manager|dashboard_client|move_group|planning_scene' || true

echo "=== ROS2 ACTION LIST ==="
timeout 6s ros2 action list 2>/dev/null || echo "ACTION_LIST_FAIL"

echo "=== ACTION INFO: scaled follow_joint_trajectory ==="
timeout 6s ros2 action info /scaled_joint_trajectory_controller/follow_joint_trajectory 2>/dev/null || echo "ACTION_INFO_FAIL"

echo "=== CONTROLLER LIST ==="
timeout 6s ros2 control list_controllers 2>/dev/null || echo "CONTROLLER_LIST_FAIL"

echo "=== SPEED SCALING SAMPLE ==="
timeout 4s ros2 topic echo /speed_scaling_state_broadcaster/speed_scaling --once 2>/dev/null || echo "SPEED_SCALING_SAMPLE_FAIL"

echo "=== SCALED CONTROLLER STATE SAMPLE ==="
timeout 4s ros2 topic echo /scaled_joint_trajectory_controller/controller_state --once 2>/dev/null || \
timeout 4s ros2 topic echo /scaled_joint_trajectory_controller/state --once 2>/dev/null || \
echo "CONTROLLER_STATE_SAMPLE_FAIL"

echo "=== ROBOT MODE / SAFETY MODE ==="
timeout 5s ros2 service call /dashboard_client/robot_mode ur_dashboard_msgs/srv/GetRobotMode 2>/dev/null || echo "ROBOT_MODE_FAIL"
timeout 5s ros2 service call /dashboard_client/safety_mode ur_dashboard_msgs/srv/GetSafetyMode 2>/dev/null || echo "SAFETY_MODE_FAIL"

echo "=== SOCKET LISTEN/CONNECTIONS 50001-50004 ==="
ss -lntp | grep -E ':5000(1|2|3|4)' || echo "NO_5000X_LISTENING"
ss -tnp | grep -E ':5000(1|2|3|4)' || echo "NO_5000X_CONNECTIONS"

echo "=== PROCESS SNAPSHOT (driver/moveit/rviz/controller) ==="
ps -eo pid,cmd --sort=-pid | grep -E 'ur_ros2_control_node|ur_robot_driver|move_group|rviz2|controller_manager|dashboard_client|urscript_interface|trajectory_until_node' | grep -v grep || true

echo "=== RECENT ROS LOG HINTS ==="
find "$HOME/.ros/log" -maxdepth 3 -type f -name '*.log' -mmin -20 -print0 2>/dev/null | \
  xargs -0 -r grep -IhE 'RTDE|overflow|reverse interface|Connection attempt on port 50003|Cannot push a new trajectory|Goal request accepted|MoveGroupInterface::move' 2>/dev/null | \
  tail -n 80 || true
echo "=== AUTO_EXECUTE_CAPTURE_END ==="
'''
        return f"{self._source_prefix()} && bash -lc {self._shell_quote(script)}"

    def _new_report_path(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.error_logs_dir / f"{stamp}_execute_capture.md"

    def _append_report(self, path: Path, text: str) -> None:
        with self._capture_lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(text)

    def _start_execute_auto_capture(self, trigger: str, msg: str, force_new: bool = False) -> None:
        now = time.time()
        if now - self._last_capture_ts.get(trigger, 0.0) < 2.0:
            return
        self._last_capture_ts[trigger] = now
        if self._capture_inflight and not force_new:
            return
        if force_new or self._active_exec_report is None:
            self._active_exec_report = self._new_report_path()
            header = (
                f"# Execute 自动诊断报告\n\n"
                f"- 生成时间: {datetime.now().isoformat(timespec='seconds')}\n"
                f"- 触发事件: `{trigger}`\n"
                f"- ExecState: `{self.exec_state}`\n"
                f"- READY: `{self.ready}`\n"
                f"- RTDE: `{'OK' if self.rtde_ok else 'RTDE_OVERFLOW'}`\n"
                f"- Workspace: `{self.workspace}`\n\n"
                f"## 触发日志\n\n```\n{msg}\n```\n\n"
                f"## 触发前 GUI 近期日志\n\n```\n" + "\n".join(self._recent_logs) + "\n```\n\n"
            )
            self._append_report(self._active_exec_report, header)
        report_path = self._active_exec_report
        assert report_path is not None
        self._capture_inflight = True
        self._log(f"[execdiag] AUTO_CAPTURE_TRIGGER={trigger}")

        def worker() -> None:
            try:
                try:
                    result = subprocess.run(
                        ["bash", "-lc", self._auto_capture_cmd()],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        env=_clean_ros_child_env(),
                        timeout=45,
                    )
                    output = result.stdout or ""
                except subprocess.TimeoutExpired as exc:
                    output = (exc.stdout or "") + "\nAUTO_CAPTURE_TIMEOUT\n"
                section = (
                    f"## 捕获片段 `{trigger}` @ {datetime.now().isoformat(timespec='seconds')}\n\n"
                    f"### GUI状态\n\n"
                    f"- ExecState: `{self.exec_state}`\n"
                    f"- READY: `{self.ready}`\n"
                    f"- MOVEIT_LAUNCH_OK: `{self.moveit_launch_ok}`\n"
                    f"- RTDE: `{'OK' if self.rtde_ok else 'RTDE_OVERFLOW'}`\n\n"
                    f"### 自动诊断输出\n\n```text\n{output.rstrip()}\n```\n\n"
                )
                self._append_report(report_path, section)
                self.log_queue.put(f"[execdiag] AUTO_CAPTURE_SAVED={report_path}")
            finally:
                self._capture_inflight = False

        threading.Thread(target=worker, daemon=True).start()

    def _verify_cmd(self) -> str:
        port = self.script_sender_port.text().strip()
        external_host_ip = self.external_host_ip.text().strip()
        required_ports = " ".join(str(p) for p in REQUIRED_WINDOWS_PORTS)
        motion_ports = " ".join(str(p) for p in MOTION_PORTS)
        script = f"""
set +e
echo "=== DRIVER PREFIX ==="
ros2 pkg prefix ur_robot_driver

echo "=== WSL2 NETWORK CHECK ==="
wsl_ip="$(hostname -I | awk '{{print $1}}')"
echo "WSL2_IP=${{wsl_ip}}"
if ss -lntp | grep -q ':{port}'; then
  echo WSL_50002_LISTENING
else
  echo WSL_50002_NOT_LISTENING
fi
wsl_motion_ok=1
for p in {motion_ports}; do
  if ss -lntp | grep -q ":${{p}}"; then
    echo "WSL_PORT_${{p}}_LISTENING"
  else
    echo "WSL_PORT_${{p}}_NOT_LISTENING"
    wsl_motion_ok=0
  fi
done
if [ "$wsl_motion_ok" -eq 1 ]; then
  echo WSL_MOTION_PORTS_LISTENING
else
  echo WSL_MOTION_PORTS_NOT_LISTENING
fi

echo "=== WINDOWS PORTPROXY CHECK ==="
ps_exe="$(command -v powershell.exe 2>/dev/null)"
if [ -z "$ps_exe" ] && [ -x /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe ]; then
  ps_exe=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
fi
if [ -n "$ps_exe" ]; then
  echo "POWERSHELL_EXE=$ps_exe"
  ps_out="$("$ps_exe" -NoProfile -ExecutionPolicy Bypass -Command "netsh interface portproxy show all; Write-Output '---NETSTAT---'; netstat -ano | Select-String '50001|50002|50003|50004'" 2>&1 | tr -d '\\r')"
  echo "$ps_out"
  proxy_ok=1
  win_listen_ok=1
  for p in {required_ports}; do
    if echo "$ps_out" | grep -Eq "{external_host_ip}[[:space:]]+${{p}}[[:space:]]+${{wsl_ip}}[[:space:]]+${{p}}"; then
      echo "WINDOWS_PORTPROXY_${{p}}_OK"
    else
      echo "WINDOWS_PORTPROXY_${{p}}_MISSING"
      proxy_ok=0
    fi
    if echo "$ps_out" | grep -Eq "{external_host_ip}:${{p}}[[:space:]].*LISTENING"; then
      echo "WINDOWS_PORT_${{p}}_LISTENING"
    else
      echo "WINDOWS_PORT_${{p}}_NOT_LISTENING"
      win_listen_ok=0
    fi
  done
  if [ "$proxy_ok" -eq 1 ]; then
    echo WINDOWS_PORTPROXY_OK
  else
    echo WINDOWS_PORTPROXY_MISSING
    echo "POWERSHELL_FIX_PORTPROXY:"
    echo "  Restart-Service iphlpsvc -Force"
    for p in {required_ports}; do
      echo "  netsh interface portproxy delete v4tov4 listenaddress={external_host_ip} listenport=${{p}}"
      echo "  netsh interface portproxy add v4tov4 listenaddress={external_host_ip} listenport=${{p}} connectaddress=${{wsl_ip}} connectport=${{p}}"
    done
    echo "  Restart-Service iphlpsvc -Force"
  fi
  if echo "$ps_out" | grep -Eq "{external_host_ip}:{port}[[:space:]].*LISTENING"; then
    echo WINDOWS_50002_LISTENING
  else
    echo WINDOWS_50002_NOT_LISTENING
  fi
  if [ "$win_listen_ok" -eq 1 ]; then
    echo WINDOWS_MOTION_PORTS_LISTENING
  else
    echo WINDOWS_MOTION_PORTS_NOT_LISTENING
    echo "POWERSHELL_CHECK_NETSTAT: netstat -ano | Select-String '50001|50002|50003|50004'"
  fi
else
  echo WINDOWS_POWERSHELL_UNAVAILABLE
  echo "Cannot run powershell.exe from WSL. Manually check Windows PowerShell:"
  echo "  netsh interface portproxy show all"
  echo "  netstat -ano | Select-String '50001|50002|50003|50004'"
fi

echo "=== SCALED CONTROLLER AUTO-ACTIVATE ==="
ctrl_before="$(timeout 5s ros2 control list_controllers 2>/dev/null)"
echo "$ctrl_before"
ctrl_before_clean="$(printf '%s\n' "$ctrl_before" | sed -r 's/\x1B\[[0-9;]*[mK]//g')"
if echo "$ctrl_before_clean" | grep -Eq '^scaled_joint_trajectory_controller[[:space:]].*[[:space:]]active[[:space:]]*$'; then
  echo SCALED_ALREADY_ACTIVE
else
  echo SWITCH_SCALED_ATTEMPTED
  timeout 10s ros2 control switch_controllers --activate scaled_joint_trajectory_controller --strict
  switch_code=$?
  if [ "$switch_code" -ne 0 ]; then
    echo "SWITCH_SCALED_FAILED_CODE=${{switch_code}}"
    echo LOAD_SCALED_ATTEMPTED
    timeout 10s ros2 control load_controller --set-state active scaled_joint_trajectory_controller
  fi
fi

echo "=== REAL MOTION STATE CHECK ==="
speed_topic="$(timeout 5s ros2 topic list 2>/dev/null | grep -E '/speed_scaling_state_broadcaster/speed_scaling$|/speed_scaling$' | head -1)"
if [ -n "$speed_topic" ]; then
  echo "SPEED_SCALING_TOPIC=${{speed_topic}}"
  speed_msg="$(timeout 5s ros2 topic echo "$speed_topic" --once 2>/dev/null)"
  echo "$speed_msg"
  speed_value="$(printf '%s\n' "$speed_msg" | awk '/data:/ {{print $2; exit}}')"
  if awk "BEGIN {{exit !(${{speed_value:-0}} > 0.01)}}"; then
    echo SPEED_SCALING_NONZERO
  else
    echo SPEED_SCALING_ZERO_OR_MISSING
    echo "CHECK_TEACH_PENDANT: External Control program must be running and speed slider must be above 0%."
  fi
else
  echo SPEED_SCALING_TOPIC_MISSING
fi

echo "=== DRIVER MOTION SOCKETS ==="
ss -tnp | grep -E ':5000(1|3|4)' || true
echo "=== SCALED CONTROLLER STATE SAMPLE ==="
timeout 3s ros2 topic echo /scaled_joint_trajectory_controller/state --once || true

echo "=== RTDE OVERFLOW CHECK ==="
rtde_hits="$(
  {{
    find "$HOME/.ros/log" -maxdepth 3 -type f -name '*.log' -mmin -30 -print0 2>/dev/null \
      | xargs -0 -r grep -IhE 'Pipeline producer overflowed|RTDE Data Pipeline|RTDE.*overflowed|overflowed.*RTDE' 2>/dev/null
  }} | grep -E 'Pipeline producer overflowed|RTDE Data Pipeline|RTDE.*overflowed|overflowed.*RTDE' | tail -n 10
)"
if [ -n "$rtde_hits" ]; then
  echo "$rtde_hits"
  echo RTDE_OVERFLOW
  echo "NOT_READY: RTDE realtime pipeline is unstable. Stop execution, restart driver, reduce diagnostics, and check WSL2/network/CPU/portproxy stability."
else
  echo RTDE_OK
fi

ros2 run ur10_assembly_real_control check_real_ur10_ready.sh
"""
        return f"{self._source_prefix()} && bash -lc {self._shell_quote(script)}"

    def _preflight_cmd(self) -> str:
        robot_ip = self.robot_ip.text().strip()
        ws = self.workspace_edit.text().strip() or str(self.workspace)
        script = f"""
set +e
echo "=== PREFLIGHT_BEGIN ==="
date -Iseconds
echo "PREFLIGHT_WORKSPACE={ws}"
if [ -d "{ws}" ]; then
  echo PREFLIGHT_WORKSPACE_OK
else
  echo PREFLIGHT_WORKSPACE_MISSING
fi
if [ -f "{ws}/install/setup.bash" ]; then
  echo PREFLIGHT_INSTALL_SETUP_OK
else
  echo PREFLIGHT_INSTALL_SETUP_MISSING
fi

echo "=== REQUIRED FILES ==="
for f in \\
  "{ws}/src/ur10_assembly_real_control/urdf/assembly_real.urdf.xacro" \\
  "{ws}/src/ur10_assembly_real_control/config/assembly_real.urdf.xacro" \\
  "{ws}/src/ur10_assembly_real_control/launch/ur10_assembly_real.launch.py" \\
  "{ws}/src/ur10_assembly_real_control/scripts/check_real_ur10_ready.sh"
do
  if [ -f "$f" ]; then
    echo "PREFLIGHT_FILE_OK $f"
  else
    echo "PREFLIGHT_FILE_MISSING $f"
  fi
done

echo "=== ROS PACKAGE PREFIX ==="
driver_prefix="$(ros2 pkg prefix ur_robot_driver 2>/dev/null)"
desc_prefix="$(ros2 pkg prefix ur_description 2>/dev/null)"
ctrl_prefix="$(ros2 pkg prefix ur10_assembly_real_control 2>/dev/null)"
echo "UR_DRIVER_PREFIX=${{driver_prefix}}"
echo "UR_DESCRIPTION_PREFIX=${{desc_prefix}}"
echo "UR10_CTRL_PREFIX=${{ctrl_prefix}}"
case "${{driver_prefix}}" in /opt/ros/humble*) echo PREFLIGHT_DRIVER_PREFIX_OK ;; *) echo PREFLIGHT_DRIVER_PREFIX_BAD ;; esac
if [ -n "${{desc_prefix}}" ]; then echo PREFLIGHT_UR_DESCRIPTION_OK; else echo PREFLIGHT_UR_DESCRIPTION_MISSING; fi
if [ -n "${{ctrl_prefix}}" ]; then echo PREFLIGHT_CTRL_PACKAGE_OK; else echo PREFLIGHT_CTRL_PACKAGE_MISSING; fi

echo "=== ROBOT IP PING ==="
if timeout 3s ping -c 1 -W 1 {robot_ip} >/dev/null 2>&1; then
  echo PREFLIGHT_ROBOT_PING_OK
else
  echo PREFLIGHT_ROBOT_PING_FAIL
fi

echo "=== PORT OCCUPANCY 50001-50004 ==="
ss -lntp | grep -E ':5000(1|2|3|4)' || echo "PREFLIGHT_NO_5000X_LISTENER"
foreign="$(ss -lntp | grep -E ':5000(1|2|3|4)' | grep -Ev 'ur_ros2_control|pid=' || true)"
if [ -n "$foreign" ]; then
  echo "$foreign"
  echo PREFLIGHT_PORT_CONFLICT
else
  echo PREFLIGHT_PORT_CONFLICT_NONE
fi

echo "=== POSSIBLE CONFLICT PROCESSES ==="
pgrep -a -f 'MATLAB|matlab|ur_rtde|rtde_control|rtde_receive|ExternalControl|external_control|urx|RoboDK|python.*rtde' || echo "PREFLIGHT_NO_EXTRA_CONTROL_CLIENT"

echo "=== ROS GRAPH QUICK CHECK ==="
timeout 4s ros2 node list 2>/dev/null | head -n 40 || echo "PREFLIGHT_NODE_LIST_FAIL"
timeout 4s ros2 action list 2>/dev/null | head -n 40 || echo "PREFLIGHT_ACTION_LIST_FAIL"

echo "=== PREFLIGHT_END ==="
"""
        return f"{self._source_prefix()} && bash -lc {self._shell_quote(script)}"

    def _record_finding(self, code: str, detail: str, severity: str = "WARN") -> None:
        now = time.time()
        if now - self._runtime_finding_dedup.get(code, 0.0) < 5.0:
            return
        self._runtime_finding_dedup[code] = now
        stamp = datetime.now().strftime("%H:%M:%S")
        self._runtime_findings.append(f"[{stamp}] [{severity}] {code}: {detail}")
        if len(self._runtime_findings) > 220:
            self._runtime_findings = self._runtime_findings[-220:]

    def _token_snapshot_md(self) -> str:
        lines = []
        for token, label in self.token_labels.items():
            lines.append(f"- {token}: `{label.text()}`")
        return "\n".join(lines)

    def _write_session_report(self, reason: str) -> Path:
        execute_reports = sorted(self.error_logs_dir.glob("*_execute_capture.md"))
        execute_report_paths = [str(p) for p in execute_reports[-12:]]
        findings = self._runtime_findings or ["(none)"]
        body = (
            f"# UR10 实机 GUI 总分析报告\n\n"
            f"- 生成时间: {datetime.now().isoformat(timespec='seconds')}\n"
            f"- Session 起始: {self.session_started_at.isoformat(timespec='seconds')}\n"
            f"- 导出原因: `{reason}`\n"
            f"- Workspace: `{self.workspace}`\n"
            f"- Robot IP: `{self.robot_ip.text().strip()}`\n"
            f"- External Host IP: `{self.external_host_ip.text().strip()}`\n"
            f"- ExecState: `{self.exec_state}`\n"
            f"- READY: `{self.ready}`\n"
            f"- MoveItLaunchOK: `{self.moveit_launch_ok}`\n"
            f"- RTDE: `{'OK' if self.rtde_ok else 'RTDE_OVERFLOW'}`\n\n"
            f"## 1) 启动前检验状态\n\n"
            f"{self._token_snapshot_md()}\n\n"
            f"## 2) 关键运行发现\n\n"
            + "\n".join(f"- {item}" for item in findings)
            + "\n\n"
            f"## 3) 最新启动前完整检验输出\n\n```text\n{self._latest_preflight_output.strip() or '(none)'}\n```\n\n"
            f"## 4) 最新验证输出\n\n```text\n{self._latest_verify_output.strip() or '(none)'}\n```\n\n"
            f"## 5) 最近 GUI 日志片段\n\n```text\n{chr(10).join(self._recent_logs)}\n```\n\n"
            f"## 6) Execute 自动捕获报告索引\n\n"
            + ("\n".join(f"- `{p}`" for p in execute_report_paths) if execute_report_paths else "- (none)")
            + "\n"
        )
        with self._session_report_path.open("w", encoding="utf-8") as f:
            f.write(body)
        return self._session_report_path

    def export_session_report(self, reason: str = "manual") -> None:
        if self._export_inflight:
            return
        self._export_inflight = True
        self._log(f"[report] 开始导出总分析报告 reason={reason}")

        def worker() -> None:
            try:
                path = self._write_session_report(reason)
                self.log_queue.put(f"[report] SESSION_REPORT_SAVED={path}")
            finally:
                self._export_inflight = False

        threading.Thread(target=worker, daemon=True).start()

    def run_preflight(self) -> None:
        self._log("[preflight] 启动前完整检验开始（工作区/依赖/端口/网络/冲突进程）...")

        def worker() -> None:
            try:
                result = subprocess.run(
                    ["bash", "-lc", self._preflight_cmd()],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=_clean_ros_child_env(),
                    timeout=35,
                )
                output = result.stdout
            except subprocess.TimeoutExpired as exc:
                output = (exc.stdout or "") + "\nPREFLIGHT_TIMEOUT"
            self.log_queue.put("[preflight] " + output.replace("\n", "\n[preflight] ").rstrip())
            self.log_queue.put("__PREFLIGHT_RESULT__" + output)

        threading.Thread(target=worker, daemon=True).start()

    def start_driver(self) -> None:
        if not self._latest_preflight_output:
            self._log("[operator] 未检测到本会话 preflight 结果，自动先执行一次启动前完整检验。")
            self.run_preflight()
        self.ready = False
        self.moveit_launch_ok = False
        self._reset_tokens()
        proc = self.processes.get("driver")
        if proc is None:
            proc = ManagedProcess("driver", self._driver_cmd(), self.log_queue)
            self.processes["driver"] = proc
        else:
            proc.cmd = self._driver_cmd()
        proc.start()
        self._log("[operator] 等待 50001/50002/50003/50004 监听后，在 CB3 示教器点击运行 External Control 程序。")

    def verify_ready(self) -> None:
        self._reset_tokens()
        self._log("[verify] checking WSL/Windows 50001-50004, /joint_states, scaled controller, action and speed scaling...")
        self._log(
            "[verify] Windows motion ports 50001/50003/50004 are advisory only under WSL2 portproxy; they do not block MoveIt execution if the driver reports READY."
        )

        def worker() -> None:
            try:
                result = subprocess.run(
                    ["bash", "-lc", self._verify_cmd()],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=_clean_ros_child_env(),
                    timeout=45,
                )
                output = result.stdout
            except subprocess.TimeoutExpired as exc:
                output = (exc.stdout or "") + "\nVERIFY_TIMEOUT"
            self.log_queue.put("[verify] " + output.replace("\n", "\n[verify] ").rstrip())
            self.log_queue.put("__VERIFY_RESULT__" + output)

        threading.Thread(target=worker, daemon=True).start()

    def start_moveit(self) -> None:
        if not self.ready and not self.moveit_launch_ok:
            QMessageBox.warning(
                self,
                "尚未就绪",
                "请先点击“验证连接与控制器”。至少需要 JOINT_STATES_OK、CONTROLLER_ACTIVE、ACTION_ONLINE、SPEED_SCALING_NONZERO 后，才能启动 MoveIt2/RViz2。",
            )
            return
        if not self.ready and self.moveit_launch_ok:
            QMessageBox.warning(
                self,
                "仅允许规划查看",
                "当前 RTDE_OVERFLOW，不能视为 READY_FOR_RVIZ2_MOVEIT_EXECUTION。将启动 MoveIt2/RViz2 用于查看和 Plan，但不要点击 Execute；请先重启 driver 并排查 WSL2/网络/CPU/端口转发。",
            )
        proc = self.processes.get("moveit")
        if proc is None:
            proc = ManagedProcess("moveit", self._moveit_cmd(), self.log_queue)
            self.processes["moveit"] = proc
        else:
            proc.cmd = self._moveit_cmd()
        self.exec_state = EXEC_STATE_IDLE
        self._tf_tree_split_warned = False
        self._stop_exec_diag_thread()
        proc.start()
        self._log("[operator] RViz2 中使用 Start State = Current，只做小范围 Plan -> Execute。")
        self._log("[operator] 模型链路保持官方关节名 shoulder_pan_joint ... wrist_3_joint，真实姿态来自 ur_robot_driver /joint_states。")
        self._log("[operator] MoveIt 碰撞检测已在规划层放开；真实 UR 安全模式、保护停止、External Control 与 RTDE 状态仍然有效。")
        if not self.ready:
            self._log("[operator] RTDE_OVERFLOW: 本次仅用于 RViz2/MoveIt2 查看和 Plan，不要 Execute。")
        self._log("[execdiag] Execute 期间高频 shell 诊断已停用；仅在执行前/后触发一次快照。")

    def diagnose_execute(self) -> None:
        self._log("[diagnose] 开始执行前诊断...")
        self._log("[diagnose] 结果含义: speed_scaling>0.01 才可执行; controller state 应有 active轨迹; TF 应无报错")

        def worker() -> None:
            try:
                result = subprocess.run(
                    ["bash", "-lc", self._diagnose_execute_cmd()],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=_clean_ros_child_env(),
                    timeout=30,
                )
                output = result.stdout
            except subprocess.TimeoutExpired as exc:
                output = (exc.stdout or "") + "\nDIAGNOSE_TIMEOUT"
            self.log_queue.put("[diagnose] " + output.replace("\n", "\n[diagnose] ").rstrip())

        threading.Thread(target=worker, daemon=True).start()

    def kill_all(self) -> None:
        self.ready = False
        self.exec_state = EXEC_STATE_IDLE
        self._stop_exec_diag_thread()
        self._reset_tokens()
        self.export_session_report(reason="kill_all")
        self._log("[cleanup] terminating managed launch processes...")
        for proc in self.processes.values():
            proc.terminate()
        time.sleep(0.5)
        for proc in self.processes.values():
            proc.kill()
        killed = self._kill_matching_processes()
        self._log(f"[cleanup] killed/terminated {killed} residual processes")

    def _kill_matching_processes(self) -> int:
        current = os.getpid()
        killed = 0
        targets = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                pid = proc.info["pid"]
                if pid == current:
                    continue
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if "real_control_gui.py" in cmdline:
                    continue
                name = proc.info.get("name") or ""
                haystack = f"{name} {cmdline}"
                if any(pattern in haystack for pattern in KILL_PATTERNS):
                    targets.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        for proc in targets:
            try:
                self._log(f"[cleanup] terminate pid={proc.pid} {' '.join(proc.cmdline())[:180]}")
                proc.terminate()
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _, alive = psutil.wait_procs(targets, timeout=2.0)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return killed

    def _reset_tokens(self) -> None:
        self.rtde_ok = True
        self.moveit_launch_ok = False
        self._rtde_overflow_warned = False
        for label in self.token_labels.values():
            label.setText("未验证")
            self._set_label_color(label, "#777777")

    def _mark_rtde_overflow(self, source: str) -> None:
        self.rtde_ok = False
        self.ready = False
        self._record_finding("RTDE_OVERFLOW", f"来源={source}", "ERROR")
        if "RTDE_OK" in self.token_labels:
            self.token_labels["RTDE_OK"].setText("RTDE_OVERFLOW")
            self._set_label_color(self.token_labels["RTDE_OK"], "#a83232")
        if "READY_FOR_RVIZ2_MOVEIT_EXECUTION" in self.token_labels:
            self.token_labels["READY_FOR_RVIZ2_MOVEIT_EXECUTION"].setText("NOT_READY")
            self._set_label_color(self.token_labels["READY_FOR_RVIZ2_MOVEIT_EXECUTION"], "#a83232")
        if not self._rtde_overflow_warned:
            self._rtde_overflow_warned = True
            self._log(f"[rtde] RTDE_OVERFLOW detected from {source}")
            self._log("[rtde] NOT_READY: RTDE 实时链路不稳定。停止执行，重启 driver，降低诊断负载，并检查 WSL2/网络/CPU/端口转发。")

    def _is_ready_from_tokens(self, output: str) -> bool:
        if not self.rtde_ok or "RTDE_OVERFLOW" in output or _contains_rtde_overflow(output):
            return False
        return all(token in output for token in READY_FALLBACK_TOKENS)

    @staticmethod
    def _is_moveit_launch_ok_from_tokens(output: str) -> bool:
        # This is intentionally weaker than real execution READY. It only means
        # RViz2/MoveIt2 can be opened for visualization and planning inspection.
        core_tokens = (
            "JOINT_STATES_OK",
            "CONTROLLER_ACTIVE",
            "ACTION_ONLINE",
            "SPEED_SCALING_NONZERO",
        )
        return all(token in output for token in core_tokens)

    def _apply_preflight_output(self, output: str) -> None:
        self._latest_preflight_output = output
        if "PREFLIGHT_WORKSPACE_MISSING" in output:
            self._record_finding("PREFLIGHT_WORKSPACE_MISSING", "workspace 路径不存在", "ERROR")
        if "PREFLIGHT_INSTALL_SETUP_MISSING" in output:
            self._record_finding("PREFLIGHT_INSTALL_SETUP_MISSING", "install/setup.bash 缺失，可能未构建", "ERROR")
        if "PREFLIGHT_DRIVER_PREFIX_BAD" in output:
            self._record_finding("PREFLIGHT_DRIVER_PREFIX_BAD", "ur_robot_driver 不是 /opt/ros/humble 官方包", "ERROR")
        if "PREFLIGHT_UR_DESCRIPTION_MISSING" in output:
            self._record_finding("PREFLIGHT_UR_DESCRIPTION_MISSING", "找不到 ur_description 包", "ERROR")
        if "PREFLIGHT_ROBOT_PING_FAIL" in output:
            self._record_finding("PREFLIGHT_ROBOT_PING_FAIL", "无法 ping 通机器人 IP", "WARN")
        if "PREFLIGHT_PORT_CONFLICT" in output:
            self._record_finding("PREFLIGHT_PORT_CONFLICT", "50001-50004 端口存在冲突监听", "ERROR")
        if "PREFLIGHT_FILE_MISSING" in output:
            self._record_finding("PREFLIGHT_FILE_MISSING", "关键模型/launch/脚本文件缺失", "ERROR")
        self.export_session_report(reason="preflight_done")

    def _apply_verify_output(self, output: str) -> None:
        self._latest_verify_output = output
        if "RTDE_OVERFLOW" in output or _contains_rtde_overflow(output):
            self._mark_rtde_overflow("verify output")
            self._record_finding("RTDE_OVERFLOW", "verify 检测到 RTDE 数据通道溢出", "ERROR")
        elif "RTDE_OK" in output:
            self.rtde_ok = True
        for token, label in self.token_labels.items():
            if token == "WINDOWS_MOTION_PORTS_LISTENING":
                if token in output:
                    label.setText("OK")
                    self._set_label_color(label, "#148a3b")
                elif any(warn_token in output for warn_token in WINDOWS_MOTION_WARN_TOKENS):
                    label.setText("WARN")
                    self._set_label_color(label, "#d18a00")
                else:
                    label.setText("未验证")
                    self._set_label_color(label, "#777777")
            elif token == "READY_FOR_RVIZ2_MOVEIT_EXECUTION":
                if self._is_ready_from_tokens(output):
                    label.setText("OK")
                    self._set_label_color(label, "#148a3b")
                else:
                    label.setText("FAIL")
                    self._set_label_color(label, "#a83232")
            elif token == "RTDE_OK":
                if self.rtde_ok and token in output:
                    label.setText("OK")
                    self._set_label_color(label, "#148a3b")
                else:
                    label.setText("RTDE_OVERFLOW" if not self.rtde_ok else "FAIL")
                    self._set_label_color(label, "#a83232")
            elif token in output:
                label.setText("OK")
                self._set_label_color(label, "#148a3b")
            else:
                label.setText("FAIL")
                self._set_label_color(label, "#a83232")
        self.moveit_launch_ok = self._is_moveit_launch_ok_from_tokens(output)
        self.ready = self._is_ready_from_tokens(output)
        if "ROBOT_MODE_FAIL" in output:
            self._record_finding("ROBOT_MODE_FAIL", "dashboard robot_mode 服务不可用", "WARN")
        if "SAFETY_MODE_FAIL" in output:
            self._record_finding("SAFETY_MODE_FAIL", "dashboard safety_mode 服务不可用", "WARN")
        if "WINDOWS_PORTPROXY_MISSING" in output:
            self._record_finding("WINDOWS_PORTPROXY_MISSING", "Windows 端口转发缺失", "WARN")
        if "WINDOWS_50002_NOT_LISTENING" in output:
            self._record_finding("WINDOWS_50002_NOT_LISTENING", "Windows 50002 未监听", "WARN")
        if "SPEED_SCALING_ZERO_OR_MISSING" in output:
            self._record_finding("SPEED_SCALING_LOW_OR_ZERO", "速度缩放为0或缺失", "ERROR")
        if "ACTION_OFFLINE" in output or "ACTION_INFO_FAIL" in output:
            self._record_finding("ACTION_OFFLINE", "scaled follow_joint_trajectory 不在线", "ERROR")
        if self.moveit_launch_ok and not self.ready:
            self._log("[verify] MOVEIT_RVIZ_PLAN_ONLY_OK: control graph is online, but execution READY is blocked by RTDE/other hard gate.")
        self.export_session_report(reason="verify_done")

    def _refresh_process_status(self) -> None:
        driver = "running" if self.processes.get("driver") and self.processes["driver"].is_running() else "stopped"
        moveit = "running" if self.processes.get("moveit") and self.processes["moveit"].is_running() else "stopped"
        rtde = "OK" if self.rtde_ok else "RTDE_OVERFLOW"
        self.process_status.setText(f"Driver: {driver} | MoveIt/RViz: {moveit} | ExecState: {self.exec_state} | RTDE: {rtde}")

    def _start_exec_diag_thread(self) -> None:
        # Intentionally disabled for real-robot execution: high-frequency ROS2
        # subprocess diagnostics can add load to WSL2 + RTDE timing.
        self._exec_diag_stop.set()
        self._exec_diag_thread = None

    def _stop_exec_diag_thread(self) -> None:
        self._exec_diag_stop.set()

    def _snapshot_exec_runtime(self, reason: str) -> None:
        now = time.time()
        if now - self._last_exec_snapshot_ts < 1.0 and not reason.startswith("POST_EXECUTE"):
            return
        self._last_exec_snapshot_ts = now
        self.log_queue.put(f"[execdiag] EXEC_RUNTIME_SNAPSHOT_TRIGGER={reason}")

        def worker() -> None:
            try:
                result = subprocess.run(
                    ["bash", "-lc", self._runtime_exec_diag_cmd()],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=_clean_ros_child_env(),
                    timeout=8,
                )
                out = result.stdout.strip()
                if out:
                    self.log_queue.put("[execdiag] " + out.replace("\n", "\n[execdiag] "))
            except subprocess.TimeoutExpired:
                self.log_queue.put("[execdiag] EXEC_RUNTIME_SNAPSHOT_TIMEOUT")

        threading.Thread(target=worker, daemon=True).start()

    def _update_exec_state_from_log(self, msg: str) -> None:
        if "Connection to reverse interface dropped" in msg:
            self._record_finding("REVERSE_INTERFACE_DROPPED", "reverse interface 连接频繁断开", "ERROR")
        if "Connection attempt on port 50003 while maximum number of clients (1) is already connected" in msg:
            self._record_finding("PORT_50003_CLIENT_CONFLICT", "50003 端口出现重复客户端连接冲突", "ERROR")
        if "Connection attempt on port 50004 while maximum number of clients (1) is already connected" in msg:
            self._record_finding("PORT_50004_CLIENT_CONFLICT", "50004 端口出现重复客户端连接冲突", "ERROR")
        if "Accepted new action goal" in msg or "Goal request accepted!" in msg:
            if self.exec_state != EXEC_STATE_EXECUTING:
                self.exec_state = EXEC_STATE_EXECUTING
                self._log("[exec] EXEC_STATE_EXECUTING")
                self._snapshot_exec_runtime("PRE_EXECUTE_SNAPSHOT")
                self._start_execute_auto_capture("EXECUTE_ACCEPTED", msg, force_new=True)
        if "Cannot push a new trajectory while another is being executed" in msg:
            self.exec_state = EXEC_STATE_EXECUTION_ERROR
            self._record_finding("EXEC_ERROR_CONCURRENT_GOAL", "轨迹并发提交，上一条未完成", "WARN")
            self._log("[exec] EXEC_ERROR_CONCURRENT_GOAL")
            self._log("[exec] 上一条轨迹仍在执行，当前 Plan/Execute 被拒绝；请等待执行结束后再发下一条。")
            self._log("[exec] 该错误不是“速度太快”导致。")
            self._snapshot_exec_runtime("POST_EXECUTE_SNAPSHOT_EXEC_ERROR_CONCURRENT_GOAL")
            self._start_execute_auto_capture("EXECUTE_ERROR_CONCURRENT_GOAL", msg)
        if "MoveGroupInterface::move() failed or timeout reached" in msg:
            self.exec_state = EXEC_STATE_EXECUTION_ERROR
            self._record_finding("EXEC_TIMEOUT_OR_ABORT", "MoveGroupInterface::move 超时或被中止", "ERROR")
            self._log("[exec] EXEC_ERROR_TIMEOUT_OR_ABORT")
            self._snapshot_exec_runtime("POST_EXECUTE_SNAPSHOT_EXEC_ERROR_TIMEOUT_OR_ABORT")
            self._start_execute_auto_capture("EXECUTE_ERROR_TIMEOUT_OR_ABORT", msg)
            self.export_session_report(reason="execute_timeout_or_abort")
        if "SPEED_SCALING_LOW_OR_ZERO" in msg:
            self._record_finding("SPEED_SCALING_LOW_OR_ZERO", "执行期间速度缩放过低/为零", "ERROR")
            self._log("[exec] SPEED_SCALING_LOW_OR_ZERO")
            self._start_execute_auto_capture("EXECUTE_SPEED_SCALING_LOW", msg)
        if (
            "Unable to transform object from frame" in msg
            and "planning frame'base_jizuo'" in msg
            and not self._tf_tree_split_warned
        ):
            self._tf_tree_split_warned = True
            self._log("[exec] TF_TREE_SPLIT_WARN")
            self._log("[exec] TF 树存在分裂风险，可能影响场景一致性；该项与并发执行拒绝需分开判断。")
            self._start_execute_auto_capture("EXECUTE_TF_TREE_SPLIT_WARN", msg)
        if msg.startswith("[moveit] EXIT code="):
            if self.exec_state == EXEC_STATE_EXECUTING:
                self.exec_state = EXEC_STATE_EXECUTION_DONE
                self._record_finding("EXEC_STATE_EXECUTION_DONE", "moveit 进程退出前已进入执行态", "INFO")
                self._log("[exec] EXEC_STATE_EXECUTION_DONE")
            else:
                self.exec_state = EXEC_STATE_IDLE
            self._snapshot_exec_runtime("POST_EXECUTE_SNAPSHOT_MOVEIT_EXIT")
            self._start_execute_auto_capture("MOVEIT_EXIT", msg)
            self._stop_exec_diag_thread()

    def _drain_logs(self) -> None:
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if msg.startswith("__PREFLIGHT_RESULT__"):
                self._apply_preflight_output(msg.replace("__PREFLIGHT_RESULT__", "", 1))
                continue
            if msg.startswith("__VERIFY_RESULT__"):
                self._apply_verify_output(msg.replace("__VERIFY_RESULT__", "", 1))
                continue
            if _contains_rtde_overflow(msg):
                self._mark_rtde_overflow("runtime log")
            self._update_exec_state_from_log(msg)
            self._log(msg)

    def _log(self, msg: str) -> None:
        self._recent_logs.append(msg)
        self.log_box.append(msg)

    def closeEvent(self, event) -> None:
        self._stop_exec_diag_thread()
        try:
            path = self._write_session_report("close_event")
            self._log(f"[report] SESSION_REPORT_SAVED={path}")
        except Exception as exc:
            self._log(f"[report] SESSION_REPORT_SAVE_FAIL: {exc}")
        for proc in self.processes.values():
            proc.terminate()
        super().closeEvent(event)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot-ip", default="10.160.9.21")
    parser.add_argument("--external-host-ip", default="10.160.9.100")
    parser.add_argument("--script-sender-port", default="50002")
    parser.add_argument("--workspace", default="/root/ur10_ws")
    parser.add_argument("--qt-platform", default="", help="Optional QT_QPA_PLATFORM override, e.g. xcb/offscreen/wayland")
    args, _ = parser.parse_known_args()
    return args


def main() -> int:
    args = parse_args()
    _qt_plugin_fix()
    _configure_qt_platform(args)
    cleaned = _cleanup_stale_gui_instances()
    if cleaned:
        print(f"[gui] cleaned stale instances: {cleaned}", flush=True)
    print(
        "[gui] boot",
        f"DISPLAY={os.environ.get('DISPLAY', '')}",
        f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '')}",
        f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM', '')}",
        flush=True,
    )
    app = QApplication(sys.argv)
    if not app.screens():
        print("[gui] no active Qt screen detected; check DISPLAY/Wayland/X11 forwarding.", flush=True)
        return 3
    win = MainWindow(args)
    win.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    win.show()
    win.raise_()
    win.activateWindow()
    QTimer.singleShot(300, win.raise_)
    QTimer.singleShot(300, win.activateWindow)
    # Keep top-most only during startup, then restore normal stacking.
    def _drop_startup_topmost() -> None:
        win.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        win.show()

    QTimer.singleShot(3000, _drop_startup_topmost)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

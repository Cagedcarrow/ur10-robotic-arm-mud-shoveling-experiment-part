#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

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
    "READY_FOR_RVIZ2_MOVEIT_EXECUTION": "MoveIt 执行就绪",
}

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


def _clean_ros_child_env() -> Dict[str, str]:
    env = os.environ.copy()
    for key in QT_CHILD_ENV_KEYS:
        env.pop(key, None)
    return env


def _qt_plugin_fix() -> None:
    try:
        from PyQt5 import QtCore

        plugins = Path(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.PluginsPath))
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugins))
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(plugins / "platforms"))
    except Exception:
        pass


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
        self.token_labels: Dict[str, QLabel] = {}

        self._build_ui(args)

        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self._drain_logs)
        self.log_timer.start(100)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._refresh_process_status)
        self.status_timer.start(500)

        self._log("[init] GUI ready. 正式姿态来源: ur_robot_driver /joint_states")

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
        self.btn_start_driver = QPushButton("1 启动监听节点 / Driver")
        self.btn_verify = QPushButton("验证连接与控制器")
        self.btn_diagnose = QPushButton("诊断执行状态")
        self.btn_start_moveit = QPushButton("2 启动 RViz2 + MoveIt2")
        self.btn_kill = QPushButton("3 杀死所有相关进程")
        self.btn_start_driver.clicked.connect(self.start_driver)
        self.btn_verify.clicked.connect(self.verify_ready)
        self.btn_diagnose.clicked.connect(self.diagnose_execute)
        self.btn_start_moveit.clicked.connect(self.start_moveit)
        self.btn_kill.clicked.connect(self.kill_all)
        h.addWidget(self.btn_start_driver)
        h.addWidget(self.btn_verify)
        h.addWidget(self.btn_diagnose)
        h.addWidget(self.btn_start_moveit)
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
            # Kill the driver's robot_state_publisher to avoid TF conflict with assembly model
            'echo "[moveit] killing conflicting robot_state_publisher from driver..." && '
            "pkill -f 'robot_state_publisher.*ur_robot_driver' 2>/dev/null; "
            "pkill -f 'robot_state_publisher.*ur_rsp' 2>/dev/null; "
            "sleep 0.5 && "
            # Verify only one RSP is left (ours will start inside the launch)
            'echo "[moveit] remaining RSP processes:" && '
            "pgrep -a robot_state_publisher 2>/dev/null || echo '(none)' && "
            "ros2 launch ur10_assembly_real_control ur10_assembly_real.launch.py "
            f"robot_ip:={robot_ip} "
            "ur_type:=ur10 "
            "launch_driver:=false "
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

ros2 run ur10_assembly_real_control check_real_ur10_ready.sh
"""
        return f"{self._source_prefix()} && bash -lc {self._shell_quote(script)}"

    def start_driver(self) -> None:
        self.ready = False
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
        if not self.ready:
            QMessageBox.warning(
                self,
                "尚未就绪",
                "请先点击“验证连接与控制器”，看到 READY_FOR_RVIZ2_MOVEIT_EXECUTION 后再启动 MoveIt2/RViz2。",
            )
            return
        proc = self.processes.get("moveit")
        if proc is None:
            proc = ManagedProcess("moveit", self._moveit_cmd(), self.log_queue)
            self.processes["moveit"] = proc
        else:
            proc.cmd = self._moveit_cmd()
        proc.start()
        self._log("[operator] RViz2 中使用 Start State = Current，只做小范围 Plan -> Execute。")

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
        self._reset_tokens()
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
        for label in self.token_labels.values():
            label.setText("未验证")
            self._set_label_color(label, "#777777")

    def _apply_verify_output(self, output: str) -> None:
        for token, label in self.token_labels.items():
            if token in output:
                label.setText("OK")
                self._set_label_color(label, "#148a3b")
            else:
                label.setText("FAIL")
                self._set_label_color(label, "#a83232")
        self.ready = all(token in output for token in TOKEN_LABELS)

    def _refresh_process_status(self) -> None:
        driver = "running" if self.processes.get("driver") and self.processes["driver"].is_running() else "stopped"
        moveit = "running" if self.processes.get("moveit") and self.processes["moveit"].is_running() else "stopped"
        self.process_status.setText(f"Driver: {driver} | MoveIt/RViz: {moveit}")

    def _drain_logs(self) -> None:
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if msg.startswith("__VERIFY_RESULT__"):
                self._apply_verify_output(msg.replace("__VERIFY_RESULT__", "", 1))
                continue
            self._log(msg)

    def _log(self, msg: str) -> None:
        self.log_box.append(msg)

    def closeEvent(self, event) -> None:
        for proc in self.processes.values():
            proc.terminate()
        super().closeEvent(event)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot-ip", default="10.160.9.21")
    parser.add_argument("--external-host-ip", default="10.160.9.100")
    parser.add_argument("--script-sender-port", default="50002")
    parser.add_argument("--workspace", default="/root/ur10_ws")
    args, _ = parser.parse_known_args()
    return args


def main() -> int:
    _qt_plugin_fix()
    args = parse_args()
    app = QApplication(sys.argv)
    win = MainWindow(args)
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

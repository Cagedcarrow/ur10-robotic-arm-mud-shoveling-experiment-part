#!/usr/bin/env python3
"""Unified visualization + run orchestrator for UR10 real verification and sim launch."""

from __future__ import annotations

import ipaddress
import json
import os
import queue
import queue as queue_module
import re
import shlex
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from config_schema import UnifiedGUIConfig


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path.home() / ".ur10_unified_gui.json"

VALID_STATUS = {"IDLE", "RUNNING", "PASS", "FAIL", "WARN", "STOPPED"}
ERROR_HINT_RE = re.compile(r"(\berror\b|\bexception\b|\bfail\b|traceback)", re.IGNORECASE)


def _file_exists(path: str) -> bool:
    try:
        return Path(path).is_file()
    except Exception:
        return False


def _dir_exists(path: str) -> bool:
    try:
        return Path(path).is_dir()
    except Exception:
        return False


class ProcessSession:
    def __init__(self, cmd, cwd: Optional[str], env: Optional[Dict[str, str]], label: str, log_queue):
        self.cmd = cmd
        self.cwd = cwd
        self.env = env
        self.label = label
        self.log_queue = log_queue
        self.proc: Optional[subprocess.Popen] = None
        self._stop = threading.Event()

    def start(self):
        preexec_fn = os.setsid if os.name == "posix" else None
        self.proc = subprocess.Popen(
            self.cmd,
            cwd=self.cwd,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            preexec_fn=preexec_fn,
        )
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        if not self.proc or not self.proc.stdout:
            return
        try:
            for line in self.proc.stdout:
                if self._stop.is_set():
                    break
                self.log_queue.put((self.label, line.rstrip("\n")))
            rc = self.proc.wait()
            self.log_queue.put((self.label, f"[INFO] Process exit={rc}"))
        except Exception as exc:
            self.log_queue.put((self.label, f"[ERROR] {exc}"))

    def stop(self, term_timeout: float = 2.5):
        self._stop.set()
        if not self.proc:
            return
        try:
            if self.proc.poll() is not None:
                return
            pgid = os.getpgid(self.proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            try:
                self.proc.wait(timeout=term_timeout)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
                self.proc.wait(timeout=1)
        except Exception:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None


class UnifiedGUIApp(tk.Tk):
    SUMMARY_RE = re.compile(r"\[SUMMARY\]\s+state=([A-Z]+)\s+reason=(.+)")
    PROCESS_EXIT_RE = re.compile(r"\[INFO\]\s+Process\s+exit=(-?\d+)")

    def __init__(self):
        super().__init__()
        self.title("UR10 一体化可视化 GUI")
        self.geometry("1280x860")

        self.config_data = self._load_config()
        self.log_queue: "queue.Queue[Tuple[str, str]]" = queue.Queue()
        self.current_session: Optional[ProcessSession] = None
        self.active_mode: Optional[str] = None

        self.last_summary_state: Optional[str] = None
        self.last_summary_reason: Optional[str] = None
        self.last_error_hint: Optional[str] = None

        self._build_vars()
        self._build_ui()
        self._poll()

    def _build_vars(self):
        c = self.config_data
        self.v_mode = tk.StringVar(value=c.mode)
        self.v_host_ip = tk.StringVar(value=c.host_ip)
        self.v_robot_ip = tk.StringVar(value=c.robot_ip)
        self.v_robot_subnet = tk.StringVar(value=c.robot_subnet)
        self.v_reverse_ip = tk.StringVar(value=c.reverse_ip or c.host_ip)
        self.v_wrist_delta = tk.StringVar(value=c.wrist3_delta)
        self.v_controller = tk.StringVar(value=c.controller)
        self.v_status_timeout = tk.StringVar(value=c.status_timeout)

        self.v_ur_type = tk.StringVar(value=c.ur_type)
        self.v_use_fake_hardware = tk.StringVar(value=c.use_fake_hardware)
        self.v_world = tk.StringVar(value=c.world)
        self.v_start_rviz = tk.StringVar(value=c.start_rviz)
        self.v_enable_gantry_rviz_control = tk.StringVar(value=c.enable_gantry_rviz_control)
        self.v_auto_network_check = tk.BooleanVar(value=c.auto_network_check)

        self.v_run_full_verify_script = tk.StringVar(value=c.run_full_verify_script)
        self.v_run_full_verify_wsl_script = tk.StringVar(value=c.run_full_verify_wsl_script)
        self.v_workspace_root = tk.StringVar(value=c.workspace_root)

    def _build_ui(self):
        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(container)
        top.pack(fill=tk.X)
        ttk.Label(top, text="模式").pack(side=tk.LEFT, padx=(0, 8))
        for m in ("Real", "Sim"):
            ttk.Radiobutton(top, text=m, value=m, variable=self.v_mode, command=self._toggle_mode).pack(side=tk.LEFT)

        network = ttk.LabelFrame(container, text="网络检查", padding=8)
        network.pack(fill=tk.X, pady=(8, 4))
        ttk.Checkbutton(network, text="启动前自动快速检查", variable=self.v_auto_network_check).grid(row=0, column=0, sticky=tk.W)
        self.btn_check = ttk.Button(network, text="快速网络检查", command=self._quick_network_check)
        self.btn_check.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        params = ttk.Frame(container)
        params.pack(fill=tk.X, pady=(0, 8))
        self.real_frame = ttk.LabelFrame(params, text="Real 参数", padding=8)
        self.real_frame.grid(row=0, column=0, sticky=tk.NW, padx=(0, 10))
        self.sim_frame = ttk.LabelFrame(params, text="Sim 参数", padding=8)
        self.sim_frame.grid(row=0, column=1, sticky=tk.NW)

        self._add_field(self.real_frame, "host_ip", self.v_host_ip, 0)
        self._add_field(self.real_frame, "robot_ip", self.v_robot_ip, 1)
        self._add_field(self.real_frame, "robot_subnet", self.v_robot_subnet, 2)
        self._add_field(self.real_frame, "reverse_ip", self.v_reverse_ip, 3)
        self._add_field(self.real_frame, "wrist3_delta", self.v_wrist_delta, 4)
        self._add_field(self.real_frame, "controller", self.v_controller, 5)
        self._add_field(self.real_frame, "status_timeout", self.v_status_timeout, 6)
        self._add_field(self.real_frame, "run_full_verify.sh", self.v_run_full_verify_script, 7, chooser=True, file_modes=("Shell", "*.sh"))
        self._add_field(self.real_frame, "run_full_verify_wsl.sh(备用)", self.v_run_full_verify_wsl_script, 8, chooser=True, file_modes=("Shell", "*.sh"))

        self._add_field(self.sim_frame, "ur_type", self.v_ur_type, 0)
        self._add_field(self.sim_frame, "use_fake_hardware", self.v_use_fake_hardware, 1)
        self._add_field(self.sim_frame, "world", self.v_world, 2, chooser=True, file_modes=("World", "*.world"))
        self._add_field(self.sim_frame, "start_rviz", self.v_start_rviz, 3)
        self._add_field(self.sim_frame, "enable_gantry_rviz_control", self.v_enable_gantry_rviz_control, 4)
        self._add_field(self.sim_frame, "workspace", self.v_workspace_root, 5, chooser=True, file_modes=("Directory", "*"), is_dir=True)

        btn = ttk.Frame(container)
        btn.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btn, text="启动实机验证", command=self._start_real).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn, text="启动仿真（Gazebo+RViz2+MoveIt）", command=self._start_sim).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn, text="停止所有", command=self._stop_session).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn, text="导出日志", command=self._export_log).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn, text="保存参数", command=self._save_config).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn, text="加载参数", command=self._load_config_to_ui).pack(side=tk.LEFT)

        ttk.Separator(container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 6))

        body = ttk.Frame(container)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text="执行日志").pack(anchor=tk.W)
        self.txt = tk.Text(body, wrap=tk.WORD, height=32)
        self.txt.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="IDLE")
        status = ttk.Label(self, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN)
        status.pack(side=tk.BOTTOM, fill=tk.X)

        self._toggle_mode()

    def _add_field(self, frame: ttk.LabelFrame, label: str, var: tk.StringVar, row: int, chooser: bool = False, file_modes=("All", "*"), is_dir: bool = False):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W)
        entry = ttk.Entry(frame, textvariable=var, width=58)
        entry.grid(row=row, column=1, sticky=tk.EW, padx=(4, 4))

        if chooser:
            if is_dir:
                cmd = lambda: self._pick_dir(var)
            else:
                exts = (file_modes, ("All", "*")) if file_modes[0] != "All" else (file_modes,)
                cmd = lambda: self._pick_file(var, exts)
            ttk.Button(frame, text="…", width=3, command=cmd).grid(row=row, column=2)

    def _pick_file(self, var: tk.StringVar, types):
        path = filedialog.askopenfilename(filetypes=types)
        if path:
            var.set(path)

    def _pick_dir(self, var: tk.StringVar):
        path = filedialog.askdirectory(initialdir=var.get() or str(BASE_DIR))
        if path:
            var.set(path)

    def _toggle_mode(self):
        if self.v_mode.get() == "Real":
            for child in self.sim_frame.winfo_children():
                child.configure(state=tk.DISABLED)
            for child in self.real_frame.winfo_children():
                child.configure(state=tk.NORMAL)
        else:
            for child in self.real_frame.winfo_children():
                child.configure(state=tk.DISABLED)
            for child in self.sim_frame.winfo_children():
                child.configure(state=tk.NORMAL)

    def _set_status(self, status: str, reason: Optional[str] = None):
        status = status if status in VALID_STATUS else "WARN"
        text = status if not reason else f"{status} | {reason[:200]}"
        self.status_var.set(text)

    def _prepare_run_state(self, mode: str):
        self.active_mode = mode
        self.last_summary_state = None
        self.last_summary_reason = None
        self.last_error_hint = None
        self._set_status("RUNNING")

    def _session_busy(self) -> bool:
        return self.current_session is not None and self.current_session.is_running()

    def _guard_mutex(self, target_mode: str) -> bool:
        if not self._session_busy():
            return True
        active = self.active_mode or "Unknown"
        self._append_log("Main", f"[WARN] 当前 {active} 任务运行中，按互斥策略拒绝启动 {target_mode}")
        messagebox.showwarning("提示", f"当前 {active} 任务运行中，请先停止")
        return False

    def _append_log(self, source: str, text: str):
        line = f"[{source}] {text}"
        self.txt.configure(state=tk.NORMAL)
        self.txt.insert(tk.END, line + "\n")
        self.txt.see(tk.END)

        m = self.SUMMARY_RE.match(text)
        if m:
            self.last_summary_state = m.group(1)
            self.last_summary_reason = m.group(2)
            self._set_status(self.last_summary_state, self.last_summary_reason)
            return

        if ERROR_HINT_RE.search(text):
            self.last_error_hint = text

        m_exit = self.PROCESS_EXIT_RE.match(text)
        if m_exit and self.current_session and not self.current_session.is_running():
            rc = int(m_exit.group(1))
            self._finalize_from_exit(rc)

    def _finalize_from_exit(self, rc: int):
        if self.last_summary_state:
            # Summary is authoritative.
            if self.last_summary_state in {"PASS", "FAIL", "WARN"}:
                self._set_status(self.last_summary_state, self.last_summary_reason)
            else:
                self._set_status("WARN", self.last_summary_reason or "unknown_summary_state")
            self.current_session = None
            self.active_mode = None
            return

        if rc == 0:
            self._set_status("PASS", "process_exit_0_no_summary")
            self._append_log("Main", "[WARN] 未检测到 [SUMMARY]，按 exit=0 判定 PASS")
        else:
            reason = self.last_error_hint or f"process_exit_{rc}"
            self._set_status("FAIL", reason)
            self._append_log("Main", f"[WARN] 未检测到 [SUMMARY]，按 exit={rc} 判定 FAIL")
        self.current_session = None
        self.active_mode = None

    def _poll(self):
        try:
            while True:
                source, text = self.log_queue.get_nowait()
                self._append_log(source, text)
        except queue_module.Empty:
            pass

        if self.current_session and not self.current_session.is_running():
            # In case the exit line was not parsed due to race, finalize here.
            if self.active_mode is not None:
                rc = self.current_session.proc.poll() if self.current_session.proc else 1
                self._finalize_from_exit(int(rc if rc is not None else 1))

        self.after(120, self._poll)

    def _quick_network_check(self):
        if self.v_mode.get() == "Real":
            self._check_real_network(self._gather_real())
        else:
            self._check_sim_network(self._gather_sim())

    def _check_real_network(self, cfg: UnifiedGUIConfig) -> bool:
        ok = True
        warn = 0
        try:
            ipaddress.ip_address(cfg.host_ip)
        except Exception:
            self._append_log("Net", "[FAIL] host_ip 非法")
            messagebox.showerror("参数错误", "host_ip 不合法")
            return False

        try:
            ipaddress.ip_address(cfg.robot_ip)
        except Exception:
            self._append_log("Net", "[FAIL] robot_ip 非法")
            messagebox.showerror("参数错误", "robot_ip 不合法")
            return False

        try:
            ipaddress.ip_network(cfg.robot_subnet, strict=False)
        except Exception:
            self._append_log("Net", "[FAIL] robot_subnet 非法")
            messagebox.showerror("参数错误", "robot_subnet 不合法")
            return False

        host = ipaddress.ip_address(cfg.host_ip)
        robot = ipaddress.ip_address(cfg.robot_ip)
        subnet = ipaddress.ip_network(cfg.robot_subnet, strict=False)
        if host not in subnet:
            warn += 1
            self._append_log("Net", f"[WARN] host_ip 不在子网 {cfg.robot_subnet}")
        if robot not in subnet:
            warn += 1
            self._append_log("Net", f"[WARN] robot_ip 不在子网 {cfg.robot_subnet}")

        try:
            p = subprocess.run(
                ["ping", "-c", "1", "-W", "2", cfg.robot_ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            if p.returncode == 0:
                self._append_log("Net", "[PASS] ping 到 robot_ip 成功")
            else:
                warn += 1
                self._append_log("Net", "[WARN] ping 到 robot_ip 失败（仅警告）")
        except Exception as exc:
            warn += 1
            self._append_log("Net", f"[WARN] ping 检查异常: {exc}")

        for port in (50001, 50002, 50003, 50004):
            if self._tcp_check(cfg.robot_ip, port, timeout=2.0):
                self._append_log("Net", f"[PASS] tcp {cfg.robot_ip}:{port}")
            else:
                warn += 1
                self._append_log("Net", f"[WARN] tcp {cfg.robot_ip}:{port} 未立即连接")

        if _file_exists(cfg.run_full_verify_script):
            self._append_log("Net", f"[PASS] 实机脚本存在: {cfg.run_full_verify_script}")
        elif _file_exists(cfg.run_full_verify_wsl_script):
            warn += 1
            self._append_log("Net", "[WARN] 主脚本缺失，将回退备用脚本")
        else:
            ok = False
            self._append_log("Net", "[FAIL] 主脚本与备用脚本均不存在")

        if ok and warn == 0:
            self._set_status("PASS")
            self._append_log("Net", "[SUMMARY] state=PASS reason=network_check_ok")
            return True
        if ok:
            self._set_status("WARN")
            self._append_log("Net", f"[SUMMARY] state=WARN reason=network_check_pass_with_warnings warn={warn}")
            return True

        self._set_status("FAIL")
        self._append_log("Net", "[SUMMARY] state=FAIL reason=network_check_failed")
        return False

    def _tcp_check(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except Exception:
            return False

    def _check_sim_network(self, cfg: UnifiedGUIConfig) -> bool:
        self._append_log("Net", "[INFO] Sim 快速检查：仅校验启动参数与目录")
        if not _dir_exists(cfg.workspace_root):
            self._append_log("Net", f"[FAIL] workspace_root 不存在或非目录: {cfg.workspace_root}")
            self._set_status("FAIL")
            return False
        if not cfg.ur_type:
            messagebox.showerror("参数错误", "ur_type 不能为空")
            self._set_status("FAIL")
            return False
        if not cfg.world:
            messagebox.showerror("参数错误", "world 不能为空")
            self._set_status("FAIL")
            return False

        self._set_status("PASS")
        self._append_log("Net", f"[PASS] workspace={cfg.workspace_root}")
        self._append_log("Net", f"[PASS] world={cfg.world}")
        self._append_log("Net", "[SUMMARY] state=PASS reason=sim_check_ok")
        return True

    def _gather_real(self) -> UnifiedGUIConfig:
        c = self.config_data
        return UnifiedGUIConfig(
            mode="Real",
            host_ip=self.v_host_ip.get().strip(),
            robot_ip=self.v_robot_ip.get().strip(),
            robot_subnet=self.v_robot_subnet.get().strip(),
            reverse_ip=self.v_reverse_ip.get().strip() or self.v_host_ip.get().strip(),
            wrist3_delta=self.v_wrist_delta.get().strip(),
            controller=self.v_controller.get().strip(),
            status_timeout=self.v_status_timeout.get().strip(),
            run_full_verify_script=self.v_run_full_verify_script.get().strip(),
            run_full_verify_wsl_script=self.v_run_full_verify_wsl_script.get().strip(),
            workspace_root=self.v_workspace_root.get().strip(),
            auto_network_check=self.v_auto_network_check.get(),
            ur_type=c.ur_type,
            use_fake_hardware=c.use_fake_hardware,
            world=c.world,
            start_rviz=c.start_rviz,
            enable_gantry_rviz_control=c.enable_gantry_rviz_control,
            start_cpp_demo=c.start_cpp_demo,
            start_py_demo=c.start_py_demo,
            start_py_tools=c.start_py_tools,
        )

    def _gather_sim(self) -> UnifiedGUIConfig:
        c = self.config_data
        return UnifiedGUIConfig(
            mode="Sim",
            ur_type=self.v_ur_type.get().strip(),
            use_fake_hardware=self.v_use_fake_hardware.get().strip(),
            world=self.v_world.get().strip(),
            start_rviz=self.v_start_rviz.get().strip(),
            enable_gantry_rviz_control=self.v_enable_gantry_rviz_control.get().strip(),
            start_cpp_demo=c.start_cpp_demo,
            start_py_demo=c.start_py_demo,
            start_py_tools=c.start_py_tools,
            workspace_root=self.v_workspace_root.get().strip(),
            auto_network_check=self.v_auto_network_check.get(),
            host_ip=c.host_ip,
            robot_ip=c.robot_ip,
            robot_subnet=c.robot_subnet,
            reverse_ip=c.reverse_ip,
            wrist3_delta=c.wrist3_delta,
            controller=c.controller,
            status_timeout=c.status_timeout,
            run_full_verify_script=c.run_full_verify_script,
            run_full_verify_wsl_script=c.run_full_verify_wsl_script,
        )

    def _validate_real(self, cfg: UnifiedGUIConfig) -> Tuple[bool, str]:
        for field, value in (
            ("host_ip", cfg.host_ip),
            ("robot_ip", cfg.robot_ip),
            ("robot_subnet", cfg.robot_subnet),
            ("wrist3_delta", cfg.wrist3_delta),
            ("status_timeout", cfg.status_timeout),
        ):
            if not value:
                return False, f"{field} 不能为空"

        try:
            ipaddress.ip_address(cfg.host_ip)
            ipaddress.ip_address(cfg.robot_ip)
            ipaddress.ip_network(cfg.robot_subnet, strict=False)
            float(cfg.wrist3_delta)
            int(cfg.status_timeout)
        except Exception:
            return False, "IP/子网/数值参数格式不合法"

        if not _dir_exists(cfg.workspace_root):
            return False, "workspace_root 不存在或非目录"
        if not _file_exists(cfg.run_full_verify_script) and not _file_exists(cfg.run_full_verify_wsl_script):
            return False, "未找到可用实机执行脚本"
        return True, ""

    def _validate_sim(self, cfg: UnifiedGUIConfig) -> Tuple[bool, str]:
        if not cfg.ur_type:
            return False, "ur_type 不能为空"
        if not cfg.world:
            return False, "world 不能为空"
        if not _dir_exists(cfg.workspace_root):
            return False, "workspace_root 不存在或非目录"
        return True, ""

    def _start_real(self):
        if not self._guard_mutex("Real"):
            return

        cfg = self._gather_real()
        self.config_data = UnifiedGUIConfig.from_dict({**self.config_data.to_dict(), **cfg.to_dict()})
        ok, err = self._validate_real(cfg)
        if not ok:
            messagebox.showerror("参数错误", err)
            return

        if cfg.auto_network_check and not self._check_real_network(cfg):
            self._append_log("Real", "[FAIL] 启动前网络检查失败，已拒绝启动")
            return

        script = cfg.run_full_verify_script if _file_exists(cfg.run_full_verify_script) else cfg.run_full_verify_wsl_script
        script_note = "primary" if script == cfg.run_full_verify_script else "fallback_wsl"

        self._prepare_run_state("Real")
        self._append_log("Real", f"[INFO] 启动实机验证 ({script_note})")
        self._append_log("Real", f"[INFO] script={script}")

        env = os.environ.copy()
        env.update(
            {
                "ROBOT_IP": cfg.robot_ip,
                "REVERSE_IP": cfg.reverse_ip or cfg.host_ip,
                "WRIST3_DELTA_DEG": cfg.wrist3_delta,
                "CONFIRM_EXECUTE": "true",
                "LAUNCH_RVIZ": "true",
                "INITIAL_JOINT_CONTROLLER": cfg.controller,
                "STATUS_TIMEOUT_SEC": cfg.status_timeout,
            }
        )

        cmd = [
            "bash",
            "-lc",
            (
                "source /opt/ros/humble/setup.bash; "
                f"if [ -f '{cfg.workspace_root}/install/setup.bash' ]; then source '{cfg.workspace_root}/install/setup.bash'; fi; "
                f"cd {shlex.quote(str(Path(script).parent))} && {shlex.quote(script)}"
            ),
        ]

        session = ProcessSession(cmd, cwd=cfg.workspace_root, env=env, label="Real", log_queue=self.log_queue)
        self.current_session = session
        session.start()

    def _start_sim(self):
        if not self._guard_mutex("Sim"):
            return

        cfg = self._gather_sim()
        self.config_data = UnifiedGUIConfig.from_dict({**self.config_data.to_dict(), **cfg.to_dict()})
        ok, err = self._validate_sim(cfg)
        if not ok:
            messagebox.showerror("参数错误", err)
            return

        if cfg.auto_network_check and not self._check_sim_network(cfg):
            self._append_log("Sim", "[FAIL] 启动前检查失败，已拒绝启动")
            return

        self._prepare_run_state("Sim")
        self._append_log("Sim", "[INFO] 启动仿真（Gazebo+RViz2+MoveIt）")

        ros_cmd = " ".join(
            [
                "ros2 launch ur10_simulation_bringup complete_simulation.launch.py",
                f"ur_type:={cfg.ur_type}",
                f"use_fake_hardware:={cfg.use_fake_hardware}",
                "use_sim_time:=true",
                f"world:={shlex.quote(cfg.world)}",
                f"start_rviz:={cfg.start_rviz}",
                f"start_cpp_demo:={cfg.start_cpp_demo}",
                f"start_py_demo:={cfg.start_py_demo}",
                f"start_py_tools:={cfg.start_py_tools}",
                f"enable_gantry_rviz_control:={cfg.enable_gantry_rviz_control}",
                "cleanup_existing_processes:=false",
            ]
        )
        cmd = [
            "bash",
            "-lc",
            (
                "source /opt/ros/humble/setup.bash; "
                f"if [ -f '{cfg.workspace_root}/install/setup.bash' ]; then source '{cfg.workspace_root}/install/setup.bash'; fi; "
                f"{ros_cmd}"
            ),
        ]

        session = ProcessSession(cmd, cwd=cfg.workspace_root, env=None, label="Sim", log_queue=self.log_queue)
        self.current_session = session
        session.start()

    def _stop_session(self):
        if self.current_session is None:
            self._set_status("STOPPED")
            self._append_log("Main", "[INFO] 当前无运行任务")
            self.active_mode = None
            return

        mode = self.active_mode or "Unknown"
        self._append_log("Main", f"[INFO] 正在停止 {mode} 任务")
        self.current_session.stop()
        self.current_session = None
        self.active_mode = None
        self._set_status("STOPPED")
        self._append_log("Main", "[INFO] 已发送停止信号")

    def _clear_log(self):
        self.txt.configure(state=tk.NORMAL)
        self.txt.delete("1.0", tk.END)
        self.last_summary_state = None
        self.last_summary_reason = None
        self.last_error_hint = None
        if self._session_busy():
            self._set_status("RUNNING")
        else:
            self._set_status("IDLE")

    def _export_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            initialfile=f"ur10_unified_gui_{int(time.time())}.log",
            filetypes=[("Log", "*.log"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(self.txt.get("1.0", tk.END), encoding="utf-8")
            self._append_log("Main", f"[INFO] 日志导出: {path}")
        except Exception as exc:
            self._append_log("Main", f"[ERROR] 导出日志失败: {exc}")
            self._set_status("WARN", "export_log_failed")

    def _save_config(self):
        if self.v_mode.get() == "Real":
            ui_cfg = self._gather_real()
        else:
            ui_cfg = self._gather_sim()

        cfg = UnifiedGUIConfig.from_dict({**self.config_data.to_dict(), **ui_cfg.to_dict()})
        cfg.mode = self.v_mode.get()
        cfg.auto_network_check = self.v_auto_network_check.get()

        try:
            CONFIG_PATH.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            self.config_data = cfg
            self._append_log("Main", f"[INFO] 配置已保存: {CONFIG_PATH}")
        except Exception as exc:
            self._append_log("Main", f"[ERROR] 配置保存失败: {exc}")
            self._set_status("WARN", "save_config_failed")

    def _load_config(self) -> UnifiedGUIConfig:
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                return UnifiedGUIConfig.from_dict(data)
            except Exception:
                pass
        return UnifiedGUIConfig()

    def _load_config_to_ui(self):
        cfg = self._load_config()
        self.config_data = cfg

        self.v_mode.set(cfg.mode)
        self.v_host_ip.set(cfg.host_ip)
        self.v_robot_ip.set(cfg.robot_ip)
        self.v_robot_subnet.set(cfg.robot_subnet)
        self.v_reverse_ip.set(cfg.reverse_ip or cfg.host_ip)
        self.v_wrist_delta.set(cfg.wrist3_delta)
        self.v_controller.set(cfg.controller)
        self.v_status_timeout.set(cfg.status_timeout)

        self.v_ur_type.set(cfg.ur_type)
        self.v_use_fake_hardware.set(cfg.use_fake_hardware)
        self.v_world.set(cfg.world)
        self.v_start_rviz.set(cfg.start_rviz)
        self.v_enable_gantry_rviz_control.set(cfg.enable_gantry_rviz_control)
        self.v_auto_network_check.set(cfg.auto_network_check)

        self.v_run_full_verify_script.set(cfg.run_full_verify_script)
        self.v_run_full_verify_wsl_script.set(cfg.run_full_verify_wsl_script)
        self.v_workspace_root.set(cfg.workspace_root)

        self._toggle_mode()
        self._append_log("Main", f"[INFO] 已加载配置: {CONFIG_PATH}")


def main():
    app = UnifiedGUIApp()
    app.mainloop()


if __name__ == "__main__":
    main()

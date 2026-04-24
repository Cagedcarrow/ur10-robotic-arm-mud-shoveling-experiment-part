#!/usr/bin/env python3
"""
UR10 Real Robot Verify GUI (WSL-only, no PowerShell)

Enhancements:
- Layered network checks: subnet, route, ping, TCP port, optional protocol probe.
- Safer protocol probe mode with default invalid command test (no business motion command).
- Better process stop behavior (terminate process group).
- Auto-detect script path candidates.
- Export logs and clearer status summary.
"""

from __future__ import annotations

import ipaddress
import json
import os
import queue
import re
import shlex
import signal
import socket
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
CONFIG_PATH = Path.home() / ".ur10_real_verify_gui.json"


def _discover_default_script_path() -> str:
    candidates = [
        SCRIPT_DIR / "run_full_verify_wsl.sh",
        BASE_DIR / "scripts" / "run_full_verify_wsl.sh",
        Path("/root/ur10_ws/src/docs/ur10_real_comm_实机微动验证总结/run_full_verify_wsl.sh"),
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return str(candidates[0])


@dataclass
class VerifyConfig:
    host_ip: str = "192.168.56.1"
    robot_ip: str = "192.168.56.101"
    robot_subnet: str = "192.168.56.0/24"
    ws_root: str = "/root/ur10_ws"
    wrist_delta: str = "0.5"
    controller: str = "scaled_joint_trajectory_controller"
    status_timeout: str = "600"
    launch_rviz: bool = False
    confirm_execute: bool = True
    script_path: str = _discover_default_script_path()

    tcp_port: str = "8001"
    tcp_timeout: str = "2.0"
    protocol_probe_enabled: bool = False
    protocol_probe_mode: str = "safe_invalid"
    protocol_probe_custom_hex: str = "00 90"
    auto_precheck_before_start: bool = True


class VerifyWorker(threading.Thread):
    def __init__(self, cfg: VerifyConfig, dry_run: bool = False, log_queue: "queue.Queue[str]" = None, done_cb=None):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.dry_run = dry_run
        self.log_queue = log_queue if log_queue is not None else queue.Queue()
        self.done_cb = done_cb
        self.proc: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        self._returncode: Optional[int] = None

    def stop(self):
        self._stop_event.set()
        if self.proc and self.proc.poll() is None:
            try:
                if os.name == "posix":
                    os.killpg(self.proc.pid, signal.SIGTERM)
                else:
                    self.proc.terminate()
            except Exception:
                pass

    def run(self):
        cmd = self._build_cmd()
        if self.dry_run:
            self.log_queue.put(f"[DRY RUN] {shlex.join(cmd)}\n")
            if self.done_cb:
                self.done_cb(0, "DRY RUN")
            return

        try:
            self.log_queue.put(f"[INFO] start: {shlex.join(cmd)}\n")
            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "bufsize": 1,
                "universal_newlines": True,
                "cwd": str(self.cfg.ws_root),
            }
            if os.name == "posix":
                kwargs["preexec_fn"] = os.setsid

            self.proc = subprocess.Popen(cmd, **kwargs)

            if self.proc.stdout:
                for line in self.proc.stdout:
                    if self._stop_event.is_set():
                        break
                    self.log_queue.put(line)

            self.proc.wait(timeout=0.5)
            self._returncode = self.proc.returncode
            self.log_queue.put(f"[INFO] process exited with code: {self._returncode}\n")
        except Exception as exc:
            self.log_queue.put(f"[ERROR] verify run error: {exc}\n")
            self._returncode = 1
        finally:
            if self.done_cb:
                self.done_cb(self._returncode, "")

    def _build_cmd(self):
        script = self.cfg.script_path
        base = ["bash", script]
        base += ["--host-ip", self.cfg.host_ip]
        base += ["--robot-ip", self.cfg.robot_ip]
        base += ["--robot-subnet", self.cfg.robot_subnet]
        base += ["--ws-root", self.cfg.ws_root]
        base += ["--wrist-delta", self.cfg.wrist_delta]
        base += ["--controller", self.cfg.controller]
        base += ["--status-timeout", self.cfg.status_timeout]
        if not self.cfg.launch_rviz:
            base.append("--no-rviz")
        if not self.cfg.confirm_execute:
            base.append("--no-confirm")
        return base


class UR10VerifyGUI(tk.Tk):
    SUMMARY_RE = re.compile(r"\[SUMMARY\]\s+state=(\w+)\s+reason=(.*?)(\s+|$)")

    def __init__(self):
        super().__init__()
        self.title("UR10 实机微动验证（高级网络诊断 GUI）")
        self.geometry("1100x840")

        self.worker: Optional[VerifyWorker] = None
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.cfg = self._load_config()

        self._build_vars()
        self._build_ui()
        self._poll_queue()

        if Path(self.cfg.script_path).exists():
            self._append_log(f"[INFO] 找到脚本: {self.cfg.script_path}\n")
        else:
            self._append_log(f"[WARN] 脚本不存在: {self.cfg.script_path}\n")

    def _build_vars(self):
        self.v_host_ip = tk.StringVar(value=self.cfg.host_ip)
        self.v_robot_ip = tk.StringVar(value=self.cfg.robot_ip)
        self.v_robot_subnet = tk.StringVar(value=self.cfg.robot_subnet)
        self.v_ws_root = tk.StringVar(value=self.cfg.ws_root)
        self.v_wrist_delta = tk.StringVar(value=self.cfg.wrist_delta)
        self.v_controller = tk.StringVar(value=self.cfg.controller)
        self.v_status_timeout = tk.StringVar(value=self.cfg.status_timeout)
        self.v_launch_rviz = tk.BooleanVar(value=self.cfg.launch_rviz)
        self.v_confirm_execute = tk.BooleanVar(value=self.cfg.confirm_execute)
        self.v_script_path = tk.StringVar(value=self.cfg.script_path)

        self.v_tcp_port = tk.StringVar(value=self.cfg.tcp_port)
        self.v_tcp_timeout = tk.StringVar(value=self.cfg.tcp_timeout)
        self.v_protocol_probe_enabled = tk.BooleanVar(value=self.cfg.protocol_probe_enabled)
        self.v_protocol_probe_mode = tk.StringVar(value=self.cfg.protocol_probe_mode)
        self.v_protocol_probe_custom_hex = tk.StringVar(value=self.cfg.protocol_probe_custom_hex)
        self.v_auto_precheck_before_start = tk.BooleanVar(value=self.cfg.auto_precheck_before_start)

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="主机IP（Windows侧）").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.v_host_ip, width=22).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(top, text="机器人IP").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.v_robot_ip, width=22).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(top, text="网段（CIDR）").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.v_robot_subnet, width=22).grid(row=2, column=1, sticky=tk.W)

        ttk.Label(top, text="WS Root").grid(row=3, column=0, sticky=tk.W)
        row_ws = ttk.Frame(top)
        row_ws.grid(row=3, column=1, sticky=tk.W)
        ttk.Entry(row_ws, textvariable=self.v_ws_root, width=40).pack(side=tk.LEFT)
        ttk.Button(row_ws, text="浏览", command=self._browse_ws_root).pack(side=tk.LEFT, padx=6)

        ttk.Label(top, text="wrist3_delta_deg").grid(row=4, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.v_wrist_delta, width=12).grid(row=4, column=1, sticky=tk.W)

        ttk.Label(top, text="initial_joint_controller").grid(row=5, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.v_controller, width=40).grid(row=5, column=1, sticky=tk.W)

        ttk.Label(top, text="status timeout(sec)").grid(row=6, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.v_status_timeout, width=12).grid(row=6, column=1, sticky=tk.W)

        ttk.Label(top, text="run_full_verify_wsl.sh 路径").grid(row=7, column=0, sticky=tk.W)
        row_script = ttk.Frame(top)
        row_script.grid(row=7, column=1, sticky=tk.W)
        ttk.Entry(row_script, textvariable=self.v_script_path, width=50).pack(side=tk.LEFT)
        ttk.Button(row_script, text="浏览", command=self._browse_script).pack(side=tk.LEFT, padx=6)

        net = ttk.LabelFrame(top, text="网络通讯高级检查", padding=8)
        net.grid(row=0, column=2, rowspan=8, sticky=tk.NW, padx=(24, 0))

        ttk.Label(net, text="TCP端口").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(net, textvariable=self.v_tcp_port, width=10).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(net, text="TCP超时(s)").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(net, textvariable=self.v_tcp_timeout, width=10).grid(row=1, column=1, sticky=tk.W)

        ttk.Checkbutton(net, text="启用协议探测", variable=self.v_protocol_probe_enabled).grid(row=2, column=0, columnspan=2, sticky=tk.W)

        ttk.Label(net, text="探测模式").grid(row=3, column=0, sticky=tk.W)
        combo = ttk.Combobox(
            net,
            textvariable=self.v_protocol_probe_mode,
            width=16,
            state="readonly",
            values=["safe_invalid", "A1", "A2", "A3", "custom_hex"],
        )
        combo.grid(row=3, column=1, sticky=tk.W)

        ttk.Label(net, text="自定义HEX").grid(row=4, column=0, sticky=tk.W)
        ttk.Entry(net, textvariable=self.v_protocol_probe_custom_hex, width=22).grid(row=4, column=1, sticky=tk.W)

        ttk.Label(net, text="注意：A1/A2/A3 可能触发真实动作", foreground="#aa0000").grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=(6, 0)
        )

        opts = ttk.Frame(top)
        opts.grid(row=8, column=1, sticky=tk.W, pady=(4, 2))
        ttk.Checkbutton(opts, text="启动 RViz", variable=self.v_launch_rviz).pack(side=tk.LEFT)
        ttk.Checkbutton(opts, text="需要人工确认", variable=self.v_confirm_execute).pack(side=tk.LEFT, padx=12)
        ttk.Checkbutton(opts, text="开始前自动预检查", variable=self.v_auto_precheck_before_start).pack(side=tk.LEFT)

        btns = ttk.Frame(top)
        btns.grid(row=9, column=0, columnspan=3, sticky=tk.W, pady=(8, 0))
        ttk.Button(btns, text="快速预检查", command=self._precheck).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="高级网络诊断", command=self._deep_network_check).pack(side=tk.LEFT, padx=2)
        self.btn_start = ttk.Button(btns, text="开始验证", command=self._start_verify)
        self.btn_start.pack(side=tk.LEFT, padx=2)
        self.btn_stop = ttk.Button(btns, text="停止", command=self._stop_verify, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Dry Run", command=lambda: self._start_verify(dry_run=True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="发送确认服务", command=self._confirm_service).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="查询控制器状态", command=self._check_controllers).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="清空日志", command=self._clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="导出日志", command=self._export_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="保存参数", command=self._save_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="加载参数", command=self._load_config_to_ui).pack(side=tk.LEFT, padx=2)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=8)

        body = ttk.Frame(self, padding=(10, 2))
        body.pack(fill=tk.BOTH, expand=True)

        ttk.Label(body, text="执行日志").pack(anchor=tk.W)
        self.txt = tk.Text(body, wrap=tk.WORD, height=30)
        self.txt.pack(fill=tk.BOTH, expand=True)
        self.txt.configure(font=("Consolas", 10))

        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _append_log(self, text: str):
        self.txt.configure(state=tk.NORMAL)
        self.txt.insert(tk.END, text)
        self.txt.see(tk.END)

        m = self.SUMMARY_RE.search(text)
        if m:
            state, reason, _ = m.groups()
            if state.upper() == "PASS":
                self.status_var.set(f"最终结果: PASS | {reason}")
            elif state.upper() == "FAIL":
                self.status_var.set(f"最终结果: FAIL | {reason}")

    def _poll_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    def _gather_cfg(self) -> VerifyConfig:
        return VerifyConfig(
            host_ip=self.v_host_ip.get().strip(),
            robot_ip=self.v_robot_ip.get().strip(),
            robot_subnet=self.v_robot_subnet.get().strip(),
            ws_root=self.v_ws_root.get().strip(),
            wrist_delta=self.v_wrist_delta.get().strip(),
            controller=self.v_controller.get().strip(),
            status_timeout=self.v_status_timeout.get().strip(),
            launch_rviz=bool(self.v_launch_rviz.get()),
            confirm_execute=bool(self.v_confirm_execute.get()),
            script_path=self.v_script_path.get().strip(),
            tcp_port=self.v_tcp_port.get().strip(),
            tcp_timeout=self.v_tcp_timeout.get().strip(),
            protocol_probe_enabled=bool(self.v_protocol_probe_enabled.get()),
            protocol_probe_mode=self.v_protocol_probe_mode.get().strip(),
            protocol_probe_custom_hex=self.v_protocol_probe_custom_hex.get().strip(),
            auto_precheck_before_start=bool(self.v_auto_precheck_before_start.get()),
        )

    def _validate_config(self, cfg: VerifyConfig) -> Tuple[bool, str]:
        if not cfg.host_ip:
            return False, "host-ip 不能为空"
        if not cfg.robot_ip:
            return False, "robot-ip 不能为空"
        if not cfg.robot_subnet:
            return False, "robot-subnet 不能为空"
        if not cfg.ws_root:
            return False, "ws-root 不能为空"

        try:
            ipaddress.ip_address(cfg.host_ip)
        except Exception:
            return False, f"非法 host-ip: {cfg.host_ip}"

        try:
            ipaddress.ip_address(cfg.robot_ip)
        except Exception:
            return False, f"非法 robot-ip: {cfg.robot_ip}"

        try:
            ipaddress.ip_network(cfg.robot_subnet, strict=False)
        except Exception:
            return False, f"非法 robot-subnet: {cfg.robot_subnet}"

        try:
            float(cfg.wrist_delta)
        except Exception:
            return False, "wrist3_delta_deg 必须是数字"

        try:
            int(cfg.status_timeout)
        except Exception:
            return False, "status-timeout 必须是整数"

        try:
            port = int(cfg.tcp_port)
            if not (1 <= port <= 65535):
                return False, "TCP端口范围必须是 1~65535"
        except Exception:
            return False, "TCP端口必须是整数"

        try:
            timeout = float(cfg.tcp_timeout)
            if timeout <= 0:
                return False, "TCP超时必须 > 0"
        except Exception:
            return False, "TCP超时必须是数字"

        if cfg.protocol_probe_mode not in {"safe_invalid", "A1", "A2", "A3", "custom_hex"}:
            return False, "协议探测模式非法"

        if cfg.protocol_probe_mode == "custom_hex" and cfg.protocol_probe_enabled:
            try:
                _ = bytes.fromhex(cfg.protocol_probe_custom_hex)
            except Exception:
                return False, "自定义HEX格式非法，请使用类似 '00 90'"

        if not Path(cfg.script_path).is_file():
            return False, f"找不到脚本: {cfg.script_path}"

        if not Path(cfg.ws_root).is_dir():
            return False, f"工作空间不存在: {cfg.ws_root}"

        return True, ""

    def _precheck(self):
        cfg = self._gather_cfg()
        ok, msg = self._validate_config(cfg)
        if not ok:
            messagebox.showerror("参数校验失败", msg)
            return

        self._append_log("[INFO] 开始快速预检查\n")

        def _run():
            hard_ok, warn_count = self._run_network_checks(cfg, deep=False)
            if hard_ok:
                self.log_queue.put(f"[SUMMARY] state=PASS reason=quick_precheck_done_warn={warn_count}\n")
            else:
                self.log_queue.put(f"[SUMMARY] state=FAIL reason=quick_precheck_blocked_warn={warn_count}\n")

        threading.Thread(target=_run, daemon=True).start()

    def _deep_network_check(self):
        cfg = self._gather_cfg()
        ok, msg = self._validate_config(cfg)
        if not ok:
            messagebox.showerror("参数校验失败", msg)
            return

        if cfg.protocol_probe_enabled and cfg.protocol_probe_mode in {"A1", "A2", "A3"}:
            sure = messagebox.askyesno(
                "安全提示",
                "你当前选择的协议探测是 A1/A2/A3，可能触发机械臂真实动作。\n确认继续执行高级网络诊断吗？",
            )
            if not sure:
                return

        self._append_log("[INFO] 开始高级网络诊断\n")

        def _run():
            hard_ok, warn_count = self._run_network_checks(cfg, deep=True)
            if hard_ok:
                self.log_queue.put(f"[SUMMARY] state=PASS reason=deep_check_done_warn={warn_count}\n")
            else:
                self.log_queue.put(f"[SUMMARY] state=FAIL reason=deep_check_blocked_warn={warn_count}\n")

        threading.Thread(target=_run, daemon=True).start()

    def _run_network_checks(self, cfg: VerifyConfig, deep: bool) -> Tuple[bool, int]:
        warn_count = 0
        hard_ok = True

        def warn(msg: str):
            nonlocal warn_count
            warn_count += 1
            self.log_queue.put(f"[WARN] {msg}\n")

        def fail(msg: str):
            nonlocal hard_ok
            hard_ok = False
            self.log_queue.put(f"[ERROR] {msg}\n")

        subnet = ipaddress.ip_network(cfg.robot_subnet, strict=False)
        host = ipaddress.ip_address(cfg.host_ip)
        robot = ipaddress.ip_address(cfg.robot_ip)

        if host not in subnet:
            warn(f"host-ip {cfg.host_ip} 不在网段 {cfg.robot_subnet}")
        if robot not in subnet:
            warn(f"robot-ip {cfg.robot_ip} 不在网段 {cfg.robot_subnet}")

        run_script = Path(cfg.script_path)
        if not os.access(run_script, os.X_OK):
            warn(f"脚本不可执行: {run_script}，尝试 chmod +x")
            try:
                run_script.chmod(run_script.stat().st_mode | 0o111)
                self.log_queue.put("[INFO] 已补齐脚本执行权限\n")
            except Exception as exc:
                fail(f"chmod 失败: {exc}")

        try:
            route_cmd = ["bash", "-lc", f"ip route get {shlex.quote(cfg.robot_ip)}"]
            route_res = subprocess.run(route_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if route_res.returncode == 0 and route_res.stdout.strip():
                self.log_queue.put(f"[INFO] route: {route_res.stdout.strip()}\n")
            else:
                warn("无法解析到机器人路由信息")
        except Exception as exc:
            warn(f"route 检查失败: {exc}")

        ping_rounds = 3 if deep else 1
        ping_pass = 0
        for idx in range(ping_rounds):
            ping_cmd = ["ping", "-c", "1", "-W", "2", cfg.robot_ip]
            try:
                ping = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if ping.returncode == 0:
                    ping_pass += 1
                    self.log_queue.put(f"[PASS] ping round={idx + 1}/{ping_rounds} 可达\n")
                else:
                    warn(f"ping round={idx + 1}/{ping_rounds} 不可达")
            except Exception as exc:
                warn(f"ping round={idx + 1}/{ping_rounds} 执行失败: {exc}")

        try:
            tcp_rounds = 3 if deep else 1
            tcp_pass = 0
            costs_ms = []
            port = int(cfg.tcp_port)
            timeout = float(cfg.tcp_timeout)
            for idx in range(tcp_rounds):
                ts = time.time()
                try:
                    with socket.create_connection((cfg.robot_ip, port), timeout=timeout):
                        cost = (time.time() - ts) * 1000.0
                        costs_ms.append(cost)
                        tcp_pass += 1
                        self.log_queue.put(
                            f"[PASS] TCP连接 round={idx + 1}/{tcp_rounds} {cfg.robot_ip}:{port} success, rtt={cost:.1f}ms\n"
                        )
                except Exception as exc:
                    warn(f"TCP连接 round={idx + 1}/{tcp_rounds} 失败: {exc}")
            if tcp_pass == 0:
                fail(f"TCP端口 {cfg.robot_ip}:{port} 完全不可达")
            elif deep and costs_ms:
                self.log_queue.put(
                    f"[INFO] TCP时延统计: min={min(costs_ms):.1f}ms avg={sum(costs_ms)/len(costs_ms):.1f}ms max={max(costs_ms):.1f}ms\n"
                )
        except Exception as exc:
            fail(f"TCP检查发生异常: {exc}")

        if cfg.protocol_probe_enabled:
            if self._run_protocol_probe(cfg):
                self.log_queue.put("[PASS] 协议探测完成\n")
            else:
                warn("协议探测失败")

        self.log_queue.put(
            f"[INFO] 网络检查完成 | host={cfg.host_ip} robot={cfg.robot_ip} subnet={cfg.robot_subnet} port={cfg.tcp_port}\n"
        )
        return hard_ok, warn_count

    def _protocol_payload(self, cfg: VerifyConfig) -> bytes:
        mode = cfg.protocol_probe_mode
        if mode == "safe_invalid":
            # 与 ur10_server_.py 的 command=data[1:2] 对齐，放一个未定义命令 0x90，
            # 预期收到 FF 错误回包，通常不会触发业务运动流程。
            return bytes.fromhex("00 90")
        if mode == "A1":
            return bytes.fromhex("00 A1")
        if mode == "A2":
            return bytes.fromhex("00 A2")
        if mode == "A3":
            return bytes.fromhex("00 A3")
        return bytes.fromhex(cfg.protocol_probe_custom_hex)

    def _run_protocol_probe(self, cfg: VerifyConfig) -> bool:
        try:
            payload = self._protocol_payload(cfg)
            port = int(cfg.tcp_port)
            timeout = float(cfg.tcp_timeout)
            self.log_queue.put(
                f"[INFO] 协议探测 mode={cfg.protocol_probe_mode} send={payload.hex(' ')} target={cfg.robot_ip}:{port}\n"
            )
            with socket.create_connection((cfg.robot_ip, port), timeout=timeout) as sock:
                sock.settimeout(timeout)
                sock.sendall(payload)
                data = sock.recv(1024)

            if not data:
                self.log_queue.put("[WARN] 协议探测未收到回包\n")
                return False

            self.log_queue.put(f"[INFO] 协议回包: {data.hex(' ')}\n")
            if data.startswith(b"\xEE") and data.endswith(b"\xDD"):
                if cfg.protocol_probe_mode == "safe_invalid" and len(data) >= 4 and data[3:4] == b"\xFF":
                    self.log_queue.put("[PASS] safe_invalid 收到预期错误码 FF（服务在线）\n")
                return True
            return True
        except socket.timeout:
            self.log_queue.put("[WARN] 协议探测超时\n")
            return False
        except Exception as exc:
            self.log_queue.put(f"[WARN] 协议探测异常: {exc}\n")
            return False

    def _start_verify(self, dry_run: bool = False):
        cfg = self._gather_cfg()
        ok, msg = self._validate_config(cfg)
        if not ok:
            messagebox.showerror("参数校验失败", msg)
            return

        if self.worker and self.worker.is_alive():
            messagebox.showwarning("提示", "已有验证任务在运行")
            return

        if cfg.protocol_probe_enabled and cfg.protocol_probe_mode in {"A1", "A2", "A3"}:
            sure = messagebox.askyesno(
                "安全提示",
                "当前启用了 A1/A2/A3 协议探测，这可能触发机械臂动作。\n是否继续开始验证？",
            )
            if not sure:
                return

        if cfg.auto_precheck_before_start:
            self.log_queue.put("[INFO] 开始验证前执行自动预检查\n")
            hard_ok, warn_count = self._run_network_checks(cfg, deep=False)
            if not hard_ok:
                go_on = messagebox.askyesno(
                    "预检查失败",
                    f"检测到阻断问题（warn={warn_count}）。\n仍要继续执行验证脚本吗？",
                )
                if not go_on:
                    self.status_var.set("已取消：预检查阻断")
                    return

        self._save_config()
        self.log_queue.put("-----------------------------------------\n")
        self._append_log(f"[INFO] 配置: {cfg}\n")

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("运行中...")

        self.worker = VerifyWorker(
            cfg=cfg,
            dry_run=dry_run,
            log_queue=self.log_queue,
            done_cb=self._on_verify_done,
        )
        self.worker.start()

    def _stop_verify(self):
        if self.worker:
            self.worker.stop()
            self.log_queue.put("[INFO] 已发出停止信号\n")

    def _on_verify_done(self, retcode: int, _msg: str):
        self.after(0, lambda: self._finalize_after_verify(retcode))

    def _finalize_after_verify(self, retcode: int):
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        if retcode == 0:
            self.status_var.set("完成：PASS")
        elif retcode == 1:
            self.status_var.set("完成：FAIL")
        else:
            self.status_var.set(f"退出码：{retcode}")

    def _confirm_service(self):
        cfg = self._gather_cfg()
        if not Path(cfg.ws_root).is_dir():
            messagebox.showerror("错误", "ws-root 不存在")
            return

        cmd = [
            "bash",
            "-lc",
            (
                f"source /opt/ros/humble/setup.bash\n"
                f"if [ -f \"{cfg.ws_root}/install/setup.bash\" ]; then source \"{cfg.ws_root}/install/setup.bash\"; fi\n"
                "ros2 service call /ur10_real_comm/confirm_execute std_srvs/srv/Trigger '{}'"
            ),
        ]

        def _run():
            try:
                self.log_queue.put("[INFO] 发送确认服务\n")
                p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.log_queue.put(p.stdout)
                self.log_queue.put(f"[INFO] confirm service return {p.returncode}\n")
                if p.returncode == 0:
                    self.log_queue.put("[PASS] confirm command done\n")
                else:
                    self.log_queue.put("[WARN] confirm command failed\n")
            except Exception as exc:
                self.log_queue.put(f"[ERROR] confirm command error: {exc}\n")

        threading.Thread(target=_run, daemon=True).start()

    def _check_controllers(self):
        cfg = self._gather_cfg()
        if not Path(cfg.ws_root).is_dir():
            messagebox.showerror("错误", "ws-root 不存在")
            return

        cmd = [
            "bash",
            "-lc",
            (
                f"source /opt/ros/humble/setup.bash\n"
                f"if [ -f \"{cfg.ws_root}/install/setup.bash\" ]; then source \"{cfg.ws_root}/install/setup.bash\"; fi\n"
                "ros2 control list_controllers"
            ),
        ]

        def _run():
            self.log_queue.put("[INFO] 查询控制器列表\n")
            try:
                p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.log_queue.put(p.stdout)
                self.log_queue.put(f"[INFO] controller check return {p.returncode}\n")
            except Exception as exc:
                self.log_queue.put(f"[ERROR] 控制器查询失败: {exc}\n")

        threading.Thread(target=_run, daemon=True).start()

    def _clear_logs(self):
        self.txt.configure(state=tk.NORMAL)
        self.txt.delete("1.0", tk.END)
        self.status_var.set("就绪")

    def _export_logs(self):
        default_name = f"ur10_verify_gui_log_{int(time.time())}.log"
        path = filedialog.asksaveasfilename(
            title="导出日志",
            defaultextension=".log",
            initialfile=default_name,
            filetypes=[("Log", "*.log"), ("Text", "*.txt"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            content = self.txt.get("1.0", tk.END)
            Path(path).write_text(content, encoding="utf-8")
            self._append_log(f"[INFO] 日志已导出: {path}\n")
        except Exception as exc:
            self._append_log(f"[ERROR] 导出日志失败: {exc}\n")

    def _browse_ws_root(self):
        path = filedialog.askdirectory(initialdir=self.v_ws_root.get())
        if path:
            self.v_ws_root.set(path)

    def _browse_script(self):
        path = filedialog.askopenfilename(initialdir=str(SCRIPT_DIR), filetypes=[("Shell", "*.sh"), ("All", "*.*")])
        if path:
            self.v_script_path.set(path)

    def _save_config(self):
        cfg = asdict(self._gather_cfg())
        try:
            CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            self._append_log(f"[INFO] 配置已保存: {CONFIG_PATH}\n")
        except Exception as exc:
            self._append_log(f"[ERROR] 保存配置失败: {exc}\n")

    def _load_config(self) -> VerifyConfig:
        try:
            if CONFIG_PATH.exists():
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if "script_path" not in data or not data.get("script_path"):
                    data["script_path"] = _discover_default_script_path()
                return VerifyConfig(**data)
        except Exception:
            pass
        return VerifyConfig(script_path=_discover_default_script_path())

    def _load_config_to_ui(self):
        cfg = self._load_config()
        self.v_host_ip.set(cfg.host_ip)
        self.v_robot_ip.set(cfg.robot_ip)
        self.v_robot_subnet.set(cfg.robot_subnet)
        self.v_ws_root.set(cfg.ws_root)
        self.v_wrist_delta.set(cfg.wrist_delta)
        self.v_controller.set(cfg.controller)
        self.v_status_timeout.set(cfg.status_timeout)
        self.v_launch_rviz.set(cfg.launch_rviz)
        self.v_confirm_execute.set(cfg.confirm_execute)
        self.v_script_path.set(cfg.script_path)
        self.v_tcp_port.set(cfg.tcp_port)
        self.v_tcp_timeout.set(cfg.tcp_timeout)
        self.v_protocol_probe_enabled.set(cfg.protocol_probe_enabled)
        self.v_protocol_probe_mode.set(cfg.protocol_probe_mode)
        self.v_protocol_probe_custom_hex.set(cfg.protocol_probe_custom_hex)
        self.v_auto_precheck_before_start.set(cfg.auto_precheck_before_start)
        self._append_log(f"[INFO] 已加载配置: {CONFIG_PATH}\n")


def main():
    app = UR10VerifyGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

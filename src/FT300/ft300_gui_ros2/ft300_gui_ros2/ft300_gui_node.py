#!/usr/bin/env python3
"""FT300 integrated GUI ROS 2 node.

Features:
- USB connection test (open serial + receive valid FT300 frame)
- FT300 realtime reading and /ft300/wrench publishing
- Realtime GUI display with rolling plots
- Session save on stop: CSV + PNG + JSON (Asia/Shanghai local time)
"""

import csv
import json
import math
import os
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Deque, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import rclpy
from geometry_msgs.msg import WrenchStamped
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
import tkinter as tk
from tkinter import messagebox, ttk

try:
    import serial
    from serial import SerialException
except ImportError as exc:
    raise ImportError("pyserial is required. Install via: sudo apt install python3-serial") from exc


FT300_FRAME_SIZE = 16
FT300_HEADER = b"\x20\x4E"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def modbus_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def parse_ft300_frame(frame: bytes, validate_crc: bool = True) -> Tuple[float, float, float, float, float, float]:
    if len(frame) != FT300_FRAME_SIZE:
        raise ValueError("invalid_length")
    if frame[:2] != FT300_HEADER:
        raise ValueError("invalid_header")

    if validate_crc:
        expected_crc = frame[-2] | (frame[-1] << 8)
        computed_crc = modbus_crc16(frame[:-2])
        if expected_crc != computed_crc:
            raise ValueError("invalid_crc")

    raw = []
    for i in range(6):
        offset = 2 + i * 2
        raw.append(struct.unpack_from("<h", frame, offset)[0])

    fx = raw[0] / 100.0
    fy = raw[1] / 100.0
    fz = raw[2] / 100.0
    tx = raw[3] / 1000.0
    ty = raw[4] / 1000.0
    tz = raw[5] / 1000.0
    return (fx, fy, fz, tx, ty, tz)


def build_fc16_start_stream(slave_id: int) -> bytes:
    # Write 0x0200 to register 0x019A (410)
    payload = bytes([
        slave_id & 0xFF,
        0x10,
        0x01,
        0x9A,
        0x00,
        0x01,
        0x02,
        0x02,
        0x00,
    ])
    crc = modbus_crc16(payload)
    return payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


class SerialClient:
    def __init__(self, port: str, baudrate: int, timeout: float, slave_id: int) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.slave_id = slave_id
        self.conn: Optional[serial.Serial] = None
        self.buffer = bytearray()
        self._lock = threading.Lock()

    def is_open(self) -> bool:
        return self.conn is not None and self.conn.is_open

    def open(self) -> None:
        with self._lock:
            if self.is_open():
                return
            self.conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
            )
            self.buffer.clear()

    def close(self) -> None:
        with self._lock:
            if self.conn is not None:
                try:
                    if self.conn.is_open:
                        self.conn.close()
                finally:
                    self.conn = None
            self.buffer.clear()

    def start_stream(self) -> None:
        with self._lock:
            if not self.is_open():
                raise SerialException("serial port not open")
            req = build_fc16_start_stream(self.slave_id)
            self.conn.reset_input_buffer()
            self.conn.write(req)
            self.conn.flush()
            self.conn.read(8)

    def stop_stream(self) -> None:
        with self._lock:
            if not self.is_open():
                return
            self.conn.write(b"\xFF" * 50)
            self.conn.flush()

    def read_frame(self) -> Optional[bytes]:
        with self._lock:
            if not self.is_open():
                return None

            incoming = self.conn.read(64)
            if incoming:
                self.buffer.extend(incoming)

            if len(self.buffer) > 4096:
                self.buffer = self.buffer[-256:]

            while len(self.buffer) >= FT300_FRAME_SIZE:
                idx = self.buffer.find(FT300_HEADER)
                if idx < 0:
                    self.buffer = self.buffer[-1:]
                    return None
                if idx > 0:
                    del self.buffer[:idx]
                if len(self.buffer) < FT300_FRAME_SIZE:
                    return None
                frame = bytes(self.buffer[:FT300_FRAME_SIZE])
                del self.buffer[:FT300_FRAME_SIZE]
                return frame
            return None


@dataclass
class SessionSummary:
    ok: bool
    directory: str
    message: str


class AcquisitionSession:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.active = False
        self.samples: List[Tuple[datetime, float, float, float, float, float, float]] = []
        self.start_local: Optional[datetime] = None
        self.end_local: Optional[datetime] = None
        self.start_monotonic = 0.0
        self.end_monotonic = 0.0
        self.crc_fail_count = 0
        self.parse_fail_count = 0
        self.read_fail_count = 0
        self.serial_number: Optional[str] = None

    def start(self) -> None:
        self.reset()
        self.active = True
        self.start_local = datetime.now(SHANGHAI_TZ)
        self.start_monotonic = time.monotonic()

    def add_sample(self, ts_local: datetime, values: Tuple[float, float, float, float, float, float]) -> None:
        self.samples.append((ts_local, *values))

    def stop(self) -> None:
        self.active = False
        self.end_local = datetime.now(SHANGHAI_TZ)
        self.end_monotonic = time.monotonic()

    def _session_dir(self, save_root_dir: str) -> Path:
        root = Path(os.path.expanduser(save_root_dir))
        root.mkdir(parents=True, exist_ok=True)
        stamp = (self.end_local or datetime.now(SHANGHAI_TZ)).strftime("%Y%m%d_%H%M%S")
        session_dir = root / f"session_{stamp}"
        suffix = 1
        while session_dir.exists():
            session_dir = root / f"session_{stamp}_{suffix}"
            suffix += 1
        session_dir.mkdir(parents=True, exist_ok=False)
        return session_dir

    def _save_csv(self, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_local_iso", "force_x", "force_y", "force_z", "torque_x", "torque_y", "torque_z"])
            for row in self.samples:
                writer.writerow([
                    row[0].isoformat(),
                    f"{row[1]:.6f}",
                    f"{row[2]:.6f}",
                    f"{row[3]:.6f}",
                    f"{row[4]:.6f}",
                    f"{row[5]:.6f}",
                    f"{row[6]:.6f}",
                ])

    def _save_plot(self, path: Path) -> None:
        fig = plt.figure(figsize=(10, 6))
        ax_force = fig.add_subplot(2, 1, 1)
        ax_torque = fig.add_subplot(2, 1, 2)

        if self.samples:
            t0 = self.samples[0][0]
            ts = [(row[0] - t0).total_seconds() for row in self.samples]
            fx = [row[1] for row in self.samples]
            fy = [row[2] for row in self.samples]
            fz = [row[3] for row in self.samples]
            tx = [row[4] for row in self.samples]
            ty = [row[5] for row in self.samples]
            tz = [row[6] for row in self.samples]

            ax_force.plot(ts, fx, label="Fx")
            ax_force.plot(ts, fy, label="Fy")
            ax_force.plot(ts, fz, label="Fz")
            ax_force.set_ylabel("Force (N)")
            ax_force.legend(loc="upper right")
            ax_force.grid(True)

            ax_torque.plot(ts, tx, label="Tx")
            ax_torque.plot(ts, ty, label="Ty")
            ax_torque.plot(ts, tz, label="Tz")
            ax_torque.set_ylabel("Torque (Nm)")
            ax_torque.set_xlabel("Time (s)")
            ax_torque.legend(loc="upper right")
            ax_torque.grid(True)

        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)

    def _save_meta(self, path: Path, meta: Dict[str, object]) -> None:
        with path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def save(self, save_root_dir: str, base_meta: Dict[str, object]) -> SessionSummary:
        if self.start_local is None or self.end_local is None:
            return SessionSummary(False, "", "会话起止时间无效，无法保存")

        session_dir = self._session_dir(save_root_dir)

        csv_path = session_dir / "wrench_data.csv"
        png_path = session_dir / "wrench_plot.png"
        json_path = session_dir / "session_meta.json"

        self._save_csv(csv_path)
        self._save_plot(png_path)

        duration = max(0.0, self.end_monotonic - self.start_monotonic)
        sample_count = len(self.samples)
        avg_rate = (sample_count / duration) if duration > 0.0 else 0.0

        meta = {
            **base_meta,
            "start_time_local": self.start_local.isoformat(),
            "end_time_local": self.end_local.isoformat(),
            "duration_sec": duration,
            "sample_count": sample_count,
            "average_rate_hz": avg_rate,
            "crc_fail_count": self.crc_fail_count,
            "parse_fail_count": self.parse_fail_count,
            "read_fail_count": self.read_fail_count,
            "serial_number": self.serial_number,
            "files": {
                "csv": str(csv_path),
                "png": str(png_path),
                "meta": str(json_path),
            },
        }
        self._save_meta(json_path, meta)
        return SessionSummary(True, str(session_dir), "保存成功")


class FT300GuiNode(Node):
    def __init__(self) -> None:
        super().__init__("ft300_gui_node")

        self.declare_parameter("port", "/dev/ttyUSB0")
        self.declare_parameter("baudrate", 19200)
        self.declare_parameter("timeout", 0.1)
        self.declare_parameter("frame_id", "ft300_sensor_link")
        self.declare_parameter("publish_rate", 100.0)
        self.declare_parameter("validate_crc", True)
        self.declare_parameter("save_root_dir", "~/ft300_sessions")
        self.declare_parameter("plot_window_sec", 30)
        self.declare_parameter("slave_id", 9)

        self.port = str(self.get_parameter("port").value)
        self.baudrate = int(self.get_parameter("baudrate").value)
        self.timeout = float(self.get_parameter("timeout").value)
        self.frame_id = str(self.get_parameter("frame_id").value)
        self.publish_rate = max(1.0, float(self.get_parameter("publish_rate").value))
        self.validate_crc = bool(self.get_parameter("validate_crc").value)
        self.save_root_dir = str(self.get_parameter("save_root_dir").value)
        self.plot_window_sec = int(self.get_parameter("plot_window_sec").value)
        self.slave_id = int(self.get_parameter("slave_id").value)

        self.publisher = self.create_publisher(WrenchStamped, "/ft300/wrench", 50)
        self.serial_client = SerialClient(self.port, self.baudrate, self.timeout, self.slave_id)

        self._lock = threading.Lock()
        self.sample_queue: Queue = Queue(maxsize=2000)

        self.session = AcquisitionSession()
        self.acquiring = False
        self.connected = False
        self.last_error = ""

        self.total_sample_count = 0
        self.last_publish_time = 0.0
        self.last_values = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self._timer_cb)

        self.get_logger().info("FT300 GUI node started.")

    def test_usb_connection(self, timeout_sec: float = 2.0) -> Tuple[bool, str]:
        try:
            self.serial_client.open()
            self.serial_client.start_stream()
        except Exception as exc:  # pylint: disable=broad-except
            self.connected = False
            self.last_error = str(exc)
            self.serial_client.close()
            return False, f"USB测试失败: {exc}"

        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            try:
                frame = self.serial_client.read_frame()
            except Exception as exc:  # pylint: disable=broad-except
                self.connected = False
                self.last_error = str(exc)
                self.serial_client.close()
                return False, f"串口读取失败: {exc}"

            if frame is None:
                time.sleep(0.01)
                continue

            try:
                values = parse_ft300_frame(frame, validate_crc=self.validate_crc)
                self.connected = True
                self.last_values = values
                return True, "USB连接测试成功: 已收到有效FT300数据帧"
            except ValueError:
                continue

        self.connected = False
        self.serial_client.close()
        return False, "USB测试失败: 未在超时内收到有效FT300数据帧"

    def start_acquisition(self) -> Tuple[bool, str]:
        with self._lock:
            if self.acquiring:
                return False, "采集中，无需重复开始"

        if not self.serial_client.is_open():
            ok, msg = self.test_usb_connection()
            if not ok:
                return False, f"开始采集失败: {msg}"

        with self._lock:
            self.session.start()
            self.acquiring = True
            self.last_error = ""

        return True, "采集已开始"

    def stop_acquisition(self) -> SessionSummary:
        with self._lock:
            if not self.acquiring:
                return SessionSummary(False, "", "当前未在采集")
            self.acquiring = False
            self.session.stop()

            base_meta = {
                "port": self.port,
                "baudrate": self.baudrate,
                "timeout": self.timeout,
                "frame_id": self.frame_id,
                "publish_rate": self.publish_rate,
                "validate_crc": self.validate_crc,
                "timezone": "Asia/Shanghai",
            }
            summary = self.session.save(self.save_root_dir, base_meta)
            self.session.reset()
            return summary

    def stop_and_close(self) -> None:
        with self._lock:
            self.acquiring = False
        try:
            self.serial_client.stop_stream()
        except Exception:
            pass
        self.serial_client.close()

    def get_runtime_status(self) -> Dict[str, object]:
        with self._lock:
            now = time.monotonic()
            node_ok = self.publisher is not None and (self.total_sample_count == 0 or now - self.last_publish_time < 2.0)
            return {
                "connected": self.connected,
                "acquiring": self.acquiring,
                "node_ok": node_ok,
                "sample_count": self.total_sample_count,
                "last_error": self.last_error,
                "last_values": self.last_values,
            }

    def _publish_wrench(self, values: Tuple[float, float, float, float, float, float]) -> None:
        fx, fy, fz, tx, ty, tz = values
        msg = WrenchStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.wrench.force.x = fx
        msg.wrench.force.y = fy
        msg.wrench.force.z = fz
        msg.wrench.torque.x = tx
        msg.wrench.torque.y = ty
        msg.wrench.torque.z = tz
        self.publisher.publish(msg)

    def _timer_cb(self) -> None:
        with self._lock:
            is_acquiring = self.acquiring

        if not is_acquiring:
            return

        if not self.serial_client.is_open():
            self.connected = False
            self.last_error = "串口未连接"
            return

        try:
            frame = self.serial_client.read_frame()
        except Exception as exc:  # pylint: disable=broad-except
            self.connected = False
            self.last_error = f"串口读取异常: {exc}"
            with self._lock:
                self.session.read_fail_count += 1
                self.acquiring = False
            return

        if frame is None:
            return

        try:
            values = parse_ft300_frame(frame, validate_crc=self.validate_crc)
        except ValueError as exc:
            reason = str(exc)
            with self._lock:
                if reason == "invalid_crc":
                    self.session.crc_fail_count += 1
                else:
                    self.session.parse_fail_count += 1
            return

        ts_local = datetime.now(SHANGHAI_TZ)
        with self._lock:
            self.connected = True
            self.last_values = values
            self.total_sample_count += 1
            self.last_publish_time = time.monotonic()
            self.session.add_sample(ts_local, values)

        self._publish_wrench(values)

        try:
            self.sample_queue.put_nowait((ts_local, values))
        except Exception:
            pass


class FT300GuiApp(tk.Tk):
    def __init__(self, node: FT300GuiNode) -> None:
        super().__init__()
        self.node = node
        self.title("FT300 一体化可视化 GUI (ROS 2)")
        self.geometry("1200x820")

        self._last_redraw_time = 0.0
        self._plot_window_sec = max(5, self.node.plot_window_sec)

        self.time_buffer: Deque[datetime] = deque()
        self.fx_buf: Deque[float] = deque()
        self.fy_buf: Deque[float] = deque()
        self.fz_buf: Deque[float] = deque()
        self.tx_buf: Deque[float] = deque()
        self.ty_buf: Deque[float] = deque()
        self.tz_buf: Deque[float] = deque()

        self.value_vars = {name: tk.StringVar(value="0.000") for name in ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]}
        self.status_usb_var = tk.StringVar(value="未测试")
        self.status_node_var = tk.StringVar(value="未运行")
        self.status_acq_var = tk.StringVar(value="未采集")
        self.status_save_var = tk.StringVar(value="尚未保存")
        self.status_error_var = tk.StringVar(value="")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll)

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(top, text="USB测试连接", command=self._on_usb_test).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="开始采集", command=self._on_start).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="停止采集并保存", command=self._on_stop).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="退出", command=self._on_close).pack(side=tk.LEFT, padx=4)

        status = ttk.LabelFrame(self, text="系统状态")
        status.pack(fill=tk.X, padx=8, pady=6)

        grid = ttk.Frame(status)
        grid.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(grid, text="USB连接:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(grid, textvariable=self.status_usb_var).grid(row=0, column=1, sticky=tk.W, padx=4)

        ttk.Label(grid, text="数据节点测试:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        ttk.Label(grid, textvariable=self.status_node_var).grid(row=0, column=3, sticky=tk.W, padx=4)

        ttk.Label(grid, text="采集状态:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(grid, textvariable=self.status_acq_var).grid(row=1, column=1, sticky=tk.W, padx=4)

        ttk.Label(grid, text="保存结果:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0))
        ttk.Label(grid, textvariable=self.status_save_var).grid(row=1, column=3, sticky=tk.W, padx=4)

        ttk.Label(grid, text="错误信息:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(grid, textvariable=self.status_error_var, foreground="#aa2222").grid(
            row=2, column=1, columnspan=3, sticky=tk.W, padx=4
        )

        values_frame = ttk.LabelFrame(self, text="实时六维力数据")
        values_frame.pack(fill=tk.X, padx=8, pady=6)

        for idx, name in enumerate(["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]):
            unit = "N" if name.startswith("F") else "Nm"
            box = ttk.Frame(values_frame)
            box.grid(row=0, column=idx, padx=8, pady=6, sticky=tk.NSEW)
            ttk.Label(box, text=name, font=("TkDefaultFont", 10, "bold")).pack()
            ttk.Label(box, textvariable=self.value_vars[name], font=("TkDefaultFont", 12)).pack()
            ttk.Label(box, text=unit).pack()

        plot_frame = ttk.LabelFrame(self, text="实时曲线")
        plot_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self.fig = Figure(figsize=(10, 5), dpi=100)
        self.ax_f = self.fig.add_subplot(2, 1, 1)
        self.ax_t = self.fig.add_subplot(2, 1, 2)

        self.line_fx, = self.ax_f.plot([], [], label="Fx")
        self.line_fy, = self.ax_f.plot([], [], label="Fy")
        self.line_fz, = self.ax_f.plot([], [], label="Fz")
        self.ax_f.set_ylabel("Force (N)")
        self.ax_f.grid(True)
        self.ax_f.legend(loc="upper right")

        self.line_tx, = self.ax_t.plot([], [], label="Tx")
        self.line_ty, = self.ax_t.plot([], [], label="Ty")
        self.line_tz, = self.ax_t.plot([], [], label="Tz")
        self.ax_t.set_ylabel("Torque (Nm)")
        self.ax_t.set_xlabel("Time (s)")
        self.ax_t.grid(True)
        self.ax_t.legend(loc="upper right")

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_usb_test(self) -> None:
        ok, msg = self.node.test_usb_connection()
        self.status_usb_var.set("通信正常" if ok else "通信失败")
        self.status_error_var.set("" if ok else msg)
        if ok:
            messagebox.showinfo("USB测试", msg)
        else:
            messagebox.showerror("USB测试", msg)

    def _on_start(self) -> None:
        ok, msg = self.node.start_acquisition()
        if ok:
            self.status_acq_var.set("采集中")
            self.status_save_var.set("采集中，尚未保存")
            self.status_error_var.set("")
            messagebox.showinfo("采集", msg)
        else:
            self.status_error_var.set(msg)
            messagebox.showerror("采集", msg)

    def _on_stop(self) -> None:
        summary = self.node.stop_acquisition()
        if summary.ok:
            self.status_acq_var.set("已停止")
            self.status_save_var.set(f"已保存: {summary.directory}")
            self.status_error_var.set("")
            messagebox.showinfo("保存完成", f"{summary.message}\n目录: {summary.directory}")
        else:
            self.status_error_var.set(summary.message)
            messagebox.showwarning("停止采集", summary.message)

    def _trim_plot_buffers(self) -> None:
        if not self.time_buffer:
            return
        latest = self.time_buffer[-1]
        threshold = latest.timestamp() - self._plot_window_sec
        while self.time_buffer and self.time_buffer[0].timestamp() < threshold:
            self.time_buffer.popleft()
            self.fx_buf.popleft()
            self.fy_buf.popleft()
            self.fz_buf.popleft()
            self.tx_buf.popleft()
            self.ty_buf.popleft()
            self.tz_buf.popleft()

    def _redraw_plot(self) -> None:
        if not self.time_buffer:
            return

        t0 = self.time_buffer[0]
        ts = [(t - t0).total_seconds() for t in self.time_buffer]

        self.line_fx.set_data(ts, list(self.fx_buf))
        self.line_fy.set_data(ts, list(self.fy_buf))
        self.line_fz.set_data(ts, list(self.fz_buf))
        self.line_tx.set_data(ts, list(self.tx_buf))
        self.line_ty.set_data(ts, list(self.ty_buf))
        self.line_tz.set_data(ts, list(self.tz_buf))

        self.ax_f.relim()
        self.ax_f.autoscale_view()
        self.ax_t.relim()
        self.ax_t.autoscale_view()
        self.canvas.draw_idle()

    def _update_node_status(self) -> None:
        status = self.node.get_runtime_status()
        self.status_node_var.set("发布正常" if status["node_ok"] else "发布异常")
        if status["acquiring"]:
            self.status_acq_var.set("采集中")
        if status["connected"]:
            self.status_usb_var.set("通信正常")
        if status["last_error"]:
            self.status_error_var.set(str(status["last_error"]))

    def _poll(self) -> None:
        updated = False
        while True:
            try:
                ts_local, values = self.node.sample_queue.get_nowait()
            except Empty:
                break

            fx, fy, fz, tx, ty, tz = values
            self.time_buffer.append(ts_local)
            self.fx_buf.append(fx)
            self.fy_buf.append(fy)
            self.fz_buf.append(fz)
            self.tx_buf.append(tx)
            self.ty_buf.append(ty)
            self.tz_buf.append(tz)

            self.value_vars["Fx"].set(f"{fx:.3f}")
            self.value_vars["Fy"].set(f"{fy:.3f}")
            self.value_vars["Fz"].set(f"{fz:.3f}")
            self.value_vars["Tx"].set(f"{tx:.4f}")
            self.value_vars["Ty"].set(f"{ty:.4f}")
            self.value_vars["Tz"].set(f"{tz:.4f}")
            updated = True

        self._update_node_status()

        if updated:
            self._trim_plot_buffers()
            now = time.monotonic()
            if now - self._last_redraw_time > 0.2:
                self._redraw_plot()
                self._last_redraw_time = now

        self.after(100, self._poll)

    def _on_close(self) -> None:
        try:
            status = self.node.get_runtime_status()
            if status["acquiring"]:
                summary = self.node.stop_acquisition()
                if summary.ok:
                    self.status_save_var.set(f"退出前自动保存: {summary.directory}")
            self.node.stop_and_close()
        except Exception:
            pass
        self.destroy()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FT300GuiNode()

    executor = SingleThreadedExecutor()
    executor.add_node(node)

    spin_stop = threading.Event()

    def spin_loop() -> None:
        while rclpy.ok() and not spin_stop.is_set():
            executor.spin_once(timeout_sec=0.1)

    spin_thread = threading.Thread(target=spin_loop, daemon=True)
    spin_thread.start()

    app = FT300GuiApp(node)
    app.mainloop()

    spin_stop.set()
    spin_thread.join(timeout=1.0)

    executor.remove_node(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

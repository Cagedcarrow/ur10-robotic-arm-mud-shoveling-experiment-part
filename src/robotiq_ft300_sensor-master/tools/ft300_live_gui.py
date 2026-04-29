#!/usr/bin/env python3
"""Standalone FT300 live GUI over serial.

Directly talks to FT300 on /dev/ttyUSB0, starts stream mode, and displays:
- Realtime Fx/Fy/Fz/Mx/My/Mz values
- Rolling force and torque plots
- Connection / acquisition status
"""

from __future__ import annotations

import argparse
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from typing import Deque, Optional, Tuple

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import serial
import tkinter as tk
from tkinter import messagebox, ttk


FT300_FRAME_SIZE = 16
FT300_HEADER = b"\x20\x4E"


def modbus_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_fc16_start_stream(slave_id: int) -> bytes:
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


def parse_ft300_frame(frame: bytes) -> Tuple[float, float, float, float, float, float]:
    if len(frame) != FT300_FRAME_SIZE:
        raise ValueError("invalid_length")
    if frame[:2] != FT300_HEADER:
        raise ValueError("invalid_header")

    expected_crc = frame[-2] | (frame[-1] << 8)
    computed_crc = modbus_crc16(frame[:-2])
    if expected_crc != computed_crc:
        raise ValueError("invalid_crc")

    raw = [struct.unpack_from("<h", frame, 2 + i * 2)[0] for i in range(6)]
    return (
        raw[0] / 100.0,
        raw[1] / 100.0,
        raw[2] / 100.0,
        raw[3] / 1000.0,
        raw[4] / 1000.0,
        raw[5] / 1000.0,
    )


class FT300SerialClient:
    def __init__(self, port: str, baudrate: int, timeout: float, slave_id: int) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.slave_id = slave_id
        self.conn: Optional[serial.Serial] = None
        self.buffer = bytearray()
        self._lock = threading.Lock()

    def open(self) -> None:
        with self._lock:
            if self.conn is not None and self.conn.is_open:
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

    def stop_stream(self) -> None:
        with self._lock:
            if self.conn is None or not self.conn.is_open:
                return
            self.conn.write(b"\xFF" * 50)
            self.conn.flush()

    def start_stream(self) -> None:
        with self._lock:
            if self.conn is None or not self.conn.is_open:
                raise serial.SerialException("serial port not open")
            req = build_fc16_start_stream(self.slave_id)
            self.conn.reset_input_buffer()
            self.conn.write(req)
            self.conn.flush()
            self.conn.read(64)

    def read_frame(self) -> Optional[bytes]:
        with self._lock:
            if self.conn is None or not self.conn.is_open:
                return None

            incoming = self.conn.read(256)
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
class FT300Sample:
    ts: float
    values: Tuple[float, float, float, float, float, float]


class FT300Gui(tk.Tk):
    def __init__(self, port: str, baudrate: int, timeout: float, slave_id: int, window_sec: int) -> None:
        super().__init__()
        self.title("FT300 Live Serial GUI")
        self.geometry("1280x840")

        self.client = FT300SerialClient(port, baudrate, timeout, slave_id)
        self.window_sec = max(5, window_sec)
        self.queue: Queue[FT300Sample] = Queue(maxsize=5000)
        self.stop_event = threading.Event()
        self.reader_thread: Optional[threading.Thread] = None

        self.connected = False
        self.acquiring = False
        self.sample_count = 0
        self.crc_fail_count = 0
        self.last_error = ""

        self.time_buf: Deque[float] = deque()
        self.fx_buf: Deque[float] = deque()
        self.fy_buf: Deque[float] = deque()
        self.fz_buf: Deque[float] = deque()
        self.mx_buf: Deque[float] = deque()
        self.my_buf: Deque[float] = deque()
        self.mz_buf: Deque[float] = deque()

        self.value_vars = {name: tk.StringVar(value="0.0000") for name in ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]}
        self.status_var = tk.StringVar(value="未连接")
        self.info_var = tk.StringVar(value=f"port={port} baudrate={baudrate} slave_id={slave_id}")
        self.error_var = tk.StringVar(value="")
        self.count_var = tk.StringVar(value="0")

        self._last_redraw_time = 0.0
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(top, text="连接并开始", command=self._on_start).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="停止", command=self._on_stop).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="退出", command=self._on_close).pack(side=tk.LEFT, padx=4)

        status = ttk.LabelFrame(self, text="状态")
        status.pack(fill=tk.X, padx=10, pady=6)
        grid = ttk.Frame(status)
        grid.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(grid, text="连接状态:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(grid, textvariable=self.status_var).grid(row=0, column=1, sticky=tk.W, padx=4)
        ttk.Label(grid, text="样本数:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        ttk.Label(grid, textvariable=self.count_var).grid(row=0, column=3, sticky=tk.W, padx=4)
        ttk.Label(grid, text="串口参数:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(grid, textvariable=self.info_var).grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=4)
        ttk.Label(grid, text="错误信息:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(grid, textvariable=self.error_var, foreground="#aa2222").grid(
            row=2, column=1, columnspan=3, sticky=tk.W, padx=4
        )

        values_frame = ttk.LabelFrame(self, text="实时六维数据")
        values_frame.pack(fill=tk.X, padx=10, pady=6)
        for idx, name in enumerate(["Fx", "Fy", "Fz", "Mx", "My", "Mz"]):
            unit = "N" if name.startswith("F") else "Nm"
            box = ttk.Frame(values_frame)
            box.grid(row=0, column=idx, padx=8, pady=8, sticky=tk.NSEW)
            ttk.Label(box, text=name, font=("TkDefaultFont", 10, "bold")).pack()
            ttk.Label(box, textvariable=self.value_vars[name], font=("TkDefaultFont", 14)).pack()
            ttk.Label(box, text=unit).pack()

        plot_frame = ttk.LabelFrame(self, text="滚动曲线")
        plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.ax_force = self.fig.add_subplot(2, 1, 1)
        self.ax_torque = self.fig.add_subplot(2, 1, 2)

        self.line_fx, = self.ax_force.plot([], [], label="Fx")
        self.line_fy, = self.ax_force.plot([], [], label="Fy")
        self.line_fz, = self.ax_force.plot([], [], label="Fz")
        self.ax_force.set_ylabel("Force (N)")
        self.ax_force.grid(True)
        self.ax_force.legend(loc="upper right")

        self.line_mx, = self.ax_torque.plot([], [], label="Mx")
        self.line_my, = self.ax_torque.plot([], [], label="My")
        self.line_mz, = self.ax_torque.plot([], [], label="Mz")
        self.ax_torque.set_ylabel("Torque (Nm)")
        self.ax_torque.set_xlabel("Time (s)")
        self.ax_torque.grid(True)
        self.ax_torque.legend(loc="upper right")

        canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas = canvas

    def _on_start(self) -> None:
        if self.acquiring:
            return
        try:
            self.client.open()
            self.client.start_stream()
        except Exception as exc:  # pylint: disable=broad-except
            self.connected = False
            self.acquiring = False
            self.error_var.set(str(exc))
            self.status_var.set("连接失败")
            messagebox.showerror("FT300", f"启动失败: {exc}")
            self.client.close()
            return

        self.stop_event.clear()
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()
        self.connected = True
        self.acquiring = True
        self.error_var.set("")
        self.status_var.set("采集中")

    def _on_stop(self) -> None:
        self.acquiring = False
        self.stop_event.set()
        try:
            self.client.stop_stream()
        except Exception:
            pass
        self.client.close()
        self.status_var.set("已停止")

    def _reader_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                frame = self.client.read_frame()
                if frame is None:
                    continue
                values = parse_ft300_frame(frame)
                sample = FT300Sample(ts=time.time(), values=values)
                try:
                    self.queue.put_nowait(sample)
                except Exception:
                    pass
            except ValueError as exc:
                if str(exc) == "invalid_crc":
                    self.crc_fail_count += 1
                continue
            except Exception as exc:  # pylint: disable=broad-except
                self.last_error = str(exc)
                self.error_var.set(self.last_error)
                self.status_var.set("读取失败")
                self.acquiring = False
                self.connected = False
                self.stop_event.set()
                break

    def _trim_buffers(self) -> None:
        if not self.time_buf:
            return
        threshold = self.time_buf[-1] - self.window_sec
        while self.time_buf and self.time_buf[0] < threshold:
            self.time_buf.popleft()
            self.fx_buf.popleft()
            self.fy_buf.popleft()
            self.fz_buf.popleft()
            self.mx_buf.popleft()
            self.my_buf.popleft()
            self.mz_buf.popleft()

    def _redraw_plot(self) -> None:
        if not self.time_buf:
            return
        t0 = self.time_buf[0]
        xs = [t - t0 for t in self.time_buf]

        self.line_fx.set_data(xs, list(self.fx_buf))
        self.line_fy.set_data(xs, list(self.fy_buf))
        self.line_fz.set_data(xs, list(self.fz_buf))
        self.line_mx.set_data(xs, list(self.mx_buf))
        self.line_my.set_data(xs, list(self.my_buf))
        self.line_mz.set_data(xs, list(self.mz_buf))

        self.ax_force.relim()
        self.ax_force.autoscale_view()
        self.ax_torque.relim()
        self.ax_torque.autoscale_view()
        self.canvas.draw_idle()

    def _poll_queue(self) -> None:
        updated = False
        while True:
            try:
                sample = self.queue.get_nowait()
            except Empty:
                break
            fx, fy, fz, mx, my, mz = sample.values
            self.time_buf.append(sample.ts)
            self.fx_buf.append(fx)
            self.fy_buf.append(fy)
            self.fz_buf.append(fz)
            self.mx_buf.append(mx)
            self.my_buf.append(my)
            self.mz_buf.append(mz)
            self.value_vars["Fx"].set(f"{fx:.3f}")
            self.value_vars["Fy"].set(f"{fy:.3f}")
            self.value_vars["Fz"].set(f"{fz:.3f}")
            self.value_vars["Mx"].set(f"{mx:.4f}")
            self.value_vars["My"].set(f"{my:.4f}")
            self.value_vars["Mz"].set(f"{mz:.4f}")
            self.sample_count += 1
            self.count_var.set(str(self.sample_count))
            updated = True

        if updated:
            self._trim_buffers()
            now = time.monotonic()
            if now - self._last_redraw_time > 0.2:
                self._redraw_plot()
                self._last_redraw_time = now

        self.after(100, self._poll_queue)

    def _on_close(self) -> None:
        self._on_stop()
        self.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FT300 live GUI over serial")
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=19200)
    parser.add_argument("--timeout", type=float, default=0.1)
    parser.add_argument("--slave-id", type=int, default=9)
    parser.add_argument("--window-sec", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = FT300Gui(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        slave_id=args.slave_id,
        window_sec=args.window_sec,
    )
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

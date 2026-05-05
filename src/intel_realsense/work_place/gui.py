from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import cv2
from PIL import Image, ImageTk

from recorder import RealSenseRecorder
from utils import create_timestamp_dir


class RecorderGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("RealSense Recorder")
        self.root.geometry("980x700")

        self.base_data_dir = Path(__file__).resolve().parent / "data"
        self.base_data_dir.mkdir(parents=True, exist_ok=True)

        self.recorder = RealSenseRecorder(width=640, height=480, fps=30)
        self.current_save_dir: Path | None = None

        self.status_var = tk.StringVar(value="状态: 空闲")
        self.path_var = tk.StringVar(value="保存路径: -")

        self.color_photo = None
        self.depth_photo = None

        self._build_widgets()
        self._schedule_status_poll()
        self._schedule_preview_update()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self) -> None:
        frame = tk.Frame(self.root, padx=14, pady=14)
        frame.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(0, 12))

        self.start_btn = tk.Button(btn_frame, text="Start Recording", width=18, command=self._start_recording)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_btn = tk.Button(btn_frame, text="Stop Recording", width=18, command=self._stop_recording, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        status_label = tk.Label(frame, textvariable=self.status_var, anchor="w", justify="left")
        status_label.pack(fill=tk.X, pady=(0, 8))

        path_label = tk.Label(frame, textvariable=self.path_var, anchor="w", justify="left", wraplength=940)
        path_label.pack(fill=tk.X, pady=(0, 10))

        preview_frame = tk.Frame(frame)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(preview_frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        tk.Label(left, text="RGB 预览").pack(anchor="w")
        self.color_label = tk.Label(left, bg="black", width=460, height=300)
        self.color_label.pack(fill=tk.BOTH, expand=True)

        right = tk.Frame(preview_frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        tk.Label(right, text="彩色深度图预览").pack(anchor="w")
        self.depth_label = tk.Label(right, bg="black", width=460, height=300)
        self.depth_label.pack(fill=tk.BOTH, expand=True)

    def _start_recording(self) -> None:
        if self.recorder.is_recording:
            return

        try:
            self.current_save_dir = create_timestamp_dir(self.base_data_dir)
            self.recorder.start(self.current_save_dir)
        except Exception as exc:
            self.status_var.set("状态: 启动失败")
            self.path_var.set("保存路径: -")
            messagebox.showerror("Start Failed", str(exc))
            return

        self.status_var.set("状态: 录制中")
        self.path_var.set(f"保存路径: {self.current_save_dir}")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def _stop_recording(self) -> None:
        self.recorder.stop()
        self.status_var.set("状态: 空闲")
        if self.current_save_dir is not None:
            self.path_var.set(f"保存路径: {self.current_save_dir}")
        else:
            self.path_var.set("保存路径: -")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def _schedule_status_poll(self) -> None:
        if self.recorder.last_error:
            self.status_var.set(f"状态: 错误 - {self.recorder.last_error}")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.recorder.stop()

        self.root.after(300, self._schedule_status_poll)

    def _schedule_preview_update(self) -> None:
        color_bgr, depth_bgr = self.recorder.get_latest_preview()
        if color_bgr is not None:
            self.color_photo = self._to_photo(color_bgr)
            self.color_label.config(image=self.color_photo)
        if depth_bgr is not None:
            self.depth_photo = self._to_photo(depth_bgr)
            self.depth_label.config(image=self.depth_photo)
        self.root.after(50, self._schedule_preview_update)

    def _to_photo(self, bgr_image):
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (460, 300), interpolation=cv2.INTER_AREA)
        image = Image.fromarray(resized)
        return ImageTk.PhotoImage(image)

    def _on_close(self) -> None:
        try:
            self.recorder.stop()
        finally:
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = RecorderGUI(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()

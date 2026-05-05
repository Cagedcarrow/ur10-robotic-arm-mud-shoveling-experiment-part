import csv
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pyrealsense2 as rs

from utils import create_csv_writer, init_video_writers


class RealSenseRecorder:
    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        depth_min: float = 1.25,
        depth_max: float = 1.35,
        depth_color_scheme: int = 0,
        depth_histogram_eq: bool = True,
    ) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.depth_min = depth_min
        self.depth_max = depth_max
        self.depth_color_scheme = depth_color_scheme
        self.depth_histogram_eq = depth_histogram_eq

        self._lock = threading.Lock()
        self._preview_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._pipeline: Optional[rs.pipeline] = None
        self._colorizer: Optional[rs.colorizer] = None
        self._video_writers: Dict[str, cv2.VideoWriter] = {}
        self._csv_file = None
        self._csv_writer = None

        self._save_dir: Optional[Path] = None
        self._latest_color: Optional[np.ndarray] = None
        self._latest_depth_color: Optional[np.ndarray] = None

        self.frame_id = 0
        self.is_recording = False
        self.last_error = ""
        self.last_fps_est = 0.0

    def start(self, save_dir: Path) -> None:
        with self._lock:
            if self.is_recording:
                raise RuntimeError("Recorder is already running.")

            self.last_error = ""
            self.frame_id = 0
            self.last_fps_est = 0.0
            self._stop_event.clear()
            with self._preview_lock:
                self._latest_color = None
                self._latest_depth_color = None

            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
            config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
            config.enable_stream(rs.stream.infrared, 1, self.width, self.height, rs.format.y8, self.fps)
            config.enable_stream(rs.stream.infrared, 2, self.width, self.height, rs.format.y8, self.fps)

            try:
                profile = pipeline.start(config)
                colorizer = rs.colorizer()
                colorizer.set_option(rs.option.color_scheme, self.depth_color_scheme)
                colorizer.set_option(rs.option.histogram_equalization_enabled, 1 if self.depth_histogram_eq else 0)
                colorizer.set_option(rs.option.min_distance, self.depth_min)
                colorizer.set_option(rs.option.max_distance, self.depth_max)
                self._write_camera_info(profile, save_dir)
                video_writers = init_video_writers(save_dir, self.fps, self.width, self.height)
                csv_file, csv_writer = create_csv_writer(
                    save_dir / "meta.csv",
                    [
                        "timestamp",
                        "frame_id",
                        "fps",
                        "depth_mean",
                        "depth_min",
                        "depth_max",
                        "depth_std",
                    ],
                )
            except Exception:
                try:
                    pipeline.stop()
                except Exception:
                    pass
                raise

            self._pipeline = pipeline
            self._colorizer = colorizer
            self._video_writers = video_writers
            self._csv_file = csv_file
            self._csv_writer = csv_writer
            self._save_dir = save_dir

            self.is_recording = True
            self._thread = threading.Thread(target=self.run, name="realsense-recorder", daemon=True)
            self._thread.start()

    def _write_camera_info(self, profile: rs.pipeline_profile, save_dir: Path) -> None:
        depth_stream = profile.get_stream(rs.stream.depth).as_video_stream_profile()
        intr = depth_stream.get_intrinsics()
        intrinsics = {
            "fx": intr.fx,
            "fy": intr.fy,
            "ppx": intr.ppx,
            "ppy": intr.ppy,
            "width": intr.width,
            "height": intr.height,
            "model": str(intr.model),
            "coeffs": list(intr.coeffs),
        }

        device = profile.get_device()
        depth_sensor = device.first_depth_sensor()
        config = {
            "depth_scale": depth_sensor.get_depth_scale(),
            "color_resolution": [self.width, self.height],
            "depth_resolution": [self.width, self.height],
            "fps": self.fps,
        }

        (save_dir / "camera_intrinsics.json").write_text(
            json.dumps(intrinsics, indent=2), encoding="utf-8"
        )
        (save_dir / "camera_config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

    def stop(self) -> None:
        thread_to_join = None
        save_dir = None
        with self._lock:
            if not self.is_recording and self._thread is None:
                return
            self._stop_event.set()
            thread_to_join = self._thread
            save_dir = self._save_dir

        if thread_to_join is not None and thread_to_join.is_alive():
            thread_to_join.join(timeout=5.0)

        with self._lock:
            self._cleanup_resources()
            self.is_recording = False
            self._thread = None
            self._stop_event.clear()

        if save_dir is not None:
            self._fix_video_fps(save_dir)

    def get_latest_preview(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        with self._preview_lock:
            color = None if self._latest_color is None else self._latest_color.copy()
            depth_color = None if self._latest_depth_color is None else self._latest_depth_color.copy()
        return color, depth_color

    def update_depth_colorizer(
        self,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
        color_scheme: Optional[int] = None,
        histogram_eq: Optional[bool] = None,
    ) -> None:
        colorizer = self._colorizer
        if colorizer is None:
            return

        if min_distance is not None:
            self.depth_min = min_distance
            colorizer.set_option(rs.option.min_distance, min_distance)
        if max_distance is not None:
            self.depth_max = max_distance
            colorizer.set_option(rs.option.max_distance, max_distance)
        if color_scheme is not None:
            self.depth_color_scheme = color_scheme
            colorizer.set_option(rs.option.color_scheme, color_scheme)
        if histogram_eq is not None:
            self.depth_histogram_eq = histogram_eq
            colorizer.set_option(rs.option.histogram_equalization_enabled, 1 if histogram_eq else 0)

    def run(self) -> None:
        prev_rs_ts_ms: Optional[float] = None
        prev_frame_number: Optional[int] = None
        prev_host_t: Optional[float] = None
        smoothed_fps: Optional[float] = None
        alpha = 0.25
        expected_shape = (self.height, self.width)
        rows_since_flush = 0

        while not self._stop_event.is_set():
            pipeline = self._pipeline
            if pipeline is None:
                break

            try:
                frames = pipeline.wait_for_frames(timeout_ms=1000)
            except Exception as exc:
                self.last_error = f"wait_for_frames failed: {exc}"
                break

            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            if depth_frame is None:
                print("[WARN] drop: depth_frame is None", flush=True)
                continue

            rs_ts_ms = float(frames.get_timestamp())
            frame_number = int(depth_frame.get_frame_number())
            # Integrity checks + deduplication
            if rs_ts_ms <= 0.0:
                print("[WARN] drop: invalid timestamp", flush=True)
                continue
            if frame_number <= 0:
                print("[WARN] drop: invalid frame_number", flush=True)
                continue
            if prev_rs_ts_ms is not None and rs_ts_ms <= prev_rs_ts_ms:
                print("[WARN] drop: non-increasing timestamp", flush=True)
                continue
            if prev_frame_number is not None and frame_number <= prev_frame_number:
                print("[WARN] drop: non-increasing frame_number", flush=True)
                continue

            depth_image = np.asanyarray(depth_frame.get_data())

            if depth_image.shape != expected_shape:
                self.last_error = f"Depth shape mismatch: {depth_image.shape} != {expected_shape}"
                break

            colorizer = self._colorizer
            if colorizer is None:
                self.last_error = "Colorizer is not initialized."
                break

            depth_color_frame = colorizer.colorize(depth_frame)
            depth_colormap = np.asanyarray(depth_color_frame.get_data()).copy()

            if color_frame is not None:
                color_image = np.asanyarray(color_frame.get_data()).copy()
                with self._preview_lock:
                    self._latest_color = color_image
                    self._latest_depth_color = depth_colormap
            else:
                print("[WARN] drop: color_frame is None", flush=True)
                continue

            ir1_frame = frames.get_infrared_frame(1)
            ir2_frame = frames.get_infrared_frame(2)
            if ir1_frame is None or ir2_frame is None:
                print("[WARN] drop: infrared frame is None", flush=True)
                continue
            ir1_image = np.asanyarray(ir1_frame.get_data())
            ir2_image = np.asanyarray(ir2_frame.get_data())
            ir1_bgr = cv2.cvtColor(ir1_image, cv2.COLOR_GRAY2BGR)
            ir2_bgr = cv2.cvtColor(ir2_image, cv2.COLOR_GRAY2BGR)

            host_now = time.perf_counter()
            if prev_host_t is None:
                fps_est = float(self.fps)
                smoothed_fps = fps_est
            else:
                dt = host_now - prev_host_t
                fps_inst = 1.0 / dt if dt > 1e-6 else float(self.fps)
                smoothed_fps = alpha * fps_inst + (1.0 - alpha) * (smoothed_fps if smoothed_fps is not None else fps_inst)
                fps_est = smoothed_fps
            self.last_fps_est = fps_est if fps_est > 0.0 else float(self.fps)

            depth_nonzero = depth_image[depth_image > 0]
            if depth_nonzero.size > 0:
                d_mean = float(depth_nonzero.mean())
                d_min = int(depth_nonzero.min())
                d_max = int(depth_nonzero.max())
                d_std = float(depth_nonzero.std())
            else:
                d_mean, d_min, d_max, d_std = 0.0, 0, 0, 0.0

            try:
                self._video_writers["rgb"].write(color_image)
                self._video_writers["depth"].write(depth_colormap)
                self._video_writers["ir1"].write(ir1_bgr)
                self._video_writers["ir2"].write(ir2_bgr)

                self._csv_writer.writerow(
                    {
                        "timestamp": f"{rs_ts_ms:.3f}",
                        "frame_id": frame_number,
                        "fps": f"{fps_est:.2f}",
                        "depth_mean": f"{d_mean:.3f}",
                        "depth_min": d_min,
                        "depth_max": d_max,
                        "depth_std": f"{d_std:.3f}",
                    }
                )
                rows_since_flush += 1
                if rows_since_flush >= 30:
                    self._csv_file.flush()
                    rows_since_flush = 0
            except Exception as exc:
                self.last_error = f"Write failed: {exc}"
                break

            self.frame_id += 1
            print(
                f"[REC] timestamp={rs_ts_ms:.3f} frame_id={frame_number} fps={fps_est:.2f} depth_mean={d_mean:.3f}",
                flush=True,
            )

            prev_rs_ts_ms = rs_ts_ms
            prev_frame_number = frame_number
            prev_host_t = host_now

        self._stop_event.set()

    def _cleanup_resources(self) -> None:
        if self._pipeline is not None:
            try:
                self._pipeline.stop()
            except Exception:
                pass
            self._pipeline = None
        self._colorizer = None

        for writer in self._video_writers.values():
            try:
                writer.release()
            except Exception:
                pass
        self._video_writers.clear()

        if self._csv_file is not None:
            try:
                self._csv_file.flush()
                self._csv_file.close()
            except Exception:
                pass
            self._csv_file = None
            self._csv_writer = None

        with self._preview_lock:
            self._latest_color = None
            self._latest_depth_color = None

    @staticmethod
    def _read_timestamps_from_csv(csv_path: Path) -> List[float]:
        timestamps: List[float] = []
        with open(csv_path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    timestamps.append(float(row["timestamp"]))
                except (KeyError, ValueError):
                    continue
        return timestamps

    def _fix_video_fps(self, save_dir: Path) -> None:
        meta_csv = save_dir / "meta.csv"
        if not meta_csv.exists():
            return

        timestamps = self._read_timestamps_from_csv(meta_csv)
        if len(timestamps) < 2:
            return

        duration_sec = (timestamps[-1] - timestamps[0]) / 1000.0
        if duration_sec <= 0.0:
            return

        actual_fps = (len(timestamps) - 1) / duration_sec
        print(
            f"[INFO] Actual recording FPS: {actual_fps:.2f} (configured: {self.fps})",
            flush=True,
        )

        if abs(actual_fps - self.fps) / max(self.fps, 1) < 0.08:
            print("[INFO] FPS matches configured value — no adjustment needed.", flush=True)
            return

        video_files = ["rgb.mp4", "depth.mp4", "ir1.mp4", "ir2.mp4"]
        for vf in video_files:
            input_path = save_dir / vf
            if not input_path.exists():
                continue
            tmp_path = save_dir / f"_{vf}"

            pts_factor = self.fps / actual_fps
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-filter:v", f"setpts=PTS*{pts_factor:.6f}",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-an",
                str(tmp_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=120)
                tmp_path.rename(input_path)
                print(f"[INFO] Fixed FPS for {vf}: {actual_fps:.2f}", flush=True)
            except subprocess.TimeoutExpired:
                print(f"[WARN] ffmpeg timed out for {vf}", flush=True)
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
            except Exception as exc:
                print(f"[WARN] Failed to fix FPS for {vf}: {exc}", flush=True)
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)

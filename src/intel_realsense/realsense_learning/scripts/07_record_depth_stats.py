#!/usr/bin/env python3
"""Record center ROI depth statistics to CSV for stability analysis."""
import pyrealsense2 as rs
import numpy as np
import cv2
import csv
import os
import time

def main():
    save_dir = os.path.expanduser("~/ur10_ws/src/intel_realsense/realsense_learning/data")
    os.makedirs(save_dir, exist_ok=True)

    csv_path = os.path.join(save_dir, "d435_depth_stats.csv")

    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    pipeline.start(config)

    print(f"[INFO] Saving depth statistics to: {csv_path}")
    print("[INFO] Press q or ESC to quit.")

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "mean_m", "median_m", "min_m", "max_m", "valid_count"])

        try:
            while True:
                frames = pipeline.wait_for_frames()
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()

                if not depth_frame or not color_frame:
                    continue

                depth_raw = np.asanyarray(depth_frame.get_data())
                color = np.asanyarray(color_frame.get_data())

                h, w = depth_raw.shape
                cx, cy = w // 2, h // 2
                roi = depth_raw[cy-30:cy+30, cx-30:cx+30]

                depth_scale = depth_frame.get_units()
                roi_m = roi.astype(np.float32) * depth_scale
                valid = roi_m[roi_m > 0]

                if valid.size > 0:
                    mean_m = float(np.mean(valid))
                    median_m = float(np.median(valid))
                    min_m = float(np.min(valid))
                    max_m = float(np.max(valid))
                    valid_count = int(valid.size)
                else:
                    mean_m = median_m = min_m = max_m = 0.0
                    valid_count = 0

                timestamp = time.time()
                writer.writerow([timestamp, mean_m, median_m, min_m, max_m, valid_count])
                f.flush()

                cv2.rectangle(color, (cx-30, cy-30), (cx+30, cy+30), (0, 255, 0), 2)
                cv2.putText(
                    color,
                    f"ROI median depth={median_m:.3f} m, valid={valid_count}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                cv2.imshow("D435 Depth Stats", color)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    break

        except Exception as e:
            print(f"[ERROR] Runtime error: {e}")
        finally:
            pipeline.stop()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

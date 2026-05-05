#!/usr/bin/env python3
"""Save textured D435 pointcloud to PLY when pressing 's'."""
import pyrealsense2 as rs
import numpy as np
import cv2
import os

def main():
    save_dir = os.path.expanduser("~/ur10_ws/src/intel_realsense/realsense_learning/data")
    os.makedirs(save_dir, exist_ok=True)

    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    pipeline.start(config)

    pointcloud = rs.pointcloud()

    print("[INFO] Press s to save point cloud, q or ESC to quit.")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            color = np.asanyarray(color_frame.get_data())
            cv2.imshow("D435 Color - Press s to save PLY", color)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("s"):
                pointcloud.map_to(color_frame)
                points = pointcloud.calculate(depth_frame)

                ply_path = os.path.join(save_dir, "d435_pointcloud.ply")
                points.export_to_ply(ply_path, color_frame)
                print(f"[INFO] Saved point cloud: {ply_path}")

            elif key == ord("q") or key == 27:
                break

    except Exception as e:
        print(f"[ERROR] Runtime error: {e}")
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

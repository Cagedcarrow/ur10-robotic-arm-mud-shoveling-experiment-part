#!/usr/bin/env python3
"""D435 RGB + Depth side-by-side preview for basic stream learning."""
import pyrealsense2 as rs
import numpy as np
import cv2

def main():
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    print("[INFO] Starting RealSense pipeline: depth 640x480@30, color 640x480@30")
    pipeline.start(config)

    try:
        while True:
            frames = pipeline.wait_for_frames()

            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()

            if not depth_frame or not color_frame:
                print("[WARN] Missing depth or color frame")
                continue

            depth = np.asanyarray(depth_frame.get_data())
            color = np.asanyarray(color_frame.get_data())

            depth_vis = cv2.convertScaleAbs(depth, alpha=0.03)
            depth_colormap = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)

            show = np.hstack((color, depth_colormap))
            cv2.imshow("D435 RGB + Depth", show)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break

    except Exception as e:
        print(f"[ERROR] Runtime error: {e}")
    finally:
        print("[INFO] Stopping pipeline")
        pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

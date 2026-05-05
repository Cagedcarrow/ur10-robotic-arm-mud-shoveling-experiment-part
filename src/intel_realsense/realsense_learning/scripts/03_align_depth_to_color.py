#!/usr/bin/env python3
"""Align depth frame to color frame coordinates using rs.align."""
import pyrealsense2 as rs
import numpy as np
import cv2

def main():
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    align = rs.align(rs.stream.color)

    pipeline.start(config)

    try:
        while True:
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)

            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            depth = np.asanyarray(depth_frame.get_data())
            color = np.asanyarray(color_frame.get_data())

            h, w = color.shape[:2]
            center_x, center_y = w // 2, h // 2
            center_distance = depth_frame.get_distance(center_x, center_y)

            cv2.circle(color, (center_x, center_y), 5, (0, 0, 255), -1)
            cv2.putText(
                color,
                f"aligned center depth={center_distance:.3f} m",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 0),
                2
            )

            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth, alpha=0.03),
                cv2.COLORMAP_JET
            )

            show = np.hstack((color, depth_colormap))
            cv2.imshow("Aligned Depth to Color", show)

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

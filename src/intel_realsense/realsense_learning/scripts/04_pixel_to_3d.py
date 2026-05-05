#!/usr/bin/env python3
"""Deproject hovered pixel into camera-coordinate 3D point."""
import pyrealsense2 as rs
import numpy as np
import cv2

mouse_x, mouse_y = 320, 240
mouse_disp_x, mouse_disp_y = 320, 240

def mouse_callback(event, x, y, flags, param):
    global mouse_disp_x, mouse_disp_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_disp_x, mouse_disp_y = x, y

def main():
    global mouse_x, mouse_y, mouse_disp_x, mouse_disp_y

    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    align = rs.align(rs.stream.color)
    profile = pipeline.start(config)

    color_profile = profile.get_stream(rs.stream.color)
    color_intrinsics = color_profile.as_video_stream_profile().get_intrinsics()

    print("[INFO] Color intrinsics:")
    print(color_intrinsics)

    window_name = "D435 Pixel to 3D"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 640, 480)
    cv2.setMouseCallback(window_name, mouse_callback)

    try:
        while True:
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)

            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            color = np.asanyarray(color_frame.get_data())
            h_img, w_img = color.shape[:2]

            # Map display-space mouse coords back to image-space coords to avoid WSLg scaling offset.
            try:
                _, _, w_win, h_win = cv2.getWindowImageRect(window_name)
            except Exception:
                w_win, h_win = w_img, h_img
            if w_win > 0 and h_win > 0:
                mouse_x = int(mouse_disp_x * w_img / w_win)
                mouse_y = int(mouse_disp_y * h_img / h_win)
            mouse_x = max(0, min(mouse_x, w_img - 1))
            mouse_y = max(0, min(mouse_y, h_img - 1))
            depth = depth_frame.get_distance(mouse_x, mouse_y)

            if depth > 0:
                point_3d = rs.rs2_deproject_pixel_to_point(
                    color_intrinsics,
                    [mouse_x, mouse_y],
                    depth
                )
                text = f"X={point_3d[0]:.3f}, Y={point_3d[1]:.3f}, Z={point_3d[2]:.3f} m"
            else:
                text = "Invalid depth"

            cv2.circle(color, (mouse_x, mouse_y), 5, (0, 0, 255), -1)
            cv2.putText(
                color,
                text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2
            )

            cv2.imshow(window_name, color)

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

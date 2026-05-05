#!/usr/bin/env python3
"""D435 mouse-hover depth distance measurement demo."""
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
    pipeline.start(config)

    window_name = "D435 Mouse Depth Measure"
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

            # Use a small ROI median depth instead of one pixel to reduce noise.
            depth_img = np.asanyarray(depth_frame.get_data())
            h, w = depth_img.shape
            x = max(0, min(mouse_x, w - 1))
            y = max(0, min(mouse_y, h - 1))
            r = 2
            roi = depth_img[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)]
            depth_scale = depth_frame.get_units()
            roi_m = roi.astype(np.float32) * depth_scale
            valid = roi_m[roi_m > 0]
            distance = float(np.median(valid)) if valid.size > 0 else 0.0

            cv2.circle(color, (mouse_x, mouse_y), 5, (0, 0, 255), -1)
            cv2.putText(
                color,
                f"pixel=({mouse_x}, {mouse_y}) depth={distance:.3f} m",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 0),
                2
            )

            cv2.imshow(window_name, color)
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

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

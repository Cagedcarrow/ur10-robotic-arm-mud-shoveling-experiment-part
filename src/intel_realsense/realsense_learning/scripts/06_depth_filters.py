#!/usr/bin/env python3
"""Compare raw depth against filtered depth pipeline output."""
import pyrealsense2 as rs
import numpy as np
import cv2

def main():
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    pipeline.start(config)

    decimation = rs.decimation_filter()
    spatial = rs.spatial_filter()
    temporal = rs.temporal_filter()
    hole_filling = rs.hole_filling_filter()

    print("[INFO] Showing Raw Depth | Filtered Depth")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()

            if not depth_frame:
                continue

            filtered = decimation.process(depth_frame)
            filtered = spatial.process(filtered)
            filtered = temporal.process(filtered)
            filtered = hole_filling.process(filtered)

            raw_depth = np.asanyarray(depth_frame.get_data())
            filtered_depth = np.asanyarray(filtered.get_data())

            raw_vis = cv2.applyColorMap(
                cv2.convertScaleAbs(raw_depth, alpha=0.03),
                cv2.COLORMAP_JET
            )

            filtered_vis = cv2.applyColorMap(
                cv2.convertScaleAbs(filtered_depth, alpha=0.03),
                cv2.COLORMAP_JET
            )
            if filtered_vis.shape[:2] != raw_vis.shape[:2]:
                filtered_vis = cv2.resize(
                    filtered_vis,
                    (raw_vis.shape[1], raw_vis.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                )

            show = np.hstack((raw_vis, filtered_vis))
            cv2.imshow("Raw Depth | Filtered Depth", show)

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

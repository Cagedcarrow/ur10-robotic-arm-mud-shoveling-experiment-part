import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple

import cv2


def create_timestamp_dir(base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_dir = base_dir / timestamp
    idx = 1
    while save_dir.exists():
        save_dir = base_dir / f"{timestamp}_{idx:02d}"
        idx += 1
    save_dir.mkdir(parents=True, exist_ok=False)
    return save_dir


def create_csv_writer(csv_path: Path, fieldnames: Iterable[str]) -> Tuple[object, csv.DictWriter]:
    csv_file = open(csv_path, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    csv_file.flush()
    return csv_file, writer


def init_video_writers(save_dir: Path, fps: int, width: int, height: int) -> Dict[str, cv2.VideoWriter]:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    streams = {
        "rgb": "rgb.mp4",
        "depth": "depth.mp4",
        "ir1": "ir1.mp4",
        "ir2": "ir2.mp4",
    }

    writers: Dict[str, cv2.VideoWriter] = {}
    for key, filename in streams.items():
        out_path = str(save_dir / filename)
        writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height), True)
        if not writer.isOpened():
            for existing in writers.values():
                existing.release()
            raise RuntimeError(f"Failed to open video writer: {out_path}")
        writers[key] = writer

    return writers

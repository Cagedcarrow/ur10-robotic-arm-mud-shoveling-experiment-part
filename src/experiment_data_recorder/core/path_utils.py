from __future__ import annotations

from datetime import datetime
from pathlib import Path


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

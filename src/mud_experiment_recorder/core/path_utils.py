from __future__ import annotations

from datetime import datetime
from pathlib import Path


def create_session_dir(data_root: Path) -> Path:
    """Create data/MM_DD_HHMMSS/ directory, appending _01, _02 on collision."""
    data_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%m_%d_%H%M%S")
    session_dir = data_root / timestamp
    idx = 1
    while session_dir.exists():
        session_dir = data_root / f"{timestamp}_{idx:02d}"
        idx += 1
    session_dir.mkdir(parents=True, exist_ok=False)
    return session_dir

#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parent
    scripts = root / "scripts"
    sys.path.insert(0, str(scripts))
    from fusion_logger_gui import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())

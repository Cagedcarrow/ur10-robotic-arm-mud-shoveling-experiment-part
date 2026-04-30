#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    project_root = Path(__file__).resolve().parent
    scripts_dir = project_root / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from main_gui import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())

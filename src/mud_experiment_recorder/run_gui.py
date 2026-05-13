#!/usr/bin/env python3
"""Mud Experiment Recorder — entry point.

Launches the unified GUI for UR10 + FT300 + RealSense data recording
with dynamics estimation, mud weight measurement, and Excel output.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# --- Enforce PyQt5 plugin path (prevent OpenCV from injecting its own) ---


def _enforce_pyqt_plugin_path() -> None:
    try:
        import PyQt5.QtCore
    except ImportError:
        return
    qt_dir = Path(PyQt5.QtCore.__file__).resolve().parent / "Qt5" / "plugins"
    if not qt_dir.is_dir():
        return
    os.environ["QT_PLUGIN_PATH"] = str(qt_dir)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_dir / "platforms")


def _main() -> int:
    _enforce_pyqt_plugin_path()

    # Headless strategy
    headless = os.environ.get("EXP_REC_HEADLESS", "").strip()
    if headless == "1":
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    elif headless != "0" and not os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    # OpenCV can reset QT_PLUGIN_PATH on import — re-apply
    try:
        import cv2  # noqa: F401
    except ImportError:
        pass
    _enforce_pyqt_plugin_path()

    from PyQt5.QtWidgets import QApplication

    _PKG = Path(__file__).resolve().parent
    if str(_PKG) not in sys.path:
        sys.path.insert(0, str(_PKG))

    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    code = app.exec_()
    return code


if __name__ == "__main__":
    raise SystemExit(_main())

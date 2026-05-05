#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _enforce_pyqt_plugin_path() -> None:
    # OpenCV may inject its own Qt plugin path (cv2/qt/plugins), which often breaks xcb loading.
    # Force Qt to use PyQt5's plugin tree instead.
    try:
        from PyQt5 import QtCore  # noqa: E402

        qt_plugins = Path(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.PluginsPath))
        os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_plugins / "platforms")
    except Exception:
        pass


_enforce_pyqt_plugin_path()

# Headless policy:
# - EXP_REC_HEADLESS=1: force offscreen
# - EXP_REC_HEADLESS=0: force normal GUI
# - unset: auto (offscreen only when DISPLAY is missing)
headless_env = os.environ.get("EXP_REC_HEADLESS")
if headless_env == "1":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
elif headless_env is None and not os.environ.get("DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    # Re-apply once after all imports (including cv2) to override any runtime mutations.
    _enforce_pyqt_plugin_path()
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

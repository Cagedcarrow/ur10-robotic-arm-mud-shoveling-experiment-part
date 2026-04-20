import os
import site
import sys
from pathlib import Path


def _prepend_env_path(variable_name, value):
    if not value:
        return

    current_entries = [entry for entry in os.environ.get(variable_name, "").split(":") if entry]
    if value in current_entries:
        current_entries.remove(value)
    os.environ[variable_name] = ":".join([value, *current_entries])


def _candidate_prefixes():
    roots = [
        Path("/root/ur10_ws/install"),
        Path("/root/moveit_ws/install"),
        Path("/opt/ros/humble"),
    ]

    prefixes = []
    for root in roots:
        if not root.exists():
            continue
        if (root / "share" / "ament_index").exists():
            prefixes.append(root)
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "share" / "ament_index").exists():
                prefixes.append(child)
    return prefixes


def bootstrap_ros_python_environment():
    for prefix in _candidate_prefixes():
        prefix_str = str(prefix)
        _prepend_env_path("AMENT_PREFIX_PATH", prefix_str)
        _prepend_env_path("CMAKE_PREFIX_PATH", prefix_str)
        _prepend_env_path("COLCON_PREFIX_PATH", prefix_str)
        _prepend_env_path("LD_LIBRARY_PATH", str(prefix / "lib"))

        python_paths = [
            prefix / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
            prefix / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "dist-packages",
            prefix / "local" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "dist-packages",
        ]
        for python_path in python_paths:
            if python_path.exists():
                _prepend_env_path("PYTHONPATH", str(python_path))
                site.addsitedir(str(python_path))

from glob import glob

from setuptools import setup

package_name = "ft300_gui_ros2"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.py")),
        (f"share/{package_name}/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools", "pyserial", "matplotlib", "numpy"],
    zip_safe=False,
    maintainer="root",
    maintainer_email="dev@example.com",
    description="Integrated FT300 GUI for USB test, realtime visualization, ROS2 publishing, and session saving.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "ft300_gui_node = ft300_gui_ros2.ft300_gui_node:main",
        ],
    },
)

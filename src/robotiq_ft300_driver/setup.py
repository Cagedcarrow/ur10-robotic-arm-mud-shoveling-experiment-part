from glob import glob

from setuptools import setup

package_name = "robotiq_ft300_driver"

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
    install_requires=[
        "setuptools",
        "pyserial",
    ],
    zip_safe=False,
    maintainer="root",
    maintainer_email="dev@example.com",
    description="ROS 2 Python driver package for Robotiq FT300 force/torque sensor communication and wrench topic publishing.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "ft300_sensor_node = robotiq_ft300_driver.ft300_sensor_node:main",
        ],
    },
)

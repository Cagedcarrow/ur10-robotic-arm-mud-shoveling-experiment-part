from glob import glob
from os.path import isfile

from setuptools import setup

package_name = "ur10_real_comm"


def file_list(pattern: str):
    return [p for p in glob(pattern) if isfile(p)]


setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", file_list("launch/*.py")),
        (f"share/{package_name}/config", file_list("config/*.yaml")),
    ],
    install_requires=[
        "setuptools",
    ],
    zip_safe=False,
    maintainer="root",
    maintainer_email="dev@example.com",
    description="UR10 real robot communication and MoveIt micro-move verification package.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "motion_verify_node = ur10_real_comm.motion_verify_node:main",
        ],
    },
)

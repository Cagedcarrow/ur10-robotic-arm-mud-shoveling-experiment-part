from setuptools import setup

package_name = "ur10_examples_py"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "numpy"],
    zip_safe=False,
    maintainer="root",
    maintainer_email="dev@example.com",
    description="Python MoveItPy examples for the UR10 simulation workspace.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "moveit_py_demo = ur10_examples_py.moveit_py_demo:main",
            "capture_and_import_pcd = ur10_examples_py.capture_and_import_pcd:main",
        ],
    },
)

from setuptools import find_packages
from setuptools import setup

setup(
    name='ur10_moveit_config',
    version='0.1.0',
    packages=find_packages(
        include=('ur10_moveit_config', 'ur10_moveit_config.*')),
)

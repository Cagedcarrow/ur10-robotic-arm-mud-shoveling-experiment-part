from glob import glob
from setuptools import setup

package_name = 'ur10_unified_gui'

setup(
    name=package_name,
    version='0.2.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=False,
    maintainer='root',
    maintainer_email='dev@example.com',
    description='PyQt5 unified GUI for UR10 shovel trajectory system.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'gui_node = ur10_unified_gui.gui_node:main',
        ],
    },
)

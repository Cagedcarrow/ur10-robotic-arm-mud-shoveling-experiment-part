from glob import glob
from setuptools import setup

package_name = 'ur10_bringup'

setup(
    name=package_name,
    version='0.1.0',
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
    description='Unified one-click bringup for UR10 gantry shovel system.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'bucket_scene_node = ur10_bringup.bucket_scene_node:main',
        ],
    },
)

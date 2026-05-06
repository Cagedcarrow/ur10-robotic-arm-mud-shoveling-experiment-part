from setuptools import setup

package_name = 'ur10_real_pose_sync'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/real_pose_rviz_sync.launch.py', 'launch/shovel_plan_execute.launch.py']),
        ('share/' + package_name + '/config', ['config/joint_map.yaml', 'config/assembly_xacro.srdf', 'config/moveit_controllers_virtual.yaml', 'config/shovel_plan_execute.rviz']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='dev',
    maintainer_email='dev@example.com',
    description='Sync real UR10 joint states to assembly model in RViz2.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ur10_joint_state_remap_node = ur10_real_pose_sync.ur10_joint_state_remap_node:main',
            'ur10_joint_state_tcp_node = ur10_real_pose_sync.ur10_joint_state_tcp_node:main',
            'virtual_trajectory_controller = ur10_real_pose_sync.virtual_trajectory_controller:main',
            'micro_plan_diagnostic_node = ur10_real_pose_sync.micro_plan_diagnostic_node:main',
            'real_trajectory_bridge = ur10_real_pose_sync.real_trajectory_bridge:main',
        ],
    },
)

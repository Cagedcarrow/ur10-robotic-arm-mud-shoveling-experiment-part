# ur10_trajectory_planner

ROS2 单功能包模板：用于铲斗末端轨迹生成、拟合、接近规划与执行编排。

## Build

```bash
cd <ws_root>
colcon build --packages-select ur10_trajectory_planner
source install/setup.bash
```

## Run

```bash
ros2 launch ur10_trajectory_planner shovel_bucket_pipeline.launch.py
```

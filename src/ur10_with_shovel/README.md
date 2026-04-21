# ur10_with_shovel

本包将你提供的 `ur10_shovel.urdf` 封装为可在 RViz2 / MoveIt + Gazebo 中控制的 URDF 模型。

说明：使用的是 `python3`，如果你机器上没有 `python` 命令可直接忽略。

## 快速启动

1) 先检查 URDF 渲染是否成功

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
xacro src/ur10_with_shovel/urdf/ur10_shovel.urdf.xacro > /tmp/shovel.urdf
```

2) RViz 交互（关节滑块）

```bash
cd /root/ur10_ws
colcon build --packages-select ur10_with_shovel
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10_with_shovel view_shovel_rviz.launch.py
```

3) Gazebo 控制

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10_with_shovel gazebo_shovel.launch.py
```

4) MoveIt + Gazebo 规划执行

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10_with_shovel moveit_shovel.launch.py
```

## 验证建议

- Gazebo：`ros2 topic hz /joint_states`
- 控制器：`ros2 control list_controllers`
- 控制动作：`ros2 action list`
- RViz/MoveIt 中执行一条小范围规划查看 Gazebo 是否同步。

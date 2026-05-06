# A. 通讯协议

- 网线只是物理连接。
- ROS2 层使用 `ur_robot_driver`。
- `ur_robot_driver` 底层使用 RTDE / URScript / Dashboard。
- 禁止自定义 RTDE 控制程序和 `ur_robot_driver` 同时写机器人。

# B. ROS2 节点/话题/action

- `/joint_states` 由 `ur_robot_driver` 控制链发布真实关节状态，作为 RViz2/MoveIt2 当前姿态输入。
- `robot_state_publisher` 基于装配 URDF 和 `/joint_states` 发布 TF，让 RViz2 显示真实机械臂姿态。
- `move_group` 负责碰撞检测、规划求解与轨迹执行请求管理。
- `scaled_joint_trajectory_controller` 负责在真实机侧执行关节轨迹并受速度缩放约束。
- `/scaled_joint_trajectory_controller/follow_joint_trajectory` 是 MoveIt2 Execute 的目标 action 接口。
- RViz2 通过 `/joint_states` + TF 读取真实姿态，通过 MoveIt2 将规划轨迹发送到上述 action 完成真实执行。

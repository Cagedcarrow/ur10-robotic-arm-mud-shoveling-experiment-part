# Gazebo 显示与启动修复备忘

## 这个专题解决什么问题

这个专题专门记录 `my_robot` 在 Gazebo 中从“启动很慢、机械臂不完整显示、控制器起不来、日志前后矛盾”，到“Gazebo 快速启动、机械臂完整显示、控制器正常加载”的完整排查和修复过程。

这组文档有两个目标：

- 给未来的自己留一份可以复用的排障手册。
- 给刚接触 ROS 2、Xacro、Gazebo、MoveIt 的新手一份能看懂的说明。

如果你之后再遇到类似问题，不需要重新猜。按照这里的顺序检查，大概率能很快缩小范围。

## 你会在这里看到什么

本专题覆盖的重点包括：

- 为什么 Gazebo 会“卡很久”。
- 为什么机械臂 mesh 会显示不出来。
- 为什么中文 link 名会把 Gazebo Classic 卡住。
- 为什么 `controller_manager` 有时看起来“像是有服务”，但控制器还是起不来。
- 为什么明明代码已经改对了，日志却还在报旧错误。
- 为什么旧 `gzserver`、旧 `spawn_entity.py`、旧 `robot_state_publisher` 会让你误判。

## 推荐阅读顺序

建议按下面顺序看：

1. `00_总览.md`
2. `01_问题现象与根因总表.md`
3. `02_Gazebo_为什么显示不出来.md`
4. `03_这次实际改了什么.md`
5. `04_进程干扰_服务干扰_为什么会误判.md`
6. `05_新手排查流程.md`
7. `06_最终验证与常见非致命日志.md`

## 一句话总结

这次问题最终不是“单一原因”导致的，而是多个问题叠在一起：

- 模型里有中文 link 名，触发 Gazebo Classic 的 UTF-8 问题。
- 铲斗 mesh 的 URI 写法不稳定，导致 Gazebo 找不到模型文件。
- world 依赖模型数据库，启动时会额外卡住。
- UR10 和 gantry 各自声明了一套 `ros2_control`，导致插件内部有重复声明问题。
- 更麻烦的是，旧进程和旧服务残留会把排查过程搞乱，让人以为“改完没生效”。

## 最终可用启动命令

```bash
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
ros2 launch my_robot sim_planning_gantry.launch.py gui:=true start_rviz:=true
```

这条命令在本次修复完成后已经验证通过：

- Gazebo 能较快启动。
- 机械臂模型可以完整显示。
- `spawn_entity` 能成功。
- 控制器能加载并激活。
- RViz2 能正常打开。

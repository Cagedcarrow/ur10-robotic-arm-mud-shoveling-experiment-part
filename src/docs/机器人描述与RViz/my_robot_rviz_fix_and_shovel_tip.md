# my_robot 模型清理与 RViz2 显示修复记录

## 一句话总结

本次整理将 `my_robot` 模型统一到正式 ROS 2 包目录中，保留了铲子与机械臂的原始连接方式，保留了 `shovel_tip` 末端坐标系，并提供了稳定的一键启动 RViz2 的方式。

## 问题背景

调试 `my_robot` 时，工作区里同时存在两份模型来源：

- 正式包：`/root/ur10_ws/src/my_robot_xacro/my_robot`
- 旧拷贝：`/root/ur10_ws/src/my_robot_xacro (1)/my_robot`

这会带来两个直接问题：

1. 容易改错文件。
2. RViz2 加载 mesh 和材质时，路径来源容易混淆，导致显示结果不稳定。

同时，模型还需要满足一个额外要求：

- 在不改变铲子与机械臂连接方式的前提下，保留一个位于铲子末端尖点附近的控制坐标系 `shovel_tip`。

## 本次处理后的最终结论

### 唯一维护入口

后续只维护这个文件：

`/root/ur10_ws/src/my_robot_xacro/my_robot/my_robot.urdf.xacro`

旧目录 `my_robot_xacro (1)` 已删除，不再作为模型入口使用。

### 铲子与机械臂连接方式

固定关节 `ur10-robot` 保持不变：

- parent: `ur10_wrist_3`
- child: `铲子`
- origin xyz: `0 0.105 0`
- origin rpy: `1.5707963 0 -1.5707963`

这意味着：

- 铲子的安装位置没有改
- 铲子的朝向没有改
- 只是补充了更清晰的末端参考坐标系

### shovel_tip 坐标系

参考文件：`/root/ur10_ws/src/ur10_shovel.urdf`

最终保留的 `shovel_tip` 定义如下：

- link: `shovel_tip`
- joint: `wrist_3_to_shovel_tip`
- parent: `ur10_wrist_3`
- child: `shovel_tip`
- origin xyz: `-0.00318 0.15268 0.47736`
- origin rpy: `1.2194 -0.0628 -0.0628`

这样做的好处是：

- 不改变铲子安装关系
- 提供稳定的末端姿态参考系
- 方便后续 TCP 调试、姿态控制和轨迹规划

## 路径与资源处理

### 正式包中的 mesh 路径

正式包中的模型仍使用：

```xml
package://my_robot/meshes/...
```

这是正式 ROS 2 包里更稳定的写法，适合通过 `ros2 launch` 和 `FindPackageShare("my_robot")` 的方式加载。

### 安装资源补齐

`CMakeLists.txt` 已更新，安装时会带上：

- `meshes`
- `textures`
- `launch`
- `rviz`

这样 `colcon build` 后，`install/share/my_robot/` 下的资源更完整，RViz2 更容易稳定解析。

## 新的启动入口

新增并验证可用的启动文件：

`/root/ur10_ws/src/my_robot_xacro/my_robot/launch/view_my_robot_rviz.launch.py`

该 launch 会启动：

- `robot_state_publisher`
- `my_robot` 包内的 `shovel_tcp_slider.py`
- `rviz2`

同时自动加载：

- `my_robot.urdf.xacro`
- `view_my_robot.rviz`

## 验证结果

本次整理后已确认：

1. `xacro` 能成功展开模型。
2. 展开后的 URDF 中包含：
   - `ur10-robot`
   - `shovel_tip`
   - `wrist_3_to_shovel_tip`
3. `my_robot` 包已重新构建成功。
4. `ros2 launch my_robot view_my_robot_rviz.launch.py --show-args` 可以正确识别启动文件。

## 使用方式

### 重新编译

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select my_robot
```

### 一键启动查看

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
ros2 launch my_robot view_my_robot_rviz.launch.py
```

## 后续维护建议

### 只改主文件

后续如需继续调整模型，只修改：

`/root/ur10_ws/src/my_robot_xacro/my_robot/my_robot.urdf.xacro`

### 不再使用旧目录

不要再从旧拷贝目录启动、编辑或对比模型，避免再次出现：

- 路径混用
- 版本不一致
- RViz2 结果和源码对应不上

## 本次整理的结果

- 正式包成为唯一主版本
- 旧目录已删除
- 铲子与机械臂连接关系保持不变
- `shovel_tip` 保留并可用于末端控制
- RViz2 查看方式收敛为统一 launch 入口

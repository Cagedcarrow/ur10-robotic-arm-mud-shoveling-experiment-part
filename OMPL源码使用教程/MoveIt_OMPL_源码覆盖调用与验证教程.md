# MoveIt/OMPL 源码覆盖调用与验证教程（ur10_ws）

## 1. 适用场景与结论

### 1.1 适用场景
本教程只针对以下场景：

- 你已经在 `/root/moveit_ws` 完成 MoveIt 源码编译（包含你改过的 OMPL/RRT 逻辑）。
- 你希望在 `/root/ur10_ws` 运行现有 launch 时，实际调用的是 `moveit_ws` 编译出的 MoveIt 库，而不是系统 `/opt/ros/humble` 的默认库。
- 你当前关注点是“怎么调用、怎么确认、怎么验证 RRT 改动是否生效”。

### 1.2 一句话结论
可以调用，且推荐固定采用三段 `source` 顺序：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
```

这会让 `ur10_ws` 的业务包（如 `ur10_moveit_config`、`ur10_simulation_bringup`）仍然可见，同时 MoveIt 核心库优先使用你在 `moveit_ws` 源码编译版本。

---

## 2. Overlay 原理（为什么 source 顺序决定调用版本）

ROS 2 的 overlay 本质是“环境链叠加”：

1. `/opt/ros/humble` 提供基础运行时。
2. `/root/moveit_ws/install` 提供你源码编译后的 MoveIt 包。
3. `/root/ur10_ws/install` 提供项目业务包（UR10 模型、launch、配置、GUI 等）。

当你按上述顺序 source 时：

- `ur10_ws` 会补充自己的包（配置和启动文件）；
- 但 MoveIt 的核心包（`moveit_ros_planning`、`moveit_ros_move_group`、`moveit_planners_ompl` 等）来自 `moveit_ws`。

关键不是“谁最后 source”，而是“同名包来自哪个前缀路径可被优先解析”。实际验证以 `ros2 pkg prefix` 为准。

---

## 3. 一次性正确调用步骤（推荐标准流程）

每开一个新终端，执行一次：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
```

然后立即做 3 个快速确认：

```bash
ros2 pkg prefix moveit_ros_planning
ros2 pkg prefix moveit_ros_move_group
ros2 pkg prefix ur10_moveit_config
```

预期：

- `moveit_ros_planning` -> `/root/moveit_ws/install/moveit_ros_planning`
- `moveit_ros_move_group` -> `/root/moveit_ws/install/moveit_ros_move_group`
- `ur10_moveit_config` -> `/root/ur10_ws/install/ur10_moveit_config`

如果前两条不是 `moveit_ws` 路径，说明你当前终端没有正确命中源码版 MoveIt。

---

## 4. 会话级与长期生效写法

### 4.1 会话级（最稳妥）
每次手动执行三段 `source`。优点是可控、无副作用。

### 4.2 长期生效（建议用函数，不建议写死）
在 `~/.bashrc` 加函数：

```bash
use_ur10_moveit_overlay() {
  source /opt/ros/humble/setup.bash
  source /root/moveit_ws/install/setup.bash
  source /root/ur10_ws/install/setup.bash
}
```

然后新终端执行：

```bash
use_ur10_moveit_overlay
```

不建议直接把三行 source 写死到 `.bashrc` 末尾，避免影响你其他 ROS 工作区。

---

## 5. 如何确认确实在用 moveit_ws

### 5.1 包前缀检查（第一准则）

```bash
ros2 pkg prefix moveit_ros_planning
ros2 pkg prefix moveit_ros_move_group
```

只要路径落在 `/root/moveit_ws/install/...`，即可判定 MoveIt 核心包来自源码工作区。

### 5.2 环境链检查（辅助）

```bash
echo "$AMENT_PREFIX_PATH"
```

你应能看到同时存在：

- `/root/ur10_ws/install/...`
- `/root/moveit_ws/install/...`
- `/opt/ros/humble`

### 5.3 业务包完整性检查

```bash
ros2 pkg prefix ur10_simulation_bringup
ros2 pkg prefix ur10_moveit_config
```

这两者应来自 `/root/ur10_ws/install/...`，否则说明 overlay 混乱。

---

## 6. 无头烟测步骤（本次实测可行）

> 目标：不启动 RViz，快速确认 move_group 能正常加载 OMPL 并进入可规划状态。

### 6.1 命令

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash

timeout 45s ros2 launch ur10_simulation_bringup moveit_planning.launch.py start_rviz:=false >/tmp/ompl_overlay_smoke.log 2>&1

echo "EXIT_CODE=$?"
tail -n 120 /tmp/ompl_overlay_smoke.log
```

### 6.2 判据

满足以下任意组合即可判定“路径可行”:

1. 日志出现：`Using planning interface 'OMPL'`
2. 日志出现：`You can start planning now!`
3. `EXIT_CODE=124`（`timeout` 超时退出）且前两项出现，视为“启动成功后被超时主动终止”，不是失败。

### 6.3 本次实测证据

- `ros2 pkg prefix moveit_ros_planning` -> `/root/moveit_ws/install/moveit_ros_planning`
- `ros2 pkg prefix moveit_ros_move_group` -> `/root/moveit_ws/install/moveit_ros_move_group`
- 无头烟测日志出现：
  - `Using planning interface 'OMPL'`
  - `You can start planning now!`
- `EXIT_CODE=124`（符合 timeout 主动终止预期）

结论：当前这条调用路径可行。

---

## 7. 如何验证你的 RRT 改动生效

仅“能启动”不等于“改动生效”。建议按三层验证。

### 7.1 配置层：明确使用目标 planner

检查并设置 OMPL 配置文件中的 planner（例如）：

- `src/ur10_moveit_config/config/ompl_planning.yaml`
- 或 `src/my_robot_moveit_config/config/ompl_planning.yaml`

确认目标 group 中已启用你要对比的 planner（如 `RRTConnectkConfigDefault` 或自定义名字）。

### 7.2 启动层：确认 move_group 使用 OMPL 管线

日志应包含：

- `Loading planning pipeline 'ompl'`
- `Using planning interface 'OMPL'`

若你的改动包含新增日志标识（推荐在源码里打唯一前缀），应在启动/规划时看到该标识。

### 7.3 行为层：A/B 对照验证

建议固定以下条件做对照实验：

- 同一目标位姿/关节目标
- 同一约束条件
- 同一场景（同 obstacles）
- 尽量固定随机种子（若你的改动支持）

对比指标：

1. 规划成功率
2. 规划耗时
3. 路径长度或关键轨迹特征
4. 平滑后轨迹质量（如速度/加速度变化）

如果 A/B 差异稳定且与你改动方向一致，可视为“RRT 改动生效”。

---

## 8. 常见错误与排查

### 8.1 source 顺序错误
现象：`ros2 pkg prefix moveit_ros_planning` 指向 `/opt/ros/humble`。

处理：重开终端，严格按三段 source 顺序执行。

### 8.2 只 source 了 ur10_ws
现象：你以为在用源码版，实际仍是系统 MoveIt。

处理：补 source `/root/moveit_ws/install/setup.bash`，再检查 prefix。

### 8.3 旧终端环境污染
现象：同一命令在不同终端表现不一致。

处理：开全新终端，不复用历史 shell session。

### 8.4 ABI/库混用问题（较少见）
现象：运行时报符号找不到、段错误或奇怪崩溃。

处理顺序：

```bash
# 在 moveit_ws 重编
cd /root/moveit_ws
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo

# 在 ur10_ws 重编
cd /root/ur10_ws
colcon build --symlink-install
```

然后重开新终端再 source。

### 8.5 进程残留干扰
现象：重复启动后出现“资源已占用/状态异常”。

处理：先结束旧 `move_group`、Gazebo 相关进程，再重启。

---

## 9. 回退方案（切回系统 MoveIt）

如果你要临时回退到系统默认 MoveIt，只 source：

```bash
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
```

然后验证：

```bash
ros2 pkg prefix moveit_ros_planning
```

如果输出变成 `/opt/ros/humble` 下路径，即说明已回退成功。

---

## 10. 最小检查清单（每次开终端 30 秒）

按这个清单执行，基本不会踩坑：

1. 执行三段 source（opt -> moveit_ws -> ur10_ws）。
2. 跑 `ros2 pkg prefix moveit_ros_planning`，确认是 `/root/moveit_ws/install/...`。
3. 跑 `ros2 pkg prefix ur10_moveit_config`，确认是 `/root/ur10_ws/install/...`。
4. 无头烟测一次：
   - `timeout 45s ros2 launch ur10_simulation_bringup moveit_planning.launch.py start_rviz:=false`
5. 日志看到 `Using planning interface 'OMPL'` + `You can start planning now!`。

如果以上都满足，你就可以认为“`ur10_ws` 已成功调用 `moveit_ws` 的源码版 MoveIt/OMPL”。

---

## 附录 A：你最常用的一键命令

```bash
source /opt/ros/humble/setup.bash && \
source /root/moveit_ws/install/setup.bash && \
source /root/ur10_ws/install/setup.bash && \
ros2 pkg prefix moveit_ros_planning && \
timeout 45s ros2 launch ur10_simulation_bringup moveit_planning.launch.py start_rviz:=false
```

## 附录 B：当前项目中的 OMPL 配置入口

- `/root/ur10_ws/src/ur10_moveit_config/config/ompl_planning.yaml`
- `/root/ur10_ws/src/my_robot_moveit_config/config/ompl_planning.yaml`

如果你在其中之一修改 planner，记得重建对应工作区并在新终端重新 source。

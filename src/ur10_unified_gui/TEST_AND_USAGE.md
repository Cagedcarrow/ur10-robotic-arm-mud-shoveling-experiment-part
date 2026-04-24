# UR10 Unified GUI 测试与使用说明

## 1. 文档目的
本说明基于 `ur10_unified_gui` 的离线全自动测试结果生成，覆盖：
- 功能清单
- 使用步骤
- 互斥行为说明
- 停止行为说明
- 测试执行结果与修复记录

测试口径：
- 不连接真实机器人
- 不实际拉起 Gazebo / RViz2 / MoveIt 全链路
- 仅验证 GUI 编排逻辑、参数校验、状态收敛和命令构造

## 2. 功能清单
- 模式管理：`Real` / `Sim` 同页切换
- 快速网络检查：
  - Real：IP/子网校验、子网归属告警、`ping`、端口探测、脚本存在性
  - Sim：工作区目录与参数存在性校验
- 实机验证触发：
  - 优先 `run_full_verify.sh`
  - 主脚本不存在时回退 `run_full_verify_wsl.sh`
- 仿真触发：
  - 调用 `ros2 launch ur10_simulation_bringup complete_simulation.launch.py`
- 运行状态管理：`IDLE / RUNNING / PASS / FAIL / WARN / STOPPED`
- 日志管理：实时日志显示、`[SUMMARY]` 状态解析、导出/清空日志
- 进程管理：进程组启动与停止（`setsid + SIGTERM -> SIGKILL`）
- 参数持久化：保存到 `~/.ur10_unified_gui.json`，支持加载恢复

## 3. 使用步骤
1. 启动 GUI
```bash
cd /root/ur10_ws/src/ur10_unified_gui
python3 main.py
```

2. 选择模式
- Real：配置 `host_ip/robot_ip/robot_subnet/reverse_ip/wrist3_delta/controller/status_timeout`
- Sim：配置 `ur_type/use_fake_hardware/world/start_rviz/enable_gantry_rviz_control`

3. 可选执行“快速网络检查”
- Real 检查失败会阻止启动
- Real 检查为 WARN 时允许继续
- Sim 检查失败会阻止启动

4. 启动流程
- 点击“启动实机验证”或“启动仿真（Gazebo+RViz2+MoveIt）”
- 观察日志区输出与状态栏变化

5. 停止流程
- 点击“停止所有”结束当前任务
- 状态栏应进入 `STOPPED`

6. 参数与日志
- 点击“保存参数”持久化配置
- 点击“加载参数”恢复配置
- 点击“导出日志”输出 `.log` 文件

## 4. 互斥行为说明
互斥策略：同一时刻只允许一个运行态任务。

触发规则：
- 当 Real 运行中，再触发 Sim：拒绝启动
- 当 Sim 运行中，再触发 Real：拒绝启动

用户可见反馈：
- 弹出 warning 提示
- 日志写入：`按互斥策略拒绝启动 ...`

预期效果：
- 避免并发启动导致资源冲突
- 保持当前运行任务不被打断，直到用户主动停止

## 5. 停止行为说明
停止逻辑：
1. 对当前会话进程组发送 `SIGTERM`
2. 超时未退出则发送 `SIGKILL`
3. 回收会话句柄，状态更新为 `STOPPED`

边界行为：
- 运行态点击“停止所有”：应停止会话并清空活动会话
- 空闲态点击“停止所有”：不报错，状态保持可预期（`STOPPED`）

## 6. 自动化测试结果
执行时间：2026-04-25

执行命令：
```bash
python3 -m py_compile main.py config_schema.py tests/test_unified_gui.py
python3 -m pytest -q tests/test_unified_gui.py
```

结果：
- `py_compile`：通过
- `pytest`：`9 passed in 0.28s`

覆盖项：
- Real 网络检查（正常告警路径 + 非法 IP 拒绝）
- Sim 工作区目录校验
- 运行互斥拦截
- 停止行为（运行态/空闲态）
- `[SUMMARY]` 解析与无 summary 退出码兜底
- 配置保存/加载回归
- Real 主脚本缺失回退备用脚本
- `ProcessSession` 的 `Popen` 可 patch 能力

## 7. 本轮修复与改进记录
本轮以测试驱动方式完成以下改进（均在 `ur10_unified_gui` 内）：
- 增强可测性边界（不改变业务语义）：
  - 可 patch 的文件对话框接口
  - 可 patch 的 messagebox 接口
  - 可 patch 的 ping 调用入口
  - `ProcessSession.POPEN` 可 patch 注入
- 新增离线自动化测试套件：`tests/test_unified_gui.py`

本轮自动化测试未发现新的阻断级运行缺陷；当前行为与设计目标一致。

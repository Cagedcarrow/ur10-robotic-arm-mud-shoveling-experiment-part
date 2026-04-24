# UR10 Unified GUI

这是一个独立的一体化可视化 GUI（tkinter），用于同时支持两条运行链路：

- Real：调用现有 `run_full_verify.sh` 完整实机验证流程
- Sim：启动 `ur10_simulation_bringup/complete_simulation.launch.py`

## 快速启动

```bash
cd /root/ur10_ws/src/ur10_unified_gui
python3 main.py
```

## 功能

- 模式切换：`Real | Sim`
- 网络快速检测：IP/subnet 校验、可选 ping、端口连通提示
- 实机验证启动：默认走 `ur10_real_comm/scripts/run_full_verify.sh`
- 仿真启动：默认走 `ros2 launch ur10_simulation_bringup complete_simulation.launch.py`
- 日志显示、实时状态更新、导出日志
- 进程树启动/停止（`preexec_fn=os.setsid` + `killpg`）
- 参数保存/加载：`~/.ur10_unified_gui.json`

## 文件

- `main.py`：GUI 主程序
- `config_schema.py`：配置与默认值
- `requirements.txt`：当前使用标准库，默认可留空

## 默认行为

### Real
- 通过环境变量传递给 `run_full_verify.sh`：
  - `ROBOT_IP`
  - `REVERSE_IP`
  - `WRIST3_DELTA_DEG`
  - `CONFIRM_EXECUTE`
  - `LAUNCH_RVIZ`
  - `INITIAL_JOINT_CONTROLLER`
  - `STATUS_TIMEOUT_SEC`

### Sim
- 默认参数建议：
  - `start_cpp_demo:=false`
  - `start_py_demo:=false`
  - `start_py_tools:=false`
  - `enable_gantry_rviz_control:=false`
  - `start_rviz:=true`

## 注意

- GUI 仅做编排和展示，不改动 `motion_verify_node`、`run_full_verify.sh` 的核心逻辑。
- 实机场景中，真实动作依赖你已有的网络与 reverse_ip 配置（与现有文档一致）。

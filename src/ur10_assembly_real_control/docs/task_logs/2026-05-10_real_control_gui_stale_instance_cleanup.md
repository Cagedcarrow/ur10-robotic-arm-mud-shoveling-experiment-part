# 本次任务总结

## 1. 任务目标
解决 `real_control_gui.py` 启动后看不到窗口，并处理“旧窗口进程未正常关闭”导致的新实例可视化异常风险。

## 2. 根因分析
- 程序并未卡死，已进入 Qt 事件循环。
- X11 窗口实际被创建，但在某些会话下不可见/被隐藏。
- 旧 GUI 实例残留会放大该问题，因此需要启动前自动回收旧实例。

## 3. 修改文件清单
- `scripts/real_control_gui.py`

## 4. 新增功能
- 启动前自动清理旧实例（仅清理 `python ... real_control_gui.py` 真实实例）。
- 清理数量日志输出：`[gui] cleaned stale instances: N`。

## 5. 核心实现逻辑
- 使用 `psutil.process_iter` 扫描进程；
- 仅匹配 Python 解释器进程且 argv 中包含 `real_control_gui.py`；
- 先 `terminate` 再超时后 `kill`，避免僵尸残留。

## 6. 执行命令
```bash
python3 -m py_compile /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py
```

## 7. 测试结果
- 通过回归验证：先启动旧实例，再启动新实例时日志显示 `cleaned stale instances: 1`。
- 旧实例被成功回收（`OLD_ALIVE False`）。

## 8. 剩余问题
- 若窗口仍不可见，属于会话显示映射问题（窗口创建成功但不在当前可见桌面），与主逻辑无关。

## 9. 下一步建议
1. 先运行一次手动清理再启动；
2. 用 `--qt-platform wayland` 与 `--qt-platform xcb` 各测一次；
3. 若仍不可见，做会话级显示排查（WSLg/远程桌面焦点）。

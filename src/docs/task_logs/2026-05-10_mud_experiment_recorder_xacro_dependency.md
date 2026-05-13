# 本次任务总结

## 1. 任务目标

确认 `mud_experiment_recorder/run_gui.py` 记录末端铲泥重量程序实际依赖的 xacro 坐标模型来源，重点排查 FT300 力传感器到世界 Z 轴重力方向投影所使用的坐标定义。

## 2. 根因分析

`mud_experiment_recorder` 当前不是标准 ROS2 package，目录内没有 `package.xml`、`setup.py`、`CMakeLists.txt` 或 launch 文件。`run_gui.py` 是直接启动 PyQt5 GUI 的入口，不在运行时加载 `robot_description` 或 xacro。

程序对 xacro 的依赖是静态数值依赖：`mud_experiment_recorder/kinematics/kinematics.py` 和 `mud_experiment_recorder/core/config.py` 手工写入了来自 `assembly_xacro` 的 UR10 关节、FT300 固定关节和 TCP 固定关节姿态。

实际匹配的 xacro 文件是：

```text
/root/ur10_ws/src/ur_base_xarco_model/assembly_xacro/assembly/assembly.urdf.xacro
```

匹配依据：

- `ur10-sensor_shovel` 固定关节：`origin xyz="0 0.09 0" rpy="-1.5707963 0 0"`
- `sensor_shovel_tcp_fixed` 固定关节：`origin xyz="-0.47377 0.077109 0.0733" rpy="-1.5708 1.5708 -0.61087"`
- UR10 各关节 origin 与 `UR10Kinematics` 中硬编码数值一致。

另一个候选文件：

```text
/root/ur10_ws/src/ur_base_xarco_model/assembly_description/urdf/assembly.urdf.xacro
```

虽然也包含相似结构，但其 `ur10-sensor_shovel` 固定关节姿态是 `rpy="0 1.5707963 1.5707963"`，和当前 Python 代码不一致，因此不是当前重量投影代码的匹配来源。

## 3. 修改文件清单

- 新增：`docs/task_logs/2026-05-10_mud_experiment_recorder_xacro_dependency.md`

## 4. 新增功能

无。本次为只读代码排查与文档记录。

## 5. 核心实现逻辑

当前重量链路为：

1. `run_gui.py` 启动 GUI。
2. `core/session_manager.py` 创建 `URFTAdapter`。
3. `core/ur_ft_adapter.py` 创建 `UR10Kinematics`，读取 `get_tcp_to_sensor_rotation()`。
4. `core/weight_calculator.py` 使用 `Act_RX/Act_RY/Act_RZ` 生成 `R_base_tcp`。
5. 通过 `R_base_sensor = R_base_tcp @ R_tcp_to_sensor` 将 FT300 力向量投影到 base/world 近似坐标系。

## 6. 执行命令

```bash
find mud_experiment_recorder -maxdepth 3 -type f | sort
rg -n "xacro|urdf|robot_description|tf|ft300|force|weight|gravity|world|base|Act_R|projection|投影" mud_experiment_recorder
rg -n "ur10-sensor_shovel|sensor_shovel_tcp|sensor_shovel|0 0.09 0|-1.5708 1.5708 -0.61087|-1.5708 0 0" ur_base_xarco_model -g '*.xacro' -g '*.urdf' -g '*.srdf'
nl -ba mud_experiment_recorder/kinematics/kinematics.py
nl -ba mud_experiment_recorder/core/weight_calculator.py
nl -ba ur_base_xarco_model/assembly_xacro/assembly/assembly.urdf.xacro
nl -ba ur_base_xarco_model/assembly_description/urdf/assembly.urdf.xacro
```

## 7. 测试结果

已完成静态源码反查。未运行 GUI、ROS2 图或硬件连接测试，因为本次目标是确认 xacro 依赖来源。

## 8. 剩余问题

当前 Z 投影仍有两个高风险点：

1. `assembly_xacro` 与 `assembly_description` 中 `ur10-sensor_shovel` 姿态不一致。
2. `WeightCalculator._finish_tare()` 中 `shovel_tare_Fz` 使用的是传感器坐标系均值 `mean_F[2]`，而不是同一时刻的 base/world Z 投影均值；这会影响 `weight_z_g` 参考值。

## 9. 下一步建议

下一步应把 `mud_experiment_recorder` 的 FT300 坐标变换来源显式化：要么直接从指定 xacro/URDF 解析固定关节，要么在配置文件中明确声明当前使用 `assembly_xacro/assembly/assembly.urdf.xacro`，并增加一个离线自检脚本输出 `R_base_sensor`、`force_base_z` 和 `weight_z_g`。

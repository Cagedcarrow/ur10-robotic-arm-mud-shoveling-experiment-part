# 本次任务总结

## 1. 任务目标

修复 `mud_experiment_recorder` 中铲泥重量严重不准的问题，重点检查 FT300 力传感器坐标变换、姿态变化和皮重逻辑对重量结果的影响。

## 2. 根因分析

发现四个核心问题：

1. 单纯依赖 `Act_RX/Act_RY/Act_RZ` 做世界/base Z 投影会强依赖 UR 示教器当前 TCP 设置。如果实际 TCP 和 xacro 中的 `sensor_shovel_tcp` 不完全一致，空铲倾斜到平放的姿态变化会被误算成泥重。
2. 重量计算原来使用已经在传感器坐标系清零后的 Fx/Fy/Fz。机械臂姿态变化后，空铲重力在传感器坐标系中的方向也会变化，先在传感器坐标系减零点再旋转会产生错误投影。
3. 原来的 EMA 滤波系数为 0.08，突加载荷刚出现时只显示真实重量约 8%，会导致记录重量明显偏低。
4. 对“空铲倾斜、铲完平放”的实际流程，最稳主信号应是 FT300 原始力模长差值，而不是姿态投影。力模长对传感器旋转不敏感，适合静止状态下估计新增泥重。

坐标变换本身的 TCP-to-sensor 旋转矩阵是正交矩阵，`det=1.0`，矩阵结构正常。主要风险在 UR 实时 TCP 姿态和 xacro TCP 是否完全一致。

## 3. 修改文件清单

- `mud_experiment_recorder/core/weight_calculator.py`
- `mud_experiment_recorder/core/ur_ft_adapter.py`
- `mud_experiment_recorder/core/session_manager.py`
- `mud_experiment_recorder/gui/main_window.py`
- `docs/task_logs/2026-05-10_mud_weight_coordinate_fix.md`

## 4. 新增功能

- 主重量 `weight_g` 改为 FT300 原始力模长皮重差。
- CSV 新增 `delta_force_base_z` 和 `weight_magnitude_g` 字段。
- GUI 改为显示“原始力模长”主重量，Z 投影仅作为诊断。
- 元数据记录 `shovel_tare_Fz_base` 和 `shovel_tare_magnitude`。

## 5. 核心实现逻辑

新的主重量链路：

1. 读取 FT300 原始力 `Fx/Fy/Fz`。
2. 空铲皮重采集保存 `|F_raw|` 的 80 样本均值。
3. 泥重计算为 `abs(|F_raw_current| - |F_raw_empty|) / 9.80665 * 1000`。
4. 同时保留 `force_base_z`、`delta_force_base_z` 和 `weight_z_g` 作为坐标诊断值。

FT300 传感器坐标系清零仍保留给实时 Fx/Fy/Fz 曲线和 CSV 修正值，但不再参与主重量计算。

## 6. 执行命令

```bash
python3 -m compileall -q mud_experiment_recorder

python3 - <<'PY'
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path('mud_experiment_recorder').resolve()))
from core.weight_calculator import GRAVITY, WeightCalculator, rotvec_to_matrix
from kinematics.kinematics import UR10Kinematics

kin = UR10Kinematics()
calc = WeightCalculator(kin.get_tcp_to_sensor_rotation())
rv_empty = np.array([-0.8, -0.2, 1.5])
rv_loaded = np.array([-1.3, -0.9, 1.4])
R_empty = rotvec_to_matrix(rv_empty) @ kin.get_tcp_to_sensor_rotation()
R_loaded = rotvec_to_matrix(rv_loaded) @ kin.get_tcp_to_sensor_rotation()
empty_weight_n = 20.0
mud_weight_n = 0.200 * GRAVITY
empty_sensor = R_empty.T @ np.array([0.0, 0.0, -empty_weight_n])
loaded_sensor = R_loaded.T @ np.array([0.0, 0.0, -(empty_weight_n + mud_weight_n)])
calc.start_tare_shovel()
for _ in range(80):
    calc.update(empty_sensor.tolist(), rv_empty.tolist())
calc.update(loaded_sensor.tolist(), rv_loaded.tolist())
assert abs(calc.current_weight_g - 200.0) < 1e-6
PY

EXP_REC_HEADLESS=1 timeout 5s python3 mud_experiment_recorder/run_gui.py
```

## 7. 测试结果

- Python 编译检查通过。
- 构造“空铲倾斜、铲完平放、只增加 200g 泥”的姿态变化测试通过：输出 `200.000 g`。
- TCP-to-sensor 旋转矩阵检查通过：`det=1.0`，正交误差约 `5.3e-33`。
- GUI 无头启动烟测通过，程序正常进入事件循环并由 `timeout` 结束。

## 8. 剩余问题

- 本次没有连接真实 UR10 和 FT300 做实机采样验证。
- 历史 CSV 不会被自动重算，新逻辑只影响后续新采集数据。
- 如果实验过程中铲子仍接触泥浆侧壁或有明显拖拽力，原始力模长也会混入非重力接触力，应在铲子离开泥浆并静止后点击记录重量。

## 9. 下一步建议

下一次实机采集时按顺序执行：

1. 开始接收数据。
2. 空铲静止时点击“清零去皮重”。
3. 等待皮重采集到 100%。
4. 开始记录数据。
5. 铲泥后保持末端静止，再点击“记录重量”。

建议后续增加一个实时诊断面板，同时显示 `force_base_x/y/z`、`delta_force_base_z` 和稳定性标准差，便于判断是否处于可记录状态。

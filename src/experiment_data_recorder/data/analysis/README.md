# 力数据分析模块

该目录用于分析 `data/<session>/ur10_ft300_realtime_data.csv`，面向铲泥实验自动识别机械臂稳定称重点，并基于模型坐标链将 FT300 三轴力投影到机器人基坐标系重力方向，估计泥重量。

## 核心思路

- 过滤 `Fx/Fy/Fz` 为 `nan` 的无效样本
- 用 `Tgt_q0..Tgt_q5` 相邻变化量识别稳定时间段
- 将最后一个长稳态段视为最终称重点
- 将最终称重点前一个长稳态段视为 `0 g` 参考段
- 读取 `assembly.urdf.xacro` 中 `sensor_shovel -> sensor_shovel_shovel_tcp` 的固定旋转
- 结合 `Act_RX/RY/RZ` 姿态，把 FT300 力从传感器坐标系投影到机器人基坐标系
- 默认使用基坐标系 `Z` 方向力差估计泥重量，单位为克

## 运行方式

在仓库根目录执行：

```bash
python3 data/analysis/analyze_force_weight.py
```

批量分析 `data` 目录下所有会话：

```bash
python3 data/analysis/analyze_all_force_weight.py
```

批量分析全部会话的关节平滑性与速度-末端载荷相关性：

```bash
python3 data/analysis/analyze_motion_smoothness.py
```

指定其它会话目录：

```bash
python3 data/analysis/analyze_force_weight.py \
  --session-dir data/2026-05-01_20-03-37
```

常用参数：

```bash
python3 data/analysis/analyze_force_weight.py \
  --session-dir data/2026-05-01_19-57-41 \
  --joint-threshold 5e-4 \
  --min-stable-samples 50 \
  --rolling-window 35 \
  --weight-axis-mode base_z \
  --reference-mode pre_final_stable \
  --model-file /root/ur10_ws/src/ur_base_xarco_model/assembly_xacro/assembly/assembly.urdf.xacro
```

## 输出目录

默认输出到：

```bash
data/analysis/output/<session_name>/
```

生成文件包括：

- `force_timeseries.csv`
- `stable_segments.csv`
- `force_analysis.png`
- `all_sessions_weight_summary.md`（批量分析时生成）

新增的运动平滑性分析会输出到：

```bash
data/analysis/<session_name>/
```

生成文件包括：

- `main_figure.png / .svg`
- `supplementary_figure.png / .svg`
- `analysis_summary.md`
- `all_sessions_motion_smoothness_summary.md`（批量分析时生成）

新版运动分析默认特性：

- 横轴使用样本序号，不显示绝对时间
- 图面使用中文字体优先链：`AR PL SungtiL GB + DejaVu Sans + Arial`
- 支持关节、TCP、末端六维载荷的多数据耦合分析
- 支持自动识别“接触 / 装载 / 回撤 / 称重”四类阶段，允许不清晰阶段缺失并在报告中说明

## 结果解释

- `force_timeseries.csv`
  - 每个有效力样本一行
  - 包含原始 `Fx/Fy/Fz`
  - 包含投影后的 `force_base_x / force_base_y / force_base_z`
  - 包含 `is_candidate_reference / is_reference_segment / is_final_measurement_window`

- `stable_segments.csv`
  - 每个稳定段一行
  - `avg_force_magnitude` 是总力模长平均值
  - `avg_force_base_z` 是基坐标系重力方向平均力
  - `delta_force_base_z_to_reference` 是相对 `0 g` 参考段的力差
  - `estimated_mass_g_from_base_z` 是默认重量结果

- `force_analysis.png`
  - 子图 1：原始 `Fx/Fy/Fz`
  - 子图 2：`force_base_z` 与参考段/最终段高亮
  - 子图 3：各稳定段的 `avg_force_base_z` 与重量对比

## 原理说明

详细原理见：

```bash
data/analysis/force_projection_principle.md
```

## 默认假设

- FT300 力数据属于 `sensor_shovel` 坐标系
- `Act_RX/RY/RZ` 对应 shovel TCP 姿态
- 默认 TCP 帧是 `sensor_shovel_shovel_tcp`
- 默认传感器帧是 `sensor_shovel`
- 默认 `0 g` 参考段采用最终称重点前一个稳定段

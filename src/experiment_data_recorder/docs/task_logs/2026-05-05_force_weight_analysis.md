# 本次任务总结

## 1. 任务目标

在 `data` 目录下新增独立分析模块，自动识别 UR10 目标关节基本不动的时间段，基于 FT300 的 `Fx/Fy/Fz` 计算总力，并以首个静止段为基准估计铲子上泥的等效重量，输出单位为克。

## 2. 根因分析

第一版离线分析工具已经能做稳态检测和总力绘图，但重量结果错误。复盘后确认根因有两点：

- 把最早静止段直接当成 `0 g` 基准，实际那一段仍混入了泥浆阻力
- 直接用总力模长 `sqrt(Fx^2 + Fy^2 + Fz^2)` 估重，没有补偿铲子姿态变化

因此会出现“最终称重段力更小，反而算出负重量”的假象。

## 3. 修改文件清单

- `data/analysis/analyze_force_weight.py`
- `data/analysis/README.md`
- `data/analysis/force_projection_principle.md`
- `docs/task_logs/2026-05-05_force_weight_analysis.md`

## 4. 新增功能

- 按会话目录读取 `ur10_ft300_realtime_data.csv`
- 结合 `assembly.urdf.xacro` 解析 shovel TCP 与传感器坐标关系
- 将 FT300 力从 `sensor_shovel` 投影到机器人基坐标系
- 默认基于 `force_base_z` 估计泥重量
- 默认把最终称重点前一稳态段作为 `0 g` 参考
- 导出含投影力分量的新时间序列 CSV、稳态段汇总 CSV 和分析图
- 新增投影原理说明 Markdown

## 5. 核心实现逻辑

- 先过滤 `Fx/Fy/Fz` 非有限值样本，只分析有效 FT300 数据
- 对每个有效样本同时计算：
  - 总力模长 `|F|`
  - 基坐标系投影力 `force_base_x / force_base_y / force_base_z`
- 使用 `Tgt_q0..Tgt_q5` 相邻变化量识别长稳态段
- 将最后一个长稳态段视为最终称重点
- 将最终称重点前一个长稳态段视为 `0 g` 参考段
- 用 `force_base_z` 的段均值差换算等效重量，单位克

## 6. 执行命令

```bash
python3 data/analysis/analyze_force_weight.py
python3 data/analysis/analyze_force_weight.py --weight-axis-mode base_z
python3 -m py_compile data/analysis/analyze_force_weight.py
```

## 7. 测试结果

- 成功生成 `data/analysis/output/2026-05-01_19-57-41/`
- 成功输出：
  - `force_timeseries.csv`
  - `stable_segments.csv`
  - `force_analysis.png`
- 成功新增：
  - `data/analysis/force_projection_principle.md`
- 默认参数下能识别出多个稳态段
- 主结果不再出现明显错误的负 `900 g` 量级
- 主结果回到接近现场记录 `230 g` 的量级

## 8. 剩余问题

- 当前默认假设 `Act_RX/RY/RZ` 对应 `sensor_shovel_shovel_tcp`
- 如果真机控制器使用了其它 TCP，需要同步切换分析参数
- 当前 `0 g` 参考段仍按“最终前一稳态”自动选择，后续可进一步增加多候选评分
- 当前未与视频帧或 `camera_meta.csv` 做跨模态对齐

## 9. 下一步建议

- 增加对多个会话目录的批处理入口
- 增加多参考段评分逻辑，而不是固定使用最终前一个稳态段
- 接入视频关键帧，自动标记“出泥完成”和“最终称重”时刻
- 如果后续要上真机闭环，建议加入 FT300 零点标定流程

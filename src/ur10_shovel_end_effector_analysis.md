# ur10_shovel.urdf.xacro 末端安装错误分析

## 结论
`ur10_with_shovel/urdf/ur10_shovel.urdf.xacro` 的“末端安装错误”不是主铲子网格本体（`铲子`）的固定连接参数错了，而是**同时存在第二套末端定义（`shovel_tip`）且位姿与铲体不一致**，导致你在 TF/末端参考系里看到“工具末端错位”。

## 对比对象
- 正常参考：`my_robot_xacro (1)/my_robot/my_robot.urdf.xacro`
- 待分析：`ur10_with_shovel/urdf/ur10_shovel.urdf.xacro`

## 关键证据
1. 两份文件的主安装关节一致
- 都有：`ur10_wrist_3 -> 铲子` 的 fixed joint
- 都是：`origin xyz="0 0.105 0" rpy="1.5707963 0 -1.5707963"`

这说明“铲子实体本体”挂接参数本身并无本质差异。

2. `ur10_shovel.urdf.xacro` 额外添加了 `shovel_tip`
- 新增 link：`<link name="shovel_tip">`
- 新增 joint：`<joint name="wrist_3_to_shovel_tip" type="fixed">`
- 位姿：`origin xyz="-0.00318 0.15268 0.47736" rpy="1.2194 -0.0628 -0.0628"`

这个 `shovel_tip` 直接从 `ur10_wrist_3` 出发，并没有以 `铲子` 为父链路继承其姿态；其姿态也明显与铲体连接位姿不共线、不共面。

3. 造成的现象
- RViz 中铲子实体看起来可以是“装对的”；
- 但如果你把末端 TCP/工具坐标参考到 `shovel_tip`，它会偏离铲体实际工作刃口，表现为“末端安装错误”或“末端有较大距离”。

## 为什么你现在的 my_robot 看起来正确
`my_robot_xacro (1)/my_robot/my_robot.urdf.xacro` 只保留了 `ur10_wrist_3 -> 铲子` 主连接，没有额外的冲突末端参考链路（`shovel_tip`），所以视觉和末端参考更一致。

## 根因归纳
- 根因不是单一 mesh 导入视角；
- 根因是模型中存在两套末端语义：
  - 一套是铲体本体（`铲子`）
  - 一套是额外 tip（`shovel_tip`）
- 且 `shovel_tip` 的固定变换未与铲体真实几何对齐，导致规划/显示所用末端参考与实体不一致。

## 建议修复策略
1. 如果不需要单独 TCP：删除 `shovel_tip` 与 `wrist_3_to_shovel_tip`。
2. 如果需要 TCP：
- 把 `shovel_tip` 挂在 `铲子` 下（父改为 `铲子`），避免与主安装链路并联冲突；
- 或保留父为 `ur10_wrist_3`，但重新标定其 `origin`，使其准确落在铲刃工作点。
3. 保证 MoveIt SRDF、控制器和任务代码统一使用同一个末端 frame（例如统一为 `shovel_tip` 或 `铲子`）。


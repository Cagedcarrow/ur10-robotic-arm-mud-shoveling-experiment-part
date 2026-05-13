# 泥浆实验记录器 — 坐标系变换与铲泥重量计算方法

## 1. 坐标系定义

系统涉及以下坐标系，均遵循右手定则：

| 符号 | 名称 | 描述 |
|------|------|------|
| $\{B\}$ | UR10 基座坐标系 (Base) | 机器人基座原点，$Z_B$ 垂直向上，与重力方向相反 |
| $\{W_i\}$ | 腕部关节坐标系 (Wrist $i$) | UR10 第 $i$ 关节 (DH 参数驱动)，$i=0,\dots,5$ |
| $\{S\}$ | 传感器坐标系 (Sensor) | FT300 力传感器本体坐标系，固连于 `sensor_shovel` 关节 |
| $\{T\}$ | TCP 坐标系 (Tool Center Point) | UR 工具点，固连于 `sensor_shovel_tcp` 关节，UR 控制器输出 $\mathbf{R}_B^T$ |

---

## 2. 运动学链 (Kinematic Chain)

### 2.1 UR10 关节参数 (源自 URDF)

UR10 六关节 DH 链参数如下表。每个关节 $i$ 的齐次变换为：

$$\mathbf{T}_i(q_i) = \mathbf{T}_{\text{xyz}}(\mathbf{p}_i) \cdot \mathbf{T}_{\text{rpy}}(\mathbf{r}_i) \cdot \mathbf{T}_{\text{rot}}(\mathbf{a}_i, q_i)$$

| 关节 $i$ | $\mathbf{p}_i$ (xyz, m) | $\mathbf{r}_i$ (rpy, rad) | 旋转轴 $\mathbf{a}_i$ |
|----------|------------------------|---------------------------|----------------------|
| 0 | $(0,\, 0,\, 0.1273)$ | $(0,\, 0,\, 0)$ | $\mathbf{\hat{z}}$ (rot_z) |
| 1 | $(0,\, 0.220941,\, 0)$ | $(0,\, \pi/2,\, 0)$ | $\mathbf{\hat{y}}$ (rot_y) |
| 2 | $(-3.9\times10^{-6},\, -0.1719,\, 0.612)$ | $(0,\, 0,\, 0)$ | $\mathbf{\hat{y}}$ (rot_y) |
| 3 | $(0,\, 0,\, 0.5723)$ | $(0,\, \pi/2,\, 0)$ | $\mathbf{\hat{y}}$ (rot_y) |
| 4 | $(0,\, 0.1149,\, 0)$ | $(0,\, 0,\, 0)$ | $\mathbf{\hat{z}}$ (rot_z) |
| 5 | $(0,\, 0,\, 0.1157)$ | $(0,\, 0,\, 0)$ | $\mathbf{\hat{y}}$ (rot_y) |

正运动学递推：

$$\mathbf{T}_B^{W_5}(q) = \prod_{i=0}^{5} \mathbf{T}_i(q_i)$$

### 2.2 腕部至传感器固连变换 (`wrist_3` → `sensor_shovel`)

FT300 传感器通过固定关节 `ur10-sensor_shovel` 安装于腕部 $W_5$ 之后。其 URDF 定义为：

$$\mathbf{p}_{W_5 \to S} = (0,\; 0.09,\; 0)\,\text{m}, \quad \mathbf{r}_{W_5 \to S} = (-\tfrac{\pi}{2},\; 0,\; 0)\,\text{rad}$$

对应的旋转矩阵（RPY = ZYX 欧拉角序）：

$$\mathbf{R}_{W_5}^S = \mathbf{R}_z(0) \cdot \mathbf{R}_y(0) \cdot \mathbf{R}_x(-\tfrac{\pi}{2}) = \mathbf{R}_x(-\tfrac{\pi}{2})$$

$$\boxed{\mathbf{R}_{W_5}^S = \begin{bmatrix}
1 & 0 & 0 \\
0 & 0 & 1 \\
0 & -1 & 0
\end{bmatrix}}$$

该矩阵表示：传感器坐标系的 $X_S$ 轴与腕部 $X_{W_5}$ 对齐；$Y_S$ 轴与腕部 $Z_{W_5}$（向上）对齐；$Z_S$ 轴与腕部 $-Y_{W_5}$ 对齐。

### 2.3 传感器至 TCP 的变换 (`sensor_shovel` → `sensor_shovel_tcp`)

UR 机器人工具点定义在 `sensor_shovel_tcp` 坐标系。从传感器框到 TCP 框的 URDF 旋转为：

$$\mathbf{r}_{S \to T} = \left(-\tfrac{\pi}{2},\; \tfrac{\pi}{2},\; -0.61087\right)\,\text{rad}$$

$$\mathbf{R}_S^T = \mathbf{R}_z(-0.61087) \cdot \mathbf{R}_y(\tfrac{\pi}{2}) \cdot \mathbf{R}_x(-\tfrac{\pi}{2})$$

数值结果：

$$\boxed{\mathbf{R}_S^T = \begin{bmatrix}
0 & -0.819149 & 0.573580 \\
0 & 0.573580 & 0.819149 \\
-1 & 0 & 0
\end{bmatrix}}$$

由此得到 TCP → 传感器的旋转矩阵（即转置）：

$$\boxed{\mathbf{R}_T^S = \left(\mathbf{R}_S^T\right)^\top = \begin{bmatrix}
0 & 0 & -1 \\
-0.819149 & 0.573580 & 0 \\
0.573580 & 0.819149 & 0
\end{bmatrix}}$$

该矩阵 $\mathbf{R}_T^S$ 是系统的**关键常量**，在初始化时通过 `kinematics.get_tcp_to_sensor_rotation()` 获取并传给 `WeightCalculator`。

### 2.4 基座到传感器的完整变换

对于任意关节角 $\mathbf{q}$，基座到 TCP 的旋转矩阵 $\mathbf{R}_B^T(\mathbf{q})$ 由 UR 控制器以轴角形式 `(Act_RX, Act_RY, Act_RZ)` 实时输出。基座到传感器的旋转为：

$$\mathbf{R}_B^S(\mathbf{q}) = \mathbf{R}_B^T(\mathbf{q}) \cdot \mathbf{R}_T^S$$

---

## 3. 力投影变换

### 3.1 轴角 → 旋转矩阵 (Rodrigues 公式)

UR 控制器输出的 TCP 姿态为轴角向量 $\boldsymbol{\omega} = (\omega_x, \omega_y, \omega_z)$。转角 $\theta = \|\boldsymbol{\omega}\|$，单位转轴 $\mathbf{u} = \boldsymbol{\omega} / \theta$（若 $\theta \to 0$ 则 $\mathbf{R} = \mathbf{I}$）。

Rodrigues 旋转公式：

$$\mathbf{R}_B^T = \mathbf{I} + \sin\theta \cdot \mathbf{K}(\mathbf{u}) + (1 - \cos\theta) \cdot \mathbf{K}(\mathbf{u})^2$$

其中 $\mathbf{K}(\mathbf{u})$ 为反对称矩阵：

$$\mathbf{K}(\mathbf{u}) = \begin{bmatrix}
0 & -u_z & u_y \\
u_z & 0 & -u_x \\
-u_y & u_x & 0
\end{bmatrix}$$

### 3.2 FT300 力向量投影到世界坐标系

FT300 实时输出传感器坐标系 $\{S\}$ 下的三维力向量（去皮重零点偏置后）：

$$\mathbf{F}_S = \begin{bmatrix} F_x^{(S)} \\ F_y^{(S)} \\ F_z^{(S)} \end{bmatrix} \in \mathbb{R}^3$$

**投影公式（核心）**：

$$\boxed{\mathbf{F}_B = \mathbf{R}_B^S \cdot \mathbf{F}_S = \mathbf{R}_B^T \cdot \mathbf{R}_T^S \cdot \mathbf{F}_S}$$

展开为三个分量：

$$\begin{bmatrix} F_x^{(B)} \\ F_y^{(B)} \\ F_z^{(B)} \end{bmatrix} =
\begin{bmatrix} R_{11} & R_{12} & R_{13} \\ R_{21} & R_{22} & R_{23} \\ R_{31} & R_{32} & R_{33} \end{bmatrix}_{(B,S)}
\cdot \begin{bmatrix} F_x^{(S)} \\ F_y^{(S)} \\ F_z^{(S)} \end{bmatrix}$$

仅取世界 $Z$ 分量用于重量计算：

$$F_z^{(B)} = R_{31}^{(B,S)} \cdot F_x^{(S)} + R_{32}^{(B,S)} \cdot F_y^{(S)} + R_{33}^{(B,S)} \cdot F_z^{(S)}$$

### 3.3 数值验证

以空铲 (800 g, $\approx$ 7.845 N) 两种典型姿态验证：

**姿态 1 — TCP 水平** ($\mathbf{R}_B^T = \mathbf{I}$)：

$$\mathbf{R}_B^S = \mathbf{I} \cdot \mathbf{R}_T^S = \mathbf{R}_W^S = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 0 & 1 \\ 0 & -1 & 0 \end{bmatrix}$$

重力在基座系为 $\mathbf{F}_B^{\text{grav}} = (0, 0, -7.845)$ N。传感器系中的反作用力：

$$\mathbf{F}_S = (\mathbf{R}_B^S)^\top \cdot \mathbf{F}_B^{\text{grav}} = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 0 & -1 \\ 0 & 1 & 0 \end{bmatrix} \begin{bmatrix} 0 \\ 0 \\ -7.845 \end{bmatrix} = \begin{bmatrix} 0 \\ 7.845 \\ 0 \end{bmatrix} \,\text{N}$$

投影回基座系：

$$\mathbf{F}_B = \mathbf{R}_B^S \cdot \mathbf{F}_S = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 0 & 1 \\ 0 & -1 & 0 \end{bmatrix} \begin{bmatrix} 0 \\ 7.845 \\ 0 \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \\ -7.845 \end{bmatrix} \,\text{N}$$

$$F_z^{(B)} = -7.845 \,\text{N} \quad\checkmark$$

**姿态 2 — TCP 绕 X 轴倾斜 45°** ($\mathbf{R}_B^T = \mathbf{R}_x(\pi/4)$)：

$$\mathbf{R}_B^S = \mathbf{R}_x(\tfrac{\pi}{4}) \cdot \mathbf{R}_W^S =
\begin{bmatrix} 1 & 0 & 0 \\ 0 & 0.7071 & 0.7071 \\ 0 & -0.7071 & 0.7071 \end{bmatrix}$$

$$\mathbf{F}_S = (\mathbf{R}_B^S)^\top \cdot \begin{bmatrix} 0 \\ 0 \\ -7.845 \end{bmatrix} =
\begin{bmatrix} 0 \\ 5.5473 \\ -5.5473 \end{bmatrix} \,\text{N}$$

$$\mathbf{F}_B = \mathbf{R}_B^S \cdot \mathbf{F}_S =
\begin{bmatrix} 1 & 0 & 0 \\ 0 & 0.7071 & 0.7071 \\ 0 & -0.7071 & 0.7071 \end{bmatrix}
\begin{bmatrix} 0 \\ 5.5473 \\ -5.5473 \end{bmatrix} =
\begin{bmatrix} 0 \\ 0 \\ -7.845 \end{bmatrix} \,\text{N}$$

$$F_z^{(B)} = -7.845 \,\text{N} \quad\checkmark$$

**结论：旋转变换 $\mathbf{R}_B^S$ 在任意 TCP 姿态下正确地将传感器测得的重力反作用力投影到世界 $Z$ 轴，投影后 $F_z^{(B)}$ 恒等于铲+泥的总重量产生的力。**

---

## 4. 泥重计算

### 4.1 皮重消除

设空铲在传感器系下对应的世界 $Z$ 力皮重为 $F_{\text{tare}}$。启动皮重采集后，系统连续采集 $N_{\text{tare}} = 80$ 个样本的 $F_z^{(B)}$ 值，取算术平均：

$$F_{\text{tare}} = \frac{1}{N_{\text{tare}}} \sum_{k=1}^{N_{\text{tare}}} F_{z,k}^{(B)}$$

皮重采集过程中不启用 CSV 记录，确保皮重样本不受铲泥动作干扰。

### 4.2 瞬时泥重

每一帧 FT300 数据到达后，计算世界 $Z$ 轴力差值并转换为质量：

$$\Delta F_z = \left|F_z^{(B)} - F_{\text{tare}}\right|$$

$$m_{\text{raw}} = \frac{\Delta F_z}{g} \times 1000 \quad (\text{单位: g})$$

其中 $g = 9.80665 \,\text{m/s}^2$（标准重力加速度）。

### 4.3 EMA 指数平滑滤波

为抑制传感器高频噪声，对原始重量施加一阶指数移动平均 (Exponential Moving Average)：

$$m_k^{\text{ema}} = \alpha \cdot m_k^{\text{raw}} + (1 - \alpha) \cdot m_{k-1}^{\text{ema}}$$

其中平滑因子 $\alpha = 0.08$。皮重采集完成后，用当前 $m^{\text{raw}}$ 初始化 $m_0^{\text{ema}}$，避免冷启动收敛延迟。

### 4.4 重量记录

用户按下"记录重量"按钮时，当前 EMA 滤波值 $m^{\text{ema}}$ 加入历史记录：

$$\text{History} = \{(t_1, m_1), (t_2, m_2), \dots\}$$

### 4.5 稳定性判定

系统维护一个长度为 $N_{\text{stab}} = 30$ 的 $F_z^{(B)}$ 滑动窗口，当其标准差满足：

$$\sigma_{F_z} < 0.15 \,\text{N}$$

时判定力读数"稳定"，GUI 提示用户可以记录泥重。该阈值对应约 15 g 的质量波动，低于典型泥重 (200–2000 g) 的 1%。

---

## 5. 信号处理框图

```
FT300 原始力 ──→ [去皮重偏置] ──→ F_sensor ──→ [R_B^T @ R_T^S] ──→ F_base
                                                                 │
                                            ┌────────────────────┘
                                            ▼
                                      Fz_world = F_base[2]
                                            │
                                            ▼
                              ┌──── delta_Fz = |Fz - F_tare| ────┐
                              │                                   │
                              ▼                                   ▼
                        皮重采集 (80样本)                   m_raw = delta_Fz / g × 1000
                              │                                   │
                              ▼                                   ▼
                         F_tare ← 均值                    m_ema = α·m_raw + (1-α)·m_ema_prev
                                                                  │
                                                                  ▼
                                                            GUI 显示泥重
```

---

## 6. 关键矩阵数值汇总

### $\mathbf{R}_T^S$ — TCP → 传感器旋转矩阵 (常量)

$$\mathbf{R}_T^S = \begin{bmatrix}
0 & 0 & -1 \\
-0.819149 & 0.573580 & 0 \\
0.573580 & 0.819149 & 0
\end{bmatrix}$$

该矩阵源自 URDF 定义的连续旋转变换：

$$\mathbf{R}_T^S = \left[\mathbf{R}_z(-0.61087) \cdot \mathbf{R}_y(\tfrac{\pi}{2}) \cdot \mathbf{R}_x(-\tfrac{\pi}{2})\right]^\top$$

### $\mathbf{R}_B^T(\boldsymbol{\omega})$ — 基座 → TCP 旋转矩阵 (实时)

由 UR 控制器输出的 TCP 轴角姿态 $\boldsymbol{\omega} = (\text{Act\_RX}, \text{Act\_RY}, \text{Act\_RZ})$ 通过 Rodrigues 公式计算，每帧更新。

### 重力加速度常数

$$g = 9.80665 \,\text{m/s}^2$$

### 滤波与控制参数

| 参数 | 符号 | 值 | 含义 |
|------|------|-----|------|
| 皮重样本数 | $N_{\text{tare}}$ | 80 | 皮重均值采集窗口 |
| EMA 平滑因子 | $\alpha$ | 0.08 | 重量指数平滑系数 |
| 稳定性窗口 | $N_{\text{stab}}$ | 30 | 标准差滑动窗口长度 |
| 稳定性阈值 | $\sigma_{\text{thr}}$ | 0.15 N | 判定读数稳定的标准差上限 |

---

## 参考文献

1. UR10 URDF 机械装配文件: `assembly_xacro/assembly/assembly.urdf.xacro`
2. Rodrigues, O. "Des lois géométriques qui régissent les déplacements d'un système solide." *Journal de Mathématiques Pures et Appliquées*, 1840.
3. Siciliano, B., Sciavicco, L., Villani, L., Oriolo, G. *Robotics: Modelling, Planning and Control*. Springer, 2009. (几何雅可比与静力变换)

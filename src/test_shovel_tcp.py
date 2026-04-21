import numpy as np
from scipy.spatial.transform import Rotation as R

def rpy_to_rot(rpy_rad):
    """将 RPY (xyz 顺序，弧度) 转换为旋转矩阵"""
    return R.from_euler('xyz', rpy_rad, degrees=False).as_matrix()

def rot_to_rpy(rot_mat):
    """将旋转矩阵转换为 RPY (xyz 顺序，弧度)"""
    return R.from_matrix(rot_mat).as_euler('xyz', degrees=False)

# ------------------------------------------------------------
# 1. 从 Xacro 提取的数据
# ------------------------------------------------------------
# T1: wrist_3_link -> 铲子
xyz1 = np.array([0.0, 0.105, 0.0])
rpy1 = np.array([1.5707963, 0.0, -1.5707963])
R1 = rpy_to_rot(rpy1)
T1 = np.eye(4)
T1[:3, :3] = R1
T1[:3, 3] = xyz1

# T2: wrist_3_link -> shovel_tip
xyz2 = np.array([-0.00318, 0.15268, 0.47736])
rpy2 = np.array([1.2194, -0.0628, -0.0628])
R2 = rpy_to_rot(rpy2)
T2 = np.eye(4)
T2[:3, :3] = R2
T2[:3, 3] = xyz2

# ------------------------------------------------------------
# 2. 论文中的 T_F^T 矩阵 (法兰 -> TCP)
# ------------------------------------------------------------
T_paper = np.array([
    [ 0.9961, -0.0372, -0.0805, -0.0032],
    [-0.0627,  0.3472, -0.9357,  0.1527],
    [ 0.0628,  0.9370,  0.3435,  0.4774],
    [ 0.0,     0.0,     0.0,     1.0   ]
])

# ------------------------------------------------------------
# 3. 对比 T2 与 T_paper
# ------------------------------------------------------------
diff_trans = T2[:3, 3] - T_paper[:3, 3]
diff_rot = T2[:3, :3] - T_paper[:3, :3]
print("=== 对比 T2 (Xacro shovel_tip) 与 T_paper ===")
print(f"平移差: {diff_trans} (范数: {np.linalg.norm(diff_trans):.6f})")
print(f"旋转矩阵最大偏差: {np.max(np.abs(diff_rot)):.6f}")
print()

# ------------------------------------------------------------
# 4. 计算铲子 -> shovel_tip 的变换 T3 = inv(T1) * T2
# ------------------------------------------------------------
T1_inv = np.linalg.inv(T1)
T3 = T1_inv @ T2
xyz3 = T3[:3, 3]
rpy3 = rot_to_rpy(T3[:3, :3])

print("=== 如果 shovel_tip 是 铲子 的子连杆，所需关节 origin ===")
print(f"xyz = [{xyz3[0]:.6f}, {xyz3[1]:.6f}, {xyz3[2]:.6f}]")
print(f"rpy = [{rpy3[0]:.6f}, {rpy3[1]:.6f}, {rpy3[2]:.6f}]")
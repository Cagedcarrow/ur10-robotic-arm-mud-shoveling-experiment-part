#!/usr/bin/env python3
"""
重新绘制 14 张分析图表，所有标签使用中文。
覆盖 data/analysis_results_20260513_005805/figures/ 下的英文版。
"""

import os, sys, glob, warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
_cache = matplotlib.get_cachedir()
for _f in glob.glob(os.path.join(_cache, 'fontlist*')):
    try:
        os.remove(_f)
    except OSError:
        pass
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
fm._load_fontmanager(try_read_cache=False)

# 中文字体
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 路径
BASE = "/root/ur10_ws/src/mud_experiment_recorder/data/analysis_results_20260513_005805"
FEAT_CSV = f"{BASE}/tables/single_run_features.csv"
GRID_CSV = f"{BASE}/tables/response_surface_grid.csv"
GROUP_CSV = f"{BASE}/tables/grouped_summary_by_test.csv"
FACTOR_CSV = f"{BASE}/tables/factor_level_summary.csv"
CAND_CSV = f"{BASE}/tables/multi_objective_candidates.csv"
FIG_DIR = f"{BASE}/figures"
os.makedirs(FIG_DIR, exist_ok=True)

df = pd.read_csv(FEAT_CSV)
grid = pd.read_csv(GRID_CSV)
cand = pd.read_csv(CAND_CSV)
group = pd.read_csv(GROUP_CSV)
factor = pd.read_csv(FACTOR_CSV)

ANGLE_LEVELS = [20, 35, 50]
SPEED_LEVELS = [35, 70, 100]
DEPTH_LEVELS = [20, 40, 60]


def save(fig, name):
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✔ {name}")


# ======= 图1: 27 次实验铲泥质量柱状图 =======
def fig01():
    fig, ax = plt.subplots(figsize=(16, 6))
    names = [f"{r['folder']}\n{r['angle_deg']}°/{r['speed_percent']}%/{r['depth_mm']}mm"
             for _, r in df.iterrows()]
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, 9))
    bar_colors = [colors[r['test_no'] - 1] for _, r in df.iterrows()]
    ax.bar(range(len(df)), df["mass_g"].values, color=bar_colors, edgecolor='k', linewidth=0.5)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(names, fontsize=6, rotation=45, ha='right')
    ax.set_ylabel("铲泥质量 (g)", fontsize=12)
    ax.set_title("图1  27 次实验铲泥质量柱状图", fontsize=14, fontweight='bold')
    idx_max = df["mass_g"].idxmax()
    ax.text(idx_max, df.loc[idx_max, "mass_g"] + 5,
            f"最大: {df.loc[idx_max, 'mass_g']:.0f}g",
            ha='center', fontsize=10, fontweight='bold', color='red')
    fig.tight_layout()
    save(fig, "01_weight_bar_all_runs.png")

# ======= 图2: 三因素铲泥质量分布 =======
def fig02():
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for idx, (factor, label, levels) in enumerate([
        ("angle_deg", "入泥角度 (°)", ANGLE_LEVELS),
        ("speed_percent", "铲泥速度 (%)", SPEED_LEVELS),
        ("depth_mm", "入泥深度 (mm)", DEPTH_LEVELS),
    ]):
        ax = axes[idx]
        data, labs = [], []
        for lv in levels:
            sub = df[df[factor] == lv]["mass_g"].dropna()
            if len(sub) > 0:
                data.append(sub.values), labs.append(str(lv))
        bp = ax.boxplot(data, labels=labs, patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor(plt.cm.viridis(0.5))
        ax.set_xlabel(label, fontsize=11)
        ax.set_ylabel("铲泥质量 (g)", fontsize=11)
        for i, d in enumerate(data):
            ax.scatter(np.ones(len(d)) * (i + 1) + np.random.uniform(-0.1, 0.1, len(d)),
                       d, alpha=0.6, color='red', s=30, zorder=3)
    fig.suptitle("图2  三因素下铲泥质量分布", fontsize=14, fontweight='bold')
    fig.tight_layout()
    save(fig, "02_weight_by_angle_speed_depth.png")

# ======= 图3: 典型力曲线 =======
def fig03():
    # 找三个典型实验：质量最大、质量最小、综合评分最佳
    idx_max_w = df["mass_g"].idxmax()
    idx_min_w = df["mass_g"].idxmin()
    df_temp = df.copy()
    for c in ["mass_g", "E_mech", "F_max"]:
        v = df_temp[c].values.astype(float)
        vm, vM = np.nanmin(v), np.nanmax(v)
        if vM - vm > 1e-9:
            if c == "mass_g":
                df_temp["_score"] = (v - vm) / (vM - vm)
            else:
                df_temp["_score"] = df_temp.get("_score", 0) - (v - vm) / (vM - vm)
    df_temp["_score"] = df_temp.get("_score", 0)
    idx_best = df_temp["_score"].idxmax()

    # 读取原始力数据
    import csv
    def load_force(folder):
        csv_path = f"/root/ur10_ws/src/mud_experiment_recorder/data/{folder}/session_data.csv"
        if not os.path.exists(csv_path): return None
        with open(csv_path) as f:
            header = [h.strip() for h in f.readline().strip().split(',')]
        dfr = pd.read_csv(csv_path, skiprows=0)
        dfr.columns = dfr.columns.str.strip()
        if "force_base_x" in dfr.columns:
            fx = pd.to_numeric(dfr["force_base_x"], errors='coerce').values
            fy = pd.to_numeric(dfr["force_base_y"], errors='coerce').values
            fz = pd.to_numeric(dfr["force_base_z"], errors='coerce').values
        elif "Fx" in dfr.columns:
            fx = pd.to_numeric(dfr["Fx"], errors='coerce').values
            fy = pd.to_numeric(dfr["Fy"], errors='coerce').values
            fz = pd.to_numeric(dfr["Fz"], errors='coerce').values
        else:
            return None
        t = pd.to_numeric(dfr["epoch_time"], errors='coerce').values
        t = t - t[0]
        f_res = np.sqrt(fx**2 + fy**2 + fz**2)
        # 检测铲泥阶段
        n_base = max(5, len(dfr)//10)
        mu0 = np.nanmean(f_res[:n_base])
        sig0 = np.nanstd(f_res[:n_base])
        thr = mu0 + 3*sig0
        above = f_res > thr
        mud_start = mud_end = None
        if np.any(above):
            idxs = np.where(above)[0]
            mud_start = float(t[max(0, idxs[0]-5)])
            mud_end = float(t[min(len(t)-1, idxs[-1]+5)])
        return {"t": t, "f_res": f_res, "mud_start": mud_start, "mud_end": mud_end}

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    titles = [
        f"铲泥质量最大: {df.loc[idx_max_w, 'folder']}（{df.loc[idx_max_w, 'mass_g']:.0f}g）",
        f"综合评分最佳: {df.loc[idx_best, 'folder']}",
        f"铲泥质量最小: {df.loc[idx_min_w, 'folder']}（{df.loc[idx_min_w, 'mass_g']:.0f}g）",
    ]
    for ax, idx_exp, title in zip(axes, [idx_max_w, idx_best, idx_min_w], titles):
        folder = df.loc[idx_exp, "folder"]
        d = load_force(folder)
        if d:
            ax.plot(d["t"], d["f_res"], 'b-', linewidth=0.8, label="合力 F_res (N)")
            if d["mud_start"] is not None:
                ax.axvline(d["mud_start"], color='g', linestyle='--', alpha=0.7, label="铲泥开始")
                ax.axvline(d["mud_end"], color='r', linestyle='--', alpha=0.7, label="铲泥结束")
                ax.axvspan(d["mud_start"], d["mud_end"], alpha=0.1, color='green')
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("时间 (s)", fontsize=10)
        ax.set_ylabel("合力 (N)", fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    fig.suptitle("图3  典型实验力-时间曲线", fontsize=14, fontweight='bold')
    fig.tight_layout()
    save(fig, "03_force_time_examples.png")

# ======= 图4: 受力特征对比 =======
def fig04():
    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(df))
    w = 0.25
    ax.bar(x - w, df["F_mean"].values, w, label="平均力", alpha=0.8)
    ax.bar(x,     df["F_max"].values,  w, label="最大力", alpha=0.8)
    ax.bar(x + w, df["F_impulse"].values / 10, w, label="力冲量/10", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['folder']}\n{r['angle_deg']}°/{r['speed_percent']}%/{r['depth_mm']}mm"
                        for _, r in df.iterrows()], fontsize=5, rotation=45, ha='right')
    ax.set_ylabel("力 (N)", fontsize=11)
    ax.set_title("图4  各实验受力特征对比", fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    fig.tight_layout()
    save(fig, "04_force_features_bar.png")

# ======= 图5: 能耗特征对比 =======
def fig05():
    fig, ax1 = plt.subplots(figsize=(16, 5))
    x = np.arange(len(df))
    width = 0.3
    ax1.bar(x - width/2, df["E_mech"].values / 100, width=width,
            label="机械能耗/100", alpha=0.8, color='orange')
    ax1.set_ylabel("机械能耗/100 (J)", color='orange', fontsize=11)
    ax1.tick_params(axis='y', labelcolor='orange')
    ax2 = ax1.twinx()
    ax2.bar(x + width/2, df["mass_per_energy"].values, width=width,
            label="单位能耗铲泥量", alpha=0.8, color='green')
    ax2.set_ylabel("单位能耗铲泥量 (g/J)", color='green', fontsize=11)
    ax2.tick_params(axis='y', labelcolor='green')
    ax1.set_xticks(x)
    ax1.set_xticklabels([r['folder'] for _, r in df.iterrows()], fontsize=6, rotation=45, ha='right')
    ax1.set_title("图5  各实验能耗特征对比", fontsize=14, fontweight='bold')
    fig.tight_layout()
    save(fig, "05_energy_features_bar.png")

# ======= 图6: 轨迹平滑性对比 =======
def fig06():
    fig, ax = plt.subplots(figsize=(16, 5))
    x = np.arange(len(df))
    w = 0.25
    ax.bar(x - w, df["tcp_acc_rms"].values, w, label="加速度 RMS", alpha=0.8)
    ax.bar(x,     df["tcp_jerk_rms"].values / 10000, w, label="急动度 RMS/10000", alpha=0.8)
    ax.bar(x + w, df["joint_rmse"].values * 10000, w, label="关节误差 RMSE×10000", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([r['folder'] for _, r in df.iterrows()], fontsize=6, rotation=45, ha='right')
    ax.set_ylabel("数值", fontsize=11)
    ax.set_title("图6  轨迹平滑性与跟踪误差对比", fontsize=14, fontweight='bold')
    ax.legend(fontsize=9)
    fig.tight_layout()
    save(fig, "06_trajectory_smoothness_bar.png")

# ======= 图7-9: 响应面 3D 图（基于完整网格插值）=======
def make_rsm_surface(x1_name, x2_name, fixed_dict, n=40):
    """
    从 grid 构造固定一个因素后的 2D 响应面切片。
    返回 Xg, Yg, Zg 用于 plot_surface。
    """
    # 找到与固定值最接近的索引
    condition = pd.Series(True, index=grid.index)
    for k, v in fixed_dict.items():
        # 找到最接近固定值的那个网格点
        idx = (grid[k] - v).abs().idxmin()
        condition &= (grid[k] == grid.loc[idx, k])

    sub = grid[condition].copy()
    if sub.empty:
        return None, None, None

    # Pivot 为矩阵
    x_vals = sorted(sub[x1_name].unique())
    y_vals = sorted(sub[x2_name].unique())
    if len(x_vals) < 3 or len(y_vals) < 3:
        return None, None, None

    piv = sub.pivot_table(index=x2_name, columns=x1_name, values="pred_mass_g", aggfunc="mean")
    Xg, Yg = np.meshgrid(piv.columns, piv.index)
    Zg = piv.values
    return Xg, Yg, Zg


def plot_rsm_figure(x1_name, x2_name, fixed_dict, xl, yl, zl, title, fname):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    Xg, Yg, Zg = make_rsm_surface(x1_name, x2_name, fixed_dict)
    if Xg is not None:
        surf = ax.plot_surface(Xg, Yg, Zg, cmap='viridis', alpha=0.8,
                               linewidth=0, antialiased=True)
        fig.colorbar(surf, ax=ax, shrink=0.5, label="预测铲泥质量 (g)")

    # 实际实验散点
    ax.scatter(df[x1_name].values, df[x2_name].values, df["mass_g"].values,
               c='red', s=50, marker='o', label='实验数据', alpha=0.8, edgecolors='k')

    ax.set_xlabel(xl, fontsize=11)
    ax.set_ylabel(yl, fontsize=11)
    ax.set_zlabel(zl, fontsize=11)
    ax.set_title(title, fontsize=13)
    ax.legend(fontsize=9)
    fig.tight_layout()
    save(fig, fname)


def fig07():
    plot_rsm_figure("angle_deg", "speed_percent", {"depth_mm": 40},
                    "入泥角度 (°)", "铲泥速度 (%)", "预测铲泥质量 (g)",
                    "图7  铲泥质量响应面趋势图（深度=40 mm）",
                    "07_response_surface_weight_angle_speed.png")

def fig08():
    plot_rsm_figure("angle_deg", "depth_mm", {"speed_percent": 70},
                    "入泥角度 (°)", "入泥深度 (mm)", "预测铲泥质量 (g)",
                    "图8  铲泥质量响应面趋势图（速度=70%）",
                    "08_response_surface_weight_angle_depth.png")

def fig09():
    plot_rsm_figure("speed_percent", "depth_mm", {"angle_deg": 35},
                    "铲泥速度 (%)", "入泥深度 (mm)", "预测铲泥质量 (g)",
                    "图9  铲泥质量响应面趋势图（角度=35°）",
                    "09_response_surface_weight_speed_depth.png")

# ======= 图10: Pareto 散点图 =======
def fig10():
    fig, ax = plt.subplots(figsize=(10, 8))
    sc = ax.scatter(df["E_mech"].values, df["mass_g"].values,
                    c=df["mass_per_energy"].values, cmap='viridis',
                    s=80, alpha=0.8, edgecolors='k', linewidth=0.5)
    cbar = plt.colorbar(sc, ax=ax, label="单位能耗铲泥量 (g/J)")
    idx_best = df["mass_g"].idxmax()
    ax.annotate(f"最大质量\n{df.loc[idx_best, 'folder']}",
                (df.loc[idx_best, "E_mech"], df.loc[idx_best, "mass_g"]),
                fontsize=8, xytext=(5, 5), textcoords='offset points')
    ax.set_xlabel("机械能耗 (J)", fontsize=11)
    ax.set_ylabel("铲泥质量 (g)", fontsize=11)
    ax.set_title("图10  能耗-质量多目标候选分布", fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save(fig, "10_pareto_mass_energy_force.png")

# ======= 图11-13: 主效应图 =======
def plot_main_effect(response, resp_label, fname, title):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    factors = ["angle_deg", "speed_percent", "depth_mm"]
    labels  = ["入泥角度 (°)", "铲泥速度 (%)", "入泥深度 (mm)"]
    for idx, (fac, lab) in enumerate(zip(factors, labels)):
        ax = axes[idx]
        levels = sorted(df[fac].unique())
        means = [df[df[fac] == l][response].mean() for l in levels]
        stds  = [df[df[fac] == l][response].std() for l in levels]
        ax.errorbar(levels, means, yerr=stds, marker='o', capsize=5, linewidth=2, color='#2C7FB8')
        ax.set_xlabel(lab, fontsize=11)
        ax.set_ylabel(resp_label, fontsize=11)
        ax.set_title(f"{lab} 对 {resp_label} 的影响", fontsize=11)
        ax.grid(True, alpha=0.3)
    fig.suptitle(title, fontsize=14, fontweight='bold')
    fig.tight_layout()
    save(fig, fname)

def fig11():
    plot_main_effect("mass_g", "铲泥质量 (g)",
                     "11_factor_main_effect_weight.png", "图11  铲泥质量主效应图")

def fig12():
    plot_main_effect("E_mech", "机械能耗 (J)",
                     "12_factor_main_effect_energy.png", "图12  机械能耗主效应图")

def fig13():
    plot_main_effect("F_max", "最大阻力 (N)",
                     "13_factor_main_effect_force.png", "图13  阻力峰值主效应图")

# ======= 图14: 相关性热力图 =======
def fig14():
    cols = ["mass_g", "F_mean", "F_max", "F_impulse", "E_mech",
            "mass_per_energy", "tcp_jerk_rms", "joint_rmse", "P_mean", "tau_rms"]
    labels_cn = ["铲泥质量", "平均力", "最大力", "力冲量", "机械能耗",
                 "单位能耗\n铲泥量", "急动度RMS", "关节误差\nRMSE", "平均功率", "扭矩RMS"]
    avail = [c for c in cols if c in df.columns]
    if len(avail) < 2:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "数据不足", ha='center', va='center')
        save(fig, "14_correlation_heatmap.png")
        return
    corr = df[avail].corr()
    # 只选对应的中文标签
    label_map = dict(zip(cols, labels_cn))
    tick_labels = [label_map.get(c, c) for c in avail]

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_xticks(range(len(avail)))
    ax.set_yticks(range(len(avail)))
    ax.set_xticklabels(tick_labels, fontsize=9, rotation=45, ha='right')
    ax.set_yticklabels(tick_labels, fontsize=9)
    for i in range(len(avail)):
        for j in range(len(avail)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha='center', va='center', fontsize=8,
                    color='white' if abs(corr.values[i, j]) > 0.5 else 'black')
    ax.set_title("图14  关键指标相关性热力图", fontsize=14, fontweight='bold')
    fig.tight_layout()
    save(fig, "14_correlation_heatmap.png")


if __name__ == "__main__":
    print("重绘中文图表...")
    fig01(); fig02(); fig03(); fig04(); fig05(); fig06()
    fig07(); fig08(); fig09()
    fig10(); fig11(); fig12(); fig13(); fig14()
    print(f"\n全部完成！图片保存在 {FIG_DIR}")

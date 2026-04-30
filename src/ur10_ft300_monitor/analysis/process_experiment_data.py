#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="处理单个 UR10+FT300 实验目录")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dir", type=str, help="实验目录，例如 data/20260430_203015")
    group.add_argument("--csv", type=str, help="直接指定 csv 文件路径")
    parser.add_argument("--mass-g", type=float, default=None, help="人工称重质量(g)，优先级高于 manual_record.txt")
    parser.add_argument("--force-threshold", type=float, default=10.0, help="力突变阈值，单位 N")
    parser.add_argument("--smooth-window", type=int, default=5, help="滑动平均窗口")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        from metrics_utils import process_experiment
    except ImportError as exc:
        print(str(exc))
        return 2

    if args.dir:
        experiment_dir = Path(args.dir).resolve()
        csv_path = experiment_dir / "ur10_ft300_realtime_data.csv"
    else:
        csv_path = Path(args.csv).resolve()
        experiment_dir = csv_path.parent

    try:
        result = process_experiment(
            experiment_dir=experiment_dir,
            csv_path=csv_path,
            mass_g_cli=args.mass_g,
            force_threshold=args.force_threshold,
            smooth_window=args.smooth_window,
        )
    except Exception as exc:
        print(f"[ERROR] 处理失败: {exc}")
        return 1

    print(f"[OK] 处理完成: {experiment_dir}")
    print(f"[OK] 关键指标: F_max={result.metrics.get('F_max')}, E_force={result.metrics.get('E_force')}")
    print(f"[OK] 输出文件:")
    print(f"  - {experiment_dir / 'processed_metrics.csv'}")
    print(f"  - {experiment_dir / 'processed_summary.txt'}")
    print(f"  - {experiment_dir / 'figures'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

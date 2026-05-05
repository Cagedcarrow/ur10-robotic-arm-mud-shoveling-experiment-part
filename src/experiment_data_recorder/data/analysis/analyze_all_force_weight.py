#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from analyze_force_weight import (
    DEFAULT_MODEL_FILE,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_REFERENCE_MODE,
    DEFAULT_ROLLING_WINDOW,
    DEFAULT_SENSOR_FRAME,
    DEFAULT_TCP_FRAME,
    DEFAULT_WEIGHT_AXIS_MODE,
    ROOT,
    analyze_session,
)


DEFAULT_DATA_ROOT = ROOT / "data"
DEFAULT_SUMMARY_MD = DEFAULT_OUTPUT_ROOT / "all_sessions_weight_summary.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch analyze all data/<session>/ur10_ft300_realtime_data.csv sessions.")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    parser.add_argument("--joint-threshold", type=float, default=5e-4)
    parser.add_argument("--min-stable-samples", type=int, default=50)
    parser.add_argument("--rolling-window", type=int, default=DEFAULT_ROLLING_WINDOW)
    parser.add_argument("--weight-axis-mode", choices=["base_z", "magnitude"], default=DEFAULT_WEIGHT_AXIS_MODE)
    parser.add_argument("--reference-mode", choices=["low_load_candidate", "pre_final_stable"], default=DEFAULT_REFERENCE_MODE)
    parser.add_argument("--model-file", type=Path, default=DEFAULT_MODEL_FILE)
    parser.add_argument("--tcp-frame-name", default=DEFAULT_TCP_FRAME)
    parser.add_argument("--sensor-frame-name", default=DEFAULT_SENSOR_FRAME)
    parser.add_argument("--reference-lookback-s", type=float, default=4.0)
    parser.add_argument("--reference-window-samples", type=int, default=60)
    parser.add_argument("--reference-min-gap-s", type=float, default=0.5)
    return parser.parse_args()


def find_session_dirs(data_root: Path) -> list[Path]:
    sessions = []
    for path in sorted(data_root.iterdir()):
        if path.is_dir() and (path / "ur10_ft300_realtime_data.csv").exists():
            sessions.append(path)
    return sessions


def build_session_args(batch_args: argparse.Namespace, session_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        session_dir=session_dir,
        joint_threshold=batch_args.joint_threshold,
        min_stable_samples=batch_args.min_stable_samples,
        rolling_window=batch_args.rolling_window,
        output_dir=batch_args.output_root / session_dir.name,
        weight_axis_mode=batch_args.weight_axis_mode,
        reference_mode=batch_args.reference_mode,
        model_file=batch_args.model_file,
        tcp_frame_name=batch_args.tcp_frame_name,
        sensor_frame_name=batch_args.sensor_frame_name,
        reference_lookback_s=batch_args.reference_lookback_s,
        reference_window_samples=batch_args.reference_window_samples,
        reference_min_gap_s=batch_args.reference_min_gap_s,
    )


def write_summary_markdown(results: list[dict[str, object]], failures: list[tuple[str, str]], summary_md: Path) -> None:
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Data 目录批量重量分析结果",
        "",
        "## 1. 分析说明",
        "",
        "- 默认采用最终称重点前一个稳态段作为 `0 g` 参考段。",
        "- 默认采用基坐标系 `Z` 方向投影力差估计重量。",
        "- 每个会话的详细图表和 CSV 输出位于 `data/analysis/output/<session>/`。",
        "",
        "## 2. 重量变化汇总",
        "",
        "| Session | Reference Type | Reference Window (s) | Final Window (s) | Pose Distance | Reference Base Z (N) | Final Base Z (N) | Delta F_base_z (N) | Estimated Mass (g) | Risk | Output |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for result in results:
        session_name = Path(result["session_dir"]).name
        output_rel = Path(result["output_dir"]).relative_to(ROOT)
        lines.append(
            f"| {session_name} | "
            f"{result['reference_type']} | "
            f"{result['reference_start_time']:.3f} -> {result['reference_end_time']:.3f} | "
            f"{result['final_start_time']:.3f} -> {result['final_end_time']:.3f} | "
            f"{result['reference_pose_distance']:.3f} | "
            f"{result['reference_force_base_z']:.3f} | "
            f"{result['final_force_base_z']:.3f} | "
            f"{result['delta_force_base_z']:.3f} | "
            f"{result['estimated_mass_g']:.2f} | "
            f"{result['risk_level']} | "
            f"`{output_rel}` |"
        )
    if failures:
        lines.extend(
            [
                "",
                "## 3. 失败会话",
                "",
                "| Session | Error |",
                "| --- | --- |",
            ]
        )
        for session_name, error in failures:
            lines.append(f"| {session_name} | {error} |")
    lines.extend(
        [
            "",
            "## 4. 备注",
            "",
            "- 若某个会话的参考段选择不符合实验语义，建议后续增加手动时间窗参数或多候选参考段评分。",
            "- 当前结果依赖 `assembly.urdf.xacro` 中的 TCP 与传感器固定旋转关系。",
        ]
    )
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    session_dirs = find_session_dirs(args.data_root.resolve())
    if not session_dirs:
        raise RuntimeError(f"No session directories with { 'ur10_ft300_realtime_data.csv' } found under {args.data_root}")

    results: list[dict[str, object]] = []
    failures: list[tuple[str, str]] = []

    print(f"Found {len(session_dirs)} session folders under {args.data_root.resolve()}")
    for session_dir in session_dirs:
        session_name = session_dir.name
        try:
            result = analyze_session(build_session_args(args, session_dir), print_console_summary=False)
            results.append(result)
            warning = " WARNING" if result["risk_level"] == "high" else ""
            print(
                f"{session_name}: "
                f"mass={result['estimated_mass_g']:.2f} g, "
                f"delta_base_z={result['delta_force_base_z']:.3f} N, "
                f"reference_type={result['reference_type']}, "
                f"pose_dist={result['reference_pose_distance']:.3f}, "
                f"ref={result['reference_start_time']:.3f}->{result['reference_end_time']:.3f} s, "
                f"final={result['final_start_time']:.3f}->{result['final_end_time']:.3f} s, "
                f"risk={result['risk_level']}{warning}"
            )
        except Exception as exc:  # pragma: no cover - batch robustness
            failures.append((session_name, str(exc)))
            print(f"{session_name}: FAILED - {exc}")

    write_summary_markdown(results, failures, args.summary_md.resolve())
    print(f"Summary markdown written to: {args.summary_md.resolve()}")
    print(f"Successful analyses: {len(results)} / {len(session_dirs)}")
    if failures:
        print(f"Failures: {len(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

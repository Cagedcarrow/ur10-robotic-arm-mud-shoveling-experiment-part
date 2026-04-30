#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
import yaml

from metrics_utils import process_experiment


DEFAULT_CONFIG = {
    "base_url": "https://api.deepseek.com",
    "api_key": "YOUR_DEEPSEEK_API_KEY",
    "model": "deepseek-v4-pro",
    "timeout_sec": 120,
    "temperature": 0.2,
}


@dataclass
class LLMReportResult:
    report_path: Path
    metrics_path: Path
    raw_response_path: Path


def ensure_config_file(config_path: Path) -> None:
    if config_path.exists():
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False, allow_unicode=True), encoding="utf-8")


def load_llm_config(config_path: Path) -> Dict[str, object]:
    ensure_config_file(config_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(data)
    return cfg


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _call_chat_completion(prompt: str, cfg: Dict[str, object]) -> Dict[str, object]:
    api_key = str(cfg.get("api_key", "")).strip()
    if not api_key or api_key == "YOUR_DEEPSEEK_API_KEY":
        raise ValueError("配置文件中的 api_key 未填写，请先在 config/llm_config.yaml 中设置。")

    base_url = str(cfg.get("base_url", DEFAULT_CONFIG["base_url"])).rstrip("/")
    model = str(cfg.get("model", DEFAULT_CONFIG["model"])).strip()
    timeout_sec = int(cfg.get("timeout_sec", 120))
    temperature = float(cfg.get("temperature", 0.2))

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是机器人实验数据分析助手，必须严格按给定README指标定义进行解读。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    if resp.status_code >= 400:
        raise RuntimeError(f"DeepSeek API 请求失败: HTTP {resp.status_code} - {resp.text[:500]}")
    return resp.json()


def build_prompt(readme_text: str, metrics_csv_text: str, meta_text: str, manual_text: str, exp_dir: Path) -> str:
    return f"""请基于以下材料，输出一份结构化 Markdown 实验分析报告（中文）：

## 输出格式（必须按此结构）
1. 实验概况
2. 关键指标解释（至少覆盖 F_max, E_force, smoothness_force, I_mean）
3. 风险诊断（机械臂/控制/数据质量）
4. 结论
5. 下一步建议（可执行）

## 约束
- 指标含义必须遵循 README 中定义，不得自造定义。
- 若指标缺失，明确写“缺失/不可判定”。
- 给出简洁、工程化建议，避免空泛表述。

## 实验目录
{exp_dir}

## 指标定义参考 README_analysis.md
{readme_text}

## processed_metrics.csv 内容
{metrics_csv_text}

## metadata.txt（若有）
{meta_text}

## manual_record.txt（若有）
{manual_text}
"""


def _extract_markdown_from_response(data: Dict[str, object]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("DeepSeek 返回中缺少 choices。")
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("DeepSeek 返回内容为空。")
    return content.strip() + "\n"


def test_connection(config_path: Path) -> str:
    cfg = load_llm_config(config_path)
    data = _call_chat_completion("请回复: 连接成功", cfg)
    msg = _extract_markdown_from_response(data)
    return msg


def generate_single_experiment_report(
    experiment_dir: Path,
    root_dir: Path,
    config_path: Path,
    force_threshold: float = 10.0,
    smooth_window: int = 5,
    report_dir: Optional[Path] = None,
) -> LLMReportResult:
    experiment_dir = experiment_dir.resolve()
    readme_path = root_dir / "analysis" / "README_analysis.md"
    metrics_path = experiment_dir / "processed_metrics.csv"
    csv_path = experiment_dir / "ur10_ft300_realtime_data.csv"

    if not experiment_dir.exists() or not experiment_dir.is_dir():
        raise FileNotFoundError(f"实验目录不存在: {experiment_dir}")
    if not metrics_path.exists():
        if not csv_path.exists():
            raise FileNotFoundError(f"目录中既没有 processed_metrics.csv 也没有原始 CSV: {experiment_dir}")
        process_experiment(
            experiment_dir=experiment_dir,
            csv_path=csv_path,
            mass_g_cli=None,
            force_threshold=force_threshold,
            smooth_window=smooth_window,
        )
        if not metrics_path.exists():
            raise RuntimeError("自动处理后仍未生成 processed_metrics.csv。")

    metrics_csv_text = metrics_path.read_text(encoding="utf-8", errors="ignore")
    readme_text = _read_text_if_exists(readme_path)
    meta_text = _read_text_if_exists(experiment_dir / "metadata.txt")
    manual_text = _read_text_if_exists(experiment_dir / "manual_record.txt")
    prompt = build_prompt(readme_text, metrics_csv_text, meta_text, manual_text, experiment_dir)
    cfg = load_llm_config(config_path)
    raw_data = _call_chat_completion(prompt, cfg)
    report_md = _extract_markdown_from_response(raw_data)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = report_dir.resolve() if report_dir is not None else (root_dir / "results" / "llm_reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{experiment_dir.name}_{ts}_report.md"
    raw_response_path = out_dir / f"{experiment_dir.name}_{ts}_raw.json"
    report_path.write_text(report_md, encoding="utf-8")
    raw_response_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return LLMReportResult(report_path=report_path, metrics_path=metrics_path, raw_response_path=raw_response_path)

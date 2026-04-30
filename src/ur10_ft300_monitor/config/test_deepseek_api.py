#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests
import yaml


def load_config(cfg_path: Path) -> dict:
    if not cfg_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {cfg_path}")
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    required = ["base_url", "api_key", "model"]
    missing = [k for k in required if not str(cfg.get(k, "")).strip()]
    if missing:
        raise ValueError(f"配置缺少字段: {', '.join(missing)}")
    if str(cfg.get("api_key")).strip() == "YOUR_DEEPSEEK_API_KEY":
        raise ValueError("请先在 llm_config.yaml 中填写真实 api_key。")
    return cfg


def call_api(cfg: dict, prompt: str) -> dict:
    base_url = str(cfg["base_url"]).rstrip("/")
    api_key = str(cfg["api_key"]).strip()
    model = str(cfg["model"]).strip()
    timeout_sec = int(cfg.get("timeout_sec", 60))
    temperature = float(cfg.get("temperature", 0.2))

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是API连通性测试助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def extract_text(resp_json: dict) -> str:
    choices = resp_json.get("choices")
    if not isinstance(choices, list) or not choices:
        return "[WARN] 返回中没有 choices。"
    msg = choices[0].get("message", {})
    content = msg.get("content", "")
    return content if isinstance(content, str) else json.dumps(msg, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="测试 DeepSeek API 调用")
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path(__file__).resolve().parent / "llm_config.yaml"),
        help="llm_config.yaml 路径",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="请只回复：API连接成功",
        help="测试提示词",
    )
    args = parser.parse_args()

    cfg_path = Path(args.config).resolve()
    try:
        cfg = load_config(cfg_path)
        resp_json = call_api(cfg, args.prompt)
        text = extract_text(resp_json)
    except Exception as exc:
        print(f"[ERROR] 调用失败: {exc}")
        return 1

    print("[OK] API 调用成功")
    print(f"[INFO] model: {cfg.get('model')}")
    print("[INFO] response:")
    print(text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

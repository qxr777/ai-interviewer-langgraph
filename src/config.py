"""全局配置加载器：从 .env + config.yaml 合并配置。"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# 默认值
DEFAULTS = {
    # LLM
    "llm_api_key": "",
    "llm_api_base": "https://api.bianxie.ai/v1",
    "llm_model": "deepseek-chat",
    "llm_timeout": 30,
    # 治理
    "evaluator_count": 3,
    "sigma_high": 5.0,
    "sigma_medium": 15.0,
    "max_retries_per_topic": 3,
    "max_global_rounds": 30,
    "max_consecutive_medium": 3,
    "max_invalid_inputs": 3,
    # 日志
    "log_dir": "logs",
    "debug": False,
}


def load_config(project_root: str | None = None) -> dict[str, Any]:
    """加载配置，优先级：环境变量 > config.yaml > 默认值。"""
    root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent
    config: dict[str, Any] = dict(DEFAULTS)

    # 加载 config.yaml
    config_path = root / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            yaml_data = yaml.safe_load(f) or {}
        _merge(config, yaml_data)

    # 加载 .env
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # 环境变量覆盖
    env_overrides = {
        "llm_api_key": os.getenv("LLM_API_KEY"),
        "llm_api_base": os.getenv("LLM_API_BASE"),
        "llm_model": os.getenv("LLM_MODEL"),
        "llm_timeout": os.getenv("LLM_TIMEOUT"),
        "debug": os.getenv("DEBUG"),
    }
    for key, val in env_overrides.items():
        if val is not None:
            config[key] = _cast(val, type(DEFAULTS[key]))

    return config


def _merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base:
            base[k] = v


def _cast(value: str, target_type: type) -> Any:
    if target_type is bool:
        return value.lower() in ("true", "1", "yes")
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    return value

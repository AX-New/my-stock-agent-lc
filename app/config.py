"""
config.py — 全局配置加载
==========================

统一入口，从 `.env` 读所有运行参数。代码中其他模块**不要直接 os.getenv**，
统一从这里 import 已经校验/转型过的常量，避免散落的硬编码。

约束（来自 CLAUDE.md）：
- 所有凭据走 .env，os.getenv 不带默认值（拿不到就报错，避免静默用默认值）
- 非凭据类（端口、目录等）允许有默认值
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根（本文件所在目录的上一级）
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# 加载 .env（若不存在则什么都不做，os.getenv 会返回 None）
load_dotenv(PROJECT_ROOT / ".env")


def _required(key: str) -> str:
    """读取必填环境变量；缺失则抛 RuntimeError。"""
    val = os.getenv(key)
    if not val:
        raise RuntimeError(
            f"环境变量 {key} 未配置。请在 .env 中填写（参考 .env.example）。"
        )
    return val


def _optional(key: str, default: str) -> str:
    """读取选填环境变量，缺失返回默认值。"""
    return os.getenv(key) or default


# ============== LLM Provider ==============
# 默认 Volcengine（豆包系列，OpenAI 兼容协议）。
# 切回 Anthropic 见 .env.example 注释。
LLM_PROVIDER: str = _optional("LLM_PROVIDER", "volcengine")  # volcengine | anthropic

# Volcengine（OpenAI 兼容）
VOLCENGINE_API_KEY: str = _optional("VOLCENGINE_API_KEY", "")
VOLCENGINE_BASE_URL: str = _optional(
    "VOLCENGINE_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"
)

# Anthropic（保留，便于切回）
ANTHROPIC_API_KEY: str = _optional("ANTHROPIC_API_KEY", "")

# 通用 LLM 参数
LLM_MODEL: str = _optional("LLM_MODEL", "doubao-seed-2.0-pro")
LLM_TEMPERATURE: float = float(_optional("LLM_TEMPERATURE", "0.2"))


def validate_llm_config() -> None:
    """启动期校验：当前 provider 的密钥必须配齐。"""
    if LLM_PROVIDER == "volcengine":
        if not VOLCENGINE_API_KEY:
            raise RuntimeError("LLM_PROVIDER=volcengine 但未配置 VOLCENGINE_API_KEY")
    elif LLM_PROVIDER == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("LLM_PROVIDER=anthropic 但未配置 ANTHROPIC_API_KEY")
    else:
        raise RuntimeError(f"不支持的 LLM_PROVIDER: {LLM_PROVIDER}")

# ============== Embedding ==============
EMBEDDING_MODEL: str = _optional("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

# ============== Vector Store ==============
CHROMA_PERSIST_DIR: Path = (
    PROJECT_ROOT / _optional("CHROMA_PERSIST_DIR", "chroma_db")
).resolve()
CHROMA_COLLECTION: str = _optional("CHROMA_COLLECTION", "docs")

# ============== Server ==============
SERVER_PORT: int = int(_optional("SERVER_PORT", "8004"))
DOCS_DIR: Path = (PROJECT_ROOT / _optional("DOCS_DIR", "data")).resolve()


# ============== 日志 ==============
def setup_logging(level: int = logging.INFO) -> None:
    """统一日志格式：时间 / 级别 / 模块 / 消息。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # 把第三方库的过度日志压一压
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


__all__ = [
    "PROJECT_ROOT",
    "LLM_PROVIDER",
    "VOLCENGINE_API_KEY",
    "VOLCENGINE_BASE_URL",
    "ANTHROPIC_API_KEY",
    "LLM_MODEL",
    "LLM_TEMPERATURE",
    "EMBEDDING_MODEL",
    "CHROMA_PERSIST_DIR",
    "CHROMA_COLLECTION",
    "SERVER_PORT",
    "DOCS_DIR",
    "setup_logging",
    "validate_llm_config",
]

"""
llm.py — LLM 实例统一构造
==============================

按 LLM_PROVIDER 路由到不同的 chat model 实现：
- `volcengine`（默认）：火山引擎方舟（豆包系列），走 OpenAI 兼容协议（langchain-openai）
- `anthropic`：Claude（langchain-anthropic）

封装的好处：上层 agent 代码完全无感切换 provider。
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel

from app.config import (
    ANTHROPIC_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    VOLCENGINE_API_KEY,
    VOLCENGINE_BASE_URL,
)

logger = logging.getLogger(__name__)


def make_llm(streaming: bool = True, temperature: float | None = None) -> BaseChatModel:
    """
    构造一个 chat model 实例（按 LLM_PROVIDER 路由）。

    参数：
        streaming: 是否流式（SSE 场景必须 True；同步调用可 False）
        temperature: 覆盖默认温度

    返回：
        BaseChatModel（ChatOpenAI 或 ChatAnthropic）
    """
    t = LLM_TEMPERATURE if temperature is None else temperature
    logger.debug(
        "创建 LLM: provider=%s model=%s temperature=%s streaming=%s",
        LLM_PROVIDER, LLM_MODEL, t, streaming,
    )

    if LLM_PROVIDER == "volcengine":
        # 火山方舟（豆包等）OpenAI 兼容协议
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=LLM_MODEL,
            temperature=t,
            streaming=streaming,
            api_key=VOLCENGINE_API_KEY,
            base_url=VOLCENGINE_BASE_URL,
            max_tokens=2048,
            # 火山的 coding 网关有时对额外参数敏感；保持最小必要字段
        )

    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=LLM_MODEL,
            temperature=t,
            streaming=streaming,
            api_key=ANTHROPIC_API_KEY,
            max_tokens=2048,
        )

    raise RuntimeError(f"不支持的 LLM_PROVIDER: {LLM_PROVIDER}")

"""
llm.py — LLM 实例统一构造
==============================

封装 ChatAnthropic 创建逻辑，给 agent 层统一调用。
不做缓存（每次新建一个 LLM 实例开销可忽略），但会按 streaming 参数区分。
"""

from __future__ import annotations

import logging

from langchain_anthropic import ChatAnthropic

from app.config import ANTHROPIC_API_KEY, LLM_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


def make_llm(streaming: bool = True, temperature: float | None = None) -> ChatAnthropic:
    """
    构造一个 ChatAnthropic 实例。

    参数：
        streaming: 是否走流式（SSE 场景必须 True；同步调用可 False）
        temperature: 覆盖默认温度（None 表示用配置默认值）

    返回：
        ChatAnthropic 实例
    """
    t = LLM_TEMPERATURE if temperature is None else temperature
    logger.debug(
        "创建 LLM: model=%s temperature=%s streaming=%s", LLM_MODEL, t, streaming
    )
    return ChatAnthropic(
        model=LLM_MODEL,
        temperature=t,
        streaming=streaming,
        api_key=ANTHROPIC_API_KEY,
        max_tokens=2048,
    )

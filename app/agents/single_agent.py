"""
single_agent.py — 基础 tool-calling agent（含会话记忆）
============================================================

最简单的一个 agent：LLM + 几个工具 + 记忆。
学习目标：
- 看懂 LangChain 1.x `create_agent` 的最小用法
- 看懂 LangGraph checkpointer 怎么挂上做 thread 级记忆

为什么不再用 AgentExecutor / ReAct prompt：
- LC 1.x 的 `create_agent` 内部就是 LangGraph，比 0.x 的 AgentExecutor 更稳
- ReAct 文本协议易出格式错误；现代 Claude 直接走 native tool calling 更稳
"""

from __future__ import annotations

import logging

from langchain.agents import create_agent

from app.agents.memory import get_checkpointer
from app.agents.tools import BASIC_TOOLS
from app.llm import make_llm

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个友好的助手，名字叫"小助"。
- 当问题需要算数、当前时间、或公司近况时，主动调用对应工具
- 不知道的事老实说不知道，不要编造
- 回答用简体中文，简洁直接
"""


def build_single_agent():
    """
    返回一个编译好的 LangGraph agent。
    使用方式（异步流式）：
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": "现在几点？"}]},
            config={"configurable": {"thread_id": "user-123"}},
            version="v2",
        ):
            ...
    """
    logger.info("构建 single_agent，工具数=%d", len(BASIC_TOOLS))
    return create_agent(
        model=make_llm(streaming=True),
        tools=BASIC_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=get_checkpointer(),
        name="single_agent",
    )

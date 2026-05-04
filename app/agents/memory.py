"""
memory.py — 会话记忆封装
=============================

LangChain 1.x 的会话记忆推荐通过 LangGraph 的 `checkpointer` 实现：
- 每次调用 agent 时传 `config={"configurable": {"thread_id": "<会话ID>"}}`
- checkpointer 自动保存/恢复该 thread 的全部状态（包括历史 messages）
- 重启进程会丢（学习项目用 InMemorySaver；生产用 SqliteSaver / RedisSaver）

为什么不用 ConversationBufferMemory：
- 那是 0.x 时代的接口，1.x 已经搬到 `langchain_classic` 了，且与新 agent API 不兼容
- checkpointer 是 LC 1.x / LangGraph 标配方案，模块统一性更好

对外暴露：
- `get_checkpointer()`：进程内单例，所有 agent 共享，方便跨 agent 类型保留同一会话历史
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_checkpointer() -> InMemorySaver:
    """进程内会话记忆单例。重启即丢。"""
    logger.info("初始化 InMemorySaver（进程内会话记忆）")
    return InMemorySaver()

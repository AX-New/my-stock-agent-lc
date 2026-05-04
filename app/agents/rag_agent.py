"""
rag_agent.py — RAG 增强的 agent
====================================

和 single_agent 的区别：多挂一个 `retrieve_documents` 工具。
LLM 自己决定什么时候去检索向量库，什么时候直接回答。

学习目标：
- 看懂 RAG 怎么以"工具"的形式融入 agent（而不是固定 chain）
- 这种 RAG 的好处：LLM 可以根据上下文判断"是否需要检索"、"用哪个 query 检索"，
  比固定 retrieval-augmented chain 灵活；坏处：偶尔会该检索却不检索（被 system prompt 引导即可）。
"""

from __future__ import annotations

import logging

from langchain.agents import create_agent

from app.agents.memory import get_checkpointer
from app.agents.tools import ALL_TOOLS
from app.llm import make_llm

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个证券研究助手。
当用户问题涉及行业研报、市场综述、公司近况、行业数据时，**必须先调用 `retrieve_documents` 工具**
检索内部研报库再回答；引用文档片段时务必带上来源文件名。
对于通用问题（算数、当前时间、生活闲聊）不要乱检索。

回答风格：简体中文、要点先行、必要时配数字。
"""


def build_rag_agent():
    """构造一个 RAG 增强的 tool-calling agent。"""
    logger.info("构建 rag_agent，工具数=%d", len(ALL_TOOLS))
    return create_agent(
        model=make_llm(streaming=True),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=get_checkpointer(),
        name="rag_agent",
    )

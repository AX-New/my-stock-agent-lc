"""
traditional_rag.py — 传统 RAG（固定流水线）
=================================================

和 `rag_agent.py` 是**两个极端**的对照样本：

| 特征 | traditional_rag (本文件) | rag_agent (另一文件) |
|------|--------------------------|------------------------|
| 是否一定检索 | ✅ 一定先检索 | ❌ LLM 自己决定 |
| 检索 query 怎么定 | 直接用用户原文 | LLM 改写或选择 |
| 是否有 tool loop | ❌ 无 | ✅ 有 |
| 是否有 agent 决策 | ❌ 无 | ✅ 有 |
| 复杂度 / 灵活性 | 简单、稳定 | 灵活、不可控 |

学习目标：
- 看清"传统 RAG"长什么样：retrieve → stuff → answer，一条直线
- 对照 rag_agent 理解"agentic RAG"为什么更像编码 agent

这里仍然用 LangGraph 实现（而非纯 Python 函数链），是为了保持和其他 agent 同一套
SSE 事件协议（节点切换事件、token 流），前端无需做特殊路由。
"""

from __future__ import annotations

import logging
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.llm import make_llm
from app.rag.vectorstore import get_retriever

logger = logging.getLogger(__name__)


# ================== 状态 ==================


class TradRagState(TypedDict):
    """messages 走 add_messages reducer；docs 暂存检索结果。"""

    messages: Annotated[list, add_messages]
    docs: list


# ================== 节点 ==================

TOP_K = 4


def _retrieve_node(state: TradRagState) -> dict:
    """从最近一条 user 消息中拿 query，调用 retriever，结果存进 state。"""
    last_user = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    query = last_user.content if last_user else ""
    if not query:
        logger.warning("traditional_rag 收到空 query，跳过检索")
        return {"docs": []}

    retriever = get_retriever(top_k=TOP_K)
    docs = retriever.invoke(query)
    logger.info("traditional_rag 检索完成：query=%r 命中=%d", query, len(docs))
    return {"docs": docs}


def _generate_node(state: TradRagState) -> dict:
    """把 docs 拼进 system prompt，再让 LLM 流式生成答案。"""
    last_user = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    query = last_user.content if last_user else ""
    docs = state.get("docs", [])

    if docs:
        ctx_blocks = []
        for i, d in enumerate(docs, 1):
            src = d.metadata.get("source", "unknown")
            ctx_blocks.append(f"[片段{i} | 来源: {src}]\n{d.page_content.strip()}")
        context = "\n\n".join(ctx_blocks)
        sys = (
            "你是研究助手。**只能基于下面提供的资料**回答用户问题。"
            "回答时务必在结尾给出引用来源（带文件名）。如果资料不足以回答，明确说"
            "「资料不足」，不要编造。\n\n"
            f"---资料开始---\n{context}\n---资料结束---"
        )
    else:
        sys = "向量库未返回任何片段，请告知用户当前知识库覆盖不到该问题。"

    llm = make_llm(streaming=True)
    resp = llm.invoke([SystemMessage(content=sys), HumanMessage(content=query)])
    return {"messages": [AIMessage(content=resp.content)]}


# ================== 组图 ==================


def build_traditional_rag():
    """
    传统 RAG：固定两步走的状态机。
    用法（异步流式）：
        async for ev in graph.astream_events(
            {"messages": [HumanMessage(content="...")]}, version="v2"
        ): ...
    """
    logger.info("构建 traditional_rag（固定 retrieve→generate）")
    g = StateGraph(TradRagState)
    g.add_node("retrieve", _retrieve_node)
    g.add_node("generate", _generate_node)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()

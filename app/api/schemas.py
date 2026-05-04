"""
schemas.py — API 请求/响应 schema
====================================
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 支持的 agent 类型
# - single:          tool-calling agent + memory（无 RAG）
# - traditional_rag: 经典 retrieve→stuff→answer，无 agent loop（无 memory）
# - rag:             agentic RAG，retriever 当 tool（有 memory）
# - plan:            plan-and-execute（无 memory）
# - multi:           supervisor 多 agent（无 memory）
# - unified:         综合体：全工具 + memory + 自主决策（日常用最实用）
AgentType = Literal["single", "traditional_rag", "rag", "plan", "multi", "unified"]


class ChatRequest(BaseModel):
    """聊天请求体（POST /chat 用）。"""

    message: str = Field(..., description="用户输入")
    agent: AgentType = Field("single", description="选用的 agent 类型")
    thread_id: str = Field("default", description="会话ID；同 thread 共享 memory")


class IngestResponse(BaseModel):
    files: int
    chunks: int
    elapsed: float

"""
schemas.py — API 请求/响应 schema
====================================
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 支持的 agent 类型
AgentType = Literal["single", "rag", "plan", "multi"]


class ChatRequest(BaseModel):
    """聊天请求体（POST /chat 用）。"""

    message: str = Field(..., description="用户输入")
    agent: AgentType = Field("single", description="选用的 agent 类型")
    thread_id: str = Field("default", description="会话ID；同 thread 共享 memory")


class IngestResponse(BaseModel):
    files: int
    chunks: int
    elapsed: float

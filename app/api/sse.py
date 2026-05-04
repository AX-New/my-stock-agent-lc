"""
sse.py — Agent 事件 → SSE 行
==============================

把 LangGraph 的 `astream_events` 输出转成前端能消费的 SSE 行。
统一事件 schema：
    {"type": "token",      "content": "..."}     # LLM 流式 token
    {"type": "tool_start", "name": "...", "input": ...}
    {"type": "tool_end",   "name": "...", "output": "..."}
    {"type": "node",       "name": "...", "phase": "start|end"}  # LangGraph 节点切换
    {"type": "done"}
    {"type": "error",      "message": "..."}

每个事件以 `data: <json>\\n\\n` 形式发出（标准 SSE）。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


def _ssepack(obj: dict) -> str:
    """把一个 dict 打成 SSE 行（含尾部双换行）。"""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


async def stream_agent_events(
    agent: Any,
    inputs: dict,
    config: dict | None = None,
) -> AsyncIterator[str]:
    """
    驱动 agent 运行并把每一步事件转成 SSE 行。

    参数：
        agent: LangGraph CompiledStateGraph
        inputs: 给 agent 的输入（一般是 {"messages": [...]}）
        config: 可选，包含 thread_id 等
    """
    try:
        async for ev in agent.astream_events(inputs, config=config, version="v2"):
            kind = ev["event"]
            name = ev.get("name", "")
            data = ev.get("data", {})

            # 1) LLM 流式 token
            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                # chunk 是 AIMessageChunk；取 content 文本
                if chunk is not None:
                    content = getattr(chunk, "content", "")
                    text = ""
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        # Claude tool_use 时 content 是 list[block]
                        for blk in content:
                            if isinstance(blk, dict) and blk.get("type") == "text":
                                text += blk.get("text", "")
                    if text:
                        yield _ssepack({"type": "token", "content": text})

            # 2) 工具调用
            elif kind == "on_tool_start":
                yield _ssepack(
                    {
                        "type": "tool_start",
                        "name": name,
                        "input": data.get("input"),
                    }
                )
            elif kind == "on_tool_end":
                # 工具输出文本
                output = data.get("output")
                if hasattr(output, "content"):
                    output = output.content
                yield _ssepack(
                    {
                        "type": "tool_end",
                        "name": name,
                        "output": str(output)[:1000],  # 截断防止过长
                    }
                )

            # 3) LangGraph 节点切换（multi-agent / planner 看节点流）
            elif kind == "on_chain_start" and ev.get("metadata", {}).get("langgraph_node"):
                node = ev["metadata"]["langgraph_node"]
                # 只在节点边界发，避免每个 sub-call 都刷
                if name == node:
                    yield _ssepack({"type": "node", "name": node, "phase": "start"})
            elif kind == "on_chain_end" and ev.get("metadata", {}).get("langgraph_node"):
                node = ev["metadata"]["langgraph_node"]
                if name == node:
                    yield _ssepack({"type": "node", "name": node, "phase": "end"})

        yield _ssepack({"type": "done"})
    except Exception as e:  # noqa: BLE001
        logger.exception("agent 流式执行失败")
        yield _ssepack({"type": "error", "message": str(e)})

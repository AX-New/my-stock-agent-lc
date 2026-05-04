"""
planner.py — Plan-and-Execute Agent（LangGraph 实现）
=========================================================

经典 plan-and-execute 模式：
1. **Planner** 节点：让 LLM 把用户问题拆成一个 JSON 步骤数组
2. **Executor** 节点：循环执行每一步，每步调用一个挂了工具的子 agent
3. **Responder** 节点：把所有步骤结果汇总成最终答案

为什么用 LangGraph 实现而不是纯 Python：
- 状态机表达更清晰（plan / execute / done 三状态）
- 天然支持流式（每个节点的输出都能 stream 出来）
- 学习项目正好展示 LangGraph 用法

为什么不用 langchain-experimental 的旧 PlanAndExecute：
- 旧实现已不维护，且基于已弃用的 AgentExecutor
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, TypedDict

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.tools import ALL_TOOLS
from app.llm import make_llm

logger = logging.getLogger(__name__)


# ================== 状态定义 ==================


class PlanState(TypedDict):
    """LangGraph 状态。messages 用 add_messages reducer 自动追加。"""

    messages: Annotated[list, add_messages]
    plan: list[str]
    current_step: int
    step_results: list[str]
    final_answer: str


# ================== Planner 节点 ==================

PLANNER_PROMPT = """你是任务规划器。用户给了一个问题，请把它拆成 2-5 个有序、可独立执行的步骤。
每一步应该是清晰的指令（动词开头），便于交给执行 agent。
**只输出 JSON 数组**，不要有任何额外文字。例如：
["第一步：检索半导体 Q1 销售数据", "第二步：计算同比增速", "第三步：总结结论"]

用户问题："""


def _planner_node(state: PlanState) -> dict:
    """让 LLM 产出步骤计划。"""
    last_user_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    if last_user_msg is None:
        return {"plan": [], "current_step": 0, "step_results": []}

    llm = make_llm(streaming=False, temperature=0.0)
    resp = llm.invoke(
        [
            SystemMessage(content=PLANNER_PROMPT),
            HumanMessage(content=last_user_msg.content),
        ]
    )
    text = resp.content.strip() if isinstance(resp.content, str) else str(resp.content)
    # 健壮地抠出 JSON 数组
    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        plan = json.loads(text[start:end])
        if not isinstance(plan, list) or not all(isinstance(s, str) for s in plan):
            raise ValueError("plan 不是字符串数组")
    except Exception as e:  # noqa: BLE001
        logger.warning("Planner 输出解析失败，回退为单步：%s", e)
        plan = [last_user_msg.content]

    logger.info("规划完成，共 %d 步: %s", len(plan), plan)
    # 把规划结果作为 AIMessage 也写进 messages，便于前端流式展示
    return {
        "plan": plan,
        "current_step": 0,
        "step_results": [],
        "messages": [AIMessage(content="📋 规划：\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(plan)))],
    }


# ================== Executor 节点 ==================


def _build_step_executor():
    """每个 step 用一个简化的 tool-calling agent 处理。"""
    return create_agent(
        model=make_llm(streaming=False),
        tools=ALL_TOOLS,
        system_prompt=(
            "你正在执行一个多步骤任务中的某一步。请专注于当前 step 的指令，"
            "必要时调用工具；输出执行结论即可，不要展开成完整段落。"
        ),
        name="step_executor",
    )


_step_executor = None


def _executor_node(state: PlanState) -> dict:
    """执行 plan[current_step]，并把结果追加到 step_results。"""
    global _step_executor
    if _step_executor is None:
        _step_executor = _build_step_executor()

    idx = state["current_step"]
    step_text = state["plan"][idx]
    logger.info("执行步骤 %d/%d: %s", idx + 1, len(state["plan"]), step_text)

    result = _step_executor.invoke(
        {"messages": [HumanMessage(content=step_text)]}
    )
    # 取最后一条 AI 消息作为本步结果
    last_ai = next(
        (m for m in reversed(result["messages"]) if isinstance(m, AIMessage)), None
    )
    answer = last_ai.content if last_ai else "(无输出)"
    if isinstance(answer, list):  # claude tool_use 时 content 可能是结构化的
        answer = "".join(
            block.get("text", "") for block in answer if isinstance(block, dict)
        )

    step_msg = AIMessage(content=f"✅ 步骤 {idx+1} 结果：{answer}")
    return {
        "current_step": idx + 1,
        "step_results": state["step_results"] + [str(answer)],
        "messages": [step_msg],
    }


def _should_continue(state: PlanState) -> str:
    """继续执行下一步还是收尾。"""
    if state["current_step"] < len(state["plan"]):
        return "executor"
    return "responder"


# ================== Responder 节点 ==================


def _responder_node(state: PlanState) -> dict:
    """把所有 step 结果交给 LLM 汇总成最终答案（流式）。"""
    last_user_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    user_q = last_user_msg.content if last_user_msg else ""

    summary_input = "\n".join(
        f"步骤 {i+1}：{state['plan'][i]}\n  结果：{r}"
        for i, r in enumerate(state["step_results"])
    )
    llm = make_llm(streaming=True)
    final_msg = llm.invoke(
        [
            SystemMessage(
                content="你是助手。基于下列每步执行结果，给用户一个清晰、要点化的最终答复。"
            ),
            HumanMessage(content=f"原问题：{user_q}\n\n每步结果：\n{summary_input}"),
        ]
    )
    final_text = final_msg.content if isinstance(final_msg.content, str) else str(final_msg.content)
    return {
        "final_answer": final_text,
        "messages": [AIMessage(content=final_text)],
    }


# ================== 组图 ==================


def build_planner_agent():
    """编译一个 plan-and-execute 状态机。"""
    logger.info("构建 plan-and-execute agent")
    g = StateGraph(PlanState)
    g.add_node("planner", _planner_node)
    g.add_node("executor", _executor_node)
    g.add_node("responder", _responder_node)

    g.add_edge(START, "planner")
    g.add_edge("planner", "executor")
    g.add_conditional_edges("executor", _should_continue, {"executor": "executor", "responder": "responder"})
    g.add_edge("responder", END)

    return g.compile()

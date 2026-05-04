"""
multi_agent.py — Supervisor 多 Agent 协作（LangGraph 实现）
================================================================

经典 supervisor 模式：
- **Supervisor**：调度员。读最近的对话，决定下一个动作派给谁，或宣布收工。
- **Researcher**：研究员，专攻文档检索（只挂 RAG 工具）。
- **Analyst**：分析师，做数字 / 公司近况查询（calculator + mock_web_search）。
- **Writer**：写手，把前面的素材整理成最终报告（无工具，只用 LLM）。

执行流程：
    user → supervisor → (researcher | analyst | writer | FINISH) → supervisor → ... → END

学习目标：
- 看懂 LangGraph 多 agent 编排的最小骨架（state / nodes / conditional_edges）
- 看懂 supervisor 怎么用 structured output 做"路由决策"
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal, TypedDict

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.agents.tools import calculator, current_time, mock_web_search, retrieve_documents
from app.llm import make_llm

logger = logging.getLogger(__name__)


# ================== 状态 ==================


class TeamState(TypedDict):
    messages: Annotated[list, add_messages]
    # supervisor 上一次的决策；用于路由
    next: str
    # 防死循环
    iterations: int


MAX_ITERATIONS = 8


# ================== Supervisor ==================


class _Route(BaseModel):
    """Supervisor 的结构化输出。"""

    next: Literal["researcher", "analyst", "writer", "FINISH"] = Field(
        description="下一步派给谁；如果信息已足够、最终报告也已写好，则选 FINISH。"
    )
    reason: str = Field(description="一句话说明为什么这么选。")


SUPERVISOR_PROMPT = """你是一个研究小组的项目经理（supervisor）。
你的成员：
- researcher：研究员，擅长检索内部研报库，回答行业/公司/市场综述类问题
- analyst：分析师，擅长算数、当前时间、查公司近况（mock_web_search）
- writer：写手，把前面的素材整理成最终报告交给用户

规则：
1. 先 dispatch 给 researcher 或 analyst 收集素材；同一个角色可以连续被叫多次
2. 素材足够后，dispatch 给 writer 生成最终回复
3. writer 已经输出过一次最终回复后，必须返回 FINISH
4. 如果用户问题非常简单不用收集素材，直接 dispatch 给 writer

请基于完整对话历史做决策，输出 JSON。"""


def _supervisor_node(state: TeamState) -> dict:
    """Supervisor 决策。"""
    if state.get("iterations", 0) >= MAX_ITERATIONS:
        logger.warning("达到最大迭代次数，强制结束")
        return {"next": "FINISH", "iterations": state.get("iterations", 0) + 1}

    llm = make_llm(streaming=False, temperature=0.0)
    # method="function_calling" 兼容更广：豆包/部分国内模型不支持 OpenAI 新版 json_schema
    structured = llm.with_structured_output(_Route, method="function_calling")
    decision: _Route = structured.invoke(
        [SystemMessage(content=SUPERVISOR_PROMPT), *state["messages"]]
    )
    logger.info("Supervisor → %s（理由：%s）", decision.next, decision.reason)
    return {
        "next": decision.next,
        "iterations": state.get("iterations", 0) + 1,
        "messages": [AIMessage(content=f"🧭 调度员：→ {decision.next}（{decision.reason}）")],
    }


# ================== 三个专精 Agent ==================


def _build_researcher():
    return create_agent(
        model=make_llm(streaming=False),
        tools=[retrieve_documents],
        system_prompt=(
            "你是研究员。只用 retrieve_documents 工具，从文档库中检索与当前任务相关的片段，"
            "把关键信息原文摘录下来（带来源），不要自由发挥。"
        ),
        name="researcher",
    )


def _build_analyst():
    return create_agent(
        model=make_llm(streaming=False),
        tools=[calculator, current_time, mock_web_search],
        system_prompt=(
            "你是分析师。需要算数就用 calculator；需要时间就用 current_time；"
            "需要查公司近况就用 mock_web_search。给出简洁的数据/事实结论。"
        ),
        name="analyst",
    )


_researcher = None
_analyst = None


def _researcher_node(state: TeamState) -> dict:
    global _researcher
    if _researcher is None:
        _researcher = _build_researcher()
    # 只把最近一条 user 消息和最近的 supervisor 决策传过去，避免上下文过长
    last_user = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    task = last_user.content if last_user else "请检索相关研报。"
    res = _researcher.invoke({"messages": [HumanMessage(content=task)]})
    last_ai = next(
        (m for m in reversed(res["messages"]) if isinstance(m, AIMessage)), None
    )
    text = (last_ai.content if last_ai else "(无输出)") if last_ai else "(无输出)"
    if isinstance(text, list):
        text = "".join(b.get("text", "") for b in text if isinstance(b, dict))
    logger.info("Researcher 完成，输出长度 %d", len(str(text)))
    return {"messages": [AIMessage(content=f"📚 研究员产出：\n{text}")]}


def _analyst_node(state: TeamState) -> dict:
    global _analyst
    if _analyst is None:
        _analyst = _build_analyst()
    last_user = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    task = last_user.content if last_user else "请进行分析。"
    res = _analyst.invoke({"messages": [HumanMessage(content=task)]})
    last_ai = next(
        (m for m in reversed(res["messages"]) if isinstance(m, AIMessage)), None
    )
    text = last_ai.content if last_ai else "(无输出)"
    if isinstance(text, list):
        text = "".join(b.get("text", "") for b in text if isinstance(b, dict))
    logger.info("Analyst 完成，输出长度 %d", len(str(text)))
    return {"messages": [AIMessage(content=f"📊 分析师产出：\n{text}")]}


def _writer_node(state: TeamState) -> dict:
    """写手：基于全部历史综合回复用户。"""
    llm = make_llm(streaming=True)
    msgs = [
        SystemMessage(
            content=(
                "你是研究小组的写手。请综合前面研究员、分析师的产出，"
                "用清晰要点化的中文回复用户。引用关键数据时尽量带来源文件名。"
            )
        ),
        *state["messages"],
    ]
    final = llm.invoke(msgs)
    text = final.content if isinstance(final.content, str) else str(final.content)
    return {"messages": [AIMessage(content=f"📝 最终回复：\n{text}")]}


# ================== 路由 ==================


def _route_after_supervisor(state: TeamState) -> str:
    nxt = state.get("next", "FINISH")
    if nxt in ("researcher", "analyst", "writer"):
        return nxt
    return END


# ================== 组图 ==================


def build_multi_agent():
    logger.info("构建 supervisor 多 agent 系统")
    g = StateGraph(TeamState)
    g.add_node("supervisor", _supervisor_node)
    g.add_node("researcher", _researcher_node)
    g.add_node("analyst", _analyst_node)
    g.add_node("writer", _writer_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {"researcher": "researcher", "analyst": "analyst", "writer": "writer", END: END},
    )
    # 每个角色干完都回到 supervisor 决策下一步
    g.add_edge("researcher", "supervisor")
    g.add_edge("analyst", "supervisor")
    g.add_edge("writer", "supervisor")

    return g.compile()

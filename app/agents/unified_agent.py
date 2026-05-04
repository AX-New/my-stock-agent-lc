"""
unified_agent.py — 综合性 agent（一锅端）
==============================================

把前 4 个 agent 的能力**合到一个 LLM 上**：
- 全部工具（calculator / current_time / mock_web_search / retrieve_documents）
- 会话记忆（checkpointer，按 thread_id 隔离）
- 由 system prompt 引导自主决策（什么时候检索、什么时候算数、什么时候直接答）

为什么单独建一个：
- 前 4 个 agent 是为了"分别教学每种能力"；本 agent 是"日常实际可用"形态
- 也是 LangChain 项目里最常见的生产形态（一个 agent + 多工具 + memory）

它和 `rag_agent` 的区别：
- rag_agent 只多了 retriever 工具
- unified_agent 多了"复杂问题先在心里规划"的引导 prompt + 全套工具
"""

from __future__ import annotations

import logging

from langchain.agents import create_agent

from app.agents.memory import get_checkpointer
from app.agents.tools import ALL_TOOLS
from app.llm import make_llm

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是综合助手"小助"。可用能力：
- `calculator`：算数、数学表达式
- `current_time`：拿当前时间 / 星期
- `mock_web_search`：查公司近况（比亚迪/英伟达/宁德时代/恒瑞医药/中际旭创）
- `retrieve_documents`：检索内部研报库（行业/市场/公司基本面综述）

行事原则：
1. **简单问题直接答**（聊天、定义、纯文本任务），不要为调工具而调工具
2. **行业/市场/研报相关问题**，先调 `retrieve_documents`，引用时带来源文件名
3. **数字计算**用 `calculator`；当前时间用 `current_time`
4. **复杂多步问题**，先在心里把步骤排好，再依次取数；步骤之间产生的新信息会进入下一步
5. 一次回答内**同一个工具可以多次调用**（如要查多家公司就连续调几次 mock_web_search）
6. 信息不足明确说"资料不够"，禁止编造数字
7. 简体中文回答，要点先行
"""


def build_unified_agent():
    """
    构造综合 agent：全工具 + memory + 自主决策 prompt。
    流式接口与其他 agent 一致：astream_events(version="v2") + thread_id config。
    """
    logger.info("构建 unified_agent，工具数=%d", len(ALL_TOOLS))
    return create_agent(
        model=make_llm(streaming=True),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=get_checkpointer(),
        name="unified_agent",
    )

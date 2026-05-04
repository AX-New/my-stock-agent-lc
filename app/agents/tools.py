"""
tools.py — Agent 可调用的工具集
====================================

LangChain 工具的两种写法：
1. `@tool` 装饰器（推荐，最简洁）
2. 继承 BaseTool（适合复杂场景，需要 sync/async 两套实现）

本项目用 @tool。每个工具都附详细 docstring，agent 选工具时会读这段。

工具列表：
- `calculator`           — 算数表达式求值（基于 AST 安全实现，不用 eval）
- `current_time`         — 当前时间（含 weekday、ISO 字符串）
- `mock_web_search`      — 假装的 web 搜索（返回固定示例，避免引外部 API）
- `retrieve_documents`   — RAG 检索向量库（在 rag_agent 里挂上）
"""

from __future__ import annotations

import ast
import datetime as dt
import logging
import math
import operator as op_

from langchain_core.tools import tool

from app.rag.vectorstore import get_retriever

logger = logging.getLogger(__name__)

# ============== 1. 计算器（AST 安全求值）==============

# 二元运算符白名单
_BINOPS = {
    ast.Add: op_.add,
    ast.Sub: op_.sub,
    ast.Mult: op_.mul,
    ast.Div: op_.truediv,
    ast.FloorDiv: op_.floordiv,
    ast.Mod: op_.mod,
    ast.Pow: op_.pow,
}

# 一元运算符白名单
_UNARYOPS = {ast.UAdd: op_.pos, ast.USub: op_.neg}

# 函数 / 常量白名单
_NAMES = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "log": math.log,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}


def _eval_ast(node: ast.AST) -> float | int:
    """递归解释 AST 节点，仅支持白名单运算和函数。"""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"不允许的常量: {node.value!r}")
    if isinstance(node, ast.BinOp):
        opf = _BINOPS.get(type(node.op))
        if opf is None:
            raise ValueError(f"不允许的二元运算符: {type(node.op).__name__}")
        return opf(_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp):
        opf = _UNARYOPS.get(type(node.op))
        if opf is None:
            raise ValueError(f"不允许的一元运算符: {type(node.op).__name__}")
        return opf(_eval_ast(node.operand))
    if isinstance(node, ast.Name):
        if node.id not in _NAMES:
            raise ValueError(f"不允许的标识符: {node.id}")
        val = _NAMES[node.id]
        if callable(val):
            raise ValueError(f"{node.id} 是函数，需要带括号调用")
        return val
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _NAMES:
            raise ValueError("不允许的函数调用")
        fn = _NAMES[node.func.id]
        if not callable(fn):
            raise ValueError(f"{node.func.id} 不是可调用对象")
        args = [_eval_ast(a) for a in node.args]
        return fn(*args)
    raise ValueError(f"不允许的语法: {type(node).__name__}")


@tool
def calculator(expression: str) -> str:
    """计算一个算术/数学表达式并返回结果。
    支持 + - * / ** % // 以及 abs/round/min/max/sum/pow/sqrt/log/exp/pi/e。
    示例：'2 * (3 + 4)'、'sqrt(16) + log(e)'。
    输入必须是合法的数学表达式。
    """
    logger.info("calculator 调用: %s", expression)
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_ast(tree)
    except Exception as e:  # noqa: BLE001
        return f"计算失败：{e}"
    return str(result)


# ============== 2. 当前时间 ==============


@tool
def current_time() -> str:
    """返回服务器当前时间。包含 ISO 格式、星期、时间戳。
    无需参数。当用户问"现在几点 / 今天周几 / 当前时间"时调用。
    """
    now = dt.datetime.now()
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
    res = f"{now.isoformat(timespec='seconds')}（{weekday}），timestamp={int(now.timestamp())}"
    logger.info("current_time 调用 -> %s", res)
    return res


# ============== 3. 假装的 web 搜索 ==============

_MOCK_SEARCH_DB = {
    "比亚迪": "比亚迪（002594）：2026 Q1 销量 98.4 万辆，海外占比 14%，DM-i 5.0 平台爬产顺利。",
    "英伟达": "英伟达（NVDA）：B200 季度出货 90 万片，HBM4 产品线 2026Q3 准备就绪。",
    "宁德时代": "宁德时代（300750）：神行 Pro 电池 4 月量产，能量密度 320Wh/kg，欧洲订单环比 +28%。",
    "恒瑞医药": "恒瑞医药（600276）：Q1 海外 license-out 收入 4 亿美元，PD-L1 数据 ESMO 公布。",
    "中际旭创": "中际旭创（300308）：800G 光模块满产，1.6T 已小批量出货，Q3 客户验证完成。",
}


@tool
def mock_web_search(keyword: str) -> str:
    """模拟 web 搜索（学习项目用，不调真实搜索 API）。
    给定一个公司/标的关键词，返回最近行业/公司动态简报。
    支持的关键词包括：比亚迪、英伟达、宁德时代、恒瑞医药、中际旭创。
    """
    logger.info("mock_web_search 调用: %s", keyword)
    for key, blurb in _MOCK_SEARCH_DB.items():
        if key in keyword:
            return blurb
    return f"未命中关键词「{keyword}」。当前样例库仅包含：{list(_MOCK_SEARCH_DB.keys())}"


# ============== 4. RAG 检索 ==============


@tool
def retrieve_documents(query: str) -> str:
    """从内部研报/行业综述向量库中检索与 query 最相关的文档片段。
    返回 top-4 片段及其来源文件。当问题涉及行业研报、市场综述、行业数据时使用。
    输入示例：'半导体 2026 Q1 销售情况'、'A 股 4 月策略'、'医药板块 Q1 表现'。
    """
    logger.info("retrieve_documents 调用: %s", query)
    retriever = get_retriever(top_k=4)
    docs = retriever.invoke(query)
    if not docs:
        return "向量库未返回任何片段。可能 ingest 还没跑过，或 query 与文档相关度过低。"
    blocks: list[str] = []
    for i, d in enumerate(docs, 1):
        src = d.metadata.get("source", "unknown")
        snippet = d.page_content.strip().replace("\n", " ")
        blocks.append(f"[片段{i} | 来源: {src}]\n{snippet}")
    return "\n\n".join(blocks)


# ============== 工具集合（默认/含RAG）==============

# 不含 RAG 的基础工具（single_agent 用）
BASIC_TOOLS = [calculator, current_time, mock_web_search]

# 含 RAG 的全工具集（rag_agent 用）
ALL_TOOLS = BASIC_TOOLS + [retrieve_documents]

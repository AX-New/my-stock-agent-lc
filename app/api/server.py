"""
server.py — FastAPI 入口
=============================

路由：
- GET  /                         → 重定向到 /static/index.html
- GET  /static/...               → 静态前端
- POST /api/chat                 → SSE 流式接口（前端用 fetch + ReadableStream 消费）
- POST /api/ingest               → 触发 RAG 文档摄入
- GET  /api/health               → 健康检查

启动：
    python -m app.api.server
    # 然后浏览器打开 http://localhost:8004/
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.agents.multi_agent import build_multi_agent
from app.agents.planner import build_planner_agent
from app.agents.rag_agent import build_rag_agent
from app.agents.single_agent import build_single_agent
from app.api.schemas import ChatRequest, IngestResponse
from app.api.sse import stream_agent_events
from app.config import PROJECT_ROOT, SERVER_PORT, setup_logging
from app.rag.ingest import ingest

logger = logging.getLogger(__name__)


# ============== Agent 单例 ==============


@lru_cache(maxsize=1)
def _agents() -> dict:
    """启动时构建所有 agent，缓存复用。"""
    logger.info("初始化所有 agent 实例...")
    a = {
        "single": build_single_agent(),
        "rag": build_rag_agent(),
        "plan": build_planner_agent(),
        "multi": build_multi_agent(),
    }
    logger.info("agent 实例构建完成: %s", list(a.keys()))
    return a


# ============== FastAPI 应用 ==============


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """启动钩子：预热 agent（首次构建会下载 embedding，避免请求时阻塞）。"""
    setup_logging()
    logger.info("=== my-stock-agent-lc 启动 ===")
    _agents()
    yield
    logger.info("=== my-stock-agent-lc 关闭 ===")


app = FastAPI(
    title="my-stock-agent-lc",
    description="LangChain + 传统 agent 学习项目（含 RAG / SSE / 多 agent）",
    version="0.1.0",
    lifespan=lifespan,
)

# 静态前端
WEB_DIR = PROJECT_ROOT / "app" / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


# ============== 路由 ==============


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": list(_agents().keys())}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    SSE 流式聊天。前端用 fetch + ReadableStream 消费 `text/event-stream`。
    """
    agents = _agents()
    if req.agent not in agents:
        raise HTTPException(400, f"不支持的 agent: {req.agent}")
    agent = agents[req.agent]

    inputs = {"messages": [{"role": "user", "content": req.message}]}
    # planner / multi 是非 checkpointer 的图，传 thread_id 会报错；
    # single / rag 是带 checkpointer 的，要传 thread_id 才能记忆
    config: dict | None = None
    if req.agent in ("single", "rag"):
        config = {"configurable": {"thread_id": req.thread_id}}

    logger.info("收到 chat 请求 agent=%s thread=%s", req.agent, req.thread_id)
    return StreamingResponse(
        stream_agent_events(agent, inputs, config=config),
        media_type="text/event-stream",
        headers={
            # nginx / proxy 友好
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def trigger_ingest():
    """触发 RAG 文档摄入；返回摘要。"""
    summary = ingest()
    return IngestResponse(**summary)


# ============== 入口 ==============


def main() -> None:
    import uvicorn

    setup_logging()
    logger.info("启动 uvicorn，端口 %d", SERVER_PORT)
    uvicorn.run(
        "app.api.server:app",
        host="0.0.0.0",
        port=SERVER_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

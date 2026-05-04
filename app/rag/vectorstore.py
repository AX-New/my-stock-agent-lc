"""
vectorstore.py — Chroma 向量库封装
======================================

对外暴露两个函数：
- get_vectorstore()：拿到一个绑定了 embedding 的 Chroma 实例（持久化目录由 config 指定）
- get_retriever()：直接拿到一个可以丢进 agent 的 retriever（默认 top_k=4）

Chroma 选型理由（学习项目场景）：
- 纯 Python、零外部服务，启动即用
- 文件持久化（chroma_db/），重启不丢
- LangChain 官方一等公民支持

不在这里做的事：
- 文档加载、切分、入库（在 ingest.py 里做）
- 重排序 / hybrid search（学习项目先不上）
"""

from __future__ import annotations

import logging

from langchain_chroma import Chroma

from app.config import CHROMA_COLLECTION, CHROMA_PERSIST_DIR
from app.rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)


def get_vectorstore() -> Chroma:
    """
    返回一个 Chroma 实例（同名 collection，绑定 embedding 与持久化目录）。
    多次调用返回的对象不同，但底层指向同一份磁盘数据。
    """
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(
        "打开 Chroma collection=%s dir=%s", CHROMA_COLLECTION, CHROMA_PERSIST_DIR
    )
    return Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_PERSIST_DIR),
    )


def get_retriever(top_k: int = 4):
    """
    返回 LangChain BaseRetriever，可直接当 tool 用，也可以塞进 chain。

    参数：
        top_k: 检索返回的最相似文档数。学习项目默认 4，前端可调。
    """
    return get_vectorstore().as_retriever(search_kwargs={"k": top_k})

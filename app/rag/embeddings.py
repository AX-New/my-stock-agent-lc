"""
embeddings.py — 本地 sentence-transformers embedding
=======================================================

为什么不用 OpenAI / Anthropic embedding：
- Anthropic 没提供 embedding API
- 走外部 embedding 要额外密钥/计费/代理，学习项目尽量降门槛
- 本地中文 embedding 已足够覆盖学习场景

默认模型：BAAI/bge-small-zh-v1.5，约 100MB。
首次使用 sentence-transformers 会自动下载到本机 HF 缓存。
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    构造（并缓存）embedding 实例。
    第一次调用会触发模型下载，几百 MB 网络流量；后续走本地缓存。
    """
    logger.info("加载 embedding 模型: %s", EMBEDDING_MODEL)
    emb = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        # bge 系列推荐 normalize 后做 cosine 相似度
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info("embedding 模型加载完成")
    return emb

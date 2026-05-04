"""
ingest.py — 文档摄入脚本
==========================

扫描 DOCS_DIR 下所有 .md / .txt，切分后写入 Chroma。
重复跑会**先清空 collection 再灌入**，保证幂等（学习项目这样最简单，不用做去重逻辑）。

运行：
    python -m app.rag.ingest

日志输出每个文件的切片数、整体耗时、向量库最终条目数。
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHROMA_COLLECTION, DOCS_DIR, setup_logging
from app.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

# 切分参数：中文研报段落较短，500 token 够覆盖一个小节
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
SUPPORTED_SUFFIXES = {".md", ".txt"}


def _load_one(path: Path) -> list[Document]:
    """加载单个文档，metadata 里带上文件名。"""
    loader = TextLoader(str(path), encoding="utf-8")
    docs = loader.load()
    for d in docs:
        d.metadata["source"] = path.name
        d.metadata["full_path"] = str(path)
    return docs


def _scan_files(docs_dir: Path) -> list[Path]:
    """扫描目录，返回支持后缀的文件列表（按文件名排序，结果稳定）。"""
    if not docs_dir.exists():
        raise FileNotFoundError(f"文档目录不存在: {docs_dir}")
    files = sorted(
        p for p in docs_dir.iterdir() if p.is_file() and p.suffix in SUPPORTED_SUFFIXES
    )
    return files


def ingest(docs_dir: Path | None = None) -> dict:
    """
    主入口。
    1. 扫描文档目录
    2. 切分
    3. 清空旧 collection
    4. 写入新数据
    返回一个 dict 摘要，便于上层（脚本/接口）展示。
    """
    docs_dir = docs_dir or DOCS_DIR
    started = time.time()
    logger.info("=== ingest 开始 ===")
    logger.info("文档目录: %s", docs_dir)

    files = _scan_files(docs_dir)
    logger.info("发现 %d 个待处理文件", len(files))
    if not files:
        logger.warning("目录为空，退出")
        return {"files": 0, "chunks": 0, "elapsed": 0.0}

    # 1) 加载
    raw_docs: list[Document] = []
    for f in files:
        loaded = _load_one(f)
        raw_docs.extend(loaded)
        logger.info("  - %s 字符数=%d", f.name, sum(len(d.page_content) for d in loaded))

    # 2) 切分
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
    )
    chunks = splitter.split_documents(raw_docs)
    logger.info("切分完成：%d 个 chunk（chunk_size=%d overlap=%d）",
                len(chunks), CHUNK_SIZE, CHUNK_OVERLAP)

    # 3) 清空旧数据 + 4) 重新灌入
    vs = get_vectorstore()
    try:
        vs.delete_collection()
        logger.info("已清空旧 collection: %s", CHROMA_COLLECTION)
    except Exception as e:  # noqa: BLE001
        # 第一次跑没旧 collection，会抛异常；学习项目直接吞掉
        logger.debug("清空 collection 失败（首次运行属正常）: %s", e)

    vs = get_vectorstore()  # 重新拿一个
    vs.add_documents(chunks)
    logger.info("写入完成。collection=%s，最终条目数=%d",
                CHROMA_COLLECTION, vs._collection.count())

    elapsed = time.time() - started
    logger.info("=== ingest 完成，耗时 %.2fs ===", elapsed)
    return {
        "files": len(files),
        "chunks": len(chunks),
        "elapsed": round(elapsed, 2),
    }


if __name__ == "__main__":
    setup_logging()
    summary = ingest()
    print(summary)

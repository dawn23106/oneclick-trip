"""向量存储模块（Vector Store）

一键游知识库的向量化存储与检索层，基于 ChromaDB 构建：

- BgeSmallZhV15EmbeddingFunction：BGE-small-zh-v1.5 ONNX 推理，CPU 友好
- ChromaTravelKnowledgeBase：多 collection 管理的 Chroma 适配层
- HashEmbeddingFunction：离线确定性 hash embedding，仅用于开发环境
- KnowledgeDocument / KnowledgeHit：入库文档与检索命中的数据模型

典型用法：
    kb = ChromaTravelKnowledgeBase(
        persist_directory, embedding_function=bge_ef
    )
    hits = kb.hybrid_search("poi", "成都景点", city="成都", limit=5)
"""

from app.vectorstore.bge_onnx import BgeSmallZhV15EmbeddingFunction
from app.vectorstore.chroma import (
    ChromaTravelKnowledgeBase,
    HashEmbeddingFunction,
    KnowledgeDocument,
    KnowledgeHit,
)

__all__ = [
    "BgeSmallZhV15EmbeddingFunction",
    "ChromaTravelKnowledgeBase",
    "HashEmbeddingFunction",
    "KnowledgeDocument",
    "KnowledgeHit",
]

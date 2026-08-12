"""ChromaDB 向量存储适配层。

提供一键游知识库的完整向量索引能力：

数据模型
--------
- KnowledgeDocument  — 入库文档（文本 + 城市/类别/来源等元数据）
- KnowledgeHit       — 检索命中结果（含语义分、词汇分、重排序分）

嵌入函数
--------
- HashEmbeddingFunction — 确定性 hash 嵌入，离线开发用（不依赖模型下载）
- BgeSmallZhV15EmbeddingFunction — BGE ONNX 嵌入，生产环境用（见 bge_onnx.py）

核心类
------
- ChromaTravelKnowledgeBase — 多 collection 管理的 ChromaDB 适配器
  支持：
  - 纯向量检索 (search)
  - 混合检索 (hybrid_search = 向量 + BM25 + 质量重排)
  - 城市过滤 (city where 子句)
  - 按知识库分类（poi / food / hotel / transport / ticket / guide）
  - 文档 upsert / 按来源删除 / 按记录删除

混合检索权重公式（hybrid_search）:
    rerank = 0.42 × 语义相似度
           + 0.33 × BM25 词汇匹配
           + 0.12 × 质量分
           + 0.08 × 来源权威度
           + 0.05 × 精确短语命中
           + 语义增强（语义 ≥ 0.7 时 +0.08）
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import chromadb
import jieba
import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from chromadb.config import Settings as ChromaSettings
from pydantic import BaseModel, Field
from rank_bm25 import BM25Plus


# ChromaDB 自身的日志较啰嗦，jieba 分词也有大量调试输出
# 在应用层将其静默，避免污染业务日志
jieba.setLogLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


class KnowledgeDocument(BaseModel):
    """入库知识文档。

    每个文档对应知识库中的一个分块（chunk），由知识管线清洗/切分后生成。

    Attributes:
        document_id: 文档唯一标识（如 "chengdu-panda-base-chunk-0"）
        text: 文档正文（已清洗、切分后的纯文本）
        knowledge_base: 所属知识库（poi / food / hotel / transport / ticket / guide）
        city: 关联城市（用于城市过滤检索）
        category: 内容分类（景点 / 美食 / 住宿 / 交通 / 门票 / 攻略）
        source: 数据来源标识（如 "admin-collect-20260731-001"）
        updated_at: 最后更新时间
        metadata: 扩展元数据（source_url, source_tier, quality_score, record_id 等）
    """
    document_id: str
    text: str = Field(min_length=1)
    knowledge_base: str
    city: str
    category: str
    source: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class KnowledgeHit(BaseModel):
    """检索命中的知识文档。

    包含原始向量距离及混合检索的逐项评分。

    Attributes:
        document_id: 命中文档 ID
        text: 文档正文
        distance: 原始向量距离（余弦距离，越小越相似）
        metadata: 文档元数据
        semantic_score: 语义相似度（0~1，越大越好）
        lexical_score: BM25 词汇匹配得分（0~1）
        rerank_score: 最终重排序得分（0~1，各维度加权求和）
        retrieval_mode: 检索模式标识（"vector" 或 "hybrid_vector_bm25_rerank"）
    """
    document_id: str
    text: str
    distance: float
    metadata: dict[str, Any]
    semantic_score: float = 0
    lexical_score: float = 0
    rerank_score: float = 0
    retrieval_mode: str = "vector"


# ---------------------------------------------------------------------------
# Hash 嵌入函数（离线开发用）
# ---------------------------------------------------------------------------


class HashEmbeddingFunction(EmbeddingFunction[Documents]):
    """离线确定性 hash 嵌入函数。

    用 BLAKE2b 哈希将文本映射到固定维度向量，不加载任何模型。
    仅用于本地开发和 CI 环境，避免下载数百 MB 的 BGE 模型文件。

    注意：
    - Hash 嵌入不具备语义能力，不同文本的向量相似度近似随机
    - 不能与 BGE 编码的 collection 混用（ChromaDB 会检查 embedding_function name）
    - 如需切换嵌入函数，必须先清空 collection 并重新入库

    工作原理：
    1. 对文本做字符级 + 二元组分词
    2. 每个 token 用 BLAKE2b 哈希映射到向量维度上的一个位置
    3. 根据哈希值符号位决定该位置的值为 +1 或 -1（随机投影）
    4. L2 归一化使向量落在单位球面上
    """

    def __init__(self, dimension: int = 384) -> None:
        """初始化 hash 嵌入函数。

        Args:
            dimension: 输出向量维度，默认 384（与 BGE 512 不同，避免混用）
        """
        self.dimension = dimension

    def __call__(self, input: Documents) -> Embeddings:
        """ChromaDB 嵌入接口：对一批文档生成向量。"""
        return [self._embed(document) for document in input]

    def embed_query(self, query: str) -> list[float]:
        """对单条查询生成向量（与文档嵌入使用相同逻辑）。"""
        return self._embed(query)

    @staticmethod
    def name() -> str:
        """返回嵌入函数唯一标识名。

        ChromaDB 在 get_or_create_collection 时会比对 collection 元数据中的
        embedding_model 字段与此名称，不匹配则抛出 ValueError 防止向量空间混用。
        """
        return "oneclick_hash_embedding"

    def get_config(self) -> dict[str, Any]:
        """返回可序列化的配置字典。"""
        return {"dimension": self.dimension}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "HashEmbeddingFunction":
        """从配置字典重建实例。"""
        return HashEmbeddingFunction(dimension=int(config.get("dimension", 384)))

    def _embed(self, text: str) -> list[float]:
        """核心 hash 嵌入算法 — 随机投影（Random Projection）。

        步骤：
        1. 文本归一化（去空格、小写）
        2. 拆分为字符 + 二元组 tokens
        3. 每个 token 用 BLAKE2b 哈希 → 向量维度索引 + 符号位
        4. 在对应维度上累加 ±1（形成稀疏随机投影）
        5. L2 归一化

        这种方法的理论依据是 Johnson-Lindenstrauss 引理：
        随机投影可以近似保留高维空间中的距离关系。
        """
        # Step 1: 文本归一化
        normalized = re.sub(r"\s+", "", text.lower())

        # Step 2: 分词 — 单个字符 + 相邻二元组
        tokens = list(normalized)
        tokens.extend(
            normalized[index : index + 2]
            for index in range(max(len(normalized) - 1, 0))
        )

        # Step 3-4: 哈希 → 随机投影
        vector = [0.0] * self.dimension
        for token in tokens or [normalized]:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            # 前 4 字节 → 向量维度索引
            index = int.from_bytes(digest[:4], "big") % self.dimension
            # 第 5 字节的最低位 → 符号（±1）
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign

        # Step 5: L2 归一化
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


# ---------------------------------------------------------------------------
# ChromaDB 知识库适配器
# ---------------------------------------------------------------------------


class ChromaTravelKnowledgeBase:
    """基于 ChromaDB 的旅行知识库向量存储。

    架构设计：
    - 每个逻辑知识库（poi / food / hotel / ...）对应一个 ChromaDB collection
    - Collection 命名规则：{prefix}_{knowledge_base}，如 travel_knowledge_bge_v15_poi
    - 支持本地 PersistentClient（开发）和 HttpClient（远程 Chroma 服务）
    - 元数据中记录 embedding_model 名称和维度，防止混用不同嵌入函数

    检索模式：
    - search()          → 纯向量语义检索（ChromaDB query）
    - hybrid_search()   → 向量 + BM25 词汇 + 质量重排（推荐生产使用）

    典型用法：
        import chromadb
        from app.vectorstore.chroma import ChromaTravelKnowledgeBase

        kb = ChromaTravelKnowledgeBase(
            Path("./data/chroma"),
            collection_prefix="travel_knowledge_bge_v15",
            embedding_function=bge_ef,
        )

        # 入库
        kb.upsert([KnowledgeDocument(text="...", knowledge_base="poi", ...)])

        # 混合检索
        hits = kb.hybrid_search("poi", "成都大熊猫", city="成都", limit=5)
        for hit in hits:
            print(f"[{hit.rerank_score:.3f}] {hit.text[:60]}")
    """

    def __init__(
        self,
        persist_directory: Path,
        *,
        collection_prefix: str = "travel_knowledge",
        embedding_function: EmbeddingFunction[Documents] | None = None,
        server_url: str | None = None,
    ) -> None:
        """初始化 ChromaDB 客户端和嵌入函数。

        Args:
            persist_directory: 本地持久化目录（仅 PersistentClient 使用）
            collection_prefix: collection 命名前缀，如 "travel_knowledge_bge_v15"
            embedding_function: 嵌入函数实例，为 None 时默认使用 HashEmbeddingFunction
            server_url: 远程 Chroma 服务地址，如 "http://chroma:8000"
                        为 None 时使用本地 PersistentClient
        """
        if server_url:
            # 远程模式：连接独立的 Chroma 服务（生产/测试环境）
            parsed = urlparse(server_url)
            if not parsed.hostname:
                raise ValueError("CHROMA_SERVER_URL must include a hostname")
            self._client = chromadb.HttpClient(
                host=parsed.hostname,
                port=parsed.port or (443 if parsed.scheme == "https" else 8000),
                ssl=parsed.scheme == "https",
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            # 本地模式：嵌入式 ChromaDB，数据直接存磁盘
            persist_directory.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(persist_directory),
                settings=ChromaSettings(anonymized_telemetry=False),
            )

        self._prefix = self._normalize_name(collection_prefix)
        # 未指定嵌入函数时默认使用 Hash（离线开发模式）
        # 生产环境应从 main.py 传入 BgeSmallZhV15EmbeddingFunction
        self._embedding = embedding_function or HashEmbeddingFunction()

    # -----------------------------------------------------------------------
    # 写入操作
    # -----------------------------------------------------------------------

    def upsert(self, documents: list[KnowledgeDocument]) -> None:
        """批量插入或更新文档。

        按 knowledge_base 分组后分别写入对应 collection。
        重复 document_id 会覆盖旧版本（upsert 语义）。

        元数据写入规则（见 _metadata）：
        - city, category, source 三段必有字段
        - embedding_model + embedding_version + embedding_dimension 用于兼容性校验
        - document.metadata 中的扩展字段（source_url, quality_score 等）一并写入
        """
        grouped: dict[str, list[KnowledgeDocument]] = {}
        for document in documents:
            grouped.setdefault(document.knowledge_base, []).append(document)

        for knowledge_base, items in grouped.items():
            collection = self._collection(knowledge_base)
            collection.upsert(
                ids=[item.document_id for item in items],
                documents=[item.text for item in items],
                metadatas=[self._metadata(item) for item in items],
            )

    def seed_demo_documents(self) -> None:
        """写入演示种子数据（仅当 poi 库为空时）。

        包含：
        - 成都大熊猫繁育研究基地（景点）
        - 宽窄巷子（景点）
        - 成都代表美食（美食）

        用于首次启动时的功能演示，不覆盖已有数据。
        """
        if self.count("poi") > 0:
            return
        self.upsert(
            [
                KnowledgeDocument(
                    document_id="chengdu-panda-base",
                    text="成都大熊猫繁育研究基地适合上午参观，建议预留三到四小时。",
                    knowledge_base="poi",
                    city="成都",
                    category="景点",
                    source="demo-seed",
                ),
                KnowledgeDocument(
                    document_id="chengdu-kuanzhai",
                    text="宽窄巷子位于成都中心城区，适合城市漫步和体验川西街巷文化。",
                    knowledge_base="poi",
                    city="成都",
                    category="景点",
                    source="demo-seed",
                ),
                KnowledgeDocument(
                    document_id="chengdu-food",
                    text="成都代表美食包括火锅、串串香、担担面和钟水饺。",
                    knowledge_base="food",
                    city="成都",
                    category="美食",
                    source="demo-seed",
                ),
            ]
        )

    # -----------------------------------------------------------------------
    # 删除操作
    # -----------------------------------------------------------------------

    def clear(self, knowledge_base: str) -> int:
        """清空指定知识库的全部文档，返回删除数量。"""
        collection = self._collection(knowledge_base)
        document_ids = list(collection.get(include=[]).get("ids") or [])
        if document_ids:
            collection.delete(ids=document_ids)
        return len(document_ids)

    def remove_documents_by_source(self, source: str) -> None:
        """按来源标识删除所有知识库中的相关文档。

        遍历全部 6 个知识库，按 metadata.source 匹配并批量删除。
        用于知识管线中"驳回批次"或"替换来源数据"的场景。
        """
        for knowledge_base in ("poi", "food", "hotel", "transport", "ticket", "guide"):
            collection = self._collection(knowledge_base)
            matching = collection.get(where={"source": source}, include=[])
            document_ids = list(matching.get("ids") or [])
            if document_ids:
                collection.delete(ids=document_ids)

    def remove_documents_by_record(self, knowledge_base: str, record_id: str) -> int:
        """按审核记录 ID 删除指定知识库中的文档。

        用于管理后台"删除单条已通过记录"时同步清除向量索引。
        """
        collection = self._collection(knowledge_base)
        matching = collection.get(where={"record_id": record_id}, include=[])
        document_ids = list(matching.get("ids") or [])
        if document_ids:
            collection.delete(ids=document_ids)
        return len(document_ids)

    # -----------------------------------------------------------------------
    # 纯向量检索
    # -----------------------------------------------------------------------

    def search(
        self,
        knowledge_base: str,
        query: str,
        *,
        city: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeHit]:
        """纯向量语义检索。

        使用 ChromaDB 的 query 接口，基于余弦相似度返回最相似的文档。

        Args:
            knowledge_base: 目标知识库名（如 "poi"）
            query: 查询文本
            city: 可选城市过滤（匹配 metadata.city 字段）
            limit: 返回数量上限

        Returns:
            按向量距离升序排列的 KnowledgeHit 列表
        """
        collection = self._collection(knowledge_base)
        # ChromaDB where 子句：精确匹配 metadata 中的字段
        where = {"city": city} if city else None

        result = collection.query(
            query_embeddings=[self._query_embedding(query)],
            n_results=max(limit, 1),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # ChromaDB 返回格式：{ids: [[id,...]], documents: [[doc,...]], ...}
        # 外层列表对应 query_embeddings 的每条查询，这里只有一条
        ids = result.get("ids", [[]])[0]
        texts = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        return [
            KnowledgeHit(
                document_id=document_id,
                text=text or "",
                distance=float(distance),
                metadata=metadata or {},
            )
            for document_id, text, metadata, distance in zip(
                ids, texts, metadatas, distances, strict=True
            )
        ]

    # -----------------------------------------------------------------------
    # 混合检索（向量 + BM25 + 质量重排）
    # -----------------------------------------------------------------------

    def hybrid_search(
        self,
        knowledge_base: str,
        query: str,
        *,
        city: str | None = None,
        limit: int = 5,
        candidate_multiplier: int = 4,
    ) -> list[KnowledgeHit]:
        """混合检索：向量语义 + BM25 词汇 + 元数据质量重排。

        这是生产环境推荐的检索方式，结合了三种信号：
        1. 向量语义相似度 — 捕捉同义词和语义关联
        2. BM25 词汇匹配 — 精确关键词命中
        3. 元数据质量分 + 来源权威度 — 优先高质量/官方来源
        4. 精确短语命中加分 — 查询内容完整出现在文档中

        流程：
        1. 用 ChromaDB 取 candidate_count 条向量候选
        2. 用 BM25Plus 对全库文档打分，取 candidate_count 条词汇候选
        3. 合并去重，对每个候选计算加权重排分
        4. 按 rerank_score 降序返回 top-N

        权重设计说明：
        - 语义 42% + 词汇 33% = 75% 内容相关性（主体）
        - 质量 12% + 权威 8% = 20% 可信度（辅助筛选）
        - 短语命中 5%（精确匹配加分，避免语义漂移）
        - 高语义项额外加 0.08（语义 guard，拉开高质量结果差距）

        Args:
            knowledge_base: 目标知识库名
            query: 查询文本
            city: 可选城市过滤
            limit: 最终返回数量
            candidate_multiplier: 候选池倍数（默认 4x，即取 limit*4 条候选）

        Returns:
            按 rerank_score 降序排列的 KnowledgeHit 列表
        """
        collection = self._collection(knowledge_base)
        where = {"city": city} if city else None

        # ==================================================================
        # 第一阶段：获取全量语料（用于 BM25 索引）
        # ==================================================================
        corpus = collection.get(
            where=where,
            include=["documents", "metadatas"],
        )
        corpus_ids = list(corpus.get("ids") or [])
        if not corpus_ids:
            return []  # 库为空，直接返回

        corpus_texts = [text or "" for text in (corpus.get("documents") or [])]
        corpus_metadatas = [metadata or {} for metadata in (corpus.get("metadatas") or [])]

        # 候选池大小：取 limit * multiplier，但不超过库总大小
        candidate_count = min(
            len(corpus_ids),
            max(limit, limit * max(candidate_multiplier, 1)),
        )

        # ==================================================================
        # 第二阶段：向量语义检索
        # ==================================================================
        vector_result = collection.query(
            query_embeddings=[self._query_embedding(query)],
            n_results=candidate_count,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        vector_ids = list(vector_result.get("ids", [[]])[0])
        vector_distances = [
            float(value) for value in vector_result.get("distances", [[]])[0]
        ]

        # 余弦距离 → 相似度：1 - distance，截断到 [0, 1]
        semantic_scores = {
            document_id: max(0.0, min(1.0, 1.0 - distance))
            for document_id, distance in zip(vector_ids, vector_distances, strict=True)
        }
        distance_by_id = dict(zip(vector_ids, vector_distances, strict=True))

        # ==================================================================
        # 第三阶段：BM25 词汇检索
        # ==================================================================
        # 用 jieba 对全库文档分词 → 构建 BM25Plus 索引
        tokenized_corpus = [_tokenize(text) for text in corpus_texts]
        query_tokens = _tokenize(query)

        # 查询或语料为空时 BM25 全返回 0
        raw_lexical_scores = (
            BM25Plus(tokenized_corpus).get_scores(query_tokens)
            if query_tokens and any(tokenized_corpus)
            else [0.0] * len(corpus_ids)
        )
        # Min-Max 归一化到 [0, 1]
        normalized_lexical_scores = _normalize_scores(raw_lexical_scores)
        lexical_scores = dict(zip(corpus_ids, normalized_lexical_scores, strict=True))

        # 取 BM25 得分最高的 candidate_count 条
        lexical_ids = [
            corpus_ids[index]
            for index in sorted(
                range(len(corpus_ids)),
                key=lambda index: raw_lexical_scores[index],
                reverse=True,
            )[:candidate_count]
        ]

        # ==================================================================
        # 第四阶段：合并候选 + 多维重排序
        # ==================================================================
        text_by_id = dict(zip(corpus_ids, corpus_texts, strict=True))
        metadata_by_id = dict(zip(corpus_ids, corpus_metadatas, strict=True))

        # 合并向量和 BM25 候选，保持原始顺序并去重
        candidate_ids = list(dict.fromkeys([*vector_ids, *lexical_ids]))
        normalized_query = _normalize_text(query)

        hits = []
        for document_id in candidate_ids:
            metadata = metadata_by_id[document_id]

            # 各项得分
            semantic = semantic_scores.get(document_id, 0.0)
            lexical = lexical_scores.get(document_id, 0.0)
            quality = _bounded_score(metadata.get("quality_score"), default=0.5)
            authority = _source_authority(str(metadata.get("source_tier") or "unknown"))

            # 精确短语匹配：查询词完整出现在文档中
            phrase_match = (
                1.0
                if normalized_query in _normalize_text(text_by_id[document_id])
                else 0.0
            )

            # 语义 guard：高语义相似度项额外加分，拉开与低质结果的差距
            semantic_guard = 0.08 if semantic >= 0.7 else 0.0

            # ==============================================================
            # 加权重排序公式
            # ==============================================================
            rerank = (
                0.42 * semantic      # 语义相似度（主力信号）
                + 0.33 * lexical     # BM25 词汇匹配（精确关键词）
                + 0.12 * quality     # 元数据质量分（审核评分）
                + 0.08 * authority   # 来源权威度（official > trusted > community）
                + 0.05 * phrase_match  # 精确短语命中
                + semantic_guard     # 高语义 boost
            )

            hits.append(
                KnowledgeHit(
                    document_id=document_id,
                    text=text_by_id[document_id],
                    distance=distance_by_id.get(document_id, 1.0),
                    metadata=metadata,
                    semantic_score=round(semantic, 4),
                    lexical_score=round(lexical, 4),
                    rerank_score=round(rerank, 4),
                    retrieval_mode="hybrid_vector_bm25_rerank",
                )
            )

        # 按 rerank_score 降序，返回 top-N
        return sorted(hits, key=lambda item: item.rerank_score, reverse=True)[
            : max(limit, 1)
        ]

    # -----------------------------------------------------------------------
    # 查询辅助
    # -----------------------------------------------------------------------

    def count(self, knowledge_base: str) -> int:
        """返回指定知识库的文档总数。"""
        return self._collection(knowledge_base).count()

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    def _collection(self, knowledge_base: str):
        """获取或创建指定知识库的 ChromaDB collection。

        Collection 命名：{prefix}_{knowledge_base}
        如 travel_knowledge_bge_v15_poi

        元数据写入：
        - hnsw:space = cosine（余弦距离，与 BGE L2 归一化配合）
        - embedding_model = 当前嵌入函数名（用于切换嵌入函数时的冲突检测）
        - embedding_dimension = 向量维度

        注意：如果 collection 已存在且 embedding_function 名不匹配，
        ChromaDB 会抛出 ValueError。这是预期行为——防止用 hash embedding
        去读取 BGE 编码的数据。
        """
        suffix = self._normalize_name(knowledge_base)
        return self._client.get_or_create_collection(
            name=f"{self._prefix}_{suffix}",
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": self._embedding.name(),
                "embedding_dimension": getattr(self._embedding, "dimension", 0),
            },
            embedding_function=self._embedding,
        )

    def _metadata(self, document: KnowledgeDocument) -> dict[str, str | int | float | bool]:
        """从 KnowledgeDocument 构建 ChromaDB metadata dict。

        包含两部分：
        1. 必有字段：city, category, source, updated_at, embedding_*
        2. 扩展字段：document.metadata 中的自定义字段（source_url, quality_score 等）

        embedding_model / embedding_version / embedding_dimension
        写入每个文档的 metadata 而非 collection 级别，便于迁移时逐条追踪。
        """
        metadata: dict[str, str | int | float | bool] = {
            "city": document.city,
            "category": document.category,
            "source": document.source,
            "updated_at": document.updated_at.isoformat(),
            "embedding_model": self._embedding.name(),
            "embedding_version": "1",
            "embedding_dimension": getattr(self._embedding, "dimension", 0),
        }
        metadata.update(document.metadata)
        return metadata

    def _query_embedding(self, query: str) -> list[float]:
        """将查询文本转为归一化嵌入向量。

        优先使用 embed_query 方法（BGE 会用 query instruction 前缀），
        降级为普通 __call__ 接口（Hash 嵌入没有专门的 query 方法）。
        """
        # BGE 嵌入函数有专门的 embed_query（加 instruction 前缀）
        embed_query = getattr(self._embedding, "embed_query", None)
        if callable(embed_query):
            raw_embedding = embed_query(query)
        else:
            # Hash 嵌入：直接用 __call__
            raw_embedding = self._embedding([query])[0]

        # 确保是 1-D float32 数组
        normalized = np.asarray(raw_embedding, dtype=np.float32)
        if normalized.ndim == 2 and normalized.shape[0] == 1:
            normalized = normalized[0]
        if normalized.ndim != 1:
            raise ValueError(
                f"Query embedding must be one-dimensional, got {normalized.shape}"
            )
        return normalized.tolist()

    @staticmethod
    def _normalize_name(value: str) -> str:
        """将知识库名规范化为合法的 collection 名。

        规则：
        - 只保留 a-z, A-Z, 0-9, _, -
        - 全部小写
        - 长度 3-63（ChromaDB collection 名限制）
        - 不足 3 位时右侧补 'x'
        """
        normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_-").lower()
        normalized = normalized or "default"
        if len(normalized) < 3:
            normalized = normalized.ljust(3, "x")
        return normalized[:63].rstrip("_-")


# ---------------------------------------------------------------------------
# 辅助函数（模块级）
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """对中文文本进行 jieba 分词 + 二元组扩展。

    分词策略：
    1. jieba 精确模式分词（保留中英文及数字的 token）
    2. 对所有中文字符生成相邻二元组（bigram）
       - 例 "大熊猫" → ["熊猫"] （相邻字符对）

    二元组的作用：即使 jieba 分错了词（如"熊猫基地"→"熊猫/基地"），
    bigram "熊猫" 仍能匹配查询中的"熊猫"。

    Returns:
        分词列表（词 + bigram 的并集）
    """
    normalized = _normalize_text(text)

    # jieba 精确模式分词
    words = [
        token.strip()
        for token in jieba.lcut(normalized, cut_all=False)
        if token.strip() and re.search(r"[\w一-鿿]", token)
    ]

    # 中文字符二元组扩展（增强召回）
    chinese = "".join(re.findall(r"[一-鿿]", normalized))
    bigrams = [
        chinese[index : index + 2]
        for index in range(max(len(chinese) - 1, 0))
    ]

    return [*words, *bigrams]


def _normalize_text(value: str) -> str:
    """文本归一化：去所有空白字符 + 全小写。

    用于分词前的预处理及精确短语匹配的比较。
    """
    return re.sub(r"\s+", "", str(value or "").casefold())


def _normalize_scores(values) -> list[float]:
    """Min-Max 归一化至 [0, 1]。

    处理边界情况：
    - 所有值相等 → 全 1.0（正值）或全 0.0（零值）
    - 空列表 → 返回空列表
    """
    scores = [float(value) for value in values]
    if not scores:
        return []
    low, high = min(scores), max(scores)
    if math.isclose(low, high):
        return [1.0 if high > 0 else 0.0 for _ in scores]
    return [(value - low) / (high - low) for value in scores]


def _bounded_score(value: object, *, default: float) -> float:
    """安全地将任意值转为 [0, 1] 范围的浮点数。

    用于处理 metadata 中的 quality_score 等字段可能为 None 或非数字的情况。
    """
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _source_authority(source_tier: str) -> float:
    """来源分级 → 权威度得分映射。

    来源分级体系（由知识管线清洗时标注）：
        official   = 1.00  官方来源（政府、景区官网）
        trusted    = 0.80  可信编辑（维基、知名旅游平台）
        commercial = 0.55  商业来源（OTA、旅行社）
        community  = 0.40  社区来源（小红书、论坛、UGC）
        unknown    = 0.20  未知来源

    权威度被纳入混合检索重排序公式（权重 8%），
    目的是在同等语义/词汇相关性下优先推荐更可靠的来源。
    """
    return {
        "official": 1.0,
        "trusted": 0.8,
        "commercial": 0.55,
        "community": 0.4,
        "unknown": 0.2,
    }.get(source_tier, 0.2)

"""BGE-small-zh-v1.5 ONNX 嵌入函数。

提供纯 CPU 的中文文本向量化能力，无需 GPU 或 PyTorch。
模型来源：Xenova/bge-small-zh-v1.5（HuggingFace），INT8 量化 ONNX。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from huggingface_hub import snapshot_download
from tokenizers import Tokenizer


class BgeSmallZhV15EmbeddingFunction(EmbeddingFunction[Documents]):
    """BGE-small-zh-v1.5 中文嵌入函数，基于 ONNX Runtime CPU 推理。

    特性：
    - 512 维向量输出
    - INT8 量化 ONNX 模型，内存占用约 24MB
    - 查询时自动拼接 instruction 前缀以提升检索质量
    - 支持批量编码（batch_size 可配，默认 16）
    - 支持从 HuggingFace 自动下载模型文件

    模型文件清单（下载到 model_directory）：
        tokenizer.json         — 分词器词表与合并规则
        onnx/model_quantized.onnx — INT8 量化 ONNX 模型
        config.json / vocab.txt / tokenizer_config.json / special_tokens_map.json

    使用方式：
        ef = BgeSmallZhV15EmbeddingFunction("./.data/models/bge-small-zh-v1.5",
                                             auto_download=True)
        vectors = ef(["成都大熊猫基地", "宽窄巷子"])
        # vectors 为 [[float, ...], [float, ...]]，每个长度 512
    """

    # 输出向量维度（BGE-small-zh 固定为 512）
    dimension = 512

    # HuggingFace 仓库标识
    model_id = "Xenova/bge-small-zh-v1.5"

    # 量化 ONNX 模型文件在仓库中的相对路径
    model_file = "onnx/model_quantized.onnx"

    # BGE 系列模型的查询 instruction 前缀
    # 论文表明加上此前缀可显著提升检索任务的向量质量
    query_instruction = "为这个句子生成表示以用于检索相关文章："

    def __init__(
        self,
        model_directory: Path | str,
        *,
        auto_download: bool = False,
        max_length: int = 512,
        batch_size: int = 16,
    ) -> None:
        """初始化嵌入函数。

        Args:
            model_directory: 模型文件所在目录（含 tokenizer.json 和 onnx/）
            auto_download: 为 True 时自动从 HuggingFace 下载缺失的模型文件
            max_length: 单条文本最大 token 数，超出部分将被截断
            batch_size: 批量编码时每批处理的文本数量
        """
        self.model_directory = Path(model_directory).resolve()
        self.max_length = max_length
        self.batch_size = batch_size

        # 自动下载缺失文件（仅当 auto_download=True 时触发）
        if auto_download:
            self.ensure_model()
        self._require_model_files()

        # 加载 HuggingFace tokenizers 分词器
        # tokenizer.json 包含 BPE 词表、合并规则及特殊 token 映射
        self._tokenizer = Tokenizer.from_file(
            str(self.model_directory / "tokenizer.json")
        )
        self._tokenizer.enable_truncation(max_length=max_length)
        self._tokenizer.enable_padding(
            pad_id=self._tokenizer.token_to_id("[PAD]") or 0,
            pad_token="[PAD]",
        )

        # 初始化 ONNX 推理会话，强制使用 CPU 执行
        self._session = ort.InferenceSession(
            str(self.model_directory / self.model_file),
            providers=["CPUExecutionProvider"],
        )
        # 记录模型接受的输入名，用于过滤编码器输出
        self._input_names = {item.name for item in self._session.get_inputs()}

    def __call__(self, input: Documents) -> Embeddings:
        """ChromaDB 要求的调用接口：对一批文档生成嵌入向量。"""
        return self._embed(list(input))

    def embed_query(self, query: str) -> list[float]:
        """对单条查询文本生成嵌入向量，自动拼接 instruction 前缀。"""
        return self._embed([f"{self.query_instruction}{query}"])[0]

    @staticmethod
    def name() -> str:
        """返回嵌入模型的唯一标识名，ChromaDB 用它校验 collection 的 embedding_function。

        如果 collection 已存在且 embedding_function 名不匹配，ChromaDB 会拒绝操作，
        防止用 Hash embedding 去读 BGE 编码的向量。
        """
        return "bge_small_zh_v1_5_onnx_int8"

    def get_config(self) -> dict[str, Any]:
        """返回可序列化的配置字典，用于 build_from_config 重建实例。"""
        return {
            "model_directory": str(self.model_directory),
            "max_length": self.max_length,
            "batch_size": self.batch_size,
        }

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "BgeSmallZhV15EmbeddingFunction":
        """从配置字典重建嵌入函数实例。"""
        return BgeSmallZhV15EmbeddingFunction(
            config["model_directory"],
            max_length=int(config.get("max_length", 512)),
            batch_size=int(config.get("batch_size", 16)),
        )

    def ensure_model(self) -> None:
        """从 HuggingFace 下载模型文件（如本地缺失）。

        使用 snapshot_download 只拉取必需文件，跳过 PyTorch 权重、
        ONNX 非量化版本等无关内容，节省带宽和磁盘空间。
        """
        if self._model_files_exist():
            return
        self.model_directory.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=self.model_id,
            local_dir=self.model_directory,
            allow_patterns=[
                "tokenizer.json",
                "tokenizer_config.json",
                "special_tokens_map.json",
                "vocab.txt",
                "config.json",
                self.model_file,
            ],
        )

    def _embed(self, texts: list[str]) -> Embeddings:
        """核心编码逻辑：分词 → ONNX 推理 → Mean Pooling → L2 归一化。

        流程：
        1. 分批处理（batch_size 控制每批数量）
        2. tokenizer 编码为 input_ids + attention_mask（+ token_type_ids 如存在）
        3. ONNX 推理得出 last_hidden_state [batch, seq_len, 512]
        4. 取 [CLS] 位置（第 0 个 token）作为句子表示
        5. L2 归一化使向量落在单位球面上，适合余弦相似度检索
        """
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for offset in range(0, len(texts), self.batch_size):
            batch = texts[offset : offset + self.batch_size]

            # Step 1: 分词编码
            encodings = self._tokenizer.encode_batch(batch)
            feeds = {
                "input_ids": np.asarray(
                    [encoding.ids for encoding in encodings], dtype=np.int64
                ),
                "attention_mask": np.asarray(
                    [encoding.attention_mask for encoding in encodings], dtype=np.int64
                ),
            }

            # 部分模型（如 BERT 系）还需要 token_type_ids
            if "token_type_ids" in self._input_names:
                feeds["token_type_ids"] = np.asarray(
                    [encoding.type_ids for encoding in encodings], dtype=np.int64
                )

            # 只送入模型实际接受的输入，避免 ONNX 报 unknown input 错误
            feeds = {name: value for name, value in feeds.items()
                     if name in self._input_names}

            # Step 2: ONNX 推理
            last_hidden_state = self._session.run(None, feeds)[0]  # [batch, seq_len, 512]

            # Step 3: CLS pooling — 取序列第一个 token 的输出
            pooled = last_hidden_state[:, 0, :]  # [batch, 512]

            # Step 4: L2 归一化
            norms = np.linalg.norm(pooled, axis=1, keepdims=True)
            normalized = pooled / np.clip(norms, 1e-12, None)

            embeddings.extend(normalized.astype(np.float32).tolist())

        return embeddings

    def _require_model_files(self) -> None:
        """校验必需模型文件存在，缺失时抛出明确错误提示。"""
        if self._model_files_exist():
            return
        raise FileNotFoundError(
            "BGE model files are missing. Enable BGE_AUTO_DOWNLOAD or run the "
            "documented model download command before starting FastAPI."
        )

    def _model_files_exist(self) -> bool:
        """检查分词器和 ONNX 模型文件是否均存在。"""
        return (
            (self.model_directory / "tokenizer.json").is_file()
            and (self.model_directory / self.model_file).is_file()
        )

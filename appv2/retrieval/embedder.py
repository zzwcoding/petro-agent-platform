"""retrieval.embedder —— 向量化 seam 与两适配器（V2-04，specs/modules.md
retrieval 卡 Seam/Adapter 行；B6 纪律——embedding 面唯一出口 infra.llm_client
.embeddings）。

- Embedder：检索探针向量化 seam（engine 只认本协议）；
- LocalHashEmbedder：本地确定性向量（V1 kb.domain.LocalHashEmbedder 逐款
  移植——md5 槽位哈希，非语义向量；测试底座/离线 fallback）；
- RemoteEmbedder：真 embedding 后端（V1 RemoteEmbedder 同款——infra.llm_client
  .embeddings 的域侧消费视图；MiniMax embo-01 query/db 分型算法：检索探针
  input_type="query"，禁与入库 db 型混用单实例）。上游失败直抛调用方不静默
  ——engine 向量腿按空腿兜底、关键词腿照跑（specs/retrieval.md 行为约定 5）。

边界：本模块 import appv2.infra.llm_client（公开接口——importlinter V2 引擎
依赖只许 infra 的在册消费）；httpx/litellm 等供应商 SDK 零接触。
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Protocol

from appv2.infra.llm_client import LlmClient

# 维度＝MiniMax embo-01 真维度 1536（V1 EMBED_DIM 同源——LocalHash 同维出形，
# 异维度对不上余弦护栏返回 0.0 不误配）。
EMBED_DIM = 1536


class Embedder(Protocol):
    """向量化 seam（真实 embedding 模型落位批只换实现，签名不动——V1 同注）。"""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


def _tokenize(text: str) -> list[str]:
    """检索用确定性分词（V1 kb.domain.tokenize 移植：ASCII 词＋CJK 二元组）。"""
    tokens: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]", text):
        if raw.isascii():
            tokens.append(raw.casefold())
        else:
            tokens.append(raw)  # 单 CJK 字
    cjk_runs = re.findall(r"[\u4e00-\u9fff]+", text)
    for run in cjk_runs:
        tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


class LocalHashEmbedder:
    """本地确定性向量（V1 逐款移植——md5 槽位＋符号位，L2 归一；非语义向量）。

    测试底座 fallback 与离线冒烟用——生产装配＝RemoteEmbedder。
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * EMBED_DIM
        for token in _tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            slot = int(digest[:8], 16) % EMBED_DIM
            sign = 1.0 if int(digest[8:10], 16) & 1 else -1.0
            vec[slot] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [round(v / norm, 6) for v in vec]


class RemoteEmbedder:
    """真 embedding 后端（检索探针侧——infra.llm_client.embeddings 消费视图）。

    B6 单点：供应商接触只在 infra.llm_client；本类是同一缝的域侧视图
    （V1 kb.service.RemoteEmbedder 同构——组合根装配，retrieval 不碰 SDK）。
    input_type 固定 "query"（MiniMax 检索文本型——与入库 db 型分型，禁混用
    单实例）；上游失败（UpstreamUnavailable/UpstreamRejected）直抛调用方
    不静默——engine 向量腿按空腿处理（关键词腿兜底）。
    """

    def __init__(self, client: LlmClient, alias: str = "petro-embed") -> None:
        self._client: Any = client
        self._alias = alias

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = await self._client.embeddings(self._alias, list(texts), input_type="query")
        return [[float(x) for x in vec] for vec in out.vectors]

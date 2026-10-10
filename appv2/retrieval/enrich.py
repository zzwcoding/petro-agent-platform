"""retrieval.enrich —— 索引管线富化阶段（V2-47 R1b，tickets/v2/V2-47-R1b
切片富化.md；参考 ai-agent-book ch2 上下文工程/ch3 知识库——Anthropic 上下文
感知检索＋RAPTOR 节级摘要单级版）。

两件富化（票面任务 1——索引期治本）：
- **切片上下文前缀**：索引期给每切片拼
  〔本段节选自〈报告名〉·〈章节路径〉〕前缀（domain.context_prefix——元数据
  已备，确定性零模型）进 BM25/向量双索引；
- **节级摘要层**：同节切片按顶层章聚类（domain.section_root）→节级 LLM 摘要
  （complete 面，caller 归因 agent_v2.retrieval.enrich）→摘要节点入索引——
  补齐「切片→节→全文」中间层，多粒度检索。

additive 幂等（票面边界红线）：富化产物只写富化索引表（EnrichStore 缝——
生产 PgEnrichStore，测试 InMemoryEnrichStore），kb_* 原表零触碰（旧向量/
原文可重建不毁 fixture）；节点确定性身份（summary_node_id）＋upsert 语义＝
重跑零重复节点。回滚路径＝清空富化索引表（检索自动回落原向量/原文）。

在线消费：EnrichedFragmentLibrary 包装任一 FragmentLibrary——overlay 覆写切
片向量＋摘要节点追加入语料；空富化库＝原样透传（上线未富化态零漂移）。
读面时延治理（P-046 中途审查 S1）：快照按 store.version() 变更令牌缓存——
每次 retrieve 只付一次廉价版本查询（标量行零向量列），全量向量读只在富化
库变更后首次发生（离线批间检索面 +227ms/retrieve 收敛为毫秒级版本读）。

摘要生成规则（P-046 中途审查 consider 1 采纳）：cover_count≥2（SUMMARY_MIN_
COVER）才生成节级摘要节点——单成员簇无「节级」信息增量（占真库 36/59 簇），
成员不足簇不调用模型、不生成节点；规则变更重跑由 prune_summaries 清理陈旧
摘要行（终态幂等——库态恰等于本轮新鲜集）。

批入口＝tools/v2_enrich_batch.py（生产装配面——R1 闭包闸把网关装配隔离
在检索包外；本模块只留注入缝 completer/embedder/store）。

边界（specs/modules.md）：依赖只许 appv2.infra＋本包；LLM 调用只经注入
completer（生产装配＝infra GatewayService.complete——B6 唯一出口）；时间只
经 infra.clock（B14）；不 import app.**／knowledge/query。
"""

from __future__ import annotations

import abc
from collections.abc import Sequence
from dataclasses import dataclass, replace

from appv2.retrieval.domain import (
    NODE_SECTION_SUMMARY,
    NODE_SLICE,
    FragmentRecord,
    enriched_index_text,
    section_root,
    summary_node_id,
)
from appv2.retrieval.embedder import Embedder
from appv2.retrieval.engine import COMPLETE_ALIAS, Completer
from appv2.retrieval.source import FragmentLibrary

# ---------- caller 归因（gateway 记账按 caller 聚合——engine 同款惯例） ----------

CALLER_ENRICH = "agent_v2.retrieval.enrich"

# 单次向量化批量上限（embo-01 单文本 4096 token——V1 reembed 同值保守实施）。
EMBED_BATCH_SIZE = 16

# 摘要生成最小覆盖（P-046 中途审查 consider 1 采纳）：同节切片 ≥2 支才生成
# 节级摘要节点——单成员簇「聚类」未发生，摘要≈单切片改写入索引（近重复候
# 选），信息增量存疑；成员不足簇不调用模型不生成节点。
SUMMARY_MIN_COVER = 2

# ---------- 节级摘要提示词（要点式短摘要——检索索引用，非生成窗材料） ----------

SUMMARY_SYSTEM_PROMPT = (
    "你是石油工程知识库的索引摘要器。给定一份报告某个章节的全部切片原文，"
    "输出该章节的要点式摘要，供检索索引使用。只输出摘要正文，"
    "不要输出标题、前言、解释或列表编号以外的内容。"
)
SUMMARY_USER_TEMPLATE = (
    "报告名：{report}\n"
    "章节路径：{section}\n"
    "本章节共 {count} 支切片，原文如下：\n{members}\n\n"
    "请输出本章节要点式摘要（至多 120 字，覆盖本章节的关键对象、数值与结论）。"
)

# 摘要节点文本头（确定性拼装单点——节路径＋覆盖支数随节点文本可检索）。
SUMMARY_HEADER_TEMPLATE = "〔节级摘要｜{report}·{section}｜覆盖 {count} 支切片〕"


# ---------- 记录形状（富化索引表行投影——store 缝与编排共用） ----------


@dataclass(frozen=True, slots=True)
class SectionCluster:
    """节聚类簇（同报告同顶层章的切片集——摘要生成的输入单元）。"""

    report_id: str
    report: str
    library_id: str
    library: str
    family: str
    root: str  # 顶层章节名（section_root——簇键）
    members: tuple[str, ...]  # 成员切片 id（语料序）
    texts: tuple[str, ...]  # 成员原文（与 members 同序）


@dataclass(frozen=True, slots=True)
class SummaryNode:
    """节级摘要节点（富化索引表 section_summary 行——可检索可展开的中间层）。"""

    node_id: str
    report_id: str
    report: str
    library_id: str
    library: str
    family: str
    section: str  # 节路径（顶层章名——展开键）
    text: str  # 〔节级摘要｜…〕＋要点正文
    cover_count: int
    source_ids: tuple[str, ...]
    embedding: list[float] | None = None
    model: str = ""


@dataclass(frozen=True, slots=True)
class SliceOverlay:
    """切片富化向量（索引文本＝前缀＋原文的 db 型重嵌——覆盖原向量的索引面）。"""

    fragment_id: str
    embedding: list[float]
    model: str


@dataclass(frozen=True, slots=True)
class EnrichLedger:
    """富化批账本（逐项数字如实——票面「账本如实记账」的编排面）。

    embedding_tokens＝向量化面 token 数（RemoteEmbedder.usage_log 累计——
    本地确定性向量无 usage 如实记 0）；complete 面逐笔账在 gateway_spend_record
    （caller=agent_v2.retrieval.enrich——B6 记账唯一真源，批侧只汇总笔数）。
    """

    corpus_total: int  # 全库片段行数（含父块）
    corpus_embedded: int  # 实际重嵌切片数（父块/空文本不入）
    overlay_written: int
    clusters_total: int
    summaries_written: int
    summaries_failed: tuple[str, ...]  # 失败簇键（报告名·节路径——重跑补齐）
    complete_calls: int
    embedding_calls: int
    embedding_tokens: int
    clusters_single_cover: int = 0  # 成员不足 SUMMARY_MIN_COVER 的簇数（不生成摘要——如实入账）


# ---------- 节聚类与摘要文本（确定性——零模型） ----------


def cluster_sections(corpus: Sequence[FragmentRecord]) -> list[SectionCluster]:
    """节聚类（票面任务 1——同节切片聚类；簇键＝（报告，顶层章））。

    - 簇序＝（report_id, root）排序序（确定性——重跑同构）；成员保持语料序；
    - 仅切片节点参与（摘要节点/父块不是聚类对象）；无路径切片不入簇
      （section_root None——不发明章节归属）；
    - 摘要块/问题块照簇（真库实态：全文档摘要/问题块·第 N 批自成顶层段——
      统一处理，摘要的摘要亦是可检索入口）。
    """
    grouped: dict[tuple[str, str], SectionCluster] = {}
    for frag in corpus:
        if frag.node_kind != NODE_SLICE or not frag.text:
            continue
        root = section_root(frag.section)
        if root is None:
            continue
        key = (frag.report_id, root)
        cluster = grouped.get(key)
        if cluster is None:
            cluster = SectionCluster(
                report_id=frag.report_id,
                report=frag.report,
                library_id=frag.library_id,
                library=frag.library,
                family=frag.family,
                root=root,
                members=(frag.fragment_id,),
                texts=(frag.text,),
            )
            grouped[key] = cluster
        else:
            grouped[key] = SectionCluster(
                report_id=cluster.report_id,
                report=cluster.report,
                library_id=cluster.library_id,
                library=cluster.library,
                family=cluster.family,
                root=cluster.root,
                members=(*cluster.members, frag.fragment_id),
                texts=(*cluster.texts, frag.text),
            )
    return [grouped[key] for key in sorted(grouped)]


def build_summary_text(cluster: SectionCluster, body: str) -> str:
    """摘要节点文本＝确定性头（节路径＋覆盖支数）＋LLM 要点正文。"""
    header = SUMMARY_HEADER_TEMPLATE.format(
        report=cluster.report, section=cluster.root, count=len(cluster.members)
    )
    return f"{header}{body.strip()}"


# ---------- 富化索引存储缝（additive 幂等——kb_* 原表零触碰） ----------


class EnrichStore(abc.ABC):
    """富化索引存储缝（生产＝PgEnrichStore；测试＝InMemoryEnrichStore）。"""

    @abc.abstractmethod
    async def snapshot(self) -> tuple[dict[str, list[float]], list[SummaryNode]]:
        """富化快照（切片 overlay 向量映射＋摘要节点列——只读副本语义）。"""

    @abc.abstractmethod
    async def version(self) -> str:
        """富化库变更令牌（廉价读——库态变则令牌变；读面缓存失效判据，S1）。

        实现须远廉于 snapshot（无向量列传输）——EnrichedFragmentLibrary 每次
        retrieve 只付本查询，全量快照仅在令牌变更后重读。
        """

    @abc.abstractmethod
    async def prune_summaries(self, keep_node_ids: set[str]) -> int:
        """删除 keep 集之外的摘要节点行，返回删除行数。

        规则变更重跑的终态幂等半边（consider 1）：upsert 只覆写同键——本轮
        不再生成的陈旧摘要（如单成员簇节点）须显式清理，库态恰等于新鲜集。
        """

    @abc.abstractmethod
    async def upsert(
        self, overlays: Sequence[SliceOverlay], summaries: Sequence[SummaryNode]
    ) -> int:
        """幂等写入（同键覆写不新增——重跑零重复节点）；返回写入行数。"""


class InMemoryEnrichStore(EnrichStore):
    """内存富化库（fixture 注入——零 I/O；返回容器一律副本，INV-2 同纪律）。"""

    def __init__(self) -> None:
        self._overlays: dict[str, list[float]] = {}
        self._nodes: dict[str, SummaryNode] = {}
        self._version = 0  # 变更令牌（upsert/prune 递增——缓存失效判据）

    async def snapshot(self) -> tuple[dict[str, list[float]], list[SummaryNode]]:
        return dict(self._overlays), list(self._nodes.values())

    async def version(self) -> str:
        return str(self._version)

    async def prune_summaries(self, keep_node_ids: set[str]) -> int:
        keep = {str(key) for key in keep_node_ids}
        stale = [key for key in self._nodes if key not in keep]
        for key in stale:
            del self._nodes[key]
        self._version += 1
        return len(stale)

    async def upsert(
        self, overlays: Sequence[SliceOverlay], summaries: Sequence[SummaryNode]
    ) -> int:
        for overlay in overlays:
            self._overlays[overlay.fragment_id] = list(overlay.embedding)
        for node in summaries:
            self._nodes[node.node_id] = node
        self._version += 1
        return len(overlays) + len(summaries)


class EnrichedFragmentLibrary(FragmentLibrary):
    """富化装配读面（包装任一 FragmentLibrary——在线消费单点）。

    - 切片：overlay 向量在簿即覆写 embedding（索引面换富化向量——原向量在
      原表不动，旧索引可重建）；
    - 摘要节点：追加入语料尾（node_kind=section_summary——双路召回独立可检
      索，engine 命中后展开节内切片）；
    - 空富化库＝原样透传（未富化态零漂移）；
    - 快照缓存（S1 时延治理）：按 store.version() 令牌缓存——同令牌重复读
      零全量快照（每次 retrieve 一次版本查询），令牌变更（富化批落库）即
      失效重读（新索引及时可见）。
    """

    def __init__(self, inner: FragmentLibrary, store: EnrichStore) -> None:
        self._inner = inner
        self._store = store
        self._cache_version: str | None = None
        self._cache: tuple[dict[str, list[float]], list[SummaryNode]] | None = None

    async def _enrich_snapshot(self) -> tuple[dict[str, list[float]], list[SummaryNode]]:
        version = await self._store.version()
        if self._cache is None or version != self._cache_version:
            self._cache = await self._store.snapshot()
            self._cache_version = version
        return self._cache

    async def fragments(self) -> list[FragmentRecord]:
        base = await self._inner.fragments()
        overlays, nodes = await self._enrich_snapshot()
        out: list[FragmentRecord] = []
        for frag in base:
            vector = overlays.get(frag.fragment_id)
            out.append(replace(frag, embedding=vector) if vector is not None else frag)
        out.extend(_summary_to_record(node) for node in nodes)
        return out


def _summary_to_record(node: SummaryNode) -> FragmentRecord:
    """摘要节点→语料记录（出处链三级＋族随节点在案——供给分池/锚保底可用）。"""
    return FragmentRecord(
        fragment_id=node.node_id,
        report_id=node.report_id,
        report=node.report,
        section=node.section,
        library_id=node.library_id,
        library=node.library,
        family=node.family,
        text=node.text,
        embedding=node.embedding,
        node_kind=NODE_SECTION_SUMMARY,
    )


# ---------- 编排（入库/重索引富化阶段——离线批与管线共用同一函数） ----------


async def enrich_index(
    *,
    corpus: Sequence[FragmentRecord],
    store: EnrichStore,
    completer: Completer,
    embedder: Embedder,
    summary_alias: str = COMPLETE_ALIAS,
    caller: str = CALLER_ENRICH,
    batch_size: int = EMBED_BATCH_SIZE,
) -> EnrichLedger:
    """索引富化编排（票面任务 1/3——切片重嵌＋节级摘要生成＋幂等落库）。

    - 重嵌面：切片索引文本（前缀＋原文）db 型向量化（与入库管线同型——
      query/db 分型纪律在 embedder 缝）；
    - 摘要面：逐簇一次 complete 调用（失败跳过入账本不炸批——重跑补齐）；
      cover_count≥SUMMARY_MIN_COVER 才生成（consider 1——单成员簇无节级增量，
      不调用模型）；
    - 落库：全量 upsert＋陈旧摘要清理（同键覆写＋prune——终态幂等：库态恰
      等于本轮新鲜集，规则变更重跑即得）。
    """
    slices = [
        frag
        for frag in corpus
        if frag.node_kind == NODE_SLICE and frag.text and frag.fragment_id
    ]
    clusters = cluster_sections(corpus)
    eligible = [c for c in clusters if len(c.members) >= SUMMARY_MIN_COVER]
    single_cover = len(clusters) - len(eligible)

    nodes: list[SummaryNode] = []
    failed: list[str] = []
    for cluster in eligible:
        body = await _summary_body(cluster, completer, summary_alias, caller)
        if body is None:
            failed.append(f"{cluster.report}·{cluster.root}")
            continue
        nodes.append(
            SummaryNode(
                node_id=summary_node_id(cluster.report_id, cluster.root),
                report_id=cluster.report_id,
                report=cluster.report,
                library_id=cluster.library_id,
                library=cluster.library,
                family=cluster.family,
                section=cluster.root,
                text=build_summary_text(cluster, body),
                cover_count=len(cluster.members),
                source_ids=cluster.members,
            )
        )

    overlay_vectors, embed_calls = await _embed_batched(
        embedder, [enriched_index_text(frag) for frag in slices], batch_size
    )
    summary_vectors, node_embed_calls = await _embed_batched(
        embedder, [node.text for node in nodes], batch_size
    )
    embed_calls += node_embed_calls

    overlays = [
        SliceOverlay(
            fragment_id=frag.fragment_id,
            embedding=vector,
            model=_embed_model_name(embedder),
        )
        for frag, vector in zip(slices, overlay_vectors, strict=True)
    ]
    nodes = [
        replace(node, embedding=vector, model=_embed_model_name(embedder))
        for node, vector in zip(nodes, summary_vectors, strict=True)
    ]
    await store.upsert(overlays, nodes)
    await store.prune_summaries({node.node_id for node in nodes})
    return EnrichLedger(
        corpus_total=len(corpus),
        corpus_embedded=len(slices),
        overlay_written=len(overlays),
        clusters_total=len(clusters),
        summaries_written=len(nodes),
        summaries_failed=tuple(failed),
        complete_calls=len(eligible) - len(failed),
        embedding_calls=embed_calls,
        embedding_tokens=_embedding_tokens(embedder),
        clusters_single_cover=single_cover,
    )


async def _summary_body(
    cluster: SectionCluster,
    completer: Completer,
    alias: str,
    caller: str,
) -> str | None:
    """单簇摘要生成（一次 complete——失败返回 None 不炸批；重跑补齐）。"""
    members = "\n\n".join(
        f"[{i}] {text}" for i, text in enumerate(cluster.texts, 1)
    )
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": SUMMARY_USER_TEMPLATE.format(
                report=cluster.report,
                section=cluster.root,
                count=len(cluster.members),
                members=members,
            ),
        },
    ]
    try:
        completion = await completer.complete(alias, messages, caller=caller)
    except Exception:  # 调用失败——跳过入账本（账面 failed 段），批照跑
        return None
    body = str(completion.content).strip()
    return body or None


async def _embed_batched(
    embedder: Embedder, texts: list[str], batch_size: int
) -> tuple[list[list[float]], int]:
    """分批向量化（embo-01 单文本 4096 token——16/批保守实施，V1 reembed 同值）。

    别名绑定在生产 embedder 构造面（RemoteEmbedder(alias)——协议无别名槽）；
    批序确定性：按入参序切片分批，向量与输入严格同序。
    """
    if not texts:
        return [], 0
    vectors: list[list[float]] = []
    calls = 0
    for start in range(0, len(texts), max(1, batch_size)):
        vectors.extend(await embedder.embed(texts[start : start + batch_size]))
        calls += 1
    return vectors, calls


def _embed_model_name(embedder: Embedder) -> str:
    """向量化后端名（RemoteEmbedder.usage_log 留痕；本地桩如实记 local-hash）。"""
    log = getattr(embedder, "usage_log", None)
    if log:
        return str(log[-1].model)
    return "local-hash"


def _embedding_tokens(embedder: Embedder) -> int:
    """向量化 token 合计（usage_log 在案如实累加；本地桩无 usage＝0）。"""
    return sum(int(entry.total_tokens) for entry in getattr(embedder, "usage_log", ()))

"""retrieval.engine —— RetrievalEngine（retrieve＋graph 两面；V2-04，specs/
retrieval.md 接口定义/行为约定节）。

V1 S4 双路召回＋精排＋生成窗供给＋图谱链移植为确定性引擎（无 SSE 链体——
供给策略本体化后 engine 一次返回完整 RetrievalBundle，叙事/生成归 runtime 阐
述步，specs/retrieval.md「不做什么」）。

行为约定对位（specs/retrieval.md）：
1. 双路召回（向量＋关键词）→ RRF 融合 → 精排（LLM 批量排序＋来源置信度，
   **至多两次 LLM 调用**；调用失败/解析失败/未接线→融合序放行——W-F34-2
   回退不炸链）。来源置信度只重排来源块序——供给窗硬规则不受其影响。
2. 供给分池（supply_window，domain 硬编码）：family_hints 命中族共享 3/4 预
   算、其余族每族保底 1 席（完井族题不挤占月报族配额）；族内同来源（报告）
   至多半额轮询（每来源至少留代表支——矛盾来源同窗并立）；预算 < 候选来源
   数→零席位来源逐个枚举进 window_note 缺位段。**V2-89b D3 真封顶**：锚保底／
   表类整行集／节内展开三通道追加席**计入 budget**（超预算即丢并落
   `over_budget`），节内展开另守 `SECTION_EXPAND_CAP` 上界——窗支数恒 ≤ budget。
3. 截断显式：window_note 恒带「共检索到 N 条材料，M 条用进了答案」
   （build_window_note 单点）——agent 据此区分「没有」与「没送」；同批计数
   落 `RetrievalBundle.recalled/sent` 结构化字段（V2-82e additive——注记措辞
   面之外的机读面，Q11 P0-2 病灶治理面）。
4. 同型文档来源标注：Observation.locator 携 library/报告名（出处链 fragment
   →report→library 三级）——锚错 A-W11 vs Y-21 可被核验步发现。
5. 失败回退语义同 V1（回退不炸链）：embedding 失败向量腿按空腿、关键词腿兜
   底；图谱源挂/未接线→空集回退＋window_note 如实声明（零异常）。

边界（specs/modules.md）：依赖只许 appv2.infra（RemoteEmbedder 消费
llm_client.embeddings——B6 embedding 唯一出口）；LLM 调用只经注入 completer
（生产装配＝infra GatewayService.complete——B6 complete 唯一出口，caller 归
agent_v2.retrieval.*）；不 import app.**／knowledge/query（引擎互禁）。

V2-97（D7）：compound 精排（`_llm_rerank`／`_batch_order`／`_doc_confidence`＋
提示词常量）**保留未接线** DEBT(V2-97)——生产装配 `RetrievalEngine` 构造无
`completer=`，恒走确定性融合序放行；本件不删，接线另立决策票（specs/retrieval.md
已登记在案）。
"""

from __future__ import annotations

from typing import Any, Protocol

from appv2.retrieval.domain import (
    NODE_SLICE,
    QUESTION_BLOCK_TYPE,
    SNIPPET_CHARS,
    FragmentRecord,
    GraphEdgeRecord,
    Hit,
    Observation,
    RetrievalBundle,
    RetrievalNeed,
    WindowSupply,
    _is_table_bearing,
    alnum_tokens,
    anchor_seat_tokens,
    bm25_scores,
    build_window_note,
    cosine_similarity,
    enriched_index_text,
    is_table_rowset_question,
    normalize_bm25,
    parse_confidence_scores,
    parse_rank_order,
    promote_entity_hits,
    rrf_merge,
    snippet_window,
    supply_window,
)
from appv2.retrieval.embedder import Embedder
from appv2.retrieval.source import FragmentLibrary, GraphSource

# ---------- caller 归因与别名（V1 chains.py 同款惯例——gateway 记账按 caller 聚合） ----------

COMPLETE_ALIAS = "petro-main"  # 精排/置信度默认出口（D1 别名——生产装配可换）
CALLER_RERANK = "agent_v2.retrieval.rerank"
CALLER_CONFIDENCE = "agent_v2.retrieval.confidence"

# ---------- 精排提示词（V1 chains.py 逐字移植——批量排序＋来源置信度） ----------

BATCH_RERANK_SYSTEM_PROMPT = (
    "你是检索精排器。根据问句判断每个候选片段与问句的相关程度，"
    "输出按相关度从高到低的候选编号列表。只输出编号和逗号，不要输出其他内容。"
)
BATCH_RERANK_USER_TEMPLATE = (
    "检索问句：{question}\n候选片段：\n{lines}\n\n"
    "只输出按与问句相关度从高到低排序的编号，逗号分隔（如 3,1,7）。"
)
DOC_CONF_SYSTEM_PROMPT = (
    "你是检索来源裁判。判断每个候选文档来源与用户问题的相关程度"
    "（0＝完全无关，10＝直接回答该问题所需的来源）。"
    "问句中点名的井号（如 W-57、Y-21）、报告名、章节号若在某来源的片段摘录中出现，"
    "该来源至少应给 8 分——片段摘录只是该来源的一小部分，未在摘录中出现"
    "不等于该来源没有相关内容，请结合出处名称与摘录综合判断。"
    '只输出一个 JSON 对象：{"scores": {"来源编号": 分数, ...}}，每个来源都必须给分，'
    "不要输出其他内容。"
)
DOC_CONF_USER_TEMPLATE = (
    "用户问题：{question}\n候选文档来源（编号｜出处｜至多 3 条片段摘录）：\n{lines}\n\n"
    '只输出 JSON：{{"scores": {{"来源编号": 分数, ...}}}}。'
)
DOC_CONF_SAMPLE_WIDTH = 90  # 来源置信度摘录窗宽（V1 同值）
DOC_CONF_SAMPLES = 3  # 每来源出示摘录条数（V1——单样例打分有采样偏）
GRAPH_SECTION = "关系图谱"  # 图谱边出处 section 槽（V1 图谱链同值）


class CompletionView(Protocol):
    """complete 应答的最小视图（infra gateway Completion 同形——content 在位）。

    成员＝只读 property 形（V2-47 R1b）：生产应答 d.Completion 为 frozen
    dataclass（属性只读）——协议成员同形只读，GatewayService 结构性兼容
    （enrich 批直接注入网关过 mypy strict）。
    """

    @property
    def content(self) -> str: ...


class Completer(Protocol):
    """精排 completer seam（生产装配＝infra GatewayService——B6 complete 唯一出口）。"""

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> CompletionView: ...


class RetrievalEngine:
    """检索引擎（retrieve 文档面＋graph 图谱面——specs/modules.md retrieval 卡）。

    依赖四缝全部构造注入：library（片段库读面）、embedder（探针向量化）、
    completer（LLM 精排——None＝确定性档不调用）、graph（图谱源——None＝图
    谱面空集回退）。零写路径（INV-2）——全引擎只读。
    """

    def __init__(
        self,
        *,
        library: FragmentLibrary,
        embedder: Embedder,
        completer: Completer | None = None,
        graph: GraphSource | None = None,
        complete_alias: str = COMPLETE_ALIAS,
        recall_k: int = 32,
    ) -> None:
        self._library = library
        self._embedder = embedder
        self._completer = completer
        self._graph = graph
        self._complete_alias = complete_alias
        self._recall_k = max(1, recall_k)

    # ---------- 文档面（双路召回→融合→精排→供给窗） ----------

    async def retrieve(self, need: RetrievalNeed) -> RetrievalBundle:
        """检索供给窗（RetrievalNeed→RetrievalBundle——specs 接口定义节原形）。

        语料装配单点过滤（V2-65 附 A）：`kb_fragment.type='问题块'` 展示面
        专用切片不参赛——不进召回、不进送窗、不进摘要展开语料（召回腿/关键词
        腿/展开语料共用这一份）。展示面消费（端点 9 ingest_additions）不经本
        读面，零影响。
        """
        fragments = [
            f for f in await self._library.fragments()
            if f.frag_type != QUESTION_BLOCK_TYPE
        ]
        if not fragments or not need.question.strip():
            return RetrievalBundle(
                observations=[],
                window_note=build_window_note(0, 0, extra="无可检索语料——空集回退"),
            )
        vector_hits = await self._vector_leg(need.question, fragments)
        keyword_hits = self._keyword_leg(need, fragments)
        fused = rrf_merge(vector_hits, keyword_hits)
        recalled = len(fused)
        ordered = await self._llm_rerank(need.question, fused)
        # 送窗席位分配（V2-45 R1a＋V2-47 R1b＋V2-89b D3）：题眼锚集与表类解锁由
        # 题面词面判定（确定性零模型）——锚保底/表类整行集/节内展开三通道追加席
        # **计入 budget**（超预算即丢并落 over_budget 机读位；节内展开另守
        # SECTION_EXPAND_CAP 上界）。扩席实录随 window_note 留痕。
        supply = supply_window(
            ordered,
            need.budget,
            need.family_hints,
            anchors=anchor_seat_tokens(need.question, need.anchors),
            rowset_question=is_table_rowset_question(need.question),
            corpus=fragments,
        )
        observations = [
            self._fragment_observation(hit) for hit, _fused in supply.window
        ]
        sources: list[str] = []
        for obs in observations:
            if obs.report not in sources:
                sources.append(obs.report)
        extra = _supply_extra_note(supply)
        return RetrievalBundle(
            observations=observations,
            window_note=build_window_note(
                recalled,
                len(observations),
                sources=sources,
                missing=supply.missing_sources,
                extra=extra,
            ),
            recalled=recalled,
            sent=len(observations),
            over_budget=supply.over_budget,
            anchor_seated=len(supply.anchor_seated),
            rowset_added=supply.rowset_added,
            summary_expanded=supply.summary_expanded,
        )

    # ---------- 图谱面（邻域遍历→fail-closed 锚校验→送窗） ----------

    async def graph(self, need: RetrievalNeed) -> RetrievalBundle:
        """图谱面（问句点名实体→一跳邻域边——F45 遍历深度 1 跳，V1 同口径）。

        边出处 fail-closed：chunk_id 锚不上片段台账的边拦截计数（绝不带病出
        窗——V1 图谱链同纪律）；图谱源挂/未接线→空集回退不炸（零异常）。
        """
        if self._graph is None:
            return RetrievalBundle(
                observations=[],
                window_note=build_window_note(0, 0, extra="图谱缝未接线——空集回退（不炸链）"),
            )
        try:
            edges = await self._graph.graph_edges()
        except Exception:  # 图存储不可用不阻断问答（V1 graph_searcher 同口径）
            return RetrievalBundle(
                observations=[],
                window_note=build_window_note(0, 0, extra="图谱源不可用——空集回退（不炸链）"),
            )
        needle = need.question
        matched = [
            edge
            for edge in edges
            if (edge.entity_from and edge.entity_from in needle)
            or (edge.entity_to and edge.entity_to in needle)
        ]
        fragment_ids = {frag.fragment_id for frag in await self._library.fragments()}
        kept: list[GraphEdgeRecord] = []
        dropped = 0
        for edge in matched:
            if edge.chunk_id is not None and edge.chunk_id not in fragment_ids:
                dropped += 1
                continue
            kept.append(edge)
        kept = kept[: need.budget]
        observations = [self._edge_observation(edge) for edge in kept]
        extra = f"拦截失锚边 {dropped} 条（fail-closed）" if dropped else ""
        return RetrievalBundle(
            observations=observations,
            window_note=build_window_note(len(matched), len(observations), extra=extra),
        )

    # ---------- 双路召回腿（V1 kb.index_search_dual 同款两腿） ----------

    async def _vector_leg(self, question: str, fragments: list[FragmentRecord]) -> list[Hit]:
        """向量腿：问题向量化 × 片段向量余弦；embedding 失败按空腿（关键词腿兜底）。"""
        try:
            probe = (await self._embedder.embed([question.strip()]))[0]
        except Exception:
            return []
        scored = [
            Hit(frag, cosine_similarity(probe, frag.embedding), "vector")
            for frag in fragments
            if frag.embedding is not None
        ]
        scored = [hit for hit in scored if hit.score > 0.0]
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[: self._recall_k]

    def _keyword_leg(self, need: RetrievalNeed, fragments: list[FragmentRecord]) -> list[Hit]:
        """关键词腿：应用层 BM25（归一 0~1）＋编号保送（问句 token/锚定名逐字命中）。

        anchors 并入检索单元与保送通道（@ 锚定资产名直取——V1 S1 锚定材料语义
        的检索侧投影；空 anchors 时与 V1 问句单源同形）。

        检索单元＝富化索引文本（V2-47 R1b——切片带上下文前缀、摘要节点照入；
        enriched_index_text 单点）：问句点名的报告名/章节路径可在前缀逐字命中，
        编号保送的词面判据同尺（前缀在索引文本内——保送与打分同一文本面）。
        """
        query_text = need.question.strip()
        if need.anchors:
            query_text = query_text + " " + " ".join(need.anchors)
        eligible = [frag for frag in fragments if frag.text]
        index_texts = [enriched_index_text(frag) for frag in eligible]
        raw = bm25_scores(query_text, index_texts)
        scored = sorted(
            (
                (Hit(frag, normalize_bm25(score), "keyword"), normalize_bm25(score))
                for frag, score in zip(eligible, raw, strict=True)
            ),
            key=lambda pair: pair[1],
            reverse=True,
        )
        ranked = [entry for entry in scored if entry[1] > 0.0][: self._recall_k]
        tokens = alnum_tokens(need.question) + [a for a in need.anchors if a.strip()]
        ranked = promote_entity_hits(
            ranked, list(scored), tokens,
            top_k=self._recall_k, text_of=lambda hit: enriched_index_text(hit.fragment),
        )
        return [hit for hit, _score in ranked]

    # ---------- LLM 精排（至多两次调用——失败回退融合序，不炸链） ----------

    async def _llm_rerank(
        self, question: str, fused: list[tuple[Hit, float]]
    ) -> list[tuple[Hit, float]]:
        """精排编排：批量排序（重排不改分）＋来源置信度（只重排来源块序）。

        completer 未接线/单候选→直接融合序（确定性档）；两次调用任一失败按
        各自回退语义放行（specs 行为约定 1——供给窗硬规则不受 LLM 影响）。
        """
        if self._completer is None or len(fused) <= 1:
            return list(fused)
        ordered = await self._batch_order(question, fused)
        confidence = await self._doc_confidence(question, ordered)
        if confidence is None:
            return ordered
        return _reorder_by_source_confidence(ordered, confidence)

    async def _batch_order(
        self, question: str, fused: list[tuple[Hit, float]]
    ) -> list[tuple[Hit, float]]:
        """片段批量精排（一次调用）：问句＋编号候选清单→相关度排序编号表。

        只重排不丢弃——编号表未覆盖的候选按原序追加在尾（parse_rank_order 半
        边）；调用失败/解析失败/无出口 → 原融合序放行（W-F34-2 回退不炸链）。
        """
        assert self._completer is not None
        lines = "\n".join(
            f"[{i}] {_candidate_place(hit.fragment)}｜{snippet_window(hit.fragment.text, question)}"
            for i, (hit, _fused) in enumerate(fused, 1)
        )
        try:
            completion = await self._completer.complete(
                self._complete_alias,
                [
                    {"role": "system", "content": BATCH_RERANK_SYSTEM_PROMPT},
                    {"role": "user", "content": BATCH_RERANK_USER_TEMPLATE.format(
                        question=question, lines=lines)},
                ],
                caller=CALLER_RERANK,
            )
            order = parse_rank_order(str(completion.content), len(fused))
        except Exception:  # 调用/解析失败按合同回退，不炸链
            return list(fused)
        return [fused[i] for i in order]

    async def _doc_confidence(
        self, question: str, ordered: list[tuple[Hit, float]]
    ) -> dict[str, float] | None:
        """文档来源置信度（一次调用）：候选按报告分组，逐来源给 0–10 相关度。

        每来源出示组内前 3 支片段摘录（V1——单样例打分有采样偏）；解析失败/
        缺任一来源分/无出口 → None（置信度弃用，来源块序保持融合序，不炸链）。
        """
        assert self._completer is not None
        if not ordered:
            return None
        groups: dict[str, list[Hit]] = {}
        for hit, _fused in ordered:
            groups.setdefault(hit.fragment.report_id or "?", []).append(hit)
        lines = "\n".join(
            f"[{i}] {group[0].fragment.report[:36]}｜"
            + " ｜ ".join(
                snippet_window(hit.fragment.text, question, width=DOC_CONF_SAMPLE_WIDTH)
                for hit in group[:DOC_CONF_SAMPLES]
            )
            for i, group in enumerate(groups.values(), 1)
        )
        try:
            completion = await self._completer.complete(
                self._complete_alias,
                [
                    {"role": "system", "content": DOC_CONF_SYSTEM_PROMPT},
                    {"role": "user", "content": DOC_CONF_USER_TEMPLATE.format(
                        question=question, lines=lines)},
                ],
                caller=CALLER_CONFIDENCE,
            )
            raw = parse_confidence_scores(str(completion.content), len(groups))
        except Exception:
            return None
        if raw is None:
            return None
        return {
            report_id: raw[i] for i, report_id in enumerate(groups, 1)
        }

    # ---------- 行投影（Hit/GraphEdgeRecord→Observation——出处链单点） ----------

    def _fragment_observation(self, hit: Hit) -> Observation:
        frag = hit.fragment
        locator: dict[str, Any] = {
            "library": frag.library,
            "report": frag.report,
            "section": frag.section or "",
            "fragment_id": frag.fragment_id,
        }
        if frag.node_kind != NODE_SLICE:
            # 摘要节点机读位（V2-47 R1b——切片 locator 不带此键，旧形零漂移）。
            locator["node_kind"] = frag.node_kind
        if _is_table_bearing(frag.text):
            # 表格承载机读位（V2-93——L3 表格保底席判据；判据单点＝`domain._is_table_bearing`，
            # 本处只打标记、不另立第二份判定；非表格支不带此键，旧形零漂移）。
            locator["table_bearing"] = True
        return Observation(
            kind="fragment",
            text=frag.text,
            snippet=frag.text[:SNIPPET_CHARS],
            score=hit.score,  # 恒原始腿分——精排只重排不改分（V1 同尺）
            leg=hit.leg,
            family=frag.family,
            fragment_id=frag.fragment_id,
            report_id=frag.report_id,
            report=frag.report,
            library_id=frag.library_id,
            library=frag.library,
            section=frag.section,
            locator=locator,
            well=frag.well,
        )

    def _edge_observation(self, edge: GraphEdgeRecord) -> Observation:
        text = edge.evidence or f"{edge.entity_from} {edge.rel} {edge.entity_to}"
        return Observation(
            kind="graph",
            text=text,
            snippet=text[:SNIPPET_CHARS],
            score=1.0,  # 图谱链无精排打分——V1 图谱证据同值
            leg="graph",
            family=edge.family,
            fragment_id=edge.chunk_id,
            report_id=edge.report_id,
            report=edge.report,
            library_id=edge.library_id,
            library=edge.library,
            section=GRAPH_SECTION,
            locator={
                "library": edge.library,
                "report": edge.report,
                "section": GRAPH_SECTION,
                "fragment_id": edge.chunk_id or "",
            },
        )


def _candidate_place(frag: FragmentRecord) -> str:
    """候选出处名（报告 · 章节——V1 精排清单 place 同形）。"""
    return f"{frag.report} · {frag.section}" if frag.section else frag.report


def _supply_extra_note(supply: WindowSupply) -> str:
    """扩席实录段（window_note extra：锚保底/表类整组/摘要展开留痕）。

    数字如实：用进答案数 M 已按实走支数计数（build_window_note 主段），本段只
    声明扩席来源与增量——无扩席＝空串（零漂移）。三段措辞＝用户语（V2-82e）：
    内部行话（锚保底/整行集/展开补席）不上材料段，数字全部参数化。V2-89b 起
    补席计入 budget（真封顶）——本段是「实际入窗」的实录，非「曾尝试追加」。
    """
    segments: list[str] = []
    if supply.anchor_seated:
        segments.append(
            "以下条目因直接命中提问关键词获得保留：" + "、".join(supply.anchor_seated)
        )
    if supply.rowset_added:
        segments.append(
            f"目标表格的整组数据行已进窗（+{supply.rowset_added} 条，不占送入答案的数量）"
        )
    if supply.summary_expanded:
        segments.append(f"命中的章节摘要已展开为节内材料（+{supply.summary_expanded} 条）")
    return "；".join(segments)


def _reorder_by_source_confidence(
    ordered: list[tuple[Hit, float]], confidence: dict[str, float]
) -> list[tuple[Hit, float]]:
    """来源块重排（置信度降序；块内原序不动——供给窗硬规则在其下游仍生效）。

    同窗规则在供给层硬编码（supply_window）——置信度只影响各族内来源的出场
    序，不能增删任何来源的代表席（specs 风险节：同窗不依赖 LLM 自觉）。
    """
    blocks: dict[str, list[tuple[Hit, float]]] = {}
    block_order: list[str] = []
    for pair in ordered:
        key = pair[0].fragment.report_id or "?"
        if key not in blocks:
            blocks[key] = []
            block_order.append(key)
        blocks[key].append(pair)
    ranked_blocks = sorted(
        block_order, key=lambda key: confidence.get(key, 0.0), reverse=True
    )
    return [pair for key in ranked_blocks for pair in blocks[key]]

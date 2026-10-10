"""V2-47 R1b 切片富化——索引管线富化阶段钉测（tickets/v2/V2-47-R1b切片富化.md）。

票面钉逐条载体：
- 富化钉：前缀逐字（报告名/章节路径——context_prefix）＋节级摘要节点可检索
  可展开（engine 双层路由：摘要节点独立进双路召回＋命中→节内切片补席展开）；
- 幂等钉：富化重跑零重复节点（确定性 node id＋upsert 语义）＋旧索引可重建
  （富化写零触碰 kb_* 原表——sqlite 底座逐格断言）；
- 全库富化/记账面：enrich_index 编排（切片重嵌 db 型＋摘要生成 complete 面）
  账本数字如实（corpus/overlay/clusters/written/failed/calls/tokens）。

装配：内存库＋LocalHashEmbedder＋剧本 completer（零真网关——真批归富化批与
评审后针对性测试，本文件全部离线确定性）。
"""

from dataclasses import replace
from pathlib import Path
from typing import Any

from sqlalchemy import text

from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.retrieval import (
    NODE_SECTION_SUMMARY,
    NODE_SLICE,
    SUMMARY_MIN_COVER,
    EnrichedFragmentLibrary,
    FragmentRecord,
    InMemoryEnrichStore,
    InMemoryFragmentLibrary,
    LocalHashEmbedder,
    PgEnrichStore,
    RetrievalEngine,
    RetrievalNeed,
    build_summary_text,
    cluster_sections,
    context_prefix,
    enrich_index,
    enriched_index_text,
    ensure_enrich_tables,
    section_root,
    summary_node_id,
)

# ---------- fixture：两报告小库（章节路径取真库形状——全路径 ＞ 分隔） ----------

_LIB_A = ("lib-a", "渤中34-5完井工程库", "completion")
_LIB_Y = ("lib-y", "渤中34-8完井工程库", "completion")
_RPT_A = ("rpt-a", "《A-W11井完井工程报告》")
_RPT_Y = ("rpt-y", "《Y-21井完井工程报告》")

_SEC_A_SAND = "章节 04 第四章 防砂设计与实施 ＞ 4.2 防砂方式与参数"
_SEC_A_PERF = "章节 03 第三章 射孔设计 ＞ 3.2 射孔参数"
_SEC_Y_SAND = "章节 04 第四章 防砂设计与实施 ＞ 4.2 防砂方式与参数"


def _frag(
    fid: str,
    lib: tuple[str, str, str],
    rpt: tuple[str, str],
    section: str,
    txt: str,
) -> FragmentRecord:
    return FragmentRecord(
        fragment_id=fid,
        report_id=rpt[0],
        report=rpt[1],
        section=section,
        library_id=lib[0],
        library=lib[1],
        family=lib[2],
        text=txt,
    )


def _corpus() -> list[FragmentRecord]:
    """六支切片：A 报告防砂节 2 支＋射孔节 1 支，Y 报告防砂节 2 支＋结论节 1 支。"""
    return [
        _frag("f-a1", _LIB_A, _RPT_A, _SEC_A_SAND,
              "防砂方式：精密冲缝筛管适度防砂，防砂精度 150 微米，未砾石充填。"),
        _frag("f-a2", _LIB_A, _RPT_A, _SEC_A_SAND,
              "出砂风险评估：地层出砂趋势中等，筛管防砂与井况匹配。"),
        _frag("f-a3", _LIB_A, _RPT_A, _SEC_A_PERF,
              "射孔参数：孔密 16 孔/米，全井射孔总厚度 28.0 米，发射率 100%。"),
        _frag("f-y1", _LIB_Y, _RPT_Y, _SEC_Y_SAND,
              "防砂方式：精密冲缝筛管适度防砂，防砂精度 175 微米。"),
        _frag("f-y2", _LIB_Y, _RPT_Y, _SEC_Y_SAND,
              "筛管目数与储层砂粒度分布匹配论证。"),
        _frag("f-y3", _LIB_Y, _RPT_Y, "章节 09 第九章 结论与建议",
              "酸化解堵使采油指数提高，储层适应性验证。"),
    ]


async def _embedded_corpus() -> list[FragmentRecord]:
    embedder = LocalHashEmbedder()
    seeds = _corpus()
    vectors = await embedder.embed([seed.text for seed in seeds])
    return [
        replace(seed, embedding=vector)
        for seed, vector in zip(seeds, vectors, strict=True)
    ]


class _ScriptCompleter:
    """摘要 completer 桩：按章节路径发剧本正文；记录调用面（alias/caller/消息）。"""

    def __init__(self, bodies: dict[str, str], fail_keys: set[str] | None = None) -> None:
        self._bodies = bodies
        self._fail = fail_keys or set()
        self.calls: list[tuple[str, str, str]] = []  # (alias, caller, user 内容)

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        user = messages[-1]["content"]
        self.calls.append((alias, caller, user))
        for key, body in self._bodies.items():
            if key in user:
                if key in self._fail:
                    raise RuntimeError("上游摘要挂（测试桩）")
                if key == "_garbage":
                    return type("_Reply", (), {"content": "抱歉无法作答"})()
                return type("_Reply", (), {"content": body})()
        raise RuntimeError(f"剧本缺key：{user[:40]}")

    def add_garbage_key(self) -> None:
        self._bodies["_garbage"] = ""


# ---------- 富化钉半边：前缀逐字（报告名/章节路径） ----------


def test_context_prefix_verbatim() -> None:
    """前缀逐字钉：〔本段节选自〈报告名〉·〈章节路径〉〕——报告名与全路径在位。"""
    prefix = context_prefix(_RPT_A[1], _SEC_A_SAND)
    assert prefix == f"〔本段节选自{_RPT_A[1]}·{_SEC_A_SAND}〕"
    assert "A-W11井完井工程报告" in prefix  # 报告名逐字
    assert "4.2 防砂方式与参数" in prefix  # 章节路径逐字（全路径）


def test_context_prefix_without_section() -> None:
    """无章节路径切片：前缀只带报告名（格式同源——不发明章节）。"""
    assert context_prefix(_RPT_Y[1], None) == f"〔本段节选自{_RPT_Y[1]}〕"


def test_section_root_extraction() -> None:
    """节聚类键＝章节路径顶层段（＞ 前首段）——None 原样返回 None。"""
    assert section_root(_SEC_A_SAND) == "章节 04 第四章 防砂设计与实施"
    assert section_root("正文 ＞ 4.1 W-22 井抽油杆断") == "正文"
    assert section_root("全文档摘要") == "全文档摘要"
    assert section_root(None) is None


def test_enriched_index_text_slice_and_summary() -> None:
    """索引文本：切片＝前缀拼接原文（BM25/向量双受益）；摘要节点＝原文照入。"""
    frag = _frag("f-a1", _LIB_A, _RPT_A, _SEC_A_SAND, "筛管精度 150 微米。")
    expected = f"〔本段节选自{_RPT_A[1]}·{_SEC_A_SAND}〕筛管精度 150 微米。"
    assert enriched_index_text(frag) == expected
    node = replace(
        frag, fragment_id="ensum-x", node_kind=NODE_SECTION_SUMMARY, text="〔节级摘要｜…〕要点"
    )
    assert enriched_index_text(node) == "〔节级摘要｜…〕要点"


def test_summary_node_id_deterministic() -> None:
    """节点身份确定性：同（报告，节）同 id（幂等半边——重跑同键不新增）。"""
    first = summary_node_id("rpt-a", "章节 04 第四章 防砂设计与实施")
    assert first == summary_node_id("rpt-a", "章节 04 第四章 防砂设计与实施")
    assert first != summary_node_id("rpt-y", "章节 04 第四章 防砂设计与实施")
    assert first.startswith("ensum-")


def test_cluster_sections_groups_and_order() -> None:
    """节聚类：按（报告，顶层节）分组、成员保持语料序、簇序确定性。"""
    clusters = cluster_sections(_corpus())
    keys = [(c.report_id, c.root) for c in clusters]
    assert keys == sorted(keys)  # 簇序确定性（排序序——重跑同构）
    by_key = {(c.report_id, c.root): c for c in clusters}
    sand_a = by_key[("rpt-a", "章节 04 第四章 防砂设计与实施")]
    assert sand_a.members == ("f-a1", "f-a2")  # 成员保持语料序
    assert sand_a.report == _RPT_A[1] and sand_a.family == "completion"
    assert len(clusters) == 4  # A 防砂／A 射孔／Y 防砂／Y 结论


def test_build_summary_text_contains_path_and_covers() -> None:
    """摘要节点文本钉：含节路径＋覆盖支数＋LLM 要点正文。"""
    clusters = {c.report_id: c for c in cluster_sections(_corpus())}
    cluster = next(c for c in clusters.values() if c.members == ("f-a1", "f-a2"))
    text = build_summary_text(cluster, "本节给出筛管防砂选型与精度论证。")
    header = "〔节级摘要｜《A-W11井完井工程报告》·章节 04 第四章 防砂设计与实施｜覆盖 2 支切片〕"
    assert text.startswith(header)
    assert "筛管防砂选型" in text  # 要点正文拼接在位


# ---------- 富化钉半边：摘要生成（complete 面——caller 归因） ----------


async def test_generate_summaries_in_enrich_index_records_caller() -> None:
    """摘要生成走 complete 面：alias/caller 逐调用在案；正文进节点文本。

    consider 1（P-046b 采纳）：仅 cover_count≥2 簇生成摘要——A/Y 防砂两簇，
    射孔/结论单成员簇零调用零节点。
    """
    store = InMemoryEnrichStore()
    completer = _ScriptCompleter({
        "章节 04 第四章 防砂设计与实施": "防砂精度选型要点。",
        "章节 03 第三章 射孔设计": "射孔参数要点。",
        "章节 09 第九章 结论与建议": "结论要点。",
    })
    corpus = await _embedded_corpus()
    ledger = await enrich_index(
        corpus=corpus, store=store, completer=completer, embedder=LocalHashEmbedder(),
    )
    assert ledger.complete_calls == len(completer.calls) == 2  # 仅两防砂簇
    assert all(caller == "agent_v2.retrieval.enrich" for _alias, caller, _u in completer.calls)
    _overlays, nodes = await store.snapshot()
    assert {n.section for n in nodes} == {"章节 04 第四章 防砂设计与实施"}
    assert {n.report_id for n in nodes} == {"rpt-a", "rpt-y"}
    y_sand = next(n for n in nodes if n.report_id == "rpt-y")
    assert "防砂精度选型要点" in y_sand.text  # 剧本正文进节点
    assert y_sand.cover_count == 2 and y_sand.source_ids == ("f-y1", "f-y2")
    assert ledger.summaries_failed == ()
    assert ledger.clusters_single_cover == 2  # 射孔/结论单成员簇跳过如实入账


async def test_single_member_cluster_gets_no_summary_node() -> None:
    """consider 1 钉（cover_count≥2）：单成员簇无摘要节点、零模型调用。

    「单成员簇 61% 摘要增量存疑」（P-046 中途审查 C1）的落地钉：射孔（1 支）/
    结论（1 支）两簇不聚类不摘要——成员不足簇不生成摘要节点。
    """
    store = InMemoryEnrichStore()
    completer = _ScriptCompleter({
        "章节 04 第四章 防砂设计与实施": "防砂要点。",
        "章节 03 第三章 射孔设计": "射孔要点。",
        "章节 09 第九章 结论与建议": "结论要点。",
    })
    ledger = await enrich_index(
        corpus=await _embedded_corpus(), store=store,
        completer=completer, embedder=LocalHashEmbedder(),
    )
    _overlays, nodes = await store.snapshot()
    assert all(n.cover_count >= SUMMARY_MIN_COVER for n in nodes)
    assert {n.section for n in nodes} == {"章节 04 第四章 防砂设计与实施"}
    assert len(completer.calls) == 2  # 单成员簇零 complete 调用（零模型成本）
    assert ledger.clusters_total == 4
    assert ledger.clusters_single_cover == 2
    assert ledger.summaries_written == len(nodes) == 2


async def test_summary_failure_skips_and_reports() -> None:
    """单簇摘要失败：跳过不炸批，失败簇键入账本（重跑补齐——幂等面）。"""
    store = InMemoryEnrichStore()
    completer = _ScriptCompleter(
        {
            "《A-W11井完井工程报告》": "防砂精度选型要点。",
            "《Y-21井完井工程报告》": "螺杆泵举升参数论证要点。",
        },
        fail_keys={"《A-W11井完井工程报告》"},
    )
    ledger = await enrich_index(
        corpus=await _embedded_corpus(), store=store,
        completer=completer, embedder=LocalHashEmbedder(),
    )
    _overlays, nodes = await store.snapshot()
    assert len(nodes) == 1  # 失败簇无节点
    assert ledger.summaries_written == 1
    assert ledger.summaries_failed == ("《A-W11井完井工程报告》·章节 04 第四章 防砂设计与实施",)
    assert ledger.complete_calls == 1


# ---------- 幂等钉：重跑零重复节点＋旧索引可重建 ----------


async def test_enrich_rerun_zero_duplicate_nodes() -> None:
    """幂等钉：同库富化重跑——节点数不变、id 全等（确定性身份＋upsert）。"""
    store = InMemoryEnrichStore()
    completer = _ScriptCompleter({
        "章节 04 第四章 防砂设计与实施": "防砂要点。",
        "章节 03 第三章 射孔设计": "射孔要点。",
        "章节 09 第九章 结论与建议": "结论要点。",
    })
    corpus = await _embedded_corpus()
    rerun = dict(corpus=corpus, store=store, completer=completer, embedder=LocalHashEmbedder())
    await enrich_index(**rerun)
    first_overlays, first_nodes = await store.snapshot()
    await enrich_index(**rerun)
    second_overlays, second_nodes = await store.snapshot()
    assert len(second_nodes) == len(first_nodes) == 2  # 仅 cover_count≥2 簇
    assert [n.node_id for n in second_nodes] == [n.node_id for n in first_nodes]
    ids = {"f-a1", "f-a2", "f-a3", "f-y1", "f-y2", "f-y3"}
    assert set(second_overlays) == set(first_overlays) == ids


async def test_pg_enrich_store_sqlite_roundtrip_and_kb_untouched(tmp_path: Path) -> None:
    """sqlite 底座：ensure 幂等＋upsert/snapshot 往返；kb_* 原表零触碰（旧索引可重建）。"""
    db_path = tmp_path / "enrich.db"
    specs = [_spec(db_path)]
    manager = ConnectionManager(specs)
    try:
        engine = manager.engine()
        await ensure_enrich_tables(engine)
        await ensure_enrich_tables(engine)  # 幂等：二次建表不炸
        async with manager.session() as session:
            await session.execute(text(
                "CREATE TABLE IF NOT EXISTS kb_fragment ("
                "id TEXT PRIMARY KEY, report_id TEXT NOT NULL, section TEXT,"
                "is_parent_only INTEGER NOT NULL, embedding TEXT)"
            ))
            await session.execute(text(
                "INSERT INTO kb_fragment VALUES ('f-a1', 'rpt-a', 'sec', 0, '[0.5,0.5]')"
            ))
        store = PgEnrichStore(specs)
        node = _summary_node_fixture()
        await store.upsert([_overlay_fixture("f-a1")], [node])
        await store.upsert([_overlay_fixture("f-a1")], [node])  # 重跑同键
        overlays, nodes = await store.snapshot()
        assert overlays == {"f-a1": [0.1, 0.2]}
        assert len(nodes) == 1 and nodes[0].node_id == node.node_id  # 零重复
        assert nodes[0].text == node.text and nodes[0].cover_count == 2
        async with manager.readonly() as session:
            row = (await session.execute(text(
                "SELECT embedding FROM kb_fragment WHERE id='f-a1'"
            ))).scalar_one()
        assert row == "[0.5,0.5]"  # 旧索引（原向量列）逐字未动
        count = (await _table_count(manager)).scalar()
        assert count == 2  # 重跑后富化表恰 2 行（1 overlay＋1 node）
    finally:
        await manager.dispose()


async def test_pg_enrich_store_version_and_prune(tmp_path: Path) -> None:
    """S1 版本令牌＋consider 1 陈旧清理（sqlite 底座）。

    version 随写入变更、空 upsert 不变；prune 只删 keep 外摘要行、overlay 行
    零触碰（规则变更重跑的终态幂等半边）。
    """
    db_path = tmp_path / "enrich-prune.db"
    specs = [_spec(db_path)]
    manager = ConnectionManager(specs)
    try:
        await ensure_enrich_tables(manager.engine())
        store = PgEnrichStore(specs)
        node = _summary_node_fixture()
        await store.upsert([_overlay_fixture("f-a1")], [node])
        version_first = await store.version()
        await store.upsert([], [])  # 空入参零行——令牌不变
        assert await store.version() == version_first
        await store.upsert([_overlay_fixture("f-a2")], [])
        assert await store.version() != version_first
        # prune：keep 内零删除；keep 空＝清空摘要面，overlay 行不受影响。
        assert await store.prune_summaries({node.node_id}) == 0
        overlays, nodes = await store.snapshot()
        assert len(nodes) == 1 and set(overlays) == {"f-a1", "f-a2"}
        assert await store.prune_summaries(set()) == 1
        overlays, nodes = await store.snapshot()
        assert nodes == [] and set(overlays) == {"f-a1", "f-a2"}
    finally:
        await manager.dispose()


async def _table_count(manager: ConnectionManager) -> Any:
    async with manager.readonly() as session:
        return await session.execute(text("SELECT COUNT(*) FROM kb_retrieval_enrich"))


def _spec(db_path: Path) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(db_path), user="", password="", pool_size=2, max_overflow=1,
    )


def _overlay_fixture(fid: str) -> Any:
    from appv2.retrieval import SliceOverlay

    return SliceOverlay(fragment_id=fid, embedding=[0.1, 0.2], model="local-hash")


def _summary_node_fixture() -> Any:
    from appv2.retrieval import SummaryNode

    return SummaryNode(
        node_id=summary_node_id("rpt-a", "章节 04"),
        report_id="rpt-a",
        report=_RPT_A[1],
        library_id=_LIB_A[0],
        library=_LIB_A[1],
        family=_LIB_A[2],
        section="章节 04",
        text="〔节级摘要｜…〕要点",
        cover_count=2,
        source_ids=("f-a1", "f-a2"),
        embedding=[0.3, 0.4],
        model="local-hash",
    )


# ---------- 装配钉：EnrichedFragmentLibrary（overlay 覆写＋摘要节点追加） ----------


async def test_enriched_library_overlay_and_summary_nodes() -> None:
    """内库向量被 overlay 覆写（不毁内库行）；摘要节点以 node_kind 追加入语料。"""
    inner = InMemoryFragmentLibrary(await _embedded_corpus())
    store = InMemoryEnrichStore()
    node = _summary_node_fixture()
    await store.upsert([_overlay_fixture("f-a1")], [node])
    library = EnrichedFragmentLibrary(inner, store)
    frags = {f.fragment_id: f for f in await library.fragments()}
    assert frags["f-a1"].embedding == [0.1, 0.2]  # overlay 覆写
    assert frags["f-a2"].embedding != [0.1, 0.2] and frags["f-a2"].embedding is not None
    summary = [f for f in frags.values() if f.node_kind == NODE_SECTION_SUMMARY]
    assert len(summary) == 1 and summary[0].fragment_id == node.node_id
    assert summary[0].report == _RPT_A[1] and summary[0].family == "completion"  # 出处链随行
    inner_rows = {f.fragment_id: f for f in await inner.fragments()}
    assert inner_rows["f-a1"].embedding != [0.1, 0.2]  # 内库原向量未动（旧索引在库）


async def test_enriched_library_empty_store_passthrough() -> None:
    """空富化库＝原语料原样透传（零摘要节点、零 overlay——上线未富化态零漂移）。"""
    inner = InMemoryFragmentLibrary(await _embedded_corpus())
    library = EnrichedFragmentLibrary(inner, InMemoryEnrichStore())
    frags = await library.fragments()
    assert [f.node_kind for f in frags] == [NODE_SLICE] * 6


class _CountingEnrichStore(InMemoryEnrichStore):
    """S1 时延钉桩：version/snapshot 调用计数（读面收敛实证面）。"""

    def __init__(self) -> None:
        super().__init__()
        self.version_calls = 0
        self.snapshot_calls = 0

    async def version(self) -> str:
        self.version_calls += 1
        return await super().version()

    async def snapshot(self):  # type: ignore[no-untyped-def]
        self.snapshot_calls += 1
        return await super().snapshot()


async def test_enriched_library_snapshot_cached_by_version() -> None:
    """S1 时延钉：同版本重复读零全量快照——retrieve 读面只付版本查询。

    治理前每次 retrieve 付一次全表向量读（197 行×1536 维≈+227ms/retrieve）；
    治理后读面＝version() 廉价查询×1，snapshot() 仅在富化库变更（upsert→
    令牌变）后首次重读——新索引及时可见。
    """
    store = _CountingEnrichStore()
    await store.upsert([_overlay_fixture("f-a1")], [_summary_node_fixture()])
    library = EnrichedFragmentLibrary(
        InMemoryFragmentLibrary(await _embedded_corpus()), store
    )
    first = await library.fragments()
    assert store.snapshot_calls == 1 and store.version_calls == 1
    second = await library.fragments()
    assert store.snapshot_calls == 1  # 缓存命中——零全量向量读
    assert [f.fragment_id for f in first] == [f.fragment_id for f in second]
    # 版本变更（富化批落库）→ 快照失效重读（一次）。
    await store.upsert([_overlay_fixture("f-a2")], [])
    await library.fragments()
    assert store.snapshot_calls == 2 and store.version_calls == 3  # 三次读各一次版本查询


# ---------- 引擎面：双层路由（前缀进 BM25＋摘要命中→节内展开） ----------


async def _engine_with_enrich(
    store: Any,
) -> tuple[RetrievalEngine, InMemoryFragmentLibrary]:
    inner = InMemoryFragmentLibrary(await _embedded_corpus())
    engine = RetrievalEngine(
        library=EnrichedFragmentLibrary(inner, store), embedder=LocalHashEmbedder()
    )
    return engine, inner


async def test_engine_prefix_only_match_reaches_slice() -> None:
    """找得准钉：问句 token 只落前缀（报告名/章节路径）也命中切片——前缀进 BM25。"""
    engine, _inner = await _engine_with_enrich(InMemoryEnrichStore())
    # f-y2 正文只有「筛管目数…匹配论证」——「4.2」与「Y-21」都只在其前缀里。
    bundle = await engine.retrieve(
        RetrievalNeed(question="Y-21井 4.2 筛管目数论证", budget=3)
    )
    ids = {obs.fragment_id for obs in bundle.observations}
    assert "f-y2" in ids  # 前缀逐字命中把目标切片带进窗


async def test_engine_summary_hit_expands_section_slices() -> None:
    """摘要命中→节内展开：摘要节点进窗后其节内切片补席（含未召回支——找得准）。"""
    store = InMemoryEnrichStore()
    completer = _ScriptCompleter({
        "章节 04 第四章 防砂设计与实施": "螺杆泵举升参数论证要点。",
        "章节 03 第三章 射孔设计": "射孔要点。",
        "章节 09 第九章 结论与建议": "结论要点。",
    })
    corpus = await _embedded_corpus()
    await enrich_index(
        corpus=corpus, store=store, completer=completer, embedder=LocalHashEmbedder()
    )
    engine, inner = await _engine_with_enrich(store)
    # 问针「螺杆泵举升参数」只出现在摘要正文（切片正文零词面重叠）——摘要腿命中。
    bundle = await engine.retrieve(
        RetrievalNeed(question="螺杆泵举升参数论证", budget=2)
    )
    kinds = [
        "summary" if obs.fragment_id.startswith("ensum-") else "slice"
        for obs in bundle.observations
    ]
    assert "summary" in kinds  # 摘要节点独立可检索（可检索钉）
    sections = {obs.section for obs in bundle.observations if obs.fragment_id.startswith("ensum-")}
    expanded = [
        obs for obs in bundle.observations
        if obs.fragment_id in {"f-a1", "f-a2", "f-y1", "f-y2"}
    ]
    assert expanded, "摘要命中后其节内切片应补席展开"
    # S2 清钉（P-046b）真实谓词：每支展开切片的节根 ∈ 窗内摘要节节集——
    # 展开按簇取材，非摘要节切片不得借展开进窗（原「or o.fragment_id」恒真摘除）。
    assert all(section_root(o.section) in sections for o in expanded)
    assert "节级摘要展开" in bundle.window_note  # 扩席实录如实（window_note extra 段）
    # S2 清钉（P-046b）真实谓词：展开池＝全节语料（含未召回支）——对照无富化
    # 引擎的同问基线窗，展开新席至少一支在基线窗外（词面零重叠切片不因自身
    # 弱被拒——原「or True」恒真摘除）。
    baseline = await RetrievalEngine(
        library=inner, embedder=LocalHashEmbedder()
    ).retrieve(RetrievalNeed(question="螺杆泵举升参数论证", budget=2))
    baseline_ids = {obs.fragment_id for obs in baseline.observations}
    expanded_ids = {obs.fragment_id for obs in expanded}
    assert expanded_ids - baseline_ids, "展开池应含召回未及的节内切片（未召回支）"


async def test_engine_locator_marks_summary_nodes() -> None:
    """观察面：摘要节点 locator 携 node_kind 机读位；切片 locator 无此键（零漂移）。"""
    store = InMemoryEnrichStore()
    completer = _ScriptCompleter({
        "章节 04 第四章 防砂设计与实施": "防砂要点。",
        "章节 03 第三章 射孔设计": "射孔要点。",
        "章节 09 第九章 结论与建议": "结论要点。",
    })
    await enrich_index(
        corpus=await _embedded_corpus(), store=store,
        completer=completer, embedder=LocalHashEmbedder(),
    )
    engine, _inner = await _engine_with_enrich(store)
    bundle = await engine.retrieve(RetrievalNeed(question="防砂方式与精度", budget=6))
    summary_locs = [
        obs.locator for obs in bundle.observations if obs.fragment_id.startswith("ensum-")
    ]
    slice_locs = [
        obs.locator for obs in bundle.observations if not obs.fragment_id.startswith("ensum-")
    ]
    assert summary_locs
    assert all(loc.get("node_kind") == NODE_SECTION_SUMMARY for loc in summary_locs)
    assert all("node_kind" not in loc for loc in slice_locs)


async def test_engine_zero_drift_without_enrich() -> None:
    """零漂移钉：空富化库——window_note 无摘要展开段、观察全为切片（旧形逐字）。"""
    engine, _inner = await _engine_with_enrich(InMemoryEnrichStore())
    bundle = await engine.retrieve(RetrievalNeed(question="防砂方式与精度", budget=4))
    assert all(obs.fragment_id.startswith("f-") for obs in bundle.observations)
    assert "节级摘要展开" not in bundle.window_note
    assert bundle.window_note.startswith("召回 ") and "送窗" in bundle.window_note


# ---------- 编排账本：全库富化数字如实 ----------


async def test_enrich_index_ledger_numbers() -> None:
    """账本钉：corpus/overlay/clusters/written/complete_calls 逐项与实跑一致。

    corpus 全量入重嵌面（读面 pg_source 已滤父块——is_parent_only 不对外寻址
    是生产读面设计态，本缝不重复判）。
    """
    store = InMemoryEnrichStore()
    completer = _ScriptCompleter({
        "章节 04 第四章 防砂设计与实施": "防砂要点。",
        "章节 03 第三章 射孔设计": "射孔要点。",
        "章节 09 第九章 结论与建议": "结论要点。",
    })
    corpus = await _embedded_corpus()
    ledger = await enrich_index(
        corpus=corpus, store=store,
        completer=completer, embedder=LocalHashEmbedder(),
    )
    assert ledger.corpus_total == 6  # 全库行数如实
    assert ledger.corpus_embedded == 6  # 全量重嵌（overlay 覆写语义——不止缺向量行）
    assert ledger.clusters_total == 4
    assert ledger.clusters_single_cover == 2  # consider 1——单成员簇跳过如实入账
    assert ledger.summaries_written == 2
    assert ledger.overlay_written == 6
    assert ledger.complete_calls == 2
    _overlays, nodes = await store.snapshot()
    assert len(nodes) == 2 and all(n.embedding is not None for n in nodes)  # 节点全带向量

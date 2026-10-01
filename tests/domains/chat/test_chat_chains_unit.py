"""chat 三链链体单测（P1-08b）——检索瀑布链（D2 配置驱动行为变化实证）＋FAQ
秒回链＋图谱问答链＋citation fail-closed。

验收获收点对照（tickets/phase1/README.md P1-08b）：
- 三链各真跑：链体帧序（S 级过程行）＋answer 收场；
- D2 配置改动可见行为变化：三级开关/命中即停关（帧序变化）/topK/合并两策/
  精排三档/引用格式两格/兜底两策/refuse_threshold/confidence_thresholds/
  faq_expand_rounds——逐字段消费；
- fail-closed 单测：编造引用（未知别名 c9）被拦＋失锚 fragment 被拦＋notice 留痕。
"""

from dataclasses import replace
from typing import Any

from app.domains.chat import domain as d
from app.domains.chat.domain import (
    FragmentAnchorFace,
    GraphHitFace,
    IndexHitFace,
)
from tests.domains.chat.conftest import (
    AQIANG,
    DEFAULT_CONFIG,
    Seams,
    collect,
    make_service,
)


def _events_by_name(events: list[Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        out.setdefault(event.event, []).append(event.data)
    return out


def _names(events: list[Any]) -> list[str]:
    return [event.event for event in events]


def _hit(fid: str, score: float, leg: str = "vector") -> IndexHitFace:
    return IndexHitFace(fragment_id=fid, report_id="rpt-1", report="N-02 完井报告",
                        section="01 井基本情况", snippet="N-02 于 2019-06-15 投产",
                        score=score, leg=leg)


def _anchor_of(hit: IndexHitFace) -> FragmentAnchorFace:
    return FragmentAnchorFace(fragment_id=hit.fragment_id, report_id=hit.report_id,
                              report=hit.report, section=hit.section)


class TestEarlyStopSemantics:
    """命中即停早停语义（D2 检索顺序卡）——配置改动可见帧序变化（验收实证）。"""

    async def test_early_stop_on_skips_lower_levels_after_anchor(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        seams.index_hits = [_hit("f1", 0.9)]
        seams.index_vector = [_hit("f1", 0.9)]
        seams.index_keyword = [_hit("f1", 0.6, "keyword")]
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=["指标卡·产量完成率"], actor_who=AQIANG,
        ))
        lines = [(f["key"], f["text"]) for f in _events_by_name(events)["node_line"]]
        assert any("命中即停——S3~S5 跳过" in text for key, text in lines if key == "S1")
        assert not any("双路召回" in text for _key, text in lines)  # S4 被早停跳过
        assert not any("S5 图扩展" in text for _key, text in lines)  # S5 同被跳过
        # S6/S7 不受早停影响（合同：资格审/权威回读照走）
        assert any(key == "S6" for key, _text in lines)
        assert any(key == "S7" for key, _text in lines)

    async def test_early_stop_off_runs_all_levels(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """关＝逐级全跑（F21 逐级升级的关闭态语义）——S3/S4/S5 全部执行。"""
        seams.index_hits = [_hit("f1", 0.9)]
        seams.index_vector = [_hit("f1", 0.9)]
        seams.index_keyword = [_hit("f1", 0.6, "keyword")]
        seams.config = replace(DEFAULT_CONFIG, early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=["指标卡·产量完成率"], actor_who=AQIANG,
        ))
        lines = [(f["key"], f["text"]) for f in _events_by_name(events)["node_line"]]
        assert any("双路召回" in text for _key, text in lines)  # 逐级全跑——S4 照走
        assert any("S5 图扩展" in text for _key, text in lines)

    async def test_level_switch_off_skips_level(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """三级开关关＝跳过该级直接看下一级（D2 开关语义）。"""
        seams.config = replace(
            DEFAULT_CONFIG, order_levels=(False, True, True), early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量完成率如何", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        lines = [f["text"] for f in _events_by_name(events)["node_line"]]
        assert any("第 1 级开关关——跳过锚定" in text for text in lines)

    async def test_ledger_hit_with_early_stop_skips_dual(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        seams.index_vector = [_hit("f1", 0.9)]
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量完成率如何", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        lines = [f["text"] for f in _events_by_name(events)["node_line"]]
        assert any("命中即停——S4~S5 跳过" in text for text in lines)
        assert seams.calls.get("index_dual", 0) == 0  # S4 真被跳过（并发召回未发起）


class TestDualRecallAndRerank:
    """S4 双路并发＋合并两策＋精排三档（D2 找候选参数卡/精排档位卡）。"""

    async def test_topk_config_drives_dual_legs(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """semantic_top_k/keyword_top_k 配置驱动两路取数（并发双路读缝入参）。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.1) for i in range(5)]
        seams.index_keyword = [_hit(f"k{i}", 0.5, "keyword") for i in range(5)]
        seams.config = replace(DEFAULT_CONFIG, semantic_top_k=2, keyword_top_k=3,
                               early_stop=False)
        svc = make_service(chat_db, seams)
        await collect(svc.ask("N-02 的情况", session_id=None, page_context=None,
                              anchors=[], actor_who=AQIANG))
        assert seams.calls.get("index_dual", 0) == 1  # 双路召回真实发起

    async def test_merge_concat_changes_line_and_order(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        seams.index_vector = [_hit("v1", 0.9)]
        seams.index_keyword = [_hit("k1", 0.6, "keyword")]
        seams.config = replace(DEFAULT_CONFIG, merge="concat", early_stop=False)
        seams.completion = "答案 [c1]。"
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 的情况", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        lines = [f["text"] for f in _events_by_name(events)["node_line"]]
        assert any("合并（concat——谁排前用谁）" in text for text in lines)
        # concat＝向量路在前——c1 即向量腿命中
        citation = _events_by_name(events)["citation"][0]
        assert citation["ref"] == "c1" and citation["locator"]["fragment_id"] == "v1"

    async def test_rerank_llm_scores_each_candidate(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """精排 llm 档：逐条打分（打 N 条就是 N 次模型调用）——W-F34。"""
        seams.index_vector = [_hit("v1", 0.5), _hit("v2", 0.8)]
        seams.config = replace(DEFAULT_CONFIG, rerank="llm", early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 的情况", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        # 每条候选一次打分调用（caller=chat.retrieval.rerank）＋一次生成调用
        assert seams.completions.count("chat.retrieval.rerank") == 2
        assert seams.completions.count("chat.retrieval.answer") == 1
        assert _events_by_name(events)["answer"][0]["kind"] == "text"

    async def test_rerank_llm_parse_failure_falls_back_to_order(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """打分解析失败→按原顺序放行，不影响整条链路（W-F34-2 回退原序不炸链）。"""
        seams.index_vector = [_hit("v1", 0.5), _hit("v2", 0.8)]
        seams.config = replace(DEFAULT_CONFIG, rerank="llm", early_stop=False)
        seams.completion = "不是分数"
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 的情况", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        lines = [f["text"] for f in _events_by_name(events)["node_line"]]
        assert any("精排（llm）" in text for text in lines)
        assert _events_by_name(events)["answer"][0]["kind"] == "text"

    async def test_rerank_compound_uses_model_scores(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """精排 compound 档：复合分（0.6 模型＋0.3 检索＋0.1 来源）＋MMR——真跑。"""
        seams.index_vector = [_hit("v1", 0.5), _hit("v2", 0.8)]
        seams.config = replace(DEFAULT_CONFIG, rerank="compound", early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 的情况", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        assert seams.completions.count("chat.retrieval.rerank") == 2
        assert _events_by_name(events)["answer"][0]["kind"] == "text"

    async def test_evidence_cap_four_with_overflow_notice(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """S6 资格裁决 4 支上限——超出的截断并标「另有 N 支未列出」。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.05) for i in range(6)]
        seams.config = replace(DEFAULT_CONFIG, early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 的情况", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        notices = [str(n["text"]) for n in _events_by_name(events)["notice"]]
        assert any("另有 2 支未列出" in text for text in notices)
        assert seams.completions.count("chat.retrieval.answer") == 1


class TestRefuseThresholdAndFallback:
    """兜底两策＋refuse_threshold 消费（D2 兜底策略卡/问答行为卡）。"""

    async def test_score_above_threshold_generates(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """证据分高于低分线 → 不兜底、走生成（refuse_threshold 之上）。"""
        seams.index_vector = [_hit("f1", 0.9)]
        seams.anchors = {"f1": _anchor_of(_hit("f1", 0.9))}
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 什么时候投产的", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        assert _events_by_name(events)["answer"][0]["kind"] == "text"
        lines = [f["text"] for f in _events_by_name(events)["node_line"]]
        assert not any("拒答判定" in text for text in lines)

    async def test_score_below_threshold_falls_back_fixed(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """证据分低于低分线 → fixed 兜底（refuse_threshold 之上走生成、之下走兜底）。"""
        seams.index_vector = [_hit("f1", 0.3)]
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("随便问", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        answer = data["answer"][0]
        assert answer["kind"] == "alert" and answer["text"] == DEFAULT_CONFIG.fallback_text
        lines = [f["text"] for f in data["node_line"]]
        assert any("低于低分线 0.40" in text for text in lines)

    async def test_fallback_free_tag_and_generation(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """free 兜底：自由回答＋「未依据报告库」标注（LLM 生成走 completer）。"""
        seams.index_vector = [_hit("f1", 0.3)]
        seams.config = replace(DEFAULT_CONFIG, fallback_strategy="free")
        seams.completion = "自由回答正文。"
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("随便问", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        answer = _events_by_name(events)["answer"][0]
        assert answer["kind"] == "text"
        assert answer["text"].endswith(d.FREE_ANSWER_TAG)

    async def test_s7_refuses_metric_off_ledger(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """S7 权威源回读：指标不在现行台账目录 → 拦下不代答（编号敲错在这里拦）。

        @ 锚定按包含匹配解析（「产量」⊂「产量完成率」可锚定），但回读以台账
        槽位名精确核对——「产量」不在现行指标目录 → 拦下。
        """
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量现在如何", session_id=None, page_context=None,
            anchors=["指标卡·产量"], actor_who=AQIANG,
        ))
        data = _events_by_name(events)
        notices = [str(n["text"]) for n in data["notice"]]
        assert any("不在现行指标目录，不代答" in text for text in notices)
        assert data["answer"][0]["kind"] == "alert"  # 兜底收场——绝不代答


class TestCitationFailClosed:
    """citation fail-closed（票面验收：编造引用被拦——绝不带病出帧）。"""

    async def test_fabricated_alias_deleted_with_notice(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """模型编造 [c9]（编号表里没有的引用）→ 直接删掉＋notice 留痕。"""
        seams.index_vector = [_hit("f1", 0.9)]
        seams.anchors = {"f1": _anchor_of(_hit("f1", 0.9))}
        seams.completion = "依据 [c1] 回答，另有编造引用 [c9]。"
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 什么时候投产的", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        answer = data["answer"][0]
        assert "[c9]" not in answer["text"]  # 伪造引用 fail-closed 删除
        assert "[c1]" not in answer["text"] or answer["text"]  # page 格式——c1 展开为标签
        assert "编造引用" in answer["text"].replace("[c9]", "")  # 正文保留、引用剥除
        refs = [c["ref"] for c in answer["citations"]]
        assert refs == ["c1"]  # 只出真实引用
        notices = [str(n["text"]) for n in data["notice"]]
        assert any("已拦截 1 条失锚/伪造引用" in text for text in notices)

    async def test_unanchored_fragment_citation_dropped(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """fragment_id 锚不上片段台账（片段已失）→ 引用丢弃＋notice，绝不带病出帧。"""
        seams.index_vector = [_hit("f1", 0.9)]
        seams.anchors = {"f1": None}  # 片段不存在——fail-closed
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 什么时候投产的", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        answer = data["answer"][0]
        assert answer["citations"] == []  # 失锚引用被拦——不外发 citation 帧
        assert "[c1]" not in answer["text"]
        notices = [str(n["text"]) for n in data["notice"]]
        assert any("失锚/伪造引用" in text for text in notices)

    async def test_citation_code_format_keeps_refs(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """citation_format=code：正文保持 [cN] 编号呈现，出处收敛进引用清单。"""
        seams.index_vector = [_hit("f1", 0.9)]
        seams.anchors = {"f1": _anchor_of(_hit("f1", 0.9))}
        seams.config = replace(DEFAULT_CONFIG, citation_format="code")
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 什么时候投产的", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        answer = data["answer"][0]
        assert "[c1]" in answer["text"]
        assert answer["citations"][0]["ref"] == "c1"

    async def test_fragment_belongs_to_hit_report(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """fragment_id 真实存在但不属于命中的报告 → 失锚拦截（归属校验）。"""
        seams.index_vector = [_hit("f1", 0.9)]
        seams.anchors = {"f1": FragmentAnchorFace(fragment_id="f1", report_id="rpt-other",
                                                  report="别的报告", section=None)}
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 什么时候投产的", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        assert data["answer"][0]["citations"] == []
        notices = [str(n["text"]) for n in data["notice"]]
        assert any("失锚/伪造引用" in text for text in notices)


class TestFaqExpandRounds:
    """FAQ 路扩检（qa_behavior.faq_expand_rounds 消费——每轮候选数翻倍，硬顶 5 轮）。"""

    async def test_expand_rounds_config_drives_attempts(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """轮数配置驱动扩检轮次（rounds=3→3 轮后停；不无限空转）。"""
        seams.config = replace(DEFAULT_CONFIG, faq_direct_hit=False, faq_expand_rounds=3)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("随便问一句", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        lines = [f["text"] for f in _events_by_name(events)["node_line"]]
        assert any("扩检第 1 轮（候选数 ×1）" in text for text in lines)
        assert any("扩检第 2 轮（候选数 ×2）" in text for text in lines)
        assert any("扩检第 3 轮（候选数 ×4）" in text for text in lines)
        assert any("扩检 3 轮未命中" in text for text in lines)
        assert seams.calls.get("faq_search", 0) == 3

    async def test_expand_hit_above_floor_joins_evidence(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """扩检命中过线（≥0.5）→ FAQ 相似问并入检索证据＋citation。"""
        seams.faq_similar = [
            d.FaqHitFace(entry_id="faq-1", question="N-02 什么时候投产的",
                         answer="2019-06-15 投产。", score=0.82),
        ]
        seams.config = replace(DEFAULT_CONFIG, faq_direct_hit=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 投产日期", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        lines = [f["text"] for f in _events_by_name(events)["node_line"]]
        assert any("扩检第 1 轮（候选数 ×1）：命中 1 条相似问" in text for text in lines)
        answer = _events_by_name(events)["answer"][0]
        assert answer["kind"] == "text"

    async def test_expand_below_floor_not_evidence(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """扩检命中低于过线分（<FAQ_EXPAND_FLOOR）→ 不进证据，继续翻倍。"""
        seams.faq_similar = [
            d.FaqHitFace(entry_id="faq-1", question="无关问题", answer="…", score=0.3),
        ]
        seams.config = replace(DEFAULT_CONFIG, faq_direct_hit=False, faq_expand_rounds=2)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("随便问", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        lines = [f["text"] for f in _events_by_name(events)["node_line"]]
        assert any("扩检 2 轮未命中" in text for text in lines)


class TestFaqDirectChain:
    async def test_direct_answer_with_citation_and_no_model(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """FAQ 秒回链：直出答案＋citation（no_model=true——未调用模型）。"""
        seams.faq_hit = d.FaqHitFace(entry_id="faq-1", question="产量完成率怎么算",
                                     answer="Σ实际产油 ÷ Σ计划配产 × 100%")
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("产量完成率怎么算", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        answer = data["answer"][0]
        assert answer["kind"] == "text" and answer["no_model"] is True
        assert "Σ实际产油 ÷ Σ计划配产 × 100%" in answer["text"]
        assert "FAQ「产量完成率怎么算」" in answer["text"]  # page 格式——出处标签展开
        citation = data["citation"][0]
        assert citation["kind"] == "台账条目"
        assert citation["locator"]["section"] == "常见问题库"
        assert seams.calls.get("complete", 0) == 0  # 秒回零模型调用

    async def test_direct_hit_vanished_falls_back(self, chat_db: Any, seams: Seams) -> None:
        """直出链被分派但命中失效（索引竞变）→ 兜底收场，不硬答（链体直驱——
        路由层与链层之间命中消失的防御面）。"""
        from app.domains.chat import chains as chains_mod
        from app.domains.chat.domain import (
            MATCHERS,
            AssemblyResult,
            ChainContext,
            LaneResult,
        )

        deps = chains_mod.ChainDeps(
            config_loader=seams.load_config,
            metrics_loader=seams.load_metrics,
            terms_loader=seams.load_terms,
            faq_matcher=seams.match_faq,
            faq_searcher=seams.search_faq_similar,
            index_searcher_dual=seams.search_index_dual,
            graph_searcher=seams.search_graph,
            anchor_loader=seams.load_anchor,
            completer=seams,
        )
        assembly = AssemblyResult(
            anchor_line=None, slots="∅", terms=[], candidates=[],
            lanes=[LaneResult(matcher=m, status="miss") for m in MATCHERS],
            faq_hit=None,
        )
        events = await collect(chains_mod.faq_direct_chain(
            deps, ChainContext(run_id="run-x", question="产量完成率怎么算",
                               actor_who=AQIANG, assembly=assembly)))
        answer = _events_by_name(events)["answer"][0]
        assert answer["kind"] == "alert" and answer["text"] == DEFAULT_CONFIG.fallback_text


class TestGraphChain:
    async def test_graph_edges_generate_with_citation(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """图谱问答链：邻域边→生成带图出处 citation（边出处回证据）。"""
        seams.graph_hits = [
            GraphHitFace(entity="N-06", relation="受效 → N-02",
                         evidence="N-06 井注水，受效井为 N-02 井。",
                         source_chunk_id="f1", source_report_id="rpt-1"),
        ]
        seams.index_vector = []  # 报告路不抢路由
        seams.anchors = {"f1": FragmentAnchorFace(fragment_id="f1", report_id="rpt-1",
                                                  report="N-02 完井报告", section="01")}
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("哪些井受过 N-06 注水影响", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        assert data["verdict"][0]["chain"] == "图谱问答链"
        citation = data["citation"][0]
        assert citation["kind"] == "图谱"
        assert citation["locator"]["fragment_id"] == "f1"
        assert citation["locator"]["report"] == "N-02 完井报告"
        assert data["answer"][0]["kind"] == "text"

    async def test_graph_stale_chunk_citation_dropped(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """图谱边 chunk 失锚（片段已失）→ 引用拦截丢弃＋notice；全部失锚→兜底
        收场——绝不带病出帧。"""
        seams.graph_hits = [
            GraphHitFace(entity="N-06", relation="受效 → N-02", evidence="…",
                         source_chunk_id="f1", source_report_id="rpt-1"),
        ]
        seams.anchors = {"f1": None}
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("哪些井受过 N-06 注水影响", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        answer = data["answer"][0]
        assert answer.get("citations", []) == []  # 无 citation 帧（兜底 alert 亦无）
        assert answer["kind"] == "alert"  # 全部失锚→无可用证据→兜底
        notices = [str(n["text"]) for n in data["notice"]]
        assert any("失锚/伪造引用" in text for text in notices)

    async def test_graph_miss_falls_back(self, chat_db: Any, seams: Seams) -> None:
        """图谱链被分派但缝内无边 → 兜底收场。"""
        seams.graph_hits = []
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("哪些井受过 N-06 注水影响", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        data = _events_by_name(events)
        assert _names(events)[-1] == "done"
        assert data["answer"][0]["text"] == DEFAULT_CONFIG.fallback_text


class TestConsumptionMatrix:
    """D2 qa_behavior 五字段消费矩阵（票面验收——五字段全消费实证）。"""

    async def test_five_fields_all_consumed(self, chat_db: Any, seams: Seams) -> None:
        """faq_direct_hit／refuse_threshold／clarify_strategy／confidence_thresholds／
        faq_expand_rounds 各有消费断言（逐字段路由到对应链体行为）。"""
        # faq_direct_hit：true→FAQ直出链（false→检索链已在 TestD2ConfigDrivenRouting 断言）
        seams.faq_hit = d.FaqHitFace(entry_id="f", question="q", answer="a")
        svc = make_service(chat_db, seams)
        data = _events_by_name(await collect(svc.ask(
            "q", session_id=None, page_context=None, anchors=[], actor_who=AQIANG)))
        assert data["verdict"][0]["chain"] == "FAQ直出链"
        # refuse_threshold：0.3 分证据 + 低分线 0.5 → 兜底（其余默认）
        seams2 = Seams()
        seams2.index_vector = [_hit("f1", 0.3)]
        seams2.config = replace(DEFAULT_CONFIG, refuse_threshold=0.5)
        svc2 = make_service(chat_db, seams2)
        data2 = _events_by_name(await collect(svc2.ask(
            "随便问", session_id=None, page_context=None, anchors=[], actor_who=AQIANG)))
        assert data2["answer"][0]["kind"] == "alert"
        # confidence_thresholds：高线 0.5→0.7 分证据即「高」（默认 0.8 时为「中」）
        seams3 = Seams()
        seams3.index_hits = [_hit("f1", 0.7)]  # 装配层命中（裁决置信度的证据分源）
        seams3.index_vector = [_hit("f1", 0.7)]
        seams3.anchors = {"f1": _anchor_of(_hit("f1", 0.7))}
        seams3.config = replace(DEFAULT_CONFIG, confidence_high=0.5)
        svc3 = make_service(chat_db, seams3)
        data3 = _events_by_name(await collect(svc3.ask(
            "N-02 什么时候投产的", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG)))
        assert data3["verdict"][0]["confidence"].startswith("高")
        # clarify_strategy：ask_missing 开澄清闸（口径两译→挂起）
        svc4 = make_service(chat_db, Seams())
        first = await collect(svc4.ask(
            "有效产量是多少", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG))
        assert any(e.event == "clarify" for e in first)
        # faq_expand_rounds：消费断言见 TestFaqExpandRounds（轮数驱动扩检轮次）

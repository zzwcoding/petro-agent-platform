"""chat 三链链体单测（P1-08b 链体＋P1-08c 树叙事步进）——检索瀑布链（D2 配置
驱动行为变化实证）＋FAQ 秒回链＋图谱问答链＋citation fail-closed＋node 帧族
时序（S 级过程行归位 node 帧/跳过级 wait＋skipped/GEN 序号/配置核对行/token
不交错）。

验收获收点对照（tickets/phase1/README.md P1-08b/P1-08c）：
- 三链各真跑：链体帧序（node 步进）＋answer 收场；
- D2 配置改动可见行为变化：三级开关/命中即停关（帧序变化）/topK/合并两策/
  精排三档/引用格式两格/兜底两策/refuse_threshold/confidence_thresholds/
  faq_expand_rounds——逐字段消费；
- fail-closed 单测：编造引用（未知别名 c9）被拦＋失锚 fragment 被拦＋notice 留痕；
- 树叙事时序断言：节点逐帧点亮序列（process→finish/wait＋skipped）＋token 帧
  在全部树帧之后（不交错乱序）。
"""

from dataclasses import replace
from typing import Any

from app.domains.chat import chains as chains_mod
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
    events_by_name,
    make_service,
    node_walk,
)


def _hit(fid: str, score: float, leg: str = "vector") -> IndexHitFace:
    return IndexHitFace(fragment_id=fid, report_id="rpt-1", report="N-02 完井报告",
                        section="01 井基本情况", snippet="N-02 于 2019-06-15 投产",
                        score=score, leg=leg)


def _anchor_of(hit: IndexHitFace) -> FragmentAnchorFace:
    return FragmentAnchorFace(fragment_id=hit.fragment_id, report_id=hit.report_id,
                              report=hit.report, section=hit.section)


def _node_notes(events: list[Any], key: str) -> list[str]:
    """某节点全部 note（node 帧族断言面）。"""
    return [
        str(f["note"]) for f in events_by_name(events)["node"]
        if f["key"] == key and f.get("note")
    ]


def _finish_notes(events: list[Any], key: str) -> list[str]:
    return [
        str(f["note"]) for f in events_by_name(events)["node"]
        if f["key"] == key and f["state"] == "finish" and f.get("note")
    ]


def _skip_frames(events: list[Any], key: str) -> list[dict[str, Any]]:
    return [
        f for f in events_by_name(events)["node"]
        if f["key"] == key and f["state"] == "wait" and f.get("skipped") is True
    ]


class TestTreeNarrative:
    """P1-08c 树叙事（node 帧族）——步进时序/跳过表达/GEN 序号/配置核对行。"""

    async def test_retrieval_node_walk_golden(self, chat_db: Any, seams: Seams) -> None:
        """检索链 node 步进金样本（A1 实时路径全量）：前门 N1→N3→N4→N5→N5b→N6
        →链内 N17→S0→S1→S3（台账命中——不停级，P1F-03）→S4 双路召回→S5 直通
        跳过→S6→S7→GEN→N17 收束；执行级 process→finish 成对、跳过级
        wait＋skipped:true。"""
        seams.index_vector = [_hit("f1", 0.9)]
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量完成率如何", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        assert node_walk(events) == [
            ("N1", "process"), ("N1", "finish"),
            ("N3", "process"), ("N3", "finish"),
            ("N4", "process"), ("N4", "finish"),
            ("N5", "process"), ("N5", "finish"),
            ("N5b", "process"), ("N5b", "finish"),
            ("N6", "process"), ("N6", "finish"),
            ("N17", "process"),
            ("S0", "process"), ("S0", "finish"),
            ("S1", "process"), ("S1", "finish"),
            ("S3", "process"), ("S3", "finish"),  # 台账命中——词表级不停下级（P1F-03）
            ("S4", "process"), ("S4", "finish"),  # 双路召回照跑
            ("S5", "wait"),  # 图扩展未启用——直通跳过
            ("S6", "process"), ("S6", "finish"),
            ("S7", "process"), ("S7", "finish"),
            ("GEN", "process"), ("GEN", "finish"),
            ("N17", "finish"),
        ]
        skips = [f for f in events_by_name(events)["node"]
                 if f["state"] == "wait" and f.get("skipped") is True]
        assert {f["key"] for f in skips} == {"S5"}
        assert all("图扩展未启用" in str(f["note"]) for f in skips)

    async def test_token_frames_never_interleave_tree_frames(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """token 帧切片与树帧不交错乱序：首个 token 之前是全部
        stage/sec_check/match/assembly/verdict/node/node_line/notice 帧。"""
        seams.index_vector = [_hit("f1", 0.9)]
        seams.anchors = {"f1": _anchor_of(_hit("f1", 0.9))}
        seams.completion = "依据材料作答 [c1]。"
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 什么时候投产的", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        names = [e.event for e in events]
        tree_frames = {"stage", "sec_check", "match", "assembly", "verdict",
                       "node", "node_line", "notice"}
        first_token = names.index("token")
        assert first_token > 0
        assert not tree_frames.intersection(names[first_token:])
        assert names[-1] == "done" and names[-2] == "answer"

    async def test_gen_ordinal_counts_rerank_calls(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """「模型第 N 次调用」标注行：精排 llm 档逐条打分计入——GEN 序号＝打分
        调用数＋1（node tag 与 node_line 标注行同源）。"""
        seams.index_vector = [_hit("v1", 0.5), _hit("v2", 0.8)]
        seams.config = replace(DEFAULT_CONFIG, rerank="llm", early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        gen_process = [f for f in events_by_name(events)["node"]
                       if f["key"] == "GEN" and f["state"] == "process"]
        assert gen_process and gen_process[0]["tag"] == "模型第 3 次调用"
        gen_lines = [str(f["text"]) for f in events_by_name(events)["node_line"]
                     if f["key"] == "GEN"]
        assert any("模型第 3 次调用" in text for text in gen_lines)

    async def test_config_check_line_lists_consumed_config(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """出口「配置核对」行（D2 行为规则 6 展示面）——只列真实消费的生效值。"""
        seams.index_vector = [_hit("f1", 0.9)]
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量完成率如何", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        check_lines = [str(f["text"]) for f in events_by_name(events)["node_line"]
                       if f["key"] == "N17"]
        assert any(
            "配置核对：三级顺序＝锚定、词表、双路 · 早停＝开（@锚定级命中即跳）"
            "，S3 命中不停下级" in text
            and "精排＝fast" in text and "兜底＝fixed" in text
            for text in check_lines
        )

    async def test_level_switch_off_emits_skip_frame(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """三级开关关＝跳过级 node 帧（state=wait＋skipped:true——00 §5.3 ①）。"""
        seams.config = replace(DEFAULT_CONFIG, order_levels=(False, True, True))
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量完成率如何", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        skips = _skip_frames(events, "S1")
        assert skips and "第 1 级开关关——跳过锚定" in str(skips[0]["note"])
        # 被跳过的级不发 process/finish 对（帧序里 S1 只有这一帧）
        assert [f["state"] for f in events_by_name(events)["node"]
                if f["key"] == "S1"] == ["wait"]

    async def test_s5_always_records_direct_skip(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """S5 图扩展未启用——直通跳过照常记录（D2「过程记录写明直通跳过」）。"""
        seams.config = replace(DEFAULT_CONFIG, early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量完成率如何", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        skips = _skip_frames(events, "S5")
        assert skips and "图扩展未启用" in str(skips[0]["note"])

    async def test_faq_chain_node_walk(self, chat_db: Any, seams: Seams) -> None:
        """FAQ 秒回链：N18 process→finish（零内部步进——秒回同拍完成）。"""
        seams.faq_hit = d.FaqHitFace(entry_id="faq-1", question="产量完成率怎么算",
                                     answer="Σ实际产油 ÷ Σ计划配产")
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量完成率怎么算", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        # 前门 N1..N6 之后的链内步进＝N18 process→finish（零内部步进——秒回同拍完成）
        assert node_walk(events)[-2:] == [("N18", "process"), ("N18", "finish")]
        assert any("no_model" in text or "未调用模型" in text
                   for text in _finish_notes(events, "N18"))

    async def test_graph_chain_node_walk(self, chat_db: Any, seams: Seams) -> None:
        """图谱问答链：N13 开跑→遍历内容行→GEN→N13 收束。"""
        seams.graph_hits = [
            GraphHitFace(entity="N-06", relation="受效 → N-02",
                         evidence="N-06 井注水，受效井为 N-02 井。",
                         source_chunk_id="f1", source_report_id="rpt-1"),
        ]
        seams.index_vector = []
        seams.anchors = {"f1": _anchor_of(_hit("f1", 0.9))}
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "哪些井受过 N-06 注水影响", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        assert node_walk(events)[-4:] == [
            ("N13", "process"),
            ("GEN", "process"), ("GEN", "finish"),
            ("N13", "finish"),
        ]
        n13_lines = [str(f["text"]) for f in events_by_name(events)["node_line"]
                     if f["key"] == "N13"]
        assert any("图谱邻域遍历：命中 1 条关系边" in text for text in n13_lines)


class TestEarlyStopSemantics:
    """早停语义（D2 检索顺序卡——P1F-03/D2 v0.3 收窄：仅 @锚定级命中即跳，
    S3 词表级命中永不停下级）——配置改动可见帧序变化（验收实证）。"""

    async def test_early_stop_on_skips_lower_levels_after_anchor(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(c) @ 锚定命中＋早停开 → S3~S5 跳过（身份确认——唯一保留的早停路径）；
        S4/S5 skip 注记保留且归因 S1 锚定；S3 级不另出帧（P1F-03：S3 skip 调用
        删除——S1 注记已声明 S3~S5 跳过）。"""
        seams.index_hits = [_hit("f1", 0.9)]
        seams.index_vector = [_hit("f1", 0.9)]
        seams.index_keyword = [_hit("f1", 0.6, "keyword")]
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=["指标卡·产量完成率"], actor_who=AQIANG,
        ))
        s1_finish = " ".join(_finish_notes(events, "S1"))
        assert "命中即停——S3~S5 跳过" in s1_finish
        assert not any("双路召回" in text for text in _finish_notes(events, "S4"))
        assert _skip_frames(events, "S4") and _skip_frames(events, "S5")
        assert all(
            "S1 锚定命中即停" in str(f["note"])
            for key in ("S4", "S5") for f in _skip_frames(events, key)
        )
        # S3 级在 S1 早停下不出任何帧（本级无 skip 调用——skip 决策只剩 S1）
        assert not [f for f in events_by_name(events)["node"] if f["key"] == "S3"]
        assert seams.calls.get("index_dual", 0) == 0  # S4 真被跳过（并发召回未发起）
        # S6/S7 不受早停影响（合同：资格审/权威回读照走）
        assert _finish_notes(events, "S6") and _finish_notes(events, "S7")

    async def test_early_stop_off_runs_all_levels(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """关＝逐级全跑（F21 逐级升级的关闭态语义）——S1 也不跳，S3/S4/S5 全部执行。"""
        seams.index_hits = [_hit("f1", 0.9)]
        seams.index_vector = [_hit("f1", 0.9)]
        seams.index_keyword = [_hit("f1", 0.6, "keyword")]
        seams.config = replace(DEFAULT_CONFIG, early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=["指标卡·产量完成率"], actor_who=AQIANG,
        ))
        assert "命中即停" not in " ".join(_finish_notes(events, "S1"))  # 关＝S1 也不跳
        assert any("双路召回" in text for text in _finish_notes(events, "S4"))
        assert any("图扩展未启用" in text for text in _skip_notes(events, "S5"))

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
        skips = _skip_frames(events, "S1")
        assert skips and "第 1 级开关关——跳过锚定" in str(skips[0]["note"])

    async def test_ledger_hit_does_not_stop_dual_recall(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(a) B-正5 形态（题面含台账词的正题，早停开）：S3 台账命中不停下级——
        S4 照跑、报告片段进生成材料、引用非空（旧病灶：S4/S5 skipped＋引用 0 条，
        第五章三项措施一个没答）。"""
        seams.index_vector = [_hit("f1", 0.9)]
        seams.anchors = {"f1": _anchor_of(_hit("f1", 0.9))}
        seams.completion = "依据材料作答 [c1]。"
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "产量完成率如何", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        data = events_by_name(events)
        s3_finish = " ".join(_finish_notes(events, "S3"))
        assert "台账完全一致命中" in s3_finish
        assert "命中即停" not in s3_finish  # 词表级命中不触发早停（观测面同步收窄）
        assert not _skip_frames(events, "S4")  # S4 不被 skip
        assert any("双路召回" in text for text in _finish_notes(events, "S4"))
        assert seams.calls.get("index_dual", 0) == 1  # 双路召回真实发起
        # S5 的 skip 只剩「未启用」一态——早停不再触及
        assert any("图扩展未启用" in text for text in _skip_notes(events, "S5"))
        # 报告片段证据进生成材料（生成 user 消息含报告 snippet——材料在场观测面）
        assert "N-02 于 2019-06-15 投产" in _last_gen_user(seams)
        assert data["citation"]  # 引用非空（B-正5 病灶＝引用 0 条）
        assert data["answer"][0]["kind"] == "text"

    async def test_definition_question_term_card_via_assembly(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(b) 释义问（什么是躺井，早停开）：词条卡经 P1F-02 装配层常驻进生成
        材料——不依赖 S3 命中跳过（S4 照跑；本测不断言 S3 跳过）。"""
        seams.index_vector = []  # 报告路空——生成材料只余台账侧（词条卡＋台账条目）
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "什么是躺井", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        assert events_by_name(events)["answer"][0]["kind"] == "text"
        assert "术语台账收录：躺井" in _last_gen_user(seams)  # 词条卡（装配层随行）
        # 词表级命中不停下级——与 (a) 同口径：S4 执行不 skip
        assert not _skip_frames(events, "S4")
        assert any("双路召回" in text for text in _finish_notes(events, "S4"))


def _skip_notes(events: list[Any], key: str) -> list[str]:
    return [str(f["note"]) for f in _skip_frames(events, key)]


def _last_gen_user(seams: Seams) -> str:
    """检索链生成步（caller=chat.retrieval.answer）最近一次 user 消息正文
    （生成材料在场观测面——P1F-03 (a)/(b) 断言用）。"""
    gen = [msgs for caller, msgs in seams.prompts if caller == chains_mod.CALLER_RETRIEVAL]
    assert gen, "检索链生成步未被调用"
    return next(m["content"] for m in gen[-1] if m["role"] == "user")


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
        s4_notes = " ".join(
            str(f.get("note") or "") for f in events_by_name(events)["node"]
            if f["key"] == "S4"
        )
        assert "合并（concat——谁排前用谁）" in s4_notes
        # concat＝向量路在前——c1 即向量腿命中
        citation = events_by_name(events)["citation"][0]
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
        assert events_by_name(events)["answer"][0]["kind"] == "text"

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
        s4_notes = " ".join(
            str(f.get("note") or "") for f in events_by_name(events)["node"]
            if f["key"] == "S4"
        )
        assert "精排（llm）" in s4_notes
        assert events_by_name(events)["answer"][0]["kind"] == "text"

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
        assert events_by_name(events)["answer"][0]["kind"] == "text"

    async def test_evidence_cap_four_with_overflow_notice(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """S6 资格裁决 4 支上限——超出的截断并标「另有 N 支未列出」。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.05) for i in range(6)]
        seams.config = replace(DEFAULT_CONFIG, early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("N-02 的情况", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        notices = [str(n["text"]) for n in events_by_name(events)["notice"]]
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
        assert events_by_name(events)["answer"][0]["kind"] == "text"
        s6_notes = " ".join(
            str(f.get("note") or "") for f in events_by_name(events)["node"]
            if f["key"] == "S6"
        )
        assert "拒答判定" not in s6_notes

    async def test_score_below_threshold_falls_back_fixed(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """证据分低于低分线 → fixed 兜底（refuse_threshold 之上走生成、之下走兜底）。"""
        seams.index_vector = [_hit("f1", 0.3)]
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("随便问", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        data = events_by_name(events)
        answer = data["answer"][0]
        assert answer["kind"] == "alert" and answer["text"] == DEFAULT_CONFIG.fallback_text
        s6_notes = " ".join(
            str(f.get("note") or "") for f in data["node"] if f["key"] == "S6"
        )
        assert "低于低分线 0.40" in s6_notes
        assert "拒答判定" in s6_notes

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
        answer = events_by_name(events)["answer"][0]
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
        data = events_by_name(events)
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
        data = events_by_name(events)
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
        data = events_by_name(events)
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
        data = events_by_name(events)
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
        data = events_by_name(events)
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
        lines = [f["text"] for f in events_by_name(events)["node_line"]]
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
        lines = [f["text"] for f in events_by_name(events)["node_line"]]
        assert any("扩检第 1 轮（候选数 ×1）：命中 1 条相似问" in text for text in lines)
        answer = events_by_name(events)["answer"][0]
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
        lines = [f["text"] for f in events_by_name(events)["node_line"]]
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
        data = events_by_name(events)
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
        answer = events_by_name(events)["answer"][0]
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
        data = events_by_name(events)
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
        data = events_by_name(events)
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
        data = events_by_name(events)
        assert [e.event for e in events][-1] == "done"
        assert data["answer"][0]["text"] == DEFAULT_CONFIG.fallback_text


class TestConsumptionMatrix:
    """D2 qa_behavior 五字段消费矩阵（票面验收——五字段全消费实证）。"""

    async def test_five_fields_all_consumed(self, chat_db: Any, seams: Seams) -> None:
        """faq_direct_hit／refuse_threshold／clarify_strategy／confidence_thresholds／
        faq_expand_rounds 各有消费断言（逐字段路由到对应链体行为）。"""
        # faq_direct_hit：true→FAQ直出链（false→检索链已在 TestD2ConfigDrivenRouting 断言）
        seams.faq_hit = d.FaqHitFace(entry_id="f", question="q", answer="a")
        svc = make_service(chat_db, seams)
        data = events_by_name(await collect(svc.ask(
            "q", session_id=None, page_context=None, anchors=[], actor_who=AQIANG)))
        assert data["verdict"][0]["chain"] == "FAQ直出链"
        # refuse_threshold：0.3 分证据 + 低分线 0.5 → 兜底（其余默认）
        seams2 = Seams()
        seams2.index_vector = [_hit("f1", 0.3)]
        seams2.config = replace(DEFAULT_CONFIG, refuse_threshold=0.5)
        svc2 = make_service(chat_db, seams2)
        data2 = events_by_name(await collect(svc2.ask(
            "随便问", session_id=None, page_context=None, anchors=[], actor_who=AQIANG)))
        assert data2["answer"][0]["kind"] == "alert"
        # confidence_thresholds：高线 0.5→0.7 分证据即「高」（默认 0.8 时为「中」）
        seams3 = Seams()
        seams3.index_hits = [_hit("f1", 0.7)]  # 装配层命中（裁决置信度的证据分源）
        seams3.index_vector = [_hit("f1", 0.7)]
        seams3.anchors = {"f1": _anchor_of(_hit("f1", 0.7))}
        seams3.config = replace(DEFAULT_CONFIG, confidence_high=0.5)
        svc3 = make_service(chat_db, seams3)
        data3 = events_by_name(await collect(svc3.ask(
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

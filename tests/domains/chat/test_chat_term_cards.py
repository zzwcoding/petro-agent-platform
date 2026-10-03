"""chat 词条卡一等材料化单测（票册 P1F-02 方案 B——P-004 开发拍）。

验收对照（tickets/phase1-fix/README.md P1F-02）：
- (a) 定义问三种措辞（什么是/解释一下/啥意思）→ 检索链生成步 user 消息含
  「术语台账收录：…」材料块（在证据支材料之前）＋GEN 系统提示含定义先行规则
  （mock completer 捕获 messages 断言）；
- (b) 反向用例「躺井治理措施有哪些」→ 卡片入材料＋规则存在＋并列条款防定义
  冒充措施——「报告检索不被词条卡阻挡」属 P1F-03 验收项，本票不断言；
- (c) 兜底两分支：装配有卡/FAQ 命中 → 文案含「台账有收录」且不含「没有找到」；
  六路全空 → 原 fallback_text 原样；free 分支不加判定（维持原语义）；
- (d) 装配层装卡零新增查询（mock loader 计数——改动前后同数）；
- (e) N18 拒答注记两情形各有一条测试路径（执行前复测未命中／装配命中已失效）；
- cards 不外泄：ask 流 SSE 帧与 run 落库 JSON（verdict/pending_interrupt/消息
  answer）均无 term_cards/metric_cards 序列化（帧构造不引用 cards——assembly 帧
  只发 anchor_line/slots/terms/candidates/chains）。
"""

import json
from dataclasses import replace
from typing import Any

import pytest

from app.domains.chat import chains as chains_mod
from app.domains.chat import domain as d
from app.domains.chat.domain import (
    MATCHERS,
    ChainContext,
    FaqHitFace,
    LaneResult,
    MetricCard,
    TermCard,
)
from tests.domains.chat.conftest import (
    AQIANG,
    DEFAULT_CONFIG,
    Seams,
    collect,
    events_by_name,
    make_service,
)


def _deps(seams: Seams) -> chains_mod.ChainDeps:
    """链体注入缝（conftest 假缝直驱——与生产组合根同构）。"""
    return chains_mod.ChainDeps(
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


def _assembly(**extra: Any) -> d.AssemblyResult:
    """六路全空基线装配（cards/faq_hit 按用例覆写）。"""
    return d.AssemblyResult(
        anchor_line=None, slots="∅", terms=[], candidates=[],
        lanes=[LaneResult(matcher=m, status="miss") for m in MATCHERS],
        **extra,
    )


def _gen_user_content(seams: Seams) -> str:
    """检索链生成步（caller=chat.retrieval.answer）最近一次 user 消息正文。"""
    gen = [msgs for caller, msgs in seams.prompts if caller == chains_mod.CALLER_RETRIEVAL]
    assert gen, "检索链生成步未被调用"
    return next(m["content"] for m in gen[-1] if m["role"] == "user")


def _gen_system_content(seams: Seams) -> str:
    gen = [msgs for caller, msgs in seams.prompts if caller == chains_mod.CALLER_RETRIEVAL]
    assert gen, "检索链生成步未被调用"
    return gen[-1][0]["content"]


class TestGenLayerDefinitionFirst:
    """改动 3：词条卡常驻生成材料＋定义先行规则在生成层（不在路由层）。"""

    @pytest.mark.parametrize("question", ["什么是躺井", "解释一下躺井", "躺井是啥意思"])
    async def test_definition_question_carries_term_card_material(
        self, chat_db: Any, seams: Seams, question: str,
    ) -> None:
        """(a) 定义问三措辞 → 生成 user 消息含词条卡材料块（状态标注原样带出）。"""
        seams.intent_reply = '{"chain": "检索问答链", "confidence": 0.9}'
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(question, session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        assert events_by_name(events)["answer"][0]["kind"] == "text"
        user = _gen_user_content(seams)
        assert "术语台账收录：躺井" in user
        assert "有效（限作业区语境）" in user  # 状态标注串原样进材料
        # 在证据支材料之前（编号表之前）
        assert user.index("术语台账收录") < user.index("依据材料（编号表）")
        system = _gen_system_content(seams)
        for phrase in ("先给定义", "状态标注必须原样带出", "并列给出", "不得忽略"):
            assert phrase in system
        assert "先给定义" in chains_mod.GEN_SYSTEM_PROMPT  # 规则在提示词常量（生成层）

    async def test_measures_question_cards_present_not_definition_forced(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(b) 反向用例：措施问——卡片入材料＋规则在场；「判断不了则并列给出」
        条款防定义冒充措施（生成内容由规则约束，不做答案内容断言）。"""
        seams.intent_reply = '{"chain": "检索问答链", "confidence": 0.9}'
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("躺井治理措施有哪些", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        assert events_by_name(events)["answer"][0]["kind"] == "text"
        assert "术语台账收录：躺井" in _gen_user_content(seams)
        for phrase in ("先给定义", "并列给出", "不得忽略"):
            assert phrase in chains_mod.GEN_SYSTEM_PROMPT


class TestFallbackHonesty:
    """改动 4：_fallback_answer 兜底诚实性（fixed 分支前置判定；free 不加判定）。"""

    async def test_fixed_with_term_cards_reports_ledger(self, seams: Seams) -> None:
        """装配有词条卡 → 「台账有收录：…；报告库未检索到相关内容」，不说「没有找到」。"""
        assembly = _assembly(term_cards=[TermCard(
            term="躺井", type="黑话 → 停产待检泵", def_text="作业区口语",
            status_note="有效（限作业区语境）",
        )])
        events = await collect(chains_mod._fallback_answer(
            _deps(seams), DEFAULT_CONFIG, "什么是躺井", assembly))
        answer = events_by_name(events)["answer"][0]
        text = str(answer["text"])
        assert "台账有收录" in text
        assert "躺井" in text and "作业区口语" in text and "有效（限作业区语境）" in text
        assert "报告库未检索到相关内容" in text
        assert "没有找到" not in text

    async def test_fixed_with_metric_cards_and_faq_hit_reports_ledger(
        self, seams: Seams,
    ) -> None:
        """指标卡（口径摘要）＋FAQ 命中任一在场 → 同款诚实文案（多卡逐条列出）。"""
        assembly = _assembly(
            metric_cards=[MetricCard(
                slot_name="有效产量", name="★有效产量（两支口径）",
                calibers=[{"key": "A", "name": "开井日历折算"},
                          {"key": "B", "name": "检修剔除"}],
                status_note="",
            )],
            faq_hit=FaqHitFace(entry_id="faq-1", question="有效产量怎么算",
                               answer="开井日历折算或检修剔除"),
        )
        events = await collect(chains_mod._fallback_answer(
            _deps(seams), DEFAULT_CONFIG, "有效产量", assembly))
        text = str(events_by_name(events)["answer"][0]["text"])
        assert "台账有收录" in text
        assert "「有效产量」" in text and "开井日历折算／检修剔除" in text
        assert "FAQ「有效产量怎么算」" in text
        assert "没有找到" not in text

    async def test_fixed_all_empty_keeps_fallback_text_verbatim(
        self, seams: Seams,
    ) -> None:
        """六路全空 → cfg.fallback_text 原样（D2 配置值一行不动）。"""
        events = await collect(chains_mod._fallback_answer(
            _deps(seams), DEFAULT_CONFIG, "随便问", _assembly()))
        answer = events_by_name(events)["answer"][0]
        assert answer["kind"] == "alert"
        assert answer["text"] == DEFAULT_CONFIG.fallback_text

    async def test_free_branch_unchanged_even_with_cards(self, seams: Seams) -> None:
        """free 分支不加判定（维持原语义）——有卡仍走自由回答＋「未依据报告库」。"""
        seams.completion = "自由回答正文。"
        cfg = replace(DEFAULT_CONFIG, fallback_strategy="free")
        assembly = _assembly(term_cards=[TermCard(
            term="躺井", type="黑话 → 停产待检泵", def_text="作业区口语", status_note="",
        )])
        events = await collect(chains_mod._fallback_answer(
            _deps(seams), cfg, "什么是躺井", assembly))
        answer = events_by_name(events)["answer"][0]
        assert answer["kind"] == "text"
        assert str(answer["text"]).endswith(d.FREE_ANSWER_TAG)
        assert "台账有收录" not in str(answer["text"])

    async def test_s6_refusal_with_cards_honest_end_to_end(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """整链集成：S6 拒答（低分线抬到 1.1）＋装配有词条卡 → 兜底诚实文案。"""
        seams.config = replace(DEFAULT_CONFIG, refuse_threshold=1.1)
        seams.intent_reply = '{"chain": "检索问答链", "confidence": 0.9}'
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("什么是躺井", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        answer = events_by_name(events)["answer"][0]
        assert answer["kind"] == "alert"
        assert "台账有收录" in str(answer["text"])
        assert "没有找到" not in str(answer["text"])


class TestAssemblyCardBuilding:
    """改动 2：完整行投影成卡——零新增查询（mock loader 计数）。"""

    async def test_term_cards_from_loaded_rows_zero_extra_queries(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        svc = make_service(chat_db, seams)
        assembly = await svc._assemble("什么是躺井", [])
        assert [c.term for c in assembly.term_cards] == ["躺井"]
        assert assembly.term_cards[0].status_note == "有效（限作业区语境）"
        assert assembly.term_cards[0].def_text == "限作业区语境"
        assert assembly.metric_cards == []
        base = dict(seams.calls)
        # @ 前门直取术语分支也补卡片——查询数与改动前同数（resolve 1 次＋主装载 1 次）
        anchored = await svc._assemble("躺井", ["术语·躺井"])
        assert [c.term for c in anchored.term_cards] == ["躺井"]
        assert anchored.term_cards[0].status_note == "有效（限作业区语境）"
        assert seams.calls["terms"] == base["terms"] + 2
        assert seams.calls["metrics"] == base["metrics"] + 1

    async def test_metric_cards_from_loaded_rows(self, chat_db: Any, seams: Seams) -> None:
        svc = make_service(chat_db, seams)
        assembly = await svc._assemble("有效产量怎么算", [])
        assert [c.slot_name for c in assembly.metric_cards] == ["有效产量"]
        assert [str(c["name"]) for c in assembly.metric_cards[0].calibers] == [
            "开井日历折算", "检修剔除",
        ]
        assert seams.calls["metrics"] == 1  # 主装载 1 次——装卡零新增


class TestN18MissAnnotations:
    """改动 5：N18 拒答注记两情形（执行前复测单点化——装配命中不豁免复测）。"""

    async def test_miss_without_assembly_hit_annotates_assembly_stage_miss(
        self, seams: Seams,
    ) -> None:
        """装配阶段即无命中＋执行前复测未命中 → 「执行前复测未命中（装配阶段即
        无命中）」——不再误标「索引竞变」（评测 4.1 帧 id=29 的错标形态）。"""
        assembly = _assembly()  # faq_hit=None
        events = await collect(chains_mod.faq_direct_chain(
            _deps(seams), ChainContext(run_id="run-x", question="产量完成率怎么算",
                                       actor_who=AQIANG, assembly=assembly)))
        notes = [str(f.get("note") or "") for f in events_by_name(events)["node"]
                 if f["key"] == "N18"]
        assert any("执行前复测未命中（装配阶段即无命中）" in n for n in notes)
        assert not any("索引竞变" in n for n in notes)
        answer = events_by_name(events)["answer"][0]
        assert answer["text"] == DEFAULT_CONFIG.fallback_text  # 兜底文案不在本改动面

    async def test_stale_assembly_hit_annotates_index_race(self, seams: Seams) -> None:
        """装配有命中但执行前复测落空 → 「装配命中已失效（索引竞变）」。"""
        seams.faq_hit = None  # 复测落空——索引竞变
        assembly = _assembly(faq_hit=FaqHitFace(
            entry_id="faq-1", question="产量完成率怎么算", answer="Σ实际产油 ÷ Σ计划配产"))
        events = await collect(chains_mod.faq_direct_chain(
            _deps(seams), ChainContext(run_id="run-x", question="产量完成率怎么算",
                                       actor_who=AQIANG, assembly=assembly)))
        notes = [str(f.get("note") or "") for f in events_by_name(events)["node"]
                 if f["key"] == "N18"]
        assert any("装配命中已失效（索引竞变）" in n for n in notes)


class TestCardsStayOffTheWire:
    """验收 2：cards 不外泄——SSE 帧与 run 落库 JSON 均无 card 键序列化。"""

    async def test_cards_never_leak_into_frames_or_run_json(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        seams.intent_reply = '{"chain": "检索问答链", "confidence": 0.9}'
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("什么是躺井", session_id=None, page_context=None,
                                       anchors=[], actor_who=AQIANG))
        # 前提：cards 确实在场并进了生成材料（否则断言空转）
        assert "术语台账收录：躺井" in _gen_user_content(seams)
        for event in events:
            blob = json.dumps(event.data, ensure_ascii=False)
            assert "term_cards" not in blob and "metric_cards" not in blob
        run_id = str(events_by_name(events)["session"][0]["run_id"])
        run = await svc._store.get_run(run_id)
        assert run is not None
        for payload in (run.verdict, run.pending_interrupt):
            if payload:
                blob = json.dumps(payload, ensure_ascii=False)
                assert "term_cards" not in blob and "metric_cards" not in blob
        for message in await svc._store.messages_of_run(run_id):
            if message.answer:
                blob = json.dumps(message.answer, ensure_ascii=False)
                assert "term_cards" not in blob and "metric_cards" not in blob

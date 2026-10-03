"""chat GEN 生成侧两条加权单测（P-009 开发拍——状态标注兜底通知＋禁推算约束）。

验收对照（dispatch/pending/P-009.md——复测报告 §三 系统-日产液届满 ⚠️／D-诱15 ❌）：
- (a) 词条卡在材料＋假 completer 返不含标注的答案 → warning 级 notice 出现且含
  标注串原文；答案已含标注（原文或倒装）→ 不重复出 notice；答案正文不被改写、
  answer 帧合同位次不动（notice 在 token 流前并列呈现——链缝合同「answer 帧
  必须最后出现」）；
- (b) 防过度通知：限语境类标注（躺井常态——生成端原样带出已工作）不触发；
  答案未提及该词条不触发；届满/禁用两类各一正面（禁用词占位段「—」滤除语义）；
- (c) GEN_SYSTEM_PROMPT 携禁推算约束断言串（缺数据不得加减推算补位＋不得虚
  声明材料覆盖范围），且实际下发 system 消息即该常量（生成端真收到）；
- (d) 兜底分支不接（fixed/free 兜底携届满卡也零 notice——非检索链生成路径）；
  整链服务路集成（svc.ask）：notice 经分派透传在 token 前落地、done 收场不变。
"""

from dataclasses import replace
from datetime import date
from typing import Any

import pytest

from app.domains.chat import chains as chains_mod
from app.domains.chat import domain as d
from app.domains.chat.domain import (
    MATCHERS,
    ChainContext,
    FragmentAnchorFace,
    IndexHitFace,
    LaneResult,
    TermCard,
    TermFace,
)
from tests.domains.chat.conftest import (
    AQIANG,
    DEFAULT_CONFIG,
    Seams,
    collect,
    events_by_name,
    make_service,
)

EXPIRED_NOTE = "2026-06-30（已届满）"


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
    """六路全空基线装配（term_cards 按用例覆写——手织卡直入链体）。"""
    return d.AssemblyResult(
        anchor_line=None, slots="∅", terms=[], candidates=[],
        lanes=[LaneResult(matcher=m, status="miss") for m in MATCHERS],
        **extra,
    )


def _hit(fid: str, score: float, leg: str = "vector") -> IndexHitFace:
    return IndexHitFace(fragment_id=fid, report_id="rpt-1", report="N-02 完井报告",
                        section="01 井基本情况", snippet="N-02 于 2019-06-15 投产",
                        score=score, leg=leg)


def _anchor_of(hit: IndexHitFace) -> FragmentAnchorFace:
    return FragmentAnchorFace(fragment_id=hit.fragment_id, report_id=hit.report_id,
                              report=hit.report, section=hit.section)


async def _run(
    seams: Seams, term_cards: list[TermCard], completion: str,
) -> list[Any]:
    """检索链直跑（证据过闸＋假 completer 定稿答案——生成收口判定观测面）。"""
    seams.index_vector = [_hit("f1", 0.9)]
    seams.completion = completion
    ctx = ChainContext(
        run_id="run-guard", question="日产液是什么", actor_who=AQIANG,
        assembly=_assembly(term_cards=term_cards),
    )
    return await collect(chains_mod.retrieval_chain(_deps(seams), ctx))


def _guard_notices(events: list[Any]) -> list[dict[str, Any]]:
    """状态标注兜底通知帧（其余 notice——如候选溢出——不在本判定面）。"""
    return [
        dict(frame.data) for frame in events
        if frame.event == "notice" and "状态标注——" in str(frame.data.get("text"))
    ]


def _card(note: str, term: str = "日产液") -> TermCard:
    return TermCard(term=term, type="口语缩写", def_text="作业区口语缩写", status_note=note)


class TestStatusAnnotationFallbackNotice:
    """(a) 主修：届满类标注生成端未带出 → warning notice 补位（不改写正文）。"""

    async def test_missing_annotation_gets_warning_notice(self, seams: Seams) -> None:
        """答案提及词条但不含标注 → 恰一条 warning notice，含标注串原文。"""
        body = "日产液指作业区口语里的日产液量，数据指引见产量月报。"
        events = await _run(seams, [_card(EXPIRED_NOTE)], body)
        guards = _guard_notices(events)
        assert len(guards) == 1
        assert guards[0]["text"] == f"注：日产液状态标注——{EXPIRED_NOTE}"
        assert guards[0]["level"] == "warning"

    async def test_answer_text_untouched_and_answer_frame_last(
        self, seams: Seams,
    ) -> None:
        """正文不被改写（token 流原样）；notice 在 token 流前并列、answer 帧仍收尾。"""
        body = "日产液指作业区口语里的日产液量，数据指引见产量月报。"
        events = await _run(seams, [_card(EXPIRED_NOTE)], body)
        names = [frame.event for frame in events]
        guard_positions = [
            i for i, frame in enumerate(events)
            if frame.event == "notice" and "状态标注——" in str(frame.data.get("text"))
        ]
        answer = events_by_name(events)["answer"]
        assert answer[-1]["text"] == body  # 正文零改写——通知帧补位不改写
        assert guard_positions == [names.index("notice")]  # 恰一帧且在首个 notice 位
        assert guard_positions[0] < names.index("token")  # token 流前并列呈现
        assert names[-1] == "answer"  # 链缝合同：answer 帧必须最后出现

    async def test_verbatim_annotation_no_duplicate_notice(self, seams: Seams) -> None:
        """答案已原样带出标注串 → 不重复出 notice（兜底只在缺失时抬手）。"""
        body = f"日产液（{EXPIRED_NOTE}）指作业区口语里的日产液量。"
        events = await _run(seams, [_card(EXPIRED_NOTE)], body)
        assert _guard_notices(events) == []

    async def test_reordered_annotation_no_duplicate_notice(self, seams: Seams) -> None:
        """倒装带出（「已届满（2026-06-30）」）语义全在 → 同样不重复出 notice。"""
        body = "日产液已届满（2026-06-30），指作业区口语里的日产液量。"
        events = await _run(seams, [_card(EXPIRED_NOTE)], body)
        assert _guard_notices(events) == []

    async def test_disabled_term_gets_notice(self, seams: Seams) -> None:
        """禁用类同款兜底（判别串「已禁用」）；占位段「—」不稀释判定。"""
        body = "老完成率指标已停止维护，请查现行指标目录。"
        events = await _run(seams, [_card("—（已禁用）", term="老完成率")], body)
        guards = _guard_notices(events)
        assert len(guards) == 1
        assert guards[0]["text"] == "注：老完成率状态标注———（已禁用）"
        assert guards[0]["level"] == "warning"


class TestNoOverNotification:
    """(b) 反向：限语境类不触发／未提及不触发——兜底不越界。"""

    async def test_context_scoped_annotation_not_guarded(self, seams: Seams) -> None:
        """限语境类标注（躺井常态——生成端原样带出已工作）→ 零 notice（防过度）。"""
        body = "躺井指抽油杆断脱或卡泵停产待检的井，治理措施见作业规程。"
        events = await _run(
            seams, [_card("有效（限作业区语境）", term="躺井")], body,
        )
        assert _guard_notices(events) == []
        assert events_by_name(events).get("notice", []) == []  # 全流零 notice

    async def test_term_not_mentioned_no_notice(self, seams: Seams) -> None:
        """答案未提及该词条 → 不触发（提及是兜底前提——不无关插话）。"""
        body = "相关数据指引见产量月报章节。"
        events = await _run(seams, [_card(EXPIRED_NOTE)], body)
        assert _guard_notices(events) == []

    async def test_empty_status_note_no_notice(self, seams: Seams) -> None:
        """台账未携状态字段（标注空串）→ 无从兜底，零 notice。"""
        body = "日产液指作业区口语里的日产液量。"
        events = await _run(seams, [_card("")], body)
        assert _guard_notices(events) == []
        assert events_by_name(events).get("notice", []) == []

    async def test_no_term_cards_no_notice(self, seams: Seams) -> None:
        """无词条卡基线 → 零 notice（既有链路行为不变）。"""
        events = await _run(seams, [], "依据材料作答的正文。")
        assert _guard_notices(events) == []


class TestAnnotationCarriedClassifier:
    """判别器直测（边界语义钉死——原文／倒装／占位段／单段不足）。"""

    @pytest.mark.parametrize(
        ("note", "answer", "carried"),
        [
            pytest.param(EXPIRED_NOTE, f"日产液（{EXPIRED_NOTE}）", True, id="verbatim"),
            pytest.param(EXPIRED_NOTE, "已届满（2026-06-30）", True, id="reordered"),
            pytest.param(EXPIRED_NOTE, "2026-06-30 有数据", False, id="date-only"),
            pytest.param(EXPIRED_NOTE, "该词已届满", False, id="marker-only"),
            pytest.param("—（已禁用）", "该词已禁用", True, id="disabled-carried"),
            pytest.param("—（已禁用）", "破折号—在此", False, id="placeholder-alone"),
            pytest.param("—（已禁用）", "无关正文", False, id="absent"),
        ],
    )
    def test_carried_semantics(self, note: str, answer: str, carried: bool) -> None:
        assert chains_mod._annotation_carried(note, answer) is carried


class TestGenPromptNoInferenceRule:
    """(c) 禁推算约束在 GEN 系统提示常量＋真下发（D-诱15 软失败层辅修）。"""

    def test_prompt_carries_no_inference_rule(self) -> None:
        for phrase in (
            "不得用其他数值加减推算补位",  # 缺数据禁加减补位（D-诱15 主判点）
            "如实说明该数据缺失",
            "不得作未核实的声明",  # 材料覆盖范围不虚声明
            "材料未披露",
        ):
            assert phrase in chains_mod.GEN_SYSTEM_PROMPT
        # 既有定义先行规则不被稀释（P1F-02 语义原样在场）
        for phrase in ("先给定义", "状态标注必须原样带出", "不得忽略"):
            assert phrase in chains_mod.GEN_SYSTEM_PROMPT

    async def test_retrieval_gen_sends_prompt_constant(self, seams: Seams) -> None:
        """生成步实际下发 system 消息即 GEN_SYSTEM_PROMPT（约束真到模型）。"""
        await _run(seams, [_card(EXPIRED_NOTE)], "日产液指作业区口语里的日产液量。")
        gen = [
            msgs for caller, msgs in seams.prompts
            if caller == chains_mod.CALLER_RETRIEVAL
        ]
        assert gen and gen[-1][0]["role"] == "system"
        assert gen[-1][0]["content"] == chains_mod.GEN_SYSTEM_PROMPT


class TestFallbackBranchesUntouched:
    """(d) 兜底分支不接判定（free/fixed——非检索链生成路径，维持原语义）。"""

    async def test_fixed_fallback_with_expired_card_no_notice(self, seams: Seams) -> None:
        events = await collect(chains_mod._fallback_answer(
            _deps(seams), DEFAULT_CONFIG, "什么是日产液",
            _assembly(term_cards=[_card(EXPIRED_NOTE)]),
        ))
        assert events_by_name(events).get("notice", []) == []
        text = str(events_by_name(events)["answer"][0]["text"])
        assert "台账有收录" in text and EXPIRED_NOTE in text  # 诚实文案原样（P1F-02）

    async def test_free_fallback_with_expired_card_no_notice(self, seams: Seams) -> None:
        seams.completion = "自由回答正文，日产液是口语说法。"
        cfg = replace(DEFAULT_CONFIG, fallback_strategy="free")
        events = await collect(chains_mod._fallback_answer(
            _deps(seams), cfg, "什么是日产液",
            _assembly(term_cards=[_card(EXPIRED_NOTE)]),
        ))
        assert events_by_name(events).get("notice", []) == []
        answer = events_by_name(events)["answer"][0]
        assert str(answer["text"]).endswith(d.FREE_ANSWER_TAG)


class TestServicePathIntegration:
    """(d) 整链集成：生产装卡路（loader 行→派生标注）＋分派透传，notice 在
    token 前落地、done 收场不变（svc.ask 全帧序不因新帧破坏）。"""

    async def test_notice_flows_through_service_before_tokens(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        seams.terms = [TermFace(
            term_id=9, term="日产液", type="口语缩写", def_text="作业区口语缩写",
            status="有效（已届满）", status_key="有效（已届满）",
            expires_at=date(2026, 6, 30),  # 恒过去——派生标注对现实时钟稳定
        )]
        seams.index_vector = [_hit("f1", 0.9)]
        seams.completion = "日产液指作业区口语里的日产液量，数据指引见产量月报。"
        seams.intent_reply = '{"chain": "检索问答链", "confidence": 0.9}'
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask("日产液是什么", session_id=None,
                                       page_context=None, anchors=[], actor_who=AQIANG))
        guards = _guard_notices(events)
        assert len(guards) == 1
        assert guards[0]["text"] == f"注：日产液状态标注——{EXPIRED_NOTE}"
        assert guards[0]["level"] == "warning"
        names = [frame.event for frame in events]
        guard_pos = next(
            i for i, frame in enumerate(events)
            if frame.event == "notice" and "状态标注——" in str(frame.data.get("text"))
        )
        assert guard_pos < names.index("token")  # token 流前并列呈现
        assert names[-1] == "done" and names[-2] == "answer"  # 收场合同不变

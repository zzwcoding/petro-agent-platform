"""chat S6 低分带双重重评＋LLM 改写＋rewrite 澄清帧单测（P1F-06／P-006 开发拍）。

票面验收对照（tickets/phase1-fix/README.md P1F-06）：
- (a) 0.37 形态：放宽窗口重评过闸 → 生成不弹帧（帧注记记录原分/重评分两值）；
- (b) 放宽仍低＋优化过闸＋额度在 → rewrite 澄清帧形状（subtype 透传/两选项）＋
      resume 链路自洽：选是→优化句上下文生成；选否/不选→诚实兜底；
- (c) 额度已用完（N5 已弹过一次）→ 自动作答＋「已按优化问法检索」标注、零弹帧；
- (d) 优化句也低/改写调用失败 → 诚实兜底＋S6 注记记三个分值（原句/放宽/优化句）；
- (e) <0.30 → 直接兜底（拒答克制回归——零重评零改写）。
"""

from types import SimpleNamespace
from typing import Any

from app.domains.chat import domain as d
from tests.domains.chat.conftest import (
    AQIANG,
    DEFAULT_CONFIG,
    Seams,
    collect,
    events_by_name,
    make_service,
)

# 测试问句（避开台账词/关系词/FAQ 标准问——确定性路由落检索问答链）。
LONG_QUESTION = "请帮忙梳理二季度注水开发月度动态并逐月合计对比"
OPTIMIZED_QUESTION = "二季度注水月度动态"
REWRITE_REPLY = OPTIMIZED_QUESTION


def _hit(fid: str, score: float, leg: str = "vector") -> d.IndexHitFace:
    return d.IndexHitFace(
        fragment_id=fid, report_id="rpt-1", report="N-02 完井报告",
        section="02 注水月度", snippet="注水月度明细", score=score, leg=leg,
    )


def _anchor_of(hit: d.IndexHitFace) -> d.FragmentAnchorFace:
    return d.FragmentAnchorFace(
        fragment_id=hit.fragment_id, report_id=hit.report_id,
        report=hit.report, section=hit.section,
    )


def install_dual(seams: Seams, behavior: Any) -> list[tuple[str, int]]:
    """问题感知的双路召回桩（behavior(question, vector_top_k, keyword_top_k)）——
    原句/优化句分路返回不同分数；返回调用记录 [(question, vector_top_k)]。"""
    calls: list[tuple[str, int]] = []

    async def dual(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
        seams._bump("index_dual")
        calls.append((question, vector_top_k))
        return behavior(question, vector_top_k, keyword_top_k)

    seams.search_index_dual = dual  # type: ignore[method-assign]
    return calls


def install_completer(seams: Seams, reply_by_caller: dict[str, str]) -> None:
    """caller 感知的 LLM 桩（chat.query.rewrite 等按 caller 定制回复）。"""

    async def complete(
        alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        seams._bump("complete")
        seams.completions.append(caller)
        seams.prompts.append((caller, messages))
        if caller in reply_by_caller:
            reply = reply_by_caller[caller]
            if isinstance(reply, Exception):
                raise reply
            return SimpleNamespace(content=reply, call_id="call-test", served_alias=alias)
        if caller == "chat.intent.verdict":
            if seams.fail_intent:
                raise RuntimeError("意图裁决上游失败（桩）")
            if seams.intent_reply is not None:
                return SimpleNamespace(
                    content=seams.intent_reply, call_id="call-intent", served_alias=alias
                )
        return SimpleNamespace(content=seams.completion, call_id="call-test", served_alias=alias)

    seams.complete = complete  # type: ignore[method-assign]


def _s6_text(events: list[Any]) -> str:
    """S6 全部注记（node note＋node_line text——分值断言面）。"""
    parts: list[str] = []
    for event in events:
        if event.event == "node" and event.data.get("key") == "S6":
            parts.append(str(event.data.get("note") or ""))
        if event.event == "node_line" and event.data.get("key") == "S6":
            parts.append(str(event.data.get("text") or ""))
    return " ".join(parts)


class TestRescoreBandConstants:
    """低分带语义常量（domain 单源——下沿固定 0.30、上沿随 D2 现值）。"""

    def test_rescore_band_floor_is_030(self) -> None:
        assert d.RESCORE_BAND_FLOOR == 0.30

    def test_in_rescore_band_boundaries(self) -> None:
        """0.30 ≤ score < refuse_threshold——两端边界照语义（下沿闭、上沿开）；
        上沿随阈值现值浮动（带宽随 D2 配置伸缩，不写死 0.40）。"""
        assert d.in_rescore_band(0.30, 0.40)
        assert d.in_rescore_band(0.39, 0.40)
        assert not d.in_rescore_band(0.29, 0.40)  # <0.30——直接兜底
        assert not d.in_rescore_band(0.40, 0.40)  # 过闸——不进低分带
        assert d.in_rescore_band(0.45, 0.50)  # 上沿随 D2 现值——带宽随配置伸缩
        assert not d.in_rescore_band(0.50, 0.50)

    def test_rewrite_clarify_shape(self) -> None:
        """rewrite 澄清帧形状：两选项（按优化问法作答/坚持原问法）——无 primary
        默认项（不选＝诚实兜底，不代选——同 candidates 惯例）。"""
        frame = d.build_rewrite_clarify(OPTIMIZED_QUESTION, frame_id="clarify-run-x")
        assert frame.frame_id == "clarify-run-x"
        assert OPTIMIZED_QUESTION in frame.question
        assert [c.value for c in frame.choices] == [
            d.REWRITE_CHOICE_ACCEPT, d.REWRITE_CHOICE_KEEP,
        ]
        assert "按优化问法" in frame.choices[0].label
        assert "坚持原问法" in frame.choices[1].label
        assert not any(c.primary for c in frame.choices)

    def test_chain_clarify_signal_is_internal_sentinel(self) -> None:
        """链内澄清哨兵＝域内事件（携 ClarifyFrame 对象与优化问句）——由
        service._run_chain 拦截转挂起，哨兵本体不出域。"""
        frame = d.build_rewrite_clarify(OPTIMIZED_QUESTION, frame_id="clarify-run-x")
        event = d.chain_clarify_signal(frame, subtype="rewrite",
                                       optimized_question=OPTIMIZED_QUESTION)
        assert event.event == d.FRAME_CLARIFY
        assert event.data["_chain_signal"] is True
        assert event.data["frame"] is frame
        assert event.data["subtype"] == "rewrite"
        assert event.data["optimized_question"] == OPTIMIZED_QUESTION


class TestRelaxedRescore:
    """第一道：放宽窗口重评（纯代码——topK 放宽＋父块家族随池回捞重算 best）。"""

    async def test_low_band_relaxed_rescore_passes_generates_without_frame(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(a) 0.37 形态：常规窗口 0.37 落低分带 → 放宽窗口回捞 0.55 → 过闸照常
        生成（不弹帧）；帧注记记录两值（原分/重评分）。"""
        def behavior(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
            if vector_top_k > DEFAULT_CONFIG.semantic_top_k:  # 放宽窗口——兄弟子块回捞
                return [_hit("f1", 0.37), _hit("f2", 0.55)], []
            return [_hit("f1", 0.37)], []

        calls = install_dual(seams, behavior)
        seams.anchors = {"f1": _anchor_of(_hit("f1", 0.37)),
                         "f2": _anchor_of(_hit("f2", 0.55))}
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            LONG_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        data = events_by_name(events)
        # 放宽重评过闸——不弹帧、走生成
        assert not data.get("clarify")
        assert data["answer"][0]["kind"] == "text"
        # 双路两次：常规 topK 20 → 放宽 topK 40（×2）
        assert [(q, k) for q, k in calls] == [
            (LONG_QUESTION, DEFAULT_CONFIG.semantic_top_k),
            (LONG_QUESTION, DEFAULT_CONFIG.semantic_top_k * d.RESCORE_RELAX_FACTOR),
        ]
        # 帧注记记录两值（原分/重评分）
        s6 = _s6_text(events)
        assert "0.37" in s6 and "0.55" in s6
        assert "放宽" in s6


class TestRewriteClarifyFlow:
    """第二道：LLM 改写＋双句评分 → rewrite 澄清帧（额度在）/自答（额度尽）。"""

    async def test_rewrite_frame_shape_and_resume_accept(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(b) 放宽仍低＋优化过闸＋额度在 → rewrite 帧形状/subtype 透传；resume
        选是 → 优化句上下文生成（引用照常）、不再弹帧、两跳到 done。"""
        def behavior(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
            if OPTIMIZED_QUESTION in question:
                return [_hit("f9", 0.71)], []
            return [_hit("f1", 0.37)], []

        install_dual(seams, behavior)
        install_completer(seams, {"chat.query.rewrite": REWRITE_REPLY})
        seams.anchors = {"f1": _anchor_of(_hit("f1", 0.37)),
                         "f9": _anchor_of(_hit("f9", 0.71))}
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            LONG_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        data = events_by_name(events)
        # rewrite 澄清帧形状（A1 帧 14 冻结形状＋additive subtype 透传）
        clarify = data["clarify"][0]
        assert clarify["subtype"] == "rewrite"
        assert [c["value"] for c in clarify["choices"]] == [
            d.REWRITE_CHOICE_ACCEPT, d.REWRITE_CHOICE_KEEP,
        ]
        assert OPTIMIZED_QUESTION in clarify["choices"][0]["label"]
        assert "坚持原问法" in clarify["choices"][1]["label"]
        assert not any(c.get("primary") for c in clarify["choices"])
        # interrupt 挂起——流收束不发 done
        names = [e.event for e in events]
        assert names[-1] == "clarify" and "done" not in names
        run_id = data["session"][0]["run_id"]
        run = await svc._store.get_run(run_id)
        assert run is not None and run.status == "interrupt_clarify"
        assert run.clarify_count == 1
        assert run.pending_interrupt is not None
        assert run.pending_interrupt["optimized_question"] == OPTIMIZED_QUESTION
        # 改写调用 caller 归因（gateway 记账溯源面）
        assert "chat.query.rewrite" in seams.completions

        # resume 选是——优化句上下文走生成（引用照常）
        events2 = await collect(svc.resume(
            run_id, kind="clarify", choice=d.REWRITE_CHOICE_ACCEPT,
            decision=None, reason=None, actor_who=AQIANG,
        ))
        data2 = events_by_name(events2)
        assert [e.event for e in events2][-1] == "done"
        assert not data2.get("clarify")  # 有界循环——绝不弹第二帧
        answer = data2["answer"][0]
        assert answer["kind"] == "text"
        assert answer["citations"]  # 引用照常
        # 选是腿≠额度尽自答路：答案不得含「已按优化问法检索」标注（自答路恒拼——
        # 两分支唯一可区分残差；防额度判定错位错走自答路仍判绿——T3 审查发现 B）
        assert d.RESCORED_ANSWER_TAG not in answer["text"]
        gen_prompts = [
            msgs for caller, msgs in seams.prompts if caller == "chat.retrieval.answer"
        ]
        assert gen_prompts and OPTIMIZED_QUESTION in gen_prompts[-1][-1]["content"]

    async def test_resume_keep_original_honest_fallback(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(b-否) resume 选否（坚持原问法）→ 诚实兜底（fixed 兜底文案）＋低分带
        重评跳过（放宽/改写零发起）——宁可不答不瞎猜。"""
        def behavior(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
            if OPTIMIZED_QUESTION in question:
                return [_hit("f9", 0.71)], []
            return [_hit("f1", 0.37)], []

        calls = install_dual(seams, behavior)
        install_completer(seams, {"chat.query.rewrite": REWRITE_REPLY})
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            LONG_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        run_id = events_by_name(events)["session"][0]["run_id"]
        rewrite_calls_after_ask = seams.completions.count("chat.query.rewrite")
        assert rewrite_calls_after_ask == 1  # 首跑：改写调用恰好一次（弹帧前）
        calls.clear()  # 只观察 resume 段的双路调用
        events2 = await collect(svc.resume(
            run_id, kind="clarify", choice=d.REWRITE_CHOICE_KEEP,
            decision=None, reason=None, actor_who=AQIANG,
        ))
        data2 = events_by_name(events2)
        assert [e.event for e in events2][-1] == "done"
        answer = data2["answer"][0]
        assert answer["kind"] == "alert"
        assert answer["text"] == DEFAULT_CONFIG.fallback_text  # 六路全空——配置文案原样
        # 低分带重评跳过：链内双路只调一次常规窗口（无放宽重评）、零新增改写调用
        assert calls == [(LONG_QUESTION, DEFAULT_CONFIG.semantic_top_k)]
        assert seams.completions.count("chat.query.rewrite") == rewrite_calls_after_ask
        s6 = _s6_text(events2)
        assert "坚持原问法" in s6 and "低于低分线 0.40" in s6

    async def test_resume_no_choice_honest_fallback(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(b-不选) resume 不选 → 诚实兜底（两跳到终态防卡死——不代选）。"""
        def behavior(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
            if OPTIMIZED_QUESTION in question:
                return [_hit("f9", 0.71)], []
            return [_hit("f1", 0.37)], []

        install_dual(seams, behavior)
        install_completer(seams, {"chat.query.rewrite": REWRITE_REPLY})
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            LONG_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        run_id = events_by_name(events)["session"][0]["run_id"]
        events2 = await collect(svc.resume(
            run_id, kind="clarify", choice=None, decision=None, reason=None, actor_who=AQIANG,
        ))
        data2 = events_by_name(events2)
        assert [e.event for e in events2][-1] == "done"
        assert data2["answer"][0]["kind"] == "alert"
        assert not data2.get("clarify")

    async def test_quota_used_auto_answers_with_optimized_tag(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(c) 额度已用完（N5 低置信候选澄清已弹过一次）→ 不弹第二帧：自动按
        优化句作答＋答案标注「已按优化问法检索」（写死路径）。

        N5 先弹一次（低置信 LLM 裁决＋报告候选在场——额度 0→1），锁定候选续推
        后链内落低分带 → 放宽仍低 → 改写过闸 → clarify_count 已 1 → 自动作答。"""
        def behavior(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
            if OPTIMIZED_QUESTION in question:
                return [_hit("f9", 0.71)], []
            return [_hit("f1", 0.37)], []

        install_dual(seams, behavior)
        install_completer(seams, {"chat.query.rewrite": REWRITE_REPLY})
        seams.anchors = {"f9": _anchor_of(_hit("f9", 0.71))}
        # N5 低置信＋报告候选在场 → 候选澄清帧（额度用完的第一跳）
        seams.index_hits = [
            d.IndexHitFace(fragment_id="f1", report_id="rpt-1", report="完井报告",
                           section="01", snippet="…", score=0.2, leg="vector"),
        ]
        seams.intent_reply = '{"chain": "检索问答链", "confidence": 0.1}'
        svc = make_service(chat_db, seams)
        first = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        first_data = events_by_name(first)
        assert first_data["clarify"][0]["subtype"] == "candidates"
        run_id = first_data["session"][0]["run_id"]
        # 第二跳：锁定候选续推 → 链内低分带 → 改写过闸 → 额度尽 → 自动作答
        second = await collect(svc.resume(
            run_id, kind="clarify", choice="《完井报告》01", decision=None, reason=None,
            actor_who=AQIANG,
        ))
        data2 = events_by_name(second)
        assert [e.event for e in second][-1] == "done"
        assert not data2.get("clarify")  # 零弹帧（写死路径——不弹第二帧）
        answer = data2["answer"][0]
        assert answer["kind"] == "text"
        assert answer["text"].endswith(d.RESCORED_ANSWER_TAG)
        assert answer["citations"]
        s6 = _s6_text(second)
        assert "原句 0.37" in s6 and "放宽" in s6 and "优化句 0.71" in s6
        assert "额度" in s6
        gen_prompts = [
            msgs for caller, msgs in seams.prompts if caller == "chat.retrieval.answer"
        ]
        assert gen_prompts and OPTIMIZED_QUESTION in gen_prompts[-1][-1]["content"]


class TestRewriteFailurePaths:
    """优化句也低/改写调用失败 → 诚实兜底＋三值注记。"""

    async def test_optimized_also_low_falls_back_with_three_scores(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(d) 优化句也低 → 诚实兜底；S6 帧注记记三个分值（原句/放宽/优化句）。"""
        def behavior(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
            return [_hit("f1", 0.37)], []

        install_dual(seams, behavior)
        install_completer(seams, {"chat.query.rewrite": REWRITE_REPLY})
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            LONG_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        data = events_by_name(events)
        assert not data.get("clarify")
        answer = data["answer"][0]
        assert answer["kind"] == "alert"
        assert answer["text"] == DEFAULT_CONFIG.fallback_text
        s6 = _s6_text(events)
        assert "原句 0.37" in s6
        assert "放宽重评 0.37" in s6
        assert "优化句 0.37" in s6
        assert "均低于低分线 0.40" in s6

    async def test_rewrite_call_failure_falls_back(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(d-失败) 改写调用失败 → 诚实兜底（不炸链）；注记记原句/放宽两值＋
        优化句缺。"""
        def behavior(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
            return [_hit("f1", 0.37)], []

        install_dual(seams, behavior)
        install_completer(seams, {"chat.query.rewrite": RuntimeError("改写上游失败（桩）")})
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            LONG_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        data = events_by_name(events)
        assert not data.get("clarify")
        assert data["answer"][0]["kind"] == "alert"
        s6 = _s6_text(events)
        assert "原句 0.37" in s6 and "放宽重评 0.37" in s6
        assert "优化句缺" in s6


class TestBelowBandDirectFallback:
    """<0.30 直接兜底（拒答克制回归——零重评零改写）。"""

    async def test_below_band_direct_fallback_no_rescore(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(e) best <0.30 → 直接兜底：无双路二次调用（零重评）、零改写调用。"""
        def behavior(question: str, vector_top_k: int, keyword_top_k: int) -> Any:
            return [_hit("f1", 0.25)], []

        install_dual(seams, behavior)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            LONG_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        data = events_by_name(events)
        assert data["answer"][0]["kind"] == "alert"
        assert data["answer"][0]["text"] == DEFAULT_CONFIG.fallback_text
        # 拒答克制：双路只调一次（常规窗口——无放宽重评）、零改写
        assert seams.calls.get("index_dual") == 1
        assert "chat.query.rewrite" not in seams.completions
        s6 = _s6_text(events)
        assert "拒答判定" in s6 and "低于低分线 0.40" in s6

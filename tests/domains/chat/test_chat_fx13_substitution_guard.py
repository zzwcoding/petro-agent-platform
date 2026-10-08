"""FX-13 指标替换封堵与窗界校验测试（R6-01/R6-03/R6-02——开闸前置，先红后绿）。

票面（tickets/phase3/FX-13-指标替换封堵与窗界校验.md）三件对应：
①R6-01 指标替换封堵：钉入前校验 draft.metric_slot ∈ 问句指标候选集
  （assembly.candidates kind=metric 槽位名集），不在→视同 validator 拒走兜底
  （澄清/降级照 L-05 既有形态）。红例＝L04-08（「去年各井含水率」→油压）与
  L04-09（「去年各井配产量」→日产油量）同形两例，修前红修后绿；血缘/verdict
  披露不得出现被替换指标。
②R6-03 钉入窗界：end ≤ today＋窗长上限 PINNED_WINDOW_MAX_DAYS＝366 天
  （票内定案：与快路确定性时间词函数可产最大窗「去年」闰年 366 天对齐——生效路
  不比快路同词面更严）。红例：end=明天、窗长超限各一。
③R6-02 附带：在册内换槽的已知接受态测试钉死（恢复重放复验照过＝现状行为——
  复验只守注册目录闭世界）；「DB 直写不在威胁模型内」待 Owner 明示（FX-13
  收尾报告登记呈 Owner）。

替身纪律照 L-05（tests/domains/chat/test_chat_plan_effective.py 同款形状）：
显式开关注入 make_service(plan_effective_enabled=True)；plan_reply 桩＝LLM#plan
返回；intent_reply 桩＝意图裁决返回（词面不齐/无指标候选形确定性路由不达六站链，
LLM 采信强制——L-05 同款注释惯例）。
"""

from datetime import date, timedelta
from typing import Any

from app.domains.chat import domain as d
from app.domains.chat.store import ChatStore
from app.infra.clock import now
from tests.domains.chat.conftest import (
    AQIANG,
    collect,
    default_metrics,
    events_by_name,
    make_service,
)

# 与 L-05 测试同款强制裁决（词面不齐/无指标候选形——兜底信号路由不达六站链）。
_SIX_STATION_INTENT = '{"chain": "状态机六站链", "confidence": 0.95}'
# 恢复重放底座问句（L-05 TRIGGER_QUESTION 同款——产量完成率在册未绑定形）。
_REPLAY_QUESTION = "上个月产量完成率最高的井"


def _last_year_window() -> tuple[date, date]:
    """「去年」窗端点（照 parse_time_window 去年分支同构——去年元旦至今年元旦）。"""
    today = now().date()
    start = today.replace(month=1, day=1).replace(year=today.year - 1)
    return start, today.replace(month=1, day=1)


def _plan_reply_for(slot: str, *, start: date, end: date) -> str:
    return (
        f'{{"metric_slot": "{slot}", "window": {{"start": "{start.isoformat()}", '
        f'"end": "{end.isoformat()}", "label": "去年"}}, '
        f'"limit_requested": null, "ranking": false, "direction": "desc"}}'
    )


def _pinned_plan(*, metric_slot: str = "日产油量") -> d.QueryPlan:
    """合法钉入计划（走 validator 产出——恢复重放底座，L-05 同款）。"""
    draft = d.QueryPlanDraft(
        metric_slot=metric_slot,
        window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月"),
        limit_requested=None, ranking=True, direction=d.DIRECTION_DESC,
    )
    return d.validate_query_plan_draft(draft, question=_REPLAY_QUESTION, actor=AQIANG)


async def _suspend_approval_run(
    chat_db: Any, *, question: str, plan_pinned: dict[str, Any] | None,
) -> str:
    """直构审批挂起 run（interrupt_approval＋持久化 plan_pinned——L-05 同款底座）。"""
    store = ChatStore(chat_db)
    session = await store.ensure_session(None, user_id="aqiang", title=question[:20])
    run = await store.create_run(session.id)
    run.status = "interrupt_approval"
    run.pending_approval_id = "APP-1013-t00001"
    run.pending_interrupt = {
        "kind": "approval", "scene": "extable", "approval_id": "APP-1013-t00001",
        "chain": "状态机六站链", "question": question,
        "tables": ["erp_well_register"], "plan": {}, "anchors": [],
    }
    run.plan_pinned = plan_pinned
    await store.save_run(run)
    return run.id


def _plan_calls(seams: Any) -> int:
    return seams.completions.count("chat.intent.plan")


# ---------- R6-01：指标替换封堵（红例 L04-08/L04-09 同形两例——修前红修后绿） ----------


class TestMetricSubstitutionRedExamples:
    async def test_l0408_watercut_to_oil_pressure_degrades(
        self, chat_db: Any, seams: Any
    ) -> None:
        """L04-08 形「去年各井含水率是多少？」→油压：含水率未注册——装配候选零指标
        支，LLM 换在册油压出数＝替换通道实锤（golden L05G3 同款）。封堵后：视同
        validator 拒→无候选降级解释链接续——零执行零钉入，披露零污染。"""
        seams.intent_reply = _SIX_STATION_INTENT  # 无指标候选——兜底路由不达，LLM 采信强制
        start, end = _last_year_window()
        seams.plan_reply = _plan_reply_for("油压", start=start, end=end)
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            "去年各井含水率是多少？", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        # 替换出数路径关闭：零执行、零钉入。
        assert seams.calls.get("query_exec") is None
        run_id = by_name["session"][0]["run_id"]
        run = await ChatStore(chat_db).get_run(run_id)
        assert run is not None and run.plan_pinned is None
        # 兜底照 L-05 既有形态：无候选→现状降级解释链接续（W-AUX③）。
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_DETERMINISTIC
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert any("降级解释链" in str(f.get("note")) for f in n71_finish)
        assert "answer" in by_name  # 接续检索照常收场
        assert _plan_calls(seams) == 2  # 生效路一次＋链内影子观测一次（钉入失败路）
        # 披露零污染：被替换指标「油压」不得出现在节点行与 verdict 值。
        assert all("油压" not in str(f.get("note")) for f in by_name.get("node", []))
        assert all("油压" not in str(v) for v in by_name["verdict"][0].values())

    async def test_l0409_allocation_to_daily_oil_clarifies(
        self, chat_db: Any, seams: Any
    ) -> None:
        """L04-09 形「去年各井配产量是多少？」→日产油量：配产量在册未绑定——候选集
        ＝{配产量}，LLM 换在册可出数的日产油量出数（golden L05G3 同款）。封堵后：
        视同 validator 拒→澄清额度在→candidates 澄清帧有界一次，零执行零钉入。"""
        seams.metrics = [
            *default_metrics(),
            d.MetricFace(metric_id=9, name="★配产量", slot_name="配产量",
                         ambiguous=False, calibers=[], default_caliber=None),
        ]
        start, end = _last_year_window()
        seams.plan_reply = _plan_reply_for("日产油量", start=start, end=end)
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            "去年各井配产量是多少？", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        # 替换出数路径关闭：零执行、零钉入。
        assert seams.calls.get("query_exec") is None
        # 兜底照 L-05 既有形态：候选在→澄清帧挂起（流收束不发 done）。
        verdict = by_name["verdict"][0]
        assert verdict["need_clarify"] is True
        assert verdict["chain"] is None
        assert verdict["intent_source"] == d.INTENT_SOURCE_DETERMINISTIC
        clarify = by_name["clarify"][0]
        assert clarify["subtype"] == "candidates"
        assert any(c["value"] == "配产量" for c in clarify["choices"])
        assert "done" not in by_name
        run_id = by_name["session"][0]["run_id"]
        run = await ChatStore(chat_db).get_run(run_id)
        assert run is not None
        assert run.status == "interrupt_clarify"
        assert run.clarify_count == 1
        assert run.plan_pinned is None
        assert _plan_calls(seams) == 1  # 链未分派——影子观测未发生
        # 披露零污染：被替换指标「日产油量」不得出现在节点行与 verdict 值。
        assert all("日产油量" not in str(f.get("note")) for f in by_name.get("node", []))
        assert all("日产油量" not in str(v) for v in verdict.values())


class TestMetricConsistencyPure:
    """一致性闸纯函数面（域内单测——候选集合法域与超域报文）。"""

    def test_slot_in_candidates_passes(self) -> None:
        candidates = [
            d.Candidate("指标卡台账", "日产油量", "high", "metric"),
            d.Candidate("术语台账", "躺井", "high", "term"),
        ]
        d.check_metric_slot_in_candidates("日产油量", candidates=candidates)  # 不抛

    def test_slot_out_of_candidates_rejected_with_reason(self) -> None:
        import pytest

        candidates = [d.Candidate("指标卡台账", "配产量", "high", "metric")]
        with pytest.raises(ValueError, match="指标替换封堵"):
            d.check_metric_slot_in_candidates("日产油量", candidates=candidates)

    def test_non_metric_candidates_never_open_the_door(self) -> None:
        import pytest

        candidates = [
            d.Candidate("术语台账", "油压", "high", "term"),  # 同名词条≠指标候选
            d.Candidate("报告索引", "日产液量", "high", "report"),
        ]
        with pytest.raises(ValueError, match="指标替换封堵"):
            d.check_metric_slot_in_candidates("油压", candidates=candidates)


# ---------- R6-03：钉入窗界（红例 end=明天／窗长超限各一——修前红修后绿） ----------


class TestWindowBoundsRedExamples:
    async def test_window_end_tomorrow_rejected_clarifies(
        self, chat_db: Any, seams: Any
    ) -> None:
        """end=明天红例：显式模糊词「近期」（LLM 具体化＝设计内能力）＋LLM 把窗具体
        化为含未来端点（end=明天）——时间落定守卫只兜零时间词形，本例穿透至窗界闸。
        封堵后：视同 validator 拒→候选在→澄清兜底，零执行零钉入。"""
        today = now().date()
        tomorrow = today + timedelta(days=1)
        seams.intent_reply = _SIX_STATION_INTENT  # 「近期」不在数据问句词面——词面不齐，LLM 采信强制
        seams.plan_reply = _plan_reply_for("日产油量", start=today, end=tomorrow)
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            "近期各井日产油量是多少？", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert seams.calls.get("query_exec") is None  # 未来窗不执行不返空表
        verdict = by_name["verdict"][0]
        assert verdict["need_clarify"] is True
        assert verdict["intent_source"] == d.INTENT_SOURCE_DETERMINISTIC
        assert by_name["clarify"][0]["subtype"] == "candidates"
        run_id = by_name["session"][0]["run_id"]
        run = await ChatStore(chat_db).get_run(run_id)
        assert run is not None and run.plan_pinned is None

    async def test_window_overlong_rejected_clarifies(
        self, chat_db: Any, seams: Any
    ) -> None:
        """窗长超限红例：LLM 把「近期」具体化为 400 天窗（超 PINNED_WINDOW_MAX_DAYS
        366——票内定案与快路「去年」最大窗对齐）。封堵后：澄清兜底，零执行零钉入。"""
        today = now().date()
        seams.intent_reply = _SIX_STATION_INTENT
        seams.plan_reply = _plan_reply_for(
            "日产油量", start=today - timedelta(days=400), end=today,
        )
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            "近期各井日产油量是多少？", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert seams.calls.get("query_exec") is None  # 无上界野窗不执行
        verdict = by_name["verdict"][0]
        assert verdict["need_clarify"] is True
        assert by_name["clarify"][0]["subtype"] == "candidates"
        run_id = by_name["session"][0]["run_id"]
        run = await ChatStore(chat_db).get_run(run_id)
        assert run is not None and run.plan_pinned is None


class TestWindowBoundsPure:
    """窗界闸纯函数面（域内单测——边界值与快路同形兼容）。"""

    def test_end_today_passes_end_tomorrow_rejected(self) -> None:
        import pytest

        today = date(2026, 10, 8)
        d.check_pinned_window_bounds(
            d.TimeWindow(today - timedelta(days=30), today, "近 30 天"), today=today,
        )  # end=today 过
        with pytest.raises(ValueError, match="未来窗"):
            d.check_pinned_window_bounds(
                d.TimeWindow(today, today + timedelta(days=1), "越界"),
                today=today,
            )

    def test_length_boundary_366_passes_367_rejected(self) -> None:
        import pytest

        today = date(2026, 10, 8)
        d.check_pinned_window_bounds(
            d.TimeWindow(today - timedelta(days=366), today, "366 天"), today=today,
        )  # 恰在上限——过
        with pytest.raises(ValueError, match="窗长"):
            d.check_pinned_window_bounds(
                d.TimeWindow(today - timedelta(days=367), today, "367 天"),
                today=today,
            )

    def test_last_year_window_shape_passes(self) -> None:
        """「去年」全历年窗（闰年 366 天）过闸——生效路不比快路同词面更严（票内定案）。"""
        start, end = _last_year_window()
        assert (end - start).days <= d.PINNED_WINDOW_MAX_DAYS
        d.check_pinned_window_bounds(
            d.TimeWindow(start, end, "去年"), today=now().date(),
        )  # 不抛

    def test_ground_pinned_window_carries_bounds_check(self) -> None:
        """窗界闸挂在时间落定守卫出口（钉入与复验同源消费——单点生效）：模糊词问句
        的未来窗过落定、被窗界拒；零时间词问句落默认窗后过闸。"""
        import pytest

        today = now().date()
        draft = d.QueryPlanDraft(
            metric_slot="日产油量",
            window=d.TimeWindow(today, today + timedelta(days=1), "具体化"),
            limit_requested=None, ranking=False, direction=d.DIRECTION_DESC,
        )
        plan = d.validate_query_plan_draft(draft, question="近期各井日产油量", actor=AQIANG)
        with pytest.raises(ValueError, match="未来窗"):
            d.ground_pinned_window(plan, question="近期各井日产油量", today=today)

    def test_ground_pinned_window_zero_time_words_returns_default(self) -> None:
        today = now().date()
        draft = d.QueryPlanDraft(
            metric_slot="日产油量",
            window=d.TimeWindow(today, today + timedelta(days=1), "编造"),
            limit_requested=None, ranking=False, direction=d.DIRECTION_DESC,
        )
        plan = d.validate_query_plan_draft(
            draft, question="各井日产油量是多少？", actor=AQIANG,
        )
        grounded = d.ground_pinned_window(plan, question="各井日产油量是多少？", today=today)
        assert grounded.window == d.default_time_window(today=today)  # 落默认窗零变化


# ---------- R6-02 附带：在册内换槽已知接受态（钉现状——恢复重放面） ----------


class TestReplayInRegistrySwapKnownAccepted:
    async def test_resume_in_registry_slot_swap_replay_accepts(
        self, chat_db: Any, seams: Any
    ) -> None:
        """R6-02 已知接受态（钉现状）：持久化 plan_pinned 载荷被 DB 直写把槽位换成
        另一个在册指标（日产油量→日产液量）——复验只守注册目录闭世界（在册即过），
        按换后指标执行。本测试把该现状钉死为已知接受态；「DB 直写不在威胁模型内」
        待 Owner 明示（FX-13 收尾报告登记呈 Owner——完整性封签为候选修法二）。"""
        payload = d.plan_pinned_payload(_pinned_plan())
        payload["metric_slot"] = "日产液量"  # 在册内换槽（模拟 DB 直写）
        run_id = await _suspend_approval_run(
            chat_db, question=_REPLAY_QUESTION, plan_pinned=payload,
        )
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert seams.calls.get("query_exec") == 1  # 复验过——照换后指标执行
        assert seams.executed_plans[0].metric_slot == "日产液量"
        assert seams.executed_plans[0].measure_column == "liquid_output"  # 服务端重推导
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_LLM_PLAN

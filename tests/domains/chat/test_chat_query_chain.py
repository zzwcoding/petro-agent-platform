"""M-06 问数链（状态机六站链）测试——票面 (a)-(f) 六族＋服务面审批状态机。

- (a) 六站帧序列（假数据源）：N7.1–N7.6 顺次步进＋血缘卡＋答案表卡＋done；
- (b) 槽位校验：三要素齐放行／时间窗缺参反问（askback 三选一——复用 D2 澄清帧
  设施：挂起→resume 补参续推／不选拒答终态）；
- (c) SQL 装配：模板落点（agg 三表）/LIMIT 收口（50/200 只封顶不抬底）/行级
  注入两步缝消费（执行缝回执＋谓词 AND 进语句）；
- (d) extable：越集挂起→approve 续跑／reject 零重试两路＋409/重放；
- (e) 血缘卡五要素：键序合同值＋逐行值断言；
- (f) 新鲜度：全窗未出数拒答／超窗改绑标注（照 E2 T-1 语义）；
- (g) 排名方向（M-06.fix R1）：「最低/最小/最少」→asc、默认 desc——展示 SQL 与
  执行同源同向。

装配：sqlite 底座＋Seams 假缝（conftest——假数据源/假水位；零真 LLM——链体
零模型调用是断言项）。纯语义件（时间窗/LIMIT 收口/血缘行）直测 domain 单源。
时间基准＝infra.clock 真值（B14）——窗口断言全部动态推导，不写死日期。
"""

from datetime import date, timedelta
from typing import Any

import pytest

from app.domains.chat import ChatParamError, ChatRunStateError
from app.domains.chat import domain as d
from app.domains.chat.domain import IndexHitFace
from app.domains.chat.query_store import QueryStore
from app.domains.chat.store import ChatRunRow
from app.infra.clock import now
from app.infra.db import ConnectionManager, RowDomainScope
from tests.domains.chat.conftest import (
    AQIANG,
    Seams,
    collect,
    make_service,
    node_walk,
)

TOP3_QUESTION = "上个月日产油量最高的三口井"
LOW3_QUESTION = "上个月日产油量最低的三口井"
DETAIL_QUESTION = "本月日产油量明细"
VAGUE_QUESTION = "日产油量最近怎么样"
EXTABLE_QUESTION = "上个月日产油量排名前三的井，和 ERP 井位台账对一下"

LINEAGE_KEYS = [
    "① 口径", "② 来源表", "③ 过滤条件", "　└（权限注入）", "④ 数据截至批次", "⑤ 收口注记",
]


def _today() -> date:
    return now().date()


def _prev_month_window(today: date) -> tuple[date, date]:
    """上个月半开窗（链体 parse_time_window 同款推导——断言基准单源）。"""
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    end = today.replace(day=1)
    return start, end


def _events_by_name(events: list[Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        out.setdefault(event.event, []).append(event.data)
    return out


def _run_id_of(events: list[Any]) -> str:
    return _events_by_name(events)["session"][0]["run_id"]


async def _run_row(db: ConnectionManager, run_id: str) -> ChatRunRow:
    async with db.readonly() as session:
        row = await session.get(ChatRunRow, run_id)
    assert row is not None
    return row


def _node_notes(events: list[Any]) -> list[str]:
    return [str(event.data.get("note") or "") for event in events if event.event == "node"]


def _waterline(*, late_days: int = 0) -> d.WaterlineFace:
    """汇总层水位面（E2 T-1 语义——达标＝昨天；落后 N 天·超期；基准＝infra.clock）。"""
    today = _today()
    data_date = today - timedelta(days=1 + late_days)
    tag = "达标（承诺 T-1）" if late_days <= 0 else f"落后 {late_days} 天 · 超期"
    return d.WaterlineFace(
        layer="汇总层", data_date=data_date, promise="T-1", tag=tag, late_days=late_days,
    )


# ---------- (a) 六站帧序列（假数据源端到端） ----------


class TestQueryChainFrameWalk:
    async def test_six_station_frame_sequence_end_to_end(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(a) 问数族端到端（假数据源）：裁决→六站→血缘卡→答案帧序列完整。"""
        seams.intent_reply = '{"chain": "状态机六站链", "confidence": 0.95}'
        seams.waterline = _waterline()
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            TOP3_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        # 裁决：LLM 采信状态机六站链（注册面内——N5b 不回退）。
        verdict = by_name["verdict"][0]
        assert verdict["chain"] == "状态机六站链"
        assert verdict["source"] == "llm"
        # 六站顺次步进（node 帧键序——N7.1..N7.6＋三闸 N7.4a/b/c 全在场且有序）。
        seq = [key for key, _state in node_walk(events)]
        for station in ("N7.1", "N7.2", "N7.3", "N7.4", "N7.4a", "N7.4b", "N7.4c", "N7.5", "N7.6"):
            assert station in seq, f"缺站帧：{station}（walk={seq}）"
        firsts = [seq.index(k) for k in ("N7.1", "N7.2", "N7.3", "N7.4", "N7.5", "N7.6")]
        assert firsts == sorted(firsts)  # 站序不乱
        states = dict(node_walk(events))
        for station in ("N7.1", "N7.5", "N7.6"):
            assert states[station] == "finish"
        # 零模型调用（链体——意图裁决外无生成/打分出口）。
        assert set(seams.completions) <= {"chat.intent.verdict"}
        assert seams.calls.get("query_exec") == 1
        # 帧面：tool_call（只读留痕）→ lineage（五要素）→ answer(kind=table) → done。
        assert "token" not in by_name
        assert "clarify" not in by_name
        assert "error" not in by_name
        tool_call = by_name["tool_call"][0]
        assert tool_call["readonly"] is True
        assert tool_call["rows_returned"] == 3
        assert tool_call["tables_hit"] == list(d.STAR_TABLES)
        order = [event.event for event in events]
        assert order.index("lineage") < order.index("answer")
        answer = by_name["answer"][0]
        assert answer["kind"] == "table"
        assert [col["dataIndex"] for col in answer["columns"]] == [
            "well_id", "block_name", "日产油量合计（吨）",
        ]
        assert answer["rows"][0]["well_id"] == "N-02"
        assert answer["lineage"] == by_name["lineage"][0]["items"]
        assert "done" in by_name

    async def test_llm_picked_chain_passes_wiring_check(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(a) LLM 选状态机六站链——已注册（N5b 接线核验不回退）。"""
        seams.intent_reply = '{"chain": "状态机六站链", "confidence": 0.9}'
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            TOP3_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        assert any(
            "已接线" in note and "状态机六站链" in note for note in _node_notes(events)
        )

    async def test_deterministic_data_signal_routes_query_chain(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(a) 确定性路由：指标命中＋时间/数量词面 → 状态机六站链（LLM 失败兜底面）。"""
        seams.fail_intent = True
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            TOP3_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        verdict = _events_by_name(events)["verdict"][0]
        assert verdict["chain"] == "状态机六站链"
        assert verdict["source"] == "deterministic"
        assert verdict["confidence"] == d.DATA_ROUTE_CONFIDENCE

    async def test_metric_hit_without_data_words_stays_retrieval(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(a) 回归护栏：指标命中但无时间/数量词面——仍走检索问答链（不劫走释义问法）。"""
        seams.fail_intent = True
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            "产量完成率怎么算", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        verdict = _events_by_name(events)["verdict"][0]
        assert verdict["chain"] == "检索问答链"

    async def test_unregistered_metric_degrades_then_continues(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(a/W-AUX③) 降级解释链：台账行未绑定计量列——不生成 SQL、不冒充审定
        口径、零执行；随后自动接续检索问答链＋答案帧如实标注（非权威数值）。"""
        seams.fail_intent = True
        seams.index_vector = [IndexHitFace(
            fragment_id="f1", report_id="rpt-1", report="N-02 完井报告",
            section="01 井基本情况", snippet="检泵周期记录", score=0.7, leg="vector",
            text="N-02 井检泵周期记录——报告库检索片段",
        )]
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            "上个月产量完成率排名前三", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["verdict"][0]["chain"] == "状态机六站链"  # 数据问句信号入链——链内降级
        assert any("不冒充审定口径" in note for note in _node_notes(events))  # 立场不变
        assert seams.calls.get("query_exec") is None  # 未执行取数
        assert "N7.3" not in [key for key, _state in node_walk(events)]  # 不生成 SQL
        # 接续检索问答链收场（不再以拒答收束——W-AUX③）：答案帧前置如实标注。
        answer = by_name["answer"][0]
        assert answer["kind"] == "text"
        assert "数据库口径未能出数" in str(answer["text"])


# ---------- (b) 槽位校验（齐／缺参反问——复用 D2 澄清帧设施） ----------


class TestSlotValidation:
    async def test_missing_time_window_pops_askback_clarify(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(b) 时间窗缺参（「最近」无量化）——反问帧挂起：三选一无默认项、不发 done。"""
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            VAGUE_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        clarify = by_name["clarify"][0]
        assert clarify["subtype"] == d.MISSING_SUBTYPE
        assert clarify["question"] == d.ASKBACK_TIME_QUESTION
        assert [c["value"] for c in clarify["choices"]] == list(d.ASKBACK_TIME_CHOICES)
        assert all("primary" not in c for c in clarify["choices"])  # 缺的是用户事实——无默认项
        assert "done" not in by_name
        assert seams.calls.get("query_exec") is None
        run = await _run_row(chat_db, _run_id_of(events))
        assert run.status == "interrupt_clarify"
        assert run.clarify_count == 1

    async def test_askback_choice_merges_and_continues(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(b) 补参回流：选项并入问句（输入严格变多）→ 六站续推到答案。"""
        service = make_service(chat_db, seams)
        first = await collect(service.ask(
            VAGUE_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        run_id = _run_id_of(first)
        events = await collect(service.resume(
            run_id, kind="clarify", choice="近 30 天", decision=None, reason=None,
            actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert "done" in by_name
        assert by_name["answer"][0]["kind"] == "table"
        items = by_name["lineage"][0]["items"]
        filter_line = next(i["value"] for i in items if i["key"] == "③ 过滤条件")
        assert "近 30 天" in filter_line
        run = await _run_row(chat_db, run_id)
        assert run.status == "done"

    async def test_askback_without_choice_refuses_terminal(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(b) 不选≠卡死：缺参反问无默认项——拒答终态（两跳到终态）。"""
        service = make_service(chat_db, seams)
        first = await collect(service.ask(
            VAGUE_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        run_id = _run_id_of(first)
        events = await collect(service.resume(
            run_id, kind="clarify", choice=None, decision=None, reason=None,
            actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["answer"][0]["text"] == d.REFUSE_TERMINAL_TEXT
        assert "done" in by_name
        assert seams.calls.get("query_exec") is None

    async def test_askback_invalid_choice_is_400(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        service = make_service(chat_db, seams)
        first = await collect(service.ask(
            VAGUE_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        run_id = _run_id_of(first)
        with pytest.raises(ChatParamError):
            await collect(service.resume(
                run_id, kind="clarify", choice="近 300 天", decision=None, reason=None,
                actor_who=AQIANG,
            ))

    async def test_no_time_word_takes_default_window(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(b) 无时间词——默认窗（最近 30 天）照常出数，血缘③标注「默认」。"""
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            "日产油量最高的三口井", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["answer"][0]["kind"] == "table"
        plan = seams.executed_plans[0]
        assert plan.window.is_default is True
        items = by_name["lineage"][0]["items"]
        filter_line = next(i["value"] for i in items if i["key"] == "③ 过滤条件")
        assert "默认" in filter_line


# ---------- (c) SQL 装配（落点／LIMIT／注入行） ----------


class TestSqlAssembly:
    def test_limit_parsing_and_closing(self) -> None:
        """(c) LIMIT 收口（F14 合同值）：没写补 50、超 200 截 200、只封顶不抬底。"""
        assert d.parse_row_limit("上个月产量最高的三口井") == 3
        assert d.parse_row_limit("排名前 5 的井") == 5
        assert d.parse_row_limit("TOP3") == 3
        assert d.parse_row_limit(DETAIL_QUESTION) is None
        assert d.effective_limit(None) == 50
        assert d.effective_limit(3) == 3  # 只封顶不抬底
        assert d.effective_limit(300) == 200
        assert d.effective_limit(200) == 200

    def test_time_window_parsing(self) -> None:
        today = date(2026, 10, 4)
        status, window = d.parse_time_window("上个月产量最高的三口井", today=today)
        assert status == "ok"
        assert (window.start, window.end, window.label) == (
            date(2026, 9, 1), date(2026, 10, 1), "上个月",
        )
        status, window = d.parse_time_window("近 7 天日产油量", today=today)
        assert status == "ok" and window.label == "近 7 天"
        assert (today - window.start).days == 7
        assert d.parse_time_window(VAGUE_QUESTION, today=today)[0] == "vague"
        assert d.parse_time_window("日产油量最高的三口井", today=today)[0] == "missing"
        default = d.default_time_window(today=today)
        assert default.is_default and default.label.startswith("最近 30 天")

    def test_ranking_and_external_detection(self) -> None:
        assert d.is_ranking_question("上个月日产油量最高的三口井")
        assert not d.is_ranking_question(DETAIL_QUESTION)  # 无排名词——明细型
        assert d.parse_time_window(DETAIL_QUESTION, today=date(2026, 10, 4))[0] == "ok"
        assert d.detect_external_tables("和 ERP 井位台账对一下") == ("erp_well_register",)
        assert d.detect_external_tables("引用 erp_well_register") == ("erp_well_register",)
        assert d.detect_external_tables("普通问句") == ()

    def test_render_plan_sql_star_join_and_limit(self) -> None:
        """(c) 落点：SELECT 唯一落点＝agg 星型三表（99 §2.12——join 结构即合同值）。"""
        plan = d.build_query_plan(
            metric_slot="日产油量", metric_name="★日产油量", question=TOP3_QUESTION,
            window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月"),
            today=date(2026, 10, 4), actor=AQIANG,
        )
        sql = d.render_plan_sql(plan)
        assert "FROM agg.fct_daily_metering" in sql
        assert "JOIN agg.dim_well" in sql
        assert "JOIN agg.dim_date" in sql
        assert "GROUP BY" in sql and "ORDER BY" in sql
        assert sql.endswith("LIMIT 3")
        assert "prod_date >= '2026-09-01'" in sql and "prod_date < '2026-10-01'" in sql

    def test_plan_wire_roundtrip(self) -> None:
        plan = d.build_query_plan(
            metric_slot="日产油量", metric_name="★日产油量", question=EXTABLE_QUESTION,
            window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月"),
            today=date(2026, 10, 4), actor=AQIANG,
        )
        restored = d.plan_from_wire(d.plan_to_wire(plan))
        assert restored == plan
        assert restored.external_tables == ("erp_well_register",)

    async def test_chain_feeds_executor_plan(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(c) 链体→执行缝：计划单源（绑定列/窗口/LIMIT/actor 全对齐）。"""
        service = make_service(chat_db, seams)
        await collect(service.ask(
            TOP3_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        plan = seams.executed_plans[0]
        start, end = _prev_month_window(_today())
        assert plan.metric_slot == "日产油量"
        assert plan.measure_column == "oil_output"
        assert plan.limit_effective == 3
        assert plan.ranking is True
        assert plan.actor == AQIANG
        assert (plan.window.start, plan.window.end) == (start, end)

    async def test_executor_injects_row_filter_predicates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(c) 注入行：M-01 两步缝——谓词 AND 进语句（非恒空形状可插拔验证）。"""
        import app.domains.chat.query_store as qs_mod

        captured: dict[str, str] = {}

        def fake_scope(actor: str, table: str) -> RowDomainScope:
            captured["actor"], captured["table"] = actor, table
            # 假分权谓词（渤南域——join 感知：dim_well 侧谓词由谓词自带表达，M-01 形状冻结）。
            return RowDomainScope(
                actor=actor, table=table,
                predicates=(qs_mod._DIM_WELL.c.block_name == "渤南",),
            )

        monkeypatch.setattr(qs_mod, "with_row_filter", fake_scope)
        store = QueryStore(None)  # type: ignore[arg-type]  # 只验语句装配——不触库
        plan = d.build_query_plan(
            metric_slot="日产油量", metric_name="★日产油量", question=TOP3_QUESTION,
            window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月"),
            today=date(2026, 10, 4), actor=AQIANG,
        )
        stmt, predicates = store.build_statement_with_scope(plan)
        assert captured == {"actor": AQIANG, "table": "agg.fct_daily_metering"}
        assert len(predicates) == 1
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "block_name" in compiled  # 谓词已并入语句
        assert "limit 3" in compiled

    def test_executor_preembedded_true_shape(self) -> None:
        """(c) 预埋恒真形状：谓词恒空——回执如实计 0（N7.4b 注记依据）。"""
        store = QueryStore(None)  # type: ignore[arg-type]
        plan = d.build_query_plan(
            metric_slot="日产油量", metric_name="★日产油量", question=TOP3_QUESTION,
            window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月"),
            today=date(2026, 10, 4), actor=AQIANG,
        )
        stmt, predicates = store.build_statement_with_scope(plan)
        assert predicates == ()
        assert stmt is not None


# ---------- (g) 排名方向（M-06.fix R1——底向问句不得返回倒序 TOP-N） ----------


class TestRankingDirection:
    """R1 修复：排名方向参数化——问句「最低/最小/最少」→升序、其余默认降序。"""

    def _plan(self, question: str) -> d.QueryPlan:
        return d.build_query_plan(
            metric_slot="日产油量", metric_name="★日产油量", question=question,
            window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月"),
            today=date(2026, 10, 4), actor=AQIANG,
        )

    def test_low_word_faces_take_asc(self) -> None:
        """最低词面 → asc：计划方向与展示 SQL 同向（问句形合法、路由接客）。"""
        plan = self._plan(LOW3_QUESTION)
        assert plan.ranking is True
        assert plan.direction == d.DIRECTION_ASC
        sql = d.render_plan_sql(plan)
        assert "ORDER BY SUM(m.oil_output) ASC" in sql
        assert "DESC" not in sql
        # 「最少」词面同走升序（解析面——与列绑定无关）。
        assert d.parse_ranking_direction("日产液量最少的五口井") == d.DIRECTION_ASC

    def test_high_faces_and_unrecognized_keep_desc(self) -> None:
        """desc 回归：最高/最大/排名与未识别词面——默认降序保持现行为。"""
        for question in (TOP3_QUESTION, "本月日产油量最大的井", "日产油量排名前三的井"):
            plan = self._plan(question)
            assert plan.direction == d.DIRECTION_DESC
        assert "ORDER BY SUM(m.oil_output) DESC" in d.render_plan_sql(self._plan(TOP3_QUESTION))

    def test_direction_wire_roundtrip_and_clamp(self) -> None:
        """wire 往返保方向；存量挂起载荷无 direction 键——clamp 回 desc 兼容。"""
        restored = d.plan_from_wire(d.plan_to_wire(self._plan(LOW3_QUESTION)))
        assert restored.direction == d.DIRECTION_ASC
        legacy = d.plan_to_wire(self._plan(TOP3_QUESTION))
        legacy.pop("direction")
        assert d.plan_from_wire(legacy).direction == d.DIRECTION_DESC

    def test_executor_order_by_follows_direction(self) -> None:
        """执行面同源：ORDER BY 方向随 plan（白名单二值分派——非字符串拼接）。"""
        store = QueryStore(None)  # type: ignore[arg-type]
        asc_sql = str(
            store.build_statement(self._plan(LOW3_QUESTION))
            .compile(compile_kwargs={"literal_binds": True})
        ).lower()
        desc_sql = str(
            store.build_statement(self._plan(TOP3_QUESTION))
            .compile(compile_kwargs={"literal_binds": True})
        ).lower()
        assert " asc" in asc_sql and "desc" not in asc_sql
        assert " desc" in desc_sql

    async def test_chain_feeds_asc_plan_for_low_question(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """端到端：最低问句被路由入链且产出 asc 计划——展示 SQL 与执行缝同向。"""
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            LOW3_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["answer"][0]["kind"] == "table"
        plan = seams.executed_plans[0]
        assert plan.ranking is True
        assert plan.direction == d.DIRECTION_ASC
        node_lines = [str(e.data.get("text") or "") for e in events if e.event == "node_line"]
        assert any("ORDER BY SUM(m.oil_output) ASC" in note for note in node_lines)


# ---------- (d) extable：越集挂起 → approve/reject 两路 ----------


class TestExtableApproval:
    async def _suspend(self, chat_db: ConnectionManager, seams: Seams) -> tuple[str, list[Any]]:
        """越集问句入链 → 审批挂起（返回 run_id 与挂起流帧）。"""
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            EXTABLE_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        return _run_id_of(events), events

    async def test_extable_suspends_with_approval_frame(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(d) 越集触发：approval 帧（A1 帧 15 形状）＋interrupt_approval 挂起。"""
        run_id, events = await self._suspend(chat_db, seams)
        by_name = _events_by_name(events)
        approval = by_name["approval"][0]
        assert approval["scene"] == "extable"
        assert approval["title"] == d.EXTABLE_TITLE
        assert "erp_well_register" in approval["reason"]
        assert approval["approval_id"].startswith("APP-")
        assert "audit_hint" in approval and "run " in approval["audit_hint"]
        assert "done" not in by_name and "answer" not in by_name  # 流收束不发 done
        assert seams.calls.get("query_exec") is None  # 未批准不执行
        run = await _run_row(chat_db, run_id)
        assert run.status == "interrupt_approval"
        assert run.pending_approval_id == approval["approval_id"]
        pending = run.pending_interrupt or {}
        assert pending["kind"] == "approval"
        assert pending["tables"] == ["erp_well_register"]
        assert pending["question"] == EXTABLE_QUESTION
        notes = _node_notes(events)
        assert any("erp_well_register" in note and "人工审批" in note for note in notes)

    async def test_extable_approve_resumes_to_result(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(d) 批准支：链恢复整节点重跑（F7 幂等）→ extable 答案＋审批留痕。"""
        run_id, _suspended = await self._suspend(chat_db, seams)
        run = await _run_row(chat_db, run_id)
        approval_id = run.pending_approval_id
        service = make_service(chat_db, seams)
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert any(
            "已批准" in note and approval_id in note for note in _node_notes(events)
        )
        assert seams.calls.get("query_exec") == 1  # 批后续跑执行
        answer = by_name["answer"][0]
        assert answer["kind"] == "extable"
        assert answer["decision"] == "approved"
        assert approval_id in answer["footnote"]
        assert answer["audit_no"] == approval_id
        assert answer["table"]["rows"]
        assert "lineage" not in answer  # R2 修复：血缘卡专帧承载——answer 撤合同外键
        assert "lineage" in by_name  # 血缘帧照发（审批支专帧不断）
        assert "done" in by_name
        run = await _run_row(chat_db, run_id)
        assert run.status == "done"

    async def test_extable_reject_is_zero_retry_terminal(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(d) 驳回支：权限拒答零重试（不自动改写 SQL）——extable 不强制理由。"""
        run_id, _suspended = await self._suspend(chat_db, seams)
        service = make_service(chat_db, seams)
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="reject", reason=None,
            actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        answer = by_name["answer"][0]
        assert answer["kind"] == "extable"
        assert answer["decision"] == "rejected"
        assert "不自动改写 SQL 重试" in answer["reject_notice"]
        assert "登记进可用表白名单" in answer["reject_notice"]
        assert seams.calls.get("query_exec") is None  # 零重试——不执行
        assert "done" in by_name
        run = await _run_row(chat_db, run_id)
        assert run.status == "done"

    async def test_extable_approval_decision_audited(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(d) 审批留痕审计可查（B12——chat.ask.approval；extable 纯链内闸）。"""
        import sqlite3

        run_id, _suspended = await self._suspend(chat_db, seams)
        service = make_service(chat_db, seams)
        await collect(service.resume(
            run_id, kind="approval", choice=None, decision="reject", reason=None,
            actor_who=AQIANG,
        ))
        url = str(chat_db.engine().url)
        conn = sqlite3.connect(url.removeprefix("sqlite+aiosqlite:///"))
        try:
            rows = conn.execute("SELECT action, content FROM audit_log ORDER BY id").fetchall()
        finally:
            conn.close()
        approvals = [(a, c) for a, c in rows if a == "chat.ask.approval"]
        assert approvals
        assert "erp_well_register" in approvals[0][1]
        assert "驳回" in approvals[0][1]

    async def test_invalid_decision_is_400(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        run_id, _suspended = await self._suspend(chat_db, seams)
        service = make_service(chat_db, seams)
        with pytest.raises(ChatParamError):
            await collect(service.resume(
                run_id, kind="approval", choice=None, decision="maybe", reason=None,
                actor_who=AQIANG,
            ))

    async def test_approval_resume_on_non_suspended_run_is_409(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            TOP3_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        run_id = _run_id_of(events)
        with pytest.raises(ChatRunStateError):
            await collect(service.resume(
                run_id, kind="approval", choice=None, decision="approve", reason=None,
                actor_who=AQIANG,
            ))

    async def test_extable_suspended_run_replays_approval_frame(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(d) 断线重连：interrupt_approval 挂起重放 approval 帧（不发 done）。"""
        run_id, _suspended = await self._suspend(chat_db, seams)
        service = make_service(chat_db, seams)
        events = await collect(service.replay(run_id))
        by_name = _events_by_name(events)
        assert by_name["approval"][0]["scene"] == "extable"
        assert "done" not in by_name


# ---------- (h) 锚定回流持久（M-07 F-01——挂起载荷携 anchors 回流） ----------


class TestAnchoredResume:
    """@ 锚定发起且问句正文不含指标名的问句——澄清/审批回流重装配仍锚定命中。

    缺陷（R-MAIN F-01）：挂起载荷无 anchors——@ 锚定发起且问句正文不含指标名
    的问句，澄清补参/审批批准回流后重装配拿不到指标卡，N7.1 降级「未命中注册
    指标声明」，已批准的审批出不了数。修法：挂起载荷携 anchors 回流（additive
    键）——resume 重判时锚定语义不丢。
    """

    ANCHOR = "指标卡·日产油量"  # 指标仅由 @ 锚定携带——问句正文不含指标名
    VAGUE_NO_METRIC = "最近怎么样"  # 时间窗缺参反问挂起（路由经锚定指标入链）

    async def test_anchored_askback_resume_keeps_anchor_hit(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """@ 锚定＋缺参反问→补参 resume→N7.1 仍锚定命中（不出降级、照常出数）。"""
        service = make_service(chat_db, seams)
        first = await collect(service.ask(
            self.VAGUE_NO_METRIC, session_id=None, page_context=None,
            anchors=[self.ANCHOR], actor_who=AQIANG,
        ))
        by_name = _events_by_name(first)
        assert by_name["clarify"][0]["subtype"] == d.MISSING_SUBTYPE  # 缺参反问挂起
        run_id = _run_id_of(first)
        run = await _run_row(chat_db, run_id)
        pending = run.pending_interrupt or {}
        assert pending["chain"] == "状态机六站链"
        assert pending["anchors"] == [self.ANCHOR]  # 挂起载荷携 anchors（F-01 修法面）
        events = await collect(service.resume(
            run_id, kind="clarify", choice="近 30 天", decision=None, reason=None,
            actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["assembly"][-1]["anchor_line"] == self.ANCHOR  # 锚定语义不丢
        answer = by_name["answer"][0]
        assert answer["kind"] == "table"  # 出数——非 N7.1 降级解释链
        assert "未命中注册指标声明" not in str(answer.get("text", ""))
        assert seams.calls.get("query_exec") == 1  # 批注补参后续跑执行
        assert "done" in by_name
        assert (await _run_row(chat_db, run_id)).status == "done"

    async def test_anchored_extable_approve_resume_keeps_anchor_hit(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """@ 锚定＋extable 审批→approve resume→同证：批准出数不降级。"""
        service = make_service(chat_db, seams)
        first = await collect(service.ask(
            "上个月排名前三的井，和 ERP 井位台账对一下", session_id=None,
            page_context=None, anchors=[self.ANCHOR], actor_who=AQIANG,
        ))
        by_name = _events_by_name(first)
        assert by_name["approval"][0]["scene"] == "extable"  # 首跑可达 N7.4c 挂审批
        run_id = _run_id_of(first)
        run = await _run_row(chat_db, run_id)
        pending = run.pending_interrupt or {}
        assert pending["kind"] == "approval"
        assert pending["anchors"] == [self.ANCHOR]  # 审批挂起载荷同携 anchors
        approval_id = run.pending_approval_id
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        answer = by_name["answer"][0]
        assert answer["kind"] == "extable"  # 已批准出数——非降级解释链
        assert answer["decision"] == "approved"
        assert approval_id in answer["footnote"]
        assert "未命中注册指标声明" not in str(answer.get("text", ""))
        assert seams.calls.get("query_exec") == 1  # 批准后续跑执行
        assert "done" in by_name
        assert (await _run_row(chat_db, run_id)).status == "done"


# ---------- (e) 血缘卡五要素（F13——合同值逐行） ----------


class TestLineageCard:
    async def test_five_elements_keys_and_values(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        seams.waterline = _waterline()
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            TOP3_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        items = _events_by_name(events)["lineage"][0]["items"]
        assert [item["key"] for item in items] == LINEAGE_KEYS  # 键序＝合同值不可改
        by_key = {item["key"]: item["value"] for item in items}
        assert "日产油量" in by_key["① 口径"] and "吨" in by_key["① 口径"]
        assert "台账未登记口径声明" in by_key["① 口径"]  # R4：conftest 行 calibers=[]——占位句
        assert "声明：，" not in by_key["① 口径"]  # R4：不出空声明空腔
        assert "fct_daily_metering" in by_key["② 来源表"]
        start, _end = _prev_month_window(_today())
        assert "上个月" in by_key["③ 过滤条件"] and start.isoformat() in by_key["③ 过滤条件"]
        assert "行级注入" in by_key["　└（权限注入）"] and "恒真" in by_key["　└（权限注入）"]
        assert "批次 B20260911-T3" in by_key["④ 数据截至批次"]
        assert "承诺 T-1" in by_key["④ 数据截至批次"]
        assert by_key["⑤ 收口注记"].startswith("LIMIT 3——")
        assert "只封顶不抬底" in by_key["⑤ 收口注记"]

    async def test_limit_closing_note_discovers_states(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(e) 收口注记区分「没写默认 50」与「显式条数」两态（不虚报）。"""
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            DETAIL_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        items = _events_by_name(events)["lineage"][0]["items"]
        closing = next(i["value"] for i in items if i["key"] == "⑤ 收口注记")
        assert "LIMIT 50——" in closing  # 没写补默认 50

    def test_caliber_line_empty_def_takes_placeholder(self) -> None:
        """R4（domain 单源直测）：def_text 空——占位句如实标注，不出「声明：，」空腔。"""
        plan = d.build_query_plan(
            metric_slot="日产油量", metric_name="★日产油量", question=TOP3_QUESTION,
            window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月"),
            today=date(2026, 10, 4), actor=AQIANG,
        )
        empty = d.lineage_caliber_line(plan, def_text="")
        assert "台账未登记口径声明" in empty
        assert "声明：，" not in empty
        declared = d.lineage_caliber_line(plan, def_text="井口日产原油量合计")
        assert "井口日产原油量合计" in declared
        assert "台账未登记口径声明" not in declared


# ---------- (f) 新鲜度闸（照 E2 T-1 语义） ----------


class TestFreshnessGate:
    async def test_freshness_full_miss_continues_to_retrieval(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(f/W-AUX③) 查询窗整体晚于水位——闸仍拦停执行缝（零调用不出空数），
        但不再以拒答收场：自动接续检索问答链＋答案帧如实标注（非权威数值）。"""
        seams.waterline = _waterline(late_days=9)  # 水位＝today-10
        seams.index_vector = [IndexHitFace(
            fragment_id="f1", report_id="rpt-1", report="N-02 完井报告",
            section="01 井基本情况", snippet="检泵周期记录", score=0.7, leg="vector",
            text="N-02 井检泵周期记录——报告库检索片段",
        )]
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            "今天日产油量最高的三口井", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        # 闸本体仍拦停：执行缝零调用（不出空数语义不变），拦停注记在场。
        assert seams.calls.get("query_exec") is None
        assert any("拦停，不出空数" in note for note in _node_notes(events))
        # 接续检索问答链：答案帧前置如实标注；新鲜度拒答话术不再收场。
        answer = by_name["answer"][0]
        assert answer["kind"] == "text"
        assert "数据库口径未能出数" in str(answer["text"])
        assert "不返回空数冒充" not in str(answer["text"])
        assert "done" in by_name

    async def test_freshness_partial_overlap_clamps_and_annotates(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(f) 窗口后半未出数——改绑最近可用日＋标注（E2「落后 N 天 · 超期」语义）。"""
        seams.waterline = _waterline(late_days=2)  # 水位＝today-3
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            "近 30 天日产油量最高的三口井", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["answer"][0]["kind"] == "table"
        plan = seams.executed_plans[0]
        assert plan.window.end == _today() - timedelta(days=2)  # 改绑：水位次日收口
        items = by_name["lineage"][0]["items"]
        watermark = next(i["value"] for i in items if i["key"] == "④ 数据截至批次")
        assert (_today() - timedelta(days=3)).isoformat() in watermark
        assert "落后 2 天" in watermark
        assert any("最近可用日" in note for note in _node_notes(events))

    async def test_freshness_ok_passes_through(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        seams.waterline = _waterline()  # 达标（承诺 T-1）
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            "近 3 天日产油量最高的三口井", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["answer"][0]["kind"] == "table"
        assert any("比对通过" in note and "达标" in note for note in _node_notes(events))

    async def test_waterline_missing_annotates_honestly(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """(f) 水位未回写——如实标注（不造达标假象），血缘④缺行。"""
        seams.waterline = None
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            TOP3_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["answer"][0]["kind"] == "table"
        items = by_name["lineage"][0]["items"]
        watermark = next(i["value"] for i in items if i["key"] == "④ 数据截至批次")
        assert "水位未回写" in watermark
        assert any("水位未回写" in note for note in _node_notes(events))

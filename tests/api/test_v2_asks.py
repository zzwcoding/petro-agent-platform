"""V2-07 api 层验收——specs/agent-loop.md「验收测试」表 API 侧条目 1:1 同名落测
（loop_step_sequence / manifest_present_each_call / ask_suspend_resume /
sse_cursor_resume / resume_error_paths / redecision_clarify_resume）＋
R10 verdict subtype wire 定型断言＋P-006b 触界收敛事件流形态对齐＋V1 前端
旧事件形兼容断言（web/ 零改动可连）。V2-31 ReAct 迁移：步序/剧本按 ReAct
周期（decision/discover/execute/observe/verify/answer），repair 桶退役
（拍板②拒因回喂重决策）。

接口级测试（modules.md api 卡 Seam 行——FastAPI TestClient，不起真实端口）；
runtime 侧全剧本件（ScriptedCompleter＋假引擎——tests/domains/test_v2_agent_loop.py
同款装配），api 层真件＝三端点路由＋SSE 事件桥（wire schema）＋统一错误包。

**编排面直测（RT-W5-01a／-01b 改写面）**：规格「验收测试」表里落本文件的六行
（loop_step_sequence／manifest_present_each_call／followup_asks_extend_session＝-01a；
ask_suspend_resume／sse_cursor_resume／resume_error_paths＝-01b）按主窗裁（流水 58 L0-4）
改为**直测 runtimev2 编排块**（`AgentRuntime` 黑盒，不经端点——`api` 面归尾票 RT-W5-02）；
本文件其余用例仍是端点级（旧运行时），待 RT-W5-02 改接后随其重排。

V1 前端兼容判据（web/src/api/chat.js streamChat＋web/src/landing/A1.jsx applyFrame
的机器可验面）：①帧信封 `id/event/data` 三行＋空行收束（00 §6.1 同形）；
②流以保留帧 done 收场（V1 客户端只在保留帧上干净收流——非保留帧收场按传输断
处理）；③wire 事件类型集 ⊇ V1 客户端连接机制依赖的类型（session 首帧＋
done/error 保留帧），同名类型（verdict/citation/notice）名字不变。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from appv2.api import create_app
from appv2.api.wire import FRAME_DONE, FRAME_ERROR, FRAME_SESSION, WIRE_EVENT_KINDS
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.query import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_WATERMARK,
    LineageLine,
    QueryOutcome,
)
from appv2.runtime import (
    Budget,
    ScriptedCompleter,
    ensure_agent_v2_tables,
)
from appv2.tools import FakeKnowledgeStore, FakeQueryEngine, FakeRetrievalEngine, ToolRegistry

ACTOR = {"X-Dev-User": "aqiang"}  # 身份桩（五角色键；缺头落默认角色）

# 剧本与问句（tests/domains/test_v2_agent_loop.py 同款——runtime 侧验收底座复用）。
# P-033b 缺省翻转：create_app 生产缺省＝四相位装配（ADR-0005）——api 剧本随
# 翻转迁移四相位发射形（澄清 decompose→工具匹配 matches，拒绝 legacy 直执行形）。
UNDERSTAND_DATA = "理解：问 2025 年 9 月上旬的日产油量。\n指标候选：日产油量"
CLARIFY_WINDOWED = (
    '{"thought": "台账命中＋窗已定——分解", "action": "decompose", '
    '"question_group": {"subtasks": [{"id": "s1", '
    '"question": "2025-09-01 到 09-03 各井日产油量", '
    '"ledger_notes": "日产油量｜bound｜窗 2025-09-01~09-03", "chain": "data", '
    '"tool": "data_query"}]}}'
)
TOOLMATCH_WINDOWED = (
    '{"matches": [{"id": "s1", "chain": "data", "tool": "data_query", "plan": '
    '{"metric_slot": "日产油量", "ranking": false, "window_start": "2025-09-01", '
    '"window_end": "2025-09-03", "limit": 5}}]}'
)
CLARIFY_VAGUE = (
    '{"action": "decompose", "question_group": {"subtasks": [{"id": "s1", '
    '"question": "最近的日产油量", "ledger_notes": "日产油量｜bound｜窗未定", '
    '"chain": "data", "tool": "data_query"}]}}'
)
TOOLMATCH_VAGUE = (
    '{"matches": [{"id": "s1", "chain": "data", "tool": "data_query", "plan": '
    '{"metric_slot": "日产油量", "ranking": false}}]}'
)
CLARIFY_REJECTED = '{"action": "fly"}'  # 澄清发射越界——拒因回喂轮照耗（收敛钉用）
ANSWER_DRAFT_CITED = "N-01 井 2025-09-01 日产油量 21.16 吨[1]。"
HAPPY_QUESTION = "2025 年 9 月 1 日到 3 日的日产油量"

# 四相位钉步序：understand(decision)→clarify(decision)→toolmatch(decision)→
# precondition(decision·纯代码)→batch(execute)→批量汇聚(observe)→answer(起草)→
# verify→answer(收口)。
HAPPY_STEP_KINDS = [
    "decision", "decision", "decision", "decision", "execute", "observe",
    "answer", "verify", "answer",
]

HAPPY_SCRIPT = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.decision": [CLARIFY_WINDOWED, TOOLMATCH_WINDOWED],
    "v2.runtime.answer": [ANSWER_DRAFT_CITED],
}
REDECISION_SCRIPT = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.decision": [
        CLARIFY_VAGUE, TOOLMATCH_VAGUE, CLARIFY_WINDOWED, TOOLMATCH_WINDOWED,
    ],
    "v2.runtime.answer": [ANSWER_DRAFT_CITED],
}


def _rows_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )


class QueueQueryEngine(FakeQueryEngine):
    """剧本化按次出列引擎（前 N-1 次逐个弹出，末位驻留——挂起/恢复两段剧本）。"""

    def __init__(self, outcomes: list[QueryOutcome]) -> None:
        super().__init__()
        self._queue = list(outcomes)

    def run(
        self, plan: Any, *, approved_tables: tuple[str, ...] = ()
    ) -> QueryOutcome:
        self.run_calls += 1
        if len(self._queue) > 1:
            return self._queue.pop(0)
        return self._queue[0]


async def _make_client(
    tmp_path: Any,
    *,
    engine: FakeQueryEngine,
    script: dict[str, list[str]],
    budget: Budget | None = None,
) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """接口级装配：sqlite 底座＋剧本 runtime＋真 api 层（路由＋SSE 桥＋错误包）。"""
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=engine,
        retrieval=FakeRetrievalEngine(),
    )
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "v2-chat-api.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    db = ConnectionManager([spec])
    await ensure_agent_v2_tables(db.engine())
    completer = ScriptedCompleter(script)
    app: FastAPI = create_app(db=db, registry=registry, completer=completer, budget=budget)
    with TestClient(app) as test_client:
        yield test_client, db
    await db.dispose()


@pytest.fixture
async def env(tmp_path: Any) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """happy path 底座（问数出数一轮完成）。"""
    async for pair in _make_client(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    ):
        yield pair


@pytest.fixture
async def env_budget(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """max_rounds=1 触界收敛底座（P-006b 形态对齐断言消费）——四相位：澄清发射
    被拒（越界动作）轮照耗，入口轮数闸收敛。"""
    async for pair in _make_client(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script={
            "v2.runtime.understand": [UNDERSTAND_DATA],
            "v2.runtime.decision": [CLARIFY_REJECTED],  # 末位驻留——轮轮被拒
        },
        budget=Budget(max_rounds=1),
    ):
        yield pair


@pytest.fixture
async def env_repair(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """拒因回喂→clarify→resume 底座（模糊计划→need_clarify ASK→选择后带窗重
    分解——四相位形：分解→匹配→批量执行遇缺参反问挂起→回收后带窗重走）。"""
    async for pair in _make_client(
        tmp_path,
        engine=QueueQueryEngine(
            [
                QueryOutcome.need_clarify(
                    question=ASKBACK_TIME_QUESTION,
                    choices=ASKBACK_TIME_CHOICES,
                ),
                _rows_outcome(),
            ]
        ),
        script=REDECISION_SCRIPT,
    ):
        yield pair


@pytest.fixture
async def env_followup(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """追问续会话底座（两轮剧本＋两份出数——首问与追问各走一轮完整执行链）。"""
    script = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [
            CLARIFY_WINDOWED, TOOLMATCH_WINDOWED,
            CLARIFY_WINDOWED, TOOLMATCH_WINDOWED,
        ],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED, ANSWER_DRAFT_CITED],
    }
    async for pair in _make_client(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome(), _rows_outcome()]),
        script=script,
    ):
        yield pair


@pytest.fixture
async def env_clarify(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """clarify 挂起/恢复底座（批量执行遇缺参反问——引擎 need_clarify 直入）。"""
    async for pair in _make_client(
        tmp_path,
        engine=QueueQueryEngine(
            [
                QueryOutcome.need_clarify(
                    question=ASKBACK_TIME_QUESTION,
                    choices=ASKBACK_TIME_CHOICES,
                ),
                _rows_outcome(),
            ]
        ),
        script=REDECISION_SCRIPT,
    ):
        yield pair


def _parse_frames(text: str) -> list[tuple[str, dict[str, Any]]]:
    """SSE 正文 → （event, data) 帧序列（V1 test_chat_sse 同款解析）。"""
    frames: list[tuple[str, dict[str, Any]]] = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        assert event is not None and data is not None
        frames.append((event, data))
    return frames


def _post_ask(
    client: TestClient, question: str = HAPPY_QUESTION
) -> list[tuple[str, dict[str, Any]]]:
    resp = client.post("/api/v2/chat/asks", json={"question": question}, headers=ACTOR)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache"
    return _parse_frames(resp.text)


def _step_kinds(frames: list[tuple[str, dict[str, Any]]]) -> list[str]:
    return [data["step"] for name, data in frames if name == "step"]


def _names(frames: list[tuple[str, dict[str, Any]]]) -> list[str]:
    return [name for name, _ in frames]


# ---------- 编排面装配（RT-W5-01b：行 22／26／28 直测 runtimev2 编排块，不经端点） ----------
#
# 主窗裁（流水 58 L0-4）已定：api 侧验收行改写为**直测 orchestration**（`AgentRuntime` 黑盒；
# `api` 面归尾票 `RT-W5-02`）——故本段用 runtimev2 编排块的标准测试装配（剧本 completer＋内存
# 簿记表＋假引擎），不引 `appv2/api/` 端点件。


def _v2_orchestration(
    script: dict[str, list[str]],
    *,
    engine: Any = None,
    budget: Any = None,
) -> tuple[Any, Any, Any, Any]:
    """runtimev2 装配（返回 runtime／剧本 completer／假引擎／台账投影端口）。

    台账投影（`wire_ledger_projection`）与引擎剧本在装配点一次性接好——本段的三个用例都跑在
    四相位真链上（澄清→匹配→前置条件机→批量执行→作答收口）。
    """
    from tests.domains import test_v2_four_phase as v2

    dump = v2.v2_ledger_dump()
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))
    engine = engine if engine is not None else v2.V2QueueEngine([v2._rows_outcome()])
    runtime, completer = v2.v2_runtime(
        script=script, registry=v2.v2_registry(engine=engine), budget=budget
    )
    return runtime, completer, engine, dump


async def _v2_ask(runtime: Any, question: str) -> tuple[list[Any], Any]:
    """受理形态①（提问）：返回（本腿事件流，回执）。"""
    from appv2.runtimev2.state import AskRequest

    handle = await runtime.ask(AskRequest(question=question, actor=_v2_actor()))
    return [event async for event in handle.stream], handle


def _v2_actor() -> Any:
    from appv2.infra.security import Actor

    return Actor(user_id="aqiang", display="阿强")


def _v2_windowed_turns(note: str) -> tuple[str, str]:
    """一轮四相位发射（澄清分解＋工具匹配——窗已定），供剧本复用。"""
    from tests.domains import test_v2_four_phase as v2

    return (
        v2.v2_decompose(
            subtask_id="s1",
            question="2025-09-01 到 09-03 各井日产油量",
            ledger_notes=note,
            chain="data",
        ),
        v2.v2_matches(
            v2.v2_data_match(
                subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
            )
        ),
    )


async def _v2_resume(runtime: Any, run_id: str, choice: Any) -> tuple[list[Any], Any]:
    """受理形态（resume）：返回（本腿事件流，回执）。"""
    handle = await runtime.resume(run_id, choice)
    return [event async for event in handle.stream], handle


# ---------- 验收③ ask_suspend_resume：工具 ask 挂起→GET waiting_ask→resume ----------


async def test_ask_suspend_resume() -> None:
    """行 22｜工具返回 ask→run 挂起→GET 状态 waiting_ask→resume 完成。

    工具侧（引擎）返回 `status=ask`（缺参反问）→run 转 `waiting_ask` 挂起（`ask` 帧出流后本腿
    收束）→读面状态 `waiting_ask`（`pending_ask`＝挂起帧投影）→`resume` 带选择续跑至完成——
    跨腿续编不重启游标（钉 `pin-29` 闭环面·工具侧形态）。
    """
    from appv2.infra.clock import freeze
    from appv2.runtimev2.persistence import RunStore
    from appv2.runtimev2.state import AskChoice
    from tests.domains import test_v2_four_phase as v2

    engine = v2.V2QueueEngine(
        [
            QueryOutcome.need_clarify(
                question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES
            ),
            v2._rows_outcome(),
        ]
    )
    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    first, second = _v2_windowed_turns(note)
    script = {
        "understand": [v2.V2_UNDERSTAND],
        "decision": [first, second, first, second],
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    runtime, _completer, _engine, _dump = _v2_orchestration(script, engine=engine)

    with freeze("2026-10-08T09:00:00"):
        events, _handle = await _v2_ask(runtime, "最近的日产油量")
        asks = [event.data for event in events if event.event == "ask"]
        assert asks, "ASK 帧未出流"
        frame = asks[-1]["frame"]
        assert frame["kind"] == "clarify"
        assert frame["options"] == list(ASKBACK_TIME_CHOICES)
        # 挂起收束：ask 帧之后的收口帧 status=waiting_ask（本腿止于此；`done` 归开流段）
        assert events[-1].event == "verdict" and events[-1].data["status"] == "waiting_ask"

        run_id = asks[-1]["run_id"]
        row = RunStore().run(run_id)
        assert row is not None and row.status == "waiting_ask"  # 读面状态（GET 投影真源）
        assert RunStore().load(run_id).pending_ask == frame  # 挂起帧投影随状态在场

        resumed, resumed_handle = await _v2_resume(
            runtime, run_id, AskChoice(kind="clarify", choice="近 3 天")
        )
    assert resumed[-1].event == "blackbox" and resumed[-1].data["status"] == "completed"
    assert RunStore().run(run_id).status == "completed"
    assert "21.16" in (RunStore().run(run_id).answer or "")
    # 同链续推＋跨腿续编：恢复腿从上一腿收口帧之后起（不重启游标、不重放已完成部分）
    assert resumed_handle.cursor == events[-1].seq + 1
    assert all(event.seq >= resumed_handle.cursor for event in resumed)
    assert not [event for event in resumed if event.event == "ask"]
    assert engine.run_calls == 2  # 首投挂起（引擎未出数）＋恢复后续跑恰一次
    state = RunStore().load(run_id)
    assert state.resume_choices[-1]["choice"] == "近 3 天"
    assert state.pending_ask is None


# ---------- 验收④ sse_cursor_resume：断线游标重连不重复不遗漏 ----------


async def test_sse_cursor_resume() -> None:
    """行 26｜断线游标重连→事件不重复不遗漏。

    受理形态②（`resume_run_id`＝断线重连）复用**同一 run 的活体总线**（历史缓冲——不新起 run、
    不重跑相位）：重放流＝该 run 全流（同 `seq`／同 `event`／同 `data`，重放不位移）；客户端以任一
    帧 `id` 回送时换算 `cursor = id + 1`（排他起点），续推即原流「`seq ≥ cursor`」后缀——不重复、
    不遗漏（真源 `specs/transport.md` 行为 5；游标全流单调＝行为 3「跨段不重启」）。
    """
    from appv2.infra.clock import freeze
    from appv2.runtimev2.state import AskRequest
    from tests.domains import test_v2_four_phase as v2

    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    first, second = _v2_windowed_turns(note)
    script = {
        "understand": [v2.V2_UNDERSTAND],
        "decision": [first, second],
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    runtime, _completer, _engine, _dump = _v2_orchestration(script)
    with freeze("2026-10-08T09:00:00"):
        events, _handle = await _v2_ask(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
        run_id = events[-1].data["run_id"]
        reconnected = await runtime.ask(AskRequest(resume_run_id=run_id, actor=_v2_actor()))
        replay = [event async for event in reconnected.stream]
        again = [
            event
            async for event in (
                await runtime.ask(AskRequest(resume_run_id=run_id, actor=_v2_actor()))
            ).stream
        ]

    # 全流单调：0 起、严格递增、无跳号无重复
    assert [event.seq for event in replay] == list(range(len(replay)))
    assert replay[0].seq == 0
    # 重放不位移：两次重放逐帧同 seq／同 event／同 data
    assert [(event.seq, event.event, event.data) for event in again] == [
        (event.seq, event.event, event.data) for event in replay
    ]
    assert [(event.seq, event.event, event.data) for event in replay] == [
        (event.seq, event.event, event.data) for event in events
    ]
    assert events[-1].event == "blackbox"

    # 断点续推（不重复不遗漏）：以任一帧 `id` 换算 `cursor = id + 1`，得原流后缀逐帧相等
    assert all(_envelope_id(event) == event.seq for event in events)  # 事件帧 `id`＝自身 `seq`
    for cursor in (1, len(events) // 2, len(events) - 1):
        last_event = next(event for event in events if event.seq == cursor - 1)
        assert _envelope_id(last_event) + 1 == cursor  # 客户端算式（行为 5 排他起点）
        suffix = [event for event in replay if event.seq >= cursor]
        assert [event.seq for event in suffix] == list(range(cursor, len(events)))
        assert suffix == [event for event in events if event.seq >= cursor]

    # 重连不新起 run：同一 run 行、状态与答案不变
    from appv2.runtimev2.persistence import RunStore

    assert RunStore().run(run_id).status == "completed"


def _envelope_id(frame: Any) -> int:
    """信封 `id:` 行读数（信封字节形真源＝`transport.envelope`——本处只解析首行）。"""
    from appv2.runtimev2.transport import envelope

    return int(envelope(frame).splitlines()[0].removeprefix("id: "))


def test_sse_replay_from_zero_replays_all_events(env: Any) -> None:
    """断点 0（只收到 session 帧即断）→重放全部事件＋done；无 Last-Event-ID 头
    ＝全量重放（缺省游标 0）。"""
    client, _db = env
    first = _post_ask(client)
    run_id = first[0][1]["run_id"]
    events = [f for f in first if f[0] not in (FRAME_SESSION, FRAME_DONE)]
    for headers in (ACTOR, {**ACTOR, "Last-Event-ID": "0"}):
        replay = _parse_frames(client.post(
            "/api/v2/chat/asks", json={"resume_run_id": run_id}, headers=headers,
        ).text)
        assert replay[1:-1] == events
        assert _names(replay)[-1] == FRAME_DONE


def test_sse_replay_unknown_run_is_404(env: Any) -> None:
    """重连 run 不存在＝无可恢复对象——开流前 404（错误码行）。"""
    client, _db = env
    resp = client.post(
        "/api/v2/chat/asks", json={"resume_run_id": "run-missing"}, headers=ACTOR,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "chat_run_not_found"


def test_invalid_last_event_id_returns_400(env: Any) -> None:
    """Last-Event-ID 非整数＝请求还没进门——HTTP 400 错误包不开流（00 §3.2）。"""
    client, _db = env
    resp = client.post(
        "/api/v2/chat/asks",
        json={"resume_run_id": "run-x"},
        headers={**ACTOR, "Last-Event-ID": "abc"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "chat_last_event_id_invalid"


# ---------- 验收⑤ resume_error_paths：404/409 ----------


async def test_resume_error_paths() -> None:
    """行 28｜resume/追问错误路径（404／409／互斥 409）。

    四条路径各自落到**具名错误源**（`api` 侧的 404／409 映射据此单点——错误码行真源
    `specs/agent-loop.md` 接口定义节：「404 run 不存在｜409 run 非挂起态不可 resume（重连/追问
    互斥同 409）」）：

    ① `resume` 到不存在的 run → 404 源异常；② `resume` 到非挂起态（completed）的 run → 409 源
    异常；③ 重连（`resume_run_id`）到不存在／不可达的 run → 404 源异常；④ 追问（`followup_run_id`）
    不存在 → 404 源异常、前轮未收口 → 409 源异常；⑤ 受理形态②③同在场 → 参数错误（互斥 409 面）。
    """
    from appv2.infra.clock import freeze
    from appv2.runtimev2.orchestration import RunNotFoundError, RunNotSuspendedError
    from appv2.runtimev2.state import AskChoice, AskRequest
    from tests.domains import test_v2_four_phase as v2

    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    first, second = _v2_windowed_turns(note)
    script = {
        "understand": [v2.V2_UNDERSTAND],
        "decision": [first, second],
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    runtime, _completer, _engine, _dump = _v2_orchestration(script)
    choice = AskChoice(kind="clarify", choice="近 3 天")

    with freeze("2026-10-08T09:00:00"):
        # ① resume 不存在的 run → 404 源
        with pytest.raises(RunNotFoundError):
            await runtime.resume("run-not-exist", choice)
        # ③ 重连不存在的 run → 404 源（无该 run 的流缓冲）
        with pytest.raises(RunNotFoundError):
            await runtime.ask(AskRequest(resume_run_id="run-missing", actor=_v2_actor()))
        # ④ 追问不存在的前轮 → 404 源
        with pytest.raises(RunNotFoundError):
            await runtime.ask(
                AskRequest(question="那 9 月 2 日呢？", followup_run_id="run-missing",
                           actor=_v2_actor())
            )
        # 走完一个 completed run
        events, _handle = await _v2_ask(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    run_id = events[-1].data["run_id"]
    assert events[-1].data["status"] == "completed"

    # ② resume 非挂起态 run → 409 源（不能静默重开）
    with pytest.raises(RunNotSuspendedError):
        await runtime.resume(run_id, choice)

    # ⑤ 受理形态②③互斥（同在场）→ 参数错误（互斥 409 的源面）
    with pytest.raises(ValueError):
        AskRequest(
            question="那 9 月 2 日呢？", resume_run_id=run_id, followup_run_id=run_id,
            actor=_v2_actor(),
        )
    # ⑤′ 追问挂起中的前轮 → 409 源（在途轮走 resume，不可追问）
    suspended = v2.V2QueueEngine(
        [QueryOutcome.need_clarify(question=ASKBACK_TIME_QUESTION,
                                   choices=ASKBACK_TIME_CHOICES)]
    )
    script_ask = {
        "understand": [v2.V2_UNDERSTAND],
        "decision": [first, second],
        "answer": ["答案。"],
    }
    runtime2, _c2, _e2, _d2 = _v2_orchestration(script_ask, engine=suspended)
    with freeze("2026-10-08T09:05:00"):
        pending_events, _h2 = await _v2_ask(runtime2, "最近的日产油量")
    pending_run = [event.data["run_id"] for event in pending_events if event.event == "ask"][-1]
    with pytest.raises(RunNotSuspendedError):
        await runtime2.ask(
            AskRequest(question="那 9 月 2 日呢？", followup_run_id=pending_run,
                       actor=_v2_actor())
        )


def test_resume_body_shape_guards(env_clarify: Any) -> None:
    """resume 入参形状 400：clarify 缺 choice／approval 缺 decision＝
    chat_param_invalid（业务形状闸，开流前）；kind/decision 枚举越界＝
    request_invalid（pydantic 校验——00 §3.2 统一收口 400）。"""
    client, _db = env_clarify
    frames = _post_ask(client, "最近的日产油量")
    run_id = frames[0][1]["run_id"]
    for body, code in (
        ({"kind": "clarify"}, "chat_param_invalid"),
        ({"kind": "clarify", "choice": "  "}, "chat_param_invalid"),
        ({"kind": "approval"}, "chat_param_invalid"),
        ({"kind": " unknown", "choice": "x"}, "request_invalid"),
        ({"kind": "approval", "decision": "maybe"}, "request_invalid"),
    ):
        resp = client.post(f"/api/v2/chat/runs/{run_id}/resume", json=body, headers=ACTOR)
        assert resp.status_code == 400, (body, resp.text)
        assert resp.json()["code"] == code, (body, resp.text)


# ---------- 验收⑥ redecision_clarify_resume：拒因回喂重决策→ASK→resume ----------
# （V2-31 拍板②：repair 桶退役——模糊计划经 need_clarify 挂起，用户选择回喂
#   重决策；原 plan_repair_clarify_resume 的 ReAct 同位测试。）


def test_redecision_clarify_resume(env_repair: Any) -> None:
    """模糊计划→引擎 need_clarify ASK 帧→resume 选择回喂→带窗重分解→出答案
    （四相位：回收后轮预算重置，分解/匹配发射留痕在案，恢复段出 citation）。"""
    client, _db = env_repair
    frames = _post_ask(client, "最近的日产油量")
    run_id = frames[0][1]["run_id"]
    decision_titles = [
        data["title"]
        for name, data in frames
        if name == "step" and data["step"] == "decision"
    ]
    assert any(t.startswith("澄清 r1：分解") for t in decision_titles)
    assert any("工具匹配" in t for t in decision_titles)
    ask_frames = [data for name, data in frames if name == "ask"]
    assert ask_frames and ask_frames[0]["frame"]["kind"] == "clarify"

    resumed = client.post(
        f"/api/v2/chat/runs/{run_id}/resume",
        json={"kind": "clarify", "choice": "近 3 天"},
        headers=ACTOR,
    )
    assert resumed.status_code == 200
    second = _parse_frames(resumed.text)
    assert any(name == "citation" for name, _ in second)
    assert _names(second)[-1] == FRAME_DONE
    done = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR)
    assert done.json()["status"] == "completed"


# ---------- R10：verdict 事件拆 subtype（wire schema 定型断言） ----------


def test_verdict_subtype_wire_schema(env: Any) -> None:
    """verify 步 verdict 载 {supported,rewritten,split,cited}＋subtype=verify；
    终局 verdict 载 {status,run_id,manifest_digest}＋subtype=final——两形按
    subtype 判别（消费面不再靠键猜载荷形态）。V2-50 起 verify 判定增 additive
    键 attribution（{anchors, cross}——族 C 归属审机读锚；行为变化，L0 追认
    注记：键集由四键扩五键，四原键语义零漂移）。"""
    client, _db = env
    frames = _post_ask(client)
    verdicts = [data for name, data in frames if name == "verdict"]
    assert len(verdicts) == 2
    verify, final = verdicts
    assert verify["subtype"] == "verify"
    assert set(verify) == {
        "subtype", "supported", "rewritten", "split", "cited", "attribution",
    }
    assert verify["attribution"]["cross"] == []  # 无实体题/全对齐＝审静默
    assert verify["cited"] == [1] and verify["supported"] == 1 and verify["rewritten"] == 0
    assert final["subtype"] == "final"
    assert set(final) == {"subtype", "status", "run_id", "manifest_digest"}
    assert final["run_id"] == frames[0][1]["run_id"]
    # 流序：起草 answer 步→verify 步→verify 判定→收口 answer 步→终局判定收尾。
    order = [
        ("step", data["step"]) if name == "step" else ("verdict", data["subtype"])
        for name, data in frames
        if name in ("step", "verdict")
    ]
    assert order[-5:] == [
        ("step", "answer"), ("step", "verify"), ("verdict", "verify"),
        ("step", "answer"), ("verdict", "final"),
    ]


# ---------- P-006b 形态对齐：触界收敛 run 事件流＝answer 步＋text＋终局 verdict ----------


def test_budget_converged_stream_shape(env_budget: Any) -> None:
    """max_rounds=1 触界收敛：四相位澄清发射被拒轮照耗，入口轮数闸收敛——收敛
    答案落 answer 步＋text 事件出流＋恰一机读 notice（budget_converged）＋终局
    verdict 收尾（P-006b·R1 修复后形态）。"""
    client, _db = env_budget
    frames = _post_ask(client)
    assert _step_kinds(frames) == ["decision", "decision", "answer"]
    texts = [data["content"] for name, data in frames if name == "text"]
    assert any("没能查到能回答" in t for t in texts)  # 如实回报——不编造（V2-80d 人话壳单源）
    notices = [data for name, data in frames if name == "notice"]
    assert len(notices) == 1 and notices[0]["type"] == "budget_converged"
    verdicts = [data for name, data in frames if name == "verdict"]
    assert [v["subtype"] for v in verdicts] == ["final"]  # 零 verify 判定——直达终局
    assert _names(frames)[-1] == FRAME_DONE
    run_id = frames[0][1]["run_id"]
    assert client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR).json()["status"] == "completed"


# ---------- V1 前端旧事件形兼容断言（web/ 零改动可连） ----------


def test_v1_wire_form_compatible(env: Any) -> None:
    """V1 前端旧事件形兼容三判据：
    ①帧信封字节形＝00 §6.1（id/event/data 三行＋空行收束，中文不转义）；
    ②wire 事件类型集 ⊇ V1 客户端连接机制依赖集（session 首帧＋done/error 保留帧）
      且同名业务类型（verdict/citation/notice）名字不变；
    ③每帧正则以 V1 render_frame 同形渲染（流内逐帧可断）。"""
    client, _db = env
    resp = client.post("/api/v2/chat/asks", json={"question": HAPPY_QUESTION}, headers=ACTOR)
    text = resp.text
    # ①首帧字节形（session 携 run_id——json.dumps 键序与分隔符同 V1 render_frame）。
    first_block = text.split("\n\n")[0]
    run_id = json.loads(first_block.split("\n")[2].removeprefix("data: "))["run_id"]
    assert first_block + "\n\n" == (
        f'id: 0\nevent: session\ndata: {{"run_id": "{run_id}", "resume": false}}\n\n'
    )
    # ②类型集超集断言（V1 客户端机制类型＋同名业务类型）。
    assert {FRAME_SESSION, FRAME_DONE, FRAME_ERROR} <= WIRE_EVENT_KINDS
    assert {"verdict", "citation", "notice"} <= WIRE_EVENT_KINDS
    # ③全流帧行结构：每块恒 id/event/data 三行（SSE 帧界＝空行）。
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        lines = block.split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("id: ") and lines[1].startswith("event: ")
        assert lines[2].startswith("data: ")
    # 中文不转义（00 §6.1——V1 render_frame ensure_ascii=False 同形）。
    assert "日产油量" in text  # understand 步 title 原文出流（非 \\u 转义形态）


# ---------- 验收⑦ 追问续会话（V2-38/ADR-0006）：followup_run_id 会话线程新轮 ----------


def test_followup_requires_question(env_followup: Any) -> None:
    """追问缺 question＝400（提问必填与普通 ask 同闸）。"""
    client, _db = env_followup
    frames = _post_ask(client)
    run_id = frames[0][1]["run_id"]
    resp = client.post(
        "/api/v2/chat/asks", json={"followup_run_id": run_id}, headers=ACTOR,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "chat_param_invalid"


def test_followup_unknown_run_is_404(env: Any) -> None:
    """追问前轮不存在＝404（开流前错误包）。"""
    client, _db = env
    resp = client.post(
        "/api/v2/chat/asks",
        json={"question": "追问", "followup_run_id": "run-missing"},
        headers=ACTOR,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "chat_run_not_found"


def test_followup_unfinished_run_is_409(env_clarify: Any) -> None:
    """前轮未收口（waiting_ask）＝409 状态机冲突——挂起轮走 resume，不走追问。"""
    client, _db = env_clarify
    frames = _post_ask(client, "最近的日产油量")
    run_id = frames[0][1]["run_id"]
    status = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR)
    assert status.json()["status"] == "waiting_ask"
    resp = client.post(
        "/api/v2/chat/asks",
        json={"question": "追问", "followup_run_id": run_id},
        headers=ACTOR,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "chat_run_state"


def test_resume_and_followup_together_is_409_not_silent(env: Any) -> None:
    """C7 钉（P-032b）：resume_run_id 与 followup_run_id 同在场＝显式 409 互斥
    拒绝——不开流、不出 run（重连形态不重新执行，同在场的 followup 不许被静默
    忽略）；机读注记在错误包 detail（conflict 键点名互斥两参）。"""
    client, _db = env
    frames = _post_ask(client)
    run_id = frames[0][1]["run_id"]
    resp = client.post(
        "/api/v2/chat/asks",
        json={"question": "那 9 月 2 日呢？", "resume_run_id": run_id,
              "followup_run_id": run_id},
        headers=ACTOR,
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == "chat_run_state"
    assert body["detail"]["conflict"] == ["resume_run_id", "followup_run_id"]
    assert body["detail"]["resume_run_id"] == run_id
    assert body["detail"]["followup_run_id"] == run_id
    # 无静默路径：互斥拒绝＝新 run 零发生（GET 该 run 仍是原 completed 行）。
    assert client.get(
        f"/api/v2/chat/runs/{run_id}", headers=ACTOR
    ).json()["status"] == "completed"


# ---------- 错误码 400/401/404/409（接口定义节错误行） ----------


def test_ask_param_and_actor_guards(env: Any) -> None:
    """question 为空→400；非五角色键→401；缺头落默认角色不 401（00 §2.4）。"""
    client, _db = env
    for body in (None, {"question": ""}, {"question": "   "}):
        resp = client.post("/api/v2/chat/asks", json=body, headers=ACTOR)
        assert resp.status_code == 400, resp.text
        assert resp.json()["code"] == "chat_param_invalid"

    bad_actor = client.post(
        "/api/v2/chat/asks", json={"question": "产量"}, headers={"X-Dev-User": "not-a-role"},
    )
    assert bad_actor.status_code == 401
    assert bad_actor.json()["code"] == "security_unauthenticated"

    ok = client.post("/api/v2/chat/asks", json={"question": HAPPY_QUESTION})
    assert ok.status_code == 200  # 缺头＝默认角色（身份桩语义不被改写）
    assert _parse_frames(ok.text)[0][0] == FRAME_SESSION


def test_get_unknown_run_is_404(env: Any) -> None:
    """GET 不存在 run→404（错误码行）。"""
    client, _db = env
    resp = client.get("/api/v2/chat/runs/run-missing", headers=ACTOR)
    assert resp.status_code == 404
    assert resp.json()["code"] == "chat_run_not_found"


# ---------- 编排面三钉（RT-W5-01a：行 17／18／29——直测 runtimev2 编排块，不经端点） ----------


async def _v2_loop_run() -> tuple[Any, Any, str]:
    """四相位 run（收口完成）——返回 (events, 剧本 completer, run_id)。"""
    from tests.domains.test_v2_multi_turn_context import _v2_e2e_run

    events, completer, run_id, _tables = await _v2_e2e_run(
        question="2025 年 9 月 1 日到 3 日的日产油量"
    )
    return events, completer, run_id


async def test_loop_step_sequence() -> None:
    """行 17｜提问→事件流步序（understand→四相位→answer 次序）。"""
    from appv2.runtimev2.persistence import RunStore

    events, _completer, run_id = await _v2_loop_run()
    assert events[-1].event == "blackbox"
    assert events[-1].data["status"] == "completed"

    steps = RunStore().steps(run_id)
    kinds = [row.step for row in steps]
    titles = [row.title for row in steps]
    assert kinds[0] == "decision" and titles[0].startswith("模型调用：understand")  # ①读题
    assert kinds[-1] == "answer"  # 收口
    assert kinds.index("execute") < kinds.index("verify") <= len(kinds) - 1
    # 四相位次序：澄清 → 前置条件机 → 批量执行 → 汇总／核验
    assert any("澄清 r1" in title for title in titles)
    assert any("前置条件机" in title for title in titles)
    assert any("data_query" in title for title in titles)
    assert any("起草答案" in title for title in titles)
    phases = [(row.payload or {}).get("phase") for row in steps]
    assert "clarify" in phases and "precondition" in phases and "execution" in phases


async def test_manifest_present_each_call() -> None:
    """行 18｜每个模型调用 step 落 Manifest（来源/版本/token——键集恒在场）。"""
    from appv2.runtimev2.persistence import RunStore
    from appv2.runtimev2.state import Manifest

    _events, _completer, run_id = await _v2_loop_run()
    calls = [
        row for row in RunStore().steps(run_id) if row.title.startswith("模型调用：")
    ]
    assert len(calls) >= 3  # understand／decision ×2／answer
    keys = set(Manifest().as_dict())
    for row in calls:
        assert isinstance(row.manifest, dict)  # 键恒在场、不省略
        assert set(row.manifest) == keys
        assert isinstance(row.manifest["token_count"], int)
        assert isinstance(row.manifest["source_type"], list)
        assert isinstance(row.manifest["version"], list)


async def test_followup_asks_extend_session() -> None:
    """行 29｜追问端点会话线程延展（新 run 播种前轮历史——钉 `pin-23` 的编排动作面）。"""
    from appv2.runtimev2.persistence import RunStore
    from tests.domains.test_v2_multi_turn_context import _v2_e2e_run

    events1, _c1, run1, tables = await _v2_e2e_run(question="2025 年 9 月 1 日到 3 日的日产油量")
    assert events1[-1].data["status"] == "completed"
    chain1 = RunStore().load(run1).messages

    events2, completer2, run2, _ = await _v2_e2e_run(
        question="再补充一问：W-111 井呢？", followup_of=run1, tables=tables
    )
    assert events2[-1].data["status"] == "completed"
    row2 = RunStore().run(run2)
    assert row2 is not None and row2.followup_of == run1  # 追问链前轮落 run 行
    chain2 = RunStore().load(run2).messages
    assert chain2[: len(chain1)] == chain1  # 前轮整链承接（跨 run 前缀延伸）
    assert chain2[len(chain1)]["content"] == "再补充一问：W-111 井呢？"  # 新问接在前链之后
    seeded = "\n".join(
        str(message.get("content", "")) for message in completer2.messages_of("decision")[0]
    )
    assert "2025 年 9 月 1 日到 3 日的日产油量" in seeded

"""V2-07 api 层验收——specs/agent-loop.md「验收测试」表 API 侧六条 1:1 同名落测
（loop_step_sequence / manifest_present_each_call / ask_suspend_resume /
sse_cursor_resume / resume_error_paths / plan_repair_clarify_resume）＋
R10 verdict subtype wire 定型断言＋P-006b 触界收敛事件流形态对齐＋V1 前端
旧事件形兼容断言（web/ 零改动可连）。

接口级测试（modules.md api 卡 Seam 行——FastAPI TestClient，不起真实端口）；
runtime 侧全剧本件（ScriptedCompleter＋假引擎——tests/domains/test_v2_agent_loop.py
同款装配），api 层真件＝三端点路由＋SSE 事件桥（wire schema）＋统一错误包。

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
UNDERSTAND_DATA = "理解：问 2025 年 9 月上旬的日产油量。\n指标候选：日产油量"
PLAN_WINDOWED = (
    '{"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}'
)
PLAN_VAGUE = '{"metric_slot": "日产油量", "ranking": false}'
PLAN_NO_SLOT = '{"ranking": false}'  # 缺 metric_slot 的半形计划（bad_args→repair 源）
ANSWER_DRAFT_CITED = "N-01 井 2025-09-01 日产油量 21.16 吨[1]。"
HAPPY_QUESTION = "2025 年 9 月 1 日到 3 日的日产油量"

HAPPY_SCRIPT = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.plan": [PLAN_WINDOWED],
    "v2.runtime.answer_draft": [ANSWER_DRAFT_CITED],
}
REPAIR_SCRIPT = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.plan": [PLAN_NO_SLOT, PLAN_WINDOWED],  # repair 后带窗计划
    "v2.runtime.plan_repair": [PLAN_VAGUE],  # repair 一轮：消模糊（出 clarify 源）
    "v2.runtime.answer_draft": [ANSWER_DRAFT_CITED],
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

    def run(self, plan: Any) -> QueryOutcome:
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
    """max_steps=3 触界收敛底座（P-006b 形态对齐断言消费）。"""
    async for pair in _make_client(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script=HAPPY_SCRIPT,
        budget=Budget(max_steps=3),
    ):
        yield pair


@pytest.fixture
async def env_repair(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """repair→clarify→resume 底座（计划校验失败源＝缺 metric_slot 半形计划）。"""
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
        script=REPAIR_SCRIPT,
    ):
        yield pair


@pytest.fixture
async def env_clarify(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """clarify 挂起/恢复底座（模糊计划直入 need_clarify——无 repair 前置）。"""
    script = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.plan": [PLAN_VAGUE, PLAN_WINDOWED],
        "v2.runtime.answer_draft": [ANSWER_DRAFT_CITED],
    }
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
        script=script,
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


# ---------- 验收① loop_step_sequence：六类 step 按合同次序 ----------


def test_loop_step_sequence(env: Any) -> None:
    """正常提问→事件流含六类 step 且按 understand→…→answer 次序（首帧 session
    携 run_id；保留帧 done 收场）。"""
    client, _db = env
    frames = _post_ask(client)
    assert frames[0][0] == FRAME_SESSION
    run_id = frames[0][1]["run_id"]
    assert run_id.startswith("run-")
    assert frames[0][1]["resume"] is False
    assert _step_kinds(frames) == [
        "understand", "plan", "tool", "observe", "verify", "answer",
    ]
    assert _names(frames)[-1] == FRAME_DONE  # 保留帧收场（V1 客户端干净收流判据）


# ---------- 验收② manifest_present_each_call：每模型调用落 Manifest ----------


def test_manifest_present_each_call(env: Any) -> None:
    """GET /api/v2/chat/runs/{run_id} → {status, steps, manifest_digest}；
    每个模型调用 step（understand/plan/verify）落七字段合同 Manifest
    （INV-5），终局 verdict 携 manifest_digest。"""
    client, _db = env
    frames = _post_ask(client)
    run_id = frames[0][1]["run_id"]
    verdicts = [data for name, data in frames if name == "verdict"]
    final = [v for v in verdicts if v.get("subtype") == "final"]
    assert final and final[-1]["manifest_digest"]

    resp = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"status", "steps", "manifest_digest"}  # 接口定义节合同形
    assert body["status"] == "completed"
    assert body["manifest_digest"] == final[-1]["manifest_digest"]
    manifest_by_step = {s["step"]: s["manifest"] for s in body["steps"]}
    for kind in ("understand", "plan", "verify"):
        manifest = manifest_by_step[kind]
        assert set(manifest) == {
            "source_type", "source_id", "version", "trust_level",
            "selected_reason", "token_count", "transform",
        }
        assert manifest["token_count"] > 0


# ---------- 验收③ ask_suspend_resume：工具 ask 挂起→GET waiting_ask→resume ----------


def test_ask_suspend_resume(env_clarify: Any) -> None:
    """工具返回 ask→run 挂起（ask 帧出流后 done 收束）→GET 状态 waiting_ask→
    resume 带选择续跑出答案（citation 在场）。"""
    client, _db = env_clarify
    frames = _post_ask(client, "最近的日产油量")
    run_id = frames[0][1]["run_id"]
    ask_frames = [data for name, data in frames if name == "ask"]
    assert ask_frames, "ASK 帧未出流"
    frame = ask_frames[0]["frame"]
    assert frame["kind"] == "clarify"
    assert frame["options"] == list(ASKBACK_TIME_CHOICES)
    assert _names(frames)[-1] == FRAME_DONE  # 挂起段正常收束（行为约定 4）

    status = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR)
    assert status.status_code == 200
    assert status.json()["status"] == "waiting_ask"

    resumed = client.post(
        f"/api/v2/chat/runs/{run_id}/resume",
        json={"kind": "clarify", "choice": "近 3 天"},
        headers=ACTOR,
    )
    assert resumed.status_code == 200
    second = _parse_frames(resumed.text)
    assert second[0][0] == FRAME_SESSION and second[0][1]["resume"] is True
    assert any(name == "citation" for name, _ in second)
    assert _names(second)[-1] == FRAME_DONE
    final = [data for name, data in second if name == "verdict" and data.get("subtype") == "final"]
    assert final and final[-1]["status"] == "completed"

    done = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR)
    assert done.json()["status"] == "completed"


# ---------- 验收④ sse_cursor_resume：断线游标重连不重复不遗漏 ----------


def test_sse_cursor_resume(env: Any) -> None:
    """断线重连形态（asks 携 resume_run_id＋Last-Event-ID——V1 帧形兼容）：
    重放流＝断点后事件序（不重复不遗漏）＋done 收场；重放流帧行首为
    session(resume)（V1 重放同形）。"""
    client, _db = env
    first = _post_ask(client)
    run_id = first[0][1]["run_id"]
    events = [f for f in first if f[0] not in (FRAME_SESSION, FRAME_DONE)]
    breakpoint = 2  # 断在帧 id 2（第三事件）——重放 seq>=2 尾部
    assert len(events) > breakpoint

    replay_resp = client.post(
        "/api/v2/chat/asks",
        json={"resume_run_id": run_id},
        headers={**ACTOR, "Last-Event-ID": str(breakpoint)},
    )
    assert replay_resp.status_code == 200
    replay = _parse_frames(replay_resp.text)
    assert replay[0][0] == FRAME_SESSION and replay[0][1]["resume"] is True
    assert replay[1:] == [*events[breakpoint:], first[-1]]  # 尾部事件＋done 同形同值


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


def test_resume_error_paths(env: Any) -> None:
    """resume 到不存在 run→404；非挂起态（completed）run→409（错误码行）。"""
    client, _db = env
    missing = client.post(
        "/api/v2/chat/runs/run-not-exist/resume",
        json={"kind": "clarify", "choice": "近 3 天"},
        headers=ACTOR,
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "chat_run_not_found"

    frames = _post_ask(client)  # 跑完一个 completed run
    run_id = frames[0][1]["run_id"]
    terminal = client.post(
        f"/api/v2/chat/runs/{run_id}/resume",
        json={"kind": "clarify", "choice": "近 3 天"},
        headers=ACTOR,
    )
    assert terminal.status_code == 409
    assert terminal.json()["code"] == "chat_run_state"


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


# ---------- 验收⑥ plan_repair_clarify_resume：校验失败→repair→ASK→resume ----------


def test_plan_repair_clarify_resume(env_repair: Any) -> None:
    """计划校验失败（缺 metric_slot）→repair 一次→clarify ASK 帧→resume 续跑
    出答案（repair 后 plan 步再现，恢复段出 citation）。"""
    client, _db = env_repair
    frames = _post_ask(client, "最近的日产油量")
    run_id = frames[0][1]["run_id"]
    plans = [data for name, data in frames if name == "step" and data["step"] == "plan"]
    assert len(plans) == 2  # 原计划＋repair 计划
    assert any(data["title"] == "计划缺 metric_slot" for name, data in frames if name == "step")
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
    subtype 判别（消费面不再靠键猜载荷形态）。"""
    client, _db = env
    frames = _post_ask(client)
    verdicts = [data for name, data in frames if name == "verdict"]
    assert len(verdicts) == 2
    verify, final = verdicts
    assert verify["subtype"] == "verify"
    assert set(verify) == {"subtype", "supported", "rewritten", "split", "cited"}
    assert verify["cited"] == [1] and verify["supported"] == 1 and verify["rewritten"] == 0
    assert final["subtype"] == "final"
    assert set(final) == {"subtype", "status", "run_id", "manifest_digest"}
    assert final["run_id"] == frames[0][1]["run_id"]
    # 流序：verify 判定先于 answer 步，终局判定收尾。
    order = [
        ("step", data["step"]) if name == "step" else ("verdict", data["subtype"])
        for name, data in frames
        if name in ("step", "verdict")
    ]
    assert order.index(("verdict", "verify")) < order.index(("step", "answer"))
    assert order[-1] == ("verdict", "final")


# ---------- P-006b 形态对齐：触界收敛 run 事件流＝answer 步＋text＋终局 verdict ----------


def test_budget_converged_stream_shape(env_budget: Any) -> None:
    """max_steps=3 触界收敛：收敛答案落 answer 步＋text 事件出流＋恰一机读
    notice（budget_converged）＋终局 verdict 收尾（P-006b·R1 修复后形态）。"""
    client, _db = env_budget
    frames = _post_ask(client)
    assert _step_kinds(frames) == ["understand", "plan", "tool", "answer"]
    texts = [data["content"] for name, data in frames if name == "text"]
    assert any("21.16" in t for t in texts)  # 已取得材料交付——不静默截断
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

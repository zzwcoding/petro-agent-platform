"""transport 块验收（RT-W2-02a：骨架／接口／闭世界与游标主干）。

票面对象＝`specs/transport.md`「验收测试」表第 1–10 行（逐字，测试标识同规格列；`#` 保留
规格表行序 1–10）。测试网钉＝pin-29（`::ask_frame_shape_and_done_after_ask`）／pin-09 与
pin-04（共载 `::notice_three_keys_closed_world`——两钉断言面在该测内均可指认）。

织网义务＝B5 golden 回放钉（`docs/runtime-refactor/eng/04-测试网设计.md` §三 B5 行）——
落本件末节 `::b5_golden_frame_replay_protocol_timeline`（钉源载体 `eval/results/frames/`）。

规格表第 11–18 行（收口／消费者／关闭语义／红线与元／边界·保留集）归
`RT-W2-02b-transport.md`；本件不重复实现 -b 的行。

**解析形（B5 钉的载体读法，本件定义）**：`eval/results/frames/*.json` 为单对象 JSON，
`frames` 数组＝帧序，元素 `{event: str, data: object, id?: int}`——`id`（在场时）＝跑批期
「响应内自增计数器」，本钉**不消费**（本块 `seq` 由总线一处重编）；旁挂键（`parsed`／
`question` 等）与不含 `frames` 数组的 JSON（跑批别的产物，如入库 task 记录）不在辖域。
"""

from __future__ import annotations

import collections
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from appv2.runtimev2.transport import (
    ASK_FRAME_KINDS,
    EVENT_KINDS,
    NOTICE_TYPES,
    VERDICT_SUBTYPES,
    WIRE_FRAMES,
    EventBus,
    SseEvent,
    envelope,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRAMES_DIR = _REPO_ROOT / "eval" / "results" / "frames"

# ── 规格逐字面（独立于实现常量书写——实现漂移即红；真源 specs/transport.md 接口定义节）──
_SPEC_EVENT_KINDS = {
    "step",
    "text",
    "tool",
    "observation",
    "ask",
    "verdict",
    "citation",
    "notice",
    "blackbox",
}
_SPEC_WIRE_FRAMES = {"session", "done", "error"}
_SPEC_NOTICE_TYPES = {
    "refused",
    "run_failed",
    "ban_exempt",
    "budget_converged",
    "clarify_capped",
    "emission_strip",
    "emission_quote_repair",
    "material_truncated",
    "unsupported_claim",
    "contradiction_split",
    "attribution_split",
    "decision_note",
    "decision_rejected",
    "chain_switch_reentry",
    "window_miss_reentry",
    "approval_gate_pending",
    "approval_recorded",
    "tool_unavailable",
    "subtask_failed",
    "subtask_refused",
    "audit_write_failed",
    "blackbox_write_failed",
}
_SPEC_VERDICT_SUBTYPES = {"verify", "final"}
_SPEC_ASK_FRAME_KINDS = {"clarify", "external_table_approval"}
# 五族常量族的导出面（卡面公开接口节；常量族之外还须有帧对象／总线／信封）
_FAMILY_EXPORTS = {
    "EVENT_KINDS",
    "WIRE_FRAMES",
    "NOTICE_TYPES",
    "VERDICT_SUBTYPES",
    "ASK_FRAME_KINDS",
}

# 跑批 UI 壳（V1 会话壳）自有帧名——不在本块十二值闭世界内；golden 载体的这半族不属本块消费面
_LEGACY_UI_EVENTS = frozenset(
    {
        "stage",
        "node",
        "node_line",
        "match",
        "assembly",
        "sec_check",
        "token",
        "tool_call",
        "lineage",
        "answer",
        "clarify",
    }
)

_RUN_ID = "run-8c1cce"


# ---------- 载荷与信封辅助 ----------


def _notice(
    notice_type: str = "run_failed", content: str = "引擎异常——本腿按失败披露"
) -> dict[str, Any]:
    return {"type": notice_type, "gates": [], "content": content}


def _ask_payload(kind: str = "clarify") -> dict[str, Any]:
    return {
        "frame": {
            "kind": kind,
            "prompt": "您想查询哪个范围的井去年配产量？",
            "options": ["全油田所有井的配产量", "指定某区块／作业区的井"],
            "detail": None,
        },
        "run_id": _RUN_ID,
    }


def _blackbox_pointer() -> dict[str, Any]:
    """收口帧瘦指针七键（形状真源 `synth/S6` §一；行为面归 `RT-W2-02b-transport.md`）。"""
    return {
        "run_id": _RUN_ID,
        "question": "渤海某井 2026 年日产油量？",
        "status": "completed",
        "error": None,
        "stored": True,
        "bytes": 2048,
        "counts": {
            "messages": 6,
            "dialogue": 2,
            "process_notes": 3,
            "observations": 4,
            "steps": 5,
        },
    }


def _payload_for(name: str) -> dict[str, Any]:
    """十二值各一的合法载荷（行为 6 键集归发射方；三类定形载荷按行为 7／8／9）。"""
    passthrough: dict[str, dict[str, Any]] = {
        "step": {"step": "decision", "seq": 1, "title": "决策"},
        "text": {"content": "某井日产油量 12.5 吨"},
        "tool": {"tool": "data_query", "status": "ok", "seq": 2, "message": "命中 3 行"},
        "observation": {
            "index": 1,
            "source": "报告",
            "content": "井身结构（实钻）",
            "trust": "high",
        },
        "citation": {"index": 1, "source": "报告", "source_id": "f4", "trust": "high"},
        "verdict": {"status": "completed", "run_id": _RUN_ID, "manifest_digest": "digest-1"},
        "notice": _notice(),
        "ask": _ask_payload(),
        "blackbox": _blackbox_pointer(),
        "session": {"run_id": _RUN_ID, "resume": False},
        "done": {"run_id": _RUN_ID},
        "error": {"code": "chat_stream_failed", "message": "流内异常——请重新提问"},
    }
    return {**passthrough[name]}


def _lines(frame: SseEvent) -> list[str]:
    return envelope(frame).split("\n")


def _envelope_id(frame: SseEvent) -> int:
    """信封 `id:` 行取值（行为 4）。"""
    head = _lines(frame)[0]
    assert head.startswith("id: ")
    return int(head[len("id: ") :])


def _triples(frames: list[SseEvent]) -> list[tuple[int, str, dict[str, Any]]]:
    return [(frame.seq, frame.event, frame.data) for frame in frames]


async def _collect(bus: EventBus, cursor: int = 0) -> list[SseEvent]:
    """读尽一条已收束总线的帧（未 `close` 会等待新帧——调用前须 `close`）。"""
    return [frame async for frame in bus.stream(cursor)]


# ---------- 1 事件名闭世界（行为 1） ----------


async def test_event_kinds_closed_world() -> None:
    """事件名闭世界（九 runtime ＋ 三 wire ＝十二值）；越界构造抛错。"""
    assert EVENT_KINDS == _SPEC_EVENT_KINDS  # 闭世界不经裁决不许长胖（九类口径＝S3 C-05）
    assert WIRE_FRAMES == _SPEC_WIRE_FRAMES
    assert len(EVENT_KINDS | WIRE_FRAMES) == 12

    bus = EventBus()
    for name in sorted(_SPEC_EVENT_KINDS | _SPEC_WIRE_FRAMES):
        frame = bus.emit(name, _payload_for(name))  # 十二个合法值各构造成功
        assert frame.event == name

    # 越界名构造期即抛错（fail-closed，不静默丢弃、不降级为默认类）：构造面与发射面同判
    for bad in ("stage", "token", "node", "SESSION", "step ", "", "notice.alert", "donex"):
        with pytest.raises(ValueError):
            SseEvent(seq=0, event=bad, data={})
        with pytest.raises(ValueError):
            EventBus().emit(bad, {})

    # 越界不留半帧（发射失败不污染历史）
    bus2 = EventBus()
    with pytest.raises(ValueError):
        bus2.emit("stage", {"state": "process"})
    bus2.close()
    assert await _collect(bus2, 0) == []


# ---------- 2 blackbox 同列导出面（行为 1；S3 C-10 收正） ----------


def test_blackbox_kind_exported() -> None:
    """`EVENT_KINDS` 九类全列导出面（含 `blackbox`）。"""
    import appv2.runtimev2.transport as transport

    # 骨架与公开面齐备（卡面签名：帧对象／总线／信封＋五族常量）
    assert {"SseEvent", "EventBus", "envelope"} <= set(transport.__all__)
    assert _FAMILY_EXPORTS <= set(transport.__all__)
    assert transport.EVENT_KINDS is EVENT_KINDS  # 导出面＝同一族（不另立第二套集合）

    assert EVENT_KINDS == _SPEC_EVENT_KINDS
    assert len(EVENT_KINDS) == 9  # 「八类」为陈旧注记（S3 C-05）
    assert "blackbox" in EVENT_KINDS  # 现状缺漏＝S3 C-10／D-P9a1-09；本块收正
    assert sorted(_SPEC_EVENT_KINDS - EVENT_KINDS) == []

    frame = EventBus().emit("blackbox", _blackbox_pointer())
    assert frame.event == "blackbox"
    assert NOTICE_TYPES == _SPEC_NOTICE_TYPES
    assert VERDICT_SUBTYPES == _SPEC_VERDICT_SUBTYPES
    assert ASK_FRAME_KINDS == _SPEC_ASK_FRAME_KINDS


# ---------- 3 帧信封字节形（行为 2） ----------


def test_envelope_bytes_stable() -> None:
    """帧信封恒三行＋空行；中文不转义；非原语不炸流。"""
    bus = EventBus()
    frames = [bus.emit(name, _payload_for(name)) for name in sorted(_SPEC_EVENT_KINDS)]
    frames += [bus.emit(name, _payload_for(name)) for name in sorted(_SPEC_WIRE_FRAMES)]

    for frame in frames:
        text = envelope(frame)
        lines = _lines(frame)
        assert len(lines) == 5, f"信封不为三行＋空行：{text!r}"
        assert lines[3] == "" and lines[4] == ""
        assert lines[0] == f"id: {frame.seq}"
        assert lines[1] == f"event: {frame.event}"
        assert lines[2].startswith("data: ")
        assert json.loads(lines[2][len("data: ") :]) == frame.data
        assert text.endswith("\n\n")

    # 中文逐字不被转义（ensure_ascii=False）
    chinese = "渤海某井 9-5/8″ 生产套管下深 2462.0 米——水泥返高至地面"
    text = envelope(bus.emit("text", {"content": chinese}))
    assert chinese in text
    assert "\\u" not in text

    # 非 JSON 原语（Decimal／date）兜底为字符串而不炸流
    exotic = envelope(bus.emit("step", {"payload": Decimal("1.5"), "when": date(2026, 8, 31)}))
    assert '"1.5"' in exotic and '"2026-08-31"' in exotic
    assert len(exotic.split("\n")) == 5


# ---------- 4 游标全流单调（行为 3） ----------


async def test_cursor_monotonic_global() -> None:
    """游标全流单调：跨段不重启、重放不位移。"""
    bus = EventBus()
    # 提问段（session → 三事件 → done）
    bus.emit("session", {"run_id": _RUN_ID, "resume": False})
    for name in ("step", "text", "ask"):
        bus.emit(name, _payload_for(name))
    bus.emit("done", {"run_id": _RUN_ID})
    seg1_events = 3

    # resume 段（同一 run、同一条总线续编——不重启、不另起计数器）
    bus.emit("session", {"run_id": _RUN_ID, "resume": True})
    for name in ("step", "verdict", "blackbox"):
        bus.emit(name, _payload_for(name))
    bus.emit("done", {"run_id": _RUN_ID})
    bus.close()

    frames = await _collect(bus, 0)
    event_seqs = [frame.seq for frame in frames if frame.event in EVENT_KINDS]
    assert event_seqs == list(range(len(event_seqs)))  # 0 起、严格递增、无跳号、无重复
    assert event_seqs[seg1_events] == seg1_events  # 第二段首个事件帧＝上一段之后（跨段不重启）

    # 重放不位移：同一游标重读两次，逐帧同 seq／同 event／同 data
    replay = await _collect(bus, 0)
    assert _triples(replay) == _triples(frames)


# ---------- 5 信封 id＝最后已消费事件 seq（行为 4） ----------


async def test_frame_id_equals_cursor() -> None:
    """信封 `id`：事件帧＝自身 `seq`、wire 帧＝最后已消费事件 `seq`。

    尚未消费任何事件时＝-1；wire 帧不推进游标（验收表行 5）。
    """
    bus = EventBus()
    session = bus.emit("session", {"run_id": _RUN_ID, "resume": False})
    assert session.seq == -1  # 尚未消费任何事件
    assert _envelope_id(session) == -1

    step = bus.emit("step", _payload_for("step"))
    text = bus.emit("text", _payload_for("text"))
    assert step.seq == 0 and _envelope_id(step) == 0  # 事件帧 id＝自身 seq
    assert text.seq == 1 and _envelope_id(text) == 1
    assert _envelope_id(step) < _envelope_id(text)  # 连续事件帧 id 严格递增

    done = bus.emit("done", {"run_id": _RUN_ID})
    assert done.seq == text.seq  # wire 帧不占 seq 号位、不推进事件游标
    assert _envelope_id(done) == _envelope_id(text)  # id＝最后已消费事件 seq（可与前帧相同）

    resume_session = bus.emit("session", {"run_id": _RUN_ID, "resume": True})
    assert _envelope_id(resume_session) == text.seq  # 段中 wire 帧仍写最后已消费事件 seq
    blackbox = bus.emit("blackbox", _blackbox_pointer())
    assert blackbox.seq == text.seq + 1  # wire 帧未推进游标：下一个事件帧接续编号

    # 客户端以任一帧 id 回送（cursor = id + 1）→ 无位移续传
    bus.close()
    resumed = await _collect(bus, _envelope_id(done) + 1)
    assert [frame.seq for frame in resumed] == [blackbox.seq]


# ---------- 6 断线续推不重不漏（行为 5） ----------


async def test_resume_no_dup_no_gap() -> None:
    """断线续推不重不漏（后缀逐帧相等）。"""
    bus = EventBus()
    bus.emit("session", {"run_id": _RUN_ID, "resume": False})
    for name in ("step", "text", "tool", "observation", "notice", "citation", "verdict"):
        bus.emit(name, _payload_for(name))
    bus.emit("blackbox", _blackbox_pointer())
    bus.emit("done", {"run_id": _RUN_ID})
    bus.close()

    full = await _collect(bus, 0)
    assert _triples(await _collect(bus, 0)) == _triples(full)
    max_seq = max(frame.seq for frame in full)
    for cursor in range(0, max_seq + 2):
        resumed = await _collect(bus, cursor)
        suffix = [frame for frame in full if frame.seq >= cursor]
        assert _triples(resumed) == _triples(suffix)  # 逐帧同 seq／同 event／同 data

    # 断点无论落在事件帧还是 wire 帧，换算同式 cursor = id + 1 → 分区不重不漏
    done = next(frame for frame in full if frame.event == "done")
    for boundary in (full[3], done):
        cursor = _envelope_id(boundary) + 1
        consumed = [frame for frame in full if frame.seq < cursor]
        resumed = await _collect(bus, cursor)
        assert [id(frame) for frame in [*consumed, *resumed]] == [id(frame) for frame in full]
        assert all(frame.seq >= cursor for frame in resumed)

    # 非法 cursor（负数）→ 抛错（错误契约）
    with pytest.raises(ValueError):
        bus.stream(-1)


# ---------- 7 载荷透传零裁剪（行为 6） ----------


def test_payload_passthrough_no_rewrite() -> None:
    """载荷透传零裁剪；verdict 唯一改造＋两形闭世界。"""
    bus = EventBus()
    payloads = {
        # 键集归发射方：越出契约的键也如实透传（本块不校键、不补键、不删键）
        "step": {"step": "decision", "seq": 3, "title": "决策", "extra": {"深": [1, None]}},
        "text": {"content": "长文本" * 500},
        "tool": {"tool": "data_query", "status": "ok", "seq": 4, "message": "命中 3 行"},
        "observation": {
            "index": 1,
            "source": "报告",
            "content": "井身结构",
            "trust": "high",
        },
        "citation": {"index": 1, "source": "报告", "source_id": "f4", "trust": "high"},
        "blackbox": _blackbox_pointer(),
        "session": {"run_id": _RUN_ID, "resume": False},
        "done": {"run_id": _RUN_ID},
    }
    for name, payload in payloads.items():
        frame = bus.emit(name, payload)
        assert frame.data == payload  # 深比较相等（零裁剪零改名零白名单）
        assert set(frame.data) == set(payload)

    # 载荷为快照：发射方事后改写不入帧（重放不位移的前提）
    mutable = {"content": "原文"}
    snapshot = bus.emit("text", mutable)
    mutable["content"] = "事后改写"
    assert snapshot.data == {"content": "原文"}

    # verdict 唯一改造：判据单点（含 `status` 键 → final，否则 → verify），原键如实透传
    verify_payload = {
        "cited": True,
        "rewritten": False,
        "split": [],
        "supported": True,
        "attribution": {"anchors": [], "cross": []},
    }
    odd_payload = {  # 键集越出契约（clarify 形裁决载荷）→ verify，原键照旧
        "chain": "检索问答链",
        "confidence": 0.8,
        "need_clarify": False,
        "slots": {},
        "source": "clean",
    }
    final_payload = {"status": "completed", "run_id": _RUN_ID, "manifest_digest": "digest-1"}
    for payload, expected in (
        (verify_payload, "verify"),
        (odd_payload, "verify"),
        (final_payload, "final"),
    ):
        frame = bus.emit("verdict", payload)
        assert frame.data == {**payload, "subtype": expected}
        assert set(frame.data) == set(payload) | {"subtype"}  # 只加不删不改名

    # 非 verdict 帧不注入 subtype（零改写面）
    assert "subtype" not in bus.emit("step", {"seq": 9, "step": "answer", "title": "作答"}).data
    assert VERDICT_SUBTYPES == _SPEC_VERDICT_SUBTYPES


# ---------- 8 通知恰三键＋分型闭世界（行为 7；pin-09／pin-04 共载） ----------


async def test_notice_three_keys_closed_world() -> None:
    """通知恰三键＋`NOTICE_TYPES` 二十二值闭世界（越界／缺键／多键／缺 `type` 判失败）。

    pin-09（P1）｜材料截断披露的**帧面**：`material_truncated` 帧必发且其 `type` 在闭世界内
    （披露行为面挂 `specs/answering.md`、字段面挂 `specs/state.md`）——断言见「pin-09」段。
    pin-04（P0）｜发射 JSON 不进答案面的**帧形面**：`emission_strip` 通知的帧形（`type` ∈
    `NOTICE_TYPES` 闭世界、载荷恰三键 `{type, gates, content}`）——断言见「pin-04」段。
    """
    assert NOTICE_TYPES == _SPEC_NOTICE_TYPES  # 取值闭世界逐字（本规格自立·码面实测）
    assert len(NOTICE_TYPES) == 22

    bus = EventBus()
    for notice_type in sorted(_SPEC_NOTICE_TYPES):
        frame = bus.emit("notice", _notice(notice_type))
        assert set(frame.data) == {"type", "gates", "content"}  # 恰三键
        assert frame.data["type"] in NOTICE_TYPES

    # pin-09：材料截断披露的帧面——发射方照发即得合法帧，type 落在闭世界内
    truncation = bus.emit(
        "notice",
        _notice("material_truncated", content="候选 20 支，仅送前 4 支进生成——另有 16 支未列出。"),
    )
    assert truncation.event == "notice"
    assert truncation.data["type"] == "material_truncated"
    assert truncation.data["type"] in NOTICE_TYPES
    assert set(truncation.data) == {"type", "gates", "content"}

    # pin-04：发射 JSON 剥离通知的帧形面——恰三键、type 在闭世界内（剥离行为面归 answering 行为 11）
    strip = bus.emit(
        "notice", _notice("emission_strip", content="发射 JSON 已从答案面剥离——泄漏=0")
    )
    assert strip.event == "notice"
    assert set(strip.data) == {"type", "gates", "content"}
    assert strip.data["type"] == "emission_strip"
    assert strip.data["type"] in NOTICE_TYPES

    # 失败面：缺键／多键／缺 type（取消隐式兜底）／越界 type 各判失败
    rejected = [
        {"type": "run_failed", "content": "缺 gates"},
        {"gates": [], "content": "缺 type"},
        {"type": "run_failed", "gates": [], "content": "多键", "detail": "x"},
        {"type": "notice", "gates": [], "content": "旧码隐式兜底值不在闭世界"},
        {"type": "unknown_alert", "gates": [], "content": "越界"},
        {},
    ]
    for payload in rejected:
        with pytest.raises(ValueError):
            bus.emit("notice", dict(payload))
    with pytest.raises(ValueError):
        SseEvent(seq=0, event="notice", data={"type": "run_failed", "gates": []})

    # 越界不留半帧
    bus2 = EventBus()
    with pytest.raises(ValueError):
        bus2.emit("notice", {"gates": [], "content": "缺 type"})
    bus2.close()
    assert await _collect(bus2, 0) == []


# ---------- 9 ask 帧形状与挂起铁律（行为 8；pin-29） ----------


async def test_ask_frame_shape_and_done_after_ask() -> None:
    """`ask` 帧形状齐备＋`kind` 闭世界；挂起后照发 `done`。

    pin-29（P0）｜挂起→resume 的**帧面**（`ask` 帧 kind 闭世界＋挂起后照发 `done`）
    ——闭环面挂 `specs/agent-loop.md`，帧面断言见「pin-29」段。
    """
    assert ASK_FRAME_KINDS == _SPEC_ASK_FRAME_KINDS
    assert len(ASK_FRAME_KINDS) == 2

    bus = EventBus()
    for kind in sorted(_SPEC_ASK_FRAME_KINDS):
        payload = _ask_payload(kind)
        frame = bus.emit("ask", payload)
        assert frame.data == payload
        assert set(frame.data) == {"frame", "run_id"}
        assert set(frame.data["frame"]) == {"kind", "prompt", "options", "detail"}
        assert frame.data["frame"]["kind"] in ASK_FRAME_KINDS

    # pin-29：挂起腿的帧序列末尾仍见 done（挂起看 ask 帧、不看 done——done 只代表本腿流结束）
    hanging = EventBus()
    produced = [
        hanging.emit("session", {"run_id": _RUN_ID, "resume": False}),
        hanging.emit("ask", _ask_payload()),
        hanging.emit("done", {"run_id": _RUN_ID}),
    ]
    hanging.close()
    assert [frame.event for frame in produced] == ["session", "ask", "done"]
    assert produced[1].data["frame"]["kind"] in ASK_FRAME_KINDS
    assert produced[-1].event == "done"
    assert produced[-1].data == {"run_id": _RUN_ID}
    # 重放面：wire 帧不占 seq（段首 session 的 seq＝-1 落在 cursor 起点 0 之前，不入重放）
    # ——wire 帧重放语义归 `api` 开流段（`transport-回工补写.md` §遗留 2）；挂起腿末尾仍见 done
    replayed = await _collect(hanging, 0)
    assert [frame.event for frame in replayed] == ["ask", "done"]
    assert replayed[-1].event == "done"

    # 失败面：kind 越界／形状不齐（缺 frame／缺 run_id／frame 缺键／多键）
    bad_payloads = [
        {**_ask_payload(), "frame": {**_ask_payload()["frame"], "kind": "escalate"}},
        {**_ask_payload(), "frame": {**_ask_payload()["frame"], "kind": None}},
        {"frame": _ask_payload()["frame"]},
        {"run_id": _RUN_ID},
        {**_ask_payload(), "extra": 1},
        {**_ask_payload(), "frame": {"kind": "clarify", "prompt": "缺 options／detail"}},
    ]
    for payload in bad_payloads:
        with pytest.raises(ValueError):
            bus.emit("ask", dict(payload))


# ---------- 10 done／error 分流与脱敏形（行为 9） ----------


async def test_done_error_split_no_raw_exception() -> None:
    """正常 `done`／异常 `error`；`error` 不含原始异常文本。"""
    bus = EventBus()
    bus.emit("session", {"run_id": _RUN_ID, "resume": False})
    bus.emit("step", _payload_for("step"))
    bus.emit("blackbox", _blackbox_pointer())
    bus.emit("done", {"run_id": _RUN_ID})
    bus.close()
    frames = await _collect(bus, 0)
    assert frames[-1].event == "done"  # 正常收束＝done
    assert frames[-1].data == {"run_id": _RUN_ID}
    assert "error" not in {frame.event for frame in frames}

    # 引擎／网关异常不走 error 帧：走 notice{type:"run_failed"} ＋ 正常 done（不降级与静默禁令）
    failed = EventBus()
    failed.emit("notice", _notice("run_failed", content="工具链异常——本腿按失败披露"))
    failed.emit("done", {"run_id": _RUN_ID})
    failed.close()
    assert [frame.event for frame in await _collect(failed, 0)] == ["notice", "done"]

    # 异常腿：error 载荷定形恰二键（稳定话术）——原始异常文本没有可安放的键位
    error_bus = EventBus()
    try:
        raise RuntimeError(
            "Traceback (most recent call last): /appv2/runtime/graph.py:1 SELECT * FROM t"
        )
    except RuntimeError as exc:
        with pytest.raises(ValueError):
            error_bus.emit(
                "error",
                {"code": "chat_stream_failed", "message": "流内异常", "detail": str(exc)},
            )
    frame = error_bus.emit(
        "error", {"code": "chat_stream_failed", "message": "流内异常——请重新提问"}
    )
    text = envelope(frame)
    assert frame.event == "error" and frame.event != "done"
    assert set(frame.data) == {"code", "message"}
    assert "Traceback" not in text and ".py" not in text and "SELECT" not in text
    with pytest.raises(ValueError):
        error_bus.emit("error", {"code": "chat_stream_failed"})


# ---------- 织网义务 B5：golden 帧流回放钉 ----------


def _golden_frame_files() -> list[Path]:
    if not _FRAMES_DIR.is_dir():
        pytest.skip(f"B5 钉源载体不在场：{_FRAMES_DIR}")
    return sorted(_FRAMES_DIR.glob("*.json"))


def _parse_golden(path: Path) -> list[dict[str, Any]] | None:
    """解析形（见模块 docstring）：返回 `frames` 数组；非本形（无 frames 数组）→ None。"""
    try:
        document: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict):
        return None
    frames = document.get("frames")
    if not isinstance(frames, list):
        return None
    parsed: list[dict[str, Any]] = []
    for item in frames:
        assert isinstance(item, dict), f"golden 载体违约（帧元素非对象）：{path.name}"
        assert isinstance(item.get("event"), str), f"golden 载体违约（帧缺 event）：{path.name}"
        assert isinstance(item.get("data"), dict), f"golden 载体违约（帧 data 非映射）：{path.name}"
        parsed.append(item)
    return parsed


async def test_b5_golden_frame_replay_protocol_timeline() -> None:
    """B5（织网义务）｜帧协议级时序与 data 形的离线 golden 回放钉。

    钉法（`docs/runtime-refactor/eng/04-测试网设计.md` §三 B5 行）：「从
    `eval/results/frames/` 真帧流转离线 golden 回放钉」。载体＝跑批真帧流（`frames` 数组，
    解析形见模块 docstring）；消费面＝帧名落本块十二值闭世界的那半族（跑批 UI 壳自有帧名
    `_LEGACY_UI_EVENTS` 不属本块）。

    断言面＝帧序保真＋载荷零改写＋一处编号（事件帧 0 起严格递增、wire 帧不占号位）＋信封
    字节形＋断线续推后缀相等。**闭世界边界**：真帧流里凡越出 `NOTICE_TYPES` 的通知帧一律被
    拒（fail-closed，无隐式兜底——行为 7 的实测面）；非 notice 帧被拒即判失败。
    """
    carriers: list[tuple[Path, list[dict[str, Any]]]] = []
    ui_carriers = 0
    for path in _golden_frame_files():
        frames = _parse_golden(path)
        if not frames:
            continue
        names = {frame["event"] for frame in frames}
        if names <= (EVENT_KINDS | WIRE_FRAMES):  # 只取 runtime 载体半族
            carriers.append((path, frames))
        elif names & _LEGACY_UI_EVENTS:  # 跑批 UI 壳半族：帧名不在本块闭世界内
            ui_carriers += 1
    assert len(carriers) >= 100, f"runtime 载体半族缺失（实得 {len(carriers)} 件）"
    assert ui_carriers >= 10, f"另半族不在场＝载体口径已变（实得 {ui_carriers} 件）"

    accepted_total = 0
    rejected_notice_types: collections.Counter[str] = collections.Counter()
    accepted_notice_types: set[str] = set()
    for index, (path, frames) in enumerate(carriers):
        bus = EventBus()
        accepted: list[SseEvent] = []
        kept: list[dict[str, Any]] = []
        for golden in frames:
            name, data = golden["event"], golden["data"]
            try:
                accepted.append(bus.emit(name, data))
            except ValueError:
                # 只许拒「notice 的 type 缺省或越界」（行为 7 fail-closed）；其余帧被拒＝闭世界漂移
                assert name == "notice", f"非 notice 帧被拒：{name!r}（载体 {path.name}）"
                assert "type" not in data or data["type"] not in NOTICE_TYPES
                rejected_notice_types[repr(data.get("type"))] += 1
                continue
            frame = accepted[-1]
            kept.append(golden)
            assert frame.event == name
            if name == "verdict":
                expected = {**data, "subtype": "final" if "status" in data else "verify"}
                assert frame.data == expected  # 唯一改造
                assert frame.data["subtype"] in VERDICT_SUBTYPES
            elif name == "notice":
                assert set(frame.data) == {"type", "gates", "content"}
                accepted_notice_types.add(str(frame.data["type"]))
            else:
                assert frame.data == data  # 载荷零裁剪零改名（真载荷深比较）
        if not accepted:
            continue
        accepted_total += len(accepted)
        assert [frame.event for frame in accepted] == [g["event"] for g in kept]  # 帧序保真

        last_event_seq = -1
        for frame in accepted:
            if frame.event in EVENT_KINDS:
                assert frame.seq == last_event_seq + 1  # 一处编号：0 起、严格递增、无跳号
                last_event_seq = frame.seq
            else:
                assert frame.seq == last_event_seq  # wire 帧不占号位、不推进游标
        for position, frame in enumerate(accepted):
            if position % 13:
                continue
            text = envelope(frame)
            assert text.endswith("\n\n") and len(text.split("\n")) == 5
            assert text.startswith(f"id: {frame.seq}\nevent: {frame.event}\ndata: ")

        if index < 3:  # 断线续推：以断点游标续推＝原流后缀（逐帧相等）
            bus.close()
            full = await _collect(bus, 0)
            # stream(0) 的起点＝seq 0：事件帧之前的 wire 帧（seq＝-1）落在起点之前（行为 4／5）
            assert _triples(full) == _triples([frame for frame in accepted if frame.seq >= 0])
            cursor = max((frame.seq for frame in full), default=0) // 2
            assert _triples(await _collect(bus, cursor)) == _triples(
                [frame for frame in full if frame.seq >= cursor]
            )

    assert accepted_total >= 10000, f"回放消费量不足（实得 {accepted_total} 帧）"
    # pin-09／pin-04 的真帧在场证据：截断披露帧与发射剥离帧在真帧流里实发且过闸
    assert {"material_truncated", "emission_strip"} <= accepted_notice_types
    assert rejected_notice_types  # 越界 type 的真实样本在场（被 fail-closed 拒——见下注）
    # 注（实测 2026-10-16）：被拒的真实 notice.type ＝ window_note／no_hit／unbound_degrade／
    # freshness_block／same_param_replay／rebind／schema_not_allowed（另有旧码 `{level,text}` 形
    # 缺 `type`）——即真码面的 notice 取值面**大于**本规格 NOTICE_TYPES 二十二值；落行为 7
    # 「新增类型必须同批入列」（规格变更回设计仓裁定，本块不私加取值）。

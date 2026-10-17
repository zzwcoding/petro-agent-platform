"""transport 块验收（RT-W2-02a：骨架／接口／闭世界与游标主干；
RT-W2-02b：收口／消费者／元／边界·保留集）。

票面对象＝`specs/transport.md`「验收测试」表：-a 收第 1–10 行；**-b** 收第 11–18 行（逐字，
测试标识同规格列；`#` 保留规格表行序、不重编）。测试网钉＝pin-29
（`::ask_frame_shape_and_done_after_ask`）／pin-09 与 pin-04（共载
`::notice_three_keys_closed_world`——两钉断言面在该测内均可指认）——三钉全在 -a，-b 零 pin 行。

织网义务＝B5 golden 回放钉（`docs/runtime-refactor/eng/04-测试网设计.md` §三 B5 行）——
落 `::b5_golden_frame_replay_protocol_timeline`（钉源载体 `eval/results/frames/`）；-b 的行 11／
行 14 同用该载体读数（复用 `_parse_golden` 解析形，不另立第二套解析）。

**解析形（B5 钉的载体读法，本件定义）**：`eval/results/frames/*.json` 为单对象 JSON，
`frames` 数组＝帧序，元素 `{event: str, data: object, id?: int}`——`id`（在场时）＝跑批期
「响应内自增计数器」，本钉**不消费**（本块 `seq` 由总线一处重编）；旁挂键（`parsed`／
`question` 等）与不含 `frames` 数组的 JSON（跑批别的产物，如入库 task 记录）不在辖域。
"""

from __future__ import annotations

import ast
import asyncio
import collections
import json
import re
from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal
from functools import lru_cache
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
    # 2026-10-17 EB3 D1（交付面分层）：第十类——程序追加内容的增补面帧
    "supplement",
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
    # 2026-10-16 补全（流水 53-C）：B5 golden 回放实测越界 7 值（规格表同批增列）
    "window_note",
    "no_hit",
    "unbound_degrade",
    "freshness_block",
    "same_param_replay",
    "rebind",
    "schema_not_allowed",
}
_SPEC_VERDICT_SUBTYPES = {"verify", "final"}
_SPEC_ASK_FRAME_KINDS = {"clarify", "external_table_approval"}
# supplement 帧块型闭世界四值（2026-10-17 EB3 D1；真源同 specs/transport.md 接口定义节）
_SPEC_SUPPLEMENT_BLOCKS = {"split", "attribution", "citations", "lineage"}
# 六族常量族的导出面（卡面公开接口节；常量族之外还须有帧对象／总线／信封）
_FAMILY_EXPORTS = {
    "EVENT_KINDS",
    "WIRE_FRAMES",
    "NOTICE_TYPES",
    "VERDICT_SUBTYPES",
    "ASK_FRAME_KINDS",
    "SUPPLEMENT_BLOCKS",
}

# 跑批 UI 壳（V1 会话壳）自有帧名——不在本块十三值闭世界内；golden 载体的这半族不属本块消费面
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
    """十三值各一的合法载荷（行为 6 键集归发射方；四类定形载荷按行为 7／8／9／16）。"""
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
        "supplement": {"block": "citations", "text": "引用：\n[1] 报告 · f4（high）"},
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
    """事件名闭世界（十 runtime ＋ 三 wire ＝十三值）；越界构造抛错。"""
    assert EVENT_KINDS == _SPEC_EVENT_KINDS  # 闭世界不经裁决不许长胖（九类口径＝S3 C-05；EB3 D1）
    assert WIRE_FRAMES == _SPEC_WIRE_FRAMES
    assert len(EVENT_KINDS | WIRE_FRAMES) == 13

    bus = EventBus()
    for name in sorted(_SPEC_EVENT_KINDS | _SPEC_WIRE_FRAMES):
        frame = bus.emit(name, _payload_for(name))  # 十三个合法值各构造成功
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
    """`EVENT_KINDS` 十类全列导出面（含 `blackbox`／`supplement`）。"""
    import appv2.runtimev2.transport as transport

    # 骨架与公开面齐备（卡面签名：帧对象／总线／信封＋六族常量）
    assert {"SseEvent", "EventBus", "envelope"} <= set(transport.__all__)
    assert _FAMILY_EXPORTS <= set(transport.__all__)
    assert transport.EVENT_KINDS is EVENT_KINDS  # 导出面＝同一族（不另立第二套集合）

    assert EVENT_KINDS == _SPEC_EVENT_KINDS
    assert len(EVENT_KINDS) == 10  # 「八类」为陈旧注记（S3 C-05）；EB3 D1 起十类
    assert "blackbox" in EVENT_KINDS  # 现状缺漏＝S3 C-10／D-P9a1-09；本块收正
    assert "supplement" in EVENT_KINDS  # 2026-10-17 EB3 D1 增第十类
    assert sorted(_SPEC_EVENT_KINDS - EVENT_KINDS) == []

    frame = EventBus().emit("blackbox", _blackbox_pointer())
    assert frame.event == "blackbox"
    assert NOTICE_TYPES == _SPEC_NOTICE_TYPES
    assert VERDICT_SUBTYPES == _SPEC_VERDICT_SUBTYPES
    assert ASK_FRAME_KINDS == _SPEC_ASK_FRAME_KINDS
    assert transport.SUPPLEMENT_BLOCKS == _SPEC_SUPPLEMENT_BLOCKS


# ---------- 2b supplement 帧定形载荷（行为 16；2026-10-17 EB3 D1） ----------


def test_supplement_frame_closed_world() -> None:
    """`supplement` 帧定形恰二键 `{block, text}`＋块型闭世界四值（EB3 D1）。

    增补面＝程序追加内容（分源块／归属块／引用清单／血缘五要素）的唯一结构化出口：
    块型越界／缺键／多键一律构造期抛错（fail-closed，不静默丢弃、不降级为默认块型）。
    """
    bus = EventBus()
    for block in sorted(_SPEC_SUPPLEMENT_BLOCKS):
        frame = bus.emit("supplement", {"block": block, "text": f"{block} 全文"})
        assert frame.event == "supplement"
        assert set(frame.data) == {"block", "text"}  # 恰二键（行为 16）
        assert frame.data["block"] == block

    for bad in (
        {"block": "summary", "text": "越界块型"},  # 四值之外（不经裁决不许长胖）
        {"block": "split"},  # 缺 text
        {"text": "缺 block"},  # 缺 block
        {"block": "split", "text": "多键", "extra": 1},  # 多键
    ):
        with pytest.raises(ValueError):
            SseEvent(seq=0, event="supplement", data=bad)
        with pytest.raises(ValueError):
            EventBus().emit("supplement", dict(bad))


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
    """通知恰三键＋`NOTICE_TYPES` 二十九值闭世界（越界／缺键／多键／缺 `type` 判失败）。

    pin-09（P1）｜材料截断披露的**帧面**：`material_truncated` 帧必发且其 `type` 在闭世界内
    （披露行为面挂 `specs/answering.md`、字段面挂 `specs/state.md`）——断言见「pin-09」段。
    pin-04（P0）｜发射 JSON 不进答案面的**帧形面**：`emission_strip` 通知的帧形（`type` ∈
    `NOTICE_TYPES` 闭世界、载荷恰三键 `{type, gates, content}`）——断言见「pin-04」段。
    """
    assert NOTICE_TYPES == _SPEC_NOTICE_TYPES  # 取值闭世界逐字（本规格自立·实测全集）
    assert len(NOTICE_TYPES) == 29

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
    解析形见模块 docstring）；消费面＝帧名落本块十三值闭世界的那半族（跑批 UI 壳自有帧名
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
    # 2026-10-16 补全（流水 53-C）的 7 值：真帧流实发且过闸——补全前它们是被 fail-closed 拒的
    # 越界样本（实测 1028 帧：window_note 828／no_hit 93／unbound_degrade 63／freshness_block 29／
    # same_param_replay 8／rebind 6／schema_not_allowed 1），补全后真帧流与本规格闭世界对齐；
    # 本回放零越界残留（越界 fail-closed 面由 `::notice_three_keys_closed_world` 的伪造样本覆盖）。
    assert {
        "window_note",
        "no_hit",
        "unbound_degrade",
        "freshness_block",
        "same_param_replay",
        "rebind",
        "schema_not_allowed",
    } <= accepted_notice_types
    assert not rejected_notice_types, f"闭世界已补全仍拒真帧：{rejected_notice_types}"


# ══════ RT-W2-02b：收口／消费者／元／边界·保留集（票面对象＝规格表第 11–18 行）══════

_TRANSPORT_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "transport"

_HANG_TIMEOUT = 5.0  # 消费者收束的挂死探测（不靠一次性哨兵——挂住即超时红）；非 wall-clock 判据
_HUGE_CHARS = 200_000  # 行 17 超长载荷面
_SETTLE_SPINS = 2000  # 消费者推进的自旋上限（`sleep(0)` 确定性推进）

# 瘦指针七键（形状真源 `synth/S6` §一；行为 10「全文入库不入帧」的键集面）
_BLACKBOX_POINTER_KEYS = frozenset(
    {"run_id", "question", "status", "error", "stored", "bytes", "counts"}
)

# 截断类**帧名**标记（行 14：wire 面无 `replay_truncated` 这类帧——截断披露走 `notice.type` 面）
_TRUNCATION_FRAME_MARK = re.compile(r"truncat|截断|replay|cut_off|partial", re.IGNORECASE)

# 行 15 的内部痕迹类（堆栈／模块路径／SQL 片段）逐类正则——机检面；内容级判定不在本块（零判断铁律）
_LEAK_MARKS: tuple[tuple[str, str], ...] = (
    ("堆栈", r"Traceback"),
    ("文件行", r'File "[^"]+"|line \d+, in |\.py\b'),
    ("内部路径", r"/appv2/|appv2\.runtimev2|site-packages|/\.venv/"),
    ("SQL", r"\b(?:SELECT|INSERT INTO|UPDATE|DELETE FROM|DROP TABLE|ALTER TABLE)\b"),
    ("驱动面", r"psycopg|asyncpg|sqlalchemy|SQLAlchemy"),
)

# 行 16 AST 判据面：禁引模块（正则／判断族＋模型出口族＋框架族＋落盘族）／禁止调用名／词表名面
_FORBIDDEN_IMPORT_MODULES = (
    "re",
    "regex",
    "litellm",
    "openai",
    "anthropic",
    "langgraph",
    "langchain",
    "langchain_core",
    "langchain_community",
    "appv2.infra.llm_client",
    "os",
    "io",
    "pathlib",
    "shutil",
    "tempfile",
    "sqlite3",
    "psycopg",
    "sqlalchemy",
)
_REGEX_CALL_NAMES = (
    "match",
    "fullmatch",
    "search",
    "findall",
    "finditer",
    "compile",
    "sub",
    "split",
)
_MODEL_CALL_NAMES = (
    "complete",
    "acomplete",
    "chat",
    "responses",
    "embed",
    "embedding",
    "embeddings",
)
_WRITE_CALL_NAMES = (
    "open",
    "write_text",
    "write_bytes",
    "unlink",
    "rmdir",
    "mkdir",
    "makedirs",
    "remove",
    "rmtree",
    "truncate",
)
_LEXICON_NAME_MARKS = ("lexicon", "wordlist", "keyword_table", "词表")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
# 边界红线①：本块只许引自身包与 `state`（＋非 appv2 的 stdlib；禁引面见上行禁引模块表）
_ALLOWED_BLOCK_IMPORTS = ("appv2.runtimev2.transport", "appv2.runtimev2.state")

# 行 18 保留集锚：常规多帧 run 的显式期望表（帧序＋一处编号的读数——不随实现漂移）
_NORMAL_RUN: tuple[tuple[str, dict[str, Any]], ...] = (
    ("session", {"run_id": _RUN_ID, "resume": False}),
    ("step", {"step": "decision", "seq": 1, "title": "N1 读题与定型"}),
    ("text", {"content": "先看子问题：某井去年配产量。", "kind": "understanding"}),
    ("tool", {"tool": "data_query", "status": "ok", "seq": 2, "message": "命中 3 行"}),
    (
        "observation",
        {"index": 1, "source": "报告", "content": "配产台账（区块级）", "trust": "high"},
    ),
    ("step", {"step": "observe", "seq": 3, "title": "N5 观察回流"}),
    (
        "verdict",
        {
            "cited": True,
            "rewritten": False,
            "split": [],
            "supported": True,
            "attribution": {"anchors": [], "cross": []},
        },
    ),
    ("citation", {"index": 1, "source": "报告", "source_id": "f4", "trust": "high"}),
    ("text", {"content": "某井 2026 年日产油量 12.5 吨。"}),
    ("verdict", {"status": "completed", "run_id": _RUN_ID, "manifest_digest": "digest-1"}),
    ("blackbox", _blackbox_pointer()),
    ("done", {"run_id": _RUN_ID}),
)
_NORMAL_RUN_EXPECTED_IDS: tuple[tuple[int, str], ...] = (
    (-1, "session"),
    (0, "step"),
    (1, "text"),
    (2, "tool"),
    (3, "observation"),
    (4, "step"),
    (5, "verdict"),
    (6, "citation"),
    (7, "text"),
    (8, "verdict"),
    (9, "blackbox"),
    (9, "done"),
)


def _expected_data(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """行 18 的载荷期望（显式写出规格规则）：唯一改造＝`verdict` 注入 `subtype`，其余原样。"""
    if name != "verdict":
        return payload
    return {**payload, "subtype": "final" if "status" in payload else "verify"}


def _leak_findings(text: str) -> list[str]:
    """文本里的内部痕迹命中（行 15 机检面；空＝无痕迹）。"""
    return [
        f"{label}：{match.group(0)}"
        for label, pattern in _LEAK_MARKS
        for match in (re.search(pattern, text),)
        if match is not None
    ]


async def _drain_into(bus: EventBus, cursor: int, sink: list[SseEvent]) -> None:
    """把总线的帧按游标读进 sink（多消费者面用）。"""
    async for frame in bus.stream(cursor):
        sink.append(frame)


async def _spin_until(condition: Callable[[], bool], *, spins: int = _SETTLE_SPINS) -> None:
    """自旋等待条件成立（`sleep(0)` 确定性推进，无 wall-clock）——消费者推进面用。"""
    for _ in range(spins):
        if condition():
            return
        await asyncio.sleep(0)
    raise AssertionError("等待消费者推进超时")


def _legs(events: Sequence[str]) -> list[list[str]]:
    """按 `session` 帧切腿（跑批载体＝多腿拼一个 `frames` 数组，session 帧开新腿）。"""
    legs: list[list[str]] = []
    current: list[str] = []
    for event in events:
        if event == "session" and current:
            legs.append(current)
            current = []
        current.append(event)
    if current:
        legs.append(current)
    return legs


@lru_cache(maxsize=1)
def _golden_frame_sets() -> tuple[tuple[str, tuple[dict[str, Any], ...]], ...]:
    """全部 golden 载体的帧序（行 11／行 14 的读数面；解析形复用 -a 的 `_parse_golden`）。"""
    carriers = tuple(
        (path.name, tuple(frames))
        for path in _golden_frame_files()
        for frames in (_parse_golden(path),)
        if frames
    )
    if not carriers:
        pytest.skip(f"B5 钉源载体不在场：{_FRAMES_DIR}")
    return carriers


def _transport_sources() -> list[tuple[str, ast.Module]]:
    """本块源码（`appv2/runtimev2/transport/`）逐文件 AST——行 16 扫描域。"""
    return [
        (path.name, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_TRANSPORT_DIR.rglob("*.py"))
    ]


def _is_forbidden_module(module: str) -> bool:
    return module in _FORBIDDEN_IMPORT_MODULES or module.split(".")[0] in _FORBIDDEN_IMPORT_MODULES


def _call_findings(node: ast.Call) -> list[str]:
    """一次调用的判据命中——正则族根名的调用、模型面调用名、落盘调用名。"""
    findings: list[str] = []
    target = node.func
    if isinstance(target, ast.Attribute):
        root = target
        while isinstance(root, ast.Attribute):
            root = root.value
        root_name = root.id if isinstance(root, ast.Name) else ""
        if root_name in {"re", "regex"} and target.attr in _REGEX_CALL_NAMES:
            findings.append(f"正则语义判定 {root_name}.{target.attr}")
        if target.attr in _MODEL_CALL_NAMES:
            findings.append(f"模型调用 .{target.attr}")
        if target.attr in _WRITE_CALL_NAMES:
            findings.append(f"落盘调用 .{target.attr}")
    elif isinstance(target, ast.Name):
        if target.id in _MODEL_CALL_NAMES:
            findings.append(f"模型调用 {target.id}")
        if target.id in _WRITE_CALL_NAMES:
            findings.append(f"落盘调用 {target.id}")
    return findings


def _str_collections(tree: ast.Module) -> list[tuple[int, set[str]]]:
    """字符串集合字面量／`set|frozenset(...)` 的元素集（疑似语义词表扫描用）。"""
    found: list[tuple[int, set[str]]] = []
    for node in ast.walk(tree):
        elements: list[ast.expr] = []
        if isinstance(node, (ast.Set, ast.Tuple, ast.List)):
            elements = list(node.elts)
        elif isinstance(node, ast.Dict):
            elements = [key for key in node.keys if key is not None]
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"set", "frozenset"}
        ):
            for argument in node.args:
                if isinstance(argument, (ast.Set, ast.Tuple, ast.List)):
                    elements.extend(argument.elts)
        else:
            continue
        found.append(
            (
                node.lineno,
                {
                    element.value
                    for element in elements
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                },
            )
        )
    return found


def _judgement_or_model_findings(trees: Sequence[tuple[str, ast.Module]]) -> list[str]:
    """行 16 的 AST 判据：词表／正则语义判定、模型调用、落盘在本块源码里的全部位点。"""
    findings: list[str] = []
    for name, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_forbidden_module(alias.name):
                        findings.append(f"{name}:{node.lineno} 禁引模块 {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if _is_forbidden_module(module):
                    findings.append(f"{name}:{node.lineno} 禁引模块 {module}")
            elif isinstance(node, ast.Call):
                findings.extend(
                    f"{name}:{node.lineno} {finding}" for finding in _call_findings(node)
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if any(mark in node.name.lower() for mark in _LEXICON_NAME_MARKS):
                    findings.append(f"{name}:{node.lineno} 词表名面 {node.name}")
            elif isinstance(node, ast.Name):
                if any(mark in node.id.lower() for mark in _LEXICON_NAME_MARKS):
                    findings.append(f"{name}:{node.lineno} 词表名面 {node.id}")
        for line, values in _str_collections(tree):
            for value in sorted(values):
                if not _IDENTIFIER.match(value):
                    findings.append(f"{name}:{line} 疑似语义词表项 {value!r}")
    return findings


def _import_findings(trees: Sequence[tuple[str, ast.Module]]) -> list[str]:
    """import 白名单（边界红线①的 AST 降维）：本块只许引自身包与 `state`。"""
    findings: list[str] = []
    for name, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                if module.startswith("appv2.") and not module.startswith(_ALLOWED_BLOCK_IMPORTS):
                    findings.append(f"{name}:{node.lineno} 越界引块 {module}")
    return findings


def _stack_text_findings(trees: Sequence[tuple[str, ast.Module]]) -> list[str]:
    """行 15 的 AST 面：本块源码里堆栈／异常文本的构造位点。

    判据面＝`traceback`／`sys` 引用、`repr(`／`str(` 调用、堆栈读取属性（`exc_info` 一族）
    ——本块不构造内部痕迹文本（载荷内容纪律归发射方，本块只保三类定形载荷与零加键）。
    """
    findings: list[str] = []
    for name, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                findings.extend(
                    f"{name}:{node.lineno} 禁引模块 {alias.name}"
                    for alias in node.names
                    if alias.name.split(".")[0] in {"traceback", "sys"}
                )
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in {"traceback", "sys"}:
                    findings.append(f"{name}:{node.lineno} 禁引模块 {node.module}")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"repr", "str"}
            ):
                findings.append(f"{name}:{node.lineno} 字符串化调用 {node.func.id}")
            elif isinstance(node, ast.Attribute) and node.attr in {
                "exc_info",
                "format_exc",
                "print_exc",
            }:
                findings.append(f"{name}:{node.lineno} 堆栈读取面 .{node.attr}")
    return findings


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """本模块／类／函数 docstring 的 Constant 节点 id（说明面——不算法定组装位点）。"""
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.body:
            continue
        head = node.body[0]
        if (
            isinstance(head, ast.Expr)
            and isinstance(head.value, ast.Constant)
            and isinstance(head.value.value, str)
        ):
            docstrings.add(id(head.value))
    return docstrings


def _enclosing_function(tree: ast.Module, node: ast.AST) -> str:
    """节点所在的最内层函数名（模块级＝`<module>`）。"""
    best = "<module>"
    best_span = -1
    for candidate in ast.walk(tree):
        if not isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = candidate.end_lineno or candidate.lineno
        if not (candidate.lineno <= node.lineno <= end):
            continue
        span = end - candidate.lineno
        if best_span == -1 or span < best_span:
            best_span, best = span, candidate.name
    return best


def _envelope_assembly_sites(
    trees: Sequence[tuple[str, ast.Module]],
) -> list[tuple[str, str]]:
    """信封字节形的组装位点：含三行标记＋尾空行的字符串字面量（docstring 除外）。

    「禁手写第二套帧通路」的降维机检面（规格「框架与依赖红线」末条「信封实现单点断言」
    登记待补）——本块恰一处，且在 `envelope` 内。
    """
    sites: list[tuple[str, str]] = []
    for name, tree in trees:
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                text = "".join(
                    part.value
                    for part in node.values
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                )
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
            ):
                text = node.value
            else:
                continue
            if all(mark in text for mark in ("id: ", "event: ", "data: ")) and "\n\n" in text:
                sites.append((name, _enclosing_function(tree, node)))
    return sites


def _envelope_definitions(trees: Sequence[tuple[str, ast.Module]]) -> list[str]:
    """定义 `envelope` 的文件清单（信封实现单点面）。"""
    return [
        name
        for name, tree in trees
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "envelope"
    ]


def _frame_name_literals(trees: Sequence[tuple[str, ast.Module]]) -> list[tuple[str, str]]:
    """`EVENT_KINDS`／`WIRE_FRAMES` 定义处的字符串元素（帧名闭世界的源头面——行 14 用）。"""
    literals: list[tuple[str, str]] = []
    for name, tree in trees:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                continue
            if not any(
                isinstance(target, ast.Name) and target.id in {"EVENT_KINDS", "WIRE_FRAMES"}
                for target in targets
            ):
                continue
            if node.value is None:
                continue
            for element in ast.walk(node.value):
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    literals.append((name, element.value))
    return literals


# ---------- 11 blackbox 帧恰一帧、在 done 之前、只出瘦指针（行为 10） ----------


async def test_blackbox_pointer_frame_last() -> None:
    """`blackbox` 帧恰一帧、在 `done` 之前、只出瘦指针。"""
    # 收口段（行为 10）：业务帧 …→ blackbox（恒发一帧）→ done → close（「随后才 close()」）
    bus = EventBus()
    bus.emit("session", {"run_id": _RUN_ID, "resume": False})
    for name in ("step", "text", "tool", "observation", "notice", "verdict", "citation"):
        bus.emit(name, _payload_for(name))
    pointer = _blackbox_pointer()
    stored_full_text = "黑匣子全文（入库面）：答案正文与步记录原文——全文只入库、不入帧"
    bus.emit("blackbox", pointer)
    bus.emit("done", {"run_id": _RUN_ID})
    bus.close()

    frames = await _collect(bus, 0)
    events = [frame.event for frame in frames]
    assert events.count("blackbox") == 1  # 恰一帧
    assert events.index("blackbox") < events.index("done")  # 在 done 之前
    assert events[-1] == "done"  # 收口帧＝业务帧意义上的流末帧
    assert all(event in WIRE_FRAMES for event in events[events.index("blackbox") + 1 :])

    blackbox = frames[events.index("blackbox")]
    assert set(blackbox.data) == _BLACKBOX_POINTER_KEYS  # 瘦指针恰七键
    assert blackbox.data == pointer  # 逐键真源＝发射方（本块透传、不裁剪不加键）
    assert blackbox.data["counts"] == pointer["counts"]
    for full_text_key in ("answer", "messages", "dialogue", "process_notes", "steps"):
        assert full_text_key not in blackbox.data  # 全文类键位不进帧
    assert stored_full_text not in envelope(blackbox)  # 收口帧字节里没有全文

    # 写库成败都在：以 `stored` 布尔区分（失败腿照发恰一帧、仍在 done 之前）
    failed = EventBus()
    failed.emit(
        "notice", _notice("blackbox_write_failed", content="黑匣子入库失败——本腿按失败披露")
    )
    failed.emit("blackbox", {**_blackbox_pointer(), "stored": False, "error": "黑匣子入库失败"})
    failed.emit("done", {"run_id": _RUN_ID})
    failed.close()
    failed_frames = await _collect(failed, 0)
    boxes = [frame for frame in failed_frames if frame.event == "blackbox"]
    assert len(boxes) == 1 and boxes[0].data["stored"] is False
    assert failed_frames[-1].event == "done"

    # 真帧流证据（载体 `eval/results/frames/`，按 session 帧切腿）：凡含 blackbox 的腿恰一帧、
    # 在 `done` 之前、其后只剩 wire 帧（实测 2026-10-16：157 腿恰一帧、1913 腿未记收口帧）。
    # 0 帧的腿＝载体未记收口帧的切面／挂起腿——不对其立判据（本块只钉「有则恰一帧且在 done
    # 之前」＋驱动面恒发一帧）。
    pointer_legs = 0
    violations: list[str] = []
    for name, golden in _golden_frame_sets():
        for leg in _legs([frame["event"] for frame in golden]):
            if "blackbox" not in leg:
                continue
            pointer_legs += 1
            index = leg.index("blackbox")
            if leg.count("blackbox") != 1 or "done" not in leg or leg.index("done") < index:
                violations.append(f"{name}：{leg[:3]}…{leg[-3:]}")
            elif not all(event in WIRE_FRAMES for event in leg[index + 1 :]):
                violations.append(f"{name}：收口帧之后仍有业务帧 {leg[index + 1 :][:3]}")
    assert violations == []
    assert pointer_legs >= 100, f"真帧流里含收口帧的腿不在场（实得 {pointer_legs}）"


# ---------- 12 多消费者各自独立游标与收束（行为 11） ----------


async def test_multi_consumer_independent_cursor() -> None:
    """多消费者各自独立游标与收束（不靠一次性哨兵）。"""
    bus = EventBus()
    primary: list[SseEvent] = []
    resumed: list[SseEvent] = []
    observer: list[SseEvent] = []

    # 原响应（自 0 起）与断线重连（中途游标加入）在流进行中并行读——各自持游标，互不抢占
    first = asyncio.create_task(_drain_into(bus, 0, primary))
    bus.emit("session", {"run_id": _RUN_ID, "resume": False})
    for index in range(3):
        bus.emit("step", {"step": "decision", "seq": index, "title": f"第 {index} 步"})
    await _spin_until(lambda: len(primary) == 3)
    second = asyncio.create_task(_drain_into(bus, 2, resumed))
    for index in range(3, 6):
        bus.emit("text", {"content": f"增量 {index}"})
    await _spin_until(lambda: len(primary) == 6 and len(resumed) == 4)
    assert [frame.seq for frame in resumed] == [2, 3, 4, 5]  # 重连自断点起：不重不漏

    bus.emit("blackbox", _blackbox_pointer())
    bus.emit("done", {"run_id": _RUN_ID})
    bus.close()  # 收束信号＝close（广播唤醒全部等待者——无一次性哨兵）
    await asyncio.wait_for(asyncio.gather(first, second), timeout=_HANG_TIMEOUT)
    assert [frame.seq for frame in primary] == [0, 1, 2, 3, 4, 5, 6, 6]
    assert [frame.event for frame in primary[-2:]] == ["blackbox", "done"]
    assert [frame.seq for frame in resumed] == [2, 3, 4, 5, 6, 6]
    # 互不抢占：分区不重不漏（原响应前段 ＋ 重连后缀 ＝ 原响应全量，逐帧同一对象）
    boundary = [frame for frame in primary if frame.seq < 2]
    assert _triples([*boundary, *resumed]) == _triples(primary)

    # 后连观察者（第三个消费者，close 之后加入）：仍拿到全量并立即收束——一次性哨兵
    # （单发终止信号被首个消费者吃掉）在此处会永久等待：本测以超时即红守之
    await asyncio.wait_for(_drain_into(bus, 0, observer), timeout=_HANG_TIMEOUT)
    assert _triples(observer) == _triples(primary)

    # 收束判定＝「已关闭且无新帧」：游标越过流末者亦立即收束（不等待不存在的帧）
    tail: list[SseEvent] = []
    await asyncio.wait_for(_drain_into(bus, primary[-1].seq + 1, tail), timeout=_HANG_TIMEOUT)
    assert tail == []


# ---------- 13 close 幂等＋关闭后拒发（行为 12） ----------


async def test_close_idempotent_rejects_after() -> None:
    """`close` 幂等；关闭后 `emit` 抛错。"""
    bus = EventBus()
    emitted = [
        bus.emit("step", _payload_for("step")),
        bus.emit("blackbox", _blackbox_pointer()),
        bus.emit("done", {"run_id": _RUN_ID}),
    ]
    waiting: list[SseEvent] = []
    pending = asyncio.create_task(_drain_into(bus, 0, waiting))
    await _spin_until(lambda: len(waiting) == len(emitted))

    # 三次 close：均无异常、不重复投递终止信号（消费者恰收束一次）、`closed` 恒真
    bus.close()
    bus.close()
    bus.close()
    assert bus.closed is True
    await asyncio.wait_for(pending, timeout=_HANG_TIMEOUT)
    assert _triples(waiting) == _triples(emitted)

    # 关闭后 emit 一律抛错（不静默丢弃）：事件帧与 wire 帧同判；越界帧名亦抛错（closed 先判）
    before = _triples(await _collect(bus, 0))
    assert before == _triples(emitted)
    for name in ("step", "blackbox", "done", "session", "error"):
        with pytest.raises(RuntimeError):
            bus.emit(name, _payload_for(name))
    with pytest.raises(RuntimeError):
        bus.emit("stage", {"state": "process"})

    # 关闭后发射尝试零副作用：历史不动、已发帧不被 close 吞（重放不位移）
    assert _triples(await _collect(bus, 0)) == before
    assert _triples(await _collect(bus, 0)) == _triples(emitted)


# ---------- 14 帧面无截断类帧名（行为 13） ----------


async def test_no_truncation_frame() -> None:
    """帧面无截断类帧名。"""
    # ① 闭世界十三值内无截断类帧名（截断披露走 `notice.type` 面——见
    # `::notice_three_keys_closed_world`）
    assert [name for name in EVENT_KINDS | WIRE_FRAMES if _TRUNCATION_FRAME_MARK.search(name)] == []

    # ② 候选截断类帧名：构造期与发射期一律拒、不留半帧（帧面不带截断信号；重连诚实拒归
    # `api` 开流段）
    bus = EventBus()
    for bad in (
        "replay_truncated",
        "truncated",
        "stream_truncated",
        "partial_replay",
        "replay",
        "cut_off",
        "截断重放",
    ):
        with pytest.raises(ValueError):
            SseEvent(seq=0, event=bad, data={})
        with pytest.raises(ValueError):
            bus.emit(bad, {})
    bus.close()
    assert await _collect(bus, 0) == []

    # ③ 帧名闭世界的源头无截断类成员（AST：`EVENT_KINDS`／`WIRE_FRAMES` 定义处的字符串元素）
    sources = _transport_sources()
    literals = _frame_name_literals(sources)
    assert len(literals) == len(EVENT_KINDS | WIRE_FRAMES)  # 探测器失效即红
    assert [value for _, value in literals if _TRUNCATION_FRAME_MARK.search(value)] == []
    forged = [("probe", ast.parse('EVENT_KINDS = frozenset({"step", "replay_truncated"})'))]
    assert [value for _, value in _frame_name_literals(forged)] == ["step", "replay_truncated"]

    # ④ 真帧流全帧集合里不存在截断类帧名（两半族同扫：runtime 闭世界 ＋ 跑批 UI 壳自有帧名）
    marked = sorted(
        {
            frame["event"]
            for _, golden in _golden_frame_sets()
            for frame in golden
            if _TRUNCATION_FRAME_MARK.search(frame["event"])
        }
    )
    assert marked == []


# ---------- 15 任何帧不携带堆栈／路径／SQL 片段（行为 14） ----------


async def test_no_internal_leak_in_frames() -> None:
    """任何帧不携带堆栈／路径／SQL 片段。"""
    raw_exception = (
        "Traceback (most recent call last):\n"
        '  File "/srv/appv2/runtime/graph.py", line 12, in run\n'
        "    SELECT * FROM petro_well WHERE well_id = 'w-1'"
    )

    # ① 一条 run 全帧扫描：正常腿（含收口帧）＋失败腿（notice{run_failed}＋done）＋异常腿（error）
    normal = EventBus()
    normal.emit("session", {"run_id": _RUN_ID, "resume": False})
    for name in ("step", "text", "tool", "observation", "citation", "verdict", "blackbox"):
        normal.emit(name, _payload_for(name))
    normal.emit("notice", _notice("run_failed", content="工具链异常——本腿按失败披露"))
    normal.emit("done", {"run_id": _RUN_ID})
    normal.close()
    error_bus = EventBus()
    error_bus.emit("step", _payload_for("step"))
    error_bus.emit("error", {"code": "chat_stream_failed", "message": "流内异常——请重新提问"})
    error_bus.close()
    frames = [*await _collect(normal, 0), *await _collect(error_bus, 0)]
    assert {frame.event for frame in frames} >= {"notice", "error", "blackbox", "text"}
    for frame in frames:
        byte_form = envelope(frame)
        assert _leak_findings(byte_form) == [], f"{frame.event} 帧携带内部痕迹：{byte_form}"
        assert _leak_findings(json.dumps(frame.data, ensure_ascii=False)) == []

    # ② 键位面：三类定形载荷把守——原始异常文本没有可安放的键位（行为 7／8／9 的形状面）
    bus = EventBus()
    error_message = "流内异常——请重新提问"
    for payload in (
        {"code": "chat_stream_failed", "message": error_message, "detail": raw_exception},
        {"code": "chat_stream_failed", "message": error_message, "traceback": raw_exception},
    ):
        with pytest.raises(ValueError):
            bus.emit("error", dict(payload))
    for payload in (
        {"type": "run_failed", "gates": [], "content": "失败披露", "detail": raw_exception},
        {"type": "run_failed", "gates": [], "content": "失败披露", "stack": raw_exception},
    ):
        with pytest.raises(ValueError):
            bus.emit("notice", dict(payload))
    with pytest.raises(ValueError):
        bus.emit("ask", {**_ask_payload(), "stack": raw_exception})
    with pytest.raises(ValueError):
        ask_with_trace = _ask_payload()
        ask_with_trace["frame"] = {**ask_with_trace["frame"], "trace": raw_exception}
        bus.emit("ask", ask_with_trace)

    # ③ 本块零加键：唯一注入＝`verdict.subtype`——本块自身不制造内部痕迹
    for name, payload in _NORMAL_RUN:
        frame = bus.emit(name, payload)
        assert set(frame.data) == set(_expected_data(name, payload))

    # ④ AST：本块源码无堆栈文本的构造面（`traceback`／`sys.exc_info`／`repr(`／`str(` 调用）
    sources = _transport_sources()
    assert _stack_text_findings(sources) == [], "本块出现堆栈／异常文本的构造位点"
    assert (
        _stack_text_findings(
            [("probe", ast.parse("import traceback\nsys.exc_info()\nrepr(exc)\nstr(exc)"))]
        )
        != []
    )

    # ⑤ 探测器非空转：伪造痕迹文本逐类命中（含堆栈／文件行／内部路径／SQL／驱动面）
    forged = _leak_findings(raw_exception)
    assert {finding.split("：", 1)[0] for finding in forged} >= {
        "堆栈",
        "文件行",
        "内部路径",
        "SQL",
    }
    assert _leak_findings("黑匣子全文（入库面）：答案正文与步记录原文") == []
    # 注（实测 2026-10-16）：`envelope` 的 `json.dumps(..., default=str)` 兜底是唯一的字符串化
    # 支路——载荷内容纪律归发射方（行为 14 是跨块红线、规格「与闸的挂钩表」登记为人审面）；
    # 本测钉「本块不制造内部痕迹＋三类定形载荷不留位」，不越界替发射方判内容。


# ---------- 16 本块零判断零模型（行为 15 AST 扫描） ----------


def test_no_judgement_or_model_in_transport() -> None:
    """本块零判断零模型（AST 扫描）。"""
    trees = _transport_sources()
    assert trees, "未扫到本块源码（探测器失效）"
    assert _judgement_or_model_findings(trees) == [], "本块出现词表／正则语义判定、模型调用或落盘面"
    # 边界红线①的 AST 降维：本块只许引自身包与 `state`（引其它 runtimev2 块＝成环风险）
    assert _import_findings(trees) == [], "本块引了包内其它块"
    # 边界红线④的 AST 降维：禁手写第二套帧通路——信封字节形恰一处组装位点、在 `envelope` 内
    assert _envelope_assembly_sites(trees) == [("frames.py", "envelope")]
    assert _envelope_definitions(trees) == ["frames.py"]

    # 探测器非空转：伪造源各形逐一命中
    forged = [
        ("probe", ast.parse("import re\nre.match('x', text)")),
        ("probe", ast.parse("from appv2.runtimev2.bookkeeping import notice")),
        ("probe", ast.parse("from appv2.infra.llm_client import embeddings")),
        ("probe", ast.parse("import langgraph")),
        ("probe", ast.parse("open('frames.txt', 'w')")),
        ("probe", ast.parse("llm.complete('提示')")),
        ("probe", ast.parse("LEXICON = {'关键词': '命中'}")),
        ("probe", ast.parse('FRAME = f"id: {seq}\\nevent: {name}\\ndata: {data}\\n\\n"')),
    ]
    findings = _judgement_or_model_findings(forged)
    assert any("禁引模块 re" in finding for finding in findings)
    assert any("禁引模块 langgraph" in finding for finding in findings)
    assert any("禁引模块 appv2.infra.llm_client" in finding for finding in findings)
    assert any("落盘调用 open" in finding for finding in findings)
    assert any("模型调用 .complete" in finding for finding in findings)
    assert any("词表名面 LEXICON" in finding for finding in findings)
    assert any("疑似语义词表项" in finding for finding in findings)
    assert [finding for finding in _import_findings(forged) if "越界引块" in finding] == [
        finding
        for finding in _import_findings(forged)
        if "appv2.runtimev2.bookkeeping" in finding or "appv2.infra.llm_client" in finding
    ]
    assert _envelope_assembly_sites(forged) == [("probe", "<module>")]


# ---------- 17 【边界集】零事件／单帧／超长载荷／关闭后再发（行 17） ----------


async def test_boundary_empty_single_huge_closed() -> None:
    """【边界集】零事件 run／单帧 run／超长载荷／关闭后再发 → 各落对应分支。"""
    # ① 零事件 run：只发 wire 帧（seq＝-1）与无帧 run——`stream(0)` 空、立即收束、不挂
    wire_only = EventBus()
    wire_only.emit("session", {"run_id": _RUN_ID, "resume": False})
    wire_only.emit("done", {"run_id": _RUN_ID})
    wire_only.close()
    assert await _collect(wire_only, 0) == []  # 段首 wire 帧 seq＝-1 落在游标起点之前（-a 定死面）
    assert await _collect(wire_only, 1) == []
    empty = EventBus()
    empty.close()
    assert await asyncio.wait_for(_collect(empty, 0), timeout=_HANG_TIMEOUT) == []

    # ② 单帧 run：恰一帧 → 读尽即收束；续推空；重放相等（重放不位移）
    single = EventBus()
    only = single.emit("text", {"content": "单帧 run"})
    single.close()
    first_read = await _collect(single, 0)
    assert _triples(first_read) == [(only.seq, only.event, only.data)]
    assert await _collect(single, only.seq + 1) == []
    assert _triples(await _collect(single, 0)) == _triples(first_read)

    # ③ 超长载荷：零裁剪透传（不插截断标记、不折行重组）＋信封可渲染且 JSON 往返相等
    huge = "长" * _HUGE_CHARS
    bus = EventBus()
    oversized = bus.emit(
        "observation",
        {
            "index": 1,
            "source": "超长材料",
            "content": huge,
            "trust": "high",
            "offsets": list(range(500)),
            "nested": {"deep": [huge[:100]]},
        },
    )
    assert oversized.data["content"] == huge
    assert len(oversized.data["content"]) == _HUGE_CHARS
    byte_form = envelope(oversized)
    assert len(byte_form) > _HUGE_CHARS
    assert byte_form.endswith("\n\n") and len(byte_form.split("\n")) == 5
    assert json.loads(byte_form.split("\n")[2][len("data: ") :]) == oversized.data
    assert "…" not in byte_form and "truncat" not in byte_form.lower()  # 本块未插截断标记

    # ④ 关闭后再发：事件帧／wire 帧一律抛错（不静默丢弃）＋越界帧名在关闭前抛错且无半帧
    fresh = EventBus()
    kept = fresh.emit("step", _payload_for("step"))
    with pytest.raises(ValueError):
        fresh.emit("stage", {"state": "process"})
    fresh.close()
    read_back = await _collect(fresh, 0)
    assert _triples(read_back) == [(kept.seq, kept.event, kept.data)]  # 越界发射不留半帧
    for name in ("step", "blackbox", "done"):
        with pytest.raises(RuntimeError):
            fresh.emit(name, _payload_for(name))
    assert _triples(await _collect(fresh, 0)) == _triples(read_back)  # 关闭后发射零副作用
    with pytest.raises(ValueError):
        fresh.stream(-1)  # 非法 cursor（错误契约）


# ---------- 18 【保留集】常规多帧 run 的帧序与载荷行为不变（行 18） ----------


async def test_retention_normal_stream_unchanged() -> None:
    """【保留集】常规多帧 run 的帧序与载荷行为不变。"""
    bus = EventBus()
    emitted = [bus.emit(name, payload) for name, payload in _NORMAL_RUN]
    bus.close()
    frames = await _collect(bus, 0)

    # ① 帧序保真（append-only、不重排、不吞帧）＋一处编号读数＝显式期望表
    assert [frame.event for frame in emitted] == [name for name, _ in _NORMAL_RUN]
    assert [(frame.seq, frame.event) for frame in emitted] == list(_NORMAL_RUN_EXPECTED_IDS)
    # 读面＝发出序去掉段首 session 帧（其 seq＝-1 落在游标起点之前——-a 定死面）
    assert [frame.event for frame in frames] == [name for name, _ in _NORMAL_RUN][1:]

    # ② 载荷行为不变：逐帧显式期望（`verdict` 唯一改造＝注入 `subtype`；其余零裁剪零加键）
    assert [frame.data for frame in emitted] == [
        _expected_data(name, payload) for name, payload in _NORMAL_RUN
    ]
    assert [frame.data for frame in frames] == [
        _expected_data(name, payload) for name, payload in _NORMAL_RUN
    ][1:]
    assert emitted[1].data == {"step": "decision", "seq": 1, "title": "N1 读题与定型"}
    assert emitted[10].data == _blackbox_pointer()

    # ③ 信封字节形恒定（恒三行＋空行；`id`＝`seq`；中文逐字不转义）
    for frame in emitted:
        lines = envelope(frame).split("\n")
        assert len(lines) == 5 and lines[3] == "" and lines[4] == ""
        assert lines[0] == f"id: {frame.seq}"
        assert lines[1] == f"event: {frame.event}"
        assert json.loads(lines[2][len("data: ") :]) == frame.data
    assert "某井 2026 年日产油量 12.5 吨。" in envelope(emitted[8])
    assert "\\u" not in envelope(emitted[8])

    # ④ 游标：事件帧 0 起严格递增无跳号；wire 帧＝最后已消费事件 seq、不推进游标
    last_event_seq = -1
    for frame in emitted:
        if frame.event in EVENT_KINDS:
            assert frame.seq == last_event_seq + 1
            last_event_seq = frame.seq
        else:
            assert frame.seq == last_event_seq

    # ⑤ 断线续推不重不漏（后缀逐帧相等）＋重放不位移
    for cursor in range(0, frames[-1].seq + 2):
        assert _triples(await _collect(bus, cursor)) == _triples(
            [frame for frame in frames if frame.seq >= cursor]
        )
    assert _triples(await _collect(bus, 0)) == _triples(frames)

    # ⑥ 多消费者各自独立游标（保留面）：原响应全量、断线重连得后缀；恰一帧收口帧在 done 之前
    primary: list[SseEvent] = []
    resumed: list[SseEvent] = []
    await asyncio.wait_for(_drain_into(bus, 0, primary), timeout=_HANG_TIMEOUT)
    await asyncio.wait_for(_drain_into(bus, 3, resumed), timeout=_HANG_TIMEOUT)
    assert _triples(primary) == _triples(frames)
    assert _triples(resumed) == _triples([frame for frame in frames if frame.seq >= 3])
    events = [frame.event for frame in frames]
    assert events.count("blackbox") == 1 and events.index("blackbox") < events.index("done")

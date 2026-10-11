"""V2-54 黑匣子观测面验收（票面附 E T1–T5 逐条落测）。

- 事件闭世界九类扩员（blackbox）；
- distill 蒸馏纯函数（形状钉／异常骨架钉／巨体键排除钉）；
- 执行器收口单点发射（流内最后一件／模型原话与观察全字段在场）；
- 快照回放渲染（人读转写／JSON 双形）。
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from appv2.runtime import AskRequest, RunStore
from appv2.runtime.blackbox import distill, pointer, render_snapshots
from appv2.runtime.events import EVENT_BLACKBOX, EVENT_KINDS
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    HAPPY_QUESTION,
    HAPPY_SCRIPT,
    QueueQueryEngine,
    _rows_outcome,
    drain,
    make_runtime,
)

# ---------- T1 · 事件闭世界九类 ----------


def test_blackbox_event_kind_in_closed_world() -> None:
    assert EVENT_BLACKBOX == "blackbox"
    assert EVENT_BLACKBOX in EVENT_KINDS


# ---------- T2/T3 · distill 蒸馏纯函数 ----------


def _final_state() -> dict[str, Any]:
    return {
        "run_id": "run-x",
        "question": "问 W-21 的检泵周期。",
        "status": "completed",
        "actor": "dev-u1",
        "history": [
            {"role": "user", "content": "【相位①·业务澄清】……"},
            {"role": "assistant", "content": '{"action": "finalize"}'},
        ],
        "steps": [
            {
                "step": "decision",
                "seq": 1,
                "title": "澄清定稿：材料足够——直答收口",
                "payload": {"phase": "clarify", "emission": {"kind": "finalize"}},
            }
        ],
        "observations": [
            {
                "index": 1,
                "source": "《月报-202608》",
                "content": "三、检泵作业明细……512……",
                "trust": "report",
                "locator": {"kind": "fragment", "report": "月报-202608"},
                "version": "v3",
            }
        ],
        "notices": [{"type": "no_hit", "gates": [], "content": "FAQ 库无命中"}],
        "ledger_dump": {"huge": "projection"},
        "manifests": [{"source_type": ["ledger_dump"]}],
        "answer": "答案：512 天[1]。",
        "rounds": 1,
        "discover_used": 2,
        "budget_hit": "",
        "pending_ask": None,
    }


def test_distill_full_shape() -> None:
    d = distill(_final_state(), run_id="run-x")
    # 身份面
    assert d["run_id"] == "run-x"
    assert d["question"] == "问 W-21 的检泵周期。"
    assert d["status"] == "completed"
    assert d["error"] == ""
    # 模型原话随 history 全量在场
    assert d["history"][-1]["content"] == '{"action": "finalize"}'
    # 步骤 payload（发射原文）在场
    assert d["steps"][0]["payload"] == {"phase": "clarify", "emission": {"kind": "finalize"}}
    # 观察全字段（locator.kind）保留
    obs = d["observations"][0]
    assert obs["locator"]["kind"] == "fragment"
    assert obs["version"] == "v3"
    # 白名单标量键
    assert d["answer"] == "答案：512 天[1]。"
    assert d["rounds"] == 1 and d["discover_used"] == 2 and d["budget_hit"] == ""
    # 巨体/噪声键排除
    assert "ledger_dump" not in d
    assert "manifests" not in d


def test_distill_error_skeleton() -> None:
    d = distill(None, run_id="run-y", error="boom")
    assert d["run_id"] == "run-y"
    assert d["error"] == "boom"
    assert "history" not in d and "observations" not in d  # 骨架无状态键


def test_distill_dirty_value_degrades() -> None:
    class Odd:
        def __str__(self) -> str:  # 非常规值——降级 str 不翻车
            return "odd!"

    d = distill({"question": "q", "verdict": {"supported": Odd()}}, run_id="run-z")
    assert d["verdict"]["supported"] == "odd!"


# ---------- T4 · 执行器收口：瘦指针出流＋蒸馏入库（V2-55 改形） ----------


@pytest.mark.asyncio
async def test_blackbox_pointer_last_and_stored(tmp_path) -> None:  # type: ignore[no-untyped-def]
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
    events = await drain(handle)
    kinds = [e.event for e in events]
    assert kinds[-1] == "blackbox"  # 收口前最后一件（close 前单点发射）
    data = next(e.data for e in events if e.event == "blackbox")
    # 瘦指针：身份面＋入库标记＋计数——无过程载荷（帧不收录大体档案）
    assert data["run_id"] == handle.run_id
    assert data["question"] == HAPPY_QUESTION
    assert data["stored"] is True
    assert data["bytes"] > 0
    assert data["counts"]["history"] > 0
    assert "history" not in data and "observations" not in data and "steps" not in data
    # 完整面在库：模型原话与观察全字段经 get_blackbox 取回
    payload = await RunStore(db).get_blackbox(handle.run_id)
    assert payload is not None
    assistant_texts = [
        str(t.get("content")) for t in payload["history"] if t.get("role") == "assistant"
    ]
    assert any("finalize" in text for text in assistant_texts)
    assert isinstance(payload["observations"], list)
    assert "ledger_dump" not in payload  # 蒸馏语义不变——巨体键排除


@pytest.mark.asyncio
async def test_blackbox_store_overwrite_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
    await drain(handle)
    store = RunStore(db)
    first = await store.get_blackbox(handle.run_id)
    assert first is not None
    await store.put_blackbox(handle.run_id, {"run_id": handle.run_id, "marker": "v2"})
    second = await store.get_blackbox(handle.run_id)
    assert second is not None and second.get("marker") == "v2"  # upsert 覆写取末次


# ---------- T6 · 瘦指针形状（blackbox.pointer 单点） ----------


def test_pointer_shape() -> None:
    record = {
        "run_id": "run-x",
        "question": "q",
        "status": "completed",
        "error": "",
        "history": [{"role": "assistant", "content": "a"}, {"role": "user", "content": "b"}],
        "observations": [],
        "steps": [{"seq": 1}],
        "ledger_dump": {"huge": "excluded"},
    }
    p = pointer(record, stored=True, bytes_written=123)
    assert p == {
        "run_id": "run-x",
        "question": "q",
        "status": "completed",
        "error": "",
        "stored": True,
        "bytes": 123,
        "counts": {"history": 2, "observations": 0, "steps": 1},
    }


# ---------- T5 · 快照回放渲染 ----------


def _fake_snapshots() -> list[dict[str, Any]]:
    return [
        {
            "checkpoint_id": "cp-1",
            "channels": {
                "question": "问 W-21 的检泵周期。",
                "history": [
                    {"role": "user", "content": "【相位①】"},
                    {"role": "assistant", "content": '{"action": "finalize"}'},
                ],
                "observations": [],
            },
        },
        {
            "checkpoint_id": "cp-2",
            "channels": {
                "observations": [
                    {
                        "index": 1,
                        "source": "《月报》",
                        "content": "512 天",
                        "trust": "report",
                        "locator": {"kind": "fragment"},
                    }
                ],
                "rounds": 2,
            },
        },
    ]


def test_render_snapshots_human() -> None:
    text = render_snapshots(_fake_snapshots())
    assert "cp-1" in text and "cp-2" in text  # 快照标头
    assert '{"action": "finalize"}' in text  # 模型原话渲染
    assert "fragment" in text  # 观察全字段（locator.kind）渲染
    assert "rounds" in text  # 标量通道渲染


def test_render_snapshots_json() -> None:
    payload = json.loads(render_snapshots(_fake_snapshots(), as_json=True))
    assert isinstance(payload, list) and len(payload) == 2
    assert payload[0]["checkpoint_id"] == "cp-1"
    assert payload[1]["channels"]["rounds"] == 2

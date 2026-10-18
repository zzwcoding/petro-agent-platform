"""V2-89 · doc_retrieve 旁路留痕钉测（入参＋候选命中——票面测试 1–4 逐条落测）。

四条对应（票面「测试」节）：
- retrieval_calllog_written：桩检索返回 3 条 → 文件 1 行、字段齐、hits 3 条；
- retrieval_calllog_off_env：`RETRIEVAL_CALL_LOG=off` → 零文件、工具返回不变；
- retrieval_calllog_write_failure_degrades：路径不可写（monkeypatch 抛错）→ 工具
  返回不变、仅告警；
- retrieval_calllog_empty_hits：空集 → 记 1 行 `returned=0`。

底座＝`FakeRetrievalEngine` 剧本化应答（`appv2.tools.fake`——工具层纯转发）＋
`tmp_path` 重指留痕目录（同 `tests/infra/test_gateway_calllog.py` 范式）；本票
零 LLM 调用、零真实检索。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from appv2.retrieval import Observation as RetrievalObservation
from appv2.retrieval import RetrievalBundle
from appv2.tools import (
    DOC_RETRIEVE,
    STATUS_OK,
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    ToolContext,
    ToolRegistry,
    retrieval_calllog,
)

# 留痕记录键闭世界（票面「施工基准」字段表逐字）。
_RECORD_KEYS = {
    "ts",
    "run_id",
    "sub_question_id",
    "need",
    "top_k",
    "hits",
    "returned",
    "truncated",
}
_HIT_KEYS = {"id", "source", "score", "chars", "has_section"}

CTX = ToolContext(actor="dev-u1", budget=7)
QUESTION = "W-111 井是干什么的？"


def _obs(
    fragment_id: str,
    *,
    report: str,
    score: float,
    text: str,
    section: str | None,
) -> RetrievalObservation:
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=score,
        leg="keyword",
        family="completion",
        fragment_id=fragment_id,
        report_id=f"rpt-{fragment_id}",
        report=report,
        library_id="lib-1",
        library="渤中34-5完井工程库",
        section=section,
        locator={
            "library": "渤中34-5完井工程库",
            "report": report,
            "section": section or "",
            "fragment_id": fragment_id,
        },
    )


def _bundle(*, hits: list[RetrievalObservation], recalled: int = 0) -> RetrievalBundle:
    return RetrievalBundle(
        observations=list(hits),
        window_note=f"共检索到 {recalled} 条材料，{len(hits)} 条用进了答案",
        recalled=recalled,
        sent=len(hits),
    )


def _registry(bundle: RetrievalBundle) -> ToolRegistry:
    return ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(bundle=bundle),
    )


def _read(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _jsonl_files(directory: Path) -> list[Path]:
    """目录内 JSONL 分片（同步读面件——异步用例只调本件，不散用 Path I/O）。"""
    return sorted(directory.glob("*.jsonl"))


async def _call(registry: ToolRegistry) -> Any:
    return await registry.call(DOC_RETRIEVE, {"question": QUESTION}, CTX)


async def test_retrieval_calllog_written(tmp_path: Path, monkeypatch) -> None:
    """桩检索返回 3 条 → 文件 1 行、字段齐、hits 3 条（召回池大于入窗＝截断位真）。"""
    monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", tmp_path)
    monkeypatch.delenv("RETRIEVAL_CALL_LOG", raising=False)
    registry = _registry(
        _bundle(
            hits=[
                _obs("f-1", report="A-W11井完井工程报告", score=2.0,
                     text="同平台 W-111 井为观察井，不承担生产任务。", section="1.1 井位与井别"),
                _obs("f-2", report="A-W11井完井工程报告", score=1.0,
                     text="1.2 井身结构（实钻）层次 套管尺寸 下深（米）", section="1.2 井身结构"),
                _obs("f-3", report="Y-21井完井工程报告", score=0.5,
                     text="Y-21 井位于渤中 34-8 油田一号构造东高点。", section=None),
            ],
            recalled=11,
        )
    )
    result = await _call(registry)
    assert result.status == STATUS_OK

    path = _jsonl_files(tmp_path)[0]
    recs = _read(path)
    assert len(recs) == 1  # 单次调用＝单行
    record = recs[0]
    assert set(record) == _RECORD_KEYS  # 字段齐（闭世界——无多键无缺键）
    assert isinstance(record["ts"], str) and record["ts"]
    assert isinstance(record["run_id"], str) and isinstance(record["sub_question_id"], str)
    # 入参面（need/budget/family_hints——取不到③的可查面）：RetrievalNeed 四字段逐字。
    assert record["need"] == {
        "question": QUESTION,
        "anchors": [],
        "family_hints": [],
        "budget": 7,
    }
    assert record["top_k"] == 7  # 送窗预算 M（ctx.budget 逐字进 need）
    assert record["returned"] == 3
    assert len(record["hits"]) == 3  # hits 3 条
    assert all(set(hit) == _HIT_KEYS for hit in record["hits"])
    assert record["hits"][0] == {
        "id": "f-1",
        "source": "A-W11井完井工程报告",
        "score": 2.0,
        "chars": len("同平台 W-111 井为观察井，不承担生产任务。"),
        "has_section": True,
    }
    assert record["hits"][2]["has_section"] is False  # section 标记如实
    # 召回池 11 > 入窗 3 → 发生截断（供给窗裁掉候选）。
    assert record["truncated"] is True
    # 不落全文：片段正文一字不进留痕件（只字符数）。
    raw = path.read_text(encoding="utf-8")
    assert "观察井" not in raw and "套管尺寸" not in raw


async def test_retrieval_calllog_off_env(tmp_path: Path, monkeypatch) -> None:
    """`RETRIEVAL_CALL_LOG=off` → 零文件、工具返回不变。"""
    monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", tmp_path)
    bundle = _bundle(
        hits=[
            _obs("f-1", report="A-W11井完井工程报告", score=2.0,
                 text="同平台 W-111 井为观察井。", section="1.1 井位与井别"),
        ],
        recalled=4,
    )
    monkeypatch.setenv("RETRIEVAL_CALL_LOG", "off")
    off_result = await _call(_registry(bundle))
    assert _jsonl_files(tmp_path) == []  # 零文件

    # 工具返回不变：同桩在开关 on 下（另目录）逐字段等值。
    on_dir = tmp_path / "on"
    monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", on_dir)
    monkeypatch.delenv("RETRIEVAL_CALL_LOG", raising=False)
    on_result = await _call(_registry(bundle))
    assert len(_jsonl_files(on_dir)) == 1  # 开关复位后照记
    assert on_result == off_result  # 留痕开关不改工具返回（结构/文案零改）


async def test_retrieval_calllog_write_failure_degrades(
    tmp_path: Path, monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    """路径不可写（monkeypatch 抛错）→ 工具返回不变、仅告警（旁路观测纪律）。"""
    monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", tmp_path)
    monkeypatch.delenv("RETRIEVAL_CALL_LOG", raising=False)
    bundle = _bundle(
        hits=[
            _obs("f-1", report="A-W11井完井工程报告", score=2.0,
                 text="同平台 W-111 井为观察井。", section="1.1 井位与井别"),
        ],
    )
    monkeypatch.setattr(
        Path, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
    )
    with caplog.at_level("WARNING"):
        result = await _call(_registry(bundle))  # 不抛
    assert result.status == STATUS_OK
    assert len(result.observations) == 2  # 1 支检索观察＋1 支 window_note 声明
    assert any("retrieval calllog" in rec.message for rec in caplog.records)
    assert _jsonl_files(tmp_path) == []  # 写失败＝零残留


async def test_retrieval_calllog_empty_hits(tmp_path: Path, monkeypatch) -> None:
    """空集 → 记 1 行 `returned=0`（成功/空集都记——异常分支不记）。"""
    monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", tmp_path)
    monkeypatch.delenv("RETRIEVAL_CALL_LOG", raising=False)
    result = await _call(_registry(_bundle(hits=[])))
    assert result.status == STATUS_OK
    recs = _read(_jsonl_files(tmp_path)[0])
    assert len(recs) == 1
    assert recs[0]["returned"] == 0
    assert recs[0]["hits"] == []
    assert recs[0]["truncated"] is False  # 召回 0／入窗 0＝不判截断（零猜测）

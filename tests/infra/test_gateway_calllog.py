"""V2-80f · LLM 调用留痕钉测（发送 messages＋返回全文——B6 单点旁路观测）。"""

from __future__ import annotations

import json
from pathlib import Path

from appv2.infra.gateway import calllog


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_record_call_success_shape(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(calllog, "_LOG_DIR", tmp_path)
    messages = [{"role": "system", "content": "红线"}, {"role": "user", "content": "问题"}]
    calllog.record_call(
        alias="petro-main", caller="v2.runtime.understand", run_id="run-x",
        messages=messages, requested="petro-main",
        content="理解：问产能\n指标候选：日产油量", prompt_tokens=100,
        completion_tokens=20, duration_ms=900,
    )
    recs = _read(next(tmp_path.glob("*.jsonl")))
    assert len(recs) == 1
    rec = recs[0]
    assert rec["caller"] == "v2.runtime.understand" and rec["run_id"] == "run-x"
    assert rec["messages"] == messages  # 发送全文逐条在案
    assert rec["response"]["content"].startswith("理解：")  # 返回全文在案
    assert rec["error"] is None


def test_record_call_error_and_off_switch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(calllog, "_LOG_DIR", tmp_path)
    calllog.record_call(alias="a", caller="c", run_id="r", messages=[], requested="a",
                        error="RateLimitError: 429")
    recs = _read(next(tmp_path.glob("*.jsonl")))
    assert recs[0]["response"] is None and "429" in recs[0]["error"]
    # off＝零写
    monkeypatch.setenv("LLM_CALL_LOG", "off")
    calllog.record_call(alias="a", caller="c", run_id="r", messages=[], requested="a")
    assert len(_read(next(tmp_path.glob("*.jsonl")))) == 1  # 未增行


def test_record_call_failure_never_breaks_call(tmp_path: Path, monkeypatch) -> None:
    """留痕故障降级——不向调用方冒泡（旁路观测纪律）。"""
    monkeypatch.setattr(calllog, "_LOG_DIR", tmp_path)
    monkeypatch.setattr(Path, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    calllog.record_call(alias="a", caller="c", run_id="r", messages=[], requested="a")  # 不抛


def test_cached_tokens_extraction_shapes() -> None:
    """缓存命中字段三形提取（litellm 归一/DeepSeek 原生/缺省零）。"""
    from appv2.infra.llm_client import _cached_tokens_of

    assert _cached_tokens_of({"prompt_tokens_details": {"cached_tokens": 512}}) == 512
    assert _cached_tokens_of({"prompt_cache_hit_tokens": 700}) == 700
    assert _cached_tokens_of({}) == 0

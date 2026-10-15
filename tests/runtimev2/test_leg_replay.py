"""harness 地基自证（eng/04 §五步骤 1 第二件）：Q15.jsonl 真实帧的解析＋断言辅助。

原料＝eval/results/V2-80-员工模拟批跑2/runs/Q15.jsonl（git 在库——离线可跑）：
open leg、23 帧、summary 收尾。违例路径用 tmp_path 合成件验 fail-fast；子集比对
语义用合成流（LegRecording 直接构）验。本件只自证 harness 能力本身——Q15 全量
行为钉（L3）随织网步骤 3/4 另落，不在本件过度钉。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.runtimev2.leg_replay import (
    LegFrame,
    LegRecording,
    sample_leg,
)

Q15 = sample_leg("Q15")

# Q15 真实 event 序（帧级指纹的真源——解析自 Q15.jsonl 帧行）。
Q15_EVENTS: tuple[str, ...] = (
    "session", "step", "text", "step", "step", "step", "tool", "step", "notice",
    "tool", "step", "notice", "tool", "step", "notice", "step", "step", "verdict",
    "step", "text", "verdict", "blackbox", "done",
)

OPEN = '{"leg": "open", "http": 200, "body": {"question": "测试问"}}'
FRAME = '{"leg": "frame", "id": "0", "t": 0.1, "event": "step", "data": {"seq": 1}}'
SUMMARY = '{"summary": {"status": "done"}}'


# ---------- 真实样本解析（Q15） ----------


class TestLoadQ15:
    def test_open_and_summary(self) -> None:
        rec = LegRecording.load(Q15)
        assert rec.question == "去年这个时候咱区块干得咋样？"
        assert rec.http == 200
        assert len(rec.frames) == 23
        assert rec.summary is not None
        assert rec.summary["id"] == "Q15"
        assert rec.summary["frames"] == 23
        assert rec.summary["n_steps"] == 10
        assert rec.summary["status"] == "done"

    def test_first_frame_line_numbers(self) -> None:
        rec = LegRecording.load(Q15)
        assert rec.frames[0].line == 2  # open 占第 1 行
        assert rec.frames[-1].line == 24  # summary 收第 25 行

    def test_event_fingerprint(self) -> None:
        rec = LegRecording.load(Q15)
        assert rec.events() == Q15_EVENTS
        rec.assert_fingerprint(Q15_EVENTS)  # 序列形
        rec.assert_fingerprint("|".join(Q15_EVENTS))  # 字符串形同参

    def test_frame_data_subset(self) -> None:
        rec = LegRecording.load(Q15)
        session = rec.assert_data("session", {"resume": False})
        assert session.data["run_id"] == "run-501ff23a"
        rec.assert_data("notice", {"type": "subtask_refused"}, nth=1)
        rec.assert_data("notice", {"type": "subtask_refused"}, nth=3)
        rec.assert_data("verdict", {"subtype": "verify", "supported": 0}, nth=1)
        rec.assert_data("verdict", {"subtype": "final", "status": "completed"}, nth=2)

    def test_presence_absence_and_counts(self) -> None:
        rec = LegRecording.load(Q15)
        assert rec.count("step") == 10  # 与 summary n_steps 对账
        assert rec.assert_has("done").data["run_id"] == rec.assert_has("session").data["run_id"]
        rec.assert_absent("ask")  # Q15 n_asks=0
        rec.assert_absent("citation")


# ---------- 解析违例 fail-fast（合成件） ----------


class TestFailFastParsing:
    @pytest.mark.parametrize(
        ("lines", "frag"),
        [
            pytest.param([], "空文件", id="empty-file"),
            pytest.param([FRAME], "首行 leg≠open", id="frame-first"),
            pytest.param([OPEN, '{bad json'], "非法 JSON", id="bad-json"),
            pytest.param(
                [OPEN, '{"leg": "frame", "id": "0", "t": 0.1, "event": "step"}'],
                "缺 data",
                id="frame-no-data",
            ),
            pytest.param(
                [OPEN, '{"leg": "frame", "t": 0.1, "event": "step", "data": {}}'],
                "缺 id",
                id="frame-no-id",
            ),
            pytest.param(
                [OPEN, '{"leg": "frame", "id": "0", "event": "step", "data": {}}'],
                "缺 t",
                id="frame-no-t",
            ),
            pytest.param(
                [OPEN, '{"leg": "frame", "id": "0", "t": 0.1, "data": {}}'],
                "缺 event",
                id="frame-no-event",
            ),
            pytest.param([OPEN, OPEN], "open 行只许首行", id="open-twice"),
            pytest.param([OPEN, SUMMARY, FRAME], "summary 后仍出现帧行", id="frame-after-summary"),
            pytest.param([OPEN, SUMMARY, SUMMARY], "summary 行重复", id="summary-twice"),
            pytest.param([OPEN, '{"event": "step", "data": {}}'], "无法识别的行", id="unknown-row"),
        ],
    )
    def test_value_error_fail_fast(
        self, tmp_path: Any, lines: list[str], frag: str
    ) -> None:
        p = tmp_path / "rec.jsonl"
        p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        with pytest.raises(ValueError, match=frag):
            LegRecording.load(p)

    def test_minimal_stream_without_summary_loads(self, tmp_path: Any) -> None:
        p = tmp_path / "rec.jsonl"
        p.write_text(f"{OPEN}\n{FRAME}\n", encoding="utf-8")
        rec = LegRecording.load(p)
        assert rec.summary is None
        assert rec.events() == ("step",)


# ---------- 断言辅助语义（合成流直构） ----------


def _synthetic(data: dict[str, Any]) -> LegRecording:
    return LegRecording(
        question="合成问",
        http=200,
        frames=[LegFrame(id="0", t=0.0, event="step", data=data, line=2)],
        summary=None,
    )


class TestSubsetSemantics:
    def test_nested_dict_recursive_subset(self) -> None:
        rec = _synthetic({"counts": {"dialogue": 2, "steps": 10}})
        rec.assert_data("step", {"counts": {"steps": 10}})

    def test_list_requires_exact_order(self) -> None:
        rec = _synthetic({"ids": ["a", "b"]})
        rec.assert_data("step", {"ids": ["a", "b"]})
        with pytest.raises(AssertionError, match="全等"):
            rec.assert_data("step", {"ids": ["b", "a"]})

    def test_missing_key_and_type_mismatch(self) -> None:
        rec = _synthetic({"counts": {"steps": 10}, "supported": 0})
        with pytest.raises(AssertionError, match="子集键缺失"):
            rec.assert_data("step", {"nope": 1})
        with pytest.raises(AssertionError, match="期望 mapping"):
            rec.assert_data("step", {"supported": {"raised": True}})


class TestAssertionErrors:
    def test_fingerprint_mismatch_shows_both(self) -> None:
        rec = _synthetic({})
        with pytest.raises(AssertionError, match="帧序列指纹失配"):
            rec.assert_fingerprint("session|done")

    def test_has_nth_overflow_and_absent_violation(self) -> None:
        rec = _synthetic({})
        with pytest.raises(AssertionError, match="第 2 帧缺席"):
            rec.assert_has("step", nth=2)
        with pytest.raises(AssertionError, match="应缺席却在场"):
            rec.assert_absent("step")

    def test_nth_must_be_positive(self) -> None:
        rec = _synthetic({})
        with pytest.raises(ValueError, match="nth 从 1 计"):
            rec.assert_has("step", nth=0)

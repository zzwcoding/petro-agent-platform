"""ask.py v2 事件解析＋asks_url 形参化纯函数测试（红先绿后——V2-12 · P-015）。

被测件＝eval/results/tools/ask.py 内纯函数（跑批脚本本体照 rerun.py 惯例
不进 tests/，解析纯函数进 tests/——tests/tools/test_plan_golden_judge.py
同款先例）。

wire 形真源＝appv2/api/wire.py（runtime 八类事件＋session/done/error 保留
帧＋verdict subtype 拆形）与 appv2/runtime/graph.py 发射点载荷；本文件帧
构造照其发射形：
- step{text,seq,title}（六类＝understand/plan/tool/observe/verify/answer）
- text{content}／tool{tool,status,seq,message}
- observation{index,source,content,trust}
- ask{frame,run_id}（挂起帧原样随 run_id）
- verdict 两形：verify{subtype,supported,rewritten,split,cited}｜
  final{subtype,status,run_id,manifest_digest}（subtype 键由 appv2 api 桥
  注入——appv2/api/bridge.py sse_frames）
- citation（v2 形）{index,source,source_id,trust}

三路测试：V1 八类归约逐字段不丢（含 citation 兜底门原样钉）／v2 帧全归约
（六类 step＋ask＋subtype 拆形＋text→答案按序拼接）／asks_url 形参化（V1 缺省
路径不变，/api/v2 后缀切 v2 端点族）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "eval" / "results" / "tools" / "ask.py"

_spec = importlib.util.spec_from_file_location("eval_ask", TOOL)
assert _spec is not None and _spec.loader is not None
ask = importlib.util.module_from_spec(_spec)
sys.modules["eval_ask"] = ask
_spec.loader.exec_module(ask)


# ---------- 帧构造助手（信封照 00 §6.1——id/event/data 三键，ask.py parse 形） ----------


def _f(fid: int, event: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"id": fid, "event": event, "data": data}


_C1 = {"ref": "[c1]", "kind": "报告", "label": "《R》", "locator": {"report": "R"}}


def _v1_frames() -> list[dict[str, Any]]:
    """V1 检索问答链帧族（八类全在——answer/citation/verdict/clarify/notice/
    token/node＋session/done 保留帧）。"""
    return [
        _f(0, "session", {"run_id": "run-v1", "resume": False}),
        _f(1, "node", {"key": "N1", "name": "安检", "label": "安检", "state": "finish"}),
        _f(2, "verdict", {"chain": "检索问答链", "slots": "指标＝日产油量", "confidence": "高"}),
        _f(3, "token", {"text": "去年"}),
        _f(4, "token", {"text": "日产油"}),
        _f(5, "citation", dict(_C1)),
        _f(6, "answer", {"kind": "text", "text": "答案正文", "citations": [dict(_C1)]}),
        _f(7, "notice", {"type": "note", "content": "注记"}),
        _f(8, "clarify", {"question": "缺时间窗", "options": ["去年", "本月"]}),
        _f(9, "done", {"run_id": "run-v1"}),
    ]


def _v2_frames() -> list[dict[str, Any]]:
    """v2 六步 loop 全流（数-明1 类问数题——发射形照 graph.py/bridge.py）。"""
    return [
        _f(0, "session", {"run_id": "run-v2-1", "resume": False}),
        _f(1, "step", {"step": "understand", "seq": 1, "title": "理解"}),
        _f(2, "text", {"content": "意图：问数——去年日产油量明细"}),
        _f(3, "step", {"step": "plan", "seq": 2, "title": "计划：data_query"}),
        _f(4, "step", {"step": "tool", "seq": 3, "title": "工具 data_query：ok"}),
        _f(5, "tool", {"tool": "data_query", "status": "ok", "seq": 3, "message": None}),
        _f(6, "step", {"step": "observe", "seq": 4, "title": "观察入栈 2 支"}),
        _f(7, "observation", {"index": 1, "source": "agg", "content": "Z-16 5839.6",
                              "trust": "台账"}),
        _f(8, "observation", {"index": 2, "source": "agg", "content": "X-25 5708.1",
                              "trust": "台账"}),
        _f(9, "step", {"step": "verify", "seq": 5, "title": "核验：支撑 2｜改写 0｜分源 否"}),
        _f(10, "verdict", {"subtype": "verify", "supported": 2, "rewritten": 0,
                           "split": False, "cited": [1, 2]}),
        _f(11, "step", {"step": "answer", "seq": 6, "title": "答案收口"}),
        _f(12, "citation", {"index": 1, "source": "agg", "source_id": "r1", "trust": "台账"}),
        _f(13, "citation", {"index": 2, "source": "agg", "source_id": "r2", "trust": "台账"}),
        _f(14, "text", {"content": "答案：去年日产油明细……\n\n引用：\n[1] agg · r1"}),
        _f(15, "verdict", {"subtype": "final", "status": "completed", "run_id": "run-v2-1",
                           "manifest_digest": "d" * 64}),
        _f(16, "done", {"run_id": "run-v2-1"}),
    ]


# ---------- V1 八类归约不丢（扩展字段不改动 V1 语义） ----------


class TestV1Unchanged:
    def test_eight_kinds_reduced_as_before(self) -> None:
        p = ask.parse_frames(_v1_frames())
        assert p["answer_text"] == "答案正文"  # answer 帧 text
        assert p["citations"] == [dict(_C1)]  # answer 帧内嵌为准
        assert p["chain"] == "检索问答链"  # verdict 帧 chain
        assert p["clarify"] == {"question": "缺时间窗", "options": ["去年", "本月"]}
        assert p["notices"] == [{"type": "note", "content": "注记"}]
        assert p["nodes"] == [{"key": "N1", "state": "finish", "skipped": False,
                               "label": "安检", "note": None}]
        assert p["run_id"] == "run-v1"  # session 帧（V1/v2 同形归约）

    def test_v1_verdict_not_misfiled_into_v2_subtype(self) -> None:
        p = ask.parse_frames(_v1_frames())
        assert p["verify"] == []  # V1 verdict 无 subtype 键——不进 v2 核验形
        assert p["final"] is None

    def test_citation_fallback_gate_untouched(self) -> None:
        """无 answer 帧时 V1 citation 帧兜底语义原样：只收首条（不因 v2 扩展改门）。"""
        frames = [f for f in _v1_frames() if f["event"] != "answer"]
        p = ask.parse_frames(frames)
        assert p["citations"] == [dict(_C1)]

    def test_extension_fields_neutral_for_v1(self) -> None:
        p = ask.parse_frames(_v1_frames())
        assert p["steps"] == []  # v2 step 帧族——V1 流零帧
        assert p["tools"] == []
        assert p["observations"] == []
        assert p["asks"] == []
        assert p["texts"] == []


# ---------- v2 帧全归约（六类 step＋ask＋subtype＋text/observation/tool/citation） ----------


class TestV2Reduction:
    def test_six_step_kinds_all_reduced_in_order(self) -> None:
        p = ask.parse_frames(_v2_frames())
        kinds = [s["step"] for s in p["steps"]]
        assert kinds == ["understand", "plan", "tool", "observe", "verify", "answer"]
        assert p["steps"][0] == {"step": "understand", "seq": 1, "title": "理解"}
        assert p["steps"][5]["title"] == "答案收口"

    def test_session_run_id_captured(self) -> None:
        p = ask.parse_frames(_v2_frames())
        assert p["run_id"] == "run-v2-1"

    def test_tool_and_observation_frames_reduced(self) -> None:
        p = ask.parse_frames(_v2_frames())
        assert p["tools"] == [{"tool": "data_query", "status": "ok", "seq": 3,
                               "message": None}]
        assert [o["index"] for o in p["observations"]] == [1, 2]
        assert p["observations"][0]["content"] == "Z-16 5839.6"

    def test_verdict_subtypes_split_verify_and_final(self) -> None:
        p = ask.parse_frames(_v2_frames())
        assert p["verify"] == [{"subtype": "verify", "supported": 2, "rewritten": 0,
                                "split": False, "cited": [1, 2]}]
        assert p["final"] == {"subtype": "final", "status": "completed",
                              "run_id": "run-v2-1", "manifest_digest": "d" * 64}
        assert p["chain"] is None  # v2 流无 V1 链路判定

    def test_v2_citations_all_reduced(self) -> None:
        """v2 citation 帧（index 形）逐条全归约——不走 V1 兜底门（只收首条）。"""
        p = ask.parse_frames(_v2_frames())
        assert p["citations"] == [
            {"index": 1, "source": "agg", "source_id": "r1", "trust": "台账"},
            {"index": 2, "source": "agg", "source_id": "r2", "trust": "台账"},
        ]

    def test_text_frames_concat_is_answer(self) -> None:
        """v2 理解/答案都走 text 帧——texts 全量留痕，答案兜底＝各帧按序拼接
        （V2-95 改口径：旧「流尾末条」只覆盖交付末段）。"""
        p = ask.parse_frames(_v2_frames())
        assert len(p["texts"]) == 2
        assert p["answer_text"] == "".join(p["texts"])
        assert p["answer_text"].endswith("答案：去年日产油明细……\n\n引用：\n[1] agg · r1")

    def test_ask_frame_reduced_as_is(self) -> None:
        ask_frame = _f(6, "ask", {"frame": {"kind": "clarify", "question": "哪个时间窗？",
                                            "options": ["去年", "本月"]},
                                  "run_id": "run-v2-1"})
        p = ask.parse_frames([*_v2_frames()[:6], ask_frame])
        assert p["asks"] == [{"frame": {"kind": "clarify", "question": "哪个时间窗？",
                                        "options": ["去年", "本月"]},
                              "run_id": "run-v2-1"}]

    def test_full_stream_via_sse_text(self) -> None:
        """parse_sse_text → parse_frames 全链（信封形照 00 §6.1，中文不转义）。"""
        raw = "".join(
            f"id: {f['id']}\nevent: {f['event']}\n"
            f"data: {json.dumps(f['data'], ensure_ascii=False)}\n\n"
            for f in _v2_frames()
        )
        frames = ask.parse_sse_text(raw)
        assert [f["event"] for f in frames] == [f["event"] for f in _v2_frames()]
        p = ask.parse_frames(frames)
        assert p["run_id"] == "run-v2-1"
        assert len(p["steps"]) == 6
        assert p["final"] is not None and p["final"]["status"] == "completed"
        assert "答案：" in p["answer_text"]  # 按序拼接（理解帧在前，答案帧在内）
        assert p["answer_text"] == "".join(p["texts"])


# ---------- asks_url 形参化（--base 单点——rerun.py 同消费） ----------


class TestAsksUrl:
    def test_v1_default_unchanged(self) -> None:
        assert ask.asks_url("http://localhost:8000") == "http://localhost:8000/api/chat/asks"
        assert (ask.asks_url("http://8.163.33.135")
                == "http://8.163.33.135/api/chat/asks")

    def test_v2_suffix_switches_endpoint(self) -> None:
        assert (ask.asks_url("http://localhost:8000/api/v2")
                == "http://localhost:8000/api/v2/chat/asks")

    def test_trailing_slash_tolerated(self) -> None:
        assert (ask.asks_url("http://localhost:8000/api/v2/")
                == "http://localhost:8000/api/v2/chat/asks")

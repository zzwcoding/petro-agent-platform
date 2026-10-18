"""rerun.py 真交付答案回填测试（V2-95——红先绿后）。

被测件＝`eval/results/tools/rerun.py` 内 V2-95 新增面（`runs_url` 单点／
`fetch_runs` 读口／`apply_delivered_answer` 口径／`answer_head` 取真交付前 120 字）
——跑批脚本本体照 rerun.py 惯例不进 tests/，`tests/tools/test_rerun_spend.py`
同款先例。

口径真源＝票面施工基准（逐字）：单题收口后查 `GET {base}/chat/runs?limit=50`，
按 `run_id` 取该行 `answer`；取不到退回「各 text 帧按序拼接」并标 `answer_source`
（`runs.answer`｜`texts.concat`）。兼容 V1 base（无 `/api/v2`）——V1 无 runs 读口，
查不到退回拼接、不报错、answer 帧原文不动。`answer_source` additive，`texts` 全量留痕不变。
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "eval" / "results" / "tools" / "rerun.py"

_spec = importlib.util.spec_from_file_location("eval_rerun_delivered", TOOL)
assert _spec is not None and _spec.loader is not None
rerun = importlib.util.module_from_spec(_spec)
sys.modules["eval_rerun_delivered"] = rerun
_spec.loader.exec_module(rerun)

V2_BASE = "http://localhost:8011/api/v2"
V1_BASE = "http://localhost:8000"
RUN_ID = "run-v2-95"

# 多段 text 帧（理解帧＋答案分块——真机形：EB9-D-诱12 帧同款）；末段≠真交付首段。
_TEXT_SEGMENTS = [
    "理解：问 W-22、W-24 两口杆断井的断点深度与教训差异。",
    "**W-22 井（断点 / 断口检查 / 根因）**\n"
    "- 断点深度：1980 米，第 38 根抽油杆杆体（非接头）位置断裂 [7]。\n",
    "**W-24 井**\n- 断点深度：1650 米 [42]。\n",
    "**两口井教训的不同**\n- W-22 属杆柱与井筒轨迹匹配问题；W-24 属工况变化后杆柱组合未同步重做。",
]
# 真交付答案（runs.answer 面——verify 删句后的交付正文，非流尾末段）。
DELIVERED = (
    "**W-22 井（断点 / 断口检查 / 根因）**\n"
    "- 断点深度：1980 米，第 38 根抽油杆杆体（非接头）位置断裂 [7]。\n"
    "- 断口检查：呈典型疲劳磨损特征；同位油管内壁可见深度 0.8～1.2 毫米的环状磨槽 [7]。\n"
    "**W-24 井**\n- 断点深度：1650 米 [42]。\n"
    "**区别要点**：W-22 是杆柱居中能力不足，W-24 是工况变化后杆柱组合未同步重做 [7][42]。"
)


def _frames(run_id: str = RUN_ID) -> list[dict]:
    frames: list[dict] = [
        {"event": "session", "data": {"run_id": run_id, "resume": False}},
        {"event": "step", "data": {"step": "understand", "seq": 1, "title": "理解"}},
    ]
    frames += [{"event": "text", "data": {"content": seg}} for seg in _TEXT_SEGMENTS]
    frames += [
        {"event": "verdict", "data": {"subtype": "final", "status": "completed",
                                      "run_id": run_id, "manifest_digest": "d" * 64}},
    ]
    return frames


def _parsed(run_id: str = RUN_ID) -> dict:
    return rerun.parse_frames(_frames(run_id))


def _concat() -> str:
    return "".join(_TEXT_SEGMENTS)


# ---------- ① runs.answer 优先（桩 list 返回 answer） ----------


def test_answer_from_runs_field() -> None:
    """list 返回该 run 的 answer → answer_text 等于该 answer、来源＝runs.answer。"""
    parsed = _parsed()
    rows = [{"run_id": "run-other", "answer": "别人的答案"},
            {"run_id": RUN_ID, "answer": DELIVERED}]
    rerun.apply_delivered_answer(parsed, rows)
    assert parsed["answer_text"] == DELIVERED
    assert parsed["answer_source"] == "runs.answer"
    assert parsed["texts"] == _TEXT_SEGMENTS  # texts 全量留痕不变


# ---------- ② 取不到 → 按序拼接并标来源 ----------


def test_answer_fallback_concat() -> None:
    """list 无该 run → 各 text 帧按序拼接、来源＝texts.concat；行在而 answer 空同退。"""
    parsed = _parsed()
    rerun.apply_delivered_answer(parsed, [{"run_id": "run-other", "answer": "别人的答案"}])
    assert parsed["answer_text"] == _concat()
    assert parsed["answer_source"] == "texts.concat"

    empty_list = _parsed()
    rerun.apply_delivered_answer(empty_list, [])
    assert empty_list["answer_text"] == _concat()
    assert empty_list["answer_source"] == "texts.concat"

    blank_answer = _parsed()
    rerun.apply_delivered_answer(blank_answer, [{"run_id": RUN_ID, "answer": "   "}])
    assert blank_answer["answer_text"] == _concat()
    assert blank_answer["answer_source"] == "texts.concat"


# ---------- ③ answer_head 取真交付前 120 字 ----------


def test_answer_head_from_delivered() -> None:
    """含多段 texts：head 取真交付首 120 字，不再取流尾末段（runs 面与拼接面同判）。"""
    parsed = _parsed()
    rerun.apply_delivered_answer(parsed, [{"run_id": RUN_ID, "answer": DELIVERED}])
    head = rerun.answer_head(parsed)
    assert head == DELIVERED[:120]
    assert head != _TEXT_SEGMENTS[-1][:120]  # 不再取流尾末条 text

    fallback = _parsed()
    rerun.apply_delivered_answer(fallback, [])
    assert rerun.answer_head(fallback) == _concat()[:120]
    assert rerun.answer_head({}) == ""  # 缺 answer_text 不炸


# ---------- 兼容 V1 base（无 /api/v2）：查不到退回拼接、不报错 ----------


def test_v1_base_has_no_runs_route_and_keeps_answer_frame() -> None:
    """V1 base 无 runs 读口（runs_url=None、零请求）——answer 帧原文不动（V1 缺省不变）。"""
    assert rerun.runs_url(V1_BASE) is None
    assert rerun.runs_url(V2_BASE) == f"{V2_BASE}/chat/runs?limit=50"
    assert rerun.runs_url(V2_BASE + "/") == f"{V2_BASE}/chat/runs?limit=50"

    def exploding_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("V1 base 不得发起 runs 读口请求")

    async def _fetch() -> list[dict]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(exploding_handler)
        ) as client:
            return await rerun.fetch_runs(client, V1_BASE)

    assert asyncio.run(_fetch()) == []

    frames = [
        {"event": "session", "data": {"run_id": "run-v1", "resume": False}},
        {"event": "answer", "data": {"kind": "text", "text": "答案正文", "citations": []}},
    ]
    parsed = rerun.parse_frames(frames)
    rerun.apply_delivered_answer(parsed, [])  # V1 查不到——退回拼接（空）不报错
    assert parsed["answer_text"] == "答案正文"  # answer 帧原文不动
    assert parsed.get("answer_source") is None  # 未产生来源标注

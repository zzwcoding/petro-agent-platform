"""suite-147 runner 评测口径定盘测试（V2-113——红先绿后）。

被测件＝`eval/suite-147/runner.py` 的 V2-113 新增面（README 冻结日断言／
`_run_detail` 取详情／`_verify_payload` 读 verify 步 payload／`_unsupported_claim_frames`
按帧计／`_rewrite_record` 删句原句档行）。跑批脚本本体照 eval 惯例不进 tests/ 直调
（先例 `tests/tools/test_rerun_delivered_answer.py`）。

口径真源＝票面施工基准：
1. **不改帧**：`rewrites` 原句只在 `GET {base}/chat/runs/{run_id}` 详情的 verify 步
   payload（SSE step 帧恰三键，`graph.py:190-206`）；runner 收口后取详情落档
   `results/<tag>-删句原句.jsonl`，结构对照抢回样本 `results/EB11-删句原句.jsonl`
   （键序 qid/run_id/supported/verify_mode/rewrites；rewrite 项恰 {line,reason}）。
2. **冻结日单一真源**：README §四 写明取值，runner 启动断言 env，不符即报错退出。
3. `unsupported_claim` 统计改按**帧**计（`unsupported_claim_frames` additive 键）。
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "eval" / "suite-147"
RUNNER = SUITE / "runner.py"
README = SUITE / "README.md"
SAMPLE = SUITE / "results" / "EB11-删句原句.jsonl"

_spec = importlib.util.spec_from_file_location("eval_suite_147_runner", RUNNER)
assert _spec is not None and _spec.loader is not None
runner = importlib.util.module_from_spec(_spec)
sys.modules["eval_suite_147_runner"] = runner
_spec.loader.exec_module(runner)

BASE = "http://eval.local/api/v2"
RUN_ID = "run-v113"
QID = "A-正1"

# 抢回样本行的键序（对照面：结构一致＝逐题可对）。
SAMPLE_KEYS = ["qid", "run_id", "supported", "verify_mode", "rewrites"]
REWRITE_KEYS = ["line", "reason"]


# ---------- 冻结日单一真源 ----------


def test_readme_pins_frozen_date_and_runner_mirrors_it() -> None:
    """README §四 是冻结日唯一真源；runner 常量＝README 里那一处取值（防两版并存）。"""
    import re

    text = README.read_text(encoding="utf-8")
    m = re.search(r"EVAL_FROZEN_DATE[=＝]\s*(\d{4}-\d{2}-\d{2})", text)
    assert m is not None, "README 未写明冻结日取值（EVAL_FROZEN_DATE=<ISO 日期>）"
    assert m.group(1) == runner.README_FROZEN_DATE, (
        f"runner.README_FROZEN_DATE={runner.README_FROZEN_DATE} 与 README 取值 {m.group(1)} 不一致"
    )
    assert runner.README_FROZEN_DATE == "2026-10-08", "EB11 主值（§A 执行日 10-08×210）为定盘值"


def test_frozen_date_assert_raises_on_missing_or_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """env 未设／空串／异值 → SystemExit（报错退出）；等于 README 值 → 通过。"""
    monkeypatch.delenv(runner.FROZEN_ENV, raising=False)
    with pytest.raises(SystemExit):
        runner.assert_frozen_date()

    monkeypatch.setenv(runner.FROZEN_ENV, "")
    with pytest.raises(SystemExit):
        runner.assert_frozen_date()

    monkeypatch.setenv(runner.FROZEN_ENV, "2026-08-31")  # 产品缺省水位日——不得混入
    with pytest.raises(SystemExit):
        runner.assert_frozen_date()

    monkeypatch.setenv(runner.FROZEN_ENV, runner.README_FROZEN_DATE)
    assert runner.assert_frozen_date() == runner.README_FROZEN_DATE


# ---------- verify 步 payload 读面 ----------


def test_verify_payload_from_run_detail() -> None:
    """取 verify 步 payload 五键（supported/rewritten/verify_mode/rewrites/intended_rewrites）。"""
    detail = {
        "status": "completed",
        "manifest_digest": "d",
        "steps": [
            {"seq": 10, "step": "answer", "payload": {"text": "草稿"}},
            {
                "seq": 11,
                "step": "verify",
                "payload": {
                    "phase": "verify",
                    "supported": 3,
                    "rewritten": 1,
                    "rewrites": [{"line": "- 编造句 [9]。", "reason": "no_material"}],
                    "gaps": [],
                },
            },
        ],
    }
    verify = runner._verify_payload(detail)
    assert verify["supported"] == 3
    assert verify["rewritten"] == 1
    assert verify["verify_mode"] is None  # V2-116 前口径＝null（payload 无该键）
    assert verify["rewrites"] == [{"line": "- 编造句 [9]。", "reason": "no_material"}]
    assert verify["intended_rewrites"] == []

    # 有 verify_mode 时如实透传（V2-116 后 additive 键）
    detail["steps"][1]["payload"]["verify_mode"] = "observe"
    assert runner._verify_payload(detail)["verify_mode"] == "observe"

    assert runner._verify_payload({}) == {}
    assert runner._verify_payload({"steps": []}) == {}


def test_unsupported_claim_counted_by_frame() -> None:
    """按帧计：两条 unsupported_claim notice 帧＝2（不再按题/按 run 计）。"""
    frames = [
        {"event": "notice", "data": {"type": "unsupported_claim", "gates": [], "content": "改 1"}},
        {"event": "notice", "data": {"type": "material_truncated", "gates": [], "content": "截断"}},
        {"event": "notice", "data": {"type": "unsupported_claim", "gates": [], "content": "改 2"}},
        {"event": "verdict", "data": {"subtype": "verify", "supported": 1, "rewritten": 2}},
        {"event": "step", "data": {"step": "verify", "seq": 11, "title": "核验"}},
    ]
    assert runner._unsupported_claim_frames(frames) == 2
    assert runner._unsupported_claim_frames([]) == 0


# ---------- 删句原句档（对照抢回样本结构） ----------


def test_rewrite_record_matches_recovered_sample_structure() -> None:
    """产出行键序＝抢回样本键序；rewrite 项恰 {line,reason}——逐题可对。"""
    assert SAMPLE.exists(), "抢回样本缺失（验收对照面）"
    first = json.loads(SAMPLE.read_text(encoding="utf-8").splitlines()[0])
    assert list(first.keys()) == SAMPLE_KEYS
    assert list(first["rewrites"][0].keys()) == REWRITE_KEYS

    rec = {
        "qid": QID,
        "run_id": RUN_ID,
        "verify": {
            "supported": 3,
            "rewritten": 1,
            "verify_mode": None,
            "rewrites": [{"line": "- 编造句 [9]。", "reason": "no_material"}],
            "intended_rewrites": [],
        },
    }
    row = runner._rewrite_record(rec)
    assert list(row.keys()) == SAMPLE_KEYS
    assert list(row["rewrites"][0].keys()) == REWRITE_KEYS
    assert row == {
        "qid": QID,
        "run_id": RUN_ID,
        "supported": 3,
        "verify_mode": None,
        "rewrites": [{"line": "- 编造句 [9]。", "reason": "no_material"}],
    }

    # 无详情（取证失败/异常行）不炸：rewrites 空、supported null
    empty = runner._rewrite_record({"qid": QID, "run_id": ""})
    assert list(empty.keys()) == SAMPLE_KEYS
    assert empty["supported"] is None and empty["rewrites"] == []


def test_rewrite_record_matches_sample_line_by_line() -> None:
    """逐题可对：抢回样本 147 行逐行回填 → `_rewrite_record` 输出与样本行逐字等值。"""
    rows = [json.loads(ln) for ln in SAMPLE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) == 147, f"抢回样本 {len(rows)} 行 ≠ 147"
    assert len({r["qid"] for r in rows}) == 147
    assert sum(len(r["rewrites"]) for r in rows) == 134, "删句总条数 ≠ 134"
    assert sum(1 for r in rows if r["rewrites"]) == 52, "有删句的题数 ≠ 52"
    for row in rows:
        rec = {
            "qid": row["qid"],
            "run_id": row["run_id"],
            "verify": {
                "supported": row["supported"],
                "verify_mode": row["verify_mode"],
                "rewrites": row["rewrites"],
            },
        }
        assert runner._rewrite_record(rec) == row, f"{row['qid']} 行与抢回样本不一致"


def test_main_writes_rewrite_jsonl_line_per_qid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main 收口逐题落删句原句档：一行一题、键序＝样本键序（含异常行也如实落）。"""
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"qid": q, "question": f"题干 {q}", "set": "97", "book": "册"})
            for q in ("A-正1", "A-正2")
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "MANIFEST", manifest)
    monkeypatch.setattr(runner, "RESULTS", tmp_path / "results")
    monkeypatch.setenv(runner.FROZEN_ENV, runner.README_FROZEN_DATE)

    async def fake_run_one(c, base, row, tag, **kwargs) -> dict:
        rewrites = (
            [{"line": "- 编造句 [9]。", "reason": "no_material"}] if row["qid"] == "A-正1" else []
        )
        return {
            "qid": row["qid"],
            "run_id": f"run-{row['qid']}",
            "status": "completed",
            "answer": "答",
            "answer_len": 1,
            "verify": {"supported": 1, "verify_mode": None, "rewrites": rewrites},
        }

    monkeypatch.setattr(runner, "run_one", fake_run_one)
    monkeypatch.setattr(sys, "argv", ["runner.py", "--tag", "UT113", "--sleep", "0"])
    assert asyncio.run(runner.main()) == 0

    rewrite_file = tmp_path / "results" / "UT113-删句原句.jsonl"
    lines = [json.loads(ln) for ln in rewrite_file.read_text(encoding="utf-8").splitlines()]
    assert [r["qid"] for r in lines] == ["A-正1", "A-正2"]
    for row in lines:
        assert list(row.keys()) == SAMPLE_KEYS
    assert lines[0]["rewrites"] == [{"line": "- 编造句 [9]。", "reason": "no_material"}]
    assert list(lines[0]["rewrites"][0].keys()) == REWRITE_KEYS
    assert lines[1]["rewrites"] == []


def test_main_aborts_without_matching_frozen_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """冻结日断言在 main 启动处：env 不符 → SystemExit（不进入跑批循环）。"""
    monkeypatch.setenv(runner.FROZEN_ENV, "2026-08-31")
    monkeypatch.setattr(sys, "argv", ["runner.py", "--tag", "UT113", "--dry-run"])
    with pytest.raises(SystemExit):
        asyncio.run(runner.main())


# ---------- 收口后取详情（不改帧） ----------


def _sse(frames: list[dict]) -> str:
    return "".join(
        f"event: {f['event']}\ndata: "
        f"{json.dumps(f['data'], ensure_ascii=False)}\n\n"
        for f in frames
    )


_SSE_FRAMES = [
    {"event": "session", "data": {"run_id": RUN_ID, "resume": False}},
    {"event": "step", "data": {"step": "verify", "seq": 11, "title": "核验：支撑 3｜改写 1"}},
    {"event": "notice", "data": {"type": "unsupported_claim", "gates": [], "content": "改写 1 行"}},
    {"event": "verdict", "data": {"subtype": "final", "status": "completed", "run_id": RUN_ID}},
    {"event": "done", "data": {"run_id": RUN_ID}},
]

_DETAIL = {
    "status": "completed",
    "manifest_digest": "d" * 8,
    "steps": [
        {"seq": 11, "step": "verify", "status": "ok", "title": "核验",
         "manifest": {}, "payload": {"supported": 3, "rewritten": 1, "verify_mode": None,
                                     "rewrites": [{"line": "- 编造句 [9]。",
                                                   "reason": "no_material"}]}},
    ],
}


def _mock_client(*, detail_ok: bool = True, seen: list[str] | None = None) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(f"{request.method} {request.url.path}")
        if request.method == "POST" and request.url.path.endswith("/chat/asks"):
            return httpx.Response(200, text=_sse(_SSE_FRAMES))
        if request.method == "GET" and request.url.path.endswith("/chat/runs"):
            rows = [{"run_id": RUN_ID, "answer": "交付答案", "status": "completed"}]
            return httpx.Response(200, json=rows)
        if request.method == "GET" and request.url.path.endswith(f"/chat/runs/{RUN_ID}"):
            if not detail_ok:
                return httpx.Response(404, json={"code": "chat_run_not_found", "message": "无"})
            return httpx.Response(200, json=_DETAIL)
        raise AssertionError(f"未预期请求：{request.method} {request.url}")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_run_one_persists_rewrites_run_detail_and_frozen_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """收口后 GET 详情：rec 增 verify/unsupported_claim_frames/frozen_date；帧档增 run_detail。"""
    monkeypatch.setattr(runner, "FRAMES", tmp_path / "frames")
    monkeypatch.setenv(runner.FROZEN_ENV, runner.README_FROZEN_DATE)
    seen: list[str] = []

    async def _go() -> dict:
        async with _mock_client(seen=seen) as c:
            return await runner.run_one(
                c, BASE, {"qid": QID, "question": "题干"}, "UT113", resume=False, timeout=10
            )

    rec = asyncio.run(_go())

    assert f"GET /api/v2/chat/runs/{RUN_ID}" in seen, "未取 run 详情（rewrites 原句只在详情）"
    assert rec["answer"] == "交付答案"
    assert rec["frozen_date"] == runner.README_FROZEN_DATE
    assert rec["unsupported_claim_frames"] == 1
    assert rec["verify"]["supported"] == 3
    assert rec["verify"]["rewrites"] == [{"line": "- 编造句 [9]。", "reason": "no_material"}]

    archived = json.loads((tmp_path / "frames" / f"UT113-{QID}.json").read_text(encoding="utf-8"))
    assert archived["run_detail"] == _DETAIL  # 详情落档（重启不失）

    row = runner._rewrite_record(rec)
    assert list(row.keys()) == SAMPLE_KEYS
    assert row["supported"] == 3
    assert row["rewrites"] == [{"line": "- 编造句 [9]。", "reason": "no_material"}]


def test_run_one_detail_failure_does_not_break_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """详情取证失败不炸批：verify 空、删句行仍如实落（空 rewrites）。"""
    monkeypatch.setattr(runner, "FRAMES", tmp_path / "frames")
    monkeypatch.setenv(runner.FROZEN_ENV, runner.README_FROZEN_DATE)

    async def _go() -> dict:
        async with _mock_client(detail_ok=False) as c:
            return await runner.run_one(
                c, BASE, {"qid": QID, "question": "题干"}, "UT113", resume=False, timeout=10
            )

    rec = asyncio.run(_go())
    assert rec["verify"] == {}
    assert runner._rewrite_record(rec)["rewrites"] == []
    assert rec["status"] == "completed"

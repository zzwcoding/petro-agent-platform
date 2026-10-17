"""rerun.py --resume 挂起续跑测试（F3/V2-41·P-039 附 5 行为定义——红先绿后）。

被测件＝eval/results/tools/rerun.py 内 resume 面（resume_url／is_suspended／
resume_suspended——跑批脚本本体照 rerun.py 惯例不进 tests/，
tests/tools/test_rerun_spend.py 同款先例）。

附 5 行为定义：rerun 遇 run 挂起（帧含 ask 且 done 前无终稿答案）→ --resume
模式对挂起帧 POST 题册登记的合法选项（缺省第一项）续跑至收口；非挂起帧不受
影响；判分照旧只看最终交付轮（合并帧重新归约——answer/verdict 取续跑后终稿）。
挂起帧两形（V2-82 批 EB6 修 3）：V1＝终稿 verdict 缺席；V2＝终判帧
（`subtype=final, status=waiting_ask`）在场（挂起腿照发）——`is_suspended` 两形兼容。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "eval" / "results" / "tools" / "rerun.py"

_spec = importlib.util.spec_from_file_location("eval_rerun", TOOL)
assert _spec is not None and _spec.loader is not None
rerun = importlib.util.module_from_spec(_spec)
sys.modules["eval_rerun"] = rerun
_spec.loader.exec_module(rerun)

V2_BASE = "http://localhost:8010/api/v2"


def _sse(frames: list[dict]) -> str:
    """帧列 → SSE 文本（id:/event:/data: 三行一组——wire 形镜像）。"""
    blocks = []
    for i, frame in enumerate(frames, start=1):
        data = json.dumps(frame["data"], ensure_ascii=False)
        blocks.append(f"id: {i}\nevent: {frame['event']}\ndata: {data}")
    return "\n\n".join(blocks) + "\n\n"


def _suspended_out_data(run_id: str = "run-ask-1") -> dict:
    """挂起形 out_data（ask 帧在场＋final 缺席——附 5 判定面；duration 在 parsed 内）。"""
    frames = [
        {"event": "session", "data": {"run_id": run_id, "resume": False}},
        {"event": "ask", "data": {
            "frame": {"kind": "clarify",
                      "prompt": "「最近」指哪个时间窗？",
                      "options": ["近 7 天", "近 30 天", "本月至今"],
                      "detail": None},
            "run_id": run_id}},
    ]
    parsed = rerun.parse_frames(frames)
    parsed["duration_s"] = 3.4  # ask_once 同位（ask 段真实耗时）
    return {"frames": frames, "parsed": parsed}


def _resume_frames(run_id: str, answer: str) -> list[dict]:
    return [
        {"event": "session", "data": {"run_id": run_id, "resume": True}},
        {"event": "text", "data": {"content": answer}},
        {"event": "verdict", "data": {"subtype": "final", "status": "completed",
                                      "run_id": run_id, "manifest_digest": "d" * 64}},
    ]


# ---------- resume_url／is_suspended（纯函数面） ----------


def test_resume_url_builds_v2_resume_endpoint() -> None:
    assert rerun.resume_url(V2_BASE, "run-1") == (
        "http://localhost:8010/api/v2/chat/runs/run-1/resume"
    )
    assert rerun.resume_url(V2_BASE + "/", "run-1").count("//chat") == 0


def test_is_suspended_ask_without_final_is_true() -> None:
    assert rerun.is_suspended(_suspended_out_data()["parsed"]) is True

    done = _suspended_out_data()
    done["frames"].extend(_resume_frames("run-ask-1", "答案"))
    done["parsed"] = rerun.parse_frames(done["frames"])
    assert rerun.is_suspended(done["parsed"]) is False  # 终稿在场＝已收口

    assert rerun.is_suspended({}) is False  # 无 ask 帧＝非挂起
    assert rerun.is_suspended({"asks": []}) is False


def _v2_suspended_out_data(run_id: str = "run-ask-v2") -> dict:
    """V2 真机挂起形（**终判帧在场**：`subtype=final, status=waiting_ask`）。

    帧形镜像真机存档 `eval/results/frames/EB6-B-正6.json`（id=4 verdict 帧）；挂起腿的
    `ask` 帧其后照发终判 verdict（`status=RUN_WAITING_ASK`）——旧判据（`final is None`）
    在此形下恒 False（V2-82 批 EB6 修 3 的病灶）。
    """
    frames = [
        {"event": "session", "data": {"run_id": run_id, "resume": False}},
        {"event": "ask", "data": {
            "frame": {"kind": "clarify",
                      "prompt": "这道题问的是「检泵周期」——系统里有多个油田的数据。"
                                "请确认要查哪一个：",
                      "options": ["渤中油田", "渤南油田", "渤西油田", "都要（分源对比）"],
                      "detail": {}},
            "run_id": run_id}},
        {"event": "verdict", "data": {"subtype": "final", "status": "waiting_ask",
                                      "run_id": run_id, "manifest_digest": "0" * 16}},
    ]
    parsed = rerun.parse_frames(frames)
    parsed["duration_s"] = 3.4
    return {"frames": frames, "parsed": parsed}


def test_is_suspended_v2_final_waiting_ask_frame_is_true() -> None:
    """V2 终判帧形＝挂起（V2-82 批 EB6 修 3）：`status=waiting_ask` 即挂起态本体。

    对照组＝续跑后的收口形（`status=completed`）仍判非挂起（判据方向不变）。
    """
    assert rerun.is_suspended(_v2_suspended_out_data()["parsed"]) is True

    done = _v2_suspended_out_data()
    done["frames"].extend(_resume_frames("run-ask-v2", "答案"))
    done["parsed"] = rerun.parse_frames(done["frames"])
    assert done["parsed"]["final"]["status"] == "completed"
    assert rerun.is_suspended(done["parsed"]) is False


def test_resume_fires_on_v2_waiting_ask_final_frame() -> None:
    """机制面（附 5）：V2 真机帧形下 `--resume` 真发起续跑（病灶＝此处零调用、run 零交付）。"""
    import asyncio

    out_data = _v2_suspended_out_data()
    calls: list[dict] = []
    resumes = asyncio.run(_drive_resume(
        V2_BASE, out_data, calls, _resume_frames("run-ask-v2", "按近 7 天出数。"),
    ))
    assert resumes == [{"run_id": "run-ask-v2", "choice": "渤中油田"}]
    assert len(calls) == 1  # 挂起即续跑（旧判据下此处恒 0 次）
    assert out_data["parsed"]["final"]["status"] == "completed"
    assert not rerun.is_suspended(out_data["parsed"])


# ---------- resume_suspended（附 5 行为定义主面——httpx MockTransport） ----------


def _transport_spy(calls: list[dict], resume_frames: list[dict]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({
            "method": request.method,
            "url": str(request.url),
            "body": json.loads(request.content.decode("utf-8")),
        })
        return httpx.Response(200, text=_sse(resume_frames))

    return httpx.MockTransport(handler)


async def _drive_resume(base: str, out_data: dict, calls: list[dict],
                        resume_frames: list[dict]) -> list[dict[str, str]]:
    transport = _transport_spy(calls, resume_frames)
    async with httpx.AsyncClient(transport=transport) as client:
        return await rerun.resume_suspended(client, base, out_data)


def test_resume_posts_first_option_and_merges_final_round() -> None:
    import asyncio

    out_data = _suspended_out_data()
    calls: list[dict] = []
    resumes = asyncio.run(_drive_resume(
        V2_BASE, out_data, calls, _resume_frames("run-ask-1", "按近 30 天出数。"),
    ))
    # 缺省选第一项（附 5——题册 expectedBehavior 指定项）；载荷按 ResumeBody
    # 合同携 kind=clarify（appv2/api/chat.py resume 入参形）。
    assert resumes == [{"run_id": "run-ask-1", "choice": "近 7 天"}]
    assert calls == [{
        "method": "POST",
        "url": "http://localhost:8010/api/v2/chat/runs/run-ask-1/resume",
        "body": {"kind": "clarify", "choice": "近 7 天"},
    }]
    # 续跑帧并入＋重新归约——判分只看最终交付轮（终稿答案/verdict 在场）。
    assert out_data["parsed"]["final"] is not None
    assert out_data["parsed"]["final"]["status"] == "completed"
    assert out_data["parsed"]["answer_text"] == "按近 30 天出数。"
    assert not rerun.is_suspended(out_data["parsed"])
    assert out_data["parsed"]["duration_s"] > 0  # 两段时长合并


def test_resume_skips_non_suspended_and_non_v2_base() -> None:
    import asyncio

    # 非挂起帧不受影响（附 5）——零 HTTP 调用（transport 未被触即通过）。
    done = _suspended_out_data()
    done["frames"].extend(_resume_frames("run-ask-1", "答案"))
    done["parsed"] = rerun.parse_frames(done["frames"])
    calls: list[dict] = []

    def exploding_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("非挂起帧不得发起续跑请求")

    async def _drive_non_suspended() -> list[dict[str, str]]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(exploding_handler)
        ) as client:
            return await rerun.resume_suspended(client, V2_BASE, done)

    assert asyncio.run(_drive_non_suspended()) == []

    # V1 base（非 /api/v2）无挂起帧形——--resume 不生效（零调用）。
    async def _drive_v1() -> list[dict[str, str]]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(exploding_handler)
        ) as client:
            return await rerun.resume_suspended(
                client, "http://localhost:8000", _suspended_out_data()
            )

    assert asyncio.run(_drive_v1()) == []
    assert not calls


def test_resume_stops_when_ask_frame_lacks_options() -> None:
    import asyncio

    out_data = _suspended_out_data()
    out_data["frames"][1]["data"]["frame"]["options"] = []  # 异常挂起帧（无选项）
    out_data["parsed"] = rerun.parse_frames(out_data["frames"])
    calls: list[dict] = []
    assert asyncio.run(_drive_resume(V2_BASE, out_data, calls, [])) == []
    assert not calls  # 无从续跑——原样留档不硬凑


def test_resume_reports_http_error_and_stops() -> None:
    import asyncio

    out_data = _suspended_out_data()

    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text='{"error": "run 不存在"}')

    async def _drive() -> list[dict[str, str]]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(failing_handler)) as c:
            return await rerun.resume_suspended(c, V2_BASE, out_data)

    assert asyncio.run(_drive()) == [{"run_id": "run-ask-1", "choice": "近 7 天"}]
    # 续跑失败不静默（stdout 留痕）——帧面保持挂起原样，判分侧如实见挂起。
    assert rerun.is_suspended(out_data["parsed"])


def test_resume_bound_at_three_rounds() -> None:
    """安全上限 3 次续跑（海啸保险——正常至多 1~2 次）。"""
    import asyncio

    out_data = _suspended_out_data()
    # 每次续跑仍回挂起帧——3 次后停（不无限环）。
    suspended_frames = _suspended_out_data("run-ask-1")["frames"]
    transport_calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        transport_calls.append({"url": str(request.url)})
        return httpx.Response(200, text=_sse(suspended_frames))

    async def _drive() -> list[dict[str, str]]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await rerun.resume_suspended(c, V2_BASE, out_data)

    resumes = asyncio.run(_drive())
    assert len(resumes) == 3
    assert len(transport_calls) == 3


def test_resume_approval_frame_maps_to_approve_with_id() -> None:
    """审批挂起帧（external_table_approval）→ ResumeBody approval 形（第一选项
    「批准」→approve；帧 detail.approval_id 随行）。"""
    import asyncio

    out_data = _suspended_out_data("run-ext-1")
    out_data["frames"][1]["data"]["frame"] = {
        "kind": "external_table_approval",
        "prompt": "计划引用外部表 erp_well_register——是否批准越集查询？",
        "options": ["批准", "驳回"],
        "detail": {"approval_id": "run-ext-1#APP-0910-erp_well_register"},
    }
    out_data["parsed"] = rerun.parse_frames(out_data["frames"])
    calls: list[dict] = []
    resumes = asyncio.run(_drive_resume(
        V2_BASE, out_data, calls,
        _resume_frames("run-ext-1", "外表引用审批已通过（单号留痕）。"),
    ))
    assert resumes == [{"run_id": "run-ext-1", "choice": "批准"}]
    assert calls[0]["body"] == {
        "kind": "approval",
        "decision": "approve",
        "approval_id": "run-ext-1#APP-0910-erp_well_register",
    }

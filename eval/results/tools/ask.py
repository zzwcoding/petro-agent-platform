#!/usr/bin/env python3
"""问一问 SSE 助手（评测专用，只读调用平台 API——不落库不改配置）。

用法：
    uv run python eval/results/tools/ask.py "问题文本"
    uv run python eval/results/tools/ask.py "问题文本" --user aqiang
    uv run python eval/results/tools/ask.py "问题文本" --base-url http://localhost:8000/api/v2

stdout 输出单个 JSON：
    {frames: [{id, event, data}...],
     parsed: {answer_text, citations: [...], chain, clarify, notices,
              nodes: [{key, state, skipped}],
              -- V2-12 v2 扩展（V1 字段零改动，超集归约）--
              run_id, steps: [{step, seq, title}], tools, observations,
              asks: [{frame, run_id}], verify: [...], final, texts: [...]}}

帧解析按 tests/api/test_chat_sse.py 的 wire 形（id:/event:/data: 三行一组，
空行收束）；V1 帧：answer 帧 {kind,text,citations}，citation 帧
{ref,kind,label,locator}，node 帧 {key,name,label,state[,skipped][,note]}，
verdict 帧取 chain。V2 帧（真源 appv2/api/wire.py——本脚本零 appv2 依赖，
键形镜像）：session{run_id,resume}、step{text,seq,title}（六类 understand/
plan/tool/observe/verify/answer）、text{content}、tool{tool,status,seq,
message}、observation{index,source,content,trust}、ask{frame,run_id}、
citation{index,source,source_id,trust}、verdict 拆 subtype 两形（verify 载
{supported,rewritten,split,cited}、final 载{status,run_id,manifest_digest}
——subtype 键由 appv2 api 桥注入）。

本脚本一次调用只发一次提问（计费纪律：重试与否由调用方决定，脚本自身不重试）。
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

BASE_URL = "http://localhost:8000"

# --base 形参化的 v2 端点族后缀（rerun.py --base 同消费；V1 缺省路径不变）
V2_API_SUFFIX = "/api/v2"

# verdict subtype 两形（appv2/api/wire.py VERDICT_VERIFY/VERDICT_FINAL 镜像）
VERDICT_VERIFY = "verify"
VERDICT_FINAL = "final"


def asks_url(base: str) -> str:
    """base → asks 端点 URL（--base 形参化单点，rerun.py 同消费）。

    base 以 /api/v2 结尾＝V2 端点族（POST /api/v2/chat/asks）；其余＝V1
    缺省（POST /api/chat/asks）——V1 默认行为不变（V2-12 验收①干跑对照）。
    """
    base = base.rstrip("/")
    if base.endswith(V2_API_SUFFIX):
        return f"{base}/chat/asks"
    return f"{base}/api/chat/asks"


def parse_sse_text(text: str) -> list[dict]:
    """SSE 文本 → [{id, event, data}]（id 缺省 null；data 按 JSON 解析，失败存原文）。"""
    frames: list[dict] = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        fid: str | None = None
        event: str | None = None
        raw_data: str | None = None
        for line in block.split("\n"):
            if line.startswith("id: "):
                fid = line.removeprefix("id: ").strip()
            elif line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                raw_data = line.removeprefix("data: ")
        if event is None and raw_data is None:
            continue
        try:
            data = json.loads(raw_data) if raw_data is not None else None
        except json.JSONDecodeError:
            data = {"_raw": raw_data}
        frames.append({"id": int(fid) if fid is not None and fid.isdigit() else fid,
                       "event": event, "data": data})
    return frames


def parse_frames(frames: list[dict]) -> dict:
    """帧列表 → 业务摘要（V1 八类归约不变＋v2 帧超集扩展——V2-12）。

    V1 归约（语义照旧）：answer_text/citations（answer 帧内嵌为准，无 answer
    时以 citation 帧兜底）/chain/clarify/notices/nodes，token 切片兜底拼接。
    v2 扩展（appv2/api/wire.py 事件形；V1 流这些字段全为空值——扩展不丢
    V1 八类）：session→run_id；step→steps（六类逐帧全量）；tool→tools；
    observation→observations；ask→asks（挂起帧 {frame,run_id} 原样）；
    verdict 按 subtype 拆形（verify→verify 列表，final→final 单数；V1
    verdict 无 subtype 键照走 chain——双形判别不串门）；text→texts（全量
    留痕，answer_text 兜底取流尾末条——v2 答案收口在流尾发射）；v2 citation
    （index 形）逐条全归约进 citations——与 V1 ref 形按键分流，V1 兜底门不动。
    """
    answer_text = ""
    citations: list[dict] = []
    chain = None
    clarify = None
    notices: list[dict] = []
    nodes: dict[str, dict] = {}
    tokens: list[str] = []
    # —— v2 扩展字段（V1 流恒空值）——
    run_id = None
    steps: list[dict] = []
    tools: list[dict] = []
    observations: list[dict] = []
    asks: list[dict] = []
    verifies: list[dict] = []
    final: dict | None = None
    texts: list[str] = []

    for f in frames:
        name, data = f.get("event"), f.get("data") or {}
        if name == "answer":
            answer_text = data.get("text", "")
            citations = data.get("citations", [])
        elif name == "citation":
            if "index" in data:  # v2 形（观察引用）——逐条全归约
                citations.append(data)
            elif not citations:  # V1 形——answer 帧内嵌为准；无 answer 时以 citation 帧兜底
                citations.append(data)
        elif name == "verdict":
            if "subtype" not in data and "chain" in data:  # V1 形（链路判定）
                chain = data.get("chain")
            elif data.get("subtype") == VERDICT_FINAL or (
                "subtype" not in data and "status" in data
            ):  # v2 终局形（桥注入 subtype；无 subtype 时按 wire 判别键 status 兜底）
                final = data
            else:  # v2 核验形（verify——supported/rewritten/split/cited）
                verifies.append(data)
        elif name == "clarify":
            clarify = data
        elif name == "notice":
            notices.append(data)
        elif name == "token":
            tokens.append(data.get("text", data.get("token", "")))
        elif name == "node":
            key = data.get("key")
            if key is not None:
                nodes[key] = {"key": key,
                              "state": data.get("state"),
                              "skipped": bool(data.get("skipped", False)),
                              "label": data.get("label"),
                              "note": data.get("note")}
        elif name == "session":  # v2 首帧（V1 session 帧同形携 run_id）
            run_id = data.get("run_id")
        elif name == "step":
            steps.append({"step": data.get("step"), "seq": data.get("seq"),
                          "title": data.get("title")})
        elif name == "tool":
            tools.append(dict(data))
        elif name == "observation":
            observations.append(dict(data))
        elif name == "ask":
            asks.append(dict(data))  # {frame, run_id} 原样——判分看 frame 载荷
        elif name == "text":
            texts.append(data.get("content", ""))

    if not answer_text and tokens:
        answer_text = "".join(tokens)
    if not answer_text and texts:
        answer_text = texts[-1]  # v2 答案收口＝流尾末条 text（answer_node 发射序）
    return {
        "answer_text": answer_text,
        "citations": citations,
        "chain": chain,
        "clarify": clarify,
        "notices": notices,
        "nodes": list(nodes.values()),
        # —— v2 扩展（V2-12）——
        "run_id": run_id,
        "steps": steps,
        "tools": tools,
        "observations": observations,
        "asks": asks,
        "verify": verifies,
        "final": final,
        "texts": texts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="问一问 SSE 提问助手")
    ap.add_argument("question", help="问题文本（按答案册题干原句）")
    ap.add_argument("--user", default="aqiang", help="X-Dev-User 身份（默认 aqiang）")
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--timeout", type=float, default=300.0, help="读超时秒数")
    args = ap.parse_args()

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=args.timeout,
                                                write=10.0, pool=10.0)) as client:
            with client.stream(
                "POST",
                asks_url(args.base_url),  # --base-url 形参化同 rerun.py（/api/v2 后缀切 v2 族）
                json={"question": args.question},
                headers={"X-Dev-User": args.user},
            ) as resp:
                if resp.status_code != 200:
                    body = resp.read().decode("utf-8", "replace")
                    print(json.dumps({
                        "frames": [],
                        "parsed": None,
                        "error": {"status": resp.status_code, "body": body[:2000]},
                    }, ensure_ascii=False))
                    return 1
                chunks: list[str] = []
                for chunk in resp.iter_text():
                    chunks.append(chunk)
                raw = "".join(chunks)
    except httpx.HTTPError as exc:
        print(json.dumps({"frames": [], "parsed": None,
                          "error": {"kind": type(exc).__name__, "message": str(exc)[:500]}},
                         ensure_ascii=False))
        return 1

    frames = parse_sse_text(raw)
    print(json.dumps({"frames": frames, "parsed": parse_frames(frames)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

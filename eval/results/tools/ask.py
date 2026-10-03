#!/usr/bin/env python3
"""问一问 SSE 助手（评测专用，只读调用平台 API——不落库不改配置）。

用法：
    uv run python eval/results/tools/ask.py "问题文本"
    uv run python eval/results/tools/ask.py "问题文本" --user aqiang

stdout 输出单个 JSON：
    {frames: [{id, event, data}...],
     parsed: {answer_text, citations: [{ref, kind, label, locator}],
              chain, clarify, notices, nodes: [{key, state, skipped}]}}

帧解析按 tests/api/test_chat_sse.py 的 wire 形（id:/event:/data: 三行一组，
空行收束）；answer 帧 {kind,text,citations}，citation 帧 {ref,kind,label,locator}，
node 帧 {key,name,label,state[,skipped][,note]}，verdict 帧取 chain。

本脚本一次调用只发一次提问（计费纪律：重试与否由调用方决定，脚本自身不重试）。
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

BASE_URL = "http://localhost:8000"


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
    """帧列表 → 业务摘要（answer_text/citations/chain/clarify/notices/nodes）。"""
    answer_text = ""
    citations: list[dict] = []
    chain = None
    clarify = None
    notices: list[dict] = []
    nodes: dict[str, dict] = {}
    tokens: list[str] = []

    for f in frames:
        name, data = f.get("event"), f.get("data") or {}
        if name == "answer":
            answer_text = data.get("text", "")
            citations = data.get("citations", [])
        elif name == "citation":
            if not citations:  # answer 帧内嵌为准；无 answer 时以 citation 帧兜底
                citations.append(data)
        elif name == "verdict":
            chain = data.get("chain")
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

    if not answer_text and tokens:
        answer_text = "".join(tokens)
    return {
        "answer_text": answer_text,
        "citations": citations,
        "chain": chain,
        "clarify": clarify,
        "notices": notices,
        "nodes": list(nodes.values()),
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
                f"{args.base_url}/api/chat/asks",
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

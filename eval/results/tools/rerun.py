#!/usr/bin/env python3
"""L-04 轻量跑批脚本（首版）——批量按题册原句提问、SSE 帧全量存档、产出判分辅助表。

用法：
    uv run python eval/results/tools/rerun.py --suite 问数组 --tag Q3W
    uv run python eval/results/tools/rerun.py --suite 问答组 --tag Q3Q

纪律（沿用 eval/README）：题干原句不改写；每题只问一遍、脚本自身零重试；
SSE 帧全量存档 eval/results/frames/{tag}-{qid}.json；判分由人对照答案册做，
本脚本只产出「判分辅助表」（chain/答案摘录/citations/节点摘要并排）。
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))

from ask import parse_frames, parse_sse_text  # noqa: E402

BASE = "http://localhost:8000"
HEADERS = {"X-Dev-User": "aqiang"}
FRAMES_DIR = Path(__file__).parent.parent / "frames"


async def ask_once(c: httpx.AsyncClient, question: str) -> dict:
    t0 = time.monotonic()
    async with c.stream(
        "POST", f"{BASE}/api/chat/asks", json={"question": question}, headers=HEADERS
    ) as resp:
        if resp.status_code != 200:
            body = (await resp.aread()).decode("utf-8", "replace")
            return {"error": {"status": resp.status_code, "body": body[:400]}}
        chunks = []
        async for piece in resp.aiter_text():
            chunks.append(piece)
    raw = "".join(chunks)
    frames = parse_sse_text(raw)
    parsed = parse_frames(frames)
    parsed["duration_s"] = round(time.monotonic() - t0, 1)
    return {"frames": frames, "parsed": parsed}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", default="suites_q3", help="题单模块名（suites_q3 / suites_q6）")
    ap.add_argument("--suite", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--sleep", type=float, default=2.0, help="题间间隔秒")
    args, _ = ap.parse_known_args()
    suites = importlib.import_module(args.module).SUITES
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", default=args.module)
    ap.add_argument("--suite", choices=sorted(suites), required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--sleep", type=float, default=2.0)
    args = ap.parse_args()
    suite = suites[args.suite]
    FRAMES_DIR.mkdir(exist_ok=True)
    out_path = FRAMES_DIR.parent / f"{args.tag}-跑批结果.jsonl"

    done = 0
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=300, write=10, pool=10)) as c:
        with out_path.open("a", encoding="utf-8") as out:
            for qid, group, question in suite:
                frame_path = FRAMES_DIR / f"{args.tag}-{qid}.json"
                row = {"qid": qid, "group": group, "question": question}
                try:
                    out_data = await ask_once(c, question)
                except Exception as exc:  # noqa: BLE001 —— 单题失败不断跑批
                    row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                    print(f"[{done + 1}/{len(suite)}] {qid} ❌ 异常 {row['error'][:80]}")
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    out.flush()
                    done += 1
                    continue
                frame_path.write_text(
                    json.dumps(out_data, ensure_ascii=False, indent=1), encoding="utf-8"
                )
                p = out_data.get("parsed") or {}
                row.update({
                    "chain": p.get("chain"),
                    "answer_head": (p.get("answer_text") or "")[:120],
                    "citations": len(p.get("citations") or []),
                    "duration_s": p.get("duration_s"),
                    "frame_file": frame_path.name,
                    "error": out_data.get("error"),
                })
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                done += 1
                dur = p.get("duration_s") or "?"
                print(f"[{done}/{len(suite)}] {qid} ✓ {dur}s chain={row['chain']}")
                await asyncio.sleep(args.sleep)
    print(f"完成 {done} 题 → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

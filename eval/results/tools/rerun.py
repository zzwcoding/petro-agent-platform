#!/usr/bin/env python3
"""L-04 轻量跑批脚本——批量按题册原句提问、SSE 帧全量存档、产出判分辅助表。

用法：
    uv run python eval/results/tools/rerun.py --suite 问数组 --tag Q3W
    uv run python eval/results/tools/rerun.py --suite 问答组 --tag Q3Q
    uv run python eval/results/tools/rerun.py --suite 问数组 --tag V2W \\
        --base http://localhost:8000/api/v2 --qid 数-明1   # V2 端点（V2-12）

纪律（沿用 eval/README）：题干原句不改写；每题只问一遍、脚本自身零重试；
SSE 帧全量存档 eval/results/frames/{tag}-{qid}.json；判分由人对照答案册做，
本脚本只产出「判分辅助表」（chain/答案摘录/citations/节点摘要并排）。

--base 形参化（V2-12）：缺省 http://localhost:8000（RERUN_BASE 环境量可覆写，
云测评同款）＝V1 缺省行为不变（POST /api/chat/asks）；base 以 /api/v2 结尾
＝V2 端点族（POST /api/v2/chat/asks），解析器按帧形自适应归约（ask.py
parse_frames 超集——六类 step/ask 帧/verdict subtype），判分辅助表 v2 行增
steps 列（六步链序，chain 在 v2 流恒空）。--qid 只跑指定题（干跑冒烟用，
题干原句照题册不改写）。
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))

from ask import asks_url, parse_frames, parse_sse_text

HEADERS = {"X-Dev-User": "aqiang"}
FRAMES_DIR = Path(__file__).parent.parent / "frames"


async def ask_once(c: httpx.AsyncClient, base: str, question: str) -> dict:
    t0 = time.monotonic()
    async with c.stream(
        "POST", asks_url(base), json={"question": question}, headers=HEADERS
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
    ap.add_argument("--base", default=os.environ.get("RERUN_BASE", "http://localhost:8000"),
                    help="平台 base（V1 缺省 http://localhost:8000；V2 传 …/api/v2）")
    ap.add_argument("--qid", default=None, help="只跑指定 qid（干跑冒烟用）")
    args = ap.parse_args()
    suite = suites[args.suite]
    FRAMES_DIR.mkdir(exist_ok=True)
    out_path = FRAMES_DIR.parent / f"{args.tag}-跑批结果.jsonl"

    targets = [e for e in suite if args.qid is None or e[0] == args.qid]
    done = 0
    timeout = httpx.Timeout(connect=10, read=300, write=10, pool=10)
    async with httpx.AsyncClient(timeout=timeout) as c:
        with out_path.open("a", encoding="utf-8") as out:
            for qid, group, question in targets:
                frame_path = FRAMES_DIR / f"{args.tag}-{qid}.json"
                row = {"qid": qid, "group": group, "question": question}
                try:
                    out_data = await ask_once(c, args.base, question)
                except Exception as exc:  # 单题失败不断跑批
                    row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                    print(f"[{done + 1}/{len(targets)}] {qid} ❌ 异常 {row['error'][:80]}")
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
                steps = p.get("steps") or []
                if steps:  # v2 行增六步链序列（V1 行零此键——判分辅助表 V1 照旧）
                    row["steps"] = "→".join(str(s.get("step")) for s in steps)
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                done += 1
                dur = p.get("duration_s") or "?"
                label = row["chain"] or row.get("steps") or "?"
                print(f"[{done}/{len(targets)}] {qid} ✓ {dur}s chain={label}")
                await asyncio.sleep(args.sleep)
    print(f"完成 {done} 题 → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

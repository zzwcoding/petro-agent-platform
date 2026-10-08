#!/usr/bin/env python3
"""L-03b 影子定向补测跑批脚本（题集 shadow-extra-traffic-L03b.json → 真接口）。

用法：
    RERUN_BASE=http://localhost:8000 uv run python eval/results/tools/shadow_extra_run.py \
        --tag L03B --sleep 2            # 全量（--skip-qid 跳过冒烟已跑题）
    uv run python eval/results/tools/shadow_extra_run.py --list   # 只列题集

纪律（照 plan_rerun.py／rerun.py 惯例）：题干原句不改写；每题只问一遍、脚本自身
零重试；SSE 帧全量存档 eval/results/frames/{tag}-{qid}.txt；题间间隔 --sleep。
影子行落 logs/shadow-plan.jsonl（L-02 影子接线默认路径，服务端写）。
本脚本只跑题不判分——意图命中率判分在 shadow_report_addendum.py（离线聚合）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

BASE = os.environ.get("RERUN_BASE", "http://localhost:8000")
HEADERS = {"X-Dev-User": "aqiang"}
TRAFFIC = Path(__file__).parent.parent / "golden" / "shadow-extra-traffic-L03b.json"
FRAMES_DIR = Path(__file__).parent.parent / "frames"


def load_traffic(path: str | Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    questions = raw.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("题集缺 questions 非空数组")
    qids: set[str] = set()
    for q in questions:
        for key in ("qid", "family", "question", "author_intent", "design_note"):
            if not q.get(key):
                raise ValueError(f"{q.get('qid', '?')} 缺必填字段 {key}")
        if q["qid"] in qids:
            raise ValueError(f"qid 重复：{q['qid']}")
        qids.add(q["qid"])
        intent = q["author_intent"]
        if intent.get("metric_slot") not in ("日产油量", "日产液量", "油压"):
            raise ValueError(f"{q['qid']} metric_slot 不在三绑定指标")
        if intent.get("window_rule") not in (
            "默认窗", "本月", "上月", "去年", "模糊最近", "模糊近期",
        ):
            raise ValueError(f"{q['qid']} window_rule 非法：{intent.get('window_rule')}")
        if q.get("expected_trigger") not in (True, False):
            raise ValueError(f"{q['qid']} expected_trigger 须布尔")
    return questions


async def ask_once(c: httpx.AsyncClient, question: str) -> dict[str, Any]:
    t0 = time.monotonic()
    async with c.stream(
        "POST", f"{BASE}/api/chat/asks", json={"question": question}, headers=HEADERS
    ) as resp:
        if resp.status_code != 200:
            body = (await resp.aread()).decode("utf-8", "replace")
            return {"error": {"status": resp.status_code, "body": body[:400]}}
        chunks: list[str] = []
        async for piece in resp.aiter_text():
            chunks.append(piece)
    raw = "".join(chunks)
    chain = ""
    for line in raw.splitlines():
        if '"chain": "' in line:
            chain = line.split('"chain": "')[1].split('"')[0]
            break
    return {"frames_text": raw, "chain": chain,
            "duration_s": round(time.monotonic() - t0, 1)}


async def run_batch(args: argparse.Namespace) -> int:
    questions = load_traffic(args.traffic)
    if args.skip_qid:
        skip = set(args.skip_qid.split(","))
        questions = [q for q in questions if q["qid"] not in skip]
    print(f"traffic={args.traffic}（本批 {len(questions)} 题 · BASE={BASE}）")
    print(f"帧存档→{FRAMES_DIR}/{args.tag}-*.txt；影子行→服务端 logs/shadow-plan.jsonl")
    done = 0
    timeout = httpx.Timeout(connect=10, read=300, write=10, pool=10)
    async with httpx.AsyncClient(timeout=timeout) as c:
        for q in questions:
            qid = str(q["qid"])
            try:
                data = await ask_once(c, q["question"])
            except Exception as exc:  # 单题失败不断跑批（rerun.py 同款）
                reason = f"{type(exc).__name__}: {str(exc)[:120]}"
                print(f"[{done + 1}/{len(questions)}] {qid} ⚠ 请求失败 {reason}")
                done += 1
                await asyncio.sleep(args.sleep)
                continue
            frame_path = FRAMES_DIR / f"{args.tag}-{qid}.txt"
            frame_path.write_text(data["frames_text"], encoding="utf-8")
            done += 1
            chain = data["chain"] or "未知"
            mark = "影子?" if chain == "状态机六站链" else "检索链"
            print(f"[{done}/{len(questions)}] {qid} {mark} chain={chain} {data['duration_s']}s")
            await asyncio.sleep(args.sleep)
    print(f"\n完成 {done} 题（chain=状态机六站链 的题才可能有影子行）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="L-03b 影子定向补测跑批（读题集逐问真接口）")
    ap.add_argument("--traffic", default=str(TRAFFIC))
    ap.add_argument("--tag", default="L03B", help="帧存档前缀")
    ap.add_argument("--sleep", type=float, default=2.0, help="题间间隔秒")
    ap.add_argument("--skip-qid", default="",
                    help="逗号分隔 qid 跳过（冒烟已跑题——每题一遍纪律）")
    ap.add_argument("--list", action="store_true", help="只列题集不跑")
    args = ap.parse_args()
    questions = load_traffic(args.traffic)
    if args.list:
        for q in questions:
            intent = q["author_intent"]
            print(f"{q['qid']} [{q['family']}] 触发预期={q['expected_trigger']} "
                  f"指标={intent['metric_slot']} 窗={intent['window_rule']} "
                  f"limit={intent['limit_requested']} | {q['question']}")
        return 0
    return asyncio.run(run_batch(args))


if __name__ == "__main__":
    sys.exit(main())

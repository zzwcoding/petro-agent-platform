#!/usr/bin/env python3
"""eval/suite-147 运行器 —— 147 题全量跑批（逐题真机 + 交付面取证）。

用法：
    python3 eval/suite-147/runner.py --tag EB11                 # 全量 147
    python3 eval/suite-147/runner.py --tag SMOKE --qid A-正1    # 单题
    python3 eval/suite-147/runner.py --tag EB11 --base http://127.0.0.1:8011/api/v2

纪律（沿用 eval 既有）：题干原句不改写；每题只问一遍、脚本零重试；
遇 ask 挂起默认自动续跑（选 options[0]，可 --no-resume 关闭）；
**判分唯一答案面＝GET /runs 的 answer（交付面）**，帧全量存档备审计。

产物：
    eval/suite-147/results/<tag>-跑批结果.jsonl   （一行一题：qid/run_id/status/answer/…）
    eval/suite-147/results/frames/<tag>-<qid>.json（逐题帧全量）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.jsonl"
RESULTS = HERE / "results"
FRAMES = RESULTS / "frames"
HEADERS = {"X-Dev-User": "laowang"}
MAX_RESUMES = 3


def _load_manifest(only: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if only and row.get("qid") != only:
            continue
        rows.append(row)
    return rows


def _parse_sse(text: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    event = None
    for line in text.splitlines():
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: "):
            try:
                data = json.loads(line[6:])
            except ValueError:
                continue
            frames.append({"event": event, "data": data})
            event = None
    return frames


def _run_id(frames: list[dict[str, Any]]) -> str:
    for f in frames:
        if f["event"] == "session":
            return str((f["data"] or {}).get("run_id") or "")
    return ""


def _first_ask(frames: list[dict[str, Any]]) -> dict[str, Any] | None:
    for f in frames:
        if f["event"] == "ask":
            return f["data"] or {}
    return None


def _steps(frames: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for f in frames:
        if f["event"] == "step":
            out.append(str((f["data"] or {}).get("step") or ""))
    return out


async def _ask_once(c: httpx.AsyncClient, base: str, body: dict[str, Any], timeout: int) -> str:
    r = await c.post(f"{base}/chat/asks", json=body, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


async def _resume(c: httpx.AsyncClient, base: str, run_id: str, choice: str, timeout: int) -> str:
    r = await c.post(
        f"{base}/chat/runs/{run_id}/resume",
        json={"kind": "clarify", "choice": choice},
        headers=HEADERS,
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text


async def _delivered_answer(c: httpx.AsyncClient, base: str, run_id: str) -> str:
    try:
        r = await c.get(f"{base}/chat/runs", params={"limit": 100}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        for row in r.json():
            if row.get("run_id") == run_id:
                return str(row.get("answer") or "")
    except Exception:  # noqa: BLE001 —— 取证失败不炸批（answer 落空串）
        return ""
    return ""


async def run_one(
    c: httpx.AsyncClient, base: str, row: dict[str, Any], tag: str, *, resume: bool, timeout: int
) -> dict[str, Any]:
    qid = row["qid"]
    started = time.monotonic()
    frames = _parse_sse(await _ask_once(c, base, {"question": row["question"]}, timeout))
    resumes: list[dict[str, str]] = []
    if resume:
        for _ in range(MAX_RESUMES):
            ask = _first_ask(frames)
            options = list((ask or {}).get("options") or [])
            if not ask or not options:
                break
            choice = options[0]
            rid = _run_id(frames)
            extra = _parse_sse(await _resume(c, base, rid, choice, timeout))
            resumes.append({"run_id": rid, "choice": choice})
            frames = frames + extra
            if not _first_ask(extra):
                break
    rid = _run_id(frames)
    answer = await _delivered_answer(c, base, rid)
    duration = round(time.monotonic() - started, 1)
    FRAMES.mkdir(parents=True, exist_ok=True)
    (FRAMES / f"{tag}-{qid}.json").write_text(
        json.dumps({"qid": qid, "run_id": rid, "frames": frames}, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "qid": qid,
        "set": row.get("set"),
        "book": row.get("book"),
        "run_id": rid,
        "status": "completed" if answer.strip() else "empty",
        "answer": answer,
        "answer_len": len(answer),
        "resumes": resumes,
        "steps": _steps(frames),
        "duration_s": duration,
        "asked": bool(_first_ask(frames)),
    }


async def main() -> int:
    ap = argparse.ArgumentParser(description="suite-147 全量跑批")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--base", default="http://127.0.0.1:8011/api/v2")
    ap.add_argument("--qid", default=None, help="只跑指定 qid")
    ap.add_argument("--sleep", type=float, default=2.0)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="只打印题号不跑")
    args = ap.parse_args()

    rows = _load_manifest(args.qid)
    if not rows:
        print(f"[suite-147] manifest 无匹配题（{MANIFEST}）")
        return 2
    print(f"[suite-147] tag={args.tag} 题数={len(rows)} base={args.base}")
    if args.dry_run:
        for r in rows:
            print(r["qid"], r.get("question", "")[:60])
        return 0

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS / f"{args.tag}-跑批结果.jsonl"
    async with httpx.AsyncClient() as c:
        with out_path.open("w", encoding="utf-8") as out:
            for i, row in enumerate(rows, 1):
                try:
                    rec = await run_one(
                        c, args.base, row, args.tag, resume=not args.no_resume, timeout=args.timeout
                    )
                except Exception as exc:  # noqa: BLE001 —— 单题异常如实落行，不炸批
                    rec = {
                        "qid": row["qid"],
                        "set": row.get("set"),
                        "book": row.get("book"),
                        "run_id": "",
                        "status": "error",
                        "answer": "",
                        "answer_len": 0,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                print(f"[{i}/{len(rows)}] {rec['qid']} {rec['status']} len={rec['answer_len']}")
                if i < len(rows):
                    await asyncio.sleep(args.sleep)
    print(f"[suite-147] 完成 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

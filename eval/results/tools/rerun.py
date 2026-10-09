#!/usr/bin/env python3
"""L-04 轻量跑批脚本——批量按题册原句提问、SSE 帧全量存档、产出判分辅助表。

用法：
    uv run python eval/results/tools/rerun.py --suite 问数组 --tag Q3W
    uv run python eval/results/tools/rerun.py --suite 问答组 --tag Q3Q
    uv run python eval/results/tools/rerun.py --suite 问数组 --tag V2W \\
        --base http://localhost:8000/api/v2 --qid 数-明1   # V2 端点（V2-12）
    uv run python eval/results/tools/rerun.py --suite 问数组 --tag P025DRY \\
        --base http://localhost:8001/api/v2 --spend --qid 数-明1  # ＋计费归集（V2-30）

纪律（沿用 eval/README）：题干原句不改写；每题只问一遍、脚本自身零重试；
SSE 帧全量存档 eval/results/frames/{tag}-{qid}.json；判分由人对照答案册做，
本脚本只产出「判分辅助表」（chain/答案摘录/citations/节点摘要并排）。

--base 形参化（V2-12）：缺省 http://localhost:8000（RERUN_BASE 环境量可覆写，
云测评同款）＝V1 缺省行为不变（POST /api/chat/asks）；base 以 /api/v2 结尾
＝V2 端点族（POST /api/v2/chat/asks），解析器按帧形自适应归约（ask.py
parse_frames 超集——六类 step/ask 帧/verdict subtype），判分辅助表 v2 行增
steps 列（六步链序，chain 在 v2 流恒空）。--qid 只跑指定题（干跑冒烟用，
题干原句照题册不改写）。

--spend 计费归集（V2-30，Q12 对账挂账 5 清偿）：跑批后逐题从网关 spend 账本
（PG gateway_spend_record——D5 全平台唯一账本，只读 SELECT）归集计费。
归集主路（V2-33 run_id 直查）：服务侧 _settle 已盖章（GraphRunExecutor 经
completer 协议携 run_id → 记账落 run_id 列），session 帧 run_id 即归集键——
逐题 run_id 等值直查（ix_gateway_spend_run），jsonl 行 run_id 与账本逐笔
ledger_run_ids 全等即对账成立。时间窗法退役为兜底（fallback 注记不静默）：
jsonl 行缺 run_id（V1 base/帧解析失败）→题级时间窗〔ask_started_at,
ask_ended_at〕＋caller 前缀（v2 base 缺省 v2.runtime.，--caller-prefix 可
覆写；本机墙钟与账本 time 列同钟同形：东八区 naive）；run_id 直查零行
（账本行未盖章的旧窗）→同样退窗并在 spend.fallback 注记原因。归集落点：
jsonl 行增 spend 字段（calls/fallback_calls/input_tokens/output_tokens/
cost_yuan/by_caller/call_ids/ledger_run_ids/method/fallback?）＋独立摘要件
{tag}-计费摘要.json（批次合计＋逐题清单——items 带 method 列）。
归集失败不中断跑批（行内 spend.error 留痕）。连接参数：PG_HOST/PG_PORT/
PG_DB/PG_USER/PG_PASSWORD 环境量＞仓根 .env＞config/database.yaml 开发默认
（localhost:5433/petro/petro/petro）；--spend-dsn 传整串 postgres:// DSN
时直连。--out-dir 重定位产物根目录（缺省 eval/results；frames 落
out-dir/frames——干跑产物隔离用）。
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
import time
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import asyncpg
import httpx

sys.path.insert(0, str(Path(__file__).parent))

from ask import asks_url, parse_frames, parse_sse_text

HEADERS = {"X-Dev-User": "aqiang"}
FRAMES_DIR = Path(__file__).parent.parent / "frames"

# ---------- 计费归集（--spend；V2-30，V2-33 归集主路改 run_id 直查）----------

_EAST8 = ZoneInfo("Asia/Shanghai")
DOTENV_PATH = Path(__file__).resolve().parents[3] / ".env"

# 主路：run_id 等值直查（V2-33——服务侧 _settle 已盖章，run_id 列逐笔有值；
# 走 ix_gateway_spend_run 索引；时序稳定便于逐笔对账）。
SPEND_SQL_BY_RUN = (
    "SELECT id, time, caller, alias, model_key, input_tokens, output_tokens,"
    " cost_yuan, fallback, run_id FROM gateway_spend_record"
    " WHERE run_id = $1 ORDER BY time, id"
)

# 兜底：题级时间窗（V2-30 原法——jsonl 行缺 run_id 或直查零行时退此；
# 窗口含边界；caller 前缀参数化）。
SPEND_SQL = (
    "SELECT id, time, caller, alias, model_key, input_tokens, output_tokens,"
    " cost_yuan, fallback, run_id FROM gateway_spend_record"
    " WHERE time >= $1 AND time <= $2 AND caller LIKE $3 ORDER BY time, id"
)

# PG 连接缺省＝config/database.yaml 开发默认（环境量/.env 可逐键覆写）
_PG_DEFAULTS: dict[str, str] = {
    "PG_HOST": "localhost",
    "PG_PORT": "5433",
    "PG_DB": "petro",
    "PG_USER": "petro",
    "PG_PASSWORD": "petro",
}


def now_ts() -> datetime:
    """墙钟——东八区本地 naive（与网关账本 time 列同钟同形：appv2/infra/clock 语义镜像）。"""
    return datetime.now(tz=_EAST8).replace(tzinfo=None)


def fmt_ts(at: datetime) -> str:
    """时间 → ISO 串（微秒保留——窗口边界对账用，精度高于 B14 展示秒级）。"""
    return at.isoformat(sep="T", timespec="microseconds")


def parse_ts(text: str) -> datetime:
    """ISO 串 → naive datetime（fmt_ts 逆变换）。"""
    return datetime.fromisoformat(text)


def expand_window(t0: datetime, t1: datetime, margin_s: float) -> tuple[datetime, datetime]:
    """题时间窗两侧外扩 margin 秒（防钟差/边界含入；同机部署缺省 0 即恒等）。"""
    delta = timedelta(seconds=margin_s)
    return t0 - delta, t1 + delta


def load_pg_env(path: Path) -> dict[str, str]:
    """仓根 .env 平铺解析（只收 PG_ 前缀键；注释/空行/无等号行跳过）。"""
    if not path.is_file():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("PG_"):
            env[key] = value.strip()
    return env


def pg_connect_kwargs(*, environ: Mapping[str, str], dotenv: Mapping[str, str]) -> dict[str, Any]:
    """PG 连接参数装配：环境量＞.env＞开发默认（优先级单向，端口转 int）。"""
    merged = {**_PG_DEFAULTS, **dict(dotenv), **dict(environ)}
    return {
        "host": merged["PG_HOST"],
        "port": int(merged["PG_PORT"]),
        "database": merged["PG_DB"],
        "user": merged["PG_USER"],
        "password": merged["PG_PASSWORD"],
    }


def ledger_query_plan(row: Mapping[str, Any], *, margin_s: float) -> dict[str, Any]:
    """单题归集查询计划（V2-33）：run_id 直查优先；缺 run_id 时间窗兜底。

    主路＝session 帧 run_id 等值直查（服务侧盖章后账本逐笔有值）；空串/纯空白
    同缺省处理（不拿空键直查）。兜底注记（票面「时间窗法保留为 fallback」）：
    jsonl 行缺 run_id（V1 base/帧解析失败）→时间窗；run_id 直查零行（账本行
    未盖章的旧窗）由 collect_spend 再退窗并在 spend.fallback 注记原因。
    """
    rid = str(row.get("run_id") or "").strip()
    if rid:
        return {"method": "run_id", "run_id": rid}
    start, end = expand_window(
        parse_ts(row["ask_started_at"]), parse_ts(row["ask_ended_at"]), margin_s
    )
    return {"method": "time_window", "start": start, "end": end}


def aggregate_ledger_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """账本行 → 单题计费聚合（sums＋by_caller＋逐笔 call_ids＋run_id 现值留档）。"""
    calls = fallback_calls = input_tokens = output_tokens = 0
    cost = 0.0
    by_caller: dict[str, dict[str, Any]] = {}
    call_ids: list[str] = []
    run_ids: list[str] = []
    for r in rows:
        calls += 1
        fallback_calls += 1 if r["fallback"] else 0
        row_in, row_out = int(r["input_tokens"]), int(r["output_tokens"])
        row_cost = float(r["cost_yuan"])
        input_tokens += row_in
        output_tokens += row_out
        cost += row_cost
        bucket = by_caller.setdefault(
            r["caller"],
            {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_yuan": 0.0},
        )
        bucket["calls"] += 1
        bucket["input_tokens"] += row_in
        bucket["output_tokens"] += row_out
        bucket["cost_yuan"] = round(bucket["cost_yuan"] + row_cost, 6)
        call_ids.append(r["id"])
        if r.get("run_id"):
            run_ids.append(r["run_id"])
    return {
        "calls": calls,
        "fallback_calls": fallback_calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_yuan": round(cost, 6),
        "by_caller": by_caller,
        "call_ids": call_ids,
        "ledger_run_ids": run_ids,
    }


def spend_summary(
    *,
    tag: str,
    base: str,
    caller_prefix: str,
    rows: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """批次计费摘要（合计只算归集成功行；失败行进 errors 逐条留痕）。"""
    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    totals = {"calls": 0, "fallback_calls": 0, "input_tokens": 0,
              "output_tokens": 0, "cost_yuan": 0.0}
    ok = 0
    for row in rows:
        spend = row.get("spend") or {}
        if "error" in spend:
            errors.append({"qid": row.get("qid"), "error": spend["error"]})
            continue
        ok += 1
        items.append({
            "qid": row.get("qid"),
            "group": row.get("group"),
            "run_id": row.get("run_id"),
            "method": spend.get("method"),
            "calls": spend.get("calls", 0),
            "cost_yuan": spend.get("cost_yuan", 0.0),
            "call_ids": spend.get("call_ids", []),
        })
        for key in ("calls", "fallback_calls", "input_tokens", "output_tokens"):
            totals[key] += spend.get(key, 0)
        totals["cost_yuan"] = round(totals["cost_yuan"] + spend.get("cost_yuan", 0.0), 6)
    return {
        "tag": tag,
        "base": base,
        "caller_prefix": caller_prefix,
        "generated_at": generated_at,
        "questions": len(rows),
        "spend_ok": ok,
        "spend_errors": len(errors),
        "totals": totals,
        "items": items,
        "errors": errors,
    }


async def collect_spend(
    rows: list[dict[str, Any]],
    *,
    dsn: str | None,
    connect_kwargs: dict[str, Any],
    caller_prefix: str,
    margin_s: float,
) -> None:
    """跑批后逐题归集计费（V2-33 主路 run_id 直查；时间窗兜底注记不静默）。

    只读 SELECT；单题归集失败行内留痕不断跑批。spend.method 记实际归集路
    （run_id｜time_window）；spend.fallback 仅兜底行携带（原因人话注记）。
    """
    try:
        conn = await asyncpg.connect(dsn=dsn) if dsn else await asyncpg.connect(**connect_kwargs)
    except Exception as exc:  # 连接失败＝整批计费未归集（行内留痕，跑批结果不回滚）
        reason = f"{type(exc).__name__}: {str(exc)[:200]}"
        for row in rows:
            row["spend"] = {"error": reason}
        print(f"[spend] 账本连接失败，{len(rows)} 行计费未归集：{reason}")
        return
    try:
        pattern = f"{caller_prefix}%" if caller_prefix else "%"
        for row in rows:
            plan = ledger_query_plan(row, margin_s=margin_s)
            try:
                fallback_note: str | None = None
                if plan["method"] == "run_id":
                    ledger = await conn.fetch(SPEND_SQL_BY_RUN, plan["run_id"])
                    method = "run_id"
                    if not ledger:
                        # 兜底（票面 V2-33）：直查零行＝账本行未盖章（盖章前旧窗/
                        # 旧服务版本）——退时间窗归集，注记原因不静默。
                        method = "time_window"
                        fallback_note = "run_id 直查零行（账本行未盖章？）——退时间窗兜底"
                        start, end = expand_window(
                            parse_ts(row["ask_started_at"]),
                            parse_ts(row["ask_ended_at"]),
                            margin_s,
                        )
                        ledger = await conn.fetch(SPEND_SQL, start, end, pattern)
                else:
                    method = "time_window"
                    fallback_note = "jsonl 行无 run_id——时间窗兜底"
                    ledger = await conn.fetch(
                        SPEND_SQL, plan["start"], plan["end"], pattern
                    )
                row["spend"] = aggregate_ledger_rows(ledger)
                row["spend"]["method"] = method
                if fallback_note:
                    row["spend"]["fallback"] = fallback_note
                s = row["spend"]
                print(f"[spend] {row['qid']} {s['calls']} 笔 {s['cost_yuan']} 元"
                      f"（入 {s['input_tokens']}／出 {s['output_tokens']} tokens"
                      f"｜{method}）")
            except Exception as exc:  # 单题归集失败不断批次
                row["spend"] = {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}
                print(f"[spend] {row['qid']} 归集失败：{row['spend']['error']}")
    finally:
        await conn.close()


def rewrite_jsonl_rows(out_path: Path, updated: list[dict[str, Any]]) -> None:
    """把本轮行（spend 字段补齐后）原子回写进 append-only 跑批 jsonl。

    匹配键＝(qid, ask_started_at)——同 tag 重复跑批同一题时行仍可区分；
    非本轮行原样保留（只重序列化，不改语义）。
    """
    by_key = {(r.get("qid"), r.get("ask_started_at")): r for r in updated}
    lines: list[str] = []
    for line in out_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        key = (obj.get("qid"), obj.get("ask_started_at"))
        if key in by_key:
            obj = by_key.pop(key)
        lines.append(json.dumps(obj, ensure_ascii=False))
    for rest in by_key.values():  # 理论不达（本轮行必已 append）——兜底不丢行
        lines.append(json.dumps(rest, ensure_ascii=False))
    tmp = out_path.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(out_path)


# ---------- 跑批主流程 ----------


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
    ap.add_argument("--out-dir", default=None,
                    help="产物根目录重定位（缺省 eval/results；frames 落其下 frames/）")
    ap.add_argument("--spend", action="store_true",
                    help="跑批后逐题从网关 spend 账本归集计费（jsonl 增 spend 字段＋计费摘要件）")
    ap.add_argument("--spend-dsn", default=None, help="账本 PG DSN 整串（缺省按 PG_* 参数装配）")
    ap.add_argument("--caller-prefix", default=None,
                    help="账本 caller 前缀过滤（缺省：v2 base＝v2.runtime.；V1 base＝不过滤）")
    ap.add_argument("--spend-margin", type=float, default=0.0,
                    help="题时间窗两侧外扩秒（同机部署缺省 0）")
    args = ap.parse_args()
    out_root = Path(args.out_dir) if args.out_dir else FRAMES_DIR.parent
    frames_dir = out_root / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_root / f"{args.tag}-跑批结果.jsonl"

    suite = suites[args.suite]
    targets = [e for e in suite if args.qid is None or e[0] == args.qid]
    done = 0
    this_run: list[dict] = []  # 本轮写入的行（--spend 时补齐 spend 字段用）
    timeout = httpx.Timeout(connect=10, read=300, write=10, pool=10)
    async with httpx.AsyncClient(timeout=timeout) as c:
        with out_path.open("a", encoding="utf-8") as out:
            for qid, group, question in targets:
                frame_path = frames_dir / f"{args.tag}-{qid}.json"
                row = {"qid": qid, "group": group, "question": question}
                asked_at = fmt_ts(now_ts()) if args.spend else None
                if asked_at is not None:
                    row["ask_started_at"] = asked_at
                try:
                    out_data = await ask_once(c, args.base, question)
                except Exception as exc:  # 单题失败不断跑批
                    if asked_at is not None:
                        row["ask_ended_at"] = fmt_ts(now_ts())
                    row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                    print(f"[{done + 1}/{len(targets)}] {qid} ❌ 异常 {row['error'][:80]}")
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    out.flush()
                    this_run.append(row)
                    done += 1
                    continue
                if asked_at is not None:
                    row["ask_ended_at"] = fmt_ts(now_ts())
                frame_path.write_text(
                    json.dumps(out_data, ensure_ascii=False, indent=1), encoding="utf-8"
                )
                p = out_data.get("parsed") or {}
                if p.get("run_id"):
                    row["run_id"] = p["run_id"]
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
                this_run.append(row)
                done += 1
                dur = p.get("duration_s") or "?"
                label = row["chain"] or row.get("steps") or "?"
                print(f"[{done}/{len(targets)}] {qid} ✓ {dur}s chain={label}")
                await asyncio.sleep(args.sleep)

    if args.spend and this_run:
        caller_prefix = args.caller_prefix
        if caller_prefix is None:  # 缺省按端点族：v2 归 v2.runtime.*，V1 不过滤
            caller_prefix = ("v2.runtime."
                             if args.base.rstrip("/").endswith("/api/v2") else "")
        await collect_spend(
            this_run,
            dsn=args.spend_dsn,
            connect_kwargs=pg_connect_kwargs(environ=os.environ,
                                             dotenv=load_pg_env(DOTENV_PATH)),
            caller_prefix=caller_prefix,
            margin_s=args.spend_margin,
        )
        rewrite_jsonl_rows(out_path, this_run)
        summary = spend_summary(
            tag=args.tag, base=args.base, caller_prefix=caller_prefix,
            rows=this_run, generated_at=fmt_ts(now_ts()),
        )
        summary_path = out_root / f"{args.tag}-计费摘要.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        t = summary["totals"]
        print(f"[spend] 批次合计 {t['calls']} 笔 {t['cost_yuan']} 元"
              f"（入 {t['input_tokens']}／出 {t['output_tokens']} tokens）→ {summary_path}")
    print(f"完成 {done} 题 → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

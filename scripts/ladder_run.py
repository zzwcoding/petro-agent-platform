#!/usr/bin/env python3
"""scripts/ladder_run.py —— 分级实测跑题脚本（ladder 真机跑题＋证据一次归档）。

用途：对 127.0.0.1:8001（V2 运行时）真机跑一道题，把**全部证据**落到
`docs/runtime-refactor/ladder/<LEVEL>/`——每题三件套：

1. `NN-<关键词>.sse`                原始 SSE（含 resume 续段，段间以 `# --- resume ---` 分隔）
2. `NN-<关键词>-last-context.json`  末轮模型调用完整 messages＋response
   （取 `logs/llm_calls/*.jsonl` 按 run_id 过滤的最后一条）
3. `NN-<关键词>-summary.md`         机器生成的摘要（事件统计／前缀延伸报告／调用清单／拒因／ask 帧）

用法：

    .venv/bin/python scripts/ladder_run.py --level L0 --q "asdkfjqwqe" \
        [--choice "近 30 天"] [--user laowang] [--seq 3] [--base http://127.0.0.1:8001]

行为：
- POST `{base}/api/v2/chat/asks` 收 SSE 全程落盘；
- 流中出现 `ask` 帧且传了 `--choice` → 自动 POST `{base}/api/v2/chat/runs/{run_id}/resume`
  收第二段 SSE 拼上（**端点真源＝`appv2/api/chat.py` 路由表**——仓内无
  `/asks/{run_id}/resume` 形）；
- 出现 `ask` 帧但未传 `--choice` → 归档停在该处并在摘要注明「待用户选择」。

依赖：纯标准库（SSE 用 `subprocess` 调 curl——`curl -N` 直出流，不用 urllib 自造流式解析）。
"""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "http://127.0.0.1:8001"
DEFAULT_USER = "laowang"
DEFAULT_OUT_ROOT = REPO_ROOT / "docs/runtime-refactor/ladder"
DEFAULT_LOGS_DIR = REPO_ROOT / "logs/llm_calls"
RESUME_SEPARATOR = "# --- resume ---"
SEG_FIRST = "首段"
SEG_RESUME = "续段"
KEYWORD_CHARS = 12
UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|\s\x00-\x1f]')


# ── SSE 收发（curl 子进程）────────────────────────────────────────────────────


def curl_post(url: str, payload: dict, *, user: str, timeout: int) -> dict:
    """POST 一个 JSON 体并原样收流（curl -N；返回 rc／stdout／stderr／http 状态）。"""
    with tempfile.NamedTemporaryFile("r+", suffix=".headers", delete=False) as fh:
        header_path = fh.name
    args = [
        "curl",
        "-N",
        "-sS",
        "-m",
        str(timeout),
        "-X",
        "POST",
        url,
        "-H",
        "Content-Type: application/json",
        "-H",
        "Accept: text/event-stream",
        "-H",
        f"X-Dev-User: {user}",
        "--noproxy",
        "*",
        "-D",
        header_path,
        "--data-binary",
        "@-",
    ]
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        proc = subprocess.run(args, input=body, capture_output=True)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
        try:
            headers = Path(header_path).read_text("utf-8", errors="replace")
        except OSError:
            headers = ""
    except FileNotFoundError:
        return {
            "rc": -1,
            "stdout": "",
            "stderr": "curl 不存在（PATH 未命中）",
            "http_status": None,
            "headers": "",
        }
    finally:
        try:
            os.unlink(header_path)
        except OSError:
            pass
    status = None
    match = re.search(r"^HTTP/\S+\s+(\d{3})", headers, re.MULTILINE)
    if match:
        status = int(match.group(1))
    return {
        "rc": rc,
        "stdout": out.decode("utf-8", errors="replace"),
        "stderr": err.decode("utf-8", errors="replace"),
        "http_status": status,
        "headers": headers,
    }


# ── SSE 解析 ─────────────────────────────────────────────────────────────────


def parse_sse(text: str, segment: str) -> list[dict]:
    """SSE 文本 → [{'id', 'event', 'data', 'raw_data', 'segment'}]（宽容解析）。"""
    frames: list[dict] = []
    fields: dict[str, list[str]] = {}

    def flush() -> None:
        if not fields:
            return
        raw_data = "\n".join(fields.get("data", []))
        data: object = raw_data
        if raw_data:
            try:
                data = json.loads(raw_data)
            except ValueError:
                data = raw_data
        frames.append(
            {
                "id": fields.get("id", [""])[-1],
                "event": fields.get("event", [""])[-1],
                "data": data,
                "raw_data": raw_data,
                "segment": segment,
            }
        )
        fields.clear()

    for line in text.splitlines():
        if line == "":
            flush()
            continue
        if line.startswith(":"):
            continue
        name, sep, value = line.partition(":")
        if not sep:
            continue
        if value.startswith(" "):
            value = value[1:]
        fields.setdefault(name, []).append(value)
    flush()
    return frames


def payload_of(frame: dict) -> dict:
    data = frame.get("data")
    return data if isinstance(data, dict) else {}


def run_id_of(frames: list[dict]) -> str:
    """session 帧取值（首段／续段同形）。"""
    for frame in frames:
        if frame["event"] == "session":
            rid = payload_of(frame).get("run_id")
            if rid:
                return str(rid)
    return ""


def first_ask(frames: list[dict]) -> dict | None:
    for frame in frames:
        if frame["event"] == "ask":
            return frame
    return None


# ── llm_calls 取证 ───────────────────────────────────────────────────────────


def load_calls(run_id: str, logs_dir: Path) -> tuple[list[dict], list[str]]:
    """按 run_id 抽调用记录（同日多文件 glob 全扫，排除 `*.baseline`；文件序＝标序）。"""
    if not run_id:
        return [], []
    paths = [p for p in glob.glob(str(logs_dir / "*.jsonl")) if ".baseline" not in Path(p).name]
    paths.sort(key=lambda p: (os.path.getmtime(p), p))
    records: list[dict] = []
    for seq_no, path in enumerate(paths):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or run_id not in line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if str(row.get("run_id") or "") != run_id:
                        continue
                    row["_source_file"] = Path(path).name
                    row["_file_order"] = seq_no
                    records.append(row)
        except OSError:
            continue
    records.sort(key=lambda r: (str(r.get("ts") or ""), int(r.get("_file_order") or 0)))
    return records, [Path(p).name for p in paths]


def messages_of(record: dict) -> list[object]:
    msgs = record.get("messages")
    return list(msgs) if isinstance(msgs, list) else []


def common_prefix_len(left: list[object], right: list[object]) -> int:
    count = 0
    for a, b in zip(left, right, strict=False):
        if a == b:
            count += 1
        else:
            break
    return count


# ── 归档路径 ─────────────────────────────────────────────────────────────────


def keyword_of(question: str) -> str:
    text = UNSAFE_CHARS.sub("", question.strip())
    text = text.rstrip("？?。.！!，,、；;：:")
    return text[:KEYWORD_CHARS] or "题"


def next_seq(out_dir: Path) -> int:
    used = []
    for path in out_dir.glob("*"):
        match = re.match(r"^(\d{2})-", path.name)
        if match:
            used.append(int(match.group(1)))
    return (max(used) + 1) if used else 1


# ── 摘要 ─────────────────────────────────────────────────────────────────────


def _counts_table(frames: list[dict]) -> list[str]:
    first = Counter(f["event"] for f in frames if f["segment"] == SEG_FIRST)
    second = Counter(f["event"] for f in frames if f["segment"] == SEG_RESUME)
    events = sorted(set(first) | set(second))
    lines = ["| 事件 | 首段 | 续段 | 合计 |", "| --- | --- | --- | --- |"]
    for event in events:
        lines.append(
            f"| `{event}` | {first.get(event, 0)} | {second.get(event, 0)} | "
            f"{first.get(event, 0) + second.get(event, 0)} |"
        )
    lines.append(
        f"| **合计** | {sum(first.values())} | {sum(second.values())} | "
        f"{sum(first.values()) + sum(second.values())} |"
    )
    return lines


def _prefix_report(records: list[dict]) -> tuple[list[str], str, bool]:
    """相邻调用链前缀延伸报告（KV 纪律验收线）。"""
    lines = [
        "| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    ok = True
    pairs = 0
    for index, record in enumerate(records):
        cur = messages_of(record)
        if index == 0:
            lines.append(f"| 1 | `{record.get('caller')}` | — | {len(cur)} | — | 起始调用 |")
            continue
        prev = messages_of(records[index - 1])
        common = common_prefix_len(prev, cur)
        extended = common >= len(prev) and len(cur) >= len(prev)
        pairs += 1
        ok = ok and extended
        lines.append(
            f"| {index + 1} | `{record.get('caller')}` | {len(prev)} | {len(cur)} | "
            f"{common} | {'✅ 前缀延伸' if extended else '⚠️ 非前缀延伸（KV 失效）'} |"
        )
    if not pairs:
        return lines, "调用链不足两条，无法判定前缀延伸", True
    verdict = (
        f"相邻调用前缀延伸 {pairs}/{pairs} 对 ✅（前链恒为后链前缀）"
        if ok
        else f"⚠️ 存在非前缀延伸（{pairs} 对中含断裂——KV 纪律验收线不达标）"
    )
    return lines, verdict, ok


def build_summary(
    *,
    level: str,
    seq: int,
    keyword: str,
    question: str,
    choice: str | None,
    user: str,
    base: str,
    run_id: str,
    ask_res: dict,
    resume_res: dict | None,
    frames: list[dict],
    ask_frame: dict | None,
    records: list[dict],
    logs_files: list[str],
    archive: dict[str, Path],
) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    finals = [
        payload_of(f)
        for f in frames
        if f["event"] == "verdict" and payload_of(f).get("subtype") == "final"
    ]
    verdict_line = "无 verdict(final) 帧"
    if finals:
        final = finals[-1]
        verdict_line = (
            f"`{final.get('status')}`（run_id={final.get('run_id')}，"
            f"manifest_digest={final.get('manifest_digest')}）"
        )

    notices = [
        (f["id"], payload_of(f).get("type"), payload_of(f).get("content"))
        for f in frames
        if f["event"] == "notice"
    ]
    rejects = [
        (f["id"], payload_of(f).get("title"))
        for f in frames
        if f["event"] == "step" and "被拒" in str(payload_of(f).get("title") or "")
    ]

    callers = Counter(str(r.get("caller") or "") for r in records)
    chain = [len(messages_of(r)) for r in records]
    prefix_lines, prefix_verdict, _ = _prefix_report(records)

    parts: list[str] = []
    parts.append(f"# {level} · {seq:02d} · {question}")
    parts.append("")
    parts.append(f"- 生成时刻：`{now}`（`scripts/ladder_run.py`）")
    parts.append(f"- 层级／序号：`{level}` / `{seq:02d}`")
    parts.append(f"- 题面：{question}")
    parts.append(f"- 端点：`{base}`；身份：`X-Dev-User: {user}`")
    parts.append(f"- run_id：`{run_id or '（流内未取到——非流响应？）'}`")
    parts.append(f"- verdict(final)：{verdict_line}")
    parts.append(f"- 首段 HTTP：{ask_res.get('http_status')}／curl rc={ask_res.get('rc')}")
    if resume_res is not None:
        parts.append(
            f"- 续段（resume）：`{resume_res.get('url')}` HTTP "
            f"{resume_res.get('http_status')}／curl rc={resume_res.get('rc')}"
        )
    else:
        parts.append("- 续段（resume）：未发起")
    if ask_frame is not None:
        if (choice or "").strip():
            parts.append(f"- 用户选择（`--choice`）：{choice}")
        else:
            parts.append(
                "- **状态：待用户选择**（流内出现 `ask` 帧且未传 `--choice`，归档含首段为止）"
            )
    elif (choice or "").strip():
        parts.append(f"- 传入 `--choice`：{choice}（但本次流内未出现 `ask` 帧——未发起续段）")
    parts.append("")

    parts.append("## 事件统计")
    parts.append("")
    parts.extend(_counts_table(frames))
    parts.append("")

    parts.append("## 前缀延伸报告（KV 纪律验收线）")
    parts.append("")
    parts.append(prefix_verdict)
    parts.append("")
    parts.extend(prefix_lines)
    parts.append("")
    parts.append(
        f"证据源：`logs/llm_calls/`（本次 glob {len(logs_files)} 个 jsonl，"
        f"排除 `*.baseline`；run 命中 {len(records)} 条）"
    )
    parts.append("")

    parts.append("## 调用清单")
    parts.append("")
    if records:
        parts.append("| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |")
        parts.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for index, record in enumerate(records, start=1):
            resp = record.get("response") if isinstance(record.get("response"), dict) else {}
            parts.append(
                f"| {index} | {record.get('ts')} | `{record.get('caller')}` | "
                f"{len(messages_of(record))} | {resp.get('prompt_tokens')} | "
                f"{resp.get('cached_tokens')} | {resp.get('duration_ms')} | "
                f"{record.get('error')} |"
            )
        parts.append("")
        parts.append(
            "caller×次数："
            + "、".join(f"`{name}`×{count}" for name, count in callers.most_common())
        )
        chain_text = " → ".join(str(n) for n in chain)
        grew = all(b >= a for a, b in itertools.pairwise(chain))
        parts.append("")
        parts.append(f"链长增长：{chain_text}" + ("" if grew else "（⚠️ 非单调）"))
    else:
        parts.append(
            "⚠️ 未在 `logs/llm_calls/*.jsonl` 中按 run_id 命中调用记录"
            "（run 可能未触发模型调用，或日志未落盘）"
        )
    parts.append("")

    parts.append("## 拒因与 notice")
    parts.append("")
    if rejects:
        parts.append("被拒步记录：")
        parts.append("")
        for frame_id, title in rejects:
            parts.append(f"- `id={frame_id}` {title}")
        parts.append("")
    if notices:
        parts.append("notice 帧：")
        parts.append("")
        for frame_id, ntype, content in notices:
            parts.append(f"- `id={frame_id}` `{ntype}`：{content}")
        parts.append("")
    if not rejects and not notices:
        parts.append("（无）")
        parts.append("")

    parts.append("## ask 帧")
    parts.append("")
    if ask_frame is not None:
        parts.append(f"- 帧位：`id={ask_frame['id']}`（{ask_frame['segment']}）")
        parts.append("")
        parts.append("```json")
        parts.append(json.dumps(ask_frame["data"], ensure_ascii=False, indent=2))
        parts.append("```")
    else:
        parts.append("（无 ask 帧）")
    parts.append("")

    parts.append("## 归档文件")
    parts.append("")
    for name, path in archive.items():
        parts.append(f"- `{name}`：`{path}`")
    parts.append("")
    return "\n".join(parts)


# ── 主流程 ───────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="分级实测跑题脚本（真机跑题 + 证据三件套归档）")
    parser.add_argument("--level", required=True, help="层级（L0…L5），归档案夹名")
    parser.add_argument("--q", required=True, help="题面")
    parser.add_argument("--choice", default=None, help="ask 帧的选项（传则自动 resume）")
    parser.add_argument("--user", default=DEFAULT_USER, help="X-Dev-User 身份")
    parser.add_argument("--base", default=DEFAULT_BASE, help="服务基址")
    parser.add_argument("--seq", type=int, default=None, help="级内序号（缺省自动数现有文件）")
    parser.add_argument("--timeout", type=int, default=300, help="单段 curl 超时秒数")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="归档根目录")
    parser.add_argument("--logs-dir", default=str(DEFAULT_LOGS_DIR), help="llm_calls 目录")
    parser.add_argument("--force", action="store_true", help="序号撞车时覆盖")
    args = parser.parse_args(argv)

    base = args.base.rstrip("/")
    out_dir = Path(args.out_root) / args.level
    out_dir.mkdir(parents=True, exist_ok=True)
    seq = args.seq if args.seq else next_seq(out_dir)
    keyword = keyword_of(args.q)
    stem = f"{seq:02d}-{keyword}"
    archive = {
        f"{stem}.sse": out_dir / f"{stem}.sse",
        f"{stem}-last-context.json": out_dir / f"{stem}-last-context.json",
        f"{stem}-summary.md": out_dir / f"{stem}-summary.md",
    }
    if not args.force:
        clashing = [str(p) for p in archive.values() if p.exists()]
        if clashing:
            print("序号撞车（加 --seq 换号或 --force 覆盖）：", file=sys.stderr)
            for path in clashing:
                print(f"  {path}", file=sys.stderr)
            return 2

    print(f"[ladder] {args.level} #{seq:02d} 提问：{args.q}")
    ask_res = curl_post(
        f"{base}/api/v2/chat/asks",
        {"question": args.q},
        user=args.user,
        timeout=args.timeout,
    )
    frames = parse_sse(ask_res["stdout"], SEG_FIRST)
    run_id = run_id_of(frames)
    print(
        f"[ladder] 首段：HTTP {ask_res['http_status']}／curl rc={ask_res['rc']}／"
        f"帧 {len(frames)}／run_id={run_id or '（无）'}"
    )

    sse_text = ask_res["stdout"].rstrip("\n")
    if ask_res["stderr"].strip():
        sse_text += f"\n\n# stderr: {ask_res['stderr'].strip()}"

    ask_frame = first_ask(frames)
    resume_res: dict | None = None
    choice = (args.choice or "").strip()
    if ask_frame is not None and choice:
        frame_payload = payload_of(ask_frame).get("frame")
        frame_payload = frame_payload if isinstance(frame_payload, dict) else {}
        kind = str(frame_payload.get("kind") or "clarify")
        if kind == "external_table_approval" and choice in {"approve", "reject"}:
            resume_body = {"kind": "approval", "decision": choice}
        else:
            resume_body = {"kind": "clarify", "choice": choice}
        url = f"{base}/api/v2/chat/runs/{run_id}/resume"
        print(f"[ladder] 命中 ask 帧（kind={kind}）→ resume：{url} body={resume_body}")
        got = curl_post(url, resume_body, user=args.user, timeout=args.timeout)
        got["url"] = url
        resume_res = got
        resume_frames = parse_sse(got["stdout"], SEG_RESUME)
        print(
            f"[ladder] 续段：HTTP {got['http_status']}／curl rc={got['rc']}／"
            f"帧 {len(resume_frames)}"
        )
        sse_text += f"\n\n{RESUME_SEPARATOR}\n\n" + got["stdout"].rstrip("\n")
        if got["stderr"].strip():
            sse_text += f"\n\n# stderr(resume): {got['stderr'].strip()}"
        frames = frames + resume_frames
        if not run_id:
            run_id = run_id_of(resume_frames)
    elif ask_frame is not None:
        print("[ladder] 命中 ask 帧但未传 --choice → 归档停在此处（待用户选择）")

    archive[f"{stem}.sse"].write_text(sse_text + "\n", encoding="utf-8")

    records, logs_files = load_calls(run_id, Path(args.logs_dir))
    last = records[-1] if records else None
    context_payload: dict[str, object] = {
        "_note": (
            "末轮模型调用（messages＋response 原样；来源＝logs/llm_calls/*.jsonl "
            "按 run_id 过滤取最后一条）"
        ),
        "run_id": run_id,
        "_matched_calls": len(records),
        "_scanned_files": logs_files,
        "call": last,
    }
    archive[f"{stem}-last-context.json"].write_text(
        json.dumps(context_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[ladder] llm_calls：命中 {len(records)} 条"
        + (f"，末轮 caller={last.get('caller')} 链长={len(messages_of(last))}" if last else "")
    )

    summary = build_summary(
        level=args.level,
        seq=seq,
        keyword=keyword,
        question=args.q,
        choice=args.choice,
        user=args.user,
        base=base,
        run_id=run_id,
        ask_res=ask_res,
        resume_res=resume_res,
        frames=frames,
        ask_frame=ask_frame,
        records=records,
        logs_files=logs_files,
        archive=archive,
    )
    archive[f"{stem}-summary.md"].write_text(summary, encoding="utf-8")

    print("\n[ladder] 归档：")
    for path in archive.values():
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

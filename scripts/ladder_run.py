#!/usr/bin/env python3
"""scripts/ladder_run.py —— 分级实测跑题脚本（ladder 真机跑题＋证据一次归档）。

用途：对 127.0.0.1:8001（V2 运行时）真机跑一道题，把**全部证据**落到
`docs/runtime-refactor/ladder/<LEVEL>/`——每题归档件：

1. `NN-<关键词>.sse`                原始 SSE（含 resume 续段，段间以 `# --- resume ---` 分隔）
2. `NN-<关键词>-resume.sse`         续段原始 SSE（仅发起了 resume 时落盘；前端实验单独取用）
3. `NN-<关键词>-last-context.json`  末轮模型调用完整 messages＋response
   （取 `logs/llm_calls/*.jsonl` 按 run_id 过滤的最后一条）
4. `NN-<关键词>-summary.md`         机器生成的摘要（事件统计／前缀延伸报告／调用清单／拒因／ask 帧）

**完整性纪律**：`summary.md` 只在**跑题全程结束后**生成——首段＋续段（若有）全部收流完毕、
`logs/llm_calls/` 落盘之后，才按 run_id 全量取调用记录；事件统计／ask 帧／notice／调用清单／
前缀延伸报告一律覆盖完整 run（首段＋续段）。run 中途挂起（`ask` 帧无 `--choice`）或续段被截断时，
摘要在头部显著标注覆盖范围——**summary 是完整 run 的唯一权威摘要，引用前先看覆盖范围行**。

已有归档若摘要不全（典型事故：续段事后单独补跑，首段摘要先落了盘），用 `--resummarize`
从已归档 SSE 重建摘要，不重跑题：

    .venv/bin/python scripts/ladder_run.py --resummarize L3 05

用法：

    .venv/bin/python scripts/ladder_run.py --level L0 --q "asdkfjqwqe" \
        [--choice "近 30 天"] [--user laowang] [--seq 3] [--base http://127.0.0.1:8001] \
        [--out-root ...] [--logs-dir ...] [--force]

    .venv/bin/python scripts/ladder_run.py --resummarize <级> <编号> \
        [--out-root ...] [--logs-dir ...]

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
RESUME_SEP_RE = re.compile(r"(?m)^#\s*---\s*resume\s*---\s*$")
ARCHIVE_MARKER_RE = re.compile(r"(?m)^#.*$")
RESUME_FILE_SUFFIX = "-resume.sse"
LAST_CONTEXT_SUFFIX = "-last-context.json"
SUMMARY_SUFFIX = "-summary.md"
CLARIFY_RECOVER_PREFIX = "澄清回收："
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


def load_calls(run_id: str, logs_dir: Path) -> tuple[list[dict], list[str], int]:
    """按 run_id 抽调用记录（多文件 glob 全扫，排除 `*.baseline`；文件序＝标序）。

    返回（记录，扫描到的文件名，去重掉的重复行数）。同一条记录可能同时出现在
    `logs/llm_calls/` 的当日件与备份件里（如 `<日>.before-*.jsonl` 与 `<日>.jsonl`
    逐行同内容）——按全字段去重，避免调用清单／前缀延伸报告被重复行污染。
    """
    if not run_id:
        return [], [], 0
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
    deduped: list[dict] = []
    seen: set[str] = set()
    for row in records:
        key = json.dumps(
            {k: v for k, v in row.items() if not k.startswith("_")},
            sort_keys=True,
            ensure_ascii=False,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, [Path(p).name for p in paths], len(records) - len(deduped)


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


# ── 归档回读（--resummarize）──────────────────────────────────────────────────


def locate_stem(out_dir: Path, seq: int) -> list[str]:
    """级目录里该编号的归档名干（`NN-<关键词>`）——多于一个由调用方报错。"""
    prefix = f"{seq:02d}-"
    stems = {
        path.name[: -len(".sse")]
        for path in out_dir.glob(f"{prefix}*.sse")
        if not path.name.endswith(RESUME_FILE_SUFFIX)
    }
    return sorted(stems)


def strip_archive_markers(text: str) -> str:
    """清掉归档手写标记行（`# --- resume ---`／`# stderr: …`）——只留 SSE 本体再解析。"""
    return ARCHIVE_MARKER_RE.sub("", text)


def read_archived_streams(out_dir: Path, stem: str) -> dict:
    """读已归档 SSE → 帧与来源说明（兼容合体 `.sse` 与分离 `-resume.sse` 两种布局）。"""
    sse_path = out_dir / f"{stem}.sse"
    if not sse_path.exists():
        raise FileNotFoundError(f"缺首段归档：{sse_path}")
    resume_path = out_dir / f"{stem}{RESUME_FILE_SUFFIX}"
    text = sse_path.read_text("utf-8", errors="replace")
    parts = RESUME_SEP_RE.split(text, maxsplit=1)
    first_text, resume_text = (parts[0], parts[1]) if len(parts) == 2 else (text, None)
    if resume_text is None and resume_path.exists():
        resume_text = resume_path.read_text("utf-8", errors="replace")
        resume_source = f"`{resume_path.name}`"
    elif resume_text is not None and resume_path.exists():
        resume_source = (
            f"`{sse_path.name}`（内含续段）＋`{resume_path.name}`（并存，未用于解析）"
        )
    elif resume_text is not None:
        resume_source = f"`{sse_path.name}`（内含续段，段间 `{RESUME_SEPARATOR}`）"
    else:
        resume_source = ""
    first_frames = parse_sse(strip_archive_markers(first_text), SEG_FIRST)
    resume_frames = (
        parse_sse(strip_archive_markers(resume_text), SEG_RESUME)
        if resume_text is not None
        else []
    )
    return {
        "frames": first_frames + resume_frames,
        "first_frames": len(first_frames),
        "resume_frames": len(resume_frames),
        "has_resume": resume_text is not None,
        "resume_source": resume_source,
        "sse_path": sse_path,
        "resume_path": resume_path if resume_path.exists() else None,
    }


def read_prev_summary(summary_path: Path) -> dict:
    """从既有 summary.md 回读题面／端点／身份／choice 与（调用条数，事件帧合计）。"""
    meta: dict[str, object] = {
        "question": "",
        "base": "",
        "user": "",
        "choice": "",
        "calls": None,
        "frames": None,
    }
    if not summary_path.exists():
        return meta
    text = summary_path.read_text("utf-8", errors="replace")
    patterns = {
        "question": r"^- 题面：(.+)$",
        "base": r"^- 端点：`([^`]+)`",
        "user": r"X-Dev-User: ([^`\s]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            meta[key] = match.group(1).strip()
    match = re.search(r"^- 用户选择（`--choice`）：(.+)$", text, re.MULTILINE) or re.search(
        r"^- 传入 `--choice`：(.+?)(?:（|$)", text, re.MULTILINE
    )
    if match:
        meta["choice"] = match.group(1).strip()
    match = re.search(r"命中 (\d+) 条", text)
    if match:
        meta["calls"] = int(match.group(1))
    match = re.search(r"^\| \*\*合计\*\* \| (\d+) \| (\d+) \| (\d+) \|", text, re.MULTILINE)
    if match:
        meta["frames"] = int(match.group(3))
    return meta


def recover_choice(frames: list[dict]) -> str:
    """续段首个「澄清回收：X」步的 X（归档未记 `--choice` 时的回读；取不到返回空串）。"""
    for frame in frames:
        if frame["segment"] != SEG_RESUME or frame["event"] != "step":
            continue
        title = str(payload_of(frame).get("title") or "")
        if title.startswith(CLARIFY_RECOVER_PREFIX):
            return title[len(CLARIFY_RECOVER_PREFIX) :].strip()
    return ""


def question_of(frames: list[dict]) -> str:
    """blackbox 帧里的题面（归档摘要缺失时的兜底）。"""
    for frame in frames:
        if frame["event"] == "blackbox":
            question = str(payload_of(frame).get("question") or "")
            if question:
                return question
    return ""


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


def _segment_lines(
    first_prov: dict,
    resume_prov: dict | None,
    ask_frames: list[dict],
    choice: str | None,
    choice_source: str,
) -> list[str]:
    """头部「首段／续段／选择」三组行（跑题实测＝HTTP；重建＝归档来源）。"""
    lines: list[str] = []
    if first_prov.get("kind") == "archive":
        lines.append(f"- 首段：{first_prov.get('source')} 解析重建（{first_prov['frames']} 帧）")
    else:
        lines.append(
            f"- 首段 HTTP：{first_prov.get('http_status')}／curl rc={first_prov.get('rc')}"
        )
    if resume_prov is None:
        lines.append("- 续段（resume）：未发起")
    elif resume_prov.get("kind") == "archive":
        lines.append(
            f"- 续段（resume）：{resume_prov.get('source')} 解析重建"
            f"（{resume_prov['frames']} 帧）"
        )
    else:
        lines.append(
            f"- 续段（resume）：`{resume_prov.get('url')}` HTTP "
            f"{resume_prov.get('http_status')}／curl rc={resume_prov.get('rc')}"
        )
    if ask_frames:
        if resume_prov is not None:
            if (choice or "").strip():
                label = "`--choice`" if choice_source == "flag" else "自续段 `step` 帧回读"
                lines.append(f"- 用户选择（{label}）：{choice}")
            else:
                lines.append("- 续段（resume）已发起（归档未记录选择文本）")
        elif (choice or "").strip():
            lines.append(f"- 传入 `--choice`：{choice}（但本次流内未出现 `ask` 帧——未发起续段）")
        else:
            lines.append(
                "- **状态：待用户选择**（流内出现 `ask` 帧且未传 `--choice`，归档含首段为止）"
            )
    elif (choice or "").strip():
        lines.append(f"- 传入 `--choice`：{choice}（但本次流内未出现 `ask` 帧——未发起续段）")
    return lines


def _terminal_line(frames: list[dict], *, has_resume: bool) -> str:
    """流收尾自检：每段是否收到 `done` 帧（缺＝截断／超时，摘要可能不全）。"""

    def done_of(segment: str) -> bool:
        return any(f["event"] == "done" for f in frames if f["segment"] == segment)

    first = "首段 ✅ `done`" if done_of(SEG_FIRST) else "首段 ⚠️ 无 `done`（流截断？）"
    if not has_resume:
        return f"{first}；续段未发起"
    second = "续段 ✅ `done`" if done_of(SEG_RESUME) else "续段 ⚠️ 无 `done`（超时／截断）"
    return f"{first}；{second}"


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
    first_prov: dict,
    resume_prov: dict | None,
    frames: list[dict],
    records: list[dict],
    logs_files: list[str],
    archive: dict[str, Path],
    choice_source: str = "flag",
    origin: str = "",
    duplicate_rows: int = 0,
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

    ask_frames = [f for f in frames if f["event"] == "ask"]
    first_count = sum(1 for f in frames if f["segment"] == SEG_FIRST)
    resume_count = sum(1 for f in frames if f["segment"] == SEG_RESUME)

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
    parts.extend(_segment_lines(first_prov, resume_prov, ask_frames, choice, choice_source))
    coverage = f"{SEG_FIRST} {first_count} 帧"
    if resume_prov is not None:
        coverage += f" ＋ {SEG_RESUME} {resume_count} 帧"
    parts.append(f"- 覆盖范围：{coverage}（合计 {len(frames)} 帧；本摘要按完整 run 统计）")
    parts.append(f"- 流收尾：{_terminal_line(frames, has_resume=resume_prov is not None)}")
    parts.append("")
    if origin:
        parts.append(f"> 本摘要由 `--resummarize` 从归档 SSE 重建（不重跑题）：{origin}")
        parts.append("")
    if ask_frames and resume_prov is None and not (choice or "").strip():
        parts.append(
            "> ⚠️ **本摘要仅覆盖首段**：run 挂在 `ask` 帧、未发起续段——这不是完整 run 的摘要；"
            f"续段完成后请 `--resummarize {level} {seq:02d}` 重建。"
        )
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
    evidence = (
        f"证据源：`logs/llm_calls/`（本次 glob {len(logs_files)} 个 jsonl，"
        f"排除 `*.baseline`；按 run_id 命中 {len(records)} 条"
    )
    if duplicate_rows:
        evidence += f"，另去重备份重复行 {duplicate_rows} 条"
    parts.append(f"{evidence}）")
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
    if not ask_frames:
        parts.append("（无 ask 帧）")
    elif len(ask_frames) == 1:
        frame = ask_frames[0]
        parts.append(f"- 帧位：`id={frame['id']}`（{frame['segment']}）")
        parts.append("")
        parts.append("```json")
        parts.append(json.dumps(frame["data"], ensure_ascii=False, indent=2))
        parts.append("```")
    else:
        parts.append(f"共 {len(ask_frames)} 个 ask 帧（首段＋续段全量）：")
        for index, frame in enumerate(ask_frames, start=1):
            parts.append("")
            parts.append(f"### ask 帧 {index}（`id={frame['id']}`，{frame['segment']}）")
            parts.append("")
            parts.append("```json")
            parts.append(json.dumps(frame["data"], ensure_ascii=False, indent=2))
            parts.append("```")
    parts.append("")

    parts.append("## 归档文件")
    parts.append("")
    for name, path in archive.items():
        parts.append(f"- `{name}`：`{path}`")
    parts.append("")
    return "\n".join(parts)


# ── --resummarize：从归档重建摘要（不重跑题）──────────────────────────────────


def resummarize(
    *, level: str, seq_text: str, out_root: str, logs_dir: str, user: str, base: str
) -> int:
    """按 `NN-<关键词>.sse`（＋`-resume.sse`）与 logs 重建 summary.md。"""
    digits = re.sub(r"\D", "", seq_text or "")
    if not digits:
        print(f"[resummarize] 编号非法：{seq_text!r}（示例：--resummarize L3 05）", file=sys.stderr)
        return 2
    seq = int(digits)
    out_dir = Path(out_root) / level
    if not out_dir.is_dir():
        print(f"[resummarize] 级目录不存在：{out_dir}", file=sys.stderr)
        return 2
    stems = locate_stem(out_dir, seq)
    if not stems:
        print(
            f"[resummarize] {level}/{seq:02d} 未找到归档 `.sse`"
            f"（现查目录＝{out_dir}；--out-root 指对归档根）",
            file=sys.stderr,
        )
        return 2
    if len(stems) > 1:
        print(
            f"[resummarize] {level}/{seq:02d} 命中的归档名干 {len(stems)} 个（需恰好 1 个）：",
            file=sys.stderr,
        )
        for stem in stems:
            print(f"  {stem}", file=sys.stderr)
        return 2
    stem = stems[0]
    keyword = stem[len(f"{seq:02d}-") :]
    info = read_archived_streams(out_dir, stem)
    frames: list[dict] = info["frames"]
    run_id = run_id_of(frames)
    records, logs_files, duplicate_rows = load_calls(run_id, Path(logs_dir))

    summary_path = out_dir / f"{stem}{SUMMARY_SUFFIX}"
    prev = read_prev_summary(summary_path)
    question = str(prev["question"] or "") or question_of(frames) or keyword
    prev_base = str(prev["base"] or "")
    prev_user = str(prev["user"] or "")
    choice = str(prev["choice"] or "")
    choice_source = "flag" if choice else ""
    if info["has_resume"] and not choice:
        recovered = recover_choice(frames)
        if recovered:
            choice, choice_source = recovered, "resume_step"

    first_prov = {
        "kind": "archive",
        "source": f"`{info['sse_path'].name}`",
        "frames": info["first_frames"],
    }
    resume_prov = (
        {"kind": "archive", "source": info["resume_source"], "frames": info["resume_frames"]}
        if info["has_resume"]
        else None
    )
    archive = {
        name: path
        for name, path in (
            (f"{stem}.sse", info["sse_path"]),
            (f"{stem}{LAST_CONTEXT_SUFFIX}", out_dir / f"{stem}{LAST_CONTEXT_SUFFIX}"),
            (f"{stem}{SUMMARY_SUFFIX}", summary_path),
            (f"{stem}{RESUME_FILE_SUFFIX}", info["resume_path"]),
        )
        if path is not None and path.exists()
    }
    summary = build_summary(
        level=level,
        seq=seq,
        keyword=keyword,
        question=question,
        choice=choice,
        user=prev_user or user,
        base=(prev_base or base).rstrip("/"),
        run_id=run_id,
        first_prov=first_prov,
        resume_prov=resume_prov,
        frames=frames,
        records=records,
        logs_files=logs_files,
        archive=archive,
        choice_source=choice_source,
        origin=info["resume_source"] or f"`{info['sse_path'].name}`",
        duplicate_rows=duplicate_rows,
    )
    summary_path.write_text(summary, encoding="utf-8")

    old_calls, old_frames = prev["calls"], prev["frames"]
    old_text = "—" if old_calls is None else str(old_calls)
    old_frames_text = "—" if old_frames is None else str(old_frames)
    print(
        f"[resummarize] {level}/{seq:02d}（run_id={run_id or '（无）'}）："
        f"调用 {old_text} → {len(records)} 条；"
        f"事件 {old_frames_text} → {len(frames)} 帧"
        f"（{SEG_FIRST} {info['first_frames']}＋{SEG_RESUME} {info['resume_frames']}）"
    )
    print(f"\n[resummarize] 重建：\n  {summary_path}")
    print("  证据源：" + (info["resume_source"] or f"`{info['sse_path'].name}`（无续段）"))
    return 0


# ── 主流程 ───────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="分级实测跑题脚本（真机跑题 + 证据归档）")
    parser.add_argument("--level", help="层级（L0…L5），归档案夹名")
    parser.add_argument("--q", help="题面")
    parser.add_argument("--choice", default=None, help="ask 帧的选项（传则自动 resume）")
    parser.add_argument("--user", default=DEFAULT_USER, help="X-Dev-User 身份")
    parser.add_argument("--base", default=DEFAULT_BASE, help="服务基址")
    parser.add_argument("--seq", type=int, default=None, help="级内序号（缺省自动数现有文件）")
    parser.add_argument("--timeout", type=int, default=300, help="单段 curl 超时秒数")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="归档根目录")
    parser.add_argument("--logs-dir", default=str(DEFAULT_LOGS_DIR), help="llm_calls 目录")
    parser.add_argument("--force", action="store_true", help="序号撞车时覆盖")
    parser.add_argument(
        "--resummarize",
        nargs=2,
        metavar=("<级>", "<编号>"),
        help="从已归档 SSE（＋`-resume.sse` 若存在）与 logs 重建 summary.md，不重跑题",
    )
    args = parser.parse_args(argv)

    if args.resummarize:
        return resummarize(
            level=args.resummarize[0],
            seq_text=args.resummarize[1],
            out_root=args.out_root,
            logs_dir=args.logs_dir,
            user=args.user,
            base=args.base,
        )
    if not args.level or not args.q:
        parser.error("跑题需 --level 与 --q（或改用 --resummarize <级> <编号> 重建摘要）")

    base = args.base.rstrip("/")
    out_dir = Path(args.out_root) / args.level
    out_dir.mkdir(parents=True, exist_ok=True)
    seq = args.seq if args.seq else next_seq(out_dir)
    keyword = keyword_of(args.q)
    stem = f"{seq:02d}-{keyword}"
    archive = {
        f"{stem}.sse": out_dir / f"{stem}.sse",
        f"{stem}{LAST_CONTEXT_SUFFIX}": out_dir / f"{stem}{LAST_CONTEXT_SUFFIX}",
        f"{stem}{SUMMARY_SUFFIX}": out_dir / f"{stem}{SUMMARY_SUFFIX}",
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
        resume_path = out_dir / f"{stem}{RESUME_FILE_SUFFIX}"
        resume_path.write_text(got["stdout"].rstrip("\n") + "\n", encoding="utf-8")
        archive[f"{stem}{RESUME_FILE_SUFFIX}"] = resume_path
        frames = frames + resume_frames
        if not run_id:
            run_id = run_id_of(resume_frames)
    elif ask_frame is not None:
        print("[ladder] 命中 ask 帧但未传 --choice → 归档停在此处（待用户选择）")

    archive[f"{stem}.sse"].write_text(sse_text + "\n", encoding="utf-8")

    records, logs_files, duplicate_rows = load_calls(run_id, Path(args.logs_dir))
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
        + (f"（另去重备份重复行 {duplicate_rows} 条）" if duplicate_rows else "")
        + (f"，末轮 caller={last.get('caller')} 链长={len(messages_of(last))}" if last else "")
    )

    first_prov = {
        "kind": "live",
        "http_status": ask_res.get("http_status"),
        "rc": ask_res.get("rc"),
    }
    resume_prov = (
        {
            "kind": "live",
            "url": resume_res.get("url"),
            "http_status": resume_res.get("http_status"),
            "rc": resume_res.get("rc"),
        }
        if resume_res is not None
        else None
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
        first_prov=first_prov,
        resume_prov=resume_prov,
        frames=frames,
        records=records,
        logs_files=logs_files,
        archive=archive,
        duplicate_rows=duplicate_rows,
    )
    archive[f"{stem}{SUMMARY_SUFFIX}"].write_text(summary, encoding="utf-8")

    print("\n[ladder] 归档：")
    for path in archive.values():
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""从三本新语料题册逐字抽取题干，生成 suites_q6.py（一次性工具，跑完即弃）。

抽取纪律：题干原句不改写——从「**题干**：」行起到「**标准答案**」前的空行为止，
去掉前缀后按原文行序拼接（多行题干保留换行）。
"""
from __future__ import annotations

import re
from pathlib import Path

BOOKS = [
    ("answers/completion-题册-评审稿.md", r"^## T(\d+)〔", "NQ-C{}", "新语料·完井"),
    ("answers/dynamic-题册-评审稿.md", r"^## 题 (\d+)｜", "NQ-D{}", "新语料·动态"),
    ("answers/monthly-题册-评审稿.md", r"^### 题 (\d+)〔", "NQ-M{}", "新语料·月报"),
]
ROOT = Path(__file__).resolve().parents[3]


def extract(path: Path, head_re: str) -> list[tuple[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        m = re.match(head_re, lines[i])
        if not m:
            i += 1
            continue
        no = int(m.group(1))
        # 向后找题干行
        j = i + 1
        while j < len(lines) and not lines[j].startswith("**题干**"):
            j += 1
        assert j < len(lines), f"{path.name} 题{no} 找不到题干"
        stem_lines = [lines[j].replace("**题干**：", "", 1)]
        j += 1
        while j < len(lines) and lines[j].strip() and not lines[j].startswith("**标准答案"):
            stem_lines.append(lines[j])
            j += 1
        stem = "\n".join(s.rstrip() for s in stem_lines).strip()
        out.append((str(no), stem))
        i = j
    return out


def main() -> int:
    suites: dict[str, list[tuple[str, str, str]]] = {}
    body_parts: list[str] = []
    safe = {"新语料·完井": "COMPLETION_SUITE", "新语料·动态": "DYNAMIC_SUITE", "新语料·月报": "MONTHLY_SUITE"}
    for rel, head_re, qid_fmt, group in BOOKS:
        items = extract(ROOT / "eval" / "drafts-q4" / rel, head_re)
        assert len(items) == 10, f"{rel} 抽到 {len(items)} 题，应为 10"
        rows = "\n".join(
            '    ("%s", %s, %s),' % (qid_fmt.format(no), repr(group), repr(stem))
            for no, stem in items
        )
        body_parts.append(f"{safe[group]} = [\n{rows}\n]\n")
        suites[group] = [(qid_fmt.format(no), group, s) for no, s in items]
    entries = ", ".join(f"{repr(k)}: {safe[k]}" for k in suites)
    body_parts.append(f"SUITES = {{{entries}}}\n")
    header = (
        '"""新语料题集（Q6 批，eval/drafts-q4 三册 30 题）——题干自题册逐字抽取。\n\n'
        "由 eval/results/tools/extract_suites_q6.py 生成；题册修订后重跑该脚本再生成。\n"
        '"""\n\n'
    )
    out = ROOT / "eval" / "results" / "tools" / "suites_q6.py"
    out.write_text(header + "\n".join(body_parts), encoding="utf-8")
    total = sum(len(v) for v in suites.values())
    print(f"生成 {out}（{total} 题）：")
    for k, v in suites.items():
        print(f"  {k}: {len(v)} 题 [{v[0][0]}..{v[-1][0]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

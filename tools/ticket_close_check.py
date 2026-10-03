#!/usr/bin/env python3
"""sdd-flow ticket-close 闸：关票前机检收尾报告形状。

来源：sdd-flow skill 的 references/ticket-close-check.py
用法：复制到目标仓库 tools/ticket_close_check.py；
      `python3 tools/ticket_close_check.py <票文件.md> <收尾报告.md>`。
契约：sdd-flow references/ticket-gates.md「闸二」。

判定边界（只判形状，不判语义——质量由 L0 核对，闸只挡"该发生的没发生"）：
- 门禁证据：报告须含门禁族关键词 + 通过数数字（"全绿"两字无数字 FAIL——数字可被复核）
- 回写五样：spec/modules/CONTEXT/lessons/架构投影 各有一行"已回写"或"无变更+理由"标注
- 挂账归属：每条挂账行以「归属：X」收尾；出现挂账词却无归属标记 FAIL
- 裁决节：有「收尾裁决」节，逐条含处置词（采纳/修复/挂账/关闭/不采纳）
- 提交锚：报告含至少一枚 commit SHA（7 位以上十六进制）
门禁族与回写五样名可按项目自配（下方常量表头集中改）。
退出码：0=绿；1=红。
"""
import re
import sys
from pathlib import Path

FAILS: list[str] = []

# 项目自配区：按仓门禁族改名（默认 petro 四门禁＋web 三连口径）
GATE_FAMILIES = (
    ("ruff", re.compile(r"ruff", re.I)),
    ("类型检查", re.compile(r"mypy|tsc|pyright", re.I)),
    ("测试", re.compile(r"pytest|vitest|npm test", re.I)),
    ("边界/契约闸", re.compile(r"lint-imports|dependency-cruiser|check_specs|boundary", re.I)),
)
PASS_COUNT = re.compile(r"\d+\s*passed|\d+/\d+|0 (error|错)|全过|KEPT")
VAGUE_GREEN = re.compile(r"(?:门禁|测试)(?:全)?绿(?![^\n]*\d)")

WRITE_BACKS = {
    "spec": re.compile(r"specs/<?[^>\n]*>?\S*[:：].*(已回写|无变更|不涉及)", re.I),
    "modules": re.compile(r"(modules\.md|模块卡)[:：].*(已回写|无变更|不涉及)", re.I),
    "CONTEXT": re.compile(r"CONTEXT\.md[:：].*(已回写|无变更|不涉及)", re.I),
    "lessons": re.compile(r"lessons?/[:：].*(已回写|无变更|不涉及|施工日志)", re.I),
    "架构投影": re.compile(
        r"(架构投影|arch-notes|architecture-)[:：].*(已回写|无变更|不涉及)", re.I
    ),
}
DEBT_WORD = re.compile(r"挂账|归后续|待.*批|缓做|留待")
OWNERSHIP = re.compile(r"归属[:：]\s*\S")
VERDICT_SECTION = re.compile(r"收尾裁决")
DISPOSITION = re.compile(r"采纳|修复|挂账|关闭|不采纳|驳回|转票")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")


def check_report(text: str, name: str) -> None:
    for label, rx in GATE_FAMILIES:
        if not rx.search(text):
            FAILS.append(f"{name}: 收尾报告缺门禁族「{label}」的实跑记录")
    if VAGUE_GREEN.search(text) and not PASS_COUNT.search(text):
        FAILS.append(f"{name}: 门禁结论无通过数数字（'全绿'两字不可复核）")
    for label, rx in WRITE_BACKS.items():
        if not rx.search(text):
            FAILS.append(f"{name}: 回写五样缺「{label}」行的已回写/无变更标注")
    for m in DEBT_WORD.finditer(text):
        line = text[
            m.start():text.find("\n", m.start())
            if text.find("\n", m.start()) != -1
            else len(text)
        ]
        if not OWNERSHIP.search(line):
            FAILS.append(f"{name}: 挂账行无「归属：X」收尾 —— {line.strip()[:60]}")
    if not VERDICT_SECTION.search(text):
        FAILS.append(f"{name}: 无「收尾裁决」节")
    elif not DISPOSITION.search(text):
        FAILS.append(f"{name}: 裁决节只有问题列举、无处置词（采纳/修复/挂账…）")
    if not SHA.search(text):
        FAILS.append(f"{name}: 无 commit SHA（提交锚缺失）")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    ticket, report = Path(sys.argv[1]), Path(sys.argv[2])
    for p in (ticket, report):
        if not p.is_file():
            FAILS.append(f"{p}: 文件不存在")
    if not FAILS:
        check_report(report.read_text(encoding="utf-8"), report.name)
        if not VERDICT_SECTION.search(report.read_text(encoding="utf-8")):
            t = ticket.read_text(encoding="utf-8")
            if VERDICT_SECTION.search(t) and not DISPOSITION.search(t):
                FAILS.append(f"{ticket.name}: 票面条目有裁决节但无处置词")
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"ticket-close: {'GREEN' if not FAILS else f'{len(FAILS)} FAIL'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())

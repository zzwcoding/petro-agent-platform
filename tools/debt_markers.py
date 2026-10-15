"""债务标记闸（P1-13——AGENTS.md 硬纪律 8 的第二道机器闸）。

事故背景：A1 端点 3 的缺口标记曾只活在代码注释（「挂后续批」）与 UI 降级
文案（「未接线——暂不可点开」）里——代码不是账本，只存在于代码里的欠账
等于没有登记。本闸把债务标记变成机器可判的两级规则：

- **strict（web 源码，违规即红）**：``web/src`` 非测试文件中，凡命中债务
  短语（挂后续批/挂账/未接线/留后续票/随其票/接线预留/产品化批族）的行，
  必须携 ``DEBT(去向)`` 标签（同行或上方 2 行内），且去向**可解析**——
  票号（``P\\d-…``，须在 tickets/ 票面真实存在）/ ``阶段\\d`` 标注 / Owner。
  测试文件豁免（断言会合法引用 UI 文案原文）。
- **inventory（app/tests，报告不红）**：裸短语进盘点清单（``report`` 命令），
  供阶段收官的全量对齐工序 triage（回收/转票/Owner 砍）——docstring 交叉
  引用不强制改标签，但也不再能静默。

设计取舍：错误态文案（「加载失败——暂不可编辑」）不是债务，「暂不可」
不入短语表；债务的**过期**同样可判——DEBT 标签指向的票号不存在即红
（陈旧标记 = 账已清或账写错，两样都该修）。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 债务短语（前端延迟工作的披露话术族——「暂不可」族是错误态文案，不入表）
DEBT_PHRASES = re.compile(
    r"挂后续批|挂账|未接线|留后续票|随其票|随其端点票|接线预留|产品化批"
)
DEBT_TAG = re.compile(r"DEBT\(([^)]+)\)")
TICKET_ID = re.compile(r"^P\d+-\S+$")
PHASE_REF = re.compile(r"^阶段\d")

# strict 面：web 源码（非测试——测试断言合法引用 UI 文案原文）
STRICT_GLOBS = ("web/src/**/*.js", "web/src/**/*.jsx", "web/src/**/*.ts", "web/src/**/*.tsx")
# inventory 面：后端与测试（裸短语只进盘点报告）
INVENTORY_GLOBS = ("app/**/*.py", "appv2/**/*.py", "tests/**/*.py")


def _iter_files(repo: Path, globs: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for pattern in globs:
        files.extend(sorted(p for p in repo.glob(pattern) if p.is_file()))
    return [
        p for p in files
        if "node_modules" not in p.parts and "dist" not in p.parts
        and not p.name.endswith((".test.js", ".test.jsx", ".test.ts", ".test.tsx", ".spec.js"))
    ]


def _load_tickets_text(repo: Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(repo.glob("tickets/**/README.md"))
    )


def resolve_target(target: str, tickets_text: str) -> bool:
    """DEBT 去向可解析判定：票号须在票面真实存在 / 阶段标注 / Owner。"""
    target = target.strip()
    if PHASE_REF.match(target) or target == "Owner":
        return True
    if TICKET_ID.match(target):
        return target in tickets_text
    return False


def _tagged_nearby(lines: list[str], idx: int) -> str | None:
    """同行或上方 2 行内的 DEBT 标签去向（无则 None）。"""
    for offset in (0, -1, -2):
        at = idx + offset
        if at < 0:
            continue
        m = DEBT_TAG.search(lines[at])
        if m:
            return m.group(1)
    return None


def scan(
    repo: Path = REPO_ROOT, tickets_text: str | None = None
) -> tuple[list[str], list[str]]:
    """返回（违规清单, 盘点清单）——看守测试注入面。"""
    tickets = tickets_text if tickets_text is not None else _load_tickets_text(repo)
    violations: list[str] = []
    inventory: list[str] = []
    for path in _iter_files(repo, STRICT_GLOBS):
        lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            if not DEBT_PHRASES.search(line):
                continue
            target = _tagged_nearby(lines, idx - 1)
            rel = path.relative_to(repo)
            if target is None:
                violations.append(
                    f"{rel}:{idx} 裸债务短语无 DEBT 标签：{line.strip()[:80]}"
                )
            elif not resolve_target(target, tickets):
                violations.append(
                    f"{rel}:{idx} DEBT 去向不可解析（{target}）——"
                    "票号须存在于 tickets/ 或为 阶段\\d/Owner"
                )
    for path in _iter_files(repo, INVENTORY_GLOBS):
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if DEBT_PHRASES.search(line) and not DEBT_TAG.search(line):
                inventory.append(f"{path.relative_to(repo)}:{idx} {line.strip()[:80]}")
    return violations, inventory


def check(repo: Path = REPO_ROOT) -> list[str]:
    """闸面：strict 违规清单（空＝绿）。看守测试与 CLI 同源调用。"""
    return scan(repo)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="债务标记闸（AGENTS.md 硬纪律 8）")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="strict 违规对账（web 源码——违规 exit 1）")
    sub.add_parser("report", help="裸短语盘点清单（app/tests——收官对齐工序消费）")
    args = parser.parse_args(argv)
    violations, inventory = scan()
    if args.command == "check":
        if violations:
            print("债务标记闸红：")
            for v in violations:
                print(f"  - {v}")
            return 1
        print(
            f"债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签"
            f"（盘点 {len(inventory)} 条见 report）。"
        )
        return 0
    print(f"裸债务短语盘点 {len(inventory)} 条（app/tests——不红，收官 triage）：")
    for item in inventory:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

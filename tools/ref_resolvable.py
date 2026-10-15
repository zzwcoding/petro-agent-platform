"""真源引用可解析闸（治「指向不存在的真源」这一复发形态）。

病例（2026-10-15，两次均由独立评审抓出）：
- 规格把核心红线挂到边界规则 **`R7`**，但真源 `specs/modules.md` 当时只有 R1–R5——「幻影闸」；
- 规格把「大结果阈值」挂到 `walk/裁决表.md` §06-A 的统一预算表，**该表里根本没有这条阈值**。

本闸把「引用可解析」这件可机检的部分变成退出码，两条：
1. **真源纲目可解析**：`specs/*.md` 里凡出现在含「真源」二字**行内**的路径 token（反引号包住、
   含 `/` 或以 `.md` 结尾）必须能解析到一个真实文件（试 repo 相对 / `docs/runtime-refactor/`
   相对 / 补 `.md` 后缀）；若同行还标了节号（`§06-A` → `06`），该节须在目标文件里真实存在。
   —— 测试标识（`tests/...`）**不在作用面**：那是阶段 5 的承诺，不是真源。
2. **边界规则编号存在**：`specs/*.md` 里出现的 `R<数字>[字母]?` 编号，必须 ∈ 真源编号集——
   真源＝`specs/modules.md`「边界规则」表里加粗标注的编号 ∪ `tools/importlinter_v2.toml`
   契约名开头的编号（两者都算，如 `R5b` 只在后者）。

**能红就能修**：缺文件／缺节 → 补真源或改引用；编号不存在 → 改用真编号或把该规则落进真源。
**不判语义**：本闸只管"引的东西在不在"，不管"引的那一节里到底有没有那条事实"（后者人审）。

CLI：``check``（违规 exit 1）｜``report``（盘点，不红）。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = REPO_ROOT / "specs"
MODULES = SPECS_DIR / "modules.md"
LINTER = REPO_ROOT / "tools" / "importlinter_v2.toml"
REF_ROOTS = (REPO_ROOT, REPO_ROOT / "docs" / "runtime-refactor")

# 作用面：规格文件（modules.md 是真源本身，不当被检对象）
def _spec_files() -> list[Path]:
    return sorted(p for p in SPECS_DIR.glob("*.md") if p.name != "modules.md")


_SOURCE_LINE = re.compile(r"真源")
_TOKEN = re.compile(r"`([^`]+)`")
# 路径候选：含 `/` 或以 .md 结尾
_LOOKS_LIKE_PATH = re.compile(r"[/]|\.md$")
# 测试标识是阶段 5 的承诺，不是真源
_EXEMPT_PREFIXES = ("tests/",)
# 节号：§06-A → 06 ；§四 之类中文数字不判（无法可靠解析，计入 skip）
_SECTION = re.compile(r"§\s*([0-9]+)")
_RULE_ID = re.compile(r"\bR([0-9]+[a-z]?)\b")
_RULE_LABEL = re.compile(r"\*\*\s*(R[0-9]+[a-z]?)\s*\*\*")
_LINTER_NAME = re.compile(r'^name\s*=\s*"(R[0-9]+[a-z]?)', re.M)


def resolve_ref(token: str) -> Path | None:
    """把引用 token 解析成真实文件；解析不到返回 None。"""
    candidates: list[Path] = []
    for root in REF_ROOTS:
        candidates.append(root / token)
        if not token.endswith(".md"):
            candidates.append(root / f"{token}.md")
    for cand in candidates:
        if cand.is_file():
            return cand
    return resolve_ref_at(REPO_ROOT, token)


def section_exists(target: Path, num: str) -> bool:
    """目标文件里是否存在以该节号开头的标题（形如 `## 06 …`）。"""
    pat = re.compile(rf"^#+\s*0*{num}\b", re.M)
    try:
        return bool(pat.search(target.read_text(encoding="utf-8")))
    except OSError:
        return False


def rule_ids() -> set[str]:
    """真源编号集：modules.md 边界规则表标签 ∪ importlinter 契约名前缀。"""
    ids: set[str] = set()
    if MODULES.is_file():
        ids |= set(_RULE_LABEL.findall(MODULES.read_text(encoding="utf-8")))
    if LINTER.is_file():
        ids |= set(_LINTER_NAME.findall(LINTER.read_text(encoding="utf-8")))
    return ids


def check(repo: Path | None = None) -> list[str]:
    """作用面 × 两条判据 → 违规清单（空＝绿）。看守测试与 CLI 同源调用。"""
    root = repo or REPO_ROOT
    specs = sorted(p for p in (root / "specs").glob("*.md") if p.name != "modules.md")
    valid_ids = rule_ids()
    problems: list[str] = []

    for spec in specs:
        rel = spec.relative_to(root)
        for lineno, line in enumerate(spec.read_text(encoding="utf-8").splitlines(), 1):
            if _SOURCE_LINE.search(line):
                tokens = [
                    tk for tk in _TOKEN.findall(line)
                    if _LOOKS_LIKE_PATH.search(tk) and not tk.startswith(_EXEMPT_PREFIXES)
                ]
                sole = len(tokens) == 1  # 多路径行不判节（避免张冠李戴）
                for token in tokens:
                    target = resolve_ref_at(root, token)
                    if target is None:
                        problems.append(f"{rel}:{lineno} 真源引用解析不到：`{token}`")
                        continue
                    m = _SECTION.search(line) if sole else None
                    if m and not section_exists(target, m.group(1)):
                        problems.append(
                            f"{rel}:{lineno} 真源节不存在：`{token}` §{m.group(1)}"
                            f"（{target.relative_to(root)} 里无此节）"
                        )
            for rid in _RULE_ID.findall(line):
                if f"R{rid}" not in valid_ids:
                    problems.append(
                        f"{rel}:{lineno} 边界规则编号不存在于真源：`R{rid}`"
                        f"（真源现有：{'、'.join(sorted(valid_ids))}）"
                    )
    return problems


def resolve_ref_at(root: Path, token: str) -> Path | None:
    """同 resolve_ref，但以给定 root 为基准（供看守测试注入）。"""
    for base in (root, root / "docs" / "runtime-refactor"):
        for cand in (base / token, base / f"{token}.md"):
            if cand.is_file():
                return cand
        # 简写引用：`walk/08` → `08-澄清-意图澄清.md`、`synth/S3` → `S3-口径裁决清单.md`
        for cand in sorted(base.glob(f"{token}*")):
            if cand.is_file():
                return cand
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="真源引用可解析闸")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="作用面 × 两条判据 → 违规 exit 1")
    sub.add_parser("report", help="同 check，但只盘点不判失败")
    args = parser.parse_args(argv)
    problems = check()
    if args.command == "report":
        print(f"真源引用盘点：{len(problems)} 条")
        for p in problems:
            print(f"  - {p}")
        return 0
    if problems:
        print("真源引用可解析闸红：")
        for p in problems:
            print(f"  - {p}")
        return 1
    n = len(list(_spec_files()))
    print(f"真源引用可解析闸绿：{n} 份规格的真源引用与边界规则编号均可解析。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

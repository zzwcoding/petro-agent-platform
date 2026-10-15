"""施工收票暂存区闸（阶段 5 工序闸——主窗统一 commit 前的最后一道）。

用途：阶段 5 施工收票时**防止暂存区混入非本批文件**。施工子代理只许提交派单授权
文件（票面「Touches modules」点名的块目录＋票面对象列点明的测试文件）；子代理若顺手
把别批／别块／别页面的改动一起 ``git add`` 进来，主窗统一 commit 时就把不属于本批的
改动带进历史——事后只能靠人眼翻 ``git show --stat`` 抓。本闸把这一步变成机器可判：
**暂存区（git staged）若出现不属于本批票的文件即红**。

用法::

    python tools/sweep_guard.py --ticket RT-W4-05a [--extra path ...] \\
        [--allow-glob "tests/runtimev2/*"]

从 ``tickets/v2-refactor/<ticket>.md`` 提取本批授权面（三源，**宁宽勿漏**——宽一点
只会多一条 ``--allow-glob``／人工豁免，漏了闸就废了；提取面逐条打印进报告）：

- ① 票面 ``Touches modules`` 行的模块名（小写蛇形——同一行的 ``app.py``／``RunStore``
  一类文件名与类名不映射，防造出假块目录）→ 块目录（``appv2/runtimev2/<块>/``；存量块
  按 ``appv2/<块>/`` 等候选目录解析，均不存在的按票面期望落点宽放）；
- ② 票面任一处的 ``tests/**.py`` 路径（票面对象「对应测试」列点明的测试文件——新建
  测试文件此刻还不在磁盘上，故此类**不设存在性判据**）；
- ③ 票面反引号内的仓内相对路径引文（``specs/bookkeeping.md`` 一类；仓内代码顶层目录
  形态按声明路径宽放，其余须**磁盘上真实存在**才算）。

判据：``git diff --cached --name-only -z``（``-z`` 防中文／空格文件名被引号转义）得
暂存清单，清单 ⊆ 授权面 ∪ ``--extra`` ∪ ``--allow-glob``（fnmatch）＝绿；任何越界
文件＝红（exit 1），逐文件打印并给解禁二选一。

边界：暂存区为空＝绿（打印「暂存区为空」）；``--ticket`` 票面不存在＝红报错；票面
提取不到任何授权面＝红（「票面无授权文件集，禁止派发」——防裸票过闸，**即使暂存区
为空也红**）。票面文件本身不在授权面内（改票是主窗动作；收票要连票面改动一起提交时
用 ``--extra`` 显式豁免）。

``--self-test``：不碰真仓，用假 ``git diff --cached`` 输出跑边界与解禁面（绿／越界红／
空暂存／票不存在／票面无授权面／票面文件入暂存／``--extra`` 与 ``--allow-glob`` 解禁）。
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TICKET_DIR = Path("tickets") / "v2-refactor"

# 票面「Touches modules: `bookkeeping`（……）」行
TOUCHES_LINE = re.compile(r"^Touches modules\s*[:：]\s*(.*)$", re.MULTILINE)
# 票面反引号引文（路径引用、模块名、测试标识都在其中）
BACKTICK = re.compile(r"`([^`\n]+)`")
# 票面任一处的测试文件路径（票面对象「对应测试」列）
TEST_PATH = re.compile(r"tests/[A-Za-z0-9_./\u4e00-\u9fff-]+\.py")
TEST_ID_SUFFIX = re.compile(r"::[^\s`]*$")  # ::single_write_port
# 行锚：specs/bookkeeping.md:126／:103-118／:103–:118
LINE_ANCHOR = re.compile(r":\d+(?:[-–—~]\d*)?$")
# 块模块名（小写蛇形——Touches modules 行反引号里只有模块名才映射目录；
# 同一行的 `app.py`／`__init__.py` 一类文件名、`RunStore` 一类类名不映射）
MODULE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
# 模块名 → 目录候选（按序取第一个存在的；均不存在的按票面期望落点宽放）
MODULE_DIR_CANDIDATES = (
    "appv2/runtimev2/{name}",
    "appv2/{name}",
    "web/src/{name}",
    "app/{name}",
)
# 仓内顶层目录（反引号路径引文的形态判据——命中即按声明路径宽放，不要求已存在）
TOP_DIRS = frozenset({
    "app", "appv2", "config", "data-plane", "deploy", "docs", "eval", "migrations",
    "ontology", "scripts", "specs", "tests", "tools", "web",
})
GLOB_CHARS = "*?["
# 占位符字符（票面写「`tests/...`」一类示意引文——不是真路径）
PLACEHOLDER_CHARS = "…<>{}·＊"


@dataclass(frozen=True)
class Authority:
    """本批授权面：精确文件集＋目录前缀集＋逐条来源（报告输出用）。"""

    files: tuple[str, ...] = ()
    dirs: tuple[str, ...] = ()
    notes: tuple[tuple[str, str], ...] = ()

    def covers(self, path: str) -> bool:
        return path in self.files or any(path.startswith(d) for d in self.dirs)


@dataclass(frozen=True)
class Outcome:
    """闸的判定：退出码＋待打印报告行。"""

    code: int
    lines: list[str]


class _Builder:
    """授权面收集器（去重＋保序＋逐条记来源）。"""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.files: list[str] = []
        self.dirs: list[str] = []
        self.notes: list[tuple[str, str]] = []

    def add_file(self, path: str, note: str) -> None:
        if path and path not in self.files:
            self.files.append(path)
            self.notes.append((path, note))

    def add_dir(self, path: str, note: str) -> None:
        prefix = path if path.endswith("/") else path + "/"
        if prefix != "/" and prefix not in self.dirs:
            self.dirs.append(prefix)
            self.notes.append((prefix, note))


def _module_dir(name: str, repo: Path) -> str:
    """模块名 → 块目录（取第一个存在的候选；全不存在＝按票面期望落点宽放）。"""
    for pattern in MODULE_DIR_CANDIDATES:
        candidate = pattern.format(name=name)
        if (repo / candidate).is_dir():
            return candidate
    return MODULE_DIR_CANDIDATES[0].format(name=name)


def _strip_token(raw: str) -> str:
    """反引号引文归一：剥测试标识（::name）、行锚（:126／:103–:118）与尾标点。"""
    token = raw.strip().strip("`").strip()
    token = TEST_ID_SUFFIX.sub("", token)
    while True:
        stripped = LINE_ANCHOR.sub("", token)
        if stripped == token:
            break
        token = stripped.rstrip("–—~-")
    return token.strip().rstrip("。，、；;)]}）】")


def _classify(token: str, builder: _Builder) -> None:
    """把一条反引号引文按形态登记为文件／目录前缀（宁宽勿漏）。"""
    if any(ch in token for ch in GLOB_CHARS):
        return  # glob 形态不入授权面——豁免走 --allow-glob 显式声明
    if any(ch in token for ch in PLACEHOLDER_CHARS):
        return  # 示意引文（`tests/...` 一类）不是真路径
    if any(seg and set(seg) <= {"."} for seg in token.split("/")):
        return  # `tests/...` 一类省略号省略写法
    head = token.split("/", 1)[0]
    target = builder.repo / token
    if head in TOP_DIRS:
        # 代码／文档顶层目录形态：票面点名即为授权（新建文件此刻可能还不存在）
        if target.is_dir() or token.endswith("/"):
            builder.add_dir(token, "票面路径引文（目录）")
        elif target.is_file() or "." in token.rsplit("/", 1)[-1]:
            builder.add_file(token, "票面路径引文（文件）")
        else:
            builder.add_dir(token, "票面路径引文（目录）")
        return
    if not target.exists():
        return
    if target.is_dir():
        builder.add_dir(token, "票面路径引文（目录，存在）")
    else:
        builder.add_file(token, "票面路径引文（文件，存在）")


def extract_authority(text: str, repo: Path = REPO_ROOT) -> Authority:
    """票面文本 → 授权面（三源：Touches modules 模块目录／tests 路径／路径引文）。"""
    builder = _Builder(repo)
    for line in TOUCHES_LINE.findall(text):
        for raw in BACKTICK.findall(line):
            name = _strip_token(raw)
            if not MODULE_NAME.match(name):
                continue
            builder.add_dir(
                _module_dir(name, repo), f"Touches modules 行模块名 `{name}`"
            )
    for path in TEST_PATH.findall(text):
        builder.add_file(path, "票面 tests/ 路径（票面对象「对应测试」列）")
    for raw in BACKTICK.findall(text):
        token = _strip_token(raw)
        if "/" in token:
            _classify(token, builder)
    return Authority(tuple(builder.files), tuple(builder.dirs), tuple(builder.notes))


def git_staged(repo: Path) -> list[str]:
    """暂存清单（``git diff --cached --name-only -z``——-z 防中文／空格文件名转义）。"""
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        # git 在非仓目录会甩出整页用法（--no-index 回退）——只留首行 + 归因提示
        err_lines = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        detail = err_lines[0].strip() if err_lines else f"git 调用失败（exit {proc.returncode}）"
        raise RuntimeError(f"{detail[:200]}（--repo 须为 git 仓根：{repo}）")
    return [p for p in proc.stdout.decode("utf-8", "replace").split("\0") if p]


def resolve_ticket(ticket: str, repo: Path) -> Path | None:
    """票号 → 票面路径（``tickets/v2-refactor/<票号>.md``，可省 .md；兜底全票柜检索）。"""
    name = ticket.strip()
    if "/" in name:
        candidate = repo / name
        return candidate if candidate.is_file() else None
    stem = name[:-3] if name.endswith(".md") else name
    direct = repo / TICKET_DIR / f"{stem}.md"
    if direct.is_file():
        return direct
    hits = sorted(p for p in repo.glob(f"tickets/**/{stem}.md") if p.is_file())
    return hits[0] if hits else None


def _extra_covers(path: str, extra: list[str], repo: Path) -> bool:
    for entry in extra:
        target = entry.strip()
        if not target:
            continue
        if target.endswith("/") or (repo / target).is_dir():
            if path.startswith(target.rstrip("/") + "/"):
                return True
        elif path == target:
            return True
    return False


def _authority_lines(authority: Authority, extra: list[str], allow_globs: list[str]) -> list[str]:
    lines = ["授权面（提取自票面——三源宁宽勿漏；越界先查此表再决定豁免）:"]
    for item, note in authority.notes:
        kind = "目录" if item.endswith("/") else "文件"
        lines.append(f"  [{kind}] {item}  ← {note}")
    for entry in extra:
        lines.append(f"  [额外] {entry}  ← --extra 显式追加")
    for pattern in allow_globs:
        lines.append(f"  [豁免] {pattern}  ← --allow-glob fnmatch")
    if len(lines) == 1:
        lines.append("  （空）")
    return lines


def run(
    ticket: str,
    extra: list[str] | None = None,
    allow_globs: list[str] | None = None,
    repo: Path = REPO_ROOT,
    staged_provider: Callable[[Path], list[str]] = git_staged,
) -> Outcome:
    """闸体：票面授权面 × 暂存清单对账（自测注入 ``staged_provider`` 假 git 输出）。"""
    extras = list(extra or [])
    globs = list(allow_globs or [])
    label = ticket[:-3] if ticket.endswith(".md") else ticket.strip()
    ticket_path = resolve_ticket(ticket, repo)
    if ticket_path is None:
        return Outcome(1, [
            f"sweep_guard: 红——票面不存在：tickets/v2-refactor/{label}.md",
            "票号核对：--ticket <票号>（可省 .md）或 --ticket <仓内相对路径>",
        ])
    try:
        rel_ticket = ticket_path.relative_to(repo)
    except ValueError:
        rel_ticket = ticket_path
    head = [f"票面: {rel_ticket}"]
    authority = extract_authority(ticket_path.read_text(encoding="utf-8"), repo)
    if not authority.files and not authority.dirs:
        return Outcome(1, [
            *head,
            "sweep_guard: 红——票面无授权文件集，禁止派发",
            "（票面既无 Touches modules 模块目录、也无 tests/ 路径与路径引文——"
            "回主窗补票面授权面再派工）",
        ])
    face = _authority_lines(authority, extras, globs)
    try:
        staged = list(staged_provider(repo))
    except RuntimeError as exc:
        return Outcome(1, [*head, f"sweep_guard: 红——暂存清单读取失败：{exc}"])
    if not staged:
        return Outcome(0, [*head, "sweep_guard: 绿——暂存区为空（无可检查文件）", *face])
    outside = [
        path
        for path in staged
        if not authority.covers(path)
        and not _extra_covers(path, extras, repo)
        and not any(fnmatch.fnmatchcase(path, g) for g in globs)
    ]
    if not outside:
        return Outcome(0, [
            f"sweep_guard: 绿（{len(staged)} 文件全属本批）",
            *head,
            *face,
            f"暂存清单（{len(staged)} 文件）:",
            *(f"  - {path}" for path in staged),
        ])
    hints = []
    if any(path == rel_ticket.as_posix() for path in outside):
        hints.append(
            "（票面文件本身不在授权面内——收票要连票面改动一起提交时用"
            f" --extra {rel_ticket} 显式豁免）"
        )
    lines = [
        f"sweep_guard: 红——暂存区有 {len(outside)} 个文件不属于 {label} 授权面",
        *head,
        *face,
        f"暂存清单（{len(staged)} 文件）:",
        *(f"  - {path}" for path in staged),
        "越界清单:",
        *(f"越界: {path}（不属于 {label} 授权面）" for path in outside),
        "解禁二选一：票面补授权（回主窗改票）或 --allow-glob/--extra 显式豁免",
        *hints,
    ]
    return Outcome(1, lines)


def _self_test() -> int:
    """假 git 输出自测（不碰真仓）：绿／越界红／空暂存／票不存在／票面无授权面／豁免。"""
    good_ticket = "\n".join([
        "# RT-T-01a · bookkeeping（自测票）",
        "Touches modules: `bookkeeping`（自测——只建 bookkeeping 本体；另列 `RunStore` 类名"
        "与 `__init__.py` 文件名，均非模块名）",
        "## 任务",
        "按 `specs/bookkeeping.md` 新建 `appv2/runtimev2/bookkeeping/`；"
        "旧码 `appv2/runtime/graph.py` 本批不改。",
        "## 票面对象",
        "| 1 | 只经本块 | `tests/domains/test_v2_bookkeeping.py::single_write_port` |",
        "",
    ])
    bare_ticket = "# RT-T-02 · 裸票（自测）\n## 任务\n无授权面、无路径引文。\n"
    anchor_ticket = (
        "# RT-T-03 · 锚引文（自测票）\n"
        "## 任务\n铁律见 `specs/bookkeeping.md:126-135`（只有带行锚的引文一种授权源）。\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / TICKET_DIR).mkdir(parents=True)
        (repo / "appv2" / "runtimev2" / "bookkeeping").mkdir(parents=True)
        (repo / "specs").mkdir()
        (repo / "specs" / "bookkeeping.md").write_text("# spec\n", encoding="utf-8")
        (repo / TICKET_DIR / "RT-T-01a-bookkeeping.md").write_text(good_ticket, encoding="utf-8")
        (repo / TICKET_DIR / "RT-T-02-bare.md").write_text(bare_ticket, encoding="utf-8")
        (repo / TICKET_DIR / "RT-T-03-anchor.md").write_text(anchor_ticket, encoding="utf-8")

        def staged(*paths: str) -> Callable[[Path], list[str]]:
            return lambda _repo: list(paths)

        checks: list[tuple[str, Outcome, int, tuple[str, ...]]] = [
            (
                "绿路径（块目录文件＋测试文件＋路径引文）",
                run(
                    "RT-T-01a-bookkeeping",
                    repo=repo,
                    staged_provider=staged(
                        "appv2/runtimev2/bookkeeping/__init__.py",
                        "tests/domains/test_v2_bookkeeping.py",
                        "specs/bookkeeping.md",
                    ),
                ),
                0,
                (
                    "绿（3 文件全属本批）",
                    "appv2/runtimev2/bookkeeping/",
                    "Touches modules 行模块名",
                ),
            ),
            (
                "越界红（非本批文件混入暂存区）",
                run(
                    "RT-T-01a-bookkeeping",
                    repo=repo,
                    staged_provider=staged(
                        "appv2/runtimev2/bookkeeping/__init__.py", "web/src/pages/Foo.jsx",
                    ),
                ),
                1,
                ("越界: web/src/pages/Foo.jsx（不属于 RT-T-01a-bookkeeping 授权面）", "解禁二选一"),
            ),
            (
                "空暂存（无事可做＝绿）",
                run("RT-T-01a-bookkeeping", repo=repo, staged_provider=staged()),
                0,
                ("暂存区为空",),
            ),
            (
                "票面不存在（红报错）",
                run("RT-T-99-nope", repo=repo, staged_provider=staged()),
                1,
                ("票面不存在",),
            ),
            (
                "票面无授权面（防裸票过闸）",
                run("RT-T-02-bare", repo=repo, staged_provider=staged("web/src/x.js")),
                1,
                ("票面无授权文件集，禁止派发",),
            ),
            (
                "票面无授权面＋空暂存（仍红——裸票不许过闸）",
                run("RT-T-02-bare", repo=repo, staged_provider=staged()),
                1,
                ("票面无授权文件集，禁止派发",),
            ),
            (
                "--allow-glob 解禁",
                run(
                    "RT-T-01a-bookkeeping",
                    allow_globs=["tests/runtimev2/*"],
                    repo=repo,
                    staged_provider=staged("tests/runtimev2/test_x.py"),
                ),
                0,
                ("绿（1 文件全属本批）", "[豁免] tests/runtimev2/*"),
            ),
            (
                "--extra 目录解禁",
                run(
                    "RT-T-01a-bookkeeping",
                    extra=["tests/runtimev2/"],
                    repo=repo,
                    staged_provider=staged("tests/runtimev2/test_x.py"),
                ),
                0,
                ("绿（1 文件全属本批）", "[额外] tests/runtimev2/"),
            ),
            (
                "--extra 精确文件解禁",
                run(
                    "RT-T-01a-bookkeeping",
                    extra=["tools/foo.py"],
                    repo=repo,
                    staged_provider=staged("tools/foo.py"),
                ),
                0,
                ("绿（1 文件全属本批）",),
            ),
            (
                "票面文件入暂存（红＋显式豁免提示）",
                run(
                    "RT-T-01a-bookkeeping",
                    repo=repo,
                    staged_provider=staged("tickets/v2-refactor/RT-T-01a-bookkeeping.md"),
                ),
                1,
                (
                    "越界: tickets/v2-refactor/RT-T-01a-bookkeeping.md",
                    "--extra tickets/v2-refactor/RT-T-01a-bookkeeping.md",
                ),
            ),
            (
                "带行锚的路径引文（:126-135 剥锚后命中授权面）",
                run(
                    "RT-T-03-anchor",
                    repo=repo,
                    staged_provider=staged("specs/bookkeeping.md"),
                ),
                0,
                ("绿（1 文件全属本批）", "[文件] specs/bookkeeping.md"),
            ),
            (
                "Touches 行文件名／类名不映射成假目录（`RunStore` 类名不授权）",
                run(
                    "RT-T-01a-bookkeeping",
                    repo=repo,
                    staged_provider=staged("appv2/runtimev2/RunStore/x.py"),
                ),
                1,
                ("越界: appv2/runtimev2/RunStore/x.py",),
            ),
        ]

    failed = 0
    for name, outcome, code, needles in checks:
        text = "\n".join(outcome.lines)
        missing = [n for n in needles if n not in text]
        if outcome.code != code or missing:
            failed += 1
            print(f"自测 ✗ {name}：exit={outcome.code}（期望 {code}）缺: {missing}")
            for line in outcome.lines:
                print(f"    | {line}")
        else:
            print(f"自测 ✓ {name}")
    print(f"sweep_guard --self-test：{len(checks) - failed}/{len(checks)} 过")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="施工收票暂存区闸（阶段 5 工序闸）")
    parser.add_argument(
        "--ticket", metavar="票号",
        help="本批票号（tickets/v2-refactor/<票号>.md，可省 .md）",
    )
    parser.add_argument(
        "--extra", action="append", default=[], metavar="PATH",
        help="显式追加授权路径（可多次；目录以 / 结尾——解禁二选一之一）",
    )
    parser.add_argument(
        "--allow-glob", action="append", default=[], metavar="GLOB",
        help="显式豁免 fnmatch 模式（可多次，如 \"tests/runtimev2/*\"）",
    )
    parser.add_argument("--repo", type=Path, default=REPO_ROOT, help="仓根（默认本仓）")
    parser.add_argument("--self-test", action="store_true", help="假 git 输出自测（不碰真仓）")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if not args.ticket:
        parser.error("--ticket 必填（或用 --self-test 跑自测）")
    outcome = run(args.ticket, args.extra, args.allow_glob, repo=args.repo)
    for line in outcome.lines:
        print(line)
    return outcome.code


if __name__ == "__main__":
    sys.exit(main())

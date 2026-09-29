#!/usr/bin/env python3
"""fixture_run.py —— 出厂集 runner（设计案 §3.4，票 01）。

每个 fixtures/<名>/ 目录是一个出厂集：固定输入 + assertions.json 断言集。
断言必须确定性可判（"断言在门口，人在账房"——AI 产出的质量判断不进这里）。

assertions.json 格式（路径均相对该 fixture 目录）：

    {
      "skill": "<名>",
      "description": "...",
      "assertions": [
        {"type": "file-exists", "path": "out/result.md"},
        {"type": "file-contains", "path": "out/result.md", "contains": ["小节甲", "小节乙"]},
        {"type": "file-matches-regex", "path": "out/result.md", "pattern": "^Status: done$"},
        {"type": "file-equals-golden", "path": "out/result.md", "golden": "golden/result.md"},
        {"type": "cmd-succeeds", "cmd": "python3 tools/xxx.py {fixture_dir}/in", "outputContains": ["全过"]},
        {"type": "cmd-fails", "cmd": "python3 tools/xxx.py {fixture_dir}/bad", "outputContains": ["L1"]}
      ]
    }

cmd-* 为本仓实例化新增（All-agent 票 03）：闸脚本对固定输入的确定性断言，
cmd 中 {fixture_dir} 替换为出厂集目录，cwd=仓根，判退出码+输出包含。
纯空目录 = 后续票的占位出厂集（status=pending，不红）；放了输入没写断言 = 红。

双门槛：断言全过才绿；空断言集 = 红（保守，不许空套件亮绿灯）。
整个 fixtures/ 目录不存在或没有任何出厂集 = 警告（status=no-fixtures），
默认退出码 0 但不亮绿；--require-fixtures 把"无出厂集"升级为红。

退出码：0 全过（或无出厂集且未要求）；1 有红；2 用法错误。
--json 输出机读报告供 CI 消费。
"""

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ASSERTION_TYPES = (
    "file-exists",
    "file-contains",
    "file-matches-regex",
    "file-equals-golden",
    "cmd-succeeds",
    "cmd-fails",
)


def run_cmd(fx_dir: Path, assertion: dict) -> tuple[bool, str]:
    """执行命令断言（本仓实例化新增，票 03）：闸脚本对固定输入的退出码+输出断言。

    {"type": "cmd-succeeds"|"cmd-fails", "cmd": "...", "outputContains": ["...", ...]}
    - cmd 里的 {fixture_dir} 占位符替换为出厂集目录绝对路径；cwd = 仓根
      （fixtures/ 的上级，与 CI 的调用基准一致）。
    - cmd-succeeds: 退出码 0 且输出含全部 outputContains；cmd-fails: 退出码非 0
      且输出含全部 outputContains。输出 = stdout + stderr。
    """
    cmd = assertion.get("cmd")
    if not cmd:
        return False, "命令断言缺 cmd 字段"
    cmd = cmd.replace("{fixture_dir}", str(fx_dir))
    try:
        proc = subprocess.run(
            shlex.split(cmd), capture_output=True, text=True, timeout=180,
            cwd=fx_dir.parents[1])
    except (OSError, ValueError) as exc:
        return False, f"命令无法执行: {exc}"
    output = (proc.stdout or "") + (proc.stderr or "")
    label = "成功" if assertion["type"] == "cmd-succeeds" else "失败"
    if assertion["type"] == "cmd-succeeds" and proc.returncode != 0:
        return False, f"命令应{label}但退出码为 {proc.returncode}: {cmd}"
    if assertion["type"] == "cmd-fails" and proc.returncode == 0:
        return False, f"命令应{label}但退出码为 0: {cmd}"
    needles = assertion.get("outputContains", [])
    if isinstance(needles, str):
        needles = [needles]
    missing = [n for n in needles if n not in output]
    if missing:
        return False, f"命令输出缺少内容: {missing}（输出末尾: {output[-300:]!r}）"
    return True, f"命令按预期{label}（退出码 {proc.returncode}）: {cmd}"


def check_assertion(fx_dir: Path, assertion: dict) -> tuple[bool, str]:
    """执行单条断言，返回 (是否通过, 说明)。"""
    atype = assertion.get("type")
    if atype not in ASSERTION_TYPES:
        return False, f"未知断言类型: {atype!r}（合法: {', '.join(ASSERTION_TYPES)}）"
    if atype in ("cmd-succeeds", "cmd-fails"):
        return run_cmd(fx_dir, assertion)
    rel = assertion.get("path")
    if not rel:
        return False, "断言缺 path 字段"
    target = fx_dir / rel
    if atype == "file-exists":
        ok = target.is_file()
        return ok, ("存在" if ok else "文件不存在") + f": {rel}"
    if not target.is_file():
        return False, f"文件不存在: {rel}"
    content = target.read_text(encoding="utf-8")
    if atype == "file-contains":
        needles = assertion.get("contains", [])
        if isinstance(needles, str):
            needles = [needles]
        missing = [n for n in needles if n not in content]
        if missing:
            return False, f"{rel} 缺少内容: {missing}"
        return True, f"{rel} 含全部 {len(needles)} 处指定内容"
    if atype == "file-matches-regex":
        pattern = assertion.get("pattern")
        if not pattern:
            return False, "断言缺 pattern 字段"
        try:
            ok = re.search(pattern, content, re.MULTILINE) is not None
        except re.error as exc:
            return False, f"非法正则 {pattern!r}: {exc}"
        return ok, f"{rel} {'匹配' if ok else '不匹配'} /{pattern}/"
    # file-equals-golden
    golden_rel = assertion.get("golden")
    if not golden_rel:
        return False, "断言缺 golden 字段"
    golden = fx_dir / golden_rel
    if not golden.is_file():
        return False, f"golden 文件不存在: {golden_rel}"
    ok = content == golden.read_text(encoding="utf-8")
    return ok, f"{rel} {'与' if ok else '不与'} {golden_rel} 完全一致"


def run_fixture(fx_dir: Path) -> dict:
    """跑一个出厂集目录，返回该机读报告。"""
    report = {"name": fx_dir.name, "status": "pass", "results": [], "error": None}
    aj = fx_dir / "assertions.json"
    if not aj.is_file():
        if not any(fx_dir.iterdir()):
            # 本仓实例化（票 03）：纯空目录 = 后续票的占位出厂集，pending 不红；
            # 放了输入却没写断言 = 红（空套件不许亮绿灯的镜像约束）。
            report["status"] = "pending"
            report["error"] = "占位目录（无任何文件，断言随所属票补齐）"
            return report
        report["status"] = "fail"
        report["error"] = "缺 assertions.json"
        return report
    try:
        data = json.loads(aj.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report["status"] = "fail"
        report["error"] = f"assertions.json 不是合法 JSON: {exc}"
        return report
    assertions = data.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        report["status"] = "fail"
        report["error"] = "断言集为空（空套件不许亮绿灯）"
        return report
    for a in assertions:
        if not isinstance(a, dict):
            ok, detail = False, f"断言不是对象: {a!r}"
        else:
            ok, detail = check_assertion(fx_dir, a)
        report["results"].append({"assertion": a, "ok": ok, "detail": detail})
        if not ok:
            report["status"] = "fail"
    return report


def run(fixtures_dir: Path, require_fixtures: bool = False) -> dict:
    """跑 fixtures_dir 下全部出厂集，返回总报告。"""
    fixtures = (
        sorted(d for d in fixtures_dir.iterdir() if d.is_dir())
        if fixtures_dir.is_dir()
        else []
    )
    report = {"status": "pass", "fixturesDir": str(fixtures_dir), "fixtures": []}
    if not fixtures:
        report["status"] = "fail" if require_fixtures else "no-fixtures"
        report["warning"] = "无出厂集：fixtures/ 下没有任何出厂集目录（保守：不亮绿灯）"
        return report
    for fx in fixtures:
        sub = run_fixture(fx)
        report["fixtures"].append(sub)
        if sub["status"] == "fail":
            report["status"] = "fail"
    return report


def print_human(report: dict) -> None:
    if report["status"] == "no-fixtures":
        print(f"警告: {report['warning']}")
        return
    for fx in report["fixtures"]:
        mark = {"pass": "PASS", "fail": "FAIL", "pending": "PEND"}[fx["status"]]
        print(f"[{mark}] fixtures/{fx['name']}/")
        if fx["error"] and fx["status"] != "pass":
            print(f"  注: {fx['error']}" if fx["status"] == "pending"
                  else f"  错误: {fx['error']}")
        for r in fx["results"]:
            print(f"  {'ok ' if r['ok'] else 'NG '} {r['detail']}")
    n_pass = sum(1 for f in report["fixtures"] if f["status"] == "pass")
    n_pend = sum(1 for f in report["fixtures"] if f["status"] == "pending")
    tail = f"，{n_pend} 个占位待建" if n_pend else ""
    print(f"出厂集: {n_pass}/{len(report['fixtures'])} 通过{tail}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="出厂集 runner（设计案 §3.4）")
    ap.add_argument("--root", default=None,
                        help="仓根（默认取本脚本的上级目录），fixtures 取其下 fixtures/")
    ap.add_argument("--fixtures-dir", default=None, help="直接指定 fixtures 目录")
    ap.add_argument("--require-fixtures", action="store_true",
                    help="把「无出厂集」从警告升级为红")
    ap.add_argument("--json", action="store_true", help="机读 JSON 输出（供 CI 消费）")
    args = ap.parse_args(argv)

    if args.fixtures_dir:
        fixtures_dir = Path(args.fixtures_dir)
    else:
        root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
        fixtures_dir = root / "fixtures"
    report = run(fixtures_dir, require_fixtures=args.require_fixtures)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0 if report["status"] in ("pass", "no-fixtures") else 1


if __name__ == "__main__":
    sys.exit(main())

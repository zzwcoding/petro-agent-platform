#!/usr/bin/env python3
"""onboard_check —— 新域接入 checklist（票 77）。

背景：bohai→pkb→his→hr 四域接入暴露「加域要人记 N 处」的系统性问题——AGENTS.md
锚点与协议①⑥、smoke 文案、信号路由表、体检留痕、L5 评分面、审记、exports
全靠人记忆逐处补。本工具把接入面收敛为一条命令：逐域检查（项清单见
check_domain，仓级见 check_repo），硬缺口 exit 1，软警告不阻塞。确定性、
无 LLM、只读（审记核验复用 review_gate verify_record 状态机，不复制逻辑）。

用法:
    python3 tools/onboard_check.py             # 全域（ontology/*/manifest.json 枚举）
    python3 tools/onboard_check.py bohai his   # 指定域
退出码: 0 硬面齐 / 1 有硬缺口（manifest/schema/devkit）/ 2 用法错误
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent

import review_gate  # noqa: E402  同目录模块（审记状态机唯一真源）


def list_domains(root: Path) -> "list[str]":
    """域清单唯一枚举源（与 meta_probe --list-domains 同口径）。"""
    onto = root / "ontology"
    if not onto.is_dir():
        return []
    return sorted(d.parent.name for d in onto.glob("*/manifest.json"))


def _schema_single_domain(root: Path, dname: str) -> "tuple[bool, str]":
    """对单域跑 schema_check（L1–L4），返回 (是否全绿, 摘要)。"""
    proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "schema_check.py"),
         str(root / "ontology" / dname)],
        capture_output=True, text=True, timeout=180, cwd=str(root))
    lines = (proc.stdout or proc.stderr or "").strip().splitlines()
    summary = lines[-1].strip() if lines else ""
    return proc.returncode == 0, (summary or f"exit={proc.returncode}")


def _file_contains(path: Path, token: str) -> bool:
    if not path.is_file():
        return False
    return token in path.read_text(encoding="utf-8", errors="ignore")


def _grep_glob(dirpath: Path, pattern: str, token: str) -> "list[str]":
    if not dirpath.is_dir():
        return []
    # 只收文件：金集未来出现子目录时 glob('*') 会带出目录，read_text 会炸
    # （票 77 审查 P3-4）
    return [p.name for p in sorted(dirpath.glob(pattern))
            if p.is_file()
            and token in p.read_text(encoding="utf-8", errors="ignore")]


def _review_item(root: Path, target: Path, label: str) -> dict:
    rpath = review_gate.review_path_for(target, root / "exports" / "reviews")
    _code, status, reason, _rec, _n = review_gate.verify_record(target, rpath)
    return {"item": label, "severity": "soft",
            "status": "pass" if status == "pass" else "warn",
            "detail": f"{status}: {reason.splitlines()[0]}"}


def check_domain(root: Path, dname: str) -> "list[dict]":
    """单域十项检查。硬项: manifest/语义闸/devkit；其余软项只警不拦。"""
    items: list[dict] = []

    def add(item, severity, status, detail):
        items.append({"item": item, "severity": severity,
                      "status": status, "detail": detail})

    # 1 manifest 在场且 domain=目录名（硬）
    mpath = root / "ontology" / dname / "manifest.json"
    if not mpath.is_file():
        add("manifest 在场", "hard", "fail",
            f"缺 ontology/{dname}/manifest.json")
    else:
        try:
            mdata = json.loads(mpath.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            mdata = None
            add("manifest 在场", "hard", "fail", f"JSON 不可解析: {exc}")
        if mdata is not None:
            missing = [k for k in ("domain", "profile", "schemaVersion")
                       if k not in mdata]
            if missing:
                add("manifest 在场", "hard", "fail", f"缺必备键 {missing}")
            elif mdata.get("domain") != dname:
                add("manifest 在场", "hard", "fail",
                    f"domain={mdata.get('domain')!r} 与目录名 {dname!r} 不一致")
            else:
                add("manifest 在场", "hard", "pass",
                    f"profile={mdata.get('profile')} "
                    f"schemaVersion={mdata.get('schemaVersion')}")

    # 2 语义闸单域绿（硬）
    ok, summary = _schema_single_domain(root, dname)
    add("语义闸单域绿（L1–L4）", "hard", "pass" if ok else "fail", summary)

    # 3–5 exports 面
    devkit_md = root / "exports" / "devkit" / dname / "devkit.md"
    devkit_json = root / "exports" / "devkit" / dname / "devkit.json"
    skill_md = root / "exports" / "skillpkg" / dname / "SKILL.md"
    add("devkit 导出", "hard", "pass" if devkit_md.is_file() else "fail",
        f"exports/devkit/{dname}/devkit.md" if devkit_md.is_file()
        else f"缺 exports/devkit/{dname}/devkit.md（先跑 app_pack_gen 再人审锚定）")
    add("devkit.json 伴生", "soft", "pass" if devkit_json.is_file() else "warn",
        "在场" if devkit_json.is_file()
        else f"缺 exports/devkit/{dname}/devkit.json")
    add("skillpkg 导出", "soft", "pass" if skill_md.is_file() else "warn",
        "在场" if skill_md.is_file()
        else f"缺 exports/skillpkg/{dname}/SKILL.md"
             f"（豁免域如 pkb 属正常，须有豁免裁决留痕）")

    # 6 审记（逐在场生成物；pending/失效照实报，软项）
    for t in (devkit_md, skill_md):
        if t.is_file():
            items.append(_review_item(root, t, f"审记[{t.name}]"))

    # 7 体检留痕
    hits = _grep_glob(root / "docs" / "meta", "体检-*.md", dname)
    add("体检留痕", "soft", "pass" if hits else "warn",
        f"{len(hits)} 篇提及「{dname}」" if hits
        else f"docs/meta/体检-*.md 无一提及「{dname}」（跑 meta_probe 逐域留痕）")

    # 8 L5 评分面词面（软；评分面未建的域按观察项挂账）
    # 金集真身在 fixtures/semantic-service/expected-answers/（l5-scoring/expected
    # 只做出厂占位）；词面大小写各查一次（金集里 ID 大写、叙述小写都有）。
    l5_hits: "list[str]" = []
    for hits_dir, pat in (((root / "fixtures" / "semantic-service"
                            / "expected-answers"), "**/*"),
                          (root / "fixtures" / "l5-scoring" / "expected",
                           "**/*"),
                          (root / "docs" / "meta", "l5-评分-*.md")):
        for token in (dname, dname.upper()):
            # 挂账说明是「缺席证据」（记载该域 L5 欠账），不算评分面在册
            l5_hits += [h for h in _grep_glob(hits_dir, pat, token)
                        if "挂账" not in h]
    add("L5 评分面词面", "soft", "pass" if l5_hits else "warn",
        f"{len(l5_hits)} 处提及「{dname}」" if l5_hits
        else "金集（semantic-service/expected-answers、l5-scoring/expected）"
             f"与 docs/meta/l5-评分-*.md 均无「{dname}」词面"
             "（评分面未建属观察项，须挂账）")

    # 9–11 文档面三处（smoke 文案 / AGENTS 锚点 / 信号路由表）
    add("smoke 文案", "soft", "pass" if _file_contains(
            root / "tools" / "mcp_smoke_client.py", dname) else "warn",
        "mcp_smoke_client.py 提及" if _file_contains(
            root / "tools" / "mcp_smoke_client.py", dname)
        else "mcp_smoke_client.py 无该域词面（多域示例/epilog 补一句）")
    add("AGENTS.md 域行", "soft", "pass" if _file_contains(
            root / "AGENTS.md", dname) else "warn",
        "锚点面提及" if _file_contains(root / "AGENTS.md", dname)
        else "AGENTS.md 无该域词面（目录地图/锚点段补）")
    add("信号路由表", "soft", "pass" if _file_contains(
            root / "policies" / "signal-routing.json", dname) else "warn",
        "提及" if _file_contains(root / "policies" / "signal-routing.json", dname)
        else "policies/signal-routing.json 无该域词面（词汇面是否收编待裁）")
    return items


def check_repo(root: Path) -> "list[dict]":
    """仓级检查（票 82）：全域再制件防陈旧——capability-manifest 随域增加
    必过期，过去靠出厂集 fixture 的隔层红灯暴露（病灶与红灯隔三层）。
    ontology 无 schema/ 注册表（临时夹具）时静默跳过：配置错不冒充软警告。"""
    onto = root / "ontology"
    if not (onto / "schema").is_dir():
        return []
    manifest = root / "exports" / "mcp" / "capability-manifest.json"
    proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "mcp_manifest_gen.py"),
         str(onto), "--check", str(manifest)],
        capture_output=True, text=True, timeout=180)
    lines = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = lines[-1].strip() if lines else f"exit={proc.returncode}"
    return [{"item": "capability-manifest 防陈旧", "severity": "soft",
             "status": "pass" if proc.returncode == 0 else "warn",
             "detail": (detail if proc.returncode == 0 else
                        f"{detail}——跑 mcp_manifest_gen.py {onto} --out "
                        f"{manifest} 再制（票 82 仓级项）")}]


def run(root: Path, domains: "list[str] | None" = None) -> dict:
    root = root.resolve()
    names = list(domains) if domains else list_domains(root)
    report: dict = {"root": str(root), "domains": {}, "hardFails": 0,
                    "warns": 0}
    for d in names:
        items = check_domain(root, d)
        report["domains"][d] = items
        report["hardFails"] += sum(1 for i in items
                                   if i["severity"] == "hard"
                                   and i["status"] == "fail")
        report["warns"] += sum(1 for i in items if i["status"] == "warn")
    report["repoChecks"] = check_repo(root)
    report["warns"] += sum(1 for i in report["repoChecks"]
                           if i["status"] == "warn")
    return report


def print_human(report: dict) -> None:
    mark = {"pass": "✔", "fail": "✘", "warn": "⚠"}
    for d, items in report["domains"].items():
        print(f"\n── {d} ──")
        for i in items:
            print(f" {mark[i['status']]} [{i['severity']}] "
                  f"{i['item']} — {i['detail']}")
    if report.get("repoChecks"):
        print("\n── 仓级 ──")
        for i in report["repoChecks"]:
            print(f" {mark[i['status']]} [{i['severity']}] "
                  f"{i['item']} — {i['detail']}")
    print(f"\nonboard_check: 硬缺口 {report['hardFails']}，软警告 "
          f"{report['warns']}"
          + ("—— 有硬缺口，接入未齐" if report["hardFails"] else "——硬面齐"
             if report["domains"] else "——无域可查（ontology/ 下无 manifest）"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="新域接入 checklist（票 77）：逐域十项，硬缺口 exit 1")
    ap.add_argument("domains", nargs="*",
                    help="域名单（缺省=ontology/ 全域枚举）")
    ap.add_argument("--root", default=None, help="仓根（默认取本脚本的上级目录）")
    ap.add_argument("--json", action="store_true", help="机读 JSON 输出")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else REPO_ROOT
    report = run(root, args.domains or None)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 1 if report["hardFails"] else 0


if __name__ == "__main__":
    sys.exit(main())

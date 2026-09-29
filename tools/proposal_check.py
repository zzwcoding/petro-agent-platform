#!/usr/bin/env python3
"""proposal_check.py —— 提案池确定性检查（All-agent 票 18；AC 真源=tickets/18 AC 表）。

契约: proposal_check.py <提案目录> [--root <仓根>] [--json]

对目录内全部 PROP-*.md 提案做四类确定性检查（零 LLM，只读）：

  ① proposal-schema   必备字段与枚举值自检。YAML 头（首行 `---` 起至下一个 `---`
                      行）必备七字段：id / title / status / source-signal(kind,ref) /
                      target(model,element) / change / rationale；枚举：status ∈
                      draft|open|accepted|rejected，kind ∈ 拒答|疑点|对账缺口|监督|交互，
                      change ∈ add|modify|deprecate；id 形如 PROP-<域>-<NNN>（域为
                      字母数字、NNN 恰三位数字）；同池 id 不得重复；title/rationale/
                      ref/model/element 须非空字符串。YAML 头缺失/未闭合/不可解析/
                      非映射同归此类。schema 红的文件不再进 ②③④（红因纯净，脏数据
                      不进池内比对，避免连环误报）。

  ② proposal-target   target 存在性（**仅判 draft/open**，票 56：已裁决提案的靶在场
                      =实施完成的预期态，不判——A 线 PROP-006 实弹发现的盲区）：
                      change=modify/deprecate → target.element 必须
                      已在 ontology/ 真域；change=add → 必须不存在（防重复建，要改
                      既有元素应走 modify）。元素判定口径照票 04 图索引：定义键
                      id/*Id（ref 键除外）且值为字符串、且带 ontology/schema/
                      model-deps.json idPrefixes 已登记前缀（前缀即类型标签）——
                      本工具独立实现该口径，不 import graph_index（保持 stdlib+
                      PyYAML、零耦合；单测不打真实仓）。未登记前缀的 ID 判「不存在」
                      （无类型语义即无从谈起存在），前缀登记属 schema 演进面，不在
                      本工具判定面。ref 键 = model-deps.json refKeys ∪ *Ref/*Refs
                      后缀（引用不产生定义，悬空引用不能被 modify）。

  ③ proposal-conflict  池内冲突：同 target.element 的两个 status=open 提案 change
                      类型矛盾（两个不同枚举值即矛盾，如 modify vs deprecate；
                      add vs modify 亦矛盾）。同值重复提案不判（属人裁决面）；
                      draft 与已裁决（accepted/rejected）提案不参战。

  ④ proposal-evidence  source-signal.ref 证据文件必须存在：先剥 #锚点 后缀（锚点
                      容许、不校验内容），再依次按 仓根相对 → 提案目录相对 解析，
                      两处皆无 = 红；绝对路径与只剩锚点的空路径 = 红（证据必须
                      随仓/随池可追溯）。

只解析 PROP-*.md；目录内其他 md 文件（对账 README、证据附件）跳过并在报告里
计数，不解析不报错。本工具管「提案结构可机检的部分」；提案该不该提、矛盾双方
谁对——裁决权在人（业务语义循环：自动化止于提案）。

退出码：0 全过；1 有违规；2 用法/配置错误（缺参、提案目录不存在、--root 下无
ontology/ 或缺 model-deps.json、ontology YAML 不可解析——部分元素集=说谎的
元素集，拒绝判定）。
--json 输出机读报告（status/dir/root/proposals/skippedMd/violations）供 CI 消费。

字段定义的人读镜像：references/proposal-format.md（与本章一字不差对齐，改一处
必改另一处）；出厂集：fixtures/proposal-pool/（AC1–6，fixture_run cmd cwd=仓根，
真域从仓根解析）。
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

PROP_GLOB = "PROP-*.md"
PROP_ID_RE = re.compile(r"^PROP-[A-Za-z0-9]+-[0-9]{3}$")
STATUSES = ("draft", "open", "accepted", "rejected")
KINDS = ("拒答", "疑点", "对账缺口", "监督", "交互")
CHANGES = ("add", "modify", "deprecate")
REQUIRED_FIELDS = ("id", "title", "status", "source-signal", "target",
                   "change", "rationale")

YAML_EXTS = (".yaml", ".yml")


class ConfigError(ValueError):
    """用法/配置错误（退出码 2）。"""


# ---------- ① schema：YAML 头解析与字段自检 ----------


def parse_front_matter(path: Path) -> tuple[dict | None, str | None]:
    """解析 PROP 文件的 YAML 头。返回 (映射, None) 或 (None, 红因说明)。"""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return None, f"提案文件不是 UTF-8 文本: {exc}"
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "缺 YAML 头（首行须为 ---）"
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return None, "YAML 头未闭合（缺收尾 --- 行）"
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        return None, f"YAML 头不可解析: {exc}"
    if not isinstance(data, dict):
        return None, "YAML 头为空或不是映射"
    return data, None


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def schema_violations(fname: str, data: dict,
                      seen_ids: dict[str, str]) -> list[tuple[str, str]]:
    """单份提案的 schema 违规列表 [(message, none)]；seen_ids 记 id→先到文件。"""
    bad: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            bad.append(f"缺必备字段 `{field}`")
    if bad:  # 缺字段时不再逐字段深挖（缺什么报什么，红因已定）
        return bad

    pid = data["id"]
    if not isinstance(pid, str) or not PROP_ID_RE.match(pid):
        bad.append(f"id「{pid}」不符命名 PROP-<域>-<NNN>"
                   f"（NNN 恰三位数字）")
    elif pid in seen_ids:
        bad.append(f"id「{pid}」与 {seen_ids[pid]} 重复（同池提案 id 不得重复）")
    else:
        seen_ids[pid] = fname

    if not _nonempty_str(data["title"]):
        bad.append("title 须为非空字符串")
    if data["status"] not in STATUSES:
        bad.append(f"status 值「{data['status']}」非法"
                   f"（合法值: {'/'.join(STATUSES)}）")
    if data["change"] not in CHANGES:
        bad.append(f"change 值「{data['change']}」非法"
                   f"（合法值: {'/'.join(CHANGES)}）")
    if not _nonempty_str(data["rationale"]):
        bad.append("rationale 须为非空字符串")

    signal = data["source-signal"]
    if not isinstance(signal, dict):
        bad.append("source-signal 须为映射（kind/ref 两键）")
    else:
        if signal.get("kind") not in KINDS:
            bad.append(f"source-signal.kind 值「{signal.get('kind')}」非法"
                       f"（合法值: {'/'.join(KINDS)}）")
        if not _nonempty_str(signal.get("ref")):
            bad.append("source-signal.ref 须为非空字符串（证据路径[#锚点]）")

    target = data["target"]
    if not isinstance(target, dict):
        bad.append("target 须为映射（model/element 两键）")
    else:
        if not _nonempty_str(target.get("model")):
            bad.append("target.model 须为非空字符串（模型标识，如 M1/M3）")
        if not _nonempty_str(target.get("element")):
            bad.append("target.element 须为非空字符串（元素 ID）")
    return bad


# ---------- ② target：真域元素集（口径照票 04 图索引，独立实现） ----------


def load_id_prefixes(ontology_root: Path) -> tuple[dict, set]:
    """读 ontology/schema/model-deps.json，返回 (idPrefixes, refKeys)。"""
    deps = ontology_root / "schema" / "model-deps.json"
    if not deps.is_file():
        raise ConfigError(f"缺 ontology/schema/model-deps.json（元素存在性"
                          f"判定需要已登记前缀与 ref 键清单）: {deps}")
    try:
        data = json.loads(deps.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"model-deps.json 不是合法 JSON: {deps}: {exc}")
    prefixes = data.get("idPrefixes")
    if not isinstance(prefixes, dict) or not prefixes:
        raise ConfigError(f"model-deps.json 缺非空 idPrefixes 映射: {deps}")
    return prefixes, set(data.get("refKeys", []))


def _is_ref_key(key: str, ref_keys: set) -> bool:
    return key in ref_keys or key.endswith("Ref") or key.endswith("Refs")


def collect_element_ids(ontology_root: Path, prefixes: dict,
                        ref_keys: set) -> set[str]:
    """收集真域全部元素 ID：定义键 id/*Id、非 ref 键、字符串值、带已登记前缀。

    同一映射取首个命中键（同图索引口径）；ontology YAML 不可解析 = 配置错误
    （部分元素集会制造假「不存在」，拒绝判定）。
    """

    def def_id_of(mapping: dict) -> str | None:
        for key, value in mapping.items():
            if not (isinstance(key, str)
                    and (key == "id" or key.endswith("Id"))):
                continue
            if _is_ref_key(key, ref_keys) or not isinstance(value, str):
                continue
            if any(value.startswith(pre) for pre in prefixes):
                return value
        return None

    def walk(node, ids: set) -> None:
        if isinstance(node, dict):
            did = def_id_of(node)
            if did:
                ids.add(did)
            for value in node.values():
                walk(value, ids)
        elif isinstance(node, list):
            for item in node:
                walk(item, ids)

    ids: set[str] = set()
    for path in sorted(ontology_root.rglob("*")):
        if not path.is_file() or path.suffix not in YAML_EXTS:
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            raise ConfigError(f"ontology YAML 不可解析（拒绝以部分元素集判定"
                              f"存在性）: {path}: {exc}")
        if data:
            walk(data, ids)
    return ids


# ---------- ④ evidence：证据路径解析 ----------


def evidence_missing(root: Path, pool_dir: Path, ref: str) -> str | None:
    """证据不在档时返回红因说明；在档返回 None。#锚点剥离不校验。"""
    path_part = ref.split("#", 1)[0].strip()
    if not path_part:
        return f"证据路径只剩锚点没有文件路径: {ref!r}"
    if Path(path_part).is_absolute():
        return f"证据路径须为仓根相对或提案目录相对，不许绝对路径: {path_part}"
    for base in (root, pool_dir):
        if (base / path_part).is_file():
            return None
    return (f"证据文件不存在: {path_part}"
            f"（已试: 仓根相对、提案目录相对；#锚点后缀已剥离）")


# ---------- 主流程 ----------


def run(pool_dir: Path, root: Path) -> dict:
    """跑一个提案池目录，返回机读报告。配置不可用抛 ConfigError。"""
    pool_dir = pool_dir.resolve()
    root = root.resolve()
    if not pool_dir.is_dir():
        raise ConfigError(f"用法错误: 提案目录不存在或不是目录: {pool_dir}")
    ontology_root = root / "ontology"
    if not ontology_root.is_dir():
        raise ConfigError(f"仓根下没有 ontology/ 目录（--root 指错？）: {root}")
    prefixes, ref_keys = load_id_prefixes(ontology_root)
    # 元素集先建（配置错误优先于逐文件违规）：ontology 里有不可解析的 YAML 时
    # 拒绝判定——部分元素集会制造假「不存在」（说谎的元素集，同图索引红线）。
    elements = collect_element_ids(ontology_root, prefixes, ref_keys)

    all_files = sorted(p for p in pool_dir.rglob("*") if p.is_file())
    prop_files = [p for p in all_files if p.name.startswith("PROP-")
                  and p.name.endswith(".md")]
    skipped_md = [p for p in all_files
                  if p.suffix == ".md" and p not in prop_files]
    violations: list[dict] = []

    def add(code: str, file: str, message: str) -> None:
        violations.append({"code": code, "file": file, "message": message})

    # ① schema（逐文件；红的文件不进后续检查）
    valid: list[tuple[str, dict]] = []
    seen_ids: dict[str, str] = {}
    for path in prop_files:
        fname = path.relative_to(pool_dir).as_posix()
        data, err = parse_front_matter(path)
        if err is not None:
            add("proposal-schema", fname, err)
            continue
        bad = schema_violations(fname, data, seen_ids)
        if bad:
            for message in bad:
                add("proposal-schema", fname, message)
            continue
        valid.append((fname, data))

    # ② target + ④ evidence（逐份有效提案）
    for fname, data in valid:
        element = data["target"]["element"]
        change = data["change"]
        # target 存在性只判 draft/open（票 56：已裁决提案的靶在场=实施完成的预期态，
        # 一刀切会把每份被采纳的 add 提案误报成红——A 线 PROP-006 实弹发现）；
        # ④ evidence 维持全状态（证据链终身有效）。
        if data["status"] in ("draft", "open"):
            if change == "add":
                if element in elements:
                    add("proposal-target", fname,
                        f"add 的靶元素在 ontology/ 真域已存在（要改既有元素应走 "
                        f"modify）: {element}")
            elif element not in elements:
                add("proposal-target", fname,
                    f"{change} 的靶元素在 ontology/ 真域不存在: {element}")
        missing = evidence_missing(root, pool_dir,
                                   data["source-signal"]["ref"])
        if missing is not None:
            add("proposal-evidence", fname, missing)

    # ③ conflict（池内两两比对，只看 open）
    open_props = [(fname, data) for fname, data in valid
                  if data["status"] == "open"]
    open_props.sort(key=lambda item: item[0])
    for i, (fa, da) in enumerate(open_props):
        for fb, db in open_props[i + 1:]:
            if da["target"]["element"] != db["target"]["element"]:
                continue
            ca, cb = da["change"], db["change"]
            if ca != cb:
                add("proposal-conflict", f"{fa} × {fb}",
                    f"同靶元素 {da['target']['element']} 的两个 open 提案 "
                    f"change 矛盾: {ca}（{fa}） vs {cb}（{fb}）——闸只报矛盾"
                    f"不判对错，裁决在人")

    return {
        "status": "fail" if violations else "pass",
        "dir": str(pool_dir),
        "root": str(root),
        "proposals": len(prop_files),
        "skippedMd": len(skipped_md),
        "violations": violations,
    }


def print_human(report: dict) -> None:
    print(f"提案池检查 proposal_check — 目录: {report['dir']}"
          f"（仓根: {report['root']}）")
    print(f"解析提案 {report['proposals']} 份；"
          f"跳过非提案 md 文件 {report['skippedMd']} 个"
          f"（只解析 {PROP_GLOB}）")
    for v in report["violations"]:
        print(f"[{v['code']}] {v['file']}: {v['message']}")
    if not report["violations"]:
        print("结论: 全过")
    else:
        print(f"结论: {len(report['violations'])} 处违规")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="proposal_check",
        description="提案池确定性检查（票 18）：schema 字段/枚举、target 存在性、"
                    "同靶 open 提案冲突、证据文件在档；只解析 PROP-*.md，"
                    "退出码 0 全过 / 1 有违规 / 2 用法配置错误")
    ap.add_argument("proposal_dir", help="提案池目录（工具解析其下 PROP-*.md）")
    ap.add_argument("--root", default=None,
                    help="仓根（默认取本脚本的上级目录；ontology/ 与证据仓根"
                         "相对路径以此为基准）")
    ap.add_argument("--json", action="store_true", help="机读 JSON 输出")
    args = ap.parse_args(argv)
    root = Path(args.root) if args.root else \
        Path(__file__).resolve().parent.parent
    try:
        report = run(Path(args.proposal_dir), root)
    except ConfigError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

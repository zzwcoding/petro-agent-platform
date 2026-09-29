#!/usr/bin/env python3
"""graph_index.py —— 图索引构建器（All-agent 票 04；spec: specs/graph_index.md AC1–6）。

对给定 ontology 目录从模型 YAML **全量重建**一张纯内存引用图（Git 是真源，图是
派生物；每次启动全量重建，禁止持久化缓存成权威——本脚本只读不写，无任何缓存文件）。

图的构成（ID/ref 约定见 ontology/schema/schema.md §2，机读真源 model-deps.json）：
  节点 = 元素 ID 带已登记前缀的定义（定义键 id/*Id 且非 ref 键；前缀即类型标签，
         model 取 idPrefixes 前缀映射；同 ID 重复定义取先出现者，冲突归语义闸管）。
  边   = ref 字段（refKeys 全集 ∪ *Ref/*Refs 后缀 ∪ model-deps.json edges 登记
         的 ref 字段——如 M3.reusedBy 只在 edges 登记）指向的带已登记前缀 ID，
         source=引用方（按 YAML 嵌套取最近一个带 ID 的祖先元素），边挂 ref 字段名；
         悬空引用照记不删（图反映声明，悬空判定归 tools/schema_check.py 语义闸）。

CLI: python3 tools/graph_index.py <ontology目录> --query <id> [--closure N] [--impact] [--json]
  --query <id>  查询存在的 ID → 返回该节点及属性（AC2）
  --closure N   沿 ref 正向走 N 跳的引用闭包（下游节点集，BFS，含经 ref 连出的下游）（AC3）
  --impact      沿依赖边**反向**走到底，返回受影响节点集（依赖方 ← 被改方）（AC4）
  --json        机读 JSON 输出（供 CI/skill 消费）

查询不存在的 ID 明确报「未找到」不猜（AC5）。--closure N 要求 N>=1。
YAML 不可解析/缺 model-deps.json/无任何域 = 拒绝建图（部分图=说谎的图），
不做部分索引。schema 合法性（L1–L4）归 tools/schema_check.py，本脚本不重复判定。

依赖：Python3 stdlib + PyYAML（safe 装载）。
退出码：0 命中；1 未找到；2 配置/用法错误。
"""

import argparse
import json
import os
import sys
from collections import deque
from pathlib import Path

import yaml

# ---------- 带行号的 YAML 装载（safe、只读；行号用于节点溯源） ----------


class MDict(dict):
    """带行号的映射（line = 首键所在行，1 起）。"""

    line = 0


class MList(list):
    """带行号的序列。"""

    line = 0


class LineLoader(yaml.SafeLoader):
    """SafeLoader + 容器行号标注。"""


def _construct_map(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping = MDict()
    yield mapping
    for k_node, v_node in node.value:
        key = loader.construct_object(k_node, deep=deep)
        value = loader.construct_object(v_node, deep=deep)
        mapping[key] = value
    mapping.line = node.start_mark.line + 1


def _construct_seq(loader, node, deep=False):
    seq = MList()
    yield seq
    seq.extend(loader.construct_sequence(node, deep=deep))
    seq.line = node.start_mark.line + 1


LineLoader.add_constructor("tag:yaml.org,2002:map", _construct_map)
LineLoader.add_constructor("tag:yaml.org,2002:seq", _construct_seq)


def load_yaml(path: Path):
    """解析 YAML；语法错误/顶层非映射抛 ValueError（拒绝建图，不做部分索引）。"""
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.load(fh, Loader=LineLoader)
    except yaml.MarkedYAMLError as exc:
        mark = exc.problem_mark or exc.context_mark
        line = mark.line + 1 if mark else 0
        raise ValueError(f"{path}:{line} YAML 语法错误: {exc.problem or exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"{path} YAML 解析失败: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{path} 无法读取: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} 顶层必须是映射（模型文件约定）")
    return data


# ---------- 目录/配置解析（与 schema_check 同约定） ----------


def resolve_schema_dir(target: Path) -> Path | None:
    for cand in (target / "schema", target.parent / "schema"):
        if cand.is_dir():
            return cand
    return None


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path} 不存在（图索引必配 model-deps.json）") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{path} 不是合法 JSON: {exc}") from exc


def discover_domains(target: Path) -> list[Path]:
    """域目录 = 含 manifest.json 的目录；target 本身是域则单域。"""
    if (target / "manifest.json").is_file():
        return [target]
    return sorted(sub for sub in target.iterdir()
                  if sub.is_dir() and sub.name != "schema"
                  and (sub / "manifest.json").is_file())


def model_files(domain: Path) -> list[Path]:
    return sorted(p for p in domain.rglob("*")
                  if p.is_file() and p.suffix in (".yaml", ".yml"))


# ---------- ID/ref 判定（前缀即类型标签，schema.md §2） ----------


def is_ref_key(key: str, ref_keys: set) -> bool:
    return key in ref_keys or key.endswith("Ref") or key.endswith("Refs")


def id_model_of(value: str, prefix2model: dict) -> str | None:
    for prefix, model in prefix2model.items():
        if value.startswith(prefix):
            return model
    return None


def iter_ref_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_ref_strings(item)


# ---------- 图 ----------


class Graph:
    """纯内存引用图：nodes[id] → 节点记录；edges = [{src, field, dst}]（排序去重）。

    边的方向 = ref 的引用方向（依赖方向）：src 引用 dst。closure 沿正向，
    impact 沿反向（受影响者 = 能沿 ref 正向走到被改节点的一切节点）。
    """

    def __init__(self, prefix2model: dict):
        self.prefix2model = prefix2model
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self._forward: dict[str, list[tuple[str, str]]] = {}
        self._reverse: dict[str, list[tuple[str, str]]] = {}

    def add_node(self, node_id: str, domain: str, path: Path, element) -> None:
        if node_id in self.nodes:  # 同 ID 重复定义取先出现者（冲突归语义闸）
            return
        self.nodes[node_id] = {
            "id": node_id,
            "model": id_model_of(node_id, self.prefix2model),
            "domain": domain,
            "file": str(path),
            "line": getattr(element, "line", 0),
            "element": element,
        }

    def add_edge(self, src: str, field: str, dst: str) -> None:
        self.edges.append({"src": src, "field": field, "dst": dst})

    def finalize(self) -> None:
        seen, unique = set(), []
        for edge in sorted(self.edges,
                           key=lambda e: (e["src"], e["field"], e["dst"])):
            key = (edge["src"], edge["field"], edge["dst"])
            if key not in seen:
                seen.add(key)
                unique.append(edge)
        self.edges = unique
        for edge in self.edges:
            self._forward.setdefault(edge["src"], []).append(
                (edge["field"], edge["dst"]))
            self._reverse.setdefault(edge["dst"], []).append(
                (edge["field"], edge["src"]))

    def forward_edges(self, node_id: str) -> list[tuple[str, str]]:
        return self._forward.get(node_id, [])

    def reverse_edges(self, node_id: str) -> list[tuple[str, str]]:
        return self._reverse.get(node_id, [])

    def model_of(self, node_id: str) -> str | None:
        """节点的模型标签；悬空 ID 按前缀推断（图反映声明）。"""
        node = self.nodes.get(node_id)
        return node["model"] if node else id_model_of(node_id, self.prefix2model)

    def stats(self) -> dict:
        return {"nodes": len(self.nodes), "edges": len(self.edges)}


def _index_file(graph: Graph, data, domain: str, path: Path,
                ref_keys: set) -> None:
    """一遍走 YAML 树：注册定义节点 + 按最近 ID 祖先挂 ref 边。"""

    def def_id_of(mapping) -> str | None:
        for key, value in mapping.items():
            if not (isinstance(key, str) and (key == "id" or key.endswith("Id"))):
                continue
            if is_ref_key(key, ref_keys) or not isinstance(value, str):
                continue
            if id_model_of(value, graph.prefix2model):
                return value
        return None

    def walk(node, anchor: str | None) -> None:
        if isinstance(node, dict):
            my_id = def_id_of(node)
            if my_id:
                graph.add_node(my_id, domain, path, node)
                anchor = my_id  # 自身 ref 挂自己（如 reusedBy 挂规则自身）
            for key, value in node.items():
                if anchor and isinstance(key, str) and is_ref_key(key, ref_keys):
                    for ref in iter_ref_strings(value):
                        if isinstance(ref, str) and \
                                id_model_of(ref, graph.prefix2model):
                            graph.add_edge(anchor, key, ref)
                walk(value, anchor)
        elif isinstance(node, list):
            for item in node:
                walk(item, anchor)

    walk(data, None)


def build_graph(target: Path) -> Graph:
    """从 ontology 目录全量重建内存图（AC1）。配置/内容不可用抛 ValueError。"""
    target = target.resolve()
    if not target.is_dir():
        raise ValueError(f"目标目录不存在: {target}")
    schema_dir = resolve_schema_dir(target)
    if schema_dir is None:
        raise ValueError(f"{target} 及其上级都没有 schema/ 目录（缺 model-deps.json）")
    deps = load_json(schema_dir / "model-deps.json")
    prefix2model = deps.get("idPrefixes")
    ref_keys = set(deps.get("refKeys", []))
    # ref 扫描键取并集：refKeys ∪ edges 登记字段（如 M3.reusedBy 只在 edges 登记）。
    # 图求完整（影响分析不漏通道）；越白名单的裁决权在语义闸，不在图。
    ref_keys |= {edge["field"] for edge in deps.get("edges", [])
                 if isinstance(edge, dict) and isinstance(edge.get("field"), str)}
    if not isinstance(prefix2model, dict) or not prefix2model:
        raise ValueError(f"{schema_dir / 'model-deps.json'} 缺 idPrefixes"
                         f"（ID 前缀→模型映射）")
    domains = discover_domains(target)
    if not domains:
        raise ValueError(f"{target} 下未找到任何域（域目录须含 manifest.json）")
    graph = Graph(prefix2model)
    for domain in domains:
        manifest = load_json(domain / "manifest.json")
        dname = manifest.get("domain", domain.name)
        for path in model_files(domain):
            data = load_yaml(path)
            _index_file(graph, data, dname, path, ref_keys)
    graph.finalize()
    return graph


# ---------- 查询 ----------


def closure(graph: Graph, start: str, max_hops: int) -> list[dict]:
    """沿 ref 正向 BFS N 跳（AC3）：下游节点集（BFS 发现序，确定；首达即最少跳）。"""
    out, seen = [], {start}
    queue = deque([(start, 0, [start])])
    while queue:
        node_id, hops, path = queue.popleft()
        if hops >= max_hops:
            continue
        for field, dst in graph.forward_edges(node_id):
            if dst in seen:
                continue
            seen.add(dst)
            out.append({"id": dst, "model": graph.model_of(dst),
                        "hops": hops + 1, "via": field, "path": path + [dst]})
            queue.append((dst, hops + 1, path + [dst]))
    return out


def impact(graph: Graph, start: str) -> list[dict]:
    """沿边反向走到底（AC4）：受影响节点集（依赖方 ← 被改方；路径为 ref 正向）。"""
    out, seen = [], {start}
    queue = deque([(start, 0, [start])])
    while queue:
        node_id, hops, path = queue.popleft()
        for field, src in graph.reverse_edges(node_id):
            if src in seen:
                continue
            seen.add(src)
            out.append({"id": src, "model": graph.model_of(src),
                        "hops": hops + 1, "via": field, "path": [src] + path})
            queue.append((src, hops + 1, [src] + path))
    return out


# ---------- 输出 ----------


def _plain(obj):
    """MDict/MList 带行号容器 → 纯 dict/list（PyYAML representer 按精确类型查表）。"""
    if isinstance(obj, dict):
        return {key: _plain(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_plain(value) for value in obj]
    return obj


def _display_path(file: str, target: Path) -> str:
    try:
        return os.path.relpath(file, str(target))
    except ValueError:
        return Path(file).name


def print_human(report: dict, target: Path) -> None:
    node = report["node"]
    print(f"图索引 graph_index — {report['target']}")
    print(f"命中: {node['id']} ({node['model']}) 域={node['domain']} "
          f"位置={_display_path(node['file'], target)}:{node['line']}")
    print("属性:")
    dump = yaml.safe_dump(_plain(node["element"]), allow_unicode=True,
                          default_flow_style=False, sort_keys=False)
    for line in dump.splitlines():
        print(f"  {line}")
    if "closure" in report:
        rows = report["closure"]
        print(f"引用闭包 (--closure): {len(rows)} 个下游节点")
        for row in rows:
            print(f"- {row['id']} ({row['model']}) hops={row['hops']} "
                  f"via={row['via']} path={' → '.join(row['path'])}")
    if "impact" in report:
        rows = report["impact"]
        print(f"影响集 (--impact): {len(rows)} 个受影响节点（沿依赖反向走）")
        for row in rows:
            print(f"- {row['id']} ({row['model']}) hops={row['hops']} "
                  f"via={row['via']} path={' → '.join(row['path'])}")
    stats = report["stats"]
    print(f"图统计: 节点={stats['nodes']} 边={stats['edges']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="图索引构建器（specs/graph_index.md）")
    ap.add_argument("target", help="ontology 目录（本体仓根或单域目录）")
    ap.add_argument("--query", required=True, help="要查询的元素 ID")
    ap.add_argument("--closure", type=int, default=None, metavar="N",
                    help="沿 ref 正向走 N 跳的引用闭包（N>=1）")
    ap.add_argument("--impact", action="store_true",
                    help="沿依赖边反向走，输出受影响节点集")
    ap.add_argument("--json", dest="json_out", action="store_true",
                    help="机读 JSON 输出（供 CI/skill 消费）")
    args = ap.parse_args(argv)

    if args.closure is not None and args.closure < 1:
        print("用法错误: --closure N 需要 N >= 1（0 跳闭包无意义）", file=sys.stderr)
        return 2
    try:
        graph = build_graph(Path(args.target))
    except ValueError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        return 2

    query = args.query
    if query not in graph.nodes:  # AC5：明确报未找到，不猜近似
        reason = f"未找到: {query}（图内共 {len(graph.nodes)} 节点；不做名称猜测）"
        if args.json_out:
            print(json.dumps({"target": str(Path(args.target).resolve()),
                              "query": query, "found": False, "error": reason,
                              "stats": graph.stats()},
                             ensure_ascii=False, indent=2, default=str))
        else:
            print(reason, file=sys.stderr)
        return 1

    report = {"target": str(Path(args.target).resolve()), "query": query,
              "found": True, "node": graph.nodes[query], "stats": graph.stats()}
    if args.closure is not None:
        report["closure"] = closure(graph, query, args.closure)
    if args.impact:
        report["impact"] = impact(graph, query)
    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print_human(report, Path(args.target).resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())

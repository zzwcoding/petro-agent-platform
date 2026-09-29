#!/usr/bin/env python3
"""semantic_service_core.py —— 语义服务四步瀑布的可机判核心（票 22）。

边界（提纯不重写，L0 设计裁决）：本工具提供的是「回答的确定性骨架」——
显式锚定解析、ID/名称解析、闭包/影响装配指令、拒答类型判定
（面外/仓内没有/禁用词）与命中 ID 集；**自然语言成稿仍是 skill（LLM 工序）
的事**，core 不产出回答正文。

复用不复制：
  - 图能力一律经 tools/graph_index.py 子进程 --json 调用（零耦合，票 04 产物
    是真源）；本脚本不自建图、不自算闭包。
  - 禁用词表自实现：读目标域 GLS 文件 terms[].status 含「禁用」的 term+aliases
    ——GLS 文件是唯一真源，schema_check 与 core 是两个读者（不 import schema_check）。
  - 名称解析的自建最小节点索引（id/name/alias/属性标签/前缀→模型，PyYAML 直读）：
    graph_index 的 --query 是必备参数、无全量节点输出能力，而二级名称解析需要
    全量候选面；故索引仅服务于**解析面**，图遍历（closure/impact）仍全部走
    graph_index 子进程（取舍记录 lessons/22）。

CLI 契约（票 22 L0）:
  python3 tools/semantic_service_core.py <ontology目录> --ask "问题" [--json]
  裁决结构 {status: answered|refused_out_of_surface|refused_missing|refused_banned,
            waterfall_level, anchor, hits:[{id,model,name}], citations,
            scaffold_commands, ...拒答细 Struct}
  --json 机读；人类面简报。退出码 0 answered / 1 refused（拒答也是有效裁决）/
  2 配置错误。

瀑布顺序（skills/semantic-service/references/retrieval-waterfall.md）:
  检索面裁剪在先（§0/§5）：@ID 前缀→模型（model-deps.json idPrefixes）→camp
  （model-registry.json），camp=business-core 之外一律面外拒答——**先判阵营后查
  存在性**（SCR-BOHAI-01 在真域不存在，仍按前缀判 MU 面外即拒，票 22 裁决）。
  票 25 起 R1 裁剪收敛到 Surface.in_surface 单一判定，并覆盖**名称解析候选
  产生处**：面外节点不进候选集，故不进 hits/citations/装配指令；命中集全为
  面外时按既有「未找到」（R2）语义如实拒答。
  票 34 收敛票 25 审查指出的两处 latent 出口（R1 补齐到剩余装配面）：
  ①GLS 命中的闭包目标先过 in_surface 再挂 --closure 装配指令（闭包全面外
  =不产指令）；②@锚定 --impact 行的 BEHAVIOR 类型过滤叠加 in_surface camp
  裁剪——类型过滤不豁免检索面判定。
  之后：禁用词扫问面 → 一级锚定（--impact 反向收行为）→ 二级名称解析
  （候选词对 name/alias/属性标签/GLS term+alias 的确定性分层匹配，不猜不模糊）
  → 三级闭包装配 → 四级可拒答（R2 缺件分层 + 近邻指路）。

依赖：Python3 stdlib + PyYAML（safe 装载）。零 LLM，全路径确定性。
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_INDEX = Path(__file__).resolve().parent / "graph_index.py"

ANCHOR_RE = re.compile(r"@([A-Za-z][A-Za-z0-9-]*)")
PUNCT_RE = re.compile(r"[\s「」『』《》()（）？?！!。，,；;、.·:：\"']")

# 引问面脚手架词（问句形态词，不是概念词）；按长度降序替换，长词优先。
STRIP_PHRASES = sorted(
    {"什么是", "是什么", "的意思", "什么叫", "有哪些", "还能用吗", "还能用",
     "长什么样", "怎么看", "怎么算", "页面", "界面", "细节", "按钮", "口径",
     "含义", "意思", "定义", "解释", "一下", "如何", "怎样", "怎么", "哪些",
     "行为", "什么", "请", "问", "吗", "呢", "的", "了", "么"},
    key=len, reverse=True)

# 闭包装配进 citations 的模型面（口径四件套 + 术语）：承载(OBJECT)/行为
# (BEHAVIOR)/规则(RULE)/查询出口(REPORT)/术语(GLS)。权限/角色/主体/流程不入
# citations（证据集口径收窄），但 --impact 全集可经 scaffold_commands 复现。
CITATION_MODEL_TYPES = {"OBJECT", "BEHAVIOR", "RULE", "REPORT", "GLOSSARY"}
MAX_IMPACT_HOPS = 2

STATUS_ANSWERED = "answered"
STATUS_OUT_OF_SURFACE = "refused_out_of_surface"
STATUS_MISSING = "refused_missing"
STATUS_BANNED = "refused_banned"

# 瀑布真源常量（票 39 件二，二期收官报告 §6.5 观察项 #1 清偿）：四步检索瀑布的
# (编号, 名称, 一句话)——与本模块 answer() 的瀑布实现工序一一对应
# （①↔一级·显式锚定、②↔二级·ID/名称解析、③↔三级·闭包装配、④↔四级·可拒答）。
# 真源地位：瀑布演进改这里，消费面同步重 gen——工序（skill_pack_gen 工序路由节
# import 本常量渲染）/发布物（exports/skillpkg SKILL.md+skillpack.json，--check
# 抓陈旧）/文档（skill references 细则的速查面）三处消费；运行时判定细则仍以
# skills/semantic-service/references/retrieval-waterfall.md 为准。
WATERFALL_STEPS = (
    ("①", "显式锚定",
     "问句带 @ID 时按前缀定模型定阵营（先阵营后存在性）：面内确认存在并反向收"
     "名下行为；面外拒答，不返回该元素任何细节。"),
    ("②", "名称解析",
     "无锚定/锚定失败降级：候选词对 name/alias/属性标签/术语确定性分层匹配，"
     "不猜不模糊；多义列候选请锚定修饰词，不擅自合并。"),
    ("③", "闭包装配",
     "命中元素沿引用/影响两向装配证据集（承载/行为/规则/查询出口/术语），只引"
     "用装配集内 ID，装配指令可复现。"),
    ("④", "可拒答",
     "面外/仓内没有/禁用词三分支如实拒答：缺件分层说明+近邻指路；禁用词给替代"
     "口径真实 ID；写意图走提案流程。"),
)


class ConfigError(ValueError):
    """目标域/schema 配置不可用（退出码 2）。"""


# ---------- 配置与最小节点索引（仅解析面；图遍历走 graph_index 子进程） ----------


def resolve_schema_dir(target: Path) -> Path | None:
    """schema 目录定位（照 schema_check/graph_index 同一手法）。"""
    for cand in (target / "schema", target.parent / "schema"):
        if cand.is_dir():
            return cand
    return None


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"{path} 不存在") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{path} 不是合法 JSON: {exc}") from exc


def load_yaml_doc(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} YAML 解析失败: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{path} 无法读取: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} 顶层必须是映射（模型文件约定）")
    return data


def domain_dirs(target: Path) -> list[Path]:
    """域目录 = 含 manifest.json 的目录；target 本身是域则单域。"""
    if (target / "manifest.json").is_file():
        return [target]
    return sorted(sub for sub in target.iterdir()
                  if sub.is_dir() and sub.name != "schema"
                  and (sub / "manifest.json").is_file())


class Surface:
    """检索面：前缀→模型→camp + 最小节点索引 + 禁用词表。"""

    def __init__(self, prefix2model: dict, model2camp: dict,
                 model2type: dict, model2name: dict,
                 index: dict, glossary: list):
        self.prefix2model = prefix2model
        self.model2camp = model2camp
        self.model2type = model2type
        self.model2name = model2name
        self.index = index      # id → {id, model, name, alias, labels}
        self.glossary = glossary

    def model_of(self, element_id: str) -> str | None:
        for prefix, model in self.prefix2model.items():
            if element_id.startswith(prefix):
                return model
        return None

    def camp_of(self, element_id: str) -> str | None:
        model = self.model_of(element_id)
        return self.model2camp.get(model) if model else None

    def in_surface(self, element_id: str) -> bool:
        """R1 检索面判定（唯一判定链：前缀→模型→camp，瀑布 §0/§5）——
        @锚定拒答、名称解析候选、缺件近邻、替代指路、引用装配共用本函数，
        面外（camp≠business-core 或前缀无模型）一律 False。票 25。"""
        model = self.model_of(element_id)
        return bool(model) and self.model2camp.get(model) == "business-core"

    def type_of(self, element_id: str) -> str | None:
        model = self.model_of(element_id)
        return self.model2type.get(model) if model else None

    def name_of(self, element_id: str) -> str:
        node = self.index.get(element_id)
        return (node and node.get("name")) or element_id


def load_surface(target: Path) -> Surface:
    """装载 schema 配置 + 全量扫描域模型文件建解析面。配置不可用抛 ConfigError。"""
    target = target.resolve()
    if not target.is_dir():
        raise ConfigError(f"目标目录不存在: {target}")
    schema_dir = resolve_schema_dir(target)
    if schema_dir is None:
        raise ConfigError(f"{target} 及其上级都没有 schema/ 目录")
    deps = load_json(schema_dir / "model-deps.json")
    prefix2model = deps.get("idPrefixes")
    if not isinstance(prefix2model, dict) or not prefix2model:
        raise ConfigError(f"{schema_dir / 'model-deps.json'} 缺 idPrefixes")
    registry = load_json(schema_dir / "model-registry.json")
    models = registry.get("models", {})
    model2camp = {m: info.get("camp") for m, info in models.items()
                  if isinstance(info, dict)}
    model2type = {m: info.get("modelType") for m, info in models.items()
                  if isinstance(info, dict)}
    model2name = {m: info.get("name", m) for m, info in models.items()
                  if isinstance(info, dict)}
    domains = domain_dirs(target)
    if not domains:
        raise ConfigError(f"{target} 下未找到任何域（域目录须含 manifest.json）")
    index: dict[str, dict] = {}
    glossary: list[dict] = []
    for domain in domains:
        for path in sorted(p for p in domain.rglob("*")
                           if p.is_file() and p.suffix in (".yaml", ".yml")):
            _index_doc(load_yaml_doc(path), index, glossary,
                       prefix2model, model2type)
    return Surface(prefix2model, model2camp, model2type, model2name,
                   index, glossary)


def _is_ref_key(key: str) -> bool:
    return key.endswith("Ref") or key.endswith("Refs")


def _index_doc(data: dict, index: dict, glossary: list,
               prefix2model: dict, model2type: dict) -> None:
    """一遍走 YAML：定义节点（id/name/alias/属性标签）+ 术语条目全账。"""

    def model_of(value: str) -> str | None:
        for prefix, model in prefix2model.items():
            if value.startswith(prefix):
                return model
        return None

    def def_id_of(mapping: dict) -> str | None:
        for key, value in mapping.items():
            if not (isinstance(key, str) and (key == "id" or key.endswith("Id"))):
                continue
            if _is_ref_key(key) or not isinstance(value, str):
                continue
            if model_of(value):
                return value
        return None

    def walk(node, anchor: str | None) -> None:
        if isinstance(node, dict):
            my_id = def_id_of(node)
            if my_id and my_id not in index:  # 同 ID 取先出现者（同 graph_index）
                model = model_of(my_id)
                name, alias = node.get("name"), node.get("alias")
                if model2type.get(model) == "GLOSSARY" or "term" in node:
                    name = node.get("term") or name  # GLS 条目的名字槽是 term
                    aliases = node.get("aliases")
                    alias = " ".join(aliases) if isinstance(aliases, list) else alias
                index[my_id] = {"id": my_id, "model": model, "name": name,
                                "alias": alias, "labels": []}
                anchor = my_id
            for key, value in node.items():
                if anchor and key == "attributes" and isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and isinstance(item.get("label"), str):
                            index[anchor]["labels"].append(item["label"])
                walk(value, anchor)
        elif isinstance(node, list):
            for item in node:
                walk(item, anchor)

    walk(data, None)

    terms = data.get("terms")
    if isinstance(terms, list):
        for term in terms:
            if not isinstance(term, dict) or not term.get("term"):
                continue
            aliases = term.get("aliases")
            glossary.append({
                "id": term.get("id"),
                "term": term.get("term"),
                "aliases": aliases if isinstance(aliases, list) else [],
                "status": term.get("status") or "",
                "termType": term.get("termType") or "",
                "definition": term.get("definition") or "",
                "related": term.get("relatedObjectRefs")
                if isinstance(term.get("relatedObjectRefs"), list) else [],
            })


# ---------- graph_index 子进程（图消费唯一通道） ----------


def graph_query(target: Path, query_id: str, extra: tuple = ()) -> dict | None:
    """--query 单点查询（可带 --impact/--closure）；未找到返回 None（不猜）。"""
    cmd = [sys.executable, str(GRAPH_INDEX), str(target),
           "--query", query_id, "--json", *extra]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if proc.returncode == 0:
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"graph_index 输出不可解析: {exc}") from exc
    if proc.returncode == 1:  # 未找到（有效结论，非错误）
        return None
    raise ConfigError(f"graph_index 配置错误: {(proc.stderr or '').strip()}")


# ---------- 二级名称解析（确定性分层匹配，不猜不模糊） ----------


def extract_concepts(question: str) -> list[str]:
    """剥问句脚手架与标点，剩余段（len≥2，去重保序）为概念候选词。"""
    text = ANCHOR_RE.sub(" ", question)
    for phrase in STRIP_PHRASES:
        text = text.replace(phrase, " ")
    segments = [seg.strip() for seg in PUNCT_RE.sub(" ", text).split()]
    return [seg for seg in dict.fromkeys(segments) if len(seg) >= 2]


def node_fields(node: dict) -> list[tuple[str, str]]:
    """候选面字段：name / alias / 属性标签（瀑布 §2：对象名/指标名/别名/承载标签）。"""
    fields = []
    if node.get("name"):
        fields.append(("name", node["name"]))
    if node.get("alias"):
        fields.append(("alias", node["alias"]))
    fields.extend(("label", lab) for lab in node.get("labels", []))
    return fields


def match_tier(token: str, text: str) -> int | None:
    """确定性分层：1 全等；2 字段⊆候选词；3 候选词⊆字段（限定变体）；
    4 头部共prefix（≥2 字，如 日产量→日产计量/日产油量）。"""
    if not token or not text:
        return None
    if text == token:
        return 1
    if len(text) >= 2 and text in token:
        return 2
    if len(token) >= 2 and token in text:
        return 3
    if len(token) >= 2 and len(text) >= 2 and text.startswith(token[:2]):
        return 4
    return None


def resolve_names(concepts: list[str], surface: Surface) -> list[dict]:
    """全量候选面扫描：每节点取最优分层，按（层, 字段长, ID）稳定排序。
    R1 裁剪在候选产生处（票 25）：面外节点（camp≠business-core）不进候选集，
    面外 ID 不出现在 hits/citations/装配指令；命中集全为面外=等价未命中，
    走既有 R2「仓内没有」语义，不另行报错。"""
    best: dict[str, tuple] = {}
    for node in surface.index.values():
        if not surface.in_surface(node["id"]):
            continue
        for kind, text in node_fields(node):
            for token in concepts:
                tier = match_tier(token, text)
                if tier is None:
                    continue
                rank = (tier, len(text), node["id"])
                if node["id"] not in best or rank < best[node["id"]][0]:
                    best[node["id"]] = (rank, node, {
                        "token": token, "field": kind, "text": text, "tier": tier})
    hits = []
    for _rank, node, evidence in best.values():
        hits.append({"id": node["id"], "model": node["model"],
                     "name": node.get("name") or node["id"],
                     "via": f"名称解析 t{evidence['tier']} "
                            f"{evidence['field']}=「{evidence['text']}」"
                            f" ←「{evidence['token']}」"})
    hits.sort(key=lambda h: (best[h["id"]][0], h["id"]))
    return hits


def _bigrams(token: str) -> set[str]:
    return {token[i:i + 2] for i in range(len(token) - 1)}


def scan_layers(concepts: list[str], surface: Surface) -> tuple[dict, list[dict]]:
    """R2 缺件分层核对：查询层(REPORT)/对象字段层(OBJECT)/行为规则层
    (BEHAVIOR+RULE) 各层有无 2-gram 交集的承载；近邻=有交集者（至多 2，
    标「非所问」）。机械面只证明「无承载/有近邻」，不证明语义等同。"""
    grams: set[str] = set()
    for token in concepts:
        grams |= _bigrams(token)
    layer_specs = [("查询层（统计/报表出口）", {"REPORT"}),
                   ("对象/字段层（承载概念）", {"OBJECT"}),
                   ("行为/规则层（动作/校验）", {"BEHAVIOR", "RULE"})]
    near: list[tuple[str, dict]] = []
    missing = {}
    for label, types in layer_specs:
        found = []
        for node in surface.index.values():
            if not surface.in_surface(node["id"]):  # R1：面外不进缺件/近邻（票 25）
                continue
            if surface.type_of(node["id"]) not in types:
                continue
            texts = [t for _k, t in node_fields(node)]
            if any(g in text for g in grams for text in texts):
                found.append(node["id"])
                near.append((node["id"], node))
        if found:
            missing[label] = f"有 {len(found)} 个字面近邻（非所问，见 near）"
        else:
            missing[label] = "未建（仓内无承载，待 Owner 提案补建）"
    near_sorted = [{"id": nid, "model": node["model"],
                    "name": node.get("name") or nid, "note": "近邻，非所问"}
                   for nid, node in sorted(near)[:2]]
    return missing, near_sorted


# ---------- 三级闭包装配（graph_index 子进程） ----------


def _citation_ok(surface: Surface, element_id: str) -> bool:
    if not surface.in_surface(element_id):  # R1 camp 裁剪（票 25 收敛到同一判定）
        return False
    return surface.model2type.get(surface.model_of(element_id)) in CITATION_MODEL_TYPES


def _scaffold(target_display: str, query_id: str, extra: str = "") -> str:
    tail = f" {extra}" if extra else ""
    return f"python3 tools/graph_index.py {target_display} --query {query_id}{tail} --json"


def assemble(target: Path, surface: Surface, hit_ids: list[str],
             target_display: str) -> tuple[list[str], list[str]]:
    """装配证据集：hits ∪ closure1(hits) ∪ impact(hits)（hops≤2、camp+模型面
    裁剪）；GLS 命中加扫 impact(closure 目标)（承载规则照瀑布 §2）。"""
    citations: list[str] = []
    scaffold: list[str] = []

    def add(element_id: str) -> None:
        if element_id not in citations and _citation_ok(surface, element_id):
            citations.append(element_id)

    def add_impact(node_id: str) -> None:
        report = graph_query(target, node_id, ("--impact",))
        scaffold.append(_scaffold(target_display, node_id, "--impact"))
        for row in (report or {}).get("impact", []):
            if row.get("hops", 99) <= MAX_IMPACT_HOPS:
                add(row["id"])

    for hit_id in hit_ids:
        add(hit_id)
    gls_ids = [h for h in hit_ids if surface.type_of(h) == "GLOSSARY"]
    for hit_id in hit_ids:
        if surface.type_of(hit_id) == "GLOSSARY":
            closure = graph_query(target, hit_id, ("--closure", "1"))
            related = [row["id"] for row in (closure or {}).get("closure", [])]
            # R1 裁剪在装配指令产生处（票 34 收敛票 25 latent 出口①）：闭包目标
            # 先过 Surface.in_surface——面外目标不进 citations、不产 --impact
            # 指路；闭包全为面外时连 --closure 装配指令也不挂（不产指向面外的
            # 装配指令）。
            related = [rel for rel in related if surface.in_surface(rel)]
            if related:
                scaffold.append(_scaffold(target_display, hit_id, "--closure 1"))
            for rel in related:
                add(rel)
            for rel in related:  # 指路实体的承载规则（瀑布 §2 术语装配）
                add_impact(rel)
        else:
            add_impact(hit_id)
    return sorted(citations), scaffold


# ---------- 拒答分支 ----------


def find_banned(question: str, surface: Surface) -> dict | None:
    """禁用词表自实现（GLS status 含「禁用」）：term/alias 命中问面即拦。"""
    for entry in surface.glossary:
        if "禁用" not in entry["status"]:
            continue
        names = [entry["term"], *entry["aliases"]]
        if any(name and name in question for name in names):
            return entry
    return None


_REPL_PATTERNS = (re.compile(r"替代[：:＝=]\s*([^\s，,；;。（）()）]+)"),
                  re.compile(r"替代口径[=＝]\s*([^\s，,；;。（）()）]+)"))


def replacement_pointers(entry: dict, surface: Surface) -> list[str]:
    """替代口径名称 → 真实 ID 指路（先全等后包含，稳定排序；带 ID 的拒答）。"""
    text = f"{entry['status']} {entry['definition']}"
    names: list[str] = []
    for pattern in _REPL_PATTERNS:
        names.extend(pattern.findall(text))
    pointers: list[str] = []
    for name in dict.fromkeys(names):
        if len(name) < 2:
            continue
        exact, partial = [], []
        for node in surface.index.values():
            if not surface.in_surface(node["id"]):  # R1：面外不进指路集（票 25）
                continue
            for _kind, text_field in node_fields(node):
                if text_field == name:
                    exact.append(node["id"])
                elif name in text_field:
                    partial.append(node["id"])
        pointers.extend(sorted(set(exact)))
        pointers.extend(sorted(set(partial) - set(exact)))
    return list(dict.fromkeys(pointers))


# ---------- 瀑布主流程 ----------


def answer(target: Path, question: str, surface: Surface,
           target_display: str) -> dict:
    """四步瀑布：检索面裁剪（先阵营后存在性）→ 禁用词 → 锚定/解析 → 装配/拒答。"""

    def base(status: str, waterfall: str, **extra) -> dict:
        verdict = {"question": question, "target": target_display,
                   "status": status, "waterfall_level": waterfall,
                   "anchor": None, "hits": [], "citations": [],
                   "scaffold_commands": [], "ambiguous": False, "note": ""}
        verdict.update(extra)
        return verdict

    # —— 显式锚定：先按前缀判阵营（camp 裁剪在先，瀑布 §0/§5），后查存在性 ——
    # （判定用 Surface.in_surface 同一函数，票 25 收敛；拒绝时仍展开阵营细 Struct）
    anchors = ANCHOR_RE.findall(question)
    for anchor in anchors:
        model = surface.model_of(anchor)
        camp = surface.model2camp.get(model) if model else None  # 载荷展示用
        if model and not surface.in_surface(anchor):
            return base(
                STATUS_OUT_OF_SURFACE, "一级·显式锚定（检索面外）",
                anchor=anchor,
                camp={"prefix": next(p for p in surface.prefix2model
                                     if anchor.startswith(p)),
                      "model": model,
                      "model_name": surface.model2name.get(model, model),
                      "camp": surface.model2camp.get(model),
                      "anchor_exists": anchor in surface.index},
                reason=f"不在检索面：锚定 {anchor} 前缀 → 模型 {model}"
                       f"（{surface.model2name.get(model, model)}），camp={camp}；"
                       f"本服务只答 business-core。建造契约由 build 侧消费方在建造"
                       f"链路消费；属业务语义缺口走提案流程（本服务只读，不返回该"
                       f"元素任何细节）。")

    banned = find_banned(question, surface)
    if banned is not None:
        pointers = replacement_pointers(banned, surface)
        citations = sorted({banned["id"], *pointers})
        return base(
            STATUS_BANNED, "二级·ID/名称解析（GLS 禁用词处置）",
            hits=[{"id": banned["id"], "model": surface.model_of(banned["id"]),
                   "name": banned["term"], "via": "GLS 禁用词命中"}],
            citations=citations,
            scaffold_commands=[_scaffold(target_display, banned["id"])],
            banned={"id": banned["id"], "term": banned["term"],
                    "status": banned["status"], "termType": banned["termType"],
                    "replacement_query": banned["definition"]},
            reason=f"禁用词「{banned['term']}」（{banned['id']}，"
                   f"status={banned['status']}）——不得作为可用口径作答。"
                   f"替代口径真实 ID 指路：{pointers or '（仓内未见替代承载）'}。"
                   f"口径补改走提案流程（进仓走 MR + 语义 CI）；本服务只读。")

    concepts = extract_concepts(question)

    # —— 一级显式锚定（面内）：存在性确认 + --impact 反向装配 ——
    for anchor in anchors:
        if surface.model_of(anchor) is None or anchor not in surface.index:
            missing = {"说明": "锚定 ID 未找到（不做近似拼写猜测），"
                               "无名称候选可解析"} if not concepts \
                else scan_layers(concepts, surface)[0]
            return base(
                STATUS_MISSING, "一级·显式锚定（锚定失败）",
                anchor=anchor, missing=missing,
                reason=f"锚定 ID 未找到：@{anchor}（图内无此 ID；不猜拼写，"
                       f"R3 并入 R2）。"
                       + ("请核对 ID 或改用概念词提问；业务概念缺口走提案流程。"
                          if not concepts else
                          "已降二级名称解析仍无命中——仓内没有，走提案流程。"))

        report = graph_query(target, anchor, ("--impact",))
        if report is None:
            continue  # 理论不可达（index 与图同源）；防御性降级到下一锚
        hits = [{"id": anchor, "model": surface.model_of(anchor),
                 "name": surface.name_of(anchor), "via": "显式锚定直达"}]
        for row in report.get("impact", []):
            # BEHAVIOR 过滤收敛到 Surface 判定链（票 34 收敛票 25 latent 出口②）：
            # modelType=BEHAVIOR 但 camp≠business-core 的面外行同样不进 hits——
            # 类型过滤不豁免 camp 裁剪，同一 in_surface 判定链说了算。
            if surface.type_of(row["id"]) == "BEHAVIOR" \
                    and surface.in_surface(row["id"]):
                hits.append({"id": row["id"],
                             "model": surface.model_of(row["id"]),
                             "name": surface.name_of(row["id"]),
                             "via": f"--impact 反向 {row.get('via')}"
                                    f" hops={row.get('hops')}"})
        citations, scaffold = assemble(target, surface, [anchor], target_display)
        citations = sorted(set(citations) | {h["id"] for h in hits})
        return base(
            STATUS_ANSWERED, "一级·显式锚定", anchor=anchor, hits=hits,
            citations=citations,
            scaffold_commands=scaffold + [_scaffold(target_display, anchor)],
            note=f"名下行为=ownerEntity 直挂与经子对象挂靠两类（--impact 反向"
                 f" hops=1/2 区分）；装配证据集见 citations，回答正文由 skill 成稿。")

    # —— 二级名称解析（无锚定/锚定失败降级） ——
    hits = resolve_names(concepts, surface)
    if not hits:
        missing, near = scan_layers(concepts, surface)
        return base(
            STATUS_MISSING, "四级·可拒答",
            concepts=concepts, near=near, missing=missing,
            citations=sorted(n["id"] for n in near),
            scaffold_commands=[_scaffold(target_display, n["id"])
                               for n in near],
            reason=f"拒答：仓内没有「{'/'.join(concepts) or question.strip()}」"
                   f"这一概念（检索轨迹：候选词 {concepts or '[]'} 对"
                   f" name/alias/属性标签/GLS 全量无命中，未找到不猜）。"
                   f"缺件分层：{missing}。业务口径缺口走提案流程补定义"
                   f"（进仓走 MR + 语义 CI，待 Owner 裁决）；本服务只读，"
                   f"不代填口径、不产文件。近邻指路（真实存在、非所问）："
                   f"{[n['id'] for n in near] or '无（无字面交集，不硬凑）'}。")

    hit_ids = [h["id"] for h in hits]
    citations, scaffold = assemble(target, surface, hit_ids, target_display)
    gls_hits = surface.type_of(hit_ids[0]) == "GLOSSARY"
    notes = []
    if len(hit_ids) > 1:
        notes.append("命中多个候选（多义）：列候选请锚定修饰词，不擅自合并（瀑布 §2）。")
    if gls_hits:
        notes.append("术语条目即答案一部分（定义/别名/状态照登）；已沿"
                     " relatedObjectRefs 指路关联对象与承载规则（装配集见 citations）。")
    terms = [t for t in surface.glossary if t["id"] in hit_ids]
    return base(
        STATUS_ANSWERED, "二级·ID/名称解析（GLS 术语）" if gls_hits
        else "二级·ID/名称解析",
        hits=hits, citations=citations,
        scaffold_commands=scaffold, ambiguous=len(hit_ids) > 1,
        note=" ".join(notes),
        terms=[{"id": t["id"], "term": t["term"], "aliases": t["aliases"],
                "status": t["status"], "definition": t["definition"]}
               for t in terms])


# ---------- CLI ----------


def print_human(verdict: dict) -> None:
    print(f"语义服务核心 semantic_service_core — {verdict['target']}")
    print(f"问题: {verdict['question']}")
    print(f"裁决: {verdict['status']}（{verdict['waterfall_level']}）")
    if verdict["anchor"]:
        print(f"锚定: {verdict['anchor']}")
    for hit in verdict["hits"]:
        print(f"- {hit['id']} ({hit['model']}) {hit.get('name', '')}"
              f"  [{hit.get('via', '')}]")
    if verdict.get("citations"):
        print(f"引用 ID（{len(verdict['citations'])}）: "
              f"{' '.join(verdict['citations'])}")
    if verdict.get("missing"):
        for layer, state in verdict["missing"].items():
            print(f"缺件·{layer}: {state}")
    if verdict.get("banned"):
        b = verdict["banned"]
        print(f"禁用词: {b['term']}（{b['id']}，{b['status']}）")
    if verdict.get("note"):
        print(f"注: {verdict['note']}")
    if verdict.get("reason"):
        print(f"理由: {verdict['reason']}")
    for cmd in verdict["scaffold_commands"]:
        print(f"装配指令: {cmd}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="语义服务四步瀑布可机判核心（票 22；成稿归 skill）")
    ap.add_argument("target", help="ontology 目录（本体仓根或单域目录）")
    ap.add_argument("--ask", required=True, help="用户问题（可含 @ID 显式锚定）")
    ap.add_argument("--json", dest="json_out", action="store_true",
                    help="机读 JSON 裁决")
    args = ap.parse_args(argv)

    try:
        surface = load_surface(Path(args.target))
    except ConfigError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        return 2
    verdict = answer(Path(args.target).resolve(), args.ask, surface,
                     args.target)
    if args.json_out:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    else:
        print_human(verdict)
    return 0 if verdict["status"] == STATUS_ANSWERED else 1


if __name__ == "__main__":
    sys.exit(main())

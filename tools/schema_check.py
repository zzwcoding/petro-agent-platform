#!/usr/bin/env python3
"""schema_check.py —— 语义 CI L1–L4 闸（All-agent 票 03；spec: specs/schema_check.md AC1–7；
票 10 增 GLS 术语模型套件 GLS-AC1–4；票 11 增 L2 一致性对检查组 consistency-*，真源=
tickets/11-一致性对核验.md AC 表 + ontology/schema/schema.md §14；票 13 增 L1 元素级
结构性必填闸 required-field（真源=model-registry.json 每模型 requiredElementFields）与
L4 AC6 反向闸 missing-model-file（profile 启用却缺文件，经 manifest omittedModels
带理由豁免）；票 16 增 L4 禁用词拦截面 banned-term（真源=域内 GLS 术语 status 含
「禁用」条目的 term+aliases，匹配面=递归收集键恰为 name/alias 的字符串值子串命中，
description/notes 不扫=文档自由）；票 27 元素枚举去 id 锚定——主集合每个字典即元素
（无 id 也枚举，报缺必填身份字段，修"混入合法元素即静默逃逸"盲区），空壳守卫收窄为
「主集合键缺失或集合为空」。
票 34 增 P2-A 素材目录排除：域发现对名为 `patterns` 的子目录整体排除（素材目录
不是域，不补 manifest；约定成文 schema.md §1），修"票 33 模式件进 ontology/patterns/
后裸仓根 ontology/ 语义闸红灯"的 P2-A 缺口——裸仓根全量绿灯红线恢复。
票 38 增 L1 同域元素 id 唯一性闸 duplicate-id（身份族，与 required-field 同级）：
唯一性判定键 = manifest 域值——同一 domain 值之下元素 id（id/*Id 定义键，口径同
collect_definitions：非 ref 键、带注册前缀）不得重复，撞即报且报文含双位置（先出现
+后出现 file:line 与元素名）；跨域不判（fixture 各域合法复用同形 ID）。实现挂在
票 27 元素枚举（iter_collection_items）产物上：域值→id→(file,line,键,名) 索引；
M5 的 actorId/roleId/permissionId 跨键同值同判；文件名错挂的文件跳过（红因纯净）。
票 41 增 L3 确定性闸（语义 CI 五级的 L3=指标/SQL/安全，只收确定性可判子集，真源=
tickets/41-L3确定性闸.md 可机判子集清单 L0 裁决，四项违规码 l3-* 前缀）：
  l3-source-field      M3 规则参数 sourceField 双段（对象.属性）：对象段解析到域内
                       聚合（匹配序 id→alias→name→别名驼峰词唯一包含，可配置见
                       L3_OBJECT_MATCH_ORDER；bohai 存量用「dailyProduction」式自造
                       短名——schema.md §6 示例即此形态，与聚合 alias 非直配，靠末层
                       解析），字段段在该聚合 attributes[].name 中；sourceField 容忍
                       中文注记后缀（「oilOutput（区块月合计）」截断于首个括号），
                       非双段形态（无承载字段注记）不在机判面不判；
  l3-expression-ref    M7 resultColumns[].sourceExpression 内「别名.字段」token：
                       别名须在该报表 sourceObjects[].alias 声明集，字段须在别名所指
                       聚合（objectRef）的 attributes 中；objectRef 悬空归 dangling-ref
                       （红因不混），运算符/字面量/非 x.y token 跳过；
  l3-sql-readonly      M7 referenceSql（可选字段，缺省不扫）在场即扫：DML/DDL 黑名单
                       词（INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE/GRANT）
                       大小写不敏感、\b 词边界匹配（防列名 updated_at 误伤）；
  l3-rule-form         M3 规则落地形态二选一（schema.md §6）：ruleType=EXPRESSION
                       →expression 在场且非空；其余 ruleType（值集实读=VALIDATION/
                       CALCULATION/DERIVATION/TRANSFORMATION/RISK，无 EXPRESSION/
                       NARRATIVE 型）→expression/narrative 至少一者在场且非空；
                       ruleType 本身缺失归 L1 required-field，不叠红因。
报告计数行与 --json levels 增 L3；文件名错挂的文件跳过 L3 扫描（红因纯净，沿
票 13/16 先例）。剩余子集（SQL 语义正确性/指标公式数学正确性/安全敏感度分级/
任何需 LLM 判断的项）明示不收，归 L5 设计案（批次三方案 1）。

对给定 ontology 目录做确定性校验：
  L1 schema 合法——YAML 可解析（AC2）、公共字段 model_type/version/domain 在场（AC3）、
     域 manifest.json 在场且 profile 已登记、模型类型已知、文件名与注册表该模型
     yamlFile 一致（票 10 AC4：GLS 文件名错挂/model_type 写错；真源=model-registry.json
     yamlFile，即"一模型一 YAML、固定文件名"约定的闸上强化）、schema 两份机读表互相一致、
     逐元素结构性必填字段在场（票 13 required-field：身份/类型判别/检查锚点/载荷容器四类，
     口径与逐模型推导表见 lessons/13；票 27：主集合逐字典枚举，无 id 元素报缺必填身份
     字段；空壳守卫收窄为「主集合键缺失或集合为空」，同报 required-field）；
  L2 引用与依赖——ref 指向的 ID 全仓有定义（AC4 悬空引用）、ref 目标模型不越
     类型层依赖白名单（AC5，真源 ontology/schema/model-deps.json + model-registry.json）；
     一致性对（票 11，digest §12.2 本仓可行子集）：
       consistency-redirection    M7.behaviorRef 未指向 behaviorType=QUERY 的 M2 行为
       consistency-not-one-to-one 同一 M2 查询行为被两个 M7 对象绑定（严格一对一）
       consistency-permission     M2.requiredPermissions 指到的 PERM.targetRef 未回指该行为
       consistency-flow-role      M6 活动 roleRef 不在流程 roleRefs 集合内；
     涉事元素存在性仍由 dangling-ref 承载（ref 扫描面=refKeys ∪ *Ref/Refs ∪ edges），
     本组只补"语义闭合向"，违规 kind 一律 consistency- 前缀（schema.md §14）。
  L4 profile 合规与兼容——profile 未启用的模型文件不得出现（AC6；票 10 GLS-AC2 同款）、
     profile 启用的模型缺文件且 manifest omittedModels 无带理由豁免条目必须红
     （票 13 AC6 反向 missing-model-file）、换义锁定字段（lockedFields）不得复用
     （AC7 字段换义式变更）。

模型类型/文件名/前缀/依赖/必填判定全部走两份机读表（model-registry.json +
model-deps.json），本脚本不硬编码任何模型清单——新增模型=机读表加条目。

只读不写 YAML；失败输出含文件+行级定位（行号取自 YAML node start_mark）；
--json 供 CI 消费。依赖：Python3 stdlib + PyYAML（safe 装载，PRD 技术栈唯一第三方）。

CLI: python3 tools/schema_check.py <ontology目录> [--json]
  <ontology目录> 可以是本体仓根（下含 schema/ 与若干域目录）或单个域目录
  （schema 解析顺序：本目录 schema/ → 上级目录 schema/）。

退出码：0 全过；1 有违规；2 配置/用法错误。
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

COMMON_FIELDS = ("model_type", "version", "domain")
MANIFEST_REQUIRED = ("domain", "profile")


# ---------- 带行号的 YAML 装载（只读；safe） ----------

class MDict(dict):
    """带行号与键行号的映射（行号=首键行；key_lines=各键自身行）。"""

    line = 0
    key_lines = None


class MList(list):
    """带行号的序列。"""

    line = 0


class LineLoader(yaml.SafeLoader):
    """SafeLoader + 行号标注：映射/序列容器记录 start_mark 行号。"""


def _construct_map(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping = MDict()
    yield mapping
    key_lines = {}
    for k_node, v_node in node.value:
        key = loader.construct_object(k_node, deep=deep)
        value = loader.construct_object(v_node, deep=deep)
        mapping[key] = value
        key_lines[key] = k_node.start_mark.line + 1
    mapping.line = node.start_mark.line + 1
    mapping.key_lines = key_lines


def _construct_seq(loader, node, deep=False):
    seq = MList()
    yield seq
    seq.extend(loader.construct_sequence(node, deep=deep))
    seq.line = node.start_mark.line + 1


LineLoader.add_constructor("tag:yaml.org,2002:map", _construct_map)
LineLoader.add_constructor("tag:yaml.org,2002:seq", _construct_seq)


def load_yaml(path: Path):
    """解析 YAML；语法错误抛 _YamlSyntaxError（带文件与行号）。"""
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.load(fh, Loader=LineLoader)
    except yaml.MarkedYAMLError as exc:
        mark = exc.problem_mark or exc.context_mark
        line = mark.line + 1 if mark else 0
        problem = exc.problem or str(exc)
        raise _YamlSyntaxError(f"{path.name}:{line} {problem}") from exc
    except yaml.YAMLError as exc:
        raise _YamlSyntaxError(f"{path.name} {exc}") from exc


class _YamlSyntaxError(Exception):
    pass


# ---------- 目录/配置解析 ----------

def resolve_schema_dir(target: Path) -> Path | None:
    for cand in (target / "schema", target.parent / "schema"):
        if cand.is_dir():
            return cand
    return None


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path} 不存在（schema 机读表必配）") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{path} 不是合法 JSON: {exc}") from exc


# 素材目录（票 34 P2-A）：名为 patterns 的子目录是建模素材区不是域——不作为域
# 扫描（含 manifest 的真域形态也不扫，排除只按目录名不按内容）；其结构纪律由
# fixtures/pattern-library/ 出厂集与归档闸 ontology-pattern 类承载，约定见
# schema.md §1「素材目录约定」。
PATTERN_DIRS = ("patterns",)


def discover_domains(target: Path) -> tuple[list[Path], list[Path]]:
    """返回 (域目录列表, 有模型文件但缺 manifest 的目录列表)。

    票 34 P2-A：名为 patterns 的子目录整体排除（素材目录补 manifest=撒谎，
    设计裁决不补 manifest 而是排除）；其余含模型 YAML 但缺 manifest 的目录
    照报 missing-manifest（真域扫描一个不少）。
    """
    if (target / "manifest.json").is_file():
        return [target], []
    domains, missing = [], []
    for sub in sorted(target.iterdir()):
        if not sub.is_dir() or sub.name == "schema" or sub.name in PATTERN_DIRS:
            continue
        if (sub / "manifest.json").is_file():
            domains.append(sub)
        elif any(sub.glob("*.yaml")) or any(sub.glob("*.yml")):
            missing.append(sub)
    return domains, missing


def model_files(domain: Path) -> list[Path]:
    return sorted(p for p in domain.rglob("*")
                  if p.is_file() and p.suffix in (".yaml", ".yml"))


# ---------- 遍历与 ID/ref 判定 ----------

def iter_mappings(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from iter_mappings(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_mappings(item)


def is_ref_key(key: str, ref_keys: set) -> bool:
    return key in ref_keys or key.endswith("Ref") or key.endswith("Refs")


def id_model_of(value: str, prefix2model: dict) -> str | None:
    for prefix, model in prefix2model.items():
        if value.startswith(prefix):
            return model
    return None


def key_line(mapping, key) -> int:
    if getattr(mapping, "key_lines", None):
        return mapping.key_lines.get(key, mapping.line)
    return getattr(mapping, "line", 0)


def collect_definitions(data, ref_keys: set, prefix2model: dict):
    """收集本文件定义的 ID：定义键（id / *Id，且非 ref 键）上带已知前缀的标量。"""
    found = {}
    for mapping in iter_mappings(data):
        for key, value in mapping.items():
            if is_ref_key(key, ref_keys):
                continue  # ref 值不得自证存在（防自引用洗白悬空检查）
            if key != "id" and not (isinstance(key, str) and key.endswith("Id")):
                continue
            if isinstance(value, str):
                model = id_model_of(value, prefix2model)
                if model:
                    found.setdefault(value, key_line(mapping, key))
    return found


def iter_ref_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_ref_strings(item)


def collect_elements(data, mkey: str, prefix2model: dict, ref_keys: set):
    """收集本文件中主 ID 前缀→mkey 的元素：[(元素ID, 映射)]（票 11 一致性对用）。

    元素主 ID = `id` / `*Id` 键（非 ref 键）上的字符串值——与 collect_definitions
    同一定义面，且前缀判回本模型；嵌套结构里的非注册前缀 ID（如 M6 活动 activityId、
    M7 条件 conditionId 不在 idPrefixes）天然不入选。
    """
    out = []
    for mapping in iter_mappings(data):
        for key, value in mapping.items():
            if not (isinstance(key, str) and (key == "id" or key.endswith("Id"))):
                continue
            if is_ref_key(key, ref_keys) or not isinstance(value, str):
                continue
            if id_model_of(value, prefix2model) == mkey:
                out.append((value, mapping))
    return out


def iter_collection_items(data):
    """主集合元素枚举（票 27）：模型文件顶层「列表」值里的每个字典=一个元素候选。

    不再以「有 id 键」为枚举前提（无 id 也枚举——修缺 id 盲区：无 id 元素混入
    合法元素时旧版静默逃逸，纯无 id 域被空壳守卫一条吞掉）。实测边界（票 27 盘点
    全仓模型文件）：顶层 list-of-dicts 键恰为各模型元素主集合（M1 aggregates/
    data_dictionaries/aggregate_associations、M5 actors/roles/permissions、
    GLS terms、MU screens 等），MU application 为顶层映射不入枚举；嵌套子结构
    （attributes[]/refRules[]/activities[]/types[].items 等）不在顶层、天然不入
    枚举——它们由 ref 扫描与字段检查覆盖，属性/活动字典无 id 是合法形态。
    """
    if not isinstance(data, dict):
        return
    for value in data.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield item


def element_identity(item, mkey: str, prefix2model: dict, ref_keys: set):
    """元素身份判定（票 27）：返回 (matched, stray)。

    matched = `id`/`*Id` 键（非 ref 键）字符串值判回本模型注册前缀的首个 (键, 值)
    ——有它即既有逐字段闸（requiredElementFields）覆盖；stray = 有 id 形但值不判
    回本模型的首个 (键, 值)（集合里挂了别家模型的 ID，旧版此处恰被空壳误吞）；
    两者皆无 = (None, None)，即缺 id 元素。
    """
    stray = None
    for key, value in item.items():
        if not (isinstance(key, str) and (key == "id" or key.endswith("Id"))):
            continue
        if is_ref_key(key, ref_keys) or not isinstance(value, str):
            continue
        if id_model_of(value, prefix2model) == mkey:
            return (key, value), None
        if stray is None:
            stray = (key, value)
    return None, stray


# ---------- 禁用词拦截面（票 16：GLS×schema_check 联动闸） ----------

NAME_ALIAS_KEYS = ("name", "alias")


def load_yaml_from_text(text: str):
    """文本直载（单测构造带行号数据用，与 load_yaml 同一 LineLoader）。"""
    import io
    return yaml.load(io.StringIO(text), Loader=LineLoader)


def iter_name_alias_values(data):
    """递归收集键恰为 name/alias 的字符串值：[(值, 所在映射, 键名)]。

    匹配面口径（票 16 L0 定稿）：所有字典中键**恰为** `name`/`alias` 的字符串值，
    通用口径递归全仓（不逐模型硬列挂点）。不入面的：label/definition/notes 等
    其他键（文档提及合法）、复数 `aliases` 键（那是 GLS 禁用词表的**来源**字段，
    不是匹配面）、非字符串值。GLS 条目以 `term` 键承载词面——天然不在匹配面
    （禁用词表不会自匹配，专测钉死）。
    """
    for mapping in iter_mappings(data):
        for key in NAME_ALIAS_KEYS:
            value = mapping.get(key) if isinstance(mapping, dict) else None
            if isinstance(value, str):
                yield value, mapping, key


def collect_banned_terms(data) -> list[tuple[str, str, str]]:
    """从 GLS 术语数据收集禁用词表：[(词, 条目ID, status 原文)]。

    判定（票 16 设计裁决，宽进严出）：条目 `status` 字段值**包含**「禁用」子串
    即入表（不枚举状态值——「禁用（替代：×）」「已禁用待复核」同拦）；
    禁用词成员 = term 字段值 + aliases 列表成员。
    """
    out: list[tuple[str, str, str]] = []
    terms = data.get("terms")
    if not isinstance(terms, list):
        return out
    for entry in terms:
        if not isinstance(entry, dict):
            continue
        status = entry.get("status")
        if not (isinstance(status, str) and "禁用" in status):
            continue
        gls_id = entry.get("id", "?")
        term = entry.get("term")
        if isinstance(term, str) and term:
            out.append((term, gls_id, status))
        for alias in iter_ref_strings(entry.get("aliases") or []):
            if isinstance(alias, str) and alias:
                out.append((alias, gls_id, status))
    return out


# ---------- L3 确定性闸（票 41：指标/SQL/安全的确定性可判子集） ----------

# L3-3 DML/DDL 黑名单（票面清单，大小写不敏感 + \b 词边界——防列名 updated_at 式误伤）
L3_SQL_BLACKLIST = ("INSERT", "UPDATE", "DELETE", "DROP",
                    "ALTER", "TRUNCATE", "CREATE", "GRANT")
L3_SQL_BLACKLIST_RE = re.compile(
    r"\b(" + "|".join(L3_SQL_BLACKLIST) + r")\b", re.IGNORECASE)
# L3-2 表达式 token：只取「别名.字段」形态（x.y），数字/运算符/函数名跳过
L3_REF_TOKEN_RE = re.compile(r"[A-Za-z_]\w*\.[A-Za-z_]\w*")
# L3-1 对象段匹配序（票 41 防踩坑裁决：可配置匹配序，首层命中即解析）。
# id→alias→name 为直配层（不区分大小写比 id/alias，name 按原文精确）；末层
# 「别名驼峰词唯一包含」为自造短名兼容层——bohai 存量 sourceField 用
# 「dailyProduction」式短名（schema.md §6 字段说明的示例即此形态），与聚合
# alias（OilProductionDaily）非直配；该层要求全聚合唯一命中才解析（多命中=
# 指认不了，视同未解析报本码），防「well」式泛词被 WellOverhaul/WellMeasures
# 多吃。匹配序演进=改此元组，判定逻辑不随之分叉。
L3_OBJECT_MATCH_ORDER = ("id", "alias", "name", "alias-tokens")


def l3_camel_tokens(text: str) -> set:
    """驼峰切词小写集：OilProductionDaily→{oil, production, daily}。"""
    return {t.lower() for t in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", text or "")}


def l3_split_source_field(value):
    """sourceField 拆 (对象段, 字段段)；非「x.y」双段形态返回 None（不在 L3-1 机判面）。

    字段段容忍中文注记后缀——bohai 存量「dailyProduction.oilOutput（区块月合计）」
    式值截断于首个全角（或半角 ( 括号；无承载字段注记（「存水率变动（无承载
    字段，待 Owner）」等无点值）天然非双段，不判（票 41 明示只收双段形态）。
    """
    if not isinstance(value, str) or "." not in value:
        return None
    obj, _, field = value.partition(".")
    field = re.split(r"[（(]", field, maxsplit=1)[0].strip()
    obj = obj.strip()
    if not obj or not field:
        return None
    return obj, field


def l3_resolve_object_segment(segment: str, aggregates: list):
    """对象段→聚合目录条目；按 L3_OBJECT_MATCH_ORDER 逐层试，首个命中即解析。

    返回 (聚合或 None, 命中层或 None)。末层 alias-tokens=对象段驼峰词 ⊆ 聚合
    alias 驼峰词且全聚合唯一命中；空段/多命中不解析（红因可指认）。
    """
    seg_low = segment.lower()
    for layer in L3_OBJECT_MATCH_ORDER:
        if layer == "id":
            for agg in aggregates:
                if str(agg.get("id") or "").lower() == seg_low:
                    return agg, layer
        elif layer == "alias":
            for agg in aggregates:
                if str(agg.get("alias") or "").lower() == seg_low:
                    return agg, layer
        elif layer == "name":
            for agg in aggregates:
                if agg.get("name") == segment:
                    return agg, layer
        elif layer == "alias-tokens":
            seg_tokens = l3_camel_tokens(segment)
            if not seg_tokens:
                continue
            hits = [agg for agg in aggregates
                    if seg_tokens <= l3_camel_tokens(str(agg.get("alias") or ""))]
            if len(hits) == 1:
                return hits[0], layer
    return None, None


def l3_aggregate_catalog(data) -> list:
    """M1 文件→域内聚合目录：[{id,name,alias,attrs}]（顶层 aggregates[]，schema.md §4；
    集合键与 M3 rules/M7 query_reports 同按 schema.md 顶层约定锚定，沿票 11 锚定
    结构性承载字段的先例）。attrs=attributes[].name 集合。"""
    out = []
    aggs = data.get("aggregates")
    if not isinstance(aggs, list):
        return out
    for agg in aggs:
        if not isinstance(agg, dict):
            continue
        attrs = set()
        for attr in agg.get("attributes") or []:
            if isinstance(attr, dict) and isinstance(attr.get("name"), str):
                attrs.add(attr["name"])
        out.append({"id": agg.get("id"), "name": agg.get("name"),
                    "alias": agg.get("alias"), "attrs": attrs})
    return out


# ---------- 主校验 ----------

def run(target: Path) -> dict:
    target = target.resolve()
    if not target.is_dir():
        raise ValueError(f"目标目录不存在: {target}")
    schema_dir = resolve_schema_dir(target)
    if schema_dir is None:
        raise ValueError(f"{target} 及其上级都没有 schema/ 目录（缺模型注册表）")
    registry = load_json(schema_dir / "model-registry.json")
    deps = load_json(schema_dir / "model-deps.json")
    models = registry.get("models")
    prefix2model = deps.get("idPrefixes")
    ref_keys = set(deps.get("refKeys", []))
    if not isinstance(models, dict) or not isinstance(prefix2model, dict):
        raise ValueError(f"{schema_dir} 的注册表/依赖表缺 models/idPrefixes")

    # 一致性核对：model-deps.json 的 edges 不得超出 model-registry.json 的 dependsOn（自依赖除外）
    edges = {}
    for edge in deps.get("edges", []):
        edges[(edge["from"], edge["field"])] = set(edge["to"])
    violations = []  # {level, kind, file, line, message}
    seen = set()

    def add(level, kind, file, line, message):
        key = (kind, file, line, message)
        if key not in seen:
            seen.add(key)
            violations.append(
                {"level": level, "kind": kind, "file": file,
                 "line": line, "message": message})

    for (frm, _field), to in edges.items():
        if frm not in models:
            add("L1", "deps-registry-conflict", str(schema_dir / "model-deps.json"), 0,
                f"edges 引用未注册模型 {frm}")
            continue
        extra = to - set(models[frm].get("dependsOn", [])) - {frm}
        if extra:
            add("L1", "deps-registry-conflict",
                str(schema_dir / "model-deps.json"), 0,
                f"{frm} 的依赖边 {sorted(to)} 超出 dependsOn "
                f"{sorted(models[frm].get('dependsOn', []))}（两份机读表冲突）")

    model_by_type = {m["modelType"]: key for key, m in models.items()}
    known_profiles = {p for m in models.values() for p in m.get("profiles", [])}
    domains, manifest_missing = discover_domains(target)
    for sub in manifest_missing:
        add("L1", "missing-manifest", str(sub / "manifest.json"), 0,
            f"目录「{sub.name}」含模型 YAML 但缺 manifest.json（域声明必配）")

    definitions: dict[str, tuple[str, int]] = {}
    defs_by_domain: dict[str, set[str]] = {}
    # 重复 id 索引（票 38）：manifest 域值 → id → (file, line, 键, 元素名)。
    # 唯一性判定键 = manifest 域值（同一 domain 值之下 id 不得重复，跨域不判——
    # fixture 各域合法复用同形 ID、真仓单域无跨域场景）；两目录同域值 = 同一
    # 命名空间（索引按域值共享）。
    id_index: dict[str, dict[str, tuple[str, int, str, str]]] = {}
    domain_summaries = []
    n_files = 0

    for domain in domains:
        manifest = load_json(domain / "manifest.json")
        dname = manifest.get("domain", domain.name)
        profile = manifest.get("profile")
        for field in MANIFEST_REQUIRED:
            if field not in manifest:
                add("L1", "missing-manifest-field", str(domain / "manifest.json"), 0,
                    f"manifest 缺必备字段 `{field}`")
        if profile not in known_profiles:
            add("L1", "unknown-profile", str(domain / "manifest.json"), 0,
                f"未知 profile「{profile}」（注册表可用: {sorted(known_profiles)}）")
            profile = None
        enabled = {key for key, m in models.items()
                   if profile and profile in m.get("profiles", [])}
        files = model_files(domain)
        n_files += len(files)

        # AC6 反向（票 13）：manifest omittedModels 显式豁免清单——profile 启用的
        # 模型无文件时，必须有带理由的豁免条目，否则 L4 missing-model-file 红。
        # 豁免条目 = {model: 注册表模型键, reason: 非空字符串}；reason 缺失/空串
        # 视为无效豁免（=无豁免），引用未注册模型单独 L1 红。
        omitted: dict[str, str] = {}
        for entry in manifest.get("omittedModels") or []:
            if not isinstance(entry, dict) or "model" not in entry:
                add("L1", "bad-omitted-model", str(domain / "manifest.json"), 0,
                    f"omittedModels 条目必须是含 model/reason 的对象: {entry!r}")
                continue
            om = entry.get("model")
            if om not in models:
                add("L1", "unknown-omitted-model", str(domain / "manifest.json"),
                    0, f"omittedModels 引用未注册模型「{om}」（注册表: {sorted(models)}）")
                continue
            reason = entry.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                continue  # 无理由 = 无效豁免，缺文件时照报 missing-model-file
            omitted[om] = reason.strip()
        # 在场判定按注册文件名（稳健于内容解析失败：文件建了=在场，schema 错误
        # 是 L1 的管辖面，不在此重复追责）
        file_names = {p.name for p in files}
        present_models = {key for key, m in models.items()
                          if m.get("yamlFile") in file_names}

        domain_summaries.append({"domain": dname, "profile": profile,
                                 "files": len(files), "enabled": sorted(enabled),
                                 "omittedModels": sorted(omitted)})

        for path in files:
            rel = str(path)
            try:
                data = load_yaml(path)
            except _YamlSyntaxError as exc:  # AC2
                add("L1", "yaml-syntax", rel, 0, f"YAML 语法错误: {exc}")
                continue
            if data is None or not isinstance(data, dict):
                add("L1", "yaml-syntax", rel, 0, "YAML 顶层必须是映射")
                continue
            for field in COMMON_FIELDS:  # AC3
                if field not in data:
                    add("L1", "missing-common-field", rel,
                        key_line(data, field) or data.line,
                        f"缺少公共字段 `{field}`（公共字段: model_type/version/domain）")
            mtype = data.get("model_type")
            mkey = model_by_type.get(mtype) if isinstance(mtype, str) else None
            if mtype is not None and mkey is None:  # AC3 延伸：类型必须已注册
                add("L1", "unknown-model-type", rel, data.line,
                    f"未知 model_type「{mtype}」（注册表: {sorted(model_by_type)}）")
                continue
            if mkey is None:
                continue
            yaml_file = models[mkey].get("yamlFile")
            name_mismatch = bool(yaml_file) and path.name != yaml_file
            if name_mismatch:  # 票 10 AC4：文件名与 model_type 错挂
                add("L1", "filename-mismatch", rel, data.line,
                    f"文件名「{path.name}」与 model_type「{mtype}」的注册文件名"
                    f"「{yaml_file}」不符（一模型一 YAML、固定文件名，"
                    f"真源 model-registry.json yamlFile）")

            # 元素级结构性必填闸（票 13，真源=model-registry.json
            # requiredElementFields）。文件名错挂时内容与模型的锚已断，闸让位给
            # filename-mismatch，不叠加空壳红因（负变体红因纯净，lessons/13）。
            req_map = models[mkey].get("requiredElementFields") or {}
            if req_map and not name_mismatch:
                elements = collect_elements(data, mkey, prefix2model, ref_keys)
                for eid, mapping in elements:
                    for prefix, fields in req_map.items():
                        if not eid.startswith(prefix):
                            continue
                        for fieldname in fields:
                            if fieldname not in mapping:
                                add("L1", "required-field", rel,
                                    key_line(mapping, fieldname),
                                    f"元素 {eid} 缺必填字段「{fieldname}」"
                                    f"（结构性必填：身份/类型判别/检查锚点/载荷容器，"
                                    f"缺失会使一致性对与引用扫描静默跳过；真源 "
                                    f"model-registry.json {mkey}.requiredElementFields）")

                # 主集合逐字典枚举（票 27）：无 id 也枚举，报缺必填身份字段——
                # 修"无 id 元素混入合法元素即静默逃逸"盲区。空壳守卫收窄为
                # 「主集合键缺失或集合为空」：集合里有字典就逐元素报缺 id，
                # 不再报空壳一条吞掉；纯空集合（terms:[]，REQ-AC3b）语义不变仍走空壳。
                items = list(iter_collection_items(data))
                if not items:
                    add("L1", "required-field", rel, data.line,
                        f"模型 {mkey} 文件主集合键缺失或集合为空（空壳文件：不含任何"
                        f"本模型元素）——结构性必填闸（票 13），真源 model-registry.json "
                        f"{mkey}.requiredElementFields；票 27 收窄：集合内有字典即逐元素"
                        f"枚举、无 id 元素改报缺必填字段，空壳不再兜底")
                id_fields = sorted({f for fields in req_map.values()
                                    for f in fields if f == "id" or f.endswith("Id")})
                for item in items:
                    matched, stray = element_identity(
                        item, mkey, prefix2model, ref_keys)
                    if matched:
                        continue  # 有本模型身份：上方逐字段闸已覆盖
                    hint = next((f"（{k}={item[k]}）" for k in ("name", "term")
                                 if isinstance(item.get(k), str) and item[k]), "")
                    stray_note = (f"；其「{stray[0]}」值「{stray[1]}」不判回本模型"
                                  f"注册前缀" if stray else "")
                    add("L1", "required-field", rel,
                        getattr(item, "line", 0) or data.line,
                        f"主集合元素{hint}缺必填字段「{'/'.join(id_fields)}」"
                        f"{stray_note}（元素枚举不再以有 id 为前提——票 27 修缺 id "
                        f"盲区；真源 model-registry.json {mkey}.requiredElementFields）")

            # 同域元素 id 唯一性（票 38，L1 duplicate-id 身份族）：挂点=票 27 元素
            # 枚举（iter_collection_items 主集合逐字典）。id 索引收 id/*Id 全部
            # 定义键（非 ref 键、值带注册前缀——与 collect_definitions 同口径，
            # M5 的 actorId/roleId/permissionId 跨键同值同判）；撞即报，报文含
            # 双位置（先出现+后出现 file:line 与元素名）。独立于必填闸（不依赖
            # req_map 在场）；文件名错挂的文件跳过——内容与模型锚已断，让位
            # filename-mismatch，不叠杂音红因（沿票 13/16 红因纯净先例）。
            if not name_mismatch:
                ids_of_domain = id_index.setdefault(dname, {})
                for item in iter_collection_items(data):
                    for key, value in item.items():
                        if not (isinstance(key, str)
                                and (key == "id" or key.endswith("Id"))):
                            continue
                        if is_ref_key(key, ref_keys) or not isinstance(value, str):
                            continue
                        if id_model_of(value, prefix2model) is None:
                            continue
                        elem_name = next(
                            (item.get(k) for k in ("name", "term")
                             if isinstance(item.get(k), str) and item[k]), "?")
                        loc = (rel, key_line(item, key), str(key), elem_name)
                        first = ids_of_domain.get(value)
                        if first is None:
                            ids_of_domain[value] = loc
                        else:
                            add("L1", "duplicate-id", rel, loc[1],
                                f"重复 id「{value}」: 先出现 {first[0]}:{first[1]}"
                                f"（元素「{first[3]}」，键 {first[2]}），后出现 "
                                f"{rel}:{loc[1]}（元素「{elem_name}」，键 {key}）"
                                f"——同一 manifest 域「{dname}」之下元素 id 不得"
                                f"重复（票 38 duplicate-id，L1 身份族；id/*Id "
                                f"定义键全收，M5 actorId/roleId/permissionId "
                                f"同判；跨域不判）")

            if mkey not in enabled:  # AC6
                add("L4", "profile-disabled", rel, data.line,
                    f"profile「{profile}」未启用模型 {mkey}，但出现其文件"
                    f"（注册表 profiles: {models[mkey].get('profiles')}）")
            locked = models[mkey].get("lockedFields", {})
            for mapping in iter_mappings(data):  # AC7
                for key in mapping:
                    if isinstance(key, str) and key in locked:
                        add("L4", "field-redefinition", rel, key_line(mapping, key),
                            f"字段「{key}」为换义锁定字段（旧义: {locked[key]}）——"
                            f"禁止复用换义，如需新义请新增字段名")
            depends_on = set(models[mkey].get("dependsOn", [])) | {mkey}
            for mapping in iter_mappings(data):
                for key, value in mapping.items():
                    if not (isinstance(key, str) and is_ref_key(key, ref_keys)):
                        continue
                    for ref in iter_ref_strings(value):
                        if not isinstance(ref, str):
                            continue
                        target_model = id_model_of(ref, prefix2model)
                        if target_model is None:
                            continue
                        allowed = edges.get((mkey, key), depends_on)
                        if target_model not in allowed:  # AC5
                            add("L2", "dep-whitelist", rel, key_line(mapping, key),
                                f"ref 类型越白名单: {mkey}.{key} → {target_model}"
                                f" 不在允许 {sorted(allowed)}（model-deps.json/"
                                f"model-registry.json dependsOn）")
            file_refs = collect_definitions(data, ref_keys, prefix2model)
            defs_by_domain.setdefault(dname, set()).update(file_refs)
            for ref_id, loc in file_refs.items():
                definitions.setdefault(ref_id, (rel, loc))

        # 禁用词拦截面（票 16）：域内 GLS 术语 status 含「禁用」条目的 term+aliases
        # = 机读禁用词表（闸位在 schema_check L4，真源唯一=GLS；运行时拒答是消费侧，
        # 票 17）。对全域文件 name/alias 做子串匹配，命中 = L4 banned-term。
        # GLS 无文件（未建模/旧域）时表为空、闸静默——禁用词拦截随术语表在场而启用。
        glossary_key = model_by_type.get("GLOSSARY")
        if glossary_key:
            banned: list[tuple[str, str, str]] = []
            for path in files:
                try:
                    data_b = load_yaml(path)
                except _YamlSyntaxError:
                    continue  # 语法错误由 L1 yaml-syntax 管辖
                if not isinstance(data_b, dict):
                    continue
                mtype_b = data_b.get("model_type")
                if isinstance(mtype_b, str) and \
                        model_by_type.get(mtype_b) == glossary_key:
                    banned.extend(collect_banned_terms(data_b))
            if banned:
                for path in files:
                    rel_b = str(path)
                    try:
                        data_m = load_yaml(path)
                    except _YamlSyntaxError:
                        continue
                    if not isinstance(data_m, dict):
                        continue
                    mtype_m = data_m.get("model_type")
                    mkey_m = (model_by_type.get(mtype_m)
                              if isinstance(mtype_m, str) else None)
                    if mkey_m is None:
                        continue
                    yaml_file_m = models[mkey_m].get("yamlFile")
                    if yaml_file_m and path.name != yaml_file_m:
                        continue  # filename-mismatch 管辖面，不叠禁用词红因（沿票 13 先例）
                    for value, mapping, key in iter_name_alias_values(data_m):
                        for word, gls_id, status in banned:
                            if word in value:
                                add("L4", "banned-term", rel_b,
                                    key_line(mapping, key),
                                    f"{key}「{value}」命中禁用词「{word}」"
                                    f"（{gls_id}，status={status}）——禁用术语不得"
                                    f"进元素 name/alias（description/notes 提及合法"
                                    f"=文档自由）；真源=域内 GLS 术语表 status 含"
                                    f"「禁用」条目（票 16）")

        # L3 确定性闸（票 41）：指标/SQL/安全的确定性可判子集四项，违规码 l3-*。
        # 域内聚合目录（M1）先行——L3-1/L3-2 的解析基准；文件名错挂的文件跳过
        # 本闸（内容与模型锚已断，让位 filename-mismatch，红因纯净沿票 13/16 先例）。
        agg_mkey = model_by_type.get("OBJECT")
        rule_mkey = model_by_type.get("RULE")
        rep_mkey = model_by_type.get("REPORT")
        if rule_mkey or rep_mkey:
            aggregates = []
            l3_scans = []  # (rel, data, mkey)
            for path_l in files:
                rel_l = str(path_l)
                try:
                    data_l = load_yaml(path_l)
                except _YamlSyntaxError:
                    continue  # 语法错误由 L1 yaml-syntax 管辖
                if not isinstance(data_l, dict):
                    continue
                mtype_l = data_l.get("model_type")
                mkey_l = (model_by_type.get(mtype_l)
                          if isinstance(mtype_l, str) else None)
                if mkey_l is None:
                    continue
                yaml_file_l = models[mkey_l].get("yamlFile")
                if yaml_file_l and path_l.name != yaml_file_l:
                    continue  # filename-mismatch 管辖面，不叠 L3 红因
                l3_scans.append((rel_l, data_l, mkey_l))
                if mkey_l == agg_mkey:
                    aggregates.extend(l3_aggregate_catalog(data_l))
            agg_by_id = {a["id"]: a for a in aggregates
                         if isinstance(a.get("id"), str)}

            # L3-1 M3 规则参数 sourceField 字段存在性（双段形态才判）
            if rule_mkey:
                for rel_l, data_l, mkey_l in l3_scans:
                    if mkey_l != rule_mkey:
                        continue
                    rules_l = data_l.get("rules")
                    if not isinstance(rules_l, list):
                        continue
                    for rule in rules_l:
                        if not isinstance(rule, dict):
                            continue
                        rid = rule.get("id", "?")
                        params = rule.get("inputParams")
                        for param in (params if isinstance(params, list) else []):
                            if not isinstance(param, dict):
                                continue
                            raw = param.get("sourceField")
                            parts = l3_split_source_field(raw)
                            if parts is None:
                                continue  # 非双段形态（无承载字段注记）不在机判面
                            seg, fld = parts
                            agg, layer = l3_resolve_object_segment(seg, aggregates)
                            if agg is None:
                                add("L3", "l3-source-field", rel_l,
                                    key_line(param, "sourceField"),
                                    f"规则 {rid} 参数 sourceField「{raw}」对象段"
                                    f"「{seg}」解析不到域内聚合（匹配序 "
                                    f"{'→'.join(L3_OBJECT_MATCH_ORDER)} 均未唯一"
                                    f"命中）——L3-1（票 41；sourceField 非 ref 键，"
                                    f"悬空不由 dangling-ref 管辖，本码承载）")
                                continue
                            if fld not in agg["attrs"]:
                                add("L3", "l3-source-field", rel_l,
                                    key_line(param, "sourceField"),
                                    f"规则 {rid} 参数 sourceField「{raw}」字段段"
                                    f"「{fld}」不在所指聚合 {agg['id']}"
                                    f"（alias {agg.get('alias')}，匹配层 {layer}）"
                                    f"的 attributes 中——L3-1（票 41）")

            # L3-2 / L3-3 M7 口径表达式引用一致性 + referenceSql 只读性
            if rep_mkey:
                for rel_l, data_l, mkey_l in l3_scans:
                    if mkey_l != rep_mkey:
                        continue
                    qrs = data_l.get("query_reports")
                    if not isinstance(qrs, list):
                        continue
                    for qr in qrs:
                        if not isinstance(qr, dict):
                            continue
                        qid = qr.get("id", "?")
                        alias_map = {}
                        for so in qr.get("sourceObjects") or []:
                            if isinstance(so, dict) and \
                                    isinstance(so.get("alias"), str):
                                alias_map[so["alias"]] = so.get("objectRef")
                        for col in qr.get("resultColumns") or []:
                            if not isinstance(col, dict):
                                continue
                            expr = col.get("sourceExpression")
                            if not isinstance(expr, str) or not expr.strip():
                                continue
                            for token in L3_REF_TOKEN_RE.findall(expr):
                                talias, _, tfield = token.partition(".")
                                if talias not in alias_map:
                                    add("L3", "l3-expression-ref", rel_l,
                                        key_line(col, "sourceExpression"),
                                        f"报表 {qid} sourceExpression「{expr}」"
                                        f"引用别名「{talias}」未在 sourceObjects "
                                        f"声明（声明集 {sorted(alias_map)}）——"
                                        f"L3-2（票 41）")
                                    continue
                                agg_target = agg_by_id.get(alias_map[talias])
                                if agg_target is None:
                                    continue  # objectRef 悬空=dangling-ref 管辖（红因不混）
                                if tfield not in agg_target["attrs"]:
                                    add("L3", "l3-expression-ref", rel_l,
                                        key_line(col, "sourceExpression"),
                                        f"报表 {qid} sourceExpression「{expr}」"
                                        f"字段「{token}」不在别名「{talias}」所指"
                                        f"聚合 {alias_map[talias]} 的 attributes 中"
                                        f"——L3-2（票 41）")
                        sql = qr.get("referenceSql")
                        if isinstance(sql, str) and sql.strip():
                            hits = sorted({m.group(0).upper() for m in
                                           L3_SQL_BLACKLIST_RE.finditer(sql)})
                            if hits:
                                add("L3", "l3-sql-readonly", rel_l,
                                    key_line(qr, "referenceSql"),
                                    f"报表 {qid} referenceSql 命中只读黑名单词 "
                                    f"{hits}（DML/DDL，大小写不敏感+\\b 词边界）"
                                    f"——L3-3（票 41；referenceSql 可选字段在场才扫，"
                                    f"必须只读 SELECT 形态）")

            # L3-4 M3 规则落地形态二选一（schema.md §6；票 13 缺口清单登记项）
            if rule_mkey:
                for rel_l, data_l, mkey_l in l3_scans:
                    if mkey_l != rule_mkey:
                        continue
                    rules_l = data_l.get("rules")
                    if not isinstance(rules_l, list):
                        continue
                    for rule in rules_l:
                        if not isinstance(rule, dict):
                            continue
                        rtype = rule.get("ruleType")
                        if not isinstance(rtype, str) or not rtype.strip():
                            continue  # ruleType 缺失归 L1 required-field，不叠红因
                        has_expr = (isinstance(rule.get("expression"), str)
                                    and bool(rule["expression"].strip()))
                        has_narr = (isinstance(rule.get("narrative"), str)
                                    and bool(rule["narrative"].strip()))
                        if rtype.strip().lower() == "expression":
                            form_ok = has_expr
                        else:  # 值集实读=VALIDATION/CALCULATION/DERIVATION/TRANSFORMATION/RISK
                            form_ok = has_expr or has_narr
                        if not form_ok:
                            rid = rule.get("id", "?")
                            add("L3", "l3-rule-form", rel_l,
                                getattr(rule, "line", 0) or data_l.line,
                                f"规则 {rid}（ruleType={rtype}）落地形态缺失："
                                f"expression/narrative 二选一（schema.md §6）均"
                                f"不在场或为空——L3-4（票 41；ruleType 字段本身"
                                f"缺失归 L1 required-field 管辖，不叠红因）")

        # AC6 反向（票 13）：profile 启用的模型缺文件且无带理由豁免 = L4 红。
        # profile 未知时 enabled 为空、不触发（unknown-profile 已单独红）。
        if profile is not None:
            for mkey in sorted(enabled):
                if mkey in present_models or mkey in omitted:
                    continue
                add("L4", "missing-model-file", str(domain / "manifest.json"), 0,
                    f"profile「{profile}」启用模型 {mkey}，但域内无 "
                    f"{models[mkey].get('yamlFile')} 文件且 omittedModels 无带理由"
                    f"豁免条目（AC6 反向，票 13；确属有意裁剪须在 manifest 登记 "
                    f"omittedModels: [{{\"model\": \"{mkey}\", \"reason\": \"…\"}}]）")

    # 悬空引用统一判定（定义收集完后）
    for domain in domains:
        mc_dc = load_json(domain / "manifest.json") if (domain / "manifest.json").is_file() else {}
        dname_dc = mc_dc.get("domain", domain.name) if isinstance(mc_dc, dict) else domain.name
        for path in model_files(domain):
            rel = str(path)
            try:
                data = load_yaml(path)
            except _YamlSyntaxError:
                continue
            if not isinstance(data, dict):
                continue
            mtype = data.get("model_type")
            if not isinstance(mtype, str) or mtype not in model_by_type:
                continue
            for mapping in iter_mappings(data):
                for key, value in mapping.items():
                    if not (isinstance(key, str) and is_ref_key(key, ref_keys)):
                        continue
                    for ref in iter_ref_strings(value):
                        if isinstance(ref, str) and id_model_of(ref, prefix2model) and ref not in defs_by_domain.get(dname_dc, set()):
                            add("L2", "dangling-ref", rel, key_line(mapping, key),
                                f"悬空引用: ref 字段「{key}」指向的 {ref} "
                                f"在本域（{dname}）内无 ID 定义"
                                f"（跨域引用不合法，票 76）")

    # ---------- 一致性对核验（票 11；digest §12.2 本仓可行子集，schema.md §14） ----------
    # 元素收集：锚定各模型的结构性承载字段（behaviorType/targetRef/behaviorRef/
    # activities），模型定位走注册表 modelType（脚本不硬编码模型键名）。涉事 ID 的
    # 存在性由上方 dangling-ref 承载，此处只判语义闭合向。
    m2_key = model_by_type.get("BEHAVIOR")
    m5_key = model_by_type.get("ACTOR")
    m6_key = model_by_type.get("FLOW")
    m7_key = model_by_type.get("REPORT")
    behaviors: dict[str, tuple[dict, str]] = {}
    permissions: dict[str, tuple[dict, str]] = {}
    query_reports: list[tuple[str, dict, str]] = []
    flows: list[tuple[str, dict, str]] = []
    behaviors_by_domain: dict[str, dict] = {}
    permissions_by_domain: dict[str, dict] = {}
    query_reports_by_domain: dict = {}
    flows_by_domain: dict = {}
    if m2_key or m5_key or m6_key or m7_key:
        for domain in domains:
            mc = load_json(domain / "manifest.json") if (domain / "manifest.json").is_file() else {}
            dname_c = mc.get("domain", domain.name) if isinstance(mc, dict) else domain.name
            bh_d = behaviors_by_domain.setdefault(dname_c, {})
            pm_d = permissions_by_domain.setdefault(dname_c, {})
            qr_d = query_reports_by_domain.setdefault(dname_c, [])
            fl_d = flows_by_domain.setdefault(dname_c, [])
            for path in model_files(domain):
                rel_c = str(path)
                try:
                    data_c = load_yaml(path)
                except _YamlSyntaxError:
                    continue
                if not isinstance(data_c, dict):
                    continue
                mtype_c = data_c.get("model_type")
                mkey_c = model_by_type.get(mtype_c) if isinstance(mtype_c, str) else None
                if m2_key and mkey_c == m2_key:
                    for eid, mapping in collect_elements(
                            data_c, m2_key, prefix2model, ref_keys):
                        if "behaviorType" in mapping:
                            bh_d.setdefault(eid, (mapping, rel_c))
                elif m5_key and mkey_c == m5_key:
                    for eid, mapping in collect_elements(
                            data_c, m5_key, prefix2model, ref_keys):
                        if "targetRef" in mapping:
                            pm_d.setdefault(eid, (mapping, rel_c))
                elif m7_key and mkey_c == m7_key:
                    for eid, mapping in collect_elements(
                            data_c, m7_key, prefix2model, ref_keys):
                        if "behaviorRef" in mapping:
                            qr_d.append((eid, mapping, rel_c))
                elif m6_key and mkey_c == m6_key:
                    for eid, mapping in collect_elements(
                            data_c, m6_key, prefix2model, ref_keys):
                        if "activities" in mapping:
                            fl_d.append((eid, mapping, rel_c))

    # P1 M7↔M2 严格一对一：M7.behaviorRef 必指向 behaviorType=QUERY 的行为，
    # 且同一查询行为不得被第二个 M7 绑定（依赖边单向 M7→M2，反向经 ref 反查，
    # schema.md §2/§9；本仓 M2 不写 queryReportRef）
    # 合入全局扁平 dict（既有判定块消费面零改动；票 76 域分桶后回填）
    for d in behaviors_by_domain.values():
        behaviors.update(d)
    for d in permissions_by_domain.values():
        permissions.update(d)
    for d in query_reports_by_domain.values():
        query_reports.extend(d)
    for d in flows_by_domain.values():
        flows.extend(d)

    if m2_key and m7_key:
        first_bound: dict[str, str] = {}
        for qr_id, qr, rel_c in query_reports:
            bref = qr.get("behaviorRef")
            if not isinstance(bref, str):
                continue
            beh = behaviors.get(bref)
            if beh is None:
                continue  # 指向不存在行为 = dangling-ref 已报
            if beh[0].get("behaviorType") != "QUERY":
                add("L2", "consistency-redirection", rel_c, key_line(qr, "behaviorRef"),
                    f"一致性对 P1（M7↔M2 严格一对一）: 报表 {qr_id} 的 behaviorRef"
                    f"「{bref}」指向 behaviorType={beh[0].get('behaviorType')} 的行为，"
                    f"必须指向 behaviorType=QUERY 的 M2 行为"
                    f"（依据 M7.behaviorRef ↔ M2.behaviorType，schema.md §14）")
                continue
            if bref in first_bound:
                add("L2", "consistency-not-one-to-one", rel_c, key_line(qr, "behaviorRef"),
                    f"一致性对 P1（M7↔M2 严格一对一）: M2 查询行为「{bref}」已被报表 "
                    f"{first_bound[bref]} 绑定，报表 {qr_id} 再次绑定——同一行为不得被"
                    f"两个 M7 对象共享（依据 M7.behaviorRef 反查去重，schema.md §14）")
            else:
                first_bound[bref] = qr_id

    # P2 M2.requiredPermissions ↔ M5 双向闭合：requiredPermissions 指到的每个
    # PERM 的 targetRef 必回指该行为（存在性=dangling-ref：requiredPermissions 在
    # refKeys 且有 M2→M5 边）。锚定 M2.requiredPermissions 面——M5 侧单面登记权限
    # 承载岗位职责（行为 requiredPermissions 留空）不判红（schema.md §7/§14）
    if m2_key and m5_key:
        for bh_id, (bh, rel_c) in behaviors.items():
            req = bh.get("requiredPermissions")
            if not req:
                continue
            for pref in iter_ref_strings(req):
                if not isinstance(pref, str):
                    continue
                perm = permissions.get(pref)
                if perm is None:
                    continue  # 指向不存在权限 = dangling-ref 已报
                perm_target = perm[0].get("targetRef")
                if perm_target != bh_id:
                    add("L2", "consistency-permission", rel_c,
                        key_line(bh, "requiredPermissions"),
                        f"一致性对 P2（M2.requiredPermissions↔M5）: 行为 {bh_id} 的 "
                        f"requiredPermissions「{pref}」存在，但其 targetRef="
                        f"{perm_target} 未回指本行为——权限须双向闭合"
                        f"（依据 M2.requiredPermissions ↔ M5.targetRef，schema.md §14）")

    # P3 M6 活动 roleRef ∈ 流程 roleRefs（活动级角色必须是流程角色集的子集，
    # digest §12.2 P3 / v9 §6.5；ROLE 本身的存在性由 dangling-ref 承载）
    if m6_key:
        for flow_id, flow, rel_c in flows:
            role_refs = {r for r in iter_ref_strings(flow.get("roleRefs") or [])
                         if isinstance(r, str)}
            activities = flow.get("activities")
            if not isinstance(activities, list):
                continue
            for act in activities:
                if not isinstance(act, dict):
                    continue
                for rref in iter_ref_strings(act.get("roleRef") or []):
                    if not isinstance(rref, str) or rref in role_refs:
                        continue
                    add("L2", "consistency-flow-role", rel_c, key_line(act, "roleRef"),
                        f"一致性对 P3（M6 活动 roleRef∈流程 roleRefs）: 流程 {flow_id} "
                        f"活动 {act.get('activityId', '?')} 的 roleRef「{rref}」不在"
                        f"流程 roleRefs {sorted(role_refs)} 内"
                        f"（依据 M6.roleRef ⊆ M6.roleRefs，schema.md §14）")

    by_level = {lv: sum(1 for v in violations if v["level"] == lv)
                for lv in ("L1", "L2", "L3", "L4")}
    return {
        "status": "fail" if violations else "pass",
        "target": str(target),
        "schemaDir": str(schema_dir),
        "domains": domain_summaries,
        "files": n_files,
        "levels": by_level,
        "violations": violations,
    }


def print_human(report: dict) -> None:
    domains = "、".join(
        f"{d['domain']}(profile={d['profile']},{d['files']}文件)"
        for d in report["domains"]) or "无域"
    print(f"语义闸 schema_check — {report['target']}")
    print(f"域: {domains}；模型文件 {report['files']} 个")
    for v in report["violations"]:
        loc = f"{v['file']}:{v['line']}" if v["line"] else v["file"]
        print(f"[{v['level']}][{v['kind']}] {loc} — {v['message']}")
    lv = report["levels"]
    if report["status"] == "pass":
        print("L1: 0 | L2: 0 | L3: 0 | L4: 0")
        print("语义闸: 全过")
    else:
        print(f"L1: {lv['L1']} | L2: {lv['L2']} | L3: {lv['L3']} | L4: {lv['L4']}")
        print(f"语义闸: {sum(lv.values())} 处违规")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="语义 CI L1–L4 闸（specs/schema_check.md；票 41 增 L3 确定性子集）")
    ap.add_argument("target", help="ontology 目录（仓根或单域目录）")
    ap.add_argument("--json", action="store_true", help="机读 JSON 输出（供 CI 消费）")
    args = ap.parse_args(argv)
    try:
        report = run(Path(args.target))
    except ValueError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

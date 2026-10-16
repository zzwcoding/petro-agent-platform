"""井号名录查询卡（2026-10-17 流水 70——Owner 批「让 LLM 用工具查井号」方案）。

病灶（真机 run-e1b6ff1e）：`table_schema` 的 dim_well 卡只给结构不给行值，120 口
井号锁在软失败域闸内部（`appv2/query/pg_wells.py`），模型「主体在不在」只能猜/
反问（反问四选项即该病灶）。本批修法五面落测：

① **名录随卡**：dim_well 卡附【井号名录】段（按区块分组、全角分隔、共 N 口·
dim_well 计数；**discover 现读**——非常驻注入：常驻卡片段真源
`tools.ALL_SCHEMA_CARDS` 零增重）；
② **归一比对**：名录匹配前走本体 `RULE-PETRO-005` 井号归一（`tools.well_ids`
单点）——变体形 `w-11`／`W011`／`w 11`／`W_11` 命中共册井 `W-11`；
③ **不猜纪律**：名录查不到如实 no_hit（不猜最近井、不做近似匹配）；
④ **现读不冻**：名录随数据面现读（取值时点＝每次调用，非装配期快照）；
⑤ **零模型零语义判定**：归一/比对面 AST 扫描（无模型通道、无词表／正则语义判定）。

另钉：参数三选一（area／table／well 同给不收——fail-closed）、读缝未接线与现读
失败两面如实告知（不静默冒充空名录）、超限截断＋计数照报、读缝单源（井闭世界与
名录同一次读取）。
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Any

import pytest

from appv2.query import pg_wells
from appv2.tools import (
    ALL_SCHEMA_CARDS,
    CATEGORY_BAD_ARGS,
    SCHEMA_PROBE,
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    ToolRegistry,
    normalize_well_id,
)
from appv2.tools.schema import ToolContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HANDLERS = _REPO_ROOT / "appv2" / "tools" / "handlers.py"
_WELL_IDS = _REPO_ROOT / "appv2" / "tools" / "well_ids.py"

CTX = ToolContext(actor="dev-u1", budget=4)

# 名录替身（内存面——不真连库）：N-01／n2（变体形——同一口井）、W011（变体形
# →W-11）、X-9（空区块＝未标）。
_ROWS: tuple[tuple[str, str], ...] = (
    ("N-01", "渤中"),
    ("n2", "渤中"),
    ("W011", "渤南"),
    ("X-9", ""),
)

_ROSTER_HEAD = "【井号名录】"
_WELL_SEP = "、"
_GROUP_SEP = "；"
_KV_SEP = "："


def _registry(roster: Any = None) -> ToolRegistry:
    """registry＋井名录取值缝（入参＝行集或 loader 函数；None＝未接线）。"""
    if roster is None:
        loader = None
    elif callable(roster):
        loader = roster
    else:
        loader = lambda: roster  # noqa: E731  # 行集替身包成现读缝
    return ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(),
        well_roster=loader,
    )


def _call(registry: ToolRegistry, args: dict[str, Any]) -> Any:
    return asyncio.run(registry.call(SCHEMA_PROBE, args, CTX))


def _text(result: Any) -> str:
    return "\n".join(obs.content for obs in result.observations)


def _by_kind(result: Any, kind: str) -> list[Any]:
    return [obs for obs in result.observations if obs.locator.get("kind") == kind]


# ---------- ① 名录随卡（dim_well 卡＋区块分组；常驻面零增重） ----------


def test_dim_well_card_carries_roster_grouped_by_block() -> None:
    """discover dim_well（按名与按面两径）→卡含名录段＋按区块分组＋共 N 口 计数。"""
    registry = _registry(_ROWS)
    by_name = _call(registry, {"table": "dim_well"})
    assert by_name.status == "ok"
    assert len(by_name.observations) == 1
    card = by_name.observations[0].content
    # 结构卡本体逐字在前（名录是附加段——卡头/列面零改动）。
    assert card.startswith("表 agg.dim_well（井维度·PK well_id）：well_id（井号）、")
    assert _ROSTER_HEAD in card
    assert "共 4 口·dim_well" in card  # 计数＝归一后口数（n2 与 N-01 同口不重计）
    assert "现读" in card
    # 按区块分组（区块名后全角「：」、井号间全角「、」、组间全角「；」）。
    assert f"渤中{_KV_SEP}N-01{_WELL_SEP}N-02" in card
    assert f"渤南{_KV_SEP}W-11" in card
    assert f"未标区块{_KV_SEP}X-09" in card
    assert _GROUP_SEP in card
    # 观察来源链仍归 dim_well 卡（source_id 逐字＝卡头）。
    assert by_name.observations[0].source_id == "表 agg.dim_well（井维度·PK well_id）"
    # 按面（area=agg）三卡照旧；名录段只随 dim_well 卡（其余卡零增重）。
    agg = _call(registry, {"area": "agg"})
    assert len(agg.observations) == 3
    assert sum(_ROSTER_HEAD in obs.content for obs in agg.observations) == 1
    # 全卡形（无参）同款：名录段恰一处。
    all_cards = _call(registry, {})
    assert sum(_ROSTER_HEAD in obs.content for obs in all_cards.observations) == 1


def test_roster_not_in_resident_card_projection() -> None:
    """非常驻注入钉：常驻卡片段真源（`ALL_SCHEMA_CARDS`——台账常驻块/结构卡集合）

    不携【井号名录】段（顺「常驻块瘦身」公共项——名录只在 discover 响应里现读）。
    """
    assert all(_ROSTER_HEAD not in card for card in ALL_SCHEMA_CARDS)
    dim_well_cards = [card for card in ALL_SCHEMA_CARDS if "dim_well" in card]
    assert dim_well_cards == [
        "表 agg.dim_well（井维度·PK well_id）：well_id（井号）、block_name（区块）、"
        "field_name（油田）"
    ]


def test_roster_over_limit_truncated_with_count() -> None:
    """体量纪律钉：名录超限即截断＋「共 N 口」计数照报（计数＝真值，不因截断失真）。"""
    rows = tuple((f"N-{index:02d}", "渤中") for index in range(1, 301))
    card = _call(_registry(rows), {"table": "dim_well"}).observations[0].content
    assert "共 300 口·dim_well" in card
    assert "名录超限，只列前 240 口" in card
    listed = card.split(_ROSTER_HEAD, 1)[1].split(_KV_SEP, 1)[1]
    listed = listed.split("…（名录超限", 1)[0]
    assert len(listed.split(_WELL_SEP)) == 240


# ---------- ② 归一比对（RULE-PETRO-005——变体形命中） ----------


@pytest.mark.parametrize(
    "raw", ["W-11", "w-11", "W011", "w011", "w 11", "W_11", "W－11"]
)
def test_well_lookup_variant_forms_hit_canonical(raw: str) -> None:
    """变体形（去连字符/乱连字符/空白污染/大小写混写）归一后命中共册井 W-11。"""
    result = _call(_registry(_ROWS), {"well": raw})
    assert result.status == "ok"
    hits = _by_kind(result, "well_lookup")
    assert len(hits) == 1, f"{raw} 未命中名录：{_text(result)}"
    assert hits[0].source_id == "W-11"
    assert hits[0].locator["table"] == "agg.dim_well"
    assert hits[0].locator["block_name"] == "渤南"
    assert "井号在册：W-11" in hits[0].content
    # 查值形照携 dim_well 卡（含名录段——结构卡随行）
    assert _ROSTER_HEAD in _text(result)


@pytest.mark.parametrize(
    "raw, expect", [("n2", "N-02"), ("N-2", "N-02"), ("n 02", "N-02"), ("N02", "N-02")]
)
def test_well_lookup_variant_forms_hit_n_series(raw: str, expect: str) -> None:
    hits = _by_kind(_call(_registry(_ROWS), {"well": raw}), "well_lookup")
    assert len(hits) == 1
    assert hits[0].source_id == expect
    assert hits[0].locator["block_name"] == "渤中"


@pytest.mark.parametrize(
    "raw, normalized",
    [
        ("N2", "N-02"),
        ("n-2", "N-02"),
        (" N 02 ", "N-02"),
        ("N_2", "N-02"),
        ("N－2", "N-02"),
        ("w-11", "W-11"),
        ("W011", "W-11"),
        ("X-9", "X-09"),
        ("", ""),  # 空＝not-ok
        ("abc", ""),  # 非井号形＝not-ok（不猜）
        ("N-01A", ""),  # 登记外变体＝not-ok
        ("N-0001", ""),  # 位数越界（规则 \d{1,3}）＝not-ok
    ],
)
def test_normalize_well_id_rule_petro_005(raw: str, normalized: str) -> None:
    """RULE-PETRO-005 归一表逐字（变体四类归一到规范形；匹配失败＝空串不猜）。"""
    assert normalize_well_id(raw) == normalized


def test_normalize_well_id_idempotent() -> None:
    """幂等（规则原文「归一表幂等」——规范形再归一等值）。"""
    for raw in ("n2", "W011", "w 11", "N-01"):
        once = normalize_well_id(raw)
        assert normalize_well_id(once) == once


# ---------- ③ 不猜纪律（查不到如实 no_hit，不猜最近井） ----------


@pytest.mark.parametrize("raw", ["X-99", "N-00", "N-03", "abc", "渤海油田", "W-1"])
def test_well_lookup_miss_is_honest_no_hit(raw: str) -> None:
    """不在册名如实 no_hit（notice；零 well_lookup 观察）——不猜最近井/近似匹配。

    `N-00`／`N-03` 是「最近井」诱饵形（册内最近邻 N-01／N-02）：如实 no_hit。
    """
    result = _call(_registry(_ROWS), {"well": raw})
    assert result.status == "ok"
    assert _by_kind(result, "well_lookup") == []
    notices = _by_kind(result, "notice")
    assert len(notices) == 1
    assert notices[0].locator["notice_type"] == "no_hit"
    assert notices[0].source_id == "no_hit"
    assert "未命中名录" in notices[0].content
    assert "不猜最近井" in notices[0].content
    assert raw in notices[0].content


def test_well_lookup_is_read_only_no_write_face() -> None:
    """查值只读零写副作用（INV-2）：registry 公开面不变、查值不触三引擎。"""
    registry = _registry(_ROWS)
    assert set(vars(registry)) == {"_tools"}
    result = _call(registry, {"well": "w-11"})
    assert result.status == "ok"


# ---------- ④ 现读不冻（取值时点＝每次调用） ----------


def test_roster_read_live_per_call_not_frozen_snapshot() -> None:
    """名录随数据面现读（替身两面换值）——两次 discover 各取当次行集。"""
    calls: list[int] = []

    def loader() -> tuple[tuple[str, str], ...]:
        calls.append(len(calls) + 1)
        return _ROWS if len(calls) == 1 else (("Z-16", "渤西"),)

    registry = _registry(loader)
    first = _text(_call(registry, {"table": "dim_well"}))
    second = _text(_call(registry, {"table": "dim_well"}))
    assert len(calls) == 2, "名录未按调用现读（出现了冻结快照/缓存）"
    assert "N-01" in first and "Z-16" not in first
    assert "Z-16" in second and "N-01" not in second
    assert "共 4 口·dim_well" in first and "共 1 口·dim_well" in second


def test_well_lookup_reads_live_roster() -> None:
    """查值面同款现读：第二调用换行集后，同名井由在册转不在册（如实）。

    且**每次调用恰读一次**（卡面名录段与判据同源同一行集——同一响应内不自相
    矛盾，也零重复读库）。
    """
    calls: list[int] = []

    def loader() -> tuple[tuple[str, str], ...]:
        calls.append(len(calls) + 1)
        return (("W-11", "渤南"),) if len(calls) == 1 else ()

    registry = _registry(loader)
    first = _call(registry, {"well": "w-11"})
    assert len(_by_kind(first, "well_lookup")) == 1
    assert len(calls) == 1, "单次查值重复读名录"
    assert "W-11" in _text(first)
    second = _call(registry, {"well": "w-11"})
    assert _by_kind(second, "well_lookup") == []
    assert _by_kind(second, "notice")[0].locator["notice_type"] == "no_hit"
    assert len(calls) == 2


def test_data_wells_projects_same_roster_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """读缝单源钉：井闭世界（域闸）与名录（卡面）走同一次读取（零第二份读法）。"""

    async def fake_load(specs: tuple[Any, ...]) -> tuple[tuple[str, str], ...]:
        return (("N-01", "渤中"), ("W011", "渤南"))

    monkeypatch.setattr(pg_wells, "_load_roster", fake_load)
    assert pg_wells.production_well_roster(() )() == (
        ("N-01", "渤中"),
        ("W011", "渤南"),
    )
    assert pg_wells.production_data_wells(())() == frozenset({"N-01", "W011"})
    # schema 限定仍钉（agg 星型不在默认 search_path——裸表名＝UndefinedTableError）
    assert pg_wells._DIM_WELL.schema == "agg"
    assert "block_name" in {col.name for col in pg_wells._DIM_WELL.c}


# ---------- 读缝未接线/现读失败/参数面（如实告知，零静默） ----------


def test_well_lookup_without_roster_seam_is_honest() -> None:
    """读缝未接线（旧装配/测试替身影）：卡面照静态形（零漂移）＋查值如实告知不可得。"""
    result = _call(_registry(None), {"well": "W-11"})
    assert result.status == "ok"
    assert _ROSTER_HEAD not in _text(result)  # 未接线＝静态卡逐字（无名录段）
    notices = _by_kind(result, "notice")
    assert len(notices) == 1
    assert notices[0].locator["notice_type"] == "well_roster_unavailable"
    assert "未接线" in notices[0].content and "不猜" in notices[0].content


def test_roster_read_failure_reported_not_silently_empty() -> None:
    """现读失败如实承载（不静默吞成「空名录」——空名录是合法业务态，两者不许混）。"""

    def boom() -> tuple[tuple[str, str], ...]:
        raise RuntimeError("数据面熄火")

    registry = _registry(boom)
    card = _text(_call(registry, {"table": "dim_well"}))
    assert "【井号名录】现读失败（数据面熄火）" in card
    assert "共 0 口" not in card  # 不冒充空名录
    lookup = _call(registry, {"well": "W-11"})
    assert _by_kind(lookup, "well_lookup") == []
    assert _by_kind(lookup, "notice")[0].locator["notice_type"] == ("well_roster_unavailable")


def test_empty_roster_is_legal_state() -> None:
    """现读为空（合法态）与读失败分形：如实报 0 口，查值一律 no_hit。"""
    registry = _registry(())
    card = _text(_call(registry, {"table": "dim_well"}))
    assert "共 0 口·dim_well" in card and "现读为空" in card
    result = _call(registry, {"well": "W-11"})
    assert _by_kind(result, "well_lookup") == []
    assert _by_kind(result, "notice")[0].locator["notice_type"] == "no_hit"


def test_well_arg_exclusive_with_area_and_table() -> None:
    """参数三形互斥（fail-closed）：well 与 area/table 同给＝bad_args，引擎零调用。"""
    registry = _registry(_ROWS)
    for args in ({"well": "W-11", "area": "agg"}, {"well": "W-11", "table": "dim_well"}):
        result = _call(registry, args)
        assert result.status == "failed"
        assert result.error is not None
        assert result.error.category == CATEGORY_BAD_ARGS
        assert "二选一" in result.error.message
    # area 与 table 同给照旧拒（回归）。
    both = _call(registry, {"area": "agg", "table": "dim_well"})
    assert both.status == "failed"


def test_well_arg_declared_in_args_schema() -> None:
    """args_schema 契约：`well` 在册（minLength=1）——参数面机读可发现。"""
    registry = _registry(_ROWS)
    schema = next(
        d.args_schema for d in registry.descriptors() if d.name == SCHEMA_PROBE
    )
    props = schema["properties"]
    assert set(props) == {"area", "table", "well"}
    assert props["well"]["type"] == "string" and props["well"]["minLength"] == 1
    description = next(
        d.description for d in registry.descriptors() if d.name == SCHEMA_PROBE
    )
    assert "井号名录" in description and "well" in description


# ---------- ⑤ 零模型零语义判定面（AST 扫描——归一/比对面） ----------


_MODEL_CALL_FORMS = {"complete", "acomplete", "invoke", "ainvoke", "generate", "agenerate"}
_MODEL_CHANNEL_PARTS = ("llm", "gateway", "litellm", "openai", "langchain", "embedding")
_WELL_FUNCS = (
    "_well_roster_rows",
    "_well_roster_section",
    "_dim_well_card",
    "_schema_cards",
    "_well_lookup_observations",
)


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _model_violations(tree: ast.Module) -> list[str]:
    """模型通道探测（模型调用形／LLM 通道 import）。"""
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name)):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            if name in _MODEL_CALL_FORMS:
                findings.append(f"L{node.lineno} 模型调用形：{name}")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                if any(part in name for part in _MODEL_CHANNEL_PARTS):
                    findings.append(f"L{node.lineno} import 模型通道：{name}")
    return findings


def _semantic_judgment_violations(tree: ast.Module) -> list[str]:
    """语义判定面探测（含汉字串的字面集合／非 ASCII 成员判据——词表形）。"""
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for item in node.elts:
                if (
                    isinstance(item, ast.Constant)
                    and isinstance(item.value, str)
                    and _has_cjk(item.value)
                ):
                    findings.append(f"L{node.lineno} 字面集合含汉字串（语义词表形）")
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, (ast.In, ast.NotIn)):
                    for operand in (node.left, *node.comparators):
                        if (
                            isinstance(operand, ast.Constant)
                            and isinstance(operand.value, str)
                            and not operand.value.isascii()
                        ):
                            findings.append(f"L{node.lineno} 非 ASCII 成员判据：{operand.value!r}")
    return findings


def _function_trees(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }


def _docstring_ids(tree: ast.Module) -> set[int]:
    """文档字符串常量 id 集（说明面不算字面——扫的是可执行面）。"""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        body = getattr(node, "body", [])
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            ids.add(id(body[0].value))
    return ids


def test_well_ids_zero_model_zero_semantic_judgment_scan() -> None:
    """⑤｜归一/比对面＝形态处理（零模型、零词表）：AST 扫描 well_ids 与 handlers 名录段。"""
    well_ids_tree = ast.parse(_WELL_IDS.read_text(encoding="utf-8"))
    handlers_tree = ast.parse(_HANDLERS.read_text(encoding="utf-8"))
    assert _model_violations(well_ids_tree) == []
    assert _semantic_judgment_violations(well_ids_tree) == []
    # well_ids 全文零汉字字面（形态表＋正则形判定——无任何中文词表；文档字符串不计）。
    docstrings = _docstring_ids(well_ids_tree)
    assert not any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _has_cjk(node.value)
        and id(node) not in docstrings
        for node in ast.walk(well_ids_tree)
    )
    functions = _function_trees(handlers_tree)
    scoped = [functions[name] for name in _WELL_FUNCS if name in functions]
    assert len(scoped) == len(_WELL_FUNCS), "名录段函数缺席——扫描面空转"
    for node in scoped:
        tree = ast.Module(body=[node], type_ignores=[])
        assert _model_violations(tree) == []
        assert _semantic_judgment_violations(tree) == [], node.name
    # 扫描器非空转（同款探测器对反例报警——防假绿）。
    assert _model_violations(ast.parse("x.complete(prompt)\n")) != []
    assert _model_violations(ast.parse("from appv2.infra.llm_client import X\n")) != []
    assert _semantic_judgment_violations(ast.parse('WORDS = ["躺井", "时率"]\n')) != []

"""prompts 块验收（-04a 常量族/任务书/答案轮＋-04b 决策轮/常驻块/样例＋-04c 元面·边界·保留）。

票面对象＝`specs/prompts.md`「验收测试」表逐行（23 行全量：-04a 取第 1–8、16–18 行；-04b 取第
9–15 行；-04c 取第 19–23 行——测试标识同规格列、`#` 保留规格表行序）；
测试网钉＝pin-24（落点行 1：合同常量逐字稳定面）／pin-03（落点行 2：答案要求③逐字在场）／
pin-13（落点行 18：答案轮禁令件在场＝合同侧）——3 条 pin 行全在 -04a，-04b／-04c 零 pin 行。

逐字稿真源（迁移照抄面）：`appv2/runtime/orientation.py` `_ORIENT_*`／`_ANSWER_REQUIREMENTS`
／`answer_turn_preamble`／`anchor_line`／`render_decompose_example`、`appv2/runtime/guide.py`
三合同、`appv2/runtime/graph.py` `_ANSWER_INSTRUCTION`（族⑤去重后形态——流水 43①）＋
`clarify_node`／`toolmatch_node` 相位包与增量条段＋`_resident_block`／`_resident_sources`。

**已登记张力（本件如实标注，不静默）**：族①成员 `TASK_BOOK_EXAMPLES`＝V1 Owner 审定三则样例
逐字迁移，其示例文内含实仓台账真源词（如「抽油机时率」「躺井」「Y-41」）；行为 11 的「示例词
纪律同款」（`arch/P4b` A-P4b-60 先例）若按实仓台账词集解释，本常量需改写三则样例——本票无逐字稿，
不自行裁量，登记待主窗裁决。本件行 16 的扫描词集＝本文件 fixture 投影的台账词集＋井号形＋
水位日形（规格 行为 11 判据面原文「fixture 词集与水位日形交集＝∅」）。

**行 12／13 的判据面说明（-04b 如实标注）**：规格 行为 8／9 的「三删段名字面缺席」按**段名形**落网
（`◆ **发射判据**`／`◆ **指标名册**`／`收口硬规则`——V1 三删段名形＋先例
`tests/domains/test_v2_v259_clarify_assembly.py:24-26`）：族②常量本体（V1 `CLARIFY_CONTRACT` 逐字
迁移）内含 inline 句「发射判据：台账命中＋窗已定＝分解完毕」——A-P4b-30 载该句正是「与相位合同
发射判据逐字重复」的那处重复，故「发射判据」四字的**全输出缺席**读法与常量逐字迁移相抵、不可满足。
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import string
import sys
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict
from datetime import date
from importlib import import_module
from pathlib import Path
from typing import Any, get_type_hints

import pytest

from appv2.runtimev2.prompts import (
    ANSWER_DRAFT_CONTRACT,
    ANSWER_REQUIREMENTS,
    ASSEMBLY_FUNCTIONS,
    CLARIFY_EMISSION_CONTRACT,
    CLARIFY_FINALIZE_BOUNDARY,
    CLARIFY_PHASE_HEAD,
    CONTRACT_CONSTANT_FAMILIES,
    DECISION_PHASES,
    GUIDE_REFERENCE_HEAD,
    LEDGER_DICT_NOTE,
    PHASE_CLARIFY,
    PHASE_TOOLMATCH,
    RESIDENT_BLOCK_BEGIN,
    RESIDENT_BLOCK_END,
    SUMMARY_CONTRACT,
    TASK_BOOK_EXAMPLES,
    TASK_BOOK_OUTPUT_CONTRACT,
    TASK_BOOK_REDLINE,
    TASK_BOOK_SCENE,
    TASK_BOOK_TASK,
    TOOLMATCH_EMISSION_CONTRACT,
    TOOLMATCH_PHASE_HEAD,
    anchor_line,
    assemble_answer_prompt,
    assemble_decision_increment,
    assemble_decision_package,
    assemble_task_book,
    render_decompose_example,
    render_ledger_resident_block,
)
from appv2.runtimev2.prompts import constants as constants_module
from appv2.runtimev2.state import MAX_DISCOVERS_PER_RUN, RunState

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
_PROMPTS_DIR = _V2_DIR / "prompts"
_CONSTANTS_FILE = _PROMPTS_DIR / "constants.py"
# 四业务相位块＋编排块（行 4 的残留扫描面；系统层 `SYSTEM_PROMPT` 不在范围）。
_CONSUMER_DIRS = (
    "understanding",
    "clarification",
    "tool_matching",
    "answering",
    "orchestration",
)

# 规格 接口定义节的六族名单（族名→成员常量名；「集合比较」判据面）。
_SPEC_FAMILIES: dict[str, tuple[str, ...]] = {
    "task_book_skeleton": (
        "TASK_BOOK_SCENE",
        "TASK_BOOK_TASK",
        "TASK_BOOK_EXAMPLES",
        "TASK_BOOK_REDLINE",
        "TASK_BOOK_OUTPUT_CONTRACT",
    ),
    "clarify_emission": ("CLARIFY_EMISSION_CONTRACT",),
    "toolmatch_emission": ("TOOLMATCH_EMISSION_CONTRACT",),
    "summary": ("SUMMARY_CONTRACT",),
    "answer_draft": ("ANSWER_DRAFT_CONTRACT",),
    "answer_requirements": ("ANSWER_REQUIREMENTS",),
}

# 答案要求七条逐字稿（迁移照抄——V1 `orientation.py` `_ANSWER_REQUIREMENTS`；顺序固定）。
_ANSWER_REQUIREMENTS_VERBATIM: tuple[str, ...] = (
    "逐条事实断言带 [n] 引标（n＝观察材料序号）",
    "材料未覆盖的部分不得断言、如实说明未覆盖",
    "材料含多个来源（不同报告／油田／井）时逐个来源分别作答（不冲突也要分别列出，不以反问代替作答）",
    "作答后仍有未覆盖的来源或指代不明处，如实点名未覆盖来源（含检索窗注记的未进窗来源）"
    "并请用户补充检索或指明对象，不静默略过",
    "引擎的降级/未绑定/拦停注记必须如实转述进对应子问题条目（不得静默丢弃）",
    "引用观察材料请摘录必要短语并带引标，禁整段照搬原文充当回答",
    "「理解：／指标候选：」及任何动作 JSON 是过程产物，出现在答案中即废品。",
)

# 动词钉死句逐字（V1 `answer_turn_preamble` 行 2——pin-13 合同侧之一）。
_VERB_PIN = (
    "现在：写最终答案交付用户。本步是写答案步——不再做任何决策、不再发射任何"
    "动作指令（finalize/decompose 等动作出现即废品）。"
)

# 数据区段头（来源标记——`specs/understanding.md` 行为 2 的标来源面）。
_DATA_ZONE_HEAD = "【环境】（以下由系统按当前数据现状动态装配）"
_QUESTION_HEAD = "【待解构的题干】"

# 空投影占位文案逐字（真源 recon/L2a R-L2a-19；规格 行为 5）。
_PLACEHOLDER_FAMILY = "（暂无族标注）"
_PLACEHOLDER_EMPTY = "（空）"
_PLACEHOLDER_RELATION = "关系：（空）"
_PLACEHOLDER_WATERMARK = "（水位未取得）"

# 行 16 扫描词集：本件 fixture 投影的台账词集（逐词取自 fixture dump）＋井号形
# （真源判据＝规格 行为 11「fixture 词集与水位日形交集＝∅」）。
_FIXTURE_WELL_IDS = ("K12-3", "A7")
# 实仓台账真源词哨兵（族①样例常量内含——见行 16 用例的登记张力断言）。
_LATENT_LEDGER_WORDS = ("抽油机时率", "躺井", "Y-41")


def _ledger_dump() -> dict[str, Any]:
    """台账投影 fixture（形＝`appv2/tools/ledger.py` dump schema）。"""
    return {
        "metrics": [
            {
                "slot": "生产时长",
                "name": "生产时长",
                "binding_state": "bound",
                "calibers": [],
                "default_caliber": None,
                "value": "生产时长（单位 h）",
                "source_id": "E-1",
                "version": "1",
            },
            {
                "slot": "含水率",
                "name": "含水率",
                "binding_state": "unbound",
                "calibers": [],
                "default_caliber": None,
                "value": "含水率（单位 %）",
                "source_id": "E-2",
                "version": "1",
            },
        ],
        "terms": [
            {
                "term": "井筒",
                "banned": False,
                "freshness": "现行（时效：当年）",
                "value": "井筒（井身结构）",
                "source_id": "E-3",
            },
        ],
        "objects": [{"obj": "抽油井", "value": "抽油井（人工举升井）", "source_id": "E-4"}],
        "relations": [
            {"rel": "位于", "value": "抽油井——位于——区块", "source_id": "E-5"},
        ],
        "aliases": {"含水率": "含水率"},
        "families_map": {"completion": ["completion"], "monthly": ["monthly"]},
        "cards": ["agg_oil"],
    }


def _ledger_state(**overrides: Any) -> RunState:
    fields: dict[str, Any] = {
        "run_id": "run-prompts-1",
        "question": "K12-3 井近三天生产时长？",
        "understanding": "问某井日产油量。",
        "ledger_dump": _ledger_dump(),
    }
    fields.update(overrides)
    return RunState(**fields)


def _empty_state() -> RunState:
    return RunState(run_id="run-prompts-empty", question="空投影题？")


def _empty_state_with_empty_dump() -> RunState:
    """已取之空投影态（`{}`）——与未取得态（`None`）同落占位文案。"""
    return RunState(run_id="run-prompts-empty2", question="空投影题？", ledger_dump={})


def _answer_state() -> RunState:
    return RunState(
        run_id="run-prompts-2",
        question="K12-3 井近三天生产时长？",
        ledger_dump=_ledger_dump(),
        question_group={"subtasks": [{"id": "s1", "question": "K12-3 井生产时长"}]},
        tool_matches=[
            {"id": "s1", "chain": "data", "tool": "data_query", "plan": {"ranking": True}},
            {"id": "s2", "chain": "data", "tool": "data_query", "plan": {"ranking": False}},
        ],
        subtask_results=[
            {"id": "s1", "question": "K12-3 井生产时长", "status": "ok"},
            {"id": "s2", "question": "K12-3 井含水率", "status": "failed", "reason": "不在台账"},
        ],
        observations=[
            {"n": 1, "kind": "agg_row", "content": "K12-3 井 2026-08-24 生产时长 21.5 h"},
            {"n": 2, "kind": "notice", "content": "观察材料哨兵串甲"},
        ],
    )


def _contract_constants() -> dict[str, str]:
    """六族全量常量（族名→成员名→文本）。"""
    return {
        name: getattr(constants_module, name)
        for members in CONTRACT_CONSTANT_FAMILIES.values()
        for name in members
    }


def _module_str_constants(path: Path) -> dict[str, str]:
    """模块级 `str` 常量（AST 取值——隐式拼接已归并为最终值）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        for target in targets:
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    found[target.id] = node.value.value
    return found


def _literal_strings(tree: ast.Module) -> list[tuple[int, str]]:
    """文件内全部字符串字面量（逐条字面——用于「残留副本」扫描）。"""
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _consumer_sources() -> list[tuple[Path, ast.Module]]:
    sources: list[tuple[Path, ast.Module]] = []
    for name in _CONSUMER_DIRS:
        for path in sorted((_V2_DIR / name).rglob("*.py")):
            sources.append((path, ast.parse(path.read_text(encoding="utf-8"))))
    return sources


def _runtimev2_sources() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_V2_DIR.rglob("*.py"))
    ]


def _hits(sources: list[tuple[Path, ast.Module]], feature: str) -> list[str]:
    """特征子串在字面量级命中的文件清单（探测器——行 4／行 3 共用）。"""
    found: list[str] = []
    for path, tree in sources:
        if any(feature in literal for _, literal in _literal_strings(tree)):
            found.append(path.name)
    return found


def _fixture_words(dump: dict[str, Any]) -> set[str]:
    """台账真源词集＝fixture 投影的指标名／术语／对象／归属关系字面＋井号形（行为 11 判据面）。"""
    words: set[str] = set(_FIXTURE_WELL_IDS)
    for metric in dump["metrics"]:
        words.update({metric["slot"], metric["name"]})
    words.update(term["term"] for term in dump["terms"])
    words.update(obj["obj"] for obj in dump["objects"])
    words.update(relation["value"] for relation in dump["relations"])
    return words


def _format_slots(value: str) -> set[str]:
    """文本中的标识符形格式化槽（JSON 花括号示例不计——形态判定，非语义）。"""
    return {
        field
        for _, field, _, _ in string.Formatter().parse(value)
        if field and re.fullmatch(r"[a-z_][a-z0-9_]*", field)
    }


def _zone(text: str, head: str, tail: str) -> str:
    """取 `head` 至 `tail` 之间的段（段边界定位件）。"""
    return text[text.index(head):text.index(tail)]


# ---------- 1 合同常量族集合与接口清单相等（名单闭世界）＋pin-24 ----------


def test_contract_constant_family_closed_world() -> None:
    """合同常量族集合与接口清单相等（名单闭世界）；常量无逐轮变体（pin-24 本块承诺面）。"""
    assert dict(CONTRACT_CONSTANT_FAMILIES) == _SPEC_FAMILIES  # 族集合与成员名单逐族相等
    for family, members in CONTRACT_CONSTANT_FAMILIES.items():
        assert members, f"族 {family} 零成员"
        for name in members:
            value = getattr(constants_module, name)
            assert isinstance(value, str) and value

    # 闭世界：`constants` 模块级 `str` 常量集合＝六族成员并集（无族外合同常量）
    declared = {name for members in _SPEC_FAMILIES.values() for name in members}
    assert set(_module_str_constants(_CONSTANTS_FILE)) == declared

    # 包根 re-export 与定义处同一对象（四业务相位只经包根引用——R2 的引用面）
    root = import_module("appv2.runtimev2.prompts")
    for name in (
        "ANSWER_DRAFT_CONTRACT",
        "ANSWER_REQUIREMENTS",
        "CLARIFY_EMISSION_CONTRACT",
        "SUMMARY_CONTRACT",
        "TASK_BOOK_EXAMPLES",
        "TASK_BOOK_OUTPUT_CONTRACT",
        "TASK_BOOK_REDLINE",
        "TASK_BOOK_SCENE",
        "TASK_BOOK_TASK",
        "TOOLMATCH_EMISSION_CONTRACT",
    ):
        assert getattr(root, name) is getattr(constants_module, name)

    # 包根 re-export 与定义处同一对象（四业务相位只经包根引用——R2 的引用面）
    root = import_module("appv2.runtimev2.prompts")
    for name in (
        "ANSWER_DRAFT_CONTRACT",
        "ANSWER_REQUIREMENTS",
        "CLARIFY_EMISSION_CONTRACT",
        "SUMMARY_CONTRACT",
        "TASK_BOOK_EXAMPLES",
        "TASK_BOOK_OUTPUT_CONTRACT",
        "TASK_BOOK_REDLINE",
        "TASK_BOOK_SCENE",
        "TASK_BOOK_TASK",
        "TOOLMATCH_EMISSION_CONTRACT",
    ):
        assert getattr(root, name) is getattr(constants_module, name)

    # 装配函数族名单闭世界（卡面两函数在列；-04b／-04c 只填行为、不另立第二套形状）
    assert {"assemble_task_book", "assemble_answer_prompt", "anchor_line"} <= set(
        ASSEMBLY_FUNCTIONS
    )
    for name in ASSEMBLY_FUNCTIONS:
        assert name.isidentifier()

    # pin-24 本块承诺面＝合同常量逐字稳定（常量无逐轮变体）：槽位仅 CLARIFY 两枚声明槽，
    # 且换状态装配后合同段逐字不变。
    # 槽位＝Python 格式化槽（标识符形占位字段）；JSON 花括号示例不计（形态处理豁免面）
    assert CLARIFY_EMISSION_CONTRACT.startswith("【相位①·业务澄清】")  # 相位合同头行
    assert TOOLMATCH_EMISSION_CONTRACT.startswith("【相位②·工具匹配】")
    slots = {
        name: _format_slots(value) for name, value in _contract_constants().items()
    }
    assert {name: fields for name, fields in slots.items() if fields} == {
        "CLARIFY_EMISSION_CONTRACT": {"max_subtasks", "discover_used"}
    }
    first = assemble_task_book(_ledger_state())
    second = assemble_task_book(_ledger_state(question="换个题", understanding="换个题意"))
    for constant in _SPEC_FAMILIES["task_book_skeleton"]:
        assert first.count(getattr(constants_module, constant)) == 1
        assert second.count(getattr(constants_module, constant)) == 1
    assert first.split(_DATA_ZONE_HEAD)[0] == second.split(_DATA_ZONE_HEAD)[0]  # 指令区逐字稳定


# ---------- 2 答案要求清单 7 条逐字在场（pin-03 落点） ----------


def test_answer_requirements_verbatim_seven() -> None:
    """答案要求 7 条逐字在场、顺序固定、以「；」分隔（pin-03：③多来源分源逐字在场）。"""
    items = ANSWER_REQUIREMENTS.split("；")
    assert len(items) == 7
    assert tuple(items) == _ANSWER_REQUIREMENTS_VERBATIM
    assert ANSWER_REQUIREMENTS.count("；") == 6
    assert not ANSWER_REQUIREMENTS.endswith("；")
    # pin-03 落点＝③多来源分源逐字在场（交付行为面待 `specs/answering.md` 回提承接）
    assert "材料含多个来源（不同报告／油田／井）时逐个来源分别作答" in ANSWER_REQUIREMENTS
    assert "不以反问代替作答" in ANSWER_REQUIREMENTS
    # 合同侧经答案轮装配把七条全文送进模型面
    assert f"【答案要求】{ANSWER_REQUIREMENTS}" in assemble_answer_prompt(_answer_state())


# ---------- 3 答案要求清单 runtimev2 面内恰一处定义 ----------


def test_answer_requirements_single_source() -> None:
    """答案要求清单 runtimev2 面内恰一处定义（消费方零字面副本；系统层不在范围）。"""
    feature = "逐条事实断言带 [n] 引标（n＝观察材料序号）"
    assert feature in ANSWER_REQUIREMENTS
    hits = _hits(_runtimev2_sources(), feature)
    assert hits == [_CONSTANTS_FILE.name], f"答案要求清单出现多处以字面定义：{hits}"

    # 族⑤＝去重后形态（流水 43①）：V1 句首答案规则句群不在（由族⑥单点承接）
    assert "材料未覆盖的部分不得断言" not in ANSWER_DRAFT_CONTRACT
    assert "起草答案：逐条事实断言" not in ANSWER_DRAFT_CONTRACT
    # 其余字面零删改：行集交付规矩段／台账卡边界句／A-P6a-35 半句仍在
    half = "（材料未覆盖所问时：只简短说明未找到与所缺，不逐源铺陈无关材料）。"
    assert half in ANSWER_DRAFT_CONTRACT
    assert "行集型子问题（问句要求明细/排名/列举全行集时）" in ANSWER_DRAFT_CONTRACT
    assert "台账卡（指标/术语定义面）只承载口径与定义" in ANSWER_DRAFT_CONTRACT


# ---------- 4 合同常量六族字面副本零残留 ----------


def test_contract_constants_no_duplicate_literals() -> None:
    """六族首句特征子串在四相位块／编排块源码零命中（系统层不在范围）。"""
    sources = _consumer_sources()
    assert sources, "相位块扫描面为空——扫不到源码即失去看守意义"
    for family, members in _SPEC_FAMILIES.items():
        for name in members:
            value = getattr(constants_module, name)
            feature = value.split("\n", 1)[0][:24]
            assert len(feature) >= 12 and feature in value
            assert _hits(sources, feature) == [], f"{family}.{name} 首句副本残留"

    # 探测器非空转：伪造一份相位块源码，六族首句之一在场即被咬
    forged = ast.parse(f'CONTRACT = "{TASK_BOOK_SCENE.split(chr(10), 1)[0][:24]}"')
    assert _hits([(Path("forged.py"), forged)], TASK_BOOK_SCENE.split("\n", 1)[0][:24])


# ---------- 5 任务书段序固定、题干段置末 ----------


def test_task_book_segment_order() -> None:
    """任务书段序＝指令区→数据区→输出契约区→题干段；题干段为末段。"""
    output = assemble_task_book(_ledger_state(), watermark="2026-08-24")
    order = [
        TASK_BOOK_SCENE,
        TASK_BOOK_TASK,
        TASK_BOOK_EXAMPLES,
        TASK_BOOK_REDLINE,  # 指令区内四常量相对序：场景→任务→样例→红线
        _DATA_ZONE_HEAD,
        TASK_BOOK_OUTPUT_CONTRACT,
        _QUESTION_HEAD,
    ]
    positions = [output.index(marker) for marker in order]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)
    assert output.rstrip().endswith("现在输出。）")  # 题干段为末段（紧邻生成点）
    # 段间「\n\n」连接（真源 R-L2a-17 连接形）
    assert f"\n\n{_DATA_ZONE_HEAD}" in output
    assert f"\n\n{TASK_BOOK_OUTPUT_CONTRACT}\n\n" in output
    # 红线归位＝指令区（V2 设计变更：V1 在环境段之后）
    assert output.index(TASK_BOOK_REDLINE) < output.index(_DATA_ZONE_HEAD)


# ---------- 6 任务书样例区＝固定三则 ----------


def test_task_book_examples_fixed_set() -> None:
    """任务书样例区＝固定三则、不随 state 变化、无边界对照例。"""
    for label in ("样例一（多部分题）", "样例二（口语映射题）", "样例三（判断纠错题）"):
        assert label in TASK_BOOK_EXAMPLES
    assert "样例四" not in TASK_BOOK_EXAMPLES
    assert "边界" not in TASK_BOOK_EXAMPLES.split("样例三", 1)[0].split("样例一", 1)[1]
    output_a = assemble_task_book(_ledger_state())
    output_b = assemble_task_book(_empty_state())
    assert _zone(output_a, TASK_BOOK_EXAMPLES, TASK_BOOK_REDLINE) == TASK_BOOK_EXAMPLES + "\n\n"
    assert _zone(output_b, TASK_BOOK_EXAMPLES, TASK_BOOK_REDLINE) == TASK_BOOK_EXAMPLES + "\n\n"


# ---------- 7 数据区活体投影现取 ----------


def test_data_zone_live_projection() -> None:
    """数据区活体投影现取：改投影 → 输出随之变（标来源；understanding 行为 2 面）。"""
    base = assemble_task_book(_ledger_state(), watermark="2026-08-24")
    assert _DATA_ZONE_HEAD in base
    assert "生产时长｜可出数" in base
    assert "含水率｜未绑定（台账无数值——数值走报告检索）" in base
    assert "抽油井（人工举升井）" in base
    assert "  关系：抽油井——位于——区块" in base
    assert "- 资料库族：completion（完井工程报告）、monthly（月报）——" in base
    assert "- 数据水位：2026-08-24——" in base

    dump = _ledger_dump()
    dump["metrics"].append(
        {
            "slot": "井口压力",
            "name": "井口压力",
            "binding_state": "bound",
            "value": "井口压力（单位 MPa）",
        }
    )
    dump["terms"].append({"term": "井筒", "banned": True, "value": "旧称（替代：井筒）"})
    changed = assemble_task_book(_ledger_state(ledger_dump=dump), watermark="2026-08-25")
    assert "井口压力｜可出数" in changed and "井口压力｜可出数" not in base
    assert "禁用词！旧称（替代：井筒）" in changed
    assert "- 数据水位：2026-08-25——" in changed
    assert " - 台账指标名录（3 条——名字｜状态" in changed  # 块头计数随增删同步
    # 投影增删一行 → 输出同步增删（词条删除）
    dump["terms"] = []
    dropped = assemble_task_book(_ledger_state(ledger_dump=dump))
    assert "旧称（替代：井筒）" not in dropped
    assert " - 术语表（0 条——口语／别名 → 正名；纯定义型给一句式定义）：\n  （空）" in dropped


# ---------- 8 空投影 → 占位文案逐字在场 ----------


def test_empty_projection_placeholder_verbatim() -> None:
    """空投影（None 与 {}）→ 族／指标／术语／对象／关系／水位占位文案逐字在场（不删段）。"""
    for state in (_empty_state(), _empty_state_with_empty_dump()):
        output = assemble_task_book(state, watermark="")
        assert _PLACEHOLDER_FAMILY in output
        assert _PLACEHOLDER_WATERMARK in output
        assert _PLACEHOLDER_RELATION in output
        assert output.count("\n  " + _PLACEHOLDER_EMPTY) == 3  # 指标／术语／对象各一
        for header in (" - 台账指标名录（", " - 术语表（", " - 本体速览（", "  对象："):
            assert header in output  # 段不删、只落占位
    assert " - 台账指标名录（0 条" in assemble_task_book(_empty_state_with_empty_dump())


# ---------- 16 合同常量零业务名词 ----------


def test_contract_constants_business_noun_free() -> None:
    """合同常量零业务名词：fixture 词集与水位日形扫描交集＝∅（行为 11）。"""
    date_shape = re.compile(r"\d{4}-\d{2}-\d{2}")
    words = _fixture_words(_ledger_dump())
    assert words, "fixture 词集为空——扫描失去意义"
    for name, value in _contract_constants().items():
        for word in sorted(words):
            assert word not in value, f"{name} 含台账真源词：{word}"
        assert date_shape.search(value) is None, f"{name} 含水务日期段字面"
    assert date_shape.search("水位 2026-08-24") is not None  # 水位日形探测器非空转

    # 探测器非空转（集合成员判定，属行为 15 豁免面——形态处理）
    forged = dict(_contract_constants())
    forged["FORGED"] = "样例：" + sorted(words)[0] + "是多少？"
    caught = [name for name, value in forged.items() if sorted(words)[0] in value]
    assert caught == ["FORGED"]

    # 登记张力（不静默——本件如实标注，主窗裁决）：族①成员 `TASK_BOOK_EXAMPLES` 是 V1
    # Owner 审定三则样例的**逐字迁移**（`specs/prompts.md` 行为 4 断言「三则逐字在场」），
    # 其示例文内含实仓台账真源词（`ontology/petro/glossary-model.yaml` 抽油机时率／躺井、
    # `ontology/petro/m1-object-model.yaml` Y-41）——若按实仓台账词集解释行为 11（其括注
    # 「示例词纪律同款」＝`arch/P4b` A-P4b-60 先例），本族常量即红：行为 4 与行为 11 相抵。
    assert [w for w in _LATENT_LEDGER_WORDS if w in TASK_BOOK_EXAMPLES] == list(
        _LATENT_LEDGER_WORDS
    )


# ---------- 17 答案轮段序固定、材料段零渗入 ----------


def test_answer_round_segment_order_no_material() -> None:
    """答案轮段序＝三件套→汇总合同→子问题清单→起草合同（收尾）；材料段零渗入。"""
    state = _answer_state()
    output = assemble_answer_prompt(state)
    lines = output.split("\n")
    assert lines[0] == f"用户问题：{state.question}"
    assert lines[1] == _VERB_PIN
    assert lines[2] == f"【答案要求】{ANSWER_REQUIREMENTS}"
    markers = [SUMMARY_CONTRACT, "子问题结果清单：", ANSWER_DRAFT_CONTRACT]
    positions = [output.index(marker) for marker in markers]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)
    assert lines[3] == ""
    assert output.endswith(ANSWER_DRAFT_CONTRACT)  # 末段＝起草答案合同（收尾）
    # 子问题清单逐条在场（含拒因原文与排名支配标记——零人话翻译、零词表）
    ranking = "- [s1] K12-3 井生产时长——完成（排名型——结论必须从本子问题排名观察支"
    assert ranking in output
    assert "- [s2] K12-3 井含水率——失败（不在台账）" in output
    # 材料段零渗入：观察行内容不进装配输出（材料渲染归 context）
    for observation in state.observations:
        assert observation["content"] not in output


# ---------- 18 答案轮禁令件在场（pin-13 合同侧） ----------


def test_answer_round_ban_lines_present() -> None:
    """答案轮禁令件在场：动词钉死句＋答案要求⑦两字面（pin-13 合同侧；不注入回声形指令）。"""
    output = assemble_answer_prompt(_answer_state())
    assert _VERB_PIN in output and output.count(_VERB_PIN) == 1
    assert _ANSWER_REQUIREMENTS_VERBATIM[6] in output  # ⑦ 逐字
    assert "finalize/decompose 等动作出现即废品" in output
    # 提示词侧不注入回声形指令：只出禁令件，无「回声」类指令字样
    assert "回声" not in output
    # 空状态亦恒在场（禁令件不随 state 缺位消失）
    assert _VERB_PIN in assemble_answer_prompt(_empty_state())

# =====================================================================================
# -04b：决策轮装配（行 9–15）——fixtures
# =====================================================================================

_DECISION_TODAY = date(2026, 8, 24)
_MAX_SUBTASKS = 4
_GUIDE_TEXT = "指南正文（§A 业务规则细则占位）。"
_DONE_TEXT = "【本 run 已做】- 澄清 r1：分解 1 子问题"
_DECISION_QUESTION = "K12-3 井近三天生产时长？"
_DECISION_UNDERSTANDING = "问 K12-3 井近三天生产时长。"


def _decision_dump() -> dict[str, Any]:
    """决策轮 fixture 投影＝-04a fixture＋`families` 行（常驻块台账行五族齐）。"""
    dump = _ledger_dump()
    dump["families"] = [
        {"name": "completion", "value": "completion（完井工程报告）", "source_id": "E-6"}
    ]
    return dump


def _decision_state(**overrides: Any) -> RunState:
    fields: dict[str, Any] = {
        "run_id": "run-prompts-decision",
        "question": _DECISION_QUESTION,
        "understanding": _DECISION_UNDERSTANDING,
        "ledger_dump": _decision_dump(),
        "question_group": {
            "subtasks": [
                {
                    "id": "s1",
                    "question": "K12-3 井生产时长",
                    "ledger_notes": "生产时长｜可出数｜2026-08-01~2026-08-24",
                    "chain": "data",
                    "tool": "data_query",
                }
            ]
        },
    }
    fields.update(overrides)
    return RunState(**fields)


def _clarify_package(state: RunState, **overrides: Any) -> str:
    kwargs: dict[str, Any] = {
        "guide_text": _GUIDE_TEXT,
        "today": _DECISION_TODAY,
        "max_subtasks": _MAX_SUBTASKS,
    }
    kwargs.update(overrides)
    return assemble_decision_package(state, phase=PHASE_CLARIFY, **kwargs)


def _toolmatch_package(state: RunState, **overrides: Any) -> str:
    kwargs: dict[str, Any] = {"guide_text": _GUIDE_TEXT}
    kwargs.update(overrides)
    return assemble_decision_package(state, phase=PHASE_TOOLMATCH, **kwargs)


def _unique_line(output: str, prefix: str) -> str:
    """单点定位件（段行恰一处——段名/消歧头查询用）。"""
    found = [line for line in output.split("\n") if line.startswith(prefix)]
    assert len(found) == 1, f"段行非恰一处（{prefix}）：{found}"
    return found[0]


# ---------- 9 题意锚行两形且置决策轮指令首行 ----------


def test_anchor_line_two_forms_first_line() -> None:
    """行 9 题意锚行两形（理解真值/假值）且置于决策轮指令首行（行为 6；A-P4b-59）。"""
    state = _decision_state()
    truth = f"用户原题：{state.question}｜题意：{state.understanding}"
    assert anchor_line(state.question, state.understanding) == truth
    assert anchor_line(
        state.question, state.understanding
    ) == f"用户原题：{state.question}｜题意：{state.understanding}"
    for output in (_clarify_package(state), _toolmatch_package(state)):
        assert output.split("\n", 1)[0] == truth  # 锚行在指令最前（首行位）

    # 理解假值形：单段「用户原题：{question}」——不输出空「题意：」段
    blank = _decision_state(understanding="")
    empty_form = f"用户原题：{blank.question}"
    assert anchor_line(blank.question, "") == empty_form
    assert anchor_line(blank.question) == empty_form
    outputs = {
        PHASE_CLARIFY: _clarify_package(blank),
        PHASE_TOOLMATCH: _toolmatch_package(blank),
    }
    assert set(outputs) == set(DECISION_PHASES)
    for output in outputs.values():
        first_line = output.split("\n", 1)[0]
        assert first_line == empty_form
        assert "｜题意：" not in first_line


# ---------- 10 决策轮首入包构成逐件在场 ＋ 四要素 ----------


def test_decision_package_four_elements() -> None:
    """行 10 首入包构成逐件在场（澄清／匹配轮各按其件）、常驻块包裹对恰一对；四要素按轮合看
    逐轮在场（行为 7；A-P4b-56／60）。
    """
    state = _decision_state(discover_used=2)
    clarify = _clarify_package(state)
    toolmatch = _toolmatch_package(state)

    # ①题意锚行（首行）＋②相位合同（头行＋正文；澄清轮另含 finalize 交付面边界句）
    assert clarify.split("\n", 1)[0] == anchor_line(state.question, state.understanding)
    assert CLARIFY_PHASE_HEAD in clarify
    assert "【相位①·业务澄清】只输出一个 JSON 对象（可围栏）。四动作：" in clarify
    assert "子问题 ≤4 个" in clarify  # 声明槽 {max_subtasks}＝调用方注入值
    assert "已用 2 次）：" in clarify  # 声明槽 {discover_used}＝state 投影现取
    assert CLARIFY_FINALIZE_BOUNDARY in clarify
    # ③产出样例（澄清轮）＋④§A 指南段（文本经入参注入）
    assert "填写样例（分解形——五键齐全" in clarify
    assert '"chain": "knowledge"' in clarify
    assert f"{GUIDE_REFERENCE_HEAD}\n{_GUIDE_TEXT}" in clarify
    # ⑥常驻块包裹对恰一对（投影非空）＋包尾
    assert clarify.count(RESIDENT_BLOCK_BEGIN) == 1
    assert clarify.count(RESIDENT_BLOCK_END) == 1
    assert clarify.endswith(RESIDENT_BLOCK_END)
    # 首入包逐件序：锚行→合同头→合同正文→样例→指南段→边界句→常驻块
    order = [
        anchor_line(state.question, state.understanding),
        CLARIFY_PHASE_HEAD,
        "【相位①·业务澄清】只输出",
        "填写样例（分解形",
        GUIDE_REFERENCE_HEAD,
        CLARIFY_FINALIZE_BOUNDARY,
        RESIDENT_BLOCK_BEGIN,
    ]
    positions = [clarify.index(marker) for marker in order]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)

    # 匹配轮各按其件：合同头＋正文；产出样例＝合同内嵌样例；⑤问题组 JSON（顶层 subtasks 单键形）
    assert toolmatch.split("\n", 1)[0] == anchor_line(state.question, state.understanding)
    assert TOOLMATCH_PHASE_HEAD in toolmatch
    assert TOOLMATCH_EMISSION_CONTRACT in toolmatch
    assert "填写样例（单匹配 knowledge 形）" in toolmatch
    assert '\n\n问题组：\n{"subtasks": [{"id": "s1"' in toolmatch
    assert toolmatch.count(RESIDENT_BLOCK_BEGIN) == 1
    assert toolmatch.count(RESIDENT_BLOCK_END) == 1
    assert toolmatch.endswith(RESIDENT_BLOCK_END)
    # 各按其件（不互串）：澄清轮无问题组段、匹配轮无分解样例段
    assert "问题组：" not in clarify
    assert "填写样例（分解形" not in toolmatch

    # 四要素按轮合看逐轮在场：任务动词（合同头）／题意锚（锚行）／产出样例／失败反馈（增量条回喂）
    rejected = _decision_state(discover_used=2, decision_error="缺 subtasks 键")
    for phase, package, sample, head in (
        (PHASE_CLARIFY, _clarify_package(rejected), "填写样例（分解形", CLARIFY_PHASE_HEAD),
        (
            PHASE_TOOLMATCH,
            _toolmatch_package(rejected),
            "填写样例（单匹配 knowledge 形）",
            TOOLMATCH_PHASE_HEAD,
        ),
    ):
        assert phase in DECISION_PHASES
        assert package.split("\n", 1)[0] == anchor_line(
            rejected.question, rejected.understanding
        )
        assert head in package
        assert sample in package
        assert "上次发射被拒：缺 subtasks 键——修正后重新输出 JSON。" in (
            assemble_decision_increment(rejected, phase=phase)
        )

    # 装配函数族成员经包根可达（本票成员全在名单闭世界——R2 公开面）
    for name in (
        "anchor_line",
        "assemble_decision_package",
        "assemble_decision_increment",
        "render_ledger_resident_block",
        "render_decompose_example",
    ):
        assert name in ASSEMBLY_FUNCTIONS

    # 形态越界＝参数错误（不吞错、不返回哨兵——先例 `specs/context.md` 错误契约：
    # 相位越界／族②声明槽缺值均属调用方违约，非业务错，故不落占位文案也不静默）
    with pytest.raises(ValueError):
        assemble_decision_package(state, phase="no-such-phase", guide_text=_GUIDE_TEXT)
    with pytest.raises(ValueError):
        assemble_decision_package(
            state, phase=PHASE_CLARIFY, guide_text=_GUIDE_TEXT, today=_DECISION_TODAY
        )


# ---------- 11 决策轮增量条构成与逐字稿 ----------


def test_decision_increment_lines_present() -> None:
    """行 11 决策轮增量条构成与逐字稿（澄清轮五件／匹配轮两件）；改道后缀＝机器拒因闭世界
    子串校（行为 16；R-E1-08／R-E1-19／R-E2-05）。
    """
    state = _decision_state(
        contracts_appended=[PHASE_CLARIFY],
        discover_used=3,
        user_hint="窗按上月",
        decision_error="缺 subtasks 键",
        subtask_results=[
            {"id": "s1", "question": "K12-3 井生产时长", "status": "ok"},
            {
                "id": "s2",
                "question": "含水率",
                "status": "failed",
                "reason": "未绑定（台账无数值）",
            },
            {"id": "s3", "question": "井筒口径", "status": "failed", "reason": "不在台账"},
            {"id": "s4", "question": "生产时长", "status": "failed", "reason": "参数缺失"},
        ],
    )
    # 单条 user 内各段以「\n」连接、段序固定（①探查预算②回炉③用户补充④拒因回喂⑤已做段）
    assert assemble_decision_increment(
        state, phase=PHASE_CLARIFY, done_text=_DONE_TEXT
    ).split("\n") == [
        f"探查预算：全 run ≤{MAX_DISCOVERS_PER_RUN} 次，已用 3 次。",  # 上限＝state 限额单点
        "回炉：只分解以下失败/缺失子问题（成功子问题结果已保留，禁止重复分解执行）：",
        "- [s2] 含水率——拒因：未绑定（台账无数值）→改走 knowledge 链（tool=doc_retrieve）",
        "- [s3] 井筒口径——拒因：不在台账→改走 knowledge 链（tool=doc_retrieve）",
        "- [s4] 生产时长——拒因：参数缺失",  # 拒因词面未命中 → 零追加（闭世界子串校）
        "用户已补充：窗按上月——请把它落进本轮分解。",
        "上次发射被拒：缺 subtasks 键——修正后重新输出 JSON。",
        _DONE_TEXT,  # 已做段＝调用方传入文本原样在场、零改写
    ]

    # ①仅非首入轮：相位标记未落（首入轮）→ 无预算条；零条 → 空串（整条追加＝调用方义务）
    assert assemble_decision_increment(_decision_state(), phase=PHASE_CLARIFY) == ""
    assert assemble_decision_increment(
        _decision_state(contracts_appended=[PHASE_CLARIFY], discover_used=3),
        phase=PHASE_CLARIFY,
    ) == f"探查预算：全 run ≤{MAX_DISCOVERS_PER_RUN} 次，已用 3 次。"

    # 匹配轮仅两件：拒因回喂＋已做段（无预算／回炉／用户补充条）
    assert assemble_decision_increment(
        state, phase=PHASE_TOOLMATCH, done_text=_DONE_TEXT
    ).split("\n") == [
        "上次发射被拒：缺 subtasks 键——修正后重新输出 JSON。",
        _DONE_TEXT,
    ]
    assert assemble_decision_increment(_decision_state(), phase=PHASE_TOOLMATCH) == ""


# ---------- 12 台账常驻块逐字转抄恰一份；三删段名缺席 ----------


def test_ledger_resident_block_verbatim_once() -> None:
    """行 12 台账常驻块逐字转抄、恰一份；三删段名字面缺席（行为 8；V2-59 三删纪律装配面）。"""
    state = _decision_state()
    dump = state.ledger_dump
    assert isinstance(dump, dict)
    block = render_ledger_resident_block(state)
    head, *body = block.split("\n")
    assert head == RESIDENT_BLOCK_BEGIN
    assert body[0] == LEDGER_DICT_NOTE  # 字典说明行紧随 BEGIN（逐字、单行位）
    assert block.endswith("\n" + RESIDENT_BLOCK_END)
    for label in ("台账全量（指标/术语/对象/关系/族标注）", "别名表", "数据资产结构卡"):
        assert f"【{label}】" in block
    rows = (
        [f"指标｜{m['value']}（绑定态：{m['binding_state']}）" for m in dump["metrics"]]
        + [f"术语｜{t['value']}（时效：{t['freshness']}）" for t in dump["terms"]]
        + [f"对象｜{o['value']}" for o in dump["objects"]]
        + [f"关系｜{r['value']}" for r in dump["relations"]]
        + [f"族标注｜{f['value']}" for f in dump["families"]]
    )
    assert rows and all(row in block for row in rows)  # 逐字转抄（值串直取、零改写零摘要）
    assert "含水率→含水率" in block  # 别名表块
    assert "- agg_oil" in block  # 结构卡块

    output = _clarify_package(state)
    assert output.count(RESIDENT_BLOCK_BEGIN) == 1  # 恰一份（包裹对恰一对）
    assert output.count(RESIDENT_BLOCK_END) == 1
    for row in rows:
        assert output.count(row) == 1, f"台账行非恰一次：{row}"
    for entry in (
        "生产时长（单位 h）",
        "含水率（单位 %）",
        "井筒（井身结构）",
        "抽油井——位于——区块",
        "completion（完井工程报告）",
    ):
        assert output.count(entry) == 1

    # 三删段名字面缺席（段名形／旧句逐字——见模块头「判据面说明」）
    for name in ("◆ **发射判据**", "◆ **指标名册**", "收口硬规则"):
        assert name not in output

    # 空投影（未取得 None 与已取之空态 {}）→ 空串段（不包裹、不另拼名录段）
    for empty in (_empty_state(), _empty_state_with_empty_dump()):
        assert render_ledger_resident_block(empty) == ""
        package = _clarify_package(empty)
        assert RESIDENT_BLOCK_BEGIN not in package
        assert RESIDENT_BLOCK_END not in package


# ---------- 13 消歧头统一措辞 ----------


def test_disambiguation_header_uniform() -> None:
    """行 13 消歧头统一措辞逐字在场、两轮同一字面（行为 9；A-P4b-33）。"""
    state = _decision_state()
    outputs = {
        PHASE_CLARIFY: _clarify_package(state),
        PHASE_TOOLMATCH: _toolmatch_package(state),
    }
    assert set(outputs) == set(DECISION_PHASES)
    heads = {phase: _unique_line(output, "【业务规则参考") for phase, output in outputs.items()}
    assert len(set(heads.values())) == 1  # 两轮统一（同一字面——单点常量）
    head = next(iter(heads.values()))
    assert head == GUIDE_REFERENCE_HEAD
    assert "窗词锚定/单井红线/三链路由；动作类措辞以上方合同为准" in head
    for name in ("发射判据", "指标名册", "收口硬规则"):  # 不点名已删段
        assert name not in head
    for output in outputs.values():
        assert f"{GUIDE_REFERENCE_HEAD}\n{_GUIDE_TEXT}" in output  # §A 正文紧随（入参注入）
        # 三删段名形缺席（见模块头「判据面说明」）
        assert "◆ **发射判据**" not in output
        assert "◆ **指标名册**" not in output
        assert "收口硬规则" not in output


# ---------- 14 分解样例三分支 ----------


def test_decompose_example_three_branches() -> None:
    """行 14 分解样例三分支（未绑定→knowledge／可出数→data／空→空串）（行为 10；A-P4b-32）。"""
    bound = {"slot": "生产时长", "binding_state": "bound", "value": "生产时长（单位 h）"}
    unbound = {"slot": "含水率", "binding_state": "unbound", "value": "含水率（单位 %）"}

    knowledge = render_decompose_example([bound, unbound], today=_DECISION_TODAY)
    assert "含水率是多少？" in knowledge  # 首条未绑定优先（演示 knowledge 链路由）
    assert "含水率｜未绑定｜2026-07-25~2026-08-24" in knowledge  # 窗＝today−30 天~today
    assert '"chain": "knowledge", "tool": "doc_retrieve"' in knowledge
    assert "生产时长" not in knowledge  # 仅取一条

    data = render_decompose_example([bound], today=_DECISION_TODAY)  # 无未绑定 → 首条可出数
    assert "生产时长是多少？" in data
    assert "生产时长｜在册可出数｜2026-07-25~2026-08-24" in data
    assert '"chain": "data", "tool": "data_query"' in data

    for empty_metrics in ([], None, {"slot": "x"}):  # 空投影／非列 → 空串（调用方跳过）
        assert render_decompose_example(empty_metrics, today=_DECISION_TODAY) == ""
    assert render_decompose_example([unbound], today="2026-08-24") == knowledge  # ISO 串入参同形

    # 装配面三分支：未绑定 → knowledge 样例在场；全可出数 → data 分支；空投影 → 段缺位（空串段）
    assert '"chain": "knowledge"' in _clarify_package(_decision_state())
    all_bound = _decision_dump()
    all_bound["metrics"] = [m for m in all_bound["metrics"] if m["binding_state"] == "bound"]
    assert '"chain": "data"' in _clarify_package(_decision_state(ledger_dump=all_bound))
    assert "填写样例（分解形" not in _clarify_package(_empty_state())


# ---------- 15 分解样例产出为合法 JSON 且键形正确 ----------


def test_decompose_example_valid_json() -> None:
    """行 15 分解样例产出为合法 JSON 且键形正确（行为 10；D-L2a-13 病灶不复现）。"""
    bound = {"slot": "生产时长", "binding_state": "bound", "value": "x"}
    example = render_decompose_example([bound], today=_DECISION_TODAY)
    assert example.endswith("}]}}")
    payload = example[example.index("{") :]
    obj = json.loads(payload)  # 合法 JSON（V1 字符串拼接无转义病灶不复现）
    assert set(obj) == {"action", "question_group"}  # 顶层恰两键
    assert obj["action"] == "decompose"
    assert set(obj["question_group"]) == {"subtasks"}  # 顶层 subtasks 单键形
    subtasks = obj["question_group"]["subtasks"]
    assert isinstance(subtasks, list) and len(subtasks) == 1  # subtasks 单条
    assert set(subtasks[0]) == {"id", "question", "ledger_notes", "chain", "tool"}  # 五键齐全
    assert subtasks[0]["id"] == "s1"
    assert subtasks[0]["ledger_notes"] == "生产时长｜在册可出数｜2026-07-25~2026-08-24"

    # 转义面：指标名含裸引号／反斜杠时，json.dumps 转义后仍合法（裸拼即非法）
    hostile = {"slot": '时率"高"\\', "binding_state": "bound", "value": "x"}
    hostile_example = render_decompose_example([hostile], today=_DECISION_TODAY)
    hostile_obj = json.loads(hostile_example[hostile_example.index("{") :])
    assert hostile_obj["question_group"]["subtasks"][0]["question"] == '时率"高"\\是多少？'

    # 澄清轮首入包内现造的同一条样例亦为合法 JSON（装配面无第二拼接路径）
    state = _decision_state()
    line = _unique_line(_clarify_package(state), "填写样例（分解形")
    assert isinstance(state.ledger_dump, dict)
    assert line == render_decompose_example(state.ledger_dump["metrics"], today=_DECISION_TODAY)
    json.loads(line[line.index("{") :])


# ══════════════════════════════════════════════════════════════════════════════════════
# -04c：元面（行 19–21）＋【边界集】（行 22）／【保留集】（行 23）
# ══════════════════════════════════════════════════════════════════════════════════════

# 本块依赖面白名单（行 19／20 共用）：appv2 面只许 `state`＋自身；stdlib 面只许纯计算件
# （R3「只许 import state」的半覆盖面降维补位——公共层其余块与七业务相位均在此名单外）。
_ALLOWED_APPV2_IMPORTS = ("appv2.runtimev2.state", "appv2.runtimev2.prompts")
_ALLOWED_STDLIB_ROOTS = ("__future__", "collections", "datetime", "json", "typing")
# 行 19 禁引模块（IO／落盘／网络族＋时钟族＋随机族＋模型与框架族）
_FORBIDDEN_PURE_MODULES = (
    "aiohttp",
    "anthropic",
    "httpx",
    "io",
    "langchain",
    "langgraph",
    "litellm",
    "openai",
    "os",
    "pathlib",
    "random",
    "requests",
    "secrets",
    "shutil",
    "socket",
    "subprocess",
    "tempfile",
    "time",
    "urllib",
)
# 行 19 禁止调用：零 IO（文件／进程／动态执行）／零模型；时钟与随机面按**属性形**判
# （裸 `today()`＝调用方注入的时间量，合法——真源 `render_decompose_example` 的入参面）。
_FORBIDDEN_BARE_CALLS = ("__import__", "compile", "eval", "exec", "input", "open", "print")
_FORBIDDEN_ATTR_CALLS = (
    "choice",
    "monotonic",
    "now",
    "perf_counter",
    "randint",
    "shuffle",
    "sleep",
    "time",
    "today",
    "urandom",
    "utcnow",
)
_MODEL_CALL_NAMES = ("acomplete", "chat", "complete", "embed", "embedding", "embeddings")

# 行 21 判据面：正则族＋词表名面＋非标识符形字符串集合（语义词表的机检代理，先例 state 件）
_REGEX_MODULES = ("re", "regex")
_REGEX_CALL_NAMES = (
    "compile",
    "findall",
    "finditer",
    "fullmatch",
    "match",
    "search",
    "split",
    "sub",
)
_LEXICON_NAME_MARKS = ("keyword_table", "lexicon", "wordlist", "词表")
_IDENTIFIER_SHAPE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# 豁免面（行为 15 原文「集合成员判定与逐字子串校」＝形态处理，不算语义词表／正则）：
# 块内唯一豁免容器＝机器拒因原文的闭世界子串校（机器拒因面零改动，`arch/P6b` A-P6b-05）。
_VERBATIM_CHECK_EXEMPT = ("_REROUTE_TRIGGERS",)
# 超长清单边界（行 22 ④——超 `max_subtasks` 声明槽：装配不做上限判定、零截断）
_HUGE_SUBTASK_COUNT = 12


def _prompts_sources() -> list[tuple[Path, ast.Module]]:
    """本块源码树（元面三行共用的扫描面）。"""
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_PROMPTS_DIR.rglob("*.py"))
    ]


def _imported_modules(tree: ast.Module) -> list[tuple[int, str]]:
    """文件内 import 位点（`(行, 模块名)`；相对引以点号前缀记名）。"""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append((node.lineno, "." * node.level + (node.module or "")))
    return found


def _call_sites(tree: ast.Module) -> list[tuple[int, str, str]]:
    """调用位点（`(行, 形, 被调名)`；形 ∈ `bare`／`attr`）。"""
    found: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            found.append((node.lineno, "bare", func.id))
        elif isinstance(func, ast.Attribute):
            found.append((node.lineno, "attr", func.attr))
    return found


def _purity_findings(sources: list[tuple[Path, ast.Module]]) -> list[str]:
    """行 19 AST 判据面：IO／网络／时钟／随机／模型位点＋跨块引（零 IO／模型／时钟／随机）。"""
    findings: list[str] = []
    for name, tree in sources:
        for lineno, module in _imported_modules(tree):
            root = module.split(".")[0]
            if root in _FORBIDDEN_PURE_MODULES:
                findings.append(f"{name}:{lineno} 禁引模块 {module}")
            elif root == "appv2" and not module.startswith(_ALLOWED_APPV2_IMPORTS):
                findings.append(f"{name}:{lineno} 越界引块 {module}")
        for lineno, kind, callee in _call_sites(tree):
            if kind == "bare" and callee in _FORBIDDEN_BARE_CALLS:
                findings.append(f"{name}:{lineno} 禁止调用 {callee}")
            if kind == "attr" and callee in _FORBIDDEN_ATTR_CALLS:
                findings.append(f"{name}:{lineno} 时钟／随机面调用 .{callee}")
            if callee in _MODEL_CALL_NAMES:
                findings.append(f"{name}:{lineno} 模型调用 {callee}")
    return findings


def _import_findings(sources: list[tuple[Path, ast.Module]]) -> list[str]:
    """行 20 AST 判据面：appv2 面白名单（只许 `state`＋自身）＋依赖面（只许 stdlib 纯计算件）。"""
    findings: list[str] = []
    for name, tree in sources:
        for lineno, module in _imported_modules(tree):
            root = module.split(".")[0] if module else ""
            if not root:
                continue
            if root == "appv2":
                if not module.startswith(_ALLOWED_APPV2_IMPORTS):
                    findings.append(f"{name}:{lineno} 越界引块 {module}")
            elif root not in _ALLOWED_STDLIB_ROOTS:
                external = root not in sys.stdlib_module_names
                shape = "非 stdlib 依赖" if external else "白名单外 stdlib"
                findings.append(f"{name}:{lineno} {shape} {module}")
    return findings


def _str_collection_sites(tree: ast.Module) -> list[tuple[int, str, tuple[str, ...]]]:
    """模块级字符串集合常量（`Tuple`／`List`／`Set` 形与 `set|frozenset({...})` 调用，映射取键集）。

    元素非标识符形即「自建词表」的机检代理（枚举闭世界取值与 `__all__` 名单都是标识符形）。
    """
    sites: list[tuple[int, str, tuple[str, ...]]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        target = targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        values: tuple[str, ...] = ()
        if isinstance(value, (ast.Tuple, ast.List, ast.Set)):
            values = tuple(
                element.value
                for element in value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
        elif (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in ("set", "frozenset")
            and value.args
            and isinstance(value.args[0], (ast.Tuple, ast.List, ast.Set))
        ):
            values = tuple(
                element.value
                for element in value.args[0].elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
        elif isinstance(value, ast.Dict) and all(
            isinstance(key, ast.Constant) and isinstance(key.value, str) for key in value.keys
        ):
            values = tuple(key.value for key in value.keys)
        if values:
            sites.append((node.lineno, target.id, values))
    return sites


def _in_test_subtrees(tree: ast.Module) -> list[ast.AST]:
    """含 `in`／`not in` 判定的比较与推导式子树——豁免面「逐字子串校」的语法位。"""
    subtrees: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and any(
            isinstance(op, (ast.In, ast.NotIn)) for op in node.ops
        ):
            subtrees.append(node)
        elif isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)) and any(
            isinstance(sub, ast.Compare)
            and any(isinstance(op, (ast.In, ast.NotIn)) for op in sub.ops)
            for sub in ast.walk(node)
        ):
            subtrees.append(node)
    return subtrees


def _exempt_use_findings(tree: ast.Module) -> list[str]:
    """豁免容器使用面：每次取值必须落在「逐字子串校」的语法位（否则豁免成了漏网）。"""
    covered = {id(sub) for node in _in_test_subtrees(tree) for sub in ast.walk(node)}
    return [
        f"L{node.lineno} 豁免容器 {node.id} 用于逐字子串校之外"
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id in _VERBATIM_CHECK_EXEMPT
        and id(node) not in covered
    ]


def _branch_cjk_literals(tree: ast.Module) -> list[tuple[int, str]]:
    """分支判据里的中文明文（按业务词面分派＝语义判断的机检代理，先例 gateway_adapter 件）。"""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        test: ast.expr | None = None
        if isinstance(node, (ast.If, ast.While)):
            test = node.test
        elif isinstance(node, ast.IfExp):
            test = node.test
        elif isinstance(node, ast.Assert):
            test = node.test
        if test is None:
            continue
        found.extend(
            (node.lineno, sub.value)
            for sub in ast.walk(test)
            if isinstance(sub, ast.Constant)
            and isinstance(sub.value, str)
            and any("\u4e00" <= char <= "\u9fff" for char in sub.value)
        )
    return found


def _lexicon_findings(sources: list[tuple[Path, ast.Module]]) -> list[str]:
    """行 21 AST 判据面：正则语义判定＋自建词表＋词表名面＋分支判据中文明文。

    豁免面（规格原文「集合成员判定与逐字子串校」）＝形态处理：注册表 `_VERBATIM_CHECK_EXEMPT`
    所列容器的项与用法不判；其余非标识符形字符串集合／映射键判「疑似语义词表」。
    """
    exempt_items = {
        value
        for _name, tree in sources
        for _lineno, target, values in _str_collection_sites(tree)
        if target in _VERBATIM_CHECK_EXEMPT
        for value in values
    }
    findings: list[str] = []
    for name, tree in sources:
        for lineno, module in _imported_modules(tree):
            if module.split(".")[0] in _REGEX_MODULES:
                findings.append(f"{name}:{lineno} 禁引模块 {module}")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _REGEX_CALL_NAMES
            ):
                root = node.func.value
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name) and root.id in _REGEX_MODULES:
                    findings.append(f"{name}:{node.lineno} 正则语义判定 {root.id}.{node.func.attr}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if any(mark in node.name.lower() for mark in _LEXICON_NAME_MARKS):
                    findings.append(f"{name}:{node.lineno} 词表名面 {node.name}")
            elif isinstance(node, ast.Name):
                if any(mark in node.id.lower() for mark in _LEXICON_NAME_MARKS):
                    findings.append(f"{name}:{node.lineno} 词表名面 {node.id}")
        for lineno, target, values in _str_collection_sites(tree):
            if target in _VERBATIM_CHECK_EXEMPT:
                continue
            for value in values:
                if not _IDENTIFIER_SHAPE.fullmatch(value):
                    findings.append(f"{name}:{lineno} 疑似语义词表项 {value!r}")
        findings.extend(f"{name} {finding}" for finding in _exempt_use_findings(tree))
        for lineno, literal in _branch_cjk_literals(tree):
            if literal not in exempt_items:
                findings.append(f"{name}:{lineno} 分支判据疑似语义明文 {literal!r}")
    return findings


def _deep_import_findings(sources: list[tuple[Path, ast.Module]]) -> list[str]:
    """消费方向（R2）：四相位＋编排块只许经包根 `appv2.runtimev2.prompts` 消费（深模块私有）。"""
    return [
        f"{path.name}:{lineno} 引深层子模块 {module}"
        for path, tree in sources
        for lineno, module in _imported_modules(tree)
        if module.startswith("appv2.runtimev2.prompts.")
    ]


# ---------- 19 装配确定性纯函数：两跑逐字相等／不改入参／零 IO·模型·时钟·随机（元） ----------


def test_assembly_pure_deterministic() -> None:
    """行 19 装配确定性纯函数：两跑逐字相等、不改入参、零 IO／模型／时钟（AST）（行为 14）。"""
    task_book_state = _ledger_state()
    decision_state = _decision_state(
        contracts_appended=[PHASE_CLARIFY],
        discover_used=2,
        user_hint="窗按上月",
        decision_error="缺 subtasks 键",
        subtask_results=[
            {"id": "s1", "question": "K12-3 井生产时长", "status": "ok"},
            {"id": "s2", "question": "含水率", "status": "failed", "reason": "不在台账"},
        ],
    )
    answer_state = _answer_state()
    states = (task_book_state, decision_state, answer_state, _empty_state())

    calls: list[tuple[str, Callable[[], str]]] = [
        ("assemble_task_book", lambda: assemble_task_book(task_book_state, watermark="2026-08-24")),
        ("assemble_answer_prompt", lambda: assemble_answer_prompt(answer_state)),
        ("assemble_decision_package·clarify", lambda: _clarify_package(decision_state)),
        ("assemble_decision_package·toolmatch", lambda: _toolmatch_package(decision_state)),
        (
            "assemble_decision_increment",
            lambda: assemble_decision_increment(
                decision_state, phase=PHASE_CLARIFY, done_text=_DONE_TEXT
            ),
        ),
        ("render_ledger_resident_block", lambda: render_ledger_resident_block(decision_state)),
        (
            "render_decompose_example",
            lambda: render_decompose_example(_decision_dump()["metrics"], today=_DECISION_TODAY),
        ),
        ("anchor_line", lambda: anchor_line(decision_state.question, decision_state.understanding)),
    ]
    before = [asdict(state) for state in states]
    for label, call in calls:
        first, second = call(), call()
        assert isinstance(first, str), f"{label} 输出非 str"
        assert first == second, f"{label} 两跑不逐字相等"
    assert [asdict(state) for state in states] == before, "装配改动了入参（零写入被破）"
    assert [deepcopy(state) for state in states] == list(states), "装配含随机／副作用"
    # 同输入异实例同结果（结果只由入参与合同常量决定——装配确定性）
    assert assemble_answer_prompt(_answer_state()) == assemble_answer_prompt(_answer_state())
    assert assemble_task_book(_ledger_state(), watermark="2026-08-24") == assemble_task_book(
        _ledger_state(), watermark="2026-08-24"
    )

    sources = _prompts_sources()
    assert sources, "扫描面为空——看守失效"
    assert _purity_findings(sources) == [], "本块出现 IO／模型／时钟／随机／跨块位点"

    # 探测器非空转（IO／网络／时钟／随机／模型／跨块六面各命中）
    probes: dict[str, str] = {
        "IO": "import os\nopen('痕迹')\n",
        "网络": "import requests\n",
        "时钟": "from datetime import datetime\nnow = datetime.now()\n",
        "随机": "import random\npick = random.choice([1])\n",
        "模型": "async def go(egress):\n    await egress.complete([])\n",
        "跨块": "from appv2.runtimev2.gateway_adapter import complete\n",
    }
    for label, source in probes.items():
        assert _purity_findings([(Path("forged.py"), ast.parse(source))]), f"{label} 面探测器空转"


# ---------- 20 import 面只许 state（元 AST——R3 半覆盖面的降维补位） ----------


def test_imports_state_only() -> None:
    """行 20 import 面只许 state（AST 扫描——R3 半覆盖面的降维补位；风险 5）。"""
    sources = _prompts_sources()
    assert sources, "扫描面为空——看守失效"
    assert _import_findings(sources) == [], "本块 import 面越出「只许 state＋自身」"

    appv2_modules = {
        module
        for _name, tree in sources
        for _lineno, module in _imported_modules(tree)
        if module.startswith("appv2")
    }
    assert appv2_modules == {
        "appv2.runtimev2.state",
        "appv2.runtimev2.prompts.answer_round",
        "appv2.runtimev2.prompts.constants",
        "appv2.runtimev2.prompts.decision_round",
        "appv2.runtimev2.prompts.task_book",
    }
    stdlib_roots = {
        module.split(".")[0]
        for _name, tree in sources
        for _lineno, module in _imported_modules(tree)
        if module and not module.startswith("appv2")
    }
    assert stdlib_roots and stdlib_roots <= set(_ALLOWED_STDLIB_ROOTS)

    # 探测器非空转：公共层其余块（R3 半面无闸的那半面）与七业务相位、外加依赖三形逐一被咬
    for block in (
        "bookkeeping",
        "context",
        "transport",
        "persistence",
        "gateway_adapter",
        "orchestration",
        "gate",
        "understanding",
        "clarification",
        "tool_matching",
        "answering",
    ):
        forged = [(Path("forged.py"), ast.parse(f"from appv2.runtimev2.{block} import x\n"))]
        assert any("越界引块" in finding for finding in _import_findings(forged)), f"{block} 未被咬"
    assert "非 stdlib 依赖" in "".join(
        _import_findings([(Path("forged.py"), ast.parse("import requests\n"))])
    )
    assert "白名单外 stdlib" in "".join(
        _import_findings([(Path("forged.py"), ast.parse("import functools\n"))])
    )
    assert _import_findings(
        [(Path("forged.py"), ast.parse("from appv2.infra.llm_client import embeddings\n"))]
    )


# ---------- 21 程序侧无词表／正则语义判断（元 AST；豁免面＝集合成员判定与逐字子串校） ----------


def test_no_lexicon_or_regex_in_prompts() -> None:
    """行 21 程序侧无词表／正则语义判断（AST；豁免面＝集合成员判定与逐字子串校——行为 15）。"""
    sources = _prompts_sources()
    assert sources, "扫描面为空——看守失效"
    assert _lexicon_findings(sources) == [], "本块出现正则／语义词表位点"

    # 豁免面＝闭世界注册表，且块内非标识符形字符串集合**恰一处**（机器拒因闭世界子串校）
    non_identifier_sites = [
        (target, values)
        for _name, tree in sources
        for _lineno, target, values in _str_collection_sites(tree)
        if any(not _IDENTIFIER_SHAPE.fullmatch(value) for value in values)
    ]
    assert dict(non_identifier_sites) == {"_REROUTE_TRIGGERS": ("未绑定", "不在台账")}
    assert tuple(dict(non_identifier_sites)) == _VERBATIM_CHECK_EXEMPT

    # 探测器非空转（正则／词表名面／自建词表／豁免面外使用／分支判据语义明文五类各命中）
    probes: dict[str, str] = {
        "正则": "import re\nhit = re.search('拒答', text)\n",
        "词表名面": "LEXICON = {'拒答': '无据'}\n",
        "自建词表": "WORDS: tuple[str, ...] = ('拒答', '无据')\n",
        "豁免面外使用": (
            "_REROUTE_TRIGGERS: tuple[str, ...] = ('未绑定',)\nALL = list(_REROUTE_TRIGGERS)\n"
        ),
        "分支判据语义明文": "if kind == '拒答':\n    pass\n",
    }
    for label, source in probes.items():
        assert _lexicon_findings([(Path("forged.py"), ast.parse(source))]), f"{label} 面探测器空转"
    # 豁免不是漏网：豁免容器的合法用法（闭世界子串校）不被咬
    legit = (
        "_REROUTE_TRIGGERS: tuple[str, ...] = ('未绑定', '不在台账')\n"
        "shown = any(trigger in reason for trigger in _REROUTE_TRIGGERS)\n"
    )
    assert _lexicon_findings([(Path("forged.py"), ast.parse(legit))]) == []


# ---------- 22 【边界集】（空台账／缺水位／零未绑定指标／子问题清单超长） ----------


def test_boundary_empty_projection_variants() -> None:
    """行 22【边界集】空台账／缺水位／零未绑定指标（全可出数）／子问题清单超长 →
    各落占位文案／空串段／data 链形分支（行为 5／10；不降级与静默禁令）。"""
    # ① 空台账（未取得 `None` 与已取之空 `{}` 同落）→ 占位文案逐字在场；常驻块／分解样例＝空串段
    for empty in (_empty_state(), _empty_state_with_empty_dump()):
        book = assemble_task_book(empty, watermark="2026-08-24")
        assert _PLACEHOLDER_FAMILY in book and _PLACEHOLDER_RELATION in book
        assert book.count("\n  " + _PLACEHOLDER_EMPTY) == 3  # 指标／术语／对象各一（段不删）
        assert render_ledger_resident_block(empty) == ""  # 空串段（调用方跳过）
        assert render_decompose_example(empty.ledger_dump, today=_DECISION_TODAY) == ""
        package = _clarify_package(empty)
        assert "填写样例（分解形" not in package
        assert RESIDENT_BLOCK_BEGIN not in package and RESIDENT_BLOCK_END not in package
        # 不删段、不静默：指南段与 finalize 边界句仍在
        assert GUIDE_REFERENCE_HEAD in package and CLARIFY_FINALIZE_BOUNDARY in package
    assert "子问题结果清单：\n（无）" in assemble_answer_prompt(_empty_state())  # 占位文案

    # ② 缺水位 → 「（水位未取得）」逐字在场（不编造日期——零时钟接触的装配面形态）
    no_watermark = assemble_task_book(_ledger_state(), watermark="")
    assert f"- 数据水位：{_PLACEHOLDER_WATERMARK}——" in no_watermark
    assert re.search(r"\d{4}-\d{2}-\d{2}", no_watermark) is None  # 不因缺位凭空造日
    assert "- 数据水位：2026-08-24——" in assemble_task_book(
        _ledger_state(), watermark="2026-08-24"
    )

    # ③ 零未绑定指标（全可出数）→ data 链形分支；指标名录空列 → 该段空串（不编造样例）
    all_bound = _decision_dump()
    all_bound["metrics"] = [m for m in all_bound["metrics"] if m["binding_state"] == "bound"]
    example = render_decompose_example(all_bound["metrics"], today=_DECISION_TODAY)
    assert '"chain": "data", "tool": "data_query"' in example
    assert '"chain": "knowledge"' not in example
    assert '"chain": "data"' in _clarify_package(_decision_state(ledger_dump=all_bound))
    no_metrics = _decision_dump()
    no_metrics["metrics"] = []
    assert "填写样例（分解形" not in _clarify_package(_decision_state(ledger_dump=no_metrics))
    # 只该段缺位：台账其余块仍在（不整块降级、不另拼替代段）
    assert RESIDENT_BLOCK_BEGIN in _clarify_package(_decision_state(ledger_dump=no_metrics))

    # ④ 子问题清单超长（超 `max_subtasks` 声明槽）→ 全量在场（零截断：不省略、不落占位／空串）
    huge = [
        {
            "id": f"s{index}",
            "question": f"K12-3 井第{index}项生产数据？",
            "ledger_notes": "生产时长｜可出数｜2026-08-01~2026-08-24",
            "chain": "data",
            "tool": "data_query",
        }
        for index in range(1, _HUGE_SUBTASK_COUNT + 1)
    ]
    toolmatch = _toolmatch_package(_decision_state(question_group={"subtasks": huge}))
    group_json = toolmatch.split("问题组：\n", 1)[1].split("\n", 1)[0]
    rendered = json.loads(group_json)["subtasks"]
    assert [row["id"] for row in rendered] == [row["id"] for row in huge]  # 全量（不减条）
    assert all(row["question"] in toolmatch for row in huge)  # 逐条逐字在场
    assert "…" not in group_json  # 零省略号形占位
    long_results = [
        {"id": f"r{index}", "question": f"子问题{index}", "status": "ok"}
        for index in range(1, 41)
    ]
    long_answer = assemble_answer_prompt(
        RunState(run_id="run-long", question="超长清单题？", subtask_results=long_results)
    )
    assert long_answer.count("\n- [") == len(long_results)  # 逐条全量
    assert "…" not in long_answer and "（略）" not in long_answer


# ---------- 23 【保留集】（常规投影装配输出不受空投影分支影响） ----------


def test_retention_normal_assembly_unchanged() -> None:
    """行 23【保留集】常规投影装配输出不受空投影分支影响；四消费方既有验收断言不因本块改形
    回归（形状单点在 -04a——本票只加断言、不改形状）。"""
    answer_state = _answer_state()
    normal_book = assemble_task_book(_ledger_state(), watermark="2026-08-24")
    normal_decision = _decision_state()
    normal_clarify = _clarify_package(normal_decision)
    normal_toolmatch = _toolmatch_package(normal_decision)
    normal_answer = assemble_answer_prompt(answer_state)

    # ① 分支隔离：常规投影（-04a／-04b fixture）装配输出不含任何空投影／缺位产物
    empty_signals = (
        _PLACEHOLDER_FAMILY,
        _PLACEHOLDER_EMPTY,
        _PLACEHOLDER_RELATION,
        _PLACEHOLDER_WATERMARK,
        "（无）",
    )
    for label, output in (
        ("任务书", normal_book),
        ("澄清轮首入包", normal_clarify),
        ("匹配轮首入包", normal_toolmatch),
        ("答案轮", normal_answer),
    ):
        for signal in empty_signals:
            assert signal not in output, f"{label} 常规投影落空投影分支产物：{signal}"
    # 局部空块只染该块（分支不扩散）：术语块空 → 只该块落占位，其余块与水位照常
    partial = _ledger_dump()
    partial["terms"] = []
    partial_book = assemble_task_book(_ledger_state(ledger_dump=partial), watermark="2026-08-24")
    assert partial_book.count("\n  " + _PLACEHOLDER_EMPTY) == 1
    assert "生产时长｜可出数" in partial_book
    assert _PLACEHOLDER_FAMILY not in partial_book and _PLACEHOLDER_WATERMARK not in partial_book

    # ② 常规投影下各件原样（-04a／-04b 判据面抽样重钉——本票不改形）
    assert (
        normal_book.index(TASK_BOOK_SCENE)
        < normal_book.index(_DATA_ZONE_HEAD)
        < normal_book.index(TASK_BOOK_OUTPUT_CONTRACT)
        < normal_book.index(_QUESTION_HEAD)
    )
    assert "含水率｜未绑定（台账无数值——数值走报告检索）" in normal_book
    assert normal_clarify.count(RESIDENT_BLOCK_BEGIN) == 1
    assert normal_clarify.count(RESIDENT_BLOCK_END) == 1
    assert "填写样例（分解形" in normal_clarify and "问题组：" not in normal_clarify
    assert "问题组：" in normal_toolmatch and "填写样例（分解形" not in normal_toolmatch
    assert normal_answer.split("\n", 1)[0] == f"用户问题：{answer_state.question}"
    assert normal_answer.endswith(ANSWER_DRAFT_CONTRACT)
    assert "- [s2] K12-3 井含水率——失败（不在台账）" in normal_answer

    # ③ 四消费方消费面（R2 包根）形状保留：名单闭世界逐字＋Seam 签名位置面不变
    root = import_module("appv2.runtimev2.prompts")
    assert root.ASSEMBLY_FUNCTIONS == ASSEMBLY_FUNCTIONS
    assert dict(root.CONTRACT_CONSTANT_FAMILIES) == _SPEC_FAMILIES
    for func, card_name in (
        (assemble_task_book, "assemble_task_book"),
        (assemble_answer_prompt, "assemble_answer_prompt"),
    ):
        assert card_name in ASSEMBLY_FUNCTIONS  # 卡面两函数仍在族名单（四相位消费面）
        hints = get_type_hints(func)
        assert hints["state"] is RunState and hints["return"] is str
        parameters = list(inspect.signature(func).parameters.values())
        assert parameters[0].name == "state"  # 卡面 `(state) -> str` 的位置面不变
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters[1:]
        )  # 追加仕入参只许关键字形（四相位既有调用不回归）

    # ④ 消费方向（R2）＝包根唯一入口：四相位＋编排块零引深层子模块
    consumers = _consumer_sources()
    assert consumers, "消费方扫描面为空——看守失效"
    assert _deep_import_findings(consumers) == []
    forged = [
        (
            Path("forged.py"),
            ast.parse("from appv2.runtimev2.prompts.constants import ANSWER_REQUIREMENTS\n"),
        )
    ]
    assert _deep_import_findings(forged), "深层子模块引法未被咬（探测器空转）"

    # ⑤ 既有验收断言载体在场、旧码装配面不引本块（本票只加新件——四相位既有断言不回归）
    for relative in (
        "tests/domains/test_v2_v258_understand_orientation.py",
        "tests/domains/test_v2_v259_clarify_assembly.py",
        "tests/domains/test_v2_v262_turn_selfsufficiency.py",
    ):
        assert (_REPO_ROOT / relative).is_file(), f"四消费方既有验收断言载体丢失：{relative}"
    for relative in ("appv2/runtime/orientation.py", "appv2/runtime/graph.py"):
        path = _REPO_ROOT / relative
        assert path.is_file()
        modules = [
            module
            for _lineno, module in _imported_modules(ast.parse(path.read_text(encoding="utf-8")))
            if module.startswith("appv2.runtimev2")
        ]
        assert modules == [], f"旧码装配载体引了 V2 面：{relative} → {modules}"

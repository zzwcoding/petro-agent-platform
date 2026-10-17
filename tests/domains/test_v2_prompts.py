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

from appv2.runtimev2.clarification.constants import (
    BINDING_STATES,
    NOTE_SLOT_LITERALS,
    WINDOW_LITERALS,
)
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
    JARGON_PLAIN_GLOSSARY,
    LEDGER_DICT_NOTE,
    PHASE_CLARIFY,
    PHASE_TOOLMATCH,
    RESIDENT_BLOCK_BEGIN,
    RESIDENT_BLOCK_END,
    SUMMARY_CONTRACT,
    SYSTEM_BACKGROUND,
    TASK_BOOK_EXAMPLES,
    TASK_BOOK_OUTPUT_CONTRACT,
    TASK_BOOK_REDLINE,
    TASK_BOOK_SCENE,
    TASK_BOOK_TASK,
    TOOLMATCH_EMISSION_CONTRACT,
    TOOLMATCH_PHASE_HEAD,
    anchor_line,
    answer_system_contract,
    assemble_answer_prompt,
    assemble_decision_increment,
    assemble_decision_package,
    assemble_task_book,
    clarify_system_contract,
    render_decompose_example,
    render_ledger_resident_block,
    toolmatch_system_contract,
    understand_system_contract,
)
from appv2.runtimev2.prompts import constants as constants_module
from appv2.runtimev2.state import MAX_DISCOVERS_PER_RUN, RunState
from appv2.runtimev2.tool_matching import MENTION_MODES

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
    "answer_requirements": ("ANSWER_REQUIREMENTS", "JARGON_PLAIN_GLOSSARY"),
    # 2026-10-17 H 批（角色分家）：第七族＝链首背景块（`SYSTEM_BACKGROUND` 逐字稿）
    "system_background": ("SYSTEM_BACKGROUND",),
}

# 答案要求十条逐字稿（迁移照抄——V1 `orientation.py` `_ANSWER_REQUIREMENTS` ①–⑦；顺序固定；
# 2026-10-17 EB2 D2 追加第八条〔核验元数据不进答案正文〕——①–⑦条文文本不变，⑦尾「。」改
# 「；」＝条间分隔符；⑧内文自带一「；」（条文逐字，非分隔符——拼装表按字面连接断言）；
# 2026-10-17 EB4a 追加第九／第十条〔白话化条款〕——⑧尾「。」改「；」＝条间分隔符（条文文本
# 零改，体例同 EB2 D2：非末条尾字＝「；」、末条尾「。」）；⑨内文自带一「；」＝条内标点）。
_ANSWER_REQUIREMENTS_VERBATIM: tuple[str, ...] = (
    "逐条事实断言带 [n] 引标（n＝观察材料序号）；",
    "材料未覆盖的部分不得断言、如实说明未覆盖；",
    "材料含多个来源（不同报告／油田／井）时逐个来源分别作答（不冲突也要分别列出，不以反问代替作答）；",
    "作答后仍有未覆盖的来源或指代不明处，如实点名未覆盖来源（含检索窗注记的未进窗来源）"
    "并请用户补充检索或指明对象，不静默略过；",
    "引擎的降级/未绑定/拦停注记必须如实转述进对应子问题条目（不得静默丢弃）；",
    "引用观察材料请摘录必要短语并带引标，禁整段照搬原文充当回答；",
    "「理解：／指标候选：」及任何动作 JSON 是过程产物，出现在答案中即废品；",
    "核验元数据（血缘卡五要素、来源表、数据批次）不写进答案正文——它们在界面"
    "『引用与口径』侧栏逐字展示；答案只在用户需要时带一句口径（如单位）；",
    "面向油田业务用户作答：系统内部词首次出现时紧跟一句括号里的白话解释——如"
    "『口径（这个数是按什么规则算的）』『台账（平台里登记指标和术语的名册）』；同一词后文"
    "可直接使用。不要把内部说法整句甩给用户（『召回 51 支/送窗 12 支』应写成"
    "『检索到 51 条材料，其中 12 条用进了答案』）；",
    "材料未覆盖所问时：先从已给材料中答出可能与问题相关的内容，再给用户一句更容易查到结果的"
    "提问建议（如补充井号、时间范围或报告名称）。",
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
        "JARGON_PLAIN_GLOSSARY",
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
        "JARGON_PLAIN_GLOSSARY",
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

    # pin-24 本块承诺面＝合同常量逐字稳定（常量无逐轮变体）：槽位仅 CLARIFY 一枚声明槽
    # （`{discover_used}` 槽随「已用 N 次」冻值退场——2026-10-17 消重批·缺陷二：静态块内的槽值
    # 只在相位首入替换一次、随链恒冻，真实已用数改由每轮动态条披露），且换状态装配后合同段逐字不变。
    # 槽位＝Python 格式化槽（标识符形占位字段）；JSON 花括号示例不计（形态处理豁免面）
    assert CLARIFY_EMISSION_CONTRACT.startswith("【相位①·业务澄清】")  # 相位合同头行
    assert TOOLMATCH_EMISSION_CONTRACT.startswith("【相位②·工具匹配】")
    slots = {
        name: _format_slots(value) for name, value in _contract_constants().items()
    }
    assert {name: fields for name, fields in slots.items() if fields} == {
        "CLARIFY_EMISSION_CONTRACT": {"max_subtasks"}
    }
    # 静态合同零计数（缺陷二钉）：上限留静态块、已用数只在动态条——契约文本与限额单点同值
    assert "已用 " not in CLARIFY_EMISSION_CONTRACT
    assert f"全 run ≤{MAX_DISCOVERS_PER_RUN} 次" in CLARIFY_EMISSION_CONTRACT
    # 指令区＋输出契约区（规章段＝system 承载位）逐字稳定、各恰一份；
    # 动态段（数据区＋题干段）与之分家
    first_contract = understand_system_contract()
    second_contract = understand_system_contract()
    first = assemble_task_book(_ledger_state())
    second = assemble_task_book(_ledger_state(question="换个题", understanding="换个题意"))
    for constant in _SPEC_FAMILIES["task_book_skeleton"]:
        text = getattr(constants_module, constant)
        assert first_contract.count(text) == 1
        assert second_contract.count(text) == 1
        assert text not in first and text not in second  # 规章件不入 user 动态段
    assert first_contract == second_contract  # 规章段与 state 无关（逐字稳定）
    assert first.split(_DATA_ZONE_HEAD)[0] == second.split(_DATA_ZONE_HEAD)[0] == ""


# ---------- 2 答案要求清单 10 条逐字在场（pin-03 落点） ----------


def test_answer_requirements_verbatim() -> None:
    """答案要求 10 条逐字在场、顺序固定（pin-03：③多来源分源逐字在场）。

    拼装面逐字相等（①–⑨条文尾「；」、末条尾「。」）——⑧／⑨内文各自带一「；」，故不以
    `split("；")` 计数（分隔符与条文内文两事）。
    """
    assert ANSWER_REQUIREMENTS == "".join(_ANSWER_REQUIREMENTS_VERBATIM)
    assert ANSWER_REQUIREMENTS.count("；") == 11  # ①–⑨条间分隔 9 ＋ ⑧内文 1 ＋ ⑨内文 1
    assert not ANSWER_REQUIREMENTS.endswith("；")
    # pin-03 落点＝③多来源分源逐字在场（交付行为面待 `specs/answering.md` 回提承接）
    assert "材料含多个来源（不同报告／油田／井）时逐个来源分别作答" in ANSWER_REQUIREMENTS
    assert "不以反问代替作答" in ANSWER_REQUIREMENTS
    # ⑧ 核验元数据不进答案正文（2026-10-17 EB2 D2 尾条——EB4a 后成条间条，尾字＝分隔符「；」）
    item8 = _ANSWER_REQUIREMENTS_VERBATIM[7]
    assert item8.startswith("核验元数据（血缘卡五要素、来源表、数据批次）")
    assert "『引用与口径』侧栏逐字展示" in ANSWER_REQUIREMENTS
    # ⑨ 术语注解条款（2026-10-17 EB4a）：两个白话注解示例＋系统腔句改写示例逐字在场
    item9 = _ANSWER_REQUIREMENTS_VERBATIM[8]
    assert item9.startswith("面向油田业务用户作答：")
    assert "『口径（这个数是按什么规则算的）』『台账（平台里登记指标和术语的名册）』" in (
        ANSWER_REQUIREMENTS
    )
    assert "不要把内部说法整句甩给用户（『召回 51 支/送窗 12 支』应写成" in ANSWER_REQUIREMENTS
    assert "『检索到 51 条材料，其中 12 条用进了答案』）" in ANSWER_REQUIREMENTS
    # ⑩ 材料未覆盖→先答相关＋给提问建议（2026-10-17 EB4a；Owner 当日裁决＝召回问题提示词侧缓解）
    item10 = _ANSWER_REQUIREMENTS_VERBATIM[9]
    assert item10.startswith("材料未覆盖所问时：")
    assert item10.endswith("（如补充井号、时间范围或报告名称）。")
    assert ANSWER_REQUIREMENTS.endswith(item10)  # 末条＝⑩（尾「。」）
    # 合同侧经答案轮装配把十条全文送进模型面（2026-10-17 H 批：规章段改走 system 承载位——
    # 十条全文在 `answer_system_contract()` 内，随本次请求前置为 system 条、不入链）
    assert f"【答案要求】{ANSWER_REQUIREMENTS}" in answer_system_contract()


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


# ---------- 3b 术语白话表（族⑥示例区）＝单源＋随答案包恰一次、字节级稳定 ----------


def test_jargon_plain_glossary_injected_once() -> None:
    """术语白话表＝族⑥示例区单源常量、随答案装配包恰一次入链、字节级稳定（2026-10-17 EB4a）。

    病根（EB3 全量首测）：系统行话「口径／台账／召回／送窗／水位」首现无白话注解。
    对策＝术语表注入（静态块：确定性、零幻觉、缓存友好；真源
    `docs/runtime-refactor/research/最佳实践-3a-白话化与受众适配.md` 第三节 3.1 A）：文本单点＝
    `constants.py`、注入点＝`answer_round.assemble_answer_prompt`（`state.Message` 面零副本）。
    """
    # ①文本逐条（七条映射、条目序固定；首尾逐字）
    assert JARGON_PLAIN_GLOSSARY.startswith("【术语白话表】口径＝这个数是按什么规则算的；")
    assert JARGON_PLAIN_GLOSSARY.endswith("送窗＝用进答案的材料。")
    for entry in (
        "口径＝这个数是按什么规则算的",
        "台账＝平台里登记指标和术语的名册",
        "水位＝数据目前更新到哪一天",
        "窗＝统计的时间段",
        "绑定＝登记关联",
        "召回＝检索到的材料",
        "送窗＝用进答案的材料",
    ):
        assert entry in JARGON_PLAIN_GLOSSARY
    # 与条款⑨的两处示例同一白话（术语全文一致——不各说各话）
    assert "『口径（这个数是按什么规则算的）』" in ANSWER_REQUIREMENTS
    assert "『台账（平台里登记指标和术语的名册）』" in ANSWER_REQUIREMENTS

    # ②单源：runtimev2 面内恰一处字面定义（消费方零字面副本）
    feature = "【术语白话表】口径＝这个数是按什么规则算的"
    assert feature in JARGON_PLAIN_GLOSSARY
    hits = _hits(_runtimev2_sources(), feature)
    assert hits == [_CONSTANTS_FILE.name], f"术语白话表出现多处以字面定义：{hits}"

    # ③随答案规章段（system 承载位）恰一次、字节级稳定（两跑／异状态逐字同源）；
    #   静态块置前、投影段在后（2026-10-17 H 批：白话表随规章段走 system，dynamic 段留 user）
    assert answer_system_contract() == answer_system_contract()
    contract = answer_system_contract()
    assert contract.count(JARGON_PLAIN_GLOSSARY) == 1
    assert contract.split("\n")[2] == JARGON_PLAIN_GLOSSARY  # 紧随【答案要求】全文（静态块置前）
    assert contract.index("【答案要求】") < contract.index(JARGON_PLAIN_GLOSSARY)
    assert contract.index(JARGON_PLAIN_GLOSSARY) < contract.index(SUMMARY_CONTRACT)
    # 动态段（user 位）不再携白话表（规章与材料分家）
    for state in (_answer_state(), _empty_state()):
        assert JARGON_PLAIN_GLOSSARY not in assemble_answer_prompt(state)
    assert assemble_answer_prompt(_answer_state()) == assemble_answer_prompt(_answer_state())


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


# ---------- 5 任务书两段序固定、题干段置末 ----------


def test_task_book_segment_order() -> None:
    """任务书两段（2026-10-17 H 批角色分家）：**规章段**（system）＝指令区→输出契约区；
    **动态段**（user）＝数据区→题干段；题干段为末段。

    段内相对序零改（行为 3 的四常量相对序、行为 2 的数据区、题干置末）；两段拼合的可见序＝
    「规章段（system，前置）→动态段（user）」——合看仍是「指令区→输出契约区→数据区→题干段」。
    """
    contract = understand_system_contract()
    output = assemble_task_book(_ledger_state(), watermark="2026-08-24")
    order_contract = [
        TASK_BOOK_SCENE,
        TASK_BOOK_TASK,
        TASK_BOOK_EXAMPLES,
        TASK_BOOK_REDLINE,  # 指令区内四常量相对序：场景→任务→样例→红线
        TASK_BOOK_OUTPUT_CONTRACT,
    ]
    positions = [contract.index(marker) for marker in order_contract]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)
    # 动态段：数据区→题干段（题干段为末段、紧邻生成点）
    assert output.startswith(_DATA_ZONE_HEAD)
    assert output.index(_DATA_ZONE_HEAD) < output.index(_QUESTION_HEAD)
    assert output.rstrip().endswith("现在输出。）")  # 题干段为末段（紧邻生成点）
    # 段间「\n\n」连接（真源 R-L2a-17 连接形）
    assert f"\n\n{_QUESTION_HEAD}" in output
    assert f"\n\n{TASK_BOOK_OUTPUT_CONTRACT}" in contract
    # 红线归位＝指令区（V2 设计变更：V1 在环境段之后）；规章件不入动态段（H 批承载位分家）
    assert contract.index(TASK_BOOK_REDLINE) < contract.index(TASK_BOOK_OUTPUT_CONTRACT)
    for constant in order_contract:
        assert constant not in output, f"规章件仍在 user 动态段：{constant[:12]}"


# ---------- 6 任务书样例区＝固定三则 ----------


def test_task_book_examples_fixed_set() -> None:
    """任务书样例区＝固定三则、不随 state 变化、无边界对照例（随规章段走 system 位）。"""
    for label in ("样例一（多部分题）", "样例二（口语映射题）", "样例三（判断纠错题）"):
        assert label in TASK_BOOK_EXAMPLES
    assert "样例四" not in TASK_BOOK_EXAMPLES
    assert "边界" not in TASK_BOOK_EXAMPLES.split("样例三", 1)[0].split("样例一", 1)[1]
    # 样例区＝指令区常量直引（两跑逐字同源）；在两段（system 规章段／user 动态段）中皆恰一处
    assert understand_system_contract().count(TASK_BOOK_EXAMPLES) == 1
    for state in (_ledger_state(), _empty_state()):
        assert TASK_BOOK_EXAMPLES not in assemble_task_book(state)


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


# ---------- 17 答案轮两段序固定、材料段零渗入 ----------


def test_answer_round_segment_order_no_material() -> None:
    """答案轮两段（2026-10-17 H 批角色分家）：**规章段**（system）＝动词钉死句→【答案要求】全文→
    术语白话表→汇总合同→起草答案合同（收尾）；**动态段**（user）＝题面件→子问题结果清单；
    材料段零渗入（材料渲染归 context，调用方追加于尾）。
    """
    state = _answer_state()
    contract = answer_system_contract()
    output = assemble_answer_prompt(state)
    lines = contract.split("\n")
    assert lines[0] == _VERB_PIN
    assert lines[1] == f"【答案要求】{ANSWER_REQUIREMENTS}"
    assert lines[2] == JARGON_PLAIN_GLOSSARY  # 族⑥示例区（EB4a——静态块紧跟答案要求）
    markers = [JARGON_PLAIN_GLOSSARY, SUMMARY_CONTRACT, ANSWER_DRAFT_CONTRACT]
    positions = [contract.index(marker) for marker in markers]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)
    assert lines[3] == ""
    assert contract.endswith(ANSWER_DRAFT_CONTRACT)  # 末段＝起草答案合同（收尾）
    # 动态段：题面件置首、子问题清单其后（材料段由调用方追加于尾）
    out_lines = output.split("\n")
    assert out_lines[0] == f"用户问题：{state.question}"
    assert out_lines[1] == "子问题结果清单："
    # 子问题清单逐条在场（含拒因原文与排名支配标记——零人话翻译、零词表）
    ranking = "- [s1] K12-3 井生产时长——完成（排名型——结论必须从本子问题排名观察支"
    assert ranking in output
    assert "- [s2] K12-3 井含水率——失败（不在台账）" in output
    # 规章件不入动态段（承载位分家）
    for marker in (
        f"【答案要求】{ANSWER_REQUIREMENTS}",
        JARGON_PLAIN_GLOSSARY,
        ANSWER_DRAFT_CONTRACT,
    ):
        assert marker not in output
    # 材料段零渗入：观察行内容不进装配输出（材料渲染归 context）
    for observation in state.observations:
        assert observation["content"] not in output


# ---------- 18 答案轮禁令件在场（pin-13 合同侧） ----------


def test_answer_round_ban_lines_present() -> None:
    """答案轮禁令件在场：动词钉死句＋答案要求⑦两字面（pin-13 合同侧；不注入回声形指令）。

    2026-10-17 H 批：禁令件随**规章段**（system 承载位）在场（`answer_system_contract`），
    动态段（user 位）不携合同件。
    """
    contract = answer_system_contract()
    assert _VERB_PIN in contract and contract.count(_VERB_PIN) == 1
    assert _ANSWER_REQUIREMENTS_VERBATIM[6] in contract  # ⑦ 逐字
    assert "finalize/decompose 等动作出现即废品" in contract
    # 提示词侧不注入回声形指令：只出禁令件，无「回声」类指令字样
    assert "回声" not in contract
    # 空状态亦恒在场（禁令件不随 state 缺位消失）
    assert _VERB_PIN in answer_system_contract()

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


def _clarify_contract(max_subtasks: Any = _MAX_SUBTASKS) -> str:
    """澄清环节规章段（system 承载位——2026-10-17 H 批）。"""
    return clarify_system_contract(max_subtasks)


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

    2026-10-17 补（真机消重批·缺陷一／二）：①run 级共享上下文（§A 指南段＋台账常驻块）随
    `shared_context` 标志整段进出（编排判「本 run 是否已注」后下传——缺省 `True`＝函数本体行为）；
    ②静态合同不再携「已用 N 次」冻值（真实已用数只在每轮动态条）。
    **2026-10-17 H 批（角色分家）**：**规章件**（相位头行＋相位合同＋finalize 交付面边界句）出
    user 首入包、改走**调用级 system 注入参**（`clarify_system_contract`／
    `toolmatch_system_contract`）
    ——本行判据＝动态段（user）与规章段（system）合看逐件在场（四要素口径不变）。
    """
    state = _decision_state(discover_used=2)
    clarify = _clarify_package(state)
    toolmatch = _toolmatch_package(state)
    clarify_contract = _clarify_contract()
    toolmatch_contract = toolmatch_system_contract()

    # ①题意锚行（动态段首行）＋②相位合同（规章段：头行＋正文；澄清轮另含 finalize 交付面边界句）
    assert clarify.split("\n", 1)[0] == anchor_line(state.question, state.understanding)
    assert CLARIFY_PHASE_HEAD in clarify_contract
    assert "【相位①·业务澄清】只输出一个 JSON 对象（可围栏）。四动作：" in clarify_contract
    assert "子问题 ≤4 个" in clarify_contract  # 声明槽 {max_subtasks}＝调用方注入值
    assert "可用探查（discover，全 run ≤10 次）：" in clarify_contract  # 静态合同只留上限、不载计数
    assert "已用 " not in clarify_contract  # 合同段零「已用 N 次」冻值
    assert CLARIFY_FINALIZE_BOUNDARY in clarify_contract
    assert clarify_contract.endswith(CLARIFY_FINALIZE_BOUNDARY)  # 界线句收尾（段内相对序不变）
    # 规章件不入 user 动态段（承载位分家）
    for marker in (CLARIFY_PHASE_HEAD, CLARIFY_FINALIZE_BOUNDARY):
        assert marker not in clarify
    # ③产出样例（澄清轮）＋④§A 指南段（文本经入参注入）
    assert "填写样例（分解形——五键齐全" in clarify
    assert '"chain": "knowledge"' in clarify
    assert f"{GUIDE_REFERENCE_HEAD}\n{_GUIDE_TEXT}" in clarify
    # ⑥常驻块包裹对恰一对（投影非空）＋包尾
    assert clarify.count(RESIDENT_BLOCK_BEGIN) == 1
    assert clarify.count(RESIDENT_BLOCK_END) == 1
    assert clarify.endswith(RESIDENT_BLOCK_END)
    # 动态段逐件序：锚行→样例→指南段→常驻块（段内相对序：样例先于指南段——照原装配序）
    order = [
        anchor_line(state.question, state.understanding),
        "填写样例（分解形",
        GUIDE_REFERENCE_HEAD,
        RESIDENT_BLOCK_BEGIN,
    ]
    positions = [clarify.index(marker) for marker in order]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)

    # 匹配轮各按其件：规章段＝合同头＋正文（产出样例＝合同内嵌样例）；动态段⑤问题组 JSON
    assert toolmatch.split("\n", 1)[0] == anchor_line(state.question, state.understanding)
    assert TOOLMATCH_PHASE_HEAD in toolmatch_contract
    assert TOOLMATCH_EMISSION_CONTRACT in toolmatch_contract
    assert "填写样例（单匹配 knowledge 形）" in toolmatch_contract
    assert TOOLMATCH_PHASE_HEAD not in toolmatch
    assert '\n\n问题组：\n{"subtasks": [{"id": "s1"' in toolmatch
    assert toolmatch.count(RESIDENT_BLOCK_BEGIN) == 1
    assert toolmatch.count(RESIDENT_BLOCK_END) == 1
    assert toolmatch.endswith(RESIDENT_BLOCK_END)
    # 各按其件（不互串）：澄清轮无问题组段、匹配轮无分解样例段
    assert "问题组：" not in clarify
    assert "填写样例（分解形" not in toolmatch

    # 2026-10-17 补（缺陷一）：run 级共享上下文缺席形（编排判「本 run 已注」后下传
    # `shared_context=False`）——§A 指南段与台账常驻块**两段整段缺席**，其余件照常在场
    later = _toolmatch_package(state, shared_context=False)
    assert GUIDE_REFERENCE_HEAD not in later and _GUIDE_TEXT not in later
    assert RESIDENT_BLOCK_BEGIN not in later and RESIDENT_BLOCK_END not in later
    assert '\n\n问题组：\n{"subtasks": [{"id": "s1"' in later
    assert later.endswith(
        "\n\n问题组：\n" + json.dumps(state.question_group, ensure_ascii=False)
    )  # 尾段＝问题组 JSON（常驻块零尾附）
    quiet = _clarify_package(state, shared_context=False)
    assert GUIDE_REFERENCE_HEAD not in quiet and _GUIDE_TEXT not in quiet
    assert RESIDENT_BLOCK_BEGIN not in quiet and RESIDENT_BLOCK_END not in quiet
    assert "填写样例（分解形" in quiet
    assert quiet.endswith('"chain": "data", "tool": "data_query"}]}}') or quiet.endswith("}")
    # 两段落链文本字节级不变（只改出现次数）：缺席形＝删段，逐字同源（不重排、不改写）
    assert _GUIDE_TEXT in clarify and RESIDENT_BLOCK_BEGIN in clarify

    # 四要素按轮合看逐轮在场：任务动词（合同头，system 规章段）／题意锚（锚行，user 动态段）／
    # 产出样例（澄清轮＝动态段样例／匹配轮＝规章段合同内嵌样例）／失败反馈（增量条回喂）
    rejected = _decision_state(discover_used=2, decision_error="缺 subtasks 键")
    for phase, package, sample, head, contract in (
        (
            PHASE_CLARIFY,
            _clarify_package(rejected),
            "填写样例（分解形",
            CLARIFY_PHASE_HEAD,
            _clarify_contract(),
        ),
        (
            PHASE_TOOLMATCH,
            _toolmatch_package(rejected),
            "填写样例（单匹配 knowledge 形）",
            TOOLMATCH_PHASE_HEAD,
            toolmatch_system_contract(),
        ),
    ):
        assert phase in DECISION_PHASES
        assert package.split("\n", 1)[0] == anchor_line(
            rejected.question, rejected.understanding
        )
        assert head in contract  # 任务动词＝规章段（system 位）
        assert sample in (package + contract)  # 产出样例（两轮各按其位）
        assert "上次发射被拒：缺 subtasks 键——修正后重新输出 JSON。" in (
            assemble_decision_increment(rejected, phase=phase)
        )

    # 装配函数族成员经包根可达（本票成员全在名单闭世界——R2 公开面；H 批四件同列）
    for name in (
        "anchor_line",
        "assemble_decision_package",
        "assemble_decision_increment",
        "render_ledger_resident_block",
        "render_decompose_example",
        "clarify_system_contract",
        "toolmatch_system_contract",
    ):
        assert name in ASSEMBLY_FUNCTIONS

    # 形态越界＝参数错误（不吞错、不返回哨兵——先例 `specs/context.md` 错误契约：
    # 相位越界／族②声明槽缺值均属调用方违约，非业务错，故不落占位文案也不静默）
    with pytest.raises(ValueError):
        assemble_decision_package(state, phase="no-such-phase", guide_text=_GUIDE_TEXT)
    # 2026-10-17 H 批：族②声明槽的 fail-closed 点随规章件改在**规章取件函数**（槽值转交面）
    with pytest.raises(ValueError):
        _clarify_contract(max_subtasks=None)


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
                "status": "bad_args",
                "reason": "未绑定（台账无数值）",
            },
            {"id": "s3", "question": "井筒口径", "status": "bad_args", "reason": "不在台账"},
            {"id": "s4", "question": "生产时长", "status": "retryable", "reason": "参数缺失"},
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


def test_rejection_feedback_frame_single() -> None:
    """行 11 补（流水 66·叠字病灶）：拒因回喂行**壳体恰一遍**——已自带壳者原样透传。

    真机 `run-18e5d273` 回喂形＝「上次发射被拒：上次发射被拒：ledger_notes…」「——修正后重新
    输出 JSON。——修正后重新输出 JSON。」：槽位对账拒因载荷自带整套壳体（`specs/clarification.md`
    行为 8／「接口定义」错误契约，流水 64 裁），回喂行再套一次即叠字。断言两面：①已自带壳者
    **原样透传**（不改写、不二次套壳——两相各计 1，且与载荷原文逐字相等）；②裸拒因照套壳一次
    （旧形零回归：拒因回喂条逐字稿不变）。
    """
    framed = (
        "上次发射被拒：ledger_notes 槽位对账未过：s1\n"
        "【拒因】s1 的「槽位」段「完井液密度」不在台账名录\n"
        "【期望形】〈台账行首名｜或「无台账命中」〉｜已绑定|未绑定｜〈锚定窗形：…〉\n"
        "【台账相关行】（无命中形——本子问题不锚台账行）\n"
        "——修正后重新输出 JSON。"
    )
    for phase in (PHASE_CLARIFY, PHASE_TOOLMATCH):
        text = assemble_decision_increment(
            _decision_state(decision_error=framed), phase=phase
        )
        assert text == framed  # 原样透传（首入轮／匹配轮均如此——增量条仅此一件在场）
        assert text.count("上次发射被拒：") == 1
        assert text.count("——修正后重新输出 JSON。") == 1

    # 透传只认「已自带壳」这一形态面：裸拒因照套壳一次（逐字稿不变）
    assert (
        assemble_decision_increment(
            _decision_state(decision_error="缺 subtasks 键"), phase=PHASE_CLARIFY
        )
        == "上次发射被拒：缺 subtasks 键——修正后重新输出 JSON。"
    )


def test_rework_line_status_world() -> None:
    """行 11 补：回炉条判据＝**重跑面两档**（`bad_args`／`retryable`——真源 execution
    `subtask_results` 状态闭世界〔流水 59〕）：两档渲染回炉条；`ok`（成品不重跑）／`refused`
    （终局不回炉）零渲染。
    """
    # 判据单点＝prompts 常量点两档（不引 execution 包——R1）
    module = import_module("appv2.runtimev2.prompts.decision_round")
    assert module._REWORK_STATUSES == {"bad_args", "retryable"}

    rerun = _decision_state(
        contracts_appended=[PHASE_CLARIFY],
        subtask_results=[
            {"id": "s1", "question": "含水率", "status": "bad_args", "reason": "参数缺失"},
            {"id": "s2", "question": "井筒口径", "status": "retryable", "reason": "上游超时"},
        ],
    )
    # 两档各成一行、逐字在场（预算条在前——段序不变）
    assert assemble_decision_increment(rerun, phase=PHASE_CLARIFY).split("\n")[1:] == [
        "回炉：只分解以下失败/缺失子问题（成功子问题结果已保留，禁止重复分解执行）：",
        "- [s1] 含水率——拒因：参数缺失",
        "- [s2] 井筒口径——拒因：上游超时",
    ]

    # 非重跑两档零渲染：`ok` 不重跑、`refused` 终局不回炉 → 回炉条整条缺席
    for status in ("ok", "refused"):
        terminal = _decision_state(
            contracts_appended=[PHASE_CLARIFY],
            subtask_results=[
                {
                    "id": "s1",
                    "question": "含水率",
                    "status": status,
                    "reason": "未绑定（台账无数值）",
                }
            ],
        )
        assert "回炉：" not in assemble_decision_increment(terminal, phase=PHASE_CLARIFY)

    # 混合态：只重跑档成行，终局／成品两档一律不进条
    mixed = _decision_state(
        contracts_appended=[PHASE_CLARIFY],
        subtask_results=[
            {"id": "s1", "question": "已成", "status": "ok"},
            {"id": "s2", "question": "已拒", "status": "refused", "reason": "不在台账"},
            {"id": "s3", "question": "改参", "status": "bad_args", "reason": "参数缺失"},
            {"id": "s4", "question": "重试", "status": "retryable", "reason": "上游超时"},
        ],
    )
    assert assemble_decision_increment(mixed, phase=PHASE_CLARIFY).split("\n")[1:] == [
        "回炉：只分解以下失败/缺失子问题（成功子问题结果已保留，禁止重复分解执行）：",
        "- [s3] 改参——拒因：参数缺失",
        "- [s4] 重试——拒因：上游超时",
    ]


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
    # 段二字面＝澄清对账闭世界值（样例教的即闸收的；真源 `specs/clarification.md` 行为 8②）
    assert "生产时长｜已绑定｜2026-07-25~2026-08-24" in data
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
    """行 15 分解样例产出为合法 JSON 且键形正确（行为 10；D-L2a-13 病灶不复现）。

    样例区**两行**（2026-10-17 补·分解样例补行）：首行＝现造锚定指标形、次行＝无台账命中形全样例行；
    两行各自为合法 JSON（本行断首行；无命中行形另见 `::decompose_example_no_hit_full_row`）。
    """
    bound = {"slot": "生产时长", "binding_state": "bound", "value": "x"}
    example = render_decompose_example([bound], today=_DECISION_TODAY)
    assert example.endswith("}]}}")
    obj, _rest = json.JSONDecoder().raw_decode(example[example.index("{") :])
    assert set(obj) == {"action", "question_group"}  # 顶层恰两键
    assert obj["action"] == "decompose"
    assert set(obj["question_group"]) == {"subtasks"}  # 顶层 subtasks 单键形
    subtasks = obj["question_group"]["subtasks"]
    assert isinstance(subtasks, list) and len(subtasks) == 1  # subtasks 单条
    assert set(subtasks[0]) == {"id", "question", "ledger_notes", "chain", "tool"}  # 五键齐全
    assert subtasks[0]["id"] == "s1"
    assert subtasks[0]["ledger_notes"] == "生产时长｜已绑定｜2026-07-25~2026-08-24"

    # 转义面：指标名含裸引号／反斜杠时，json.dumps 转义后仍合法（裸拼即非法）
    hostile = {"slot": '时率"高"\\', "binding_state": "bound", "value": "x"}
    hostile_example = render_decompose_example([hostile], today=_DECISION_TODAY)
    hostile_obj, _rest = json.JSONDecoder().raw_decode(
        hostile_example[hostile_example.index("{") :]
    )
    assert hostile_obj["question_group"]["subtasks"][0]["question"] == '时率"高"\\是多少？'

    # 澄清轮首入包内现造的同一条样例亦为合法 JSON（装配面无第二拼接路径）；两行同在且逐行合法
    state = _decision_state()
    assert isinstance(state.ledger_dump, dict)
    example_full = render_decompose_example(state.ledger_dump["metrics"], today=_DECISION_TODAY)
    assert example_full in _clarify_package(state)
    for row in example_full.split("\n"):
        json.loads(row[row.index("{") :])


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
        # 不删段、不静默：指南段仍在（动态段）；finalize 边界句随规章段（system 位）恒在场
        assert GUIDE_REFERENCE_HEAD in package and CLARIFY_FINALIZE_BOUNDARY in _clarify_contract()
    assert "子问题结果清单：\n（无）" in assemble_answer_prompt(_empty_state())  # 占位文案

    # ② 缺水位 → 「（水位未取得）」逐字在场（不编造日期——零时钟接触的装配面形态）
    no_watermark = assemble_task_book(_ledger_state(), watermark="")
    assert f"- 数据水位：{_PLACEHOLDER_WATERMARK}——" in no_watermark
    assert re.search(r"\d{4}-\d{2}-\d{2}", no_watermark) is None  # 不因缺位凭空造日
    assert "- 数据水位：2026-08-24——" in assemble_task_book(
        _ledger_state(), watermark="2026-08-24"
    )

    # ③ 零未绑定指标（全可出数）→ **首行**取 data 链形分支（次行＝无命中形恒 knowledge 链）；
    # 指标名录空列 → 该段空串（不编造样例）
    all_bound = _decision_dump()
    all_bound["metrics"] = [m for m in all_bound["metrics"] if m["binding_state"] == "bound"]
    example = render_decompose_example(all_bound["metrics"], today=_DECISION_TODAY)
    first_row = example.split("\n", 1)[0]  # 锚定指标形行（现造）
    assert '"chain": "data", "tool": "data_query"' in first_row
    assert '"chain": "knowledge"' not in first_row
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

    # ② 常规投影下各件原样（-04a／-04b 判据面抽样重钉——本票不改形；2026-10-17 H 批：
    #    规章段（system）与动态段（user）**合看**仍是「指令区→输出契约区→数据区→题干段」）
    full = understand_system_contract() + "\n\n" + normal_book
    assert (
        full.index(TASK_BOOK_SCENE)
        < full.index(TASK_BOOK_OUTPUT_CONTRACT)
        < full.index(_DATA_ZONE_HEAD)
        < full.index(_QUESTION_HEAD)
    )
    assert "含水率｜未绑定（台账无数值——数值走报告检索）" in normal_book
    assert normal_clarify.count(RESIDENT_BLOCK_BEGIN) == 1
    assert normal_clarify.count(RESIDENT_BLOCK_END) == 1
    assert "填写样例（分解形" in normal_clarify and "问题组：" not in normal_clarify
    assert "问题组：" in normal_toolmatch and "填写样例（分解形" not in normal_toolmatch
    assert normal_answer.split("\n", 1)[0] == f"用户问题：{answer_state.question}"
    assert "- [s2] K12-3 井含水率——失败（不在台账）" in normal_answer
    # 规章件（起草答案合同／finalize 边界句／相位头行）出 user 动态段、在 system 规章段
    assert ANSWER_DRAFT_CONTRACT not in normal_answer
    assert CLARIFY_FINALIZE_BOUNDARY not in normal_clarify
    assert TOOLMATCH_PHASE_HEAD not in normal_toolmatch
    assert ANSWER_DRAFT_CONTRACT in answer_system_contract()
    assert CLARIFY_FINALIZE_BOUNDARY in clarify_system_contract(_MAX_SUBTASKS)
    assert TOOLMATCH_PHASE_HEAD in toolmatch_system_contract()

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


# ══════════════════════════════════════════════════════════════════════════════════════
# L0/L2 三病灶修复批（2026-10-16）：合同/样例教据面 ↔ 闸闭世界对账
# ══════════════════════════════════════════════════════════════════════════════════════


def test_decompose_example_head_window_rule() -> None:
    """分解样例头行的窗词锚定说明句＋无台账行说明句在场（行为 10；2026-10-16 补（L0/L2 三病灶
    修复批②／流水 66·L3 阻塞修复批）；2026-10-17 补（L3 阻塞修复批·分解样例补行）再补半句）。

    真机形（`docs/runtime-refactor/ladder/L2/01` 的 `id=3`／`id=5` 两轮必拒「ledger_notes 槽位
    对账未过」）＝首秀形在窗段无据可依：样例头行只说「窗按窗词锚定表现算」，对模糊时间词（最近／
    近期）无片言，模型自造窗形即被三段槽位对账拒。合法形真源＝`specs/clarification.md` 行为 8③
    （锚定窗／窗未定（同义「无时间窗」）／双 null 三形）。**流水 66 同类补**：报告内容题
    （`docs/runtime-refactor/ladder/L3/01`：完井液密度无台账行）在旧教据下无合法槽位形可写 →
    头行补「子问题无台账行＝槽位写「无台账命中」，不硬凑名」，合法形真源＝行为 8①。**本批再补
    半句**（真机 `run-b5b6b056` 两轮凑不齐三段：段尾加解释／绑定态窗段自造形）＝「——三段照抄上形：
    无台账命中｜未绑定｜窗未定（不加解释、不改写）」，与次行无命中形全样例行（
    `::decompose_example_no_hit_full_row`）配套。
    断言：头行点名两档出路（模糊时间词写 `null~null`＋引擎缺参反问兜底三选一＋不自行锚窗／
    无台账行写「无台账命中」不硬凑名＋三段照抄上形），且该句随澄清轮首入包同现（装配面逐字在场，
    非只在常量里）；样例 JSON 与单行形零破。
    """
    package = _clarify_package(_decision_state())
    line = _unique_line(package, "填写样例（分解形")  # 样例段恰一处（段行单点）
    for sentence in (
        "模糊时间词（最近/近期）＝窗写 null~null",
        "由引擎缺参反问兜底三选一",
        "不要自己锚窗",
        "子问题无台账行（报告内容题）＝槽位写「无台账命中」，不硬凑名",
        "——三段照抄上形：无台账命中｜未绑定｜窗未定（不加解释、不改写）",
    ):
        assert sentence in line
    # 头行仍为单行（段行单点判据不被换行破形）；样例旧形零删改（补句只插在无台账行说明句后）
    head_part, _, payload_json = line.partition('{"action"')
    assert head_part.endswith("（不加解释、不改写））：")
    assert "ledger_notes 逐字转抄台账全量块" in head_part
    json.loads('{"action"' + payload_json)


# ══════════════════════════════════════════════════════════════════════════════════════
# 分解样例补行（2026-10-17）：无台账命中形全样例行（样例面补全 ↔ 闸闭世界）
# ══════════════════════════════════════════════════════════════════════════════════════

# 无台账命中形全样例行逐字稿（照抄实现常量——逐字比对，防样例漂移）。
_NO_HIT_ROW_VERBATIM = (
    '{"action": "decompose", "question_group": {"subtasks": [{"id": "s1", '
    '"question": "〈报告内容类问题〉", "ledger_notes": "无台账命中｜未绑定｜窗未定", '
    '"chain": "knowledge", "tool": "doc_retrieve"}]}}'
)


def test_decompose_example_no_hit_full_row() -> None:
    """样例区补无台账命中形全样例行（行为 10；2026-10-17 补·L3 阻塞修复批·分解样例补行）。

    病根（真机 `run-b5b6b056`，`docs/runtime-refactor/ladder/L3/06`）：模型知道要写无命中形，但
    两轮都没凑齐三个闭世界段——r1「无台账命中——完井液密度属于完井工程报告事实」（段尾加解释→
    段数非三）、r2「无台账命中｜无绑定｜检索式无窗」（绑定态／窗段自造形越界）→ 三轮烧光（三条
    「ledger_notes 槽位对账未过：s1」＋`budget_converged`）。病根＝样例区只给锚定指标形全样例行，
    无命中形仅头行一句说明、没有三段位完整样例可照抄。
    断言：①全样例行随样例区在场（次行，逐字）＋三段位逐字；②头行补句逐字在场；③该行＝合法 JSON
    且五键齐全、三段位取值 ∈ 闸的闭世界（教的就是闸收的——闭世界成员面，防样例教越界形）。
    """
    package = _clarify_package(_decision_state())
    head_line = _unique_line(package, "填写样例（分解形")  # 段行单点（头＋首行 JSON 同行）
    # ①首行＝现造锚定指标形（旧形零删改）；次行＝无命中形全样例行（逐字、恰一条）
    assert head_line[head_line.index("{") :].startswith('{"action": "decompose"')
    assert head_line == render_decompose_example(
        _decision_dump()["metrics"], today=_DECISION_TODAY
    ).split("\n", 1)[0]
    tail_rows = [
        row for row in package.split("\n") if row.startswith('{"action": "decompose"')
    ]
    assert tail_rows == [_NO_HIT_ROW_VERBATIM]
    # ②头行补句逐字在场（三段位闭世界值直陈——不加解释、不改写）
    assert "——三段照抄上形：无台账命中｜未绑定｜窗未定（不加解释、不改写）" in head_line
    # ③样例行＝合法 JSON、五键齐全、三段位 ∈ 闸闭世界（样例教的即闸收的）
    obj = json.loads(_NO_HIT_ROW_VERBATIM)
    assert set(obj) == {"action", "question_group"}  # 顶层恰两键
    assert obj["action"] == "decompose"
    assert set(obj["question_group"]) == {"subtasks"}
    subtask = obj["question_group"]["subtasks"][0]
    assert set(subtask) == {"id", "question", "ledger_notes", "chain", "tool"}  # 五键齐全
    assert subtask["chain"] == "knowledge" and subtask["tool"] == "doc_retrieve"
    slot, binding, window = subtask["ledger_notes"].split("｜")  # 三段位次固定
    assert slot in NOTE_SLOT_LITERALS  # 无台账命中形 ∈ 槽位段合法集
    assert binding in BINDING_STATES  # 绑定态 ∈ 对账闭世界
    assert window in WINDOW_LITERALS  # 窗 ∈ 非锚定窗合法字面闭世界


def test_toolmatch_contract_carries_mention_mode() -> None:
    """工具匹配合同带必填结论字段 `mention_mode`（2026-10-16 补（L0/L2 三病灶修复批①））。

    真机形（`docs/runtime-refactor/ladder/L2/03`：35 次模型调用、32 条 `decision_rejected`
    notice 全为工具匹配拒，末条 notice＝recursion limit 35）＝闸把 `mention_mode` 当必填
    （`appv2/runtimev2/tool_matching/matching.py` 加密集，逐字拒文「matches s1 缺 mention_mode」
    ／「缺 matches」两形交替），而合同零提及该字段 → 模型无从遵守、必拒循环。断言：合同正文
    （matches 形＋字段说明）与填写样例两处都带该键，取值对照**闸的闭世界**逐字。
    """
    schema_match = '"mention_mode": "executed"|"mentioned_only"'
    assert schema_match in TOOLMATCH_EMISSION_CONTRACT
    assert "缺该键＝参数校验拒" in TOOLMATCH_EMISSION_CONTRACT  # 必填面逐字
    assert "不执行" in TOOLMATCH_EMISSION_CONTRACT  # 提及≠执行（防废弃口径误当执行）

    # 填写样例的 matches 支带该键，取值 ∈ 闸的闭世界（教的就是闸收的）
    sample_head = "填写样例（单匹配 knowledge 形）："
    sample_line = _unique_line(TOOLMATCH_EMISSION_CONTRACT, sample_head)
    sample = json.loads(sample_line[len(sample_head) :])
    match = sample["matches"][0]
    assert "mention_mode" in match
    assert match["mention_mode"] == "executed"  # 样例取名＝闸闭世界成员（教的就是闸收的）
    assert match["mention_mode"] in MENTION_MODES
    assert MENTION_MODES == {"executed", "mentioned_only"}  # 对照面非空转
    assert match["chain"] == "knowledge"  # 样例既有形零删改

    # 装配面逐字在场（匹配轮**规章段**内同现——合同常量入包不脱节；2026-10-17 H 批：
    # 规章段＝system 承载位 `toolmatch_system_contract`，动态段（user）不携合同件）
    package = _toolmatch_package(_decision_state())
    contract = toolmatch_system_contract()
    assert schema_match in contract
    assert sample_line in contract
    assert schema_match not in package and sample_line not in package


# ══════════════ H 批（2026-10-17）：system 承载位（角色分家）══════════════════════════

# 背景块逐字稿（真源＝`docs/runtime-refactor/proposals/H批-开票-system承载位.md` §5；逐字照抄）
_SYSTEM_BACKGROUND_VERBATIM = (
    "【系统背景】你是\"问一问\"——油田生产数据问答助手。你的作用：帮业务人员用一句话"
    "查到平台里的生产数据和报告结论，省去他们自己翻系统。你的原理：你不直接连库乱查——"
    "每个问题经过读题→澄清→选链→检索/查数→起草→核验六道工序，每步都有专门程序和规则"
    "约束，你只做规定环节的事。你的目的：每条答案有据，不确定就说不确定，宁可说没查到也"
    "不编。平台数据分两类：数据库实时汇总（权威）、报告库各篇报告（人写口径，性质不同）。"
)


def test_system_background_verbatim() -> None:
    """行 24（H 批）｜链首背景块＝族⑦常量、逐字稿照抄、字节稳定（唯一新文本）。"""
    assert SYSTEM_BACKGROUND == _SYSTEM_BACKGROUND_VERBATIM
    assert SYSTEM_BACKGROUND.startswith("【系统背景】")
    assert SYSTEM_BACKGROUND.endswith("（人写口径，性质不同）。")
    assert "作用：" in SYSTEM_BACKGROUND and "原理：" in SYSTEM_BACKGROUND
    assert "目的：" in SYSTEM_BACKGROUND
    # 单源：runtimev2 面内恰一处字面定义（消费方零副本）
    feature = "【系统背景】你是"
    assert _hits(_runtimev2_sources(), feature) == [_CONSTANTS_FILE.name]
    # 族⑦登记（常量族闭世界随批改）
    assert CONTRACT_CONSTANT_FAMILIES["system_background"] == ("SYSTEM_BACKGROUND",)


def test_system_contract_carriers_split_from_user_dynamic() -> None:
    """行 25（H 批）｜四环节**规章取件函数**（system 承载位）与 **user 动态段**分家逐环节在场。

    每环节两判：① 规章头在规章段（system 位）**在场**且**字节稳定**（同参两跑逐字相等）；
    ② 同一规章头在 user 动态段**零命中**（「只换承载位不换文本」——文本零改、角色分家）。
    """
    cases: tuple[tuple[str, str, str], ...] = (
        (
            "读题",
            understand_system_contract(),
            assemble_task_book(_ledger_state(), watermark="2026-08-24"),
        ),
        (
            "相位①",
            _clarify_contract(),
            _clarify_package(_decision_state()),
        ),
        (
            "相位②",
            toolmatch_system_contract(),
            _toolmatch_package(_decision_state()),
        ),
        (
            "作答",
            answer_system_contract(),
            assemble_answer_prompt(_answer_state()),
        ),
    )
    heads = {
        "读题": ("【场景】", TASK_BOOK_OUTPUT_CONTRACT),
        "相位①": (
            CLARIFY_PHASE_HEAD,
            "【相位①·业务澄清】只输出一个 JSON 对象（可围栏）。四动作：",
            CLARIFY_FINALIZE_BOUNDARY,
        ),
        "相位②": (TOOLMATCH_PHASE_HEAD, TOOLMATCH_EMISSION_CONTRACT),
        "作答": (
            "【答案要求】",
            ANSWER_REQUIREMENTS,
            JARGON_PLAIN_GLOSSARY,
            SUMMARY_CONTRACT,
            ANSWER_DRAFT_CONTRACT,
        ),
    }
    for label, contract, dynamic in cases:
        assert contract == contract, label  # ① 字节稳定（同参两跑同源）
        for marker in heads[label]:
            assert marker in contract, (label, marker[:16])
            assert marker not in dynamic, (label, marker[:16])
    # 动态段各自照旧在场（分家不删件）
    clarify = cases[1][2]
    assert anchor_line(
        _decision_state().question, _decision_state().understanding
    ) in clarify
    assert GUIDE_REFERENCE_HEAD in clarify and RESIDENT_BLOCK_BEGIN in clarify
    answer_dynamic = cases[3][2]
    assert f"用户问题：{_answer_state().question}" in answer_dynamic
    assert "子问题结果清单：" in answer_dynamic

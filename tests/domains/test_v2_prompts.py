"""prompts 块验收（RT-W2-04a——骨架＋合同常量族＋任务书装配＋答案轮装配）。

票面对象＝`specs/prompts.md`「验收测试」表第 1–8、16–18 行（-a 逐字，测试标识同规格列）；
测试网钉＝pin-24（落点行 1：合同常量逐字稳定面）／pin-03（落点行 2：答案要求③逐字在场）／
pin-13（落点行 18：答案轮禁令件在场＝合同侧）。

逐字稿真源（迁移照抄面）：`appv2/runtime/orientation.py` `_ORIENT_*`／`_ANSWER_REQUIREMENTS`
／`answer_turn_preamble`、`appv2/runtime/guide.py` 三合同、`appv2/runtime/graph.py`
`_ANSWER_INSTRUCTION`（族⑤去重后形态——流水 43①）。

**已登记张力（本件如实标注，不静默）**：族①成员 `TASK_BOOK_EXAMPLES`＝V1 Owner 审定三则样例
逐字迁移，其示例文内含实仓台账真源词（如「抽油机时率」「躺井」「Y-41」）；行为 11 的「示例词
纪律同款」（`arch/P4b` A-P4b-60 先例）若按实仓台账词集解释，本常量需改写三则样例——本票无逐字稿，
不自行裁量，登记待主窗裁决。本件行 16 的扫描词集＝本文件 fixture 投影的台账词集＋井号形＋
水位日形（规格 行为 11 判据面原文「fixture 词集与水位日形交集＝∅」）。
"""

from __future__ import annotations

import ast
import re
import string
from importlib import import_module
from pathlib import Path
from typing import Any

from appv2.runtimev2.prompts import (
    ANSWER_DRAFT_CONTRACT,
    ANSWER_REQUIREMENTS,
    ASSEMBLY_FUNCTIONS,
    CLARIFY_EMISSION_CONTRACT,
    CONTRACT_CONSTANT_FAMILIES,
    SUMMARY_CONTRACT,
    TASK_BOOK_EXAMPLES,
    TASK_BOOK_OUTPUT_CONTRACT,
    TASK_BOOK_REDLINE,
    TASK_BOOK_SCENE,
    TASK_BOOK_TASK,
    TOOLMATCH_EMISSION_CONTRACT,
    assemble_answer_prompt,
    assemble_task_book,
)
from appv2.runtimev2.prompts import constants as constants_module
from appv2.runtimev2.state import RunState

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

"""V2-124 核验面可核对象与推断去处（S7＋S8）验收。

票面＝`tickets/v2/V2-124-核验面可核对象与推断去处.md`（含「Kimi 评审修正」节）；依据＝
`eval/suite-147/results/EB11-臆造上下文归因.md` E8／E9（核验面只认数值记号与引标源——定义式／
推断句全票放行）。两处逐字稿（票面 §逐字稿——照抄，零改写）＋承载位：

- **【定义等式可核】→ 核验侧结构式判据**：`citation_chunks` 为空 ∧ `normalize_for_match`（NFKC，
  `＝`→`=`）后含 **ASCII `=`** ⇒ 该行＝无据断言（标红交 V2-115 回炉）。判据单点＝
  `rules.definition_equation_line`（记号单点＝`constants.EQUATION_MARK`）；**禁 CJK 字面判据**
  （Kimi 评审修正 1——零词表 AST 闸
  `test_v2_verification.py::no_lexicon_or_regex_in_verification` 会咬）；**不新增
  `RewriteRecord.reason` 值**（Kimi 评审修正 4——闭世界仍两值，走既有 `no_material`）。
- **【推断去处】→ 提示词侧**：落 `ANSWER_DRAFT_CONTRACT`（族⑤）**段尾追加**（与 V2-101／V2-121
  同改本常量 ⇒ 三票串行 101→121→124 且 diff 只许追加——V2-101 置换段首、V2-121 追加中段、本票
  追加段尾）；**不得落核验侧**（Kimi 评审修正 2——落核验侧必破零词表闸）。

档位纪律（票面任务 3）：标红走 `repair` 档；`observe` 档只记录（`intended_rewrites`）；
`delete` 档照旧删句（conftest 已 pin `VERIFY_ACTION=delete`，档位用例在本例内显式覆盖）。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

import appv2.runtimev2.verification as verification
from appv2.runtimev2.orchestration.constants import PAYLOAD_REPAIR_REQUEST_KEY
from appv2.runtimev2.prompts import (
    ANSWER_DRAFT_CONTRACT,
    answer_system_contract,
)
from appv2.runtimev2.state import INTENT_REPAIR, RunState
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.verification import (
    NOTICE_UNSUPPORTED_CLAIM,
    PAYLOAD_INTENDED_REWRITES_KEY,
    PAYLOAD_REWRITES_KEY,
    PAYLOAD_VERIFY_MODE_KEY,
    REWRITE_CONFLICT,
    REWRITE_NO_MATERIAL,
    VERIFY_ACTION_ENV,
    VERIFY_MODE_OBSERVE,
    VERIFY_MODE_REPAIR,
    detect_intended,
    verify,
)
from appv2.runtimev2.verification import constants as verification_constants
from appv2.runtimev2.verification import rules as verification_rules
from tests.domains.test_v2_v2115_repair import (
    _MODEL_CALLER,
    _repair_payloads,
    _rewrite_reply,
    _ring,
)
from tests.domains.test_v2_verification import (
    _has_cjk,
    _lexicon_violations,
    _notice_types,
    _obs,
    _state,
    _step_payload,
)

# ---------- 逐字稿（票面 §逐字稿——照抄，零改写） ----------

_DEFINITION_EQUATION_VERBATIM = (
    "【定义等式可核】凡「X＝…」式定义/算法句，材料中无对应登记即为无据，须标红回炉。"
)
_INFERENCE_PLACE_VERBATIM = (
    "【推断去处】推断句须写明推断依据与不确定性（「据此推断」「若…则」），不得作为事实断言陈述。"
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VERIFICATION_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "verification"
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
_VERIFICATION_SPEC = _REPO_ROOT / "specs" / "verification.md"

# V2-101 置换后的段首第 1 句（同常量三票串行——本票零改面）。
_V101_FIRST_SENTENCE = (
    "缺位只锚本轮材料：写「本次材料未覆盖」，不得写「报告/资料库未载」或「没有任何一条材料提及」。"
)
# V2-121 追加的术语级出口（同常量中段——本票零改面）。
_V121_TERM_EXIT_HEAD = "【术语级缺位出口】"

# ---------- 形（EB11 §一-1 `Q45` `run-9d726969`；§一-7 `NQ-M1` `run-15cb1acc`） ----------

# `Q45` 形定义等式：**无引标辖域**（材料中无对应登记）∧ 含全角「＝」（NFKC 归一为 ASCII `=`）。
_Q45_DEFINITION_LINE = (
    "「措施增油达标」＝（措施后实际产量 − 递减基线产油）≥ 措施设计目标，"
    "且措施有效率口径判定为有效。"
)
# `Q45` 形材料近邻（同族兼容的另一条口径——旧判据面下它是「结构承载行」而全票放行）。
_Q45_NEAR_NEIGHBOR = "递减增油口径提示：按台账口径（递减增油＝阶段产油量较递减基准的增产量）统计。"
# 术语级缺位出口规定的合法形（回炉重写面——无引标、无计量数值、无等号 ⇒ 复检可过）。
_Q45_ABSENCE_LINE = "材料中未见该表述，无法给出其口径。"
# `NQ-M1` 形推断句：无引标、无计量数值、无等号 ⇒ 结构承载行（不因「无据」直接删句）。
_NQ_M1_INFERENCE_LINE = (
    "按已有材料推断，2027 年 1 月渤中34-8 油田当月躺井涉及的三口井可能为 Y-21、Y-23、Y-25。"
)


def _runtimev2_sources() -> list[tuple[Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in sorted(_V2_DIR.rglob("*.py"))
    ]


def _literal_holders(feature: str) -> list[str]:
    """`feature` 在 runtimev2 面内以**字面量**出现的文件清单（单源判据面——AST `Constant`）。"""
    holders: list[str] = []
    for path, text in _runtimev2_sources():
        tree = ast.parse(text)
        if any(
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and feature in node.value
            for node in ast.walk(tree)
        ):
            holders.append(path.name)
    return sorted(holders)


# ---------- 1 定义等式：逐字稿载体＋结构式判据（禁 CJK 字面） ----------


def test_definition_equation_verbatim_carrier_and_structural_criterion() -> None:
    """验收①前置｜【定义等式可核】逐字稿照抄（票面 §逐字稿）、载体＝`specs/verification.md`
    行为 16 逐字在场（AGENTS 6b——票面两行逐字稿各须有载体）；判据＝**结构式**：无引标辖域 ∧
    归一形含 ASCII 等号（全角「＝」经 NFKC 归一）——**零 CJK 字面判据**、不触零词表 AST 闸。
    """
    # ① 逐字稿照抄（票面 §逐字稿，零改写）
    assert _DEFINITION_EQUATION_VERBATIM == (
        "【定义等式可核】凡「X＝…」式定义/算法句，材料中无对应登记即为无据，须标红回炉。"
    )
    assert _DEFINITION_EQUATION_VERBATIM.startswith("【定义等式可核】")
    assert _DEFINITION_EQUATION_VERBATIM.endswith("须标红回炉。")
    # ② 载体：规格行为 16 逐字恰一份（本行即票面第一行逐字稿的施工载体）
    spec = _VERIFICATION_SPEC.read_text(encoding="utf-8")
    assert spec.count(_DEFINITION_EQUATION_VERBATIM) == 1

    # ③ 判据＝结构式（Kimi 评审修正 1）：`citation_chunks` 为空 ∧ 归一形含 ASCII `=`
    assert verification_constants.EQUATION_MARK == "="
    assert verification_constants.EQUATION_MARK.isascii()
    assert verification_rules.definition_equation_line(_Q45_DEFINITION_LINE) is True
    assert verification_rules.definition_equation_line("产量＝21.16 吨") is True  # 全角「＝」归一
    assert verification_rules.definition_equation_line("产量=21.16 吨") is True  # ASCII 等号
    assert verification_rules.definition_equation_line("该井日产油量为 21.16 吨[1]。") is False
    assert verification_rules.definition_equation_line("该井日产油量为 21.16 吨。") is False

    # ④ 判据零 CJK 字面（禁 CJK 字面判据）＋零词表 AST 闸不咬（判据本体落 `rules.py`）
    tree = ast.parse((_VERIFICATION_DIR / "rules.py").read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "definition_equation_line"
    )
    # 函数体首个字符串常量＝docstring（说明面，非判据面——按节点身份排除）
    doc_node = (
        function.body[0].value
        if function.body
        and isinstance(function.body[0], ast.Expr)
        and isinstance(function.body[0].value, ast.Constant)
        else None
    )
    literals = [
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node is not doc_node
    ]
    assert all(not _has_cjk(text) for text in literals)  # 判据面零 CJK 字面
    # 等号取**单点常量**（非就地字面——记号单点纪律）
    assert "EQUATION_MARK" in ast.unparse(function)
    assert _lexicon_violations(tree) == []
    # 旧判据面下本行是「结构承载行」（无引标、无计量数值）——即本票要补的可核对象缺口
    normalized = verification_rules.normalize_for_match(_Q45_DEFINITION_LINE)
    assert verification_rules.citation_chunks(normalized) == []
    assert verification_rules.number_tokens(normalized) == ()


# ---------- 2 `Q45` 形：`observe` 档记录「本应回炉」／`delete` 档照旧删句 ----------


def _q45_state() -> RunState:
    return _state(
        question="生产动态里写「措施增油达标」，这个达标是按啥口径算的？",
        draft="\n".join(["一、口径", _Q45_DEFINITION_LINE]),
        observations=[_obs(1, "fragment", content=_Q45_NEAR_NEIGHBOR, source="月报")],
    )


def test_q45_shape_definition_equation_recorded_in_observe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验收①前半｜`observe` 档：定义等式检出项**只记录不删**（交付＝草稿逐字）——
    `intended_rewrites` 逐条含原句与 `reason`（既有 `no_material`，闭世界不新增值）＋
    `Verdict.ok=False`（＝「本应回炉」；行为 9／14）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_OBSERVE)
    state = _q45_state()
    draft = state.draft or ""
    verdict = verify(state, bus=EventBus())

    assert state.draft == draft  # 交付面零加工：逐字等于草稿
    payload = _step_payload(state)
    assert payload[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_OBSERVE
    assert payload[PAYLOAD_INTENDED_REWRITES_KEY] == [
        {"line": _Q45_DEFINITION_LINE, "reason": REWRITE_NO_MATERIAL}
    ]
    assert verdict.rewritten == 1
    assert verdict.ok is False  # 检出即「无据断言残留」在位（本应回炉）
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    notices = [
        entry for entry in state.notices if entry.get("type") == NOTICE_UNSUPPORTED_CLAIM
    ]
    assert notices and "只记录不删" in str(notices[0].get("content"))


def test_q45_shape_definition_equation_deleted_in_delete_mode() -> None:
    """票面任务 3｜`delete` 档照旧：定义等式＝无据断言**整行离场**（行为 3 删句族）＋
    `RewriteRecord.reason="no_material"` 留痕（不新增第 4 值）——conftest 缺省档即 `delete`。"""
    state = _q45_state()
    verdict = verify(state, bus=EventBus())

    assert state.draft.splitlines() == ["一、口径"]
    assert _Q45_DEFINITION_LINE not in state.draft
    assert verdict.rewritten == 1 and verdict.ok is False
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert [entry["line"] for entry in rewrites] == [_Q45_DEFINITION_LINE]
    assert {entry["reason"] for entry in rewrites} == {REWRITE_NO_MATERIAL}


def test_cited_definition_equation_not_flagged_by_structural_criterion() -> None:
    """判据边界｜**有引标辖域**的行不属本判据面（Kimi 评审修正 1 的结构式两半之一）：
    同一「＝」形挂上可解析引标即按既有支撑判定走——不误伤有据行。"""
    observations = [
        _obs(1, "fragment", content="台账口径说明：递减增油按阶段产油量计。", source="月报")
    ]
    line = "递减增油＝阶段产油量较递减基准的增产量[1]。"
    state = _state(draft=line, observations=observations)
    verdict = verify(state, bus=EventBus())

    assert state.draft == line
    assert verdict.rewritten == 0 and verdict.ok is True
    assert verdict.cited == [1]


# ---------- 3 `Q45` 形：`repair` 档标红 → 回炉重写（V2-115 环，端到端） ----------


def test_q45_shape_definition_equation_routes_and_repairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验收①后半｜`repair` 档：定义等式检出即**只标红不删**＋意图转 `INTENT_REPAIR`（回炉口）；
    回炉环（脚本化 completer）把它重写成术语级缺位句后**复检通过**——交付面零「＝」判定式。

    回炉面（LLM 改写）归编排侧 V2-115（本块零 LLM 红线不破）；本用例走既有 `_ring` 环
    （`verify → run_repair → verify` 同一 `_verify_lines` 判据单点）。
    """
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    state = _state(
        question="生产动态里写「措施增油达标」，这个达标是按啥口径算的？",
        draft=_Q45_DEFINITION_LINE,
        observations=[_obs(1, "fragment", content=_Q45_NEAR_NEIGHBOR, source="月报")],
    )
    # 标红面：`repair` 档只检测与标红（交付＝草稿逐字、不删）
    verify(state, bus=EventBus())
    assert state.draft == _Q45_DEFINITION_LINE
    assert state.next_intent == INTENT_REPAIR
    assert _step_payload(state)[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_REPAIR
    assert _step_payload(state)[PAYLOAD_INTENDED_REWRITES_KEY] == [
        {"line": _Q45_DEFINITION_LINE, "reason": REWRITE_NO_MATERIAL}
    ]

    # 回炉重写面（同一 `_verify_lines` 复检单点）：重写成缺位句 ⇒ 复检通过
    state = _state(
        question="生产动态里写「措施增油达标」，这个达标是按啥口径算的？",
        draft=_Q45_DEFINITION_LINE,
        observations=[_obs(1, "fragment", content=_Q45_NEAR_NEIGHBOR, source="月报")],
    )
    completer = _ring(state, [_rewrite_reply(1, _Q45_ABSENCE_LINE)])

    assert completer.calls and completer.calls[0][0] == _MODEL_CALLER  # V2-125：回炉自有桶
    assert state.draft == _Q45_ABSENCE_LINE
    assert "＝" not in state.draft and "=" not in state.draft
    assert state.next_intent != INTENT_REPAIR
    assert state.repair_rounds == 1
    assert state.verdict is not None and state.verdict["ok"] is True
    repairs = _repair_payloads(state)
    assert repairs[0][PAYLOAD_REPAIR_REQUEST_KEY]["lines"] == [_Q45_DEFINITION_LINE]


# ---------- 4 `NQ-M1` 形推断句：有去处、不被判无据删 ----------


def test_nq_m1_inference_line_not_deleted_and_has_place() -> None:
    """验收②｜`NQ-M1` 形推断句**不被判无据删**（票面任务 2「不因「无据」直接删句」）：无引标、
    无计量数值、无等号 ⇒ 结构承载行原样保留、零改写；其**去处**＝提示词侧【推断去处】合同
    （须标注推断依据与不确定性、不得作事实断言）——两半同测。"""
    draft = "\n".join(["一、结论", _NQ_M1_INFERENCE_LINE])
    state = _state(
        question="2027 年 1 月渤中34-8 油田当月躺井涉及哪三口井？",
        draft=draft,
        observations=[_obs(1, "fragment", content=_Q45_NEAR_NEIGHBOR, source="月报")],
    )
    verdict = verify(state, bus=EventBus())

    # 不被判无据删（零改写、整行原样在场）
    assert _NQ_M1_INFERENCE_LINE in state.draft
    assert state.draft == draft
    assert verdict.rewritten == 0 and verdict.ok is True
    assert detect_intended(state) == []
    # 判据面（三面皆不咬——结构承载行）
    normalized = verification_rules.normalize_for_match(_NQ_M1_INFERENCE_LINE)
    assert verification_rules.citation_chunks(normalized) == []
    assert verification_rules.number_tokens(normalized) == ()
    assert verification_rules.definition_equation_line(_NQ_M1_INFERENCE_LINE) is False

    # 去处＝提示词侧合同（逐字稿照抄、段尾追加、随作答规章段恰一份、单源）
    assert _INFERENCE_PLACE_VERBATIM == (
        "【推断去处】推断句须写明推断依据与不确定性（「据此推断」「若…则」），不得作为事实断言陈述。"
    )
    assert ANSWER_DRAFT_CONTRACT.endswith(_INFERENCE_PLACE_VERBATIM)  # 段尾追加（本票追加位）
    assert ANSWER_DRAFT_CONTRACT.count(_INFERENCE_PLACE_VERBATIM) == 1
    assert ANSWER_DRAFT_CONTRACT.startswith(_V101_FIRST_SENTENCE)  # V2-101 段首置换面零改
    assert _V121_TERM_EXIT_HEAD in ANSWER_DRAFT_CONTRACT  # V2-121 中段追加面零改
    contract = answer_system_contract()
    assert contract.count(_INFERENCE_PLACE_VERBATIM) == 1
    assert contract.endswith(ANSWER_DRAFT_CONTRACT)
    assert _literal_holders(_INFERENCE_PLACE_VERBATIM) == ["constants.py"]
    # 不得落核验侧（Kimi 评审修正 2：落核验侧必破零词表闸）
    assert _INFERENCE_PLACE_VERBATIM not in (
        _VERIFICATION_DIR / "rules.py"
    ).read_text(encoding="utf-8")
    assert _INFERENCE_PLACE_VERBATIM not in (
        _VERIFICATION_DIR / "core.py"
    ).read_text(encoding="utf-8")


# ---------- 5 闭世界两值（验收③） ----------


def test_rewrite_reasons_closed_world_still_two_values() -> None:
    """验收③｜`REWRITE_REASONS` 闭世界**仍两值**（Kimi 评审修正 4）：定义等式走既有
    `no_material`，不新增第 4 值。"""
    assert verification.REWRITE_REASONS == {REWRITE_NO_MATERIAL, REWRITE_CONFLICT}
    assert len(verification.REWRITE_REASONS) == 2
    assert all(value.isascii() for value in verification.REWRITE_REASONS)

    state = _q45_state()
    verify(state, bus=EventBus())
    payload = _step_payload(state)
    reasons: set[Any] = {entry["reason"] for entry in payload[PAYLOAD_REWRITES_KEY]}
    assert reasons == {REWRITE_NO_MATERIAL}
    assert reasons <= verification.REWRITE_REASONS
    intended = {entry["reason"] for entry in payload[PAYLOAD_INTENDED_REWRITES_KEY]}
    assert intended <= verification.REWRITE_REASONS

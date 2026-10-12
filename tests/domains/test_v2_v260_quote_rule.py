"""V2-60 发射引号治理——引号规矩合同＋确定性引号自修测试（票面附 D T1–T4）。

设计宪法对齐：引号修复＝纯字符格式处理（零语义零模型），修后必须过标准
json.loads 才受理；修不好原路走既有 V2-57 定位回喂。P-039 命名闸由既有
test_v2_p039_contract_and_name_gate.py 继续看守（T4——全量套件即证）。
"""

from __future__ import annotations

from appv2.runtime.graph import _parse_with_quote_repair
from appv2.runtime.guide import CLARIFY_CONTRACT, TOOLMATCH_CONTRACT
from appv2.runtime.subtask import parse_question_group, repair_inner_quotes


def test_contract_quote_rule_present() -> None:  # T1
    for contract in (CLARIFY_CONTRACT, TOOLMATCH_CONTRACT):
        assert "禁止写不转义的英文双引号" in contract
        assert "值内裸引号，非法" in contract
        assert "值内中文引号，合法" in contract


def test_repair_inner_quotes_four_shapes() -> None:  # T2
    broken = '{"a": "1.3 节关于"杆柱"的算式", "b": 1}'
    assert repair_inner_quotes(broken) == '{"a": "1.3 节关于「杆柱」的算式", "b": 1}'
    assert repair_inner_quotes('{"a": "正常"}') is None  # 无病不修
    assert repair_inner_quotes('{"a": "x"') is None  # 坏括号＝结构伤，引号修不了
    assert repair_inner_quotes('{"a": "带\\"转义\\"的"}') is None  # 合法转义不误伤


def test_parse_wrapper_repairs_and_flags() -> None:  # T3
    broken = (
        '{"action": "decompose", "question_group": {"subtasks": '
        '[{"id": "s1", "question": "1.3 节关于"杆柱"的算式", '
        '"ledger_notes": "示例指标｜未绑定｜2026-08-01~2026-08-31", '
        '"chain": "knowledge", "tool": "doc_retrieve"}]}}'
    )
    parsed, repaired = _parse_with_quote_repair(
        lambda c: parse_question_group(
            c, max_discovers=2, discover_budget_left=10
        ),
        broken,
    )
    assert repaired is True
    assert not isinstance(parsed, str)  # 修后受理（QuestionGroup）


def test_parse_wrapper_unrepairable_keeps_rejection() -> None:  # T4
    broken = '{"action": "decompose", "question_group": {'  # 结构伤——截断
    result, repaired = _parse_with_quote_repair(
        lambda c: parse_question_group(
            c, max_discovers=2, discover_budget_left=10
        ),
        broken,
    )
    assert repaired is False
    assert isinstance(result, str)  # 既有定位回喂路径零改动

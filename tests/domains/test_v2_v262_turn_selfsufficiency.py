"""V2-62 轮次任务自足性治理——三件套/锚行/样例/观察字段测试（票面附 F T1–T6）。

设计宪法：语义归模型，程序管装配——本票零约束闸（回声与粘贴只记不拦）。
P-039 命名闸由既有 test_v2_p039_contract_and_name_gate.py 继续看守（全量套件即证）。
"""

from __future__ import annotations

from appv2.runtime.guide import TOOLMATCH_CONTRACT
from appv2.runtime.orientation import (
    anchor_line,
    answer_turn_preamble,
    assemble_answer_instruction,
    echo_signature_hit,
    paste_ratio,
)

# ---------- T1/T2 答案轮三件套置顶 ----------


def test_answer_instruction_three_piece_first() -> None:  # T1
    text = assemble_answer_instruction(
        question="问 W-21 检泵周期。",
        summary_contract="【相位④·汇总】合同原文占位",
        subtask_list="- [s1] 子问题一",
        answer_instruction="起草答案：逐条事实断言必须带 [n] 引标。",
    )
    assert text.startswith("用户问题：问 W-21 检泵周期。\n现在：写最终答案交付用户。")
    assert "不再做任何决策、不再发射任何动作指令" in text
    assert "如实转述进对应子问题条目" in text  # 转述义务（数-降跷跷板治面）
    assert "禁整段照搬原文充当回答" in text
    assert "「理解：／指标候选：」及任何动作 JSON 是过程产物" in text
    # 既有字面依次在后、零删改
    assert text.index("【答案要求】") < text.index("【相位④·汇总】合同原文占位")
    assert text.index("子问题结果清单") < text.index("起草答案：逐条事实断言必须带 [n] 引标")


def test_answer_preamble_legacy_shape() -> None:  # T2
    text = answer_turn_preamble("问产量。") + "\n" + "起草答案合同"
    assert text.startswith("用户问题：问产量。")
    assert text.endswith("起草答案合同")


# ---------- T3 题意锚行 ----------


def test_anchor_line_two_shapes() -> None:  # T3
    assert anchor_line("问产量。", "问去年日产油。") == "用户原题：问产量。｜题意：问去年日产油。"
    assert anchor_line("问产量。") == "用户原题：问产量。"


# ---------- T4 定案轮填写样例 ----------


def test_toolmatch_filled_example() -> None:  # T4
    assert "填写样例（单匹配 knowledge 形）" in TOOLMATCH_CONTRACT
    assert "杆柱" in TOOLMATCH_CONTRACT
    assert '"retrieval_need": {"question": "1.3 节关于杆柱的算式具体是什么"' in TOOLMATCH_CONTRACT


# ---------- T5/T6 观察字段（只记不拦） ----------


def test_echo_signature_two_states() -> None:  # T5
    assert echo_signature_hit("理解：问去年日产油。\n指标候选：日产油量")
    assert echo_signature_hit("前言指标候选出现在前百字内" + "x" * 90)
    assert not echo_signature_hit("①五项时率损失分别为：躺井停产损失占 1.1 个百分点……")


def test_paste_ratio_two_states() -> None:  # T6
    content = "一" * 200
    obs = [{"content": content}]
    assert paste_ratio("一" * 80, obs) > 0  # 60 字窗口重合在场
    assert paste_ratio("完全不同的回答正文，没有任何逐字重合。", obs) == 0.0
    assert paste_ratio("", obs) == 0.0

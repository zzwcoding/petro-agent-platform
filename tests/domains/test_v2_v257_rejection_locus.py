"""V2-57 拒因带定位钉测（错误原样回喂统一纪律——附 E TDD 先红后绿）。

票面附 E 钉测落点：
- T1 工具匹配少右括号 JSON → 拒因含「JSON 语法错误」「约第 N 字符」
  「坏点附近原文」且片段含真实坏点邻域（已知坏例罐头＝合法罐头摘除末个右方
  括号——取证实跑同形：括号平衡块仍在、json 语法已坏）；
- T2 澄清发射解析失败 → 同上三要素在场；
- T3 决策解析失败 → 同上；
- T4 输出无花括号 → 拒因含「没有任何以左花括号起始」提示；
- T5 合法 JSON → 解析成功零拒因（回放路径不误触）；
- T6 toolmatch 回喂行：decision_error 非空时指令尾含「上次发射被拒：…」；
  首发（空）不含；
- T7 源码对账钉：三处旧裸笼统话 return 不复存在（扫描源码断言——防修三漏一）；
- T8 既有回喂零回归（BAD_ARGS 精确拒因回喂、clarify 回喂行）：由既有测试
  全绿即证（test_v2_react_loop.test_rejection_feedback_redecision_no_repair、
  test_unparsable_decision_feedback、test_v2_multi_turn_context 上次决策被拒
  断言等）——本文件零新增断言、既有断言零删改。
"""

from __future__ import annotations

import json
from pathlib import Path

from appv2.runtime import AskRequest, parse_decision
from appv2.runtime.subtask import (
    QuestionGroup,
    parse_question_group,
    parse_tool_match,
)
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import (
    _E2E_QUESTION,
    _SUMMARY_DRAFT,
    CLARIFY_GROUP_DATA_KNOWLEDGE,
    LEDGER_DUMP,
    TOOLMATCH_TWO,
    UNDERSTAND_MULTI,
)
from tests.domains.test_v2_react_loop import (
    DECISION_DISCOVER,
    _fragment_obs,
    _retrieval_with,
    _rows_outcome,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _drop_last_rbracket(text: str) -> str:
    """已知坏例罐头（取证同形——少一个右方括号）：合法罐头摘除末个「]」。

    摘后花括号仍平衡（平衡块扫描照常圈出片段）而 JSON 语法已坏——正是
    json.JSONDecodeError 自带定位、而 extract_plan_json 判 None 的形态。
    """
    idx = text.rfind("]")
    assert idx >= 0, "罐头必须含右方括号"
    return text[:idx] + text[idx + 1 :]


def _expected_locus(content: str) -> tuple[str, int, str]:
    """定位预言机（标准库独立复算）：重放平衡块扫描取异常 msg/绝对位置/邻域片段。"""
    start = content.find("{")
    assert start >= 0
    depth = 0
    for position in range(start, len(content)):
        ch = content[position]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                segment = content[start : position + 1]
                try:
                    json.loads(segment)
                except json.JSONDecodeError as exc:
                    bad = start + exc.pos
                    return exc.msg, bad, content[max(0, bad - 40) : bad + 40]
    raise AssertionError("罐头必须产出可定位的 JSON 异常（平衡块内语法坏）")


def _assert_locus_three_elements(reason: str, bad_content: str) -> None:
    """三要素在场断言（T1/T2/T3 共用）：语法错误名＋约第 N 字符＋坏点邻域片段。"""
    msg, bad, snippet = _expected_locus(bad_content)
    assert "JSON 语法错误" in reason
    assert f"JSON 语法错误：{msg}" in reason
    assert f"约第 {bad} 字符" in reason
    assert "坏点附近原文" in reason
    assert f"「{snippet}」" in reason


# ---------- T1：工具匹配少右括号 → 拒因带定位 ----------


def test_t1_toolmatch_rejection_carries_locus() -> None:
    group = parse_question_group(CLARIFY_GROUP_DATA_KNOWLEDGE)
    assert isinstance(group.group, QuestionGroup)
    bad = _drop_last_rbracket(TOOLMATCH_TWO)
    reason = parse_tool_match(bad, group.group)
    assert isinstance(reason, str)
    assert reason.startswith("工具匹配不可解析——只输出一个 JSON")  # fallback 前缀保留
    _assert_locus_three_elements(reason, bad)


# ---------- T2：澄清发射解析失败 → 拒因带定位 ----------


def test_t2_clarify_rejection_carries_locus() -> None:
    bad = _drop_last_rbracket(CLARIFY_GROUP_DATA_KNOWLEDGE)
    reason = parse_question_group(bad)
    assert isinstance(reason, str)
    assert reason.startswith("澄清发射不可解析——只输出一个 JSON")  # fallback 前缀保留
    _assert_locus_three_elements(reason, bad)


# ---------- T3：决策解析失败 → 拒因带定位 ----------


def test_t3_decision_rejection_carries_locus() -> None:
    bad = _drop_last_rbracket(DECISION_DISCOVER)
    reason = parse_decision(bad)
    assert isinstance(reason, str)
    assert reason.startswith("决策不可解析——只输出一个 JSON 决策")  # fallback 前缀保留
    _assert_locus_three_elements(reason, bad)


# ---------- T4：输出无花括号 → 无 JSON 外壳提示 ----------


def test_t4_no_brace_output_gets_shell_hint() -> None:
    prose = "抱歉，我无法输出该决策。"
    group = parse_question_group(CLARIFY_GROUP_DATA_KNOWLEDGE)
    assert isinstance(group.group, QuestionGroup)
    reasons = [
        parse_decision(prose),
        parse_question_group(prose),
        parse_tool_match(prose, group.group),
    ]
    for reason in reasons:
        assert isinstance(reason, str)
        assert "没有任何以左花括号起始" in reason
        assert "检查是否漏了 JSON 外壳" in reason


# ---------- T5：合法 JSON → 解析成功零拒因（回放路径不误触） ----------


def test_t5_valid_json_parses_clean() -> None:
    group = parse_question_group(CLARIFY_GROUP_DATA_KNOWLEDGE)
    assert not isinstance(group, str)
    matches = parse_tool_match(TOOLMATCH_TWO, group.group)
    assert not isinstance(matches, str)
    emission = parse_decision(DECISION_DISCOVER)
    assert not isinstance(emission, str)


# ---------- T6：toolmatch 回喂行（decision_error 非空 → 指令尾回喂；首发不含） ----------


async def test_t6_toolmatch_feedback_line(tmp_path: Path) -> None:
    bad_toolmatch = _drop_last_rbracket(TOOLMATCH_TWO)
    script: dict[str, list[str]] = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [
            CLARIFY_GROUP_DATA_KNOWLEDGE,
            bad_toolmatch,
            TOOLMATCH_TWO,
        ],
        "v2.runtime.answer": [_SUMMARY_DRAFT],
    }
    retrieval = _retrieval_with(
        _fragment_obs("W-111 井采用酸压完井，投产初期日产油 291 方。", "frag-w111-1")
    )
    runtime, completer, db = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script=script,
        four_phase=True,
        ledger_dump=lambda: dict(LEDGER_DUMP),
        retrieval=retrieval,
    )
    try:
        handle = await runtime.ask(AskRequest(question=_E2E_QUESTION, actor=ACTOR))
        events = await drain(handle)
        assert events[-2].data["status"] == "completed"  # 拒一次后重发定案收口
        calls = completer.messages_of("v2.runtime.decision")
        assert len(calls) == 3  # clarify ＋ toolmatch 首发 ＋ toolmatch 重发
        first_tm = str(calls[1][-1]["content"])
        retry_tm = str(calls[2][-1]["content"])
        assert "上次发射被拒" not in first_tm  # 首发空不含
        assert "上次发射被拒" in retry_tm  # 回喂行在场
        assert "工具匹配不可解析" in retry_tm  # fallback 前缀随回喂行
        assert "JSON 语法错误" in retry_tm  # 定位随回喂行进指令（V2-57 主治）
        assert "修正后重新输出 JSON" in retry_tm  # 与 clarify 节点同款形式
    finally:
        await db.dispose()


# ---------- T7：源码对账钉（三处旧裸笼统话 return 不复存在——防修三漏一） ----------


def test_t7_no_bare_unparsable_returns_in_source() -> None:
    subtask_src = (REPO_ROOT / "appv2/runtime/subtask.py").read_text(encoding="utf-8")
    graph_src = (REPO_ROOT / "appv2/runtime/graph.py").read_text(encoding="utf-8")
    for src in (subtask_src, graph_src):
        assert "（未产出 JSON 对象）" not in src  # 旧裸笼统话零存留
    assert subtask_src.count("json_syntax_feedback(content,") == 2  # 澄清＋工具匹配
    assert graph_src.count("json_syntax_feedback(content,") == 1  # 决策
    assert "上次发射被拒" in graph_src  # toolmatch 回喂补线在场

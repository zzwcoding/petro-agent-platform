"""V2-09 宽容解析验收——understand/plan 应答解析三形态钉测＋真非法产拒答链。

票面（tickets/v2/V2-09-真模型格式校准.md 验收③）：
- 宽容解析单测：合法 JSON 裸产/围栏产/两行产三形态都解析成功；
- 真非法产走拒答链（不崩、不编造——plan 宽容解析两轮失败→plan_unparsable
  如实收敛）。

背景（P-008 偏差 5/R14 冒烟实测）：真 MiniMax 对 understand 两行合同格式
（「理解：／指标候选：」）遵循度不足——解析侧宽容化后，两行产照旧、裸 JSON
产/围栏 JSON 产降级可解（围栏容错承计划侧 JSON 子串提取器）；真非法产
（既非两行也非合法 JSON）不得误解析，照走 repair→拒答链。
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from appv2.runtime import (
    AskRequest,
    RunEvent,
    RunStore,
)
from appv2.runtime.graph import (
    extract_plan_json,
    parse_direct_reply,
    parse_understanding,
)
from appv2.tools import FakeQueryEngine
from tests.domains.test_v2_agent_loop import ACTOR, drain, make_runtime

# 数-明1 原句（问数组标准题——few-shot 样张同题，L-04 golden L04-02 同源）。
SHUMING1_QUESTION = "去年各井每天的日产油量是多少？"
_SHUMING1_UNDERSTANDING = "问去年全年各井逐日的日产油量明细。"


# ---------- understand 三形态（两行产＝合同式；裸产/围栏产＝宽容降级） ----------


def test_parse_understanding_two_line_form() -> None:
    understanding, candidates = parse_understanding(
        f"理解：{_SHUMING1_UNDERSTANDING}\n指标候选：日产油量"
    )
    assert understanding == _SHUMING1_UNDERSTANDING
    assert candidates == ["日产油量"]


def test_parse_understanding_bare_json_form() -> None:
    content = (
        '{"理解": "问去年全年各井逐日的日产油量明细。", "指标候选": ["日产油量"]}'
    )
    understanding, candidates = parse_understanding(content)
    assert understanding == _SHUMING1_UNDERSTANDING
    assert candidates == ["日产油量"]


def test_parse_understanding_fenced_json_form() -> None:
    content = (
        "```json\n"
        '{"理解": "问去年全年各井逐日的日产油量明细。", "指标候选": ["日产油量"]}\n'
        "```"
    )
    understanding, candidates = parse_understanding(content)
    assert understanding == _SHUMING1_UNDERSTANDING
    assert candidates == ["日产油量"]


def test_parse_understanding_json_candidates_delimited_string() -> None:
    # 候选值为逗号/顿号分隔串（非数组）——与两行式同口径归一。
    understanding, candidates = parse_understanding(
        '{"理解": "问日产油量。", "指标候选": "日产油量、含水率"}'
    )
    assert understanding == "问日产油量。"
    assert candidates == ["日产油量", "含水率"]


def test_parse_understanding_json_english_alias_keys() -> None:
    # 真模型 JSON 产的常见英文键形——宽容键别名（中文主键优先）。
    understanding, candidates = parse_understanding(
        '{"understanding": "问日产油量。", "metric_candidates": ["日产油量"]}'
    )
    assert understanding == "问日产油量。"
    assert candidates == ["日产油量"]


def test_parse_understanding_json_candidates_none_means_empty() -> None:
    # 「指标候选：无」合同语义在 JSON 降级形下同样成立（"无"字面＝空集）。
    understanding, candidates = parse_understanding(
        '{"理解": "问油井台账。", "指标候选": "无"}'
    )
    assert understanding == "问油井台账。"
    assert candidates == []


# ---------- 真非法产：不误解析（不编造），照走下游拒答链 ----------


def test_parse_understanding_true_garbage_yields_empty() -> None:
    understanding, candidates = parse_understanding("您好！我来帮您分析这个查询请求。")
    assert understanding == ""
    assert candidates == []


def test_parse_understanding_json_without_contract_keys_yields_empty() -> None:
    # 合法 JSON 但无理解/候选合同键——宽容解析不越权取值（空产出如实上报）。
    understanding, candidates = parse_understanding(
        '{"plan": {"metric": "日产油量", "window": "2025"}}'
    )
    assert understanding == ""
    assert candidates == []


# ---------- plan 提取器三形态钉测（裸产/围栏产/散文包裹产——回归钉） ----------


def test_parse_plan_bare_fenced_prose_forms() -> None:
    plan = {"metric_slot": "日产油量", "ranking": False, "limit": 5}
    assert extract_plan_json('{"metric_slot": "日产油量", "ranking": false, "limit": 5}') == plan
    assert extract_plan_json(
        '```json\n{"metric_slot": "日产油量", "ranking": false, "limit": 5}\n```'
    ) == plan
    assert extract_plan_json(
        '计划如下：{"metric_slot": "日产油量", "ranking": false, "limit": 5} 请查收'
    ) == plan


def test_parse_plan_true_garbage_yields_none() -> None:
    assert extract_plan_json("抱歉，我无法直接输出该计划。") is None


# ---------- 真非法产走拒答链（runtime 集成钉测——ReAct 语义迁移） ----------


async def test_true_illegal_output_walks_refusal_chain(tmp_path: Path) -> None:
    """understand 纯散文（两行/JSON 双缺）＋decision 轮轮纯散文（宽容解析失败拒因
    回喂，无 repair）→3 轮轮数闸收敛兜底：零数值不编造、run 正常 completed、
    机读 budget_converged 收口（旧 plan_unparsable 通道随 repair 取消退役——
    V2-31 拍板②：拒因回喂重决策，轮预算照耗）。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["您好！我来帮您分析这个查询请求。"],
        "v2.runtime.decision": ["抱歉，我无法直接输出该决策。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=FakeQueryEngine(), script=script
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=SHUMING1_QUESTION, actor=ACTOR))
        events: list[RunEvent] = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "没能查到能回答" in answer  # 轮耗收敛话术（V2-80d 人话壳单源——零编造）
        assert "21.16" not in answer  # 零数值不编造
        notices = [e.data for e in events if e.event == "notice"]
        converged = [n for n in notices if n.get("type") == "budget_converged"]
        assert len(converged) == 1
        assert converged[0]["gates"] == ["max_rounds"]
        # 三轮全耗且每轮被拒留痕：decision 步 ×4（understand 段＋3 决策轮），
        # 被拒标题在案；answer caller 零调用（无 repair 桶）。
        step_kinds = [e.data["step"] for e in events if e.event == "step"]
        assert step_kinds == ["decision", "decision", "decision", "decision", "answer"]
        steps = await store.list_steps(handle.run_id)
        rejected_titles = [
            s.title for s in steps
            if s.step_type == "decision" and "被拒" in s.title
        ]
        assert len(rejected_titles) == 3
        assert completer.counts() == {
            "v2.runtime.understand": 1,
            "v2.runtime.decision": 3,
        }
    finally:
        await db.dispose()


# ---------- V2-78 无关业务直答形（「直接回答：」单行——理解步第一次调用分流） ----------


def test_parse_direct_reply_present() -> None:
    """「直接回答：」行→取冒号后内容；理解/指标候选两行不解析（直答形独占）。"""
    assert parse_direct_reply("直接回答：您好！请问想查什么油田数据？") == (
        "您好！请问想查什么油田数据？"
    )


def test_parse_direct_reply_absent_and_multiline() -> None:
    """无该行＝空串（两行式解析面零变化）；多行直答逐行拼接；行首前缀才触发。"""
    assert parse_direct_reply("理解：问日产油量。\n指标候选：日产油量") == ""
    assert parse_direct_reply(
        "直接回答：您好！\n直接回答：请问想查什么油田数据？"
    ) == "您好！\n请问想查什么油田数据？"
    # 正文提及「直接回答」字样但不在行首——不误触。
    assert parse_direct_reply("理解：用户想让我直接回答问题。") == ""

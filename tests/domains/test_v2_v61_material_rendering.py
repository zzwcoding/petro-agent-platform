"""V2-61 材料承载分形渲染——W1 行集丢行治本（票面第二节 T1–T8）。

真源头（Owner 2026-10-12 定案）：装配器 DEFAULT_MAX_OBSERVATIONS=24 对所有观察
材料一刀切截断——引擎按系统设定返回 50 数据行，装配层把 50 遮成 24，模型从未见过
第 25~50 行（Q15 manifest 账证「预算 24 支截断（24/51）」）。修复＝分承载体渲染：
权威行集/台账卡全量（引擎已封顶），检索片段保 24 帽，截断必披露（模型面披露行＋
answer_node notice），Manifest 三机检字段记账。
"""

from __future__ import annotations

from typing import Any

import pytest

from appv2.runtime.context import SYSTEM_PROMPT, ContextBuilder
from appv2.runtime.state import Manifest, RunState

# ---------- 罐头 ----------

def _agg_obs(index: int, well: str, value: float) -> dict[str, Any]:
    return {
        "index": index,
        "source": "agg.fct_daily_metering",
        "source_id": "agg.fct_daily_metering",
        "locator": {"kind": "agg_row"},
        "trust": "authoritative",
        "content": f"井号={well}；区块=渤南；日期=2025-09-01；日产油量（吨）={value}",
    }


def _lineage_obs(index: int) -> dict[str, Any]:
    return {
        "index": index,
        "source": "agg.fct_daily_metering",
        "source_id": "agg.fct_daily_metering",
        "locator": {"kind": "lineage"},
        "trust": "authoritative",
        "content": "① 口径 日产油量（吨）——指标台账注册声明（血缘卡）",
    }


def _fragment_obs(index: int, tag: str) -> dict[str, Any]:
    return {
        "index": index,
        "source": f"kb://{tag}",
        "source_id": f"kb-{tag}",
        "locator": {"kind": "fragment"},
        "trust": "report",
        "content": f"检索片段{tag}：月报正文若干内容" * 3,
    }


def _notice_obs(index: int) -> dict[str, Any]:
    return {
        "index": index,
        "source": "runtime",
        "source_id": "runtime",
        "locator": {"kind": "notice"},
        "trust": "notice",
        "content": "窗口缺参反问（元信息）",
    }


def _state(observations: list[dict[str, Any]]) -> RunState:
    return RunState(question="去年各井每天的日产油量明细", observations=observations)


def _rendered_block_indices(context_messages: list[dict[str, str]]) -> list[int]:
    """从当前轮（messages[-1]）观察材料段抽 [n] 引标序号集。"""
    import re

    current = str(context_messages[-1]["content"])
    seg = current.split("观察材料：\n", 1)[1]
    return [int(m) for m in re.findall(r"\[(\d+)\]（", seg)]


# ---------- T1 权威行集全量（W1 形——治本主判据） ----------

def test_t1_authority_rows_render_in_full() -> None:
    obs = [_agg_obs(i, f"N-{i:02d}", 20.0 + i) for i in range(1, 51)]
    obs.append(_lineage_obs(51))
    obs.append(_lineage_obs(52))
    builder = ContextBuilder()  # 默认 max_observations=24——权威不受其限
    ctx = builder.compile(_state(obs), step="answer", instruction="起草答案")
    idx = _rendered_block_indices(ctx.messages)
    assert idx == list(range(1, 53))  # 52 支全渲染——24 帽不再截权威行集
    assert "（材料披露：" not in str(ctx.messages[-1]["content"])
    assert ctx.manifest.material_total == 52
    assert ctx.manifest.material_rendered == 52
    assert ctx.manifest.material_truncated is False
    assert "权威 52 支全量" in ctx.manifest.selected_reason


# ---------- T2 检索片段帽保持＋披露行逐字 ----------

def test_t2_report_cap_kept_with_disclosure() -> None:
    obs = [_agg_obs(i, f"N-{i:02d}", 20.0 + i) for i in range(1, 31)]
    obs += [_fragment_obs(30 + i, f"F{i:02d}") for i in range(1, 41)]
    builder = ContextBuilder()
    ctx = builder.compile(_state(obs), step="answer", instruction="起草答案")
    content = str(ctx.messages[-1]["content"])
    idx = _rendered_block_indices(ctx.messages)
    assert idx[:30] == list(range(1, 31))  # 权威 30 支全量在前
    assert len(idx) == 54  # 30＋min(40,24)
    assert (
        "（材料披露：检索片段共 40 支，本轮渲染前 24 支——未渲染片段不在"
        "本轮视野，不得对其断言；权威行集与台账卡已全量渲染。）" in content
    )
    assert ctx.manifest.material_total == 70
    assert ctx.manifest.material_rendered == 54
    assert ctx.manifest.material_truncated is True
    assert "检索片段帽 24 支截断（24/40）" in ctx.manifest.selected_reason


# ---------- T3 渲染序：权威恒在前（信任级序不因入栈序抖动） ----------

def test_t3_trust_order_stable() -> None:
    obs = [_fragment_obs(i, f"F{i:02d}") for i in range(1, 6)]  # 检索先入栈
    obs += [_agg_obs(10 + i, f"N-{i:02d}", 20.0 + i) for i in range(1, 4)]
    builder = ContextBuilder()
    ctx = builder.compile(_state(obs), step="answer", instruction="起草答案")
    idx = _rendered_block_indices(ctx.messages)
    assert idx == [11, 12, 13, 1, 2, 3, 4, 5]  # 权威在前、各组内入栈序


# ---------- T4 notice 类照旧不进模型面 ----------

def test_t4_notice_filtered() -> None:
    obs = [_agg_obs(1, "N-01", 21.16), _notice_obs(2), _fragment_obs(3, "F01")]
    builder = ContextBuilder()
    ctx = builder.compile(_state(obs), step="answer", instruction="起草答案")
    idx = _rendered_block_indices(ctx.messages)
    assert idx == [1, 3]
    assert ctx.manifest.material_total == 2  # 候选数不含 notice


# ---------- T5 零材料步三字段 ----------

def test_t5_zero_material_fields() -> None:
    builder = ContextBuilder()
    ctx = builder.compile(
        _state([]), step="understand", instruction="识别问句", with_material=False
    )
    assert ctx.manifest.material_total == 0
    assert ctx.manifest.material_rendered == 0
    assert ctx.manifest.material_truncated is False


# ---------- T6 Manifest as_dict 追加三键（旧键零动） ----------

def test_t6_manifest_dict_additive() -> None:
    m = Manifest()
    d = m.as_dict()
    for key in (
        "source_type",
        "source_id",
        "version",
        "trust_level",
        "selected_reason",
        "token_count",
        "transform",
    ):
        assert key in d
    assert d["material_total"] == 0
    assert d["material_rendered"] == 0
    assert d["material_truncated"] is False


# ---------- T7 附 C 逐字稿：既有零删改＋新句两路在场 ----------

def test_t7_answer_instruction_verbatim() -> None:
    import appv2.runtime.graph as graph

    instruction = graph._ANSWER_INSTRUCTION
    # 既有文本字符级零删改（V2-51 末句为锚——追加只在其后）
    anchor = "材料未覆盖该对象时如实说明未覆盖。"
    pos = instruction.find(anchor)
    assert pos != -1, "既有合同文本被删改（V2-51 台账卡句不在场）"
    tail = instruction[pos + len(anchor):]
    # V2-69 起改为前缀断言：追加式合同（V2-48→51→61→69 同模式）允许后续票在
    # 本段之后逐字追加——本钉守「V2-61 段逐字在场且未被删改」，不守「其后为空」。
    assert tail.startswith(
        "行集型子问题（问句要求明细/排名/列举全行集时）：引擎返回的全部数据行逐行"
        "交付并逐行带 [n] 引标——禁汇总引标（如「[1]–[24]」写在表尾注里）；引擎的 "
        "LIMIT 截断注记如实转述进答案。问句只要特定对象或单值（如单井读数、某井某"
        "指标）时，只交付所问对象的行并如实声明窗口与过滤态——禁止把整表倾倒充当答案。"
    )
    # 两路拼装点均含新句（legacy 与汇总路都以 _ANSWER_INSTRUCTION 收尾——常量
    # 单点追加即两路生效，此处钉常量单源性）
    assert "行集型子问题" in instruction
    assert "禁止把整表倾倒充当答案" in instruction


# ---------- T8 附 D：截断态才发 material_truncated 通知 ----------

@pytest.mark.asyncio
async def test_t8_answer_node_truncation_notice(tmp_path: Any) -> None:
    """40 支检索片段（帽 24）→answer 节点发 material_truncated notice（计数在场）；
    1 支对照（全量态）→零该 notice。fake 组合根全图实跑（react_loop 剧本①同形）。"""
    from appv2.runtime import AskRequest
    from appv2.tools import FakeQueryEngine
    from tests.domains.test_v2_agent_loop import (
        ACTOR,
        DECISION_FINALIZE,
        drain,
        make_runtime,
    )
    from tests.domains.test_v2_react_loop import (
        DECISION_KNOWLEDGE,
        UNDERSTAND_KNOWLEDGE,
        _fragment_obs,
        _notices,
        _retrieval_with,
    )

    script = {
        "v2.runtime.understand": [UNDERSTAND_KNOWLEDGE],
        "v2.runtime.decision": [DECISION_KNOWLEDGE, DECISION_FINALIZE],
        "v2.runtime.answer": ["W-111 井投产初期日产油 291 方[1]。"],
    }

    async def _run(obs_count: int) -> list[dict[str, Any]]:
        obs = [
            _fragment_obs(f"片段{i}：W-111 井酸压完井，投产初期日产油 291 方。", f"f{i:02d}")
            for i in range(1, obs_count + 1)
        ]
        workdir = tmp_path / f"run{obs_count}"
        workdir.mkdir()
        runtime, _completer, db = await make_runtime(
            workdir,
            engine=FakeQueryEngine(),
            script=script,
            retrieval=_retrieval_with(*obs),
        )
        try:
            handle = await runtime.ask(
                AskRequest(question="W-111 井完井报告里投产初期日产油是多少？",
                           actor=ACTOR)
            )
            return _notices(await drain(handle))
        finally:
            await db.dispose()

    truncated = [n for n in await _run(40) if n.get("type") == "material_truncated"]
    assert len(truncated) == 1
    assert truncated[0]["gates"] == []
    assert "24/40" in truncated[0]["content"]
    assert "权威行集与台账卡已全量" in truncated[0]["content"]

    full = [n for n in await _run(1) if n.get("type") == "material_truncated"]
    assert full == []


# ---------- 系统提示零触碰回归 ----------

def test_system_prompt_unchanged() -> None:
    assert SYSTEM_PROMPT.startswith("你是油田生产数据的查询与解读系统")  # V2-80d 查询性质声明
    assert "红线：1)" in SYSTEM_PROMPT

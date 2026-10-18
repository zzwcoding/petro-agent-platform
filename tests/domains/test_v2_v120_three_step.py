"""V2-120 作答合同三段式（先核 → 再决 → 后写）验收。

票面＝`tickets/v2/V2-120-作答合同三段式.md`（含「Kimi 评审修正」节）。验收四条：①合同段序与
逐字稿一致（文本断言）、`ANSWER_EXPLORE_CONTRACT` 仍恰一份；②端到端（脚本化 completer）：零支撑题
**先出 explore**、充分题**不 explore**；③EB12 的 explore 触发数 > 0（离线复现面在本件＝零支撑题
explore 步骤 > 0、充分题零步骤）；④全量闸绿（跑批面在回报）。

本票只改**段序**（与 V2-109 分工——V2-109 管第 ① 条引标纪律逐字）：族⑤ `answer_draft` 新成员
`ANSWER_THREE_STEP_CONTRACT` 置**规章段第 0 段**（先于动词钉死句），逐字稿＝票面 §逐字稿（照抄、
零改写）；承载位＝**system 参**（族⑤，不入链——Kimi 评审修正 1）；硬依赖 V2-119（逐字稿「对照下方
『子问题覆盖表』」指代其 user 动态段段头，逐字「子问题覆盖表：」）。

端到端替身＝**提示词条件化 completer**：同一替身按实收 user 段是否含「无支撑」自决 explore 或直接
作答（零固定序列作弊——合同＋覆盖信号是唯一分流依据），故零支撑题走「先 explore、补到正源后再作答」、
充分题零 explore 直答。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from appv2.infra.clock import freeze
from appv2.retrieval import (
    FAMILY_MONTHLY,
    RetrievalBundle,
)
from appv2.retrieval import (
    Observation as RetrievalObservation,
)
from appv2.runtimev2.answering.constants import PAYLOAD_EXPLORE_KEY
from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter
from appv2.runtimev2.prompts import (
    ANSWER_COVERAGE_HEAD,
    ANSWER_COVERAGE_LINE,
    ANSWER_DRAFT_CONTRACT,
    ANSWER_EXPLORE_CONTRACT,
    ANSWER_PERIOD_CONTRACT,
    ANSWER_REQUIREMENTS,
    ANSWER_THREE_STEP_CONTRACT,
    CONTRACT_CONSTANT_FAMILIES,
    JARGON_PLAIN_GLOSSARY,
    SUMMARY_CONTRACT,
    answer_system_contract,
    assemble_answer_prompt,
)
from appv2.runtimev2.state import RunState
from appv2.tools import FakeKnowledgeStore, FakeQueryEngine, ToolRegistry
from tests.domains.test_v2_four_phase import (
    V2LedgerPort,
    v2_decompose,
    v2_knowledge_match,
    v2_ledger_dump,
    v2_matches,
    v2_run,
    v2_runtime,
    v2_steps,
    wire_ledger_projection,
)

# ---------- 逐字稿（票面 §逐字稿——照抄，零改写） ----------

_THREE_STEP_VERBATIM = (
    "【作答前三步】\n"
    "第一步·先核：对照下方「子问题覆盖表」，逐个子问题给出「有支撑／无支撑」。\n"
    "第二步·再决：任一无支撑 → 先申请补充检索（explore）或如实说明未覆盖；"
    "全部有支撑 → 直接进入第三步。\n"
    "第三步·后写：输出答案正文。"
)

# 动词钉死句（族⑤规章段既有件——V2-120 段序断言用；真源＝V1 `answer_turn_preamble` 行 2）。
_VERB_PIN = (
    "现在：写最终答案交付用户。本步是写答案步——不再做任何决策、不再发射任何"
    "动作指令（finalize/decompose 等动作出现即废品）。"
)

# V2-119 动态段段头逐字（V2-120 逐字稿「子问题覆盖表」的指代对象）。
_COVERAGE_HEAD = "子问题覆盖表："


def _answer_state() -> RunState:
    return RunState(
        run_id="run-v120",
        question="K12-3 井近三天生产时长？",
        subtask_results=[{"id": "s1", "question": "K12-3 井生产时长", "status": "ok"}],
    )


# ---------- 1 逐字稿在场＋族登记＋`ANSWER_EXPLORE_CONTRACT` 恰一份 ----------


def test_answer_three_step_contract_verbatim_and_family() -> None:
    """验收①｜逐字稿照抄票面、入族⑤ `answer_draft`、随规章段恰一份；第二出口合同仍恰一份。"""
    assert ANSWER_THREE_STEP_CONTRACT == _THREE_STEP_VERBATIM
    assert ANSWER_THREE_STEP_CONTRACT.startswith("【作答前三步】\n第一步·先核：")
    assert ANSWER_THREE_STEP_CONTRACT.endswith("第三步·后写：输出答案正文。")
    # 族登记（闭世界纪律：新增合同常量入族＋同批改规格清单）
    assert "ANSWER_THREE_STEP_CONTRACT" in CONTRACT_CONSTANT_FAMILIES["answer_draft"]
    # 承载位＝规章段（system 参）：恰一份；第二出口合同（V2-96）仍恰一份
    contract = answer_system_contract()
    assert contract.count(ANSWER_THREE_STEP_CONTRACT) == 1
    assert contract.count(ANSWER_EXPLORE_CONTRACT) == 1
    # 单源：runtimev2 面内恰一处字面定义（消费方零副本）
    from pathlib import Path

    runtimev2 = Path(__file__).resolve().parents[2] / "appv2" / "runtimev2"
    feature = "【作答前三步】"
    holders = sorted(
        path.name for path in runtimev2.rglob("*.py") if feature in path.read_text("utf-8")
    )
    assert holders == ["constants.py"], holders


# ---------- 2 段序固定（先核 → 再决 → 后写；置规章段首件） ----------


def test_answer_three_step_segment_order() -> None:
    """验收①｜段序与逐字稿一致：三步块置规章段**首件**、先于动词钉死句；末段仍＝起草答案合同。"""
    contract = answer_system_contract()
    # 三步块＝规章段第 0 段（首行位）＋与后续段「\n\n」连接
    assert contract.startswith(ANSWER_THREE_STEP_CONTRACT + "\n\n")
    assert contract.split("\n", 1)[0] == "【作答前三步】"
    # 三步序逐字可定位（先核 → 再决 → 后写）
    step1 = "第一步·先核：对照下方「子问题覆盖表」，逐个子问题给出「有支撑／无支撑」。"
    step2 = (
        "第二步·再决：任一无支撑 → 先申请补充检索（explore）或如实说明未覆盖；"
        "全部有支撑 → 直接进入第三步。"
    )
    step3 = "第三步·后写：输出答案正文。"
    positions = [contract.index(marker) for marker in (step1, step2, step3)]
    assert positions == sorted(positions) and len(set(positions)) == 3
    # 全段序：三步块 → 动词钉死句 → 答案要求 → 白话表 → 汇总 → 第二出口 → 材料期 → 起草（收尾）
    order = [
        ANSWER_THREE_STEP_CONTRACT,
        _VERB_PIN,
        f"【答案要求】{ANSWER_REQUIREMENTS}",
        JARGON_PLAIN_GLOSSARY,
        SUMMARY_CONTRACT,
        ANSWER_EXPLORE_CONTRACT,
        ANSWER_PERIOD_CONTRACT,
        ANSWER_DRAFT_CONTRACT,
    ]
    found = [contract.index(marker) for marker in order]
    assert found == sorted(found) and len(set(found)) == len(found)
    assert contract.endswith(ANSWER_DRAFT_CONTRACT)  # 末段＝起草答案合同收尾（既有判据不破）
    # 三步块与动词钉死句相邻（第 0 段 → 第 1 段；中间恰一空行）
    assert f"{ANSWER_THREE_STEP_CONTRACT}\n\n{_VERB_PIN}" in contract
    # 指代面：V2-119 动态段段头逐字在场（「对照下方『子问题覆盖表』」有实指）
    dynamic = assemble_answer_prompt(
        _answer_state(), coverage={"s1": False}
    )
    assert _COVERAGE_HEAD == ANSWER_COVERAGE_HEAD
    assert ANSWER_COVERAGE_HEAD in dynamic
    assert ANSWER_COVERAGE_LINE.format(id="s1") in dynamic
    # 三步块不入 user 动态段（承载位＝system 参——Kimi 评审修正 1）
    assert ANSWER_THREE_STEP_CONTRACT not in dynamic


# ---------- 3 端到端（脚本化 completer）：零支撑先 explore／充分不 explore ----------

# `NQ-M8`／`B-正6` 形离线复现（EB11 归因 §S1／§S2）：题眼 `Y-41` 而窗内只有 34-5 月报（错源）。
_ZERO_SUBTASK = "Y-41 井 2027-01-06 泵效"
_SUFFICIENT_SUBTASK = "Y-41 井 泵效"
_WRONG_SOURCE = "《B-渤中34-5油田躺井治理与检泵作业月报-202608》"
_RIGHT_SOURCE = "《B-渤中34-8油田躺井治理与检泵作业月报-202701》"
_NO_HIT_NOTE = "无台账命中｜未绑定｜窗未定"
_UNDERSTAND_Y41 = json.dumps(
    {
        "route": "full",
        "text": "问 Y-41 井泵效。",
        "metric_candidates": [],
        "subjects": ["Y-41"],
        "terms": [],
    },
    ensure_ascii=False,
)
_EXPLORE_REPLY = json.dumps(
    {
        "action": "explore",
        "reason": "Y-41 井材料未见",
        "requests": [{"tool": "doc_retrieve", "query": "Y-41 井 泵效"}],
    },
    ensure_ascii=False,
)
_ANSWER_BODY = "Y-41 井泵效 52%。"


def _frag(
    text: str,
    fragment_id: str,
    *,
    report: str,
    section: str = "一、概况",
) -> RetrievalObservation:
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=0.9,
        leg="keyword",
        family=FAMILY_MONTHLY,
        fragment_id=fragment_id,
        report_id="rep-v120",
        report=report,
        library_id="lib-monthly",
        library="月报库",
        section=section,
        locator={
            "library": "月报库",
            "report": report,
            "section": section,
            "fragment_id": fragment_id,
        },
    )


def _bundle(*observations: RetrievalObservation) -> RetrievalBundle:
    return RetrievalBundle(
        observations=list(observations),
        window_note=f"召回 {len(observations)} 支/送窗 {len(observations)} 支",
        recalled=len(observations),
        sent=len(observations),
    )


class _QueueRetrieval:
    """按次出列检索面（末位驻留）——再探触发新召回的被控源。"""

    def __init__(self, bundles: Sequence[RetrievalBundle]) -> None:
        self._bundles = list(bundles)
        self.retrieve_calls = 0

    async def retrieve(self, need: Any) -> RetrievalBundle:
        self.retrieve_calls += 1
        if len(self._bundles) > 1:
            return self._bundles.pop(0)
        return self._bundles[0]

    async def graph(self, need: Any) -> RetrievalBundle:
        return _bundle()

    async def fetch_section(
        self, report: str, section: str | None = None, *, cap_chars: int = 0
    ) -> RetrievalBundle:
        return _bundle()

    async def fetch_report(self, report: str, *, cap_chars: int = 0) -> RetrievalBundle:
        return _bundle()


class _ThreeStepCompleter(ScriptedCompleter):
    """三步骤合规模型替身（**提示词条件化**）：user 段见「无支撑」⇒ 出 explore，否则直接作答。

    `understand`／`decision` 走父类固定剧本；`answer` 一律按**实收 user 段**自决（零固定序列）——
    零支撑题的覆盖提示行是 explore 的唯一触发依据，覆盖翻 true 后同一替身转直答（同 V2-119
    「随窗重算」语义）。system 条（规章段）逐次留痕供断言（承载位＝system 参）。
    """

    def __init__(
        self, script: Mapping[str, Sequence[str]], *, answer_body: str, explore_reply: str
    ) -> None:
        super().__init__(script)
        self._answer_body = answer_body
        self._explore_reply = explore_reply
        self.system_contracts: list[str] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        caller: str,
        run_id: str = "",
    ) -> ModelReply:
        if caller != "answer":
            return await super().complete(messages, caller=caller, run_id=run_id)
        self.calls.append((caller, [dict(message) for message in messages]))
        system = next(
            (
                str(message.get("content", ""))
                for message in messages
                if message.get("role") == "system"
            ),
            "",
        )
        self.system_contracts.append(system)
        # 只看**末条 user**（本轮作答动态段）——链为追加形，前轮作答段恒在链上，
        # 全链扫描会把已翻 true 的旧提示行误当本轮信号（分流必须按本轮实收窗）。
        last_user = next(
            (
                str(message.get("content", ""))
                for message in reversed(list(messages))
                if message.get("role") == "user"
            ),
            "",
        )
        content = self._explore_reply if "无支撑" in last_user else self._answer_body
        return ModelReply(
            content=content,
            caller=caller,
            run_id=run_id,
            prompt_tokens=1,
            completion_tokens=1,
            cached_tokens=0,
            usage_estimated=True,
        )


def _registry_with(retrieval: Any) -> ToolRegistry:
    return ToolRegistry(
        knowledge=FakeKnowledgeStore(), query=FakeQueryEngine(), retrieval=retrieval
    )


def _explore_steps(run_id: str) -> list[dict[str, Any]]:
    """再探轮步 payload 的 `explore` 面（每轮一条）。"""
    found: list[dict[str, Any]] = []
    for row in v2_steps(run_id):
        payload = row.payload or {}
        face = payload.get(PAYLOAD_EXPLORE_KEY)
        if isinstance(face, dict) and "round" in face:
            found.append(face)
    return found


def _load(run_id: str) -> RunState:
    from appv2.runtimev2.persistence import RunStore

    return RunStore().load(run_id)


def _answer_user_text(completer: _ThreeStepCompleter, turn: int) -> str:
    """第 `turn` 次作答调用的**末条 user**（本轮作答动态段——覆盖提示行落此）。"""
    messages = completer.messages_of("answer")[turn]
    return next(
        (
            str(message.get("content", ""))
            for message in reversed(messages)
            if message.get("role") == "user"
        ),
        "",
    )


async def _run_case(
    *,
    subtask: str,
    bundles: Sequence[RetrievalBundle],
) -> tuple[RunState, _ThreeStepCompleter, str]:
    dump = v2_ledger_dump()
    wire_ledger_projection(V2LedgerPort(dump))
    clarify = v2_decompose(
        subtask_id="s1",
        question=subtask,
        ledger_notes=_NO_HIT_NOTE,
        chain="knowledge",
    )
    retrieval = _QueueRetrieval(bundles)
    completer = _ThreeStepCompleter(
        {
            "understand": [_UNDERSTAND_Y41],
            "decision": [
                clarify,
                v2_matches(v2_knowledge_match(subtask_id="s1", question=subtask)),
            ],
        },
        answer_body=_ANSWER_BODY,
        explore_reply=_EXPLORE_REPLY,
    )
    with freeze("2026-10-08T09:00:00"):
        runtime, _channel = v2_runtime(
            script={}, registry=_registry_with(retrieval), completer=completer
        )
        events = await v2_run(runtime, subtask)
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    return _load(events[-1].data["run_id"]), completer, events[-1].data["run_id"]


async def test_three_step_zero_support_explores_first() -> None:
    """验收②③｜零支撑题（错源窗）**先出 explore**：首轮起草提示行在场 → explore → 补到正源 → 直答。

    同一提示词条件化替身零固定序列：分流唯一依据＝实收 user 段的覆盖提示行（合同三段式第二步落
    动作）。
    """
    state, completer, run_id = await _run_case(
        subtask=_ZERO_SUBTASK,
        bundles=[
            _bundle(
                _frag(
                    "W-41 井光杆密封盒刺漏，2026 年 8 月完成检泵作业 1 井次。",
                    "frag-w41",
                    report=_WRONG_SOURCE,
                )
            ),
            _bundle(
                _frag("Y-41 井 2027-01-06 泵效 52%。", "frag-y41", report=_RIGHT_SOURCE)
            ),
        ],
    )
    # 先出 explore（第二步·再决落到动作）——EB12 explore 触发数 > 0 的离线复现面
    assert state.explore_rounds == 1
    rounds = _explore_steps(run_id)
    assert len(rounds) == 1 and rounds[0]["round"] == 1 and rounds[0]["hits"] == 1
    # 首轮起草：三步合同（system 参）＋零支撑提示行在场；二轮起草：覆盖翻 true、提示行消失
    assert len(completer.system_contracts) == 2
    assert all(
        ANSWER_THREE_STEP_CONTRACT in contract
        and contract.count(ANSWER_EXPLORE_CONTRACT) == 1
        for contract in completer.system_contracts
    )
    first_user = _answer_user_text(completer, 0)
    assert ANSWER_COVERAGE_HEAD in first_user
    assert ANSWER_COVERAGE_LINE.format(id="s1") in first_user
    second_user = _answer_user_text(completer, 1)
    assert ANSWER_COVERAGE_HEAD not in second_user and "无支撑" not in second_user
    # 补到正源后照常交付
    assert _ANSWER_BODY in (state.answer or "")
    # 承载位＝system 参、不入链（Kimi 评审修正 1）
    chain = "\n".join(str(row.get("content", "")) for row in state.messages)
    assert ANSWER_THREE_STEP_CONTRACT not in chain


async def test_three_step_sufficient_no_explore() -> None:
    """验收②③｜充分题**不 explore**（零误触发）：正源窗提示行整段缺席 → 同替身直接作答。"""
    state, completer, run_id = await _run_case(
        subtask=_SUFFICIENT_SUBTASK,
        bundles=[
            _bundle(
                _frag("Y-41 井 2027-01-06 泵效 52%。", "frag-y41", report=_RIGHT_SOURCE)
            )
        ],
    )
    assert state.explore_rounds == 0
    assert _explore_steps(run_id) == []
    assert completer.counts()["answer"] == 1  # 恰一轮起草、零再探
    first_user = _answer_user_text(completer, 0)
    assert ANSWER_COVERAGE_HEAD not in first_user and "无支撑" not in first_user
    assert _ANSWER_BODY in (state.answer or "")
    # 合同仍随 system 参恰一份在场（充分题不降级合同）
    assert ANSWER_THREE_STEP_CONTRACT in completer.system_contracts[0]

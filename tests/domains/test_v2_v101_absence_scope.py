"""V2-101 缺位话术收紧（只锚本轮材料；禁库级否定）验收。

票面＝`tickets/v2/V2-101-缺位话术收紧.md`。验收四条：①逐字稿在场且**恰一份**（文本断言）；
②`A-正6` 形端到端：输出「本次材料未覆盖」而非库级否定；③与 V2-122 的逐字稿不重复（两票文本
互斥断言）；④全量闸绿（跑批面在回报）。

**边界**（票面 §边界红线）：本票只管**起草合同首句措辞**——`ANSWER_DRAFT_CONTRACT` 第 1 句
**逐字置换**（段内其余字面零改）；范围限定与计数如实归 **V2-122**，本票逐字稿只落族⑤单点、
不渗入 V2-122 边界文件（`tools/handlers.py`／`retrieval/domain.py`／`answering/`／`context/`）。
同改 `ANSWER_DRAFT_CONTRACT` 的三票（V2-101→V2-121→V2-124）**串行且后票只许追加**（真源
`docs/runtime-refactor/design/统筹方案-作答提示词.md` §五）——本件以「旧首句退役＋逐字稿恰一份」
钉住置换形（非追加形）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from appv2.infra.clock import freeze
from appv2.retrieval import FAMILY_MONTHLY, RetrievalBundle
from appv2.retrieval import Observation as RetrievalObservation
from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter
from appv2.runtimev2.persistence import RunStore
from appv2.runtimev2.prompts import (
    ANSWER_COVERAGE_LINE,
    ANSWER_DRAFT_CONTRACT,
    answer_system_contract,
)
from appv2.runtimev2.state import RunState
from appv2.tools import FakeRetrievalEngine
from tests.domains.test_v2_four_phase import (
    V2LedgerPort,
    v2_decompose,
    v2_knowledge_match,
    v2_ledger_dump,
    v2_matches,
    v2_registry,
    v2_run,
    v2_runtime,
    wire_ledger_projection,
)

# ---------- 逐字稿（票面 §逐字稿——照抄，零改写） ----------

_ABSENCE_SCOPE_VERBATIM = (
    "缺位只锚本轮材料：写「本次材料未覆盖」，不得写「报告/资料库未载」或「没有任何一条材料提及」。"
)

# 置换前首句字面（V2-101 施工前的 `ANSWER_DRAFT_CONTRACT` 第 1 句——退役面）。
_OLD_FIRST_SENTENCE = "（材料未覆盖所问时：只简短说明未找到与所缺，不逐源铺陈无关材料）。"

# 库级否定两形（本票禁升格面——**只许作禁令宾语**出现，不得作处方性第二处）。
_LIBRARY_NEGATION_PHRASES = ("报告/资料库未载", "没有任何一条材料提及")

# V2-122（范围限定与计数如实）逐字稿两行——**只读引用**，作两票互斥断言的对照面
# （真源＝`tickets/v2/V2-122-材料范围限定与计数如实.md` §逐字稿；本票不改该票任何文件）。
_V122_VERBATIM = (
    "【范围限定】你的断言与否定只对已见材料成立：不得因「未见」而断言材料中不存在；"
    "需说明「本次材料未覆盖」，不得升格为「报告/资料库未载」。",
    "【计数如实】注记中的「检索到 N 条／用进 M 条」为本次真实计数，必须与实际一致。",
)

# V2-122 边界文件（范围与计数面——本票逐字稿不得渗入）。
_V122_BOUNDARY_FILES = (
    "appv2/tools/handlers.py",
    "appv2/retrieval/domain.py",
    "appv2/runtimev2/answering/core.py",
    "appv2/runtimev2/context/materials.py",
)

_ROOT = Path(__file__).resolve().parents[2]


# ---------- 1 逐字稿在场且恰一份（首句置换形） ----------


def test_absence_scope_verbatim_first_sentence_and_single_source() -> None:
    """验收①｜逐字稿＝票面照抄、置起草合同**首句**（置换非追加）、随规章段**恰一份**、单源。

    判据三面：①**首句**＝逐字稿（`startswith`——票面「起草合同首句置换」）；②旧首句**退役**
    （`not in`——「置换」而非「追加」，段内其余字面零改）；③库级否定两形**只作禁令宾语**出现
    （段内计数＝逐字稿内计数，零处方性第二处）。
    """
    # ① 首句＝逐字稿（照抄票面，零改写）
    assert ANSWER_DRAFT_CONTRACT.startswith(_ABSENCE_SCOPE_VERBATIM)
    assert ANSWER_DRAFT_CONTRACT.count(_ABSENCE_SCOPE_VERBATIM) == 1
    # ② 旧首句退役（逐字置换）
    assert _OLD_FIRST_SENTENCE not in ANSWER_DRAFT_CONTRACT
    # 段内其余字面零改（EB3 D3 已置换句／行集交付规矩段／台账卡边界句／对象级出口句仍在）
    assert "数据行禁汇总引标；组头允许 [m]–[n] 组引标" in ANSWER_DRAFT_CONTRACT
    assert "台账卡（指标/术语定义面）只承载口径与定义" in ANSWER_DRAFT_CONTRACT
    assert "材料未覆盖该对象时如实说明未覆盖。" in ANSWER_DRAFT_CONTRACT
    assert "行集型子问题（问句要求明细/排名/列举全行集时）" in ANSWER_DRAFT_CONTRACT
    # ③ 库级否定形只作**禁令宾语**（每形段内恰一次＝逐字稿内那一处）
    for phrase in _LIBRARY_NEGATION_PHRASES:
        assert ANSWER_DRAFT_CONTRACT.count(phrase) == _ABSENCE_SCOPE_VERBATIM.count(phrase), phrase
    # 承载位＝作答规章段（system 参）：逐字稿恰一份；末段＝起草答案合同收尾（既有判据不破）
    contract = answer_system_contract()
    assert contract.count(_ABSENCE_SCOPE_VERBATIM) == 1
    assert contract.endswith(ANSWER_DRAFT_CONTRACT)
    # 单源：runtimev2 面内恰一处字面定义（消费方零副本）
    runtimev2 = _ROOT / "appv2" / "runtimev2"
    holders = sorted(
        path.name
        for path in runtimev2.rglob("*.py")
        if _ABSENCE_SCOPE_VERBATIM in path.read_text("utf-8")
    )
    assert holders == ["constants.py"], holders


# ---------- 2 与 V2-122 两票逐字稿互斥不重复 ----------


def test_absence_scope_and_v122_texts_mutually_exclusive() -> None:
    """验收③｜两票逐字稿互斥不重复：本票只管首句措辞、V2-122 管范围与计数（票面 §任务）。

    互斥判据两面：①两票逐字稿**全文互不为子串**（各是一份完整独立文本，非彼此复制）；②V2-122
    逐字稿**不在本票落点**（`ANSWER_DRAFT_CONTRACT`／作答规章段），本票逐字稿**不在 V2-122 边界
    文件**（范围与计数面零渗入）。
    """
    for line in _V122_VERBATIM:
        # ① 全文互不为子串（互斥不重复）
        assert line not in _ABSENCE_SCOPE_VERBATIM
        assert _ABSENCE_SCOPE_VERBATIM not in line
        # ② V2-122 逐字稿不在本票落点
        assert line not in ANSWER_DRAFT_CONTRACT
        assert line not in answer_system_contract()
    # 本票只落首句措辞：V2-122 两段头（范围限定／计数如实）在作答规章段零命中
    assert "【范围限定】" not in answer_system_contract()
    assert "【计数如实】" not in answer_system_contract()
    # 本票逐字稿不渗入 V2-122 边界文件（范围与计数归 V2-122）
    for rel in _V122_BOUNDARY_FILES:
        assert _ABSENCE_SCOPE_VERBATIM not in (_ROOT / rel).read_text("utf-8"), rel


# ---------- 3 `A-正6` 形端到端：本轮缺位话术而非库级否定 ----------

# `A-正6` 形（EB11：窗内无 W-111 材料，答面升格「没有任何一条材料提及」为库级否定）。
_QUESTION = "W-111 井的基本情况与用途（井别／所属区块油田／投产状态／生产定位）？"
_SUBTASK = "W-111 井的井别与投产日"
_WRONG_SOURCE = "《A-W11井完井工程报告》"
_NO_HIT_NOTE = "无台账命中｜未绑定｜窗未定"
_UNDERSTAND_W111 = json.dumps(
    {
        "route": "full",
        "text": "问 W-111 井基本情况与用途。",
        "metric_candidates": [],
        "subjects": ["W-111"],
        "terms": [],
    },
    ensure_ascii=False,
)
# 本轮缺位话术（新合同形）／库级否定（旧合同形——同替身对照面）
_SCOPED_ABSENCE = "本次材料未覆盖 W-111 井的井别、所属区块油田、投产日、状态与生产定位。"
_LIBRARY_NEGATION = "没有任何一条材料提及 W-111 井的井别、所属区块油田、投产日、状态或生产定位。"


def _frag(text: str, fragment_id: str, *, report: str) -> RetrievalObservation:
    section = "第一章 井基本情况"
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=0.9,
        leg="keyword",
        family=FAMILY_MONTHLY,
        fragment_id=fragment_id,
        report_id="rep-v101",
        report=report,
        library_id="lib-completion",
        library="完井报告库",
        section=section,
        locator={
            "library": "完井报告库",
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


class _AbsenceScopeCompleter(ScriptedCompleter):
    """缺位话术替身（**提示词条件化**）：交付话术只看**实收 system 规章段**是否携本票逐字稿。

    携（新合同）⇒ 出「本次材料未覆盖」本轮缺位话术；不携（置换前合同）⇒ 出库级否定形——同一替身
    零固定序列，分流唯一依据＝合同文本，故置换前后红→绿可直接对照（本件末段非空转对照即此面）。
    """

    def __init__(
        self, script: Mapping[str, Sequence[str]], *, scoped: str, library_level: str
    ) -> None:
        super().__init__(script)
        self._scoped = scoped
        self._library_level = library_level
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
        system = "\n".join(
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "system"
        )
        self.system_contracts.append(system)
        content = self._scoped if _ABSENCE_SCOPE_VERBATIM in system else self._library_level
        return ModelReply(
            content=content,
            caller=caller,
            run_id=run_id,
            prompt_tokens=1,
            completion_tokens=1,
            cached_tokens=0,
            usage_estimated=True,
        )


def _answer_user_text(completer: _AbsenceScopeCompleter, turn: int) -> str:
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


async def test_a_positive_6_scoped_absence_end_to_end() -> None:
    """验收②｜`A-正6` 形端到端（四相位真跑、窗内无 W-111 材料）：交付「本次材料未覆盖」、
    **零库级否定**（「报告/资料库未载」／「没有任何一条材料提及」）。

    端到端替身＝**提示词条件化 completer**：同一替身按实收 system 规章段是否携本票逐字稿自决话术
    ——末段以置换前合同作非空转对照（旧合同 ⇒ 库级否定），故「红→绿」由合同文本唯一决定。
    """
    dump = v2_ledger_dump()
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = FakeRetrievalEngine(
        bundle=_bundle(
            _frag(
                "W-11 井位于渤中34-5油田CEP-C平台，为常规定向生产井，"
                "完钻井深 2996 米，投产日期 2025-03-12。",
                "frag-w11",
                report=_WRONG_SOURCE,
            )
        )
    )
    completer = _AbsenceScopeCompleter(
        {
            "understand": [_UNDERSTAND_W111],
            "decision": [
                v2_decompose(
                    subtask_id="s1",
                    question=_SUBTASK,
                    ledger_notes=_NO_HIT_NOTE,
                    chain="knowledge",
                ),
                v2_matches(v2_knowledge_match(subtask_id="s1", question=_SUBTASK)),
            ],
        },
        scoped=_SCOPED_ABSENCE,
        library_level=_LIBRARY_NEGATION,
    )
    with freeze("2026-10-08T09:00:00"):
        runtime, _channel = v2_runtime(
            script={}, registry=v2_registry(retrieval=retrieval), completer=completer
        )
        events = await v2_run(runtime, _QUESTION)
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    state: RunState = RunStore().load(run_id)

    # 场景确为 `A-正6` 形：窗内无 W-111 ⇒ 覆盖信号判零支撑（V2-119 提示行在场）
    assert ANSWER_COVERAGE_LINE.format(id="s1") in _answer_user_text(completer, 0)
    # 合同随 system 参恰一份在场（承载位＝system）
    assert _ABSENCE_SCOPE_VERBATIM in completer.system_contracts[0]
    # 交付面＝本轮缺位话术；**零**库级否定（两形皆禁）
    answer = state.answer or ""
    draft = state.draft or ""
    assert "本次材料未覆盖" in answer
    assert "本次材料未覆盖" in draft
    for phrase in _LIBRARY_NEGATION_PHRASES:
        assert phrase not in answer, phrase
    assert "没有任何一条材料提及" not in draft
    # 非空转对照：置换前合同（旧首句字面）下**同一替身**出库级否定——红→绿由合同文本唯一决定
    control = _AbsenceScopeCompleter({}, scoped=_SCOPED_ABSENCE, library_level=_LIBRARY_NEGATION)
    reply = await control.complete(
        [{"role": "system", "content": _OLD_FIRST_SENTENCE}], caller="answer"
    )
    assert reply.content == _LIBRARY_NEGATION
    assert "本次材料未覆盖" not in reply.content

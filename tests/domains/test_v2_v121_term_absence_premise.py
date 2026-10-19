"""V2-121 术语级缺位出口＋待核前提（S1＋S3）验收。

票面＝`tickets/v2/V2-121-术语级缺位出口与待核前提.md`（含「Kimi 评审修正」节）。验收四条：
① `Q45` 形端到端（脚本化 completer）：输出「材料中未见该表述」而非判定式；② 正例回归：
`Q43`／`A-反2` 形判定不变；③ 两处逐字稿文本断言在场且各恰一份；④ 全量闸绿（跑批面在回报）。

两处逐字稿（票面 §逐字稿——照抄，零改写）＋承载位（Kimi 评审修正）：
- **术语级缺位出口**落 `ANSWER_DRAFT_CONTRACT`（族⑤），**对象级出口句之后追加**（与 V2-101／
  V2-124(作) 同常量 ⇒ 三票串行 101→121→124 且 diff 只许追加）；
- **待核前提**落 `clarify_system_contract`（system 规章段——随请求走），**不得入 user 首入包**
  （Kimi 评审修正 1：`prompts/decision_round.py` 自注「规章件不在本段」；原设计破「user 只动态段／
  规章不入链」）。

端到端替身＝**提示词＋材料条件化 completer**：同一替身按「实收 system 规章段是否携术语级出口」
与「实收本轮材料段是否覆盖所问表述／对象」两条件自决交付话术（零固定序列——合同文本与材料窗是
唯一分流依据），故 `Q45` 形出缺位句、`Q43`／`A-反2` 形（引述物是数字或对象、材料覆盖）照常作答。
"""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from appv2.infra.clock import freeze
from appv2.retrieval import FAMILY_MONTHLY, RetrievalBundle
from appv2.retrieval import Observation as RetrievalObservation
from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter
from appv2.runtimev2.persistence import RunStore
from appv2.runtimev2.prompts import (
    ANSWER_DRAFT_CONTRACT,
    CLARIFY_FINALIZE_BOUNDARY,
    CLARIFY_PENDING_PREMISE_CONTRACT,
    CLARIFY_PHASE_HEAD,
    CONTRACT_CONSTANT_FAMILIES,
    PHASE_CLARIFY,
    answer_system_contract,
    assemble_decision_package,
    clarify_system_contract,
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

_TERM_ABSENCE_VERBATIM = (
    "【术语级缺位出口】若所问口径/表述在材料中查无对应登记，直接写"
    "「材料中未见该表述，无法给出其口径」，不得自拟定义或算法。"
)
_PENDING_PREMISE_VERBATIM = (
    "【待核前提】题面中的引述与口语说法列为本轮待核前提：先在材料中核其是否成立，"
    "未成立者如实指出，不得当作已确认事实继续作答。"
)

# 对象级出口句（V2-121 追加位的锚句——逐字取自 `ANSWER_DRAFT_CONTRACT` 既有台账卡边界句尾）。
_OBJECT_EXIT_SENTENCE = "材料未覆盖该对象时如实说明未覆盖。"
# V2-101 置换后的段首第 1 句（同常量三票串行——本票零改面）。
_V101_FIRST_SENTENCE = (
    "缺位只锚本轮材料：写「本次材料未覆盖」，不得写「报告/资料库未载」或「没有任何一条材料提及」。"
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
_DECISION_ROUND = _V2_DIR / "prompts" / "decision_round.py"
# Kimi 评审修正 1 的约束原句（`decision_round.py` `_clarify_package` 自注）。
_USER_SEGMENT_NOTE = "**规章件不在本段**"

# ---------- 端到端话术（条件化替身的两出口＋对照出口） ----------

# 缺位句（术语级出口规定的合法形——`Q45` 形交付面）。
_ABSENCE_BODY = "材料中未见该表述，无法给出其口径。"
# 自造判定式（术语级出口缺席时的旧形——红面／对照面；`EB11` §一-1 病灶）。
_FABRICATED_BODY = "措施增油达标＝措施增油量达到方案设计值的 100%（按台账口径推断）。"


def _answer_state() -> RunState:
    return RunState(
        run_id="run-v121-clarify",
        question="『措施增油达标』按什么口径算？",
        understanding="问措施增油达标的口径。",
    )


def _runtimev2_sources() -> list[tuple[Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in sorted(_V2_DIR.rglob("*.py"))
    ]


def _literal_holders(feature: str) -> list[str]:
    """`feature` 在 runtimev2 面内以**字面量**出现的文件清单（单源判据面）。

    按 AST `Constant` 取值判（隐式拼接已归并为最终值——逐字稿常量由多段字面拼成，裸文本扫描不咬）。
    """
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


# ---------- 1 术语级缺位出口：对象级出口句之后追加、恰一份、单源 ----------


def test_term_absence_exit_verbatim_appended_after_object_exit() -> None:
    """验收③｜术语级出口＝票面逐字稿、落 `ANSWER_DRAFT_CONTRACT`、**对象级出口句之后追加**、
    随作答规章段恰一份、单源；既有字面（V2-101 首句／台账卡边界句／行集段／引标纪律）零改。
    """
    # ① 逐字稿照抄（票面 §逐字稿，零改写）
    assert _TERM_ABSENCE_VERBATIM == (
        "【术语级缺位出口】若所问口径/表述在材料中查无对应登记，直接写"
        "「材料中未见该表述，无法给出其口径」，不得自拟定义或算法。"
    )
    assert _TERM_ABSENCE_VERBATIM.startswith("【术语级缺位出口】")
    assert _TERM_ABSENCE_VERBATIM.endswith("不得自拟定义或算法。")
    # ② 追加位＝对象级出口句之后（逐字相邻，接在行集段之前——纯插入、接缝零改）
    assert (
        _OBJECT_EXIT_SENTENCE
        + _TERM_ABSENCE_VERBATIM
        + "行集型子问题（问句要求明细/排名/列举全行集时）"
        in ANSWER_DRAFT_CONTRACT
    )
    # ③ 只许追加：追加句恰一份，段内既有字面零改（V2-101 置换面／台账卡边界句／行集段／引标纪律）
    assert ANSWER_DRAFT_CONTRACT.count(_TERM_ABSENCE_VERBATIM) == 1
    assert ANSWER_DRAFT_CONTRACT.startswith(_V101_FIRST_SENTENCE)
    assert "台账卡（指标/术语定义面）只承载口径与定义" in ANSWER_DRAFT_CONTRACT
    assert "数据行禁汇总引标；组头允许 [m]–[n] 组引标" in ANSWER_DRAFT_CONTRACT
    assert "引用记号纪律：台账卡/权威行集在视野内有序号的" in ANSWER_DRAFT_CONTRACT
    # ④ 承载位＝作答规章段（system 参）：恰一份；末段仍＝起草答案合同（既有判据不破）
    contract = answer_system_contract()
    assert contract.count(_TERM_ABSENCE_VERBATIM) == 1
    assert contract.endswith(ANSWER_DRAFT_CONTRACT)
    # ⑤ 单源：runtimev2 面内恰一处字面定义（消费方零副本）
    assert _literal_holders(_TERM_ABSENCE_VERBATIM) == ["constants.py"]


# ---------- 2 待核前提：落 system 规章段、不入 user 首入包 ----------


def test_pending_premise_verbatim_merged_into_user_package() -> None:
    """验收③｜待核前提＝票面逐字稿、入族②、随澄清规章段**并入 user 首入包**恰一份。

    **V2-134（承载位回链）**：本判据由「system 规章段在场 ＋ user 首入包零命中」改为
    「随规章段并入 user 首入包、恰一份」（取代 `..._not_user_package` 旧判据）。
    """
    assert _PENDING_PREMISE_VERBATIM == (
        "【待核前提】题面中的引述与口语说法列为本轮待核前提：先在材料中核其是否成立，"
        "未成立者如实指出，不得当作已确认事实继续作答。"
    )
    # ① 族登记（闭世界纪律：新增合同常量入族）
    assert "CLARIFY_PENDING_PREMISE_CONTRACT" in CONTRACT_CONSTANT_FAMILIES["clarify_emission"]
    # ② 规章段：恰一份；插入位＝族②合同之后、finalize 边界句之前（边界句仍收尾）
    contract = clarify_system_contract(4)
    assert contract.count(_PENDING_PREMISE_VERBATIM) == 1
    assert contract.index(CLARIFY_PHASE_HEAD) < contract.index(_PENDING_PREMISE_VERBATIM)
    assert contract.index(_PENDING_PREMISE_VERBATIM) < contract.index(CLARIFY_FINALIZE_BOUNDARY)
    assert contract.endswith(CLARIFY_FINALIZE_BOUNDARY)
    # ③ V2-134：随规章段**并入 user 首入包**、恰一份
    package = assemble_decision_package(
        _answer_state(),
        phase=PHASE_CLARIFY,
        guide_text="§A 指南（测试）",
        today=date(2026, 10, 8),
        max_subtasks=4,
    )
    assert package.count(_PENDING_PREMISE_VERBATIM) == 1
    assert package.count("【待核前提】") == 1
    assert package.count(CLARIFY_PENDING_PREMISE_CONTRACT) == 1
    assert package.startswith(CLARIFY_PHASE_HEAD)  # 规章段并入包首
    # ⑤ 单源：runtimev2 面内恰一处字面定义（消费方零副本）
    assert _literal_holders(_PENDING_PREMISE_VERBATIM) == ["constants.py"]


# ---------- 3 `Q45` 形端到端：术语级缺位句而非自造判定式 ----------

# `Q45` 形（`EB11-臆造上下文归因.md` §一-1 `run-9d726969`）：题眼是**词**（未登记口径），
# 窗内近邻是**同族兼容**的另一条口径（递减增油）——旧合同无出口可依 ⇒ 自造判定式。
_Q45_QUESTION = "『措施增油达标』按什么口径算？"
_Q45_SUBTASK = "措施增油达标 的口径"
_Q45_REPORT = "《B-渤中34-5油田措施效果评价月报-202608》"
_Q45_NEAR_NEIGHBOR = (
    "递减增油口径提示：按台账口径（递减增油＝阶段产油量较递减基准的增产量），"
    "适用于措施效果评价。"
)
_NO_HIT_NOTE = "无台账命中｜未绑定｜窗未定"
# 材料段段头逐字（真源＝`context.render_materials`——`appv2/runtimev2/context/materials.py:620`）：
# 末条 user ＝ 作答动态段＋材料段；本件按该段头**切出材料段**（判「材料是否覆盖所问表述」只在
# 材料内看，题面里的引述本身不算覆盖——`EB11` §一-1 的病灶正是题面引述被当作已确认事实）。
_MATERIAL_HEAD = "\n观察材料：\n"


def _understand(text: str, *, subjects: Sequence[str], terms: Sequence[str]) -> str:
    return json.dumps(
        {
            "route": "full",
            "text": text,
            "metric_candidates": [],
            "subjects": list(subjects),
            "terms": list(terms),
        },
        ensure_ascii=False,
    )


def _frag(text: str, fragment_id: str, *, report: str) -> RetrievalObservation:
    section = "二、措施效果评价"
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=0.9,
        leg="keyword",
        family=FAMILY_MONTHLY,
        fragment_id=fragment_id,
        report_id="rep-v121",
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


class _TermAbsenceCompleter(ScriptedCompleter):
    """术语级缺位替身（**提示词＋材料条件化**——零固定序列）：

    分流两条件（唯一依据＝实收请求文本，非测试侧预设序列）：
    ① 本轮材料段（末条 user）覆盖所问表述／对象（`term` 在场）⇒ 照常作答（`covered_body`——
       正例 `Q43`／`A-反2` 形：引述物是数字或对象、材料可核）；
    ② 材料未覆盖：实收 system 规章段携术语级出口 ⇒ 出缺位句（`absence_body`）；缺席（对照面）
       ⇒ 自造判定式（`fabricated_body`）——故「红→绿」由合同文本唯一决定。

    `understand`／`decision` 走父类固定剧本；system 条与末条 user 逐次留痕供断言。
    """

    def __init__(
        self,
        script: Mapping[str, Sequence[str]],
        *,
        term: str,
        covered_body: str,
        absence_body: str = _ABSENCE_BODY,
        fabricated_body: str = _FABRICATED_BODY,
    ) -> None:
        super().__init__(script)
        self._term = term
        self._covered_body = covered_body
        self._absence_body = absence_body
        self._fabricated_body = fabricated_body
        self.contract_texts: list[str] = []
        self.material_segments: list[str] = []

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
        # V2-134（承载位回链）：规章段已并入 user 首入包 ⇒ 探针改收 user 面文本
        system = "\n".join(
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "user"
        )
        self.contract_texts.append(system)
        last_user = next(
            (
                str(message.get("content", ""))
                for message in reversed(list(messages))
                if message.get("role") == "user"
            ),
            "",
        )
        self.material_segments.append(last_user)
        material = last_user.split(_MATERIAL_HEAD, 1)[1] if _MATERIAL_HEAD in last_user else ""
        if self._term in material:
            content = self._covered_body
        elif _TERM_ABSENCE_VERBATIM in system:
            content = self._absence_body
        else:
            content = self._fabricated_body
        return ModelReply(
            content=content,
            caller=caller,
            run_id=run_id,
            prompt_tokens=1,
            completion_tokens=1,
            cached_tokens=0,
            usage_estimated=True,
        )


def _registry_with(retrieval: object) -> object:
    return v2_registry(retrieval=retrieval)


async def _run_case(
    *,
    question: str,
    subtask: str,
    understand: str,
    fragment: RetrievalObservation,
    term: str,
    covered_body: str,
) -> tuple[RunState, _TermAbsenceCompleter]:
    """四相位真跑（零 LLM）：knowledge 链单子问题＋窗内单支材料。"""
    dump = v2_ledger_dump()
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = FakeRetrievalEngine(bundle=_bundle(fragment))
    completer = _TermAbsenceCompleter(
        {
            "understand": [understand],
            "decision": [
                v2_decompose(
                    subtask_id="s1",
                    question=subtask,
                    ledger_notes=_NO_HIT_NOTE,
                    chain="knowledge",
                ),
                v2_matches(v2_knowledge_match(subtask_id="s1", question=subtask)),
            ],
        },
        term=term,
        covered_body=covered_body,
    )
    with freeze("2026-10-08T09:00:00"):
        runtime, _channel = v2_runtime(
            script={}, registry=_registry_with(retrieval), completer=completer
        )
        events = await v2_run(runtime, question)
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    return RunStore().load(events[-1].data["run_id"]), completer


async def test_q45_shape_term_level_absence_not_fabricated_definition() -> None:
    """验收①｜`Q45` 形端到端（脚本化 completer）：术语未登记 ⇒ 输出「材料中未见该表述」，
    **零自造判定式**（`＝` 判定式不在交付面）。

    非空转对照：同一替身在**术语级出口缺席**的 system 下出自造判定式——红→绿由合同文本唯一决定。
    """
    state, completer = await _run_case(
        question=_Q45_QUESTION,
        subtask=_Q45_SUBTASK,
        understand=_understand("问措施增油达标的口径。", subjects=[], terms=["措施增油达标"]),
        fragment=_frag(_Q45_NEAR_NEIGHBOR, "frag-v121", report=_Q45_REPORT),
        term="措施增油达标",
        covered_body="",  # `Q45` 形材料不覆盖该表述 ⇒ 本出口不被用到
    )
    # 术语级出口随作答规章段（system 参）恰一份在场
    assert len(completer.contract_texts) == 1
    assert completer.contract_texts[0].count(_TERM_ABSENCE_VERBATIM) == 1
    # 材料窗内近邻口径在场（同族兼容的近邻——本票出口正是防其被平移）
    assert "递减增油" in completer.material_segments[0]
    # 交付面＝术语级缺位句；零自造判定式
    answer = state.answer or ""
    draft = state.draft or ""
    assert "材料中未见该表述" in answer
    assert "无法给出其口径" in answer
    assert "材料中未见该表述" in draft
    assert "＝" not in answer and "＝" not in draft
    assert "100%" not in answer and "100%" not in draft
    # 非空转对照：术语级出口缺席的 system 下**同一替身**出自造判定式
    control = _TermAbsenceCompleter(
        {}, term="措施增油达标", covered_body="", absence_body=_ABSENCE_BODY
    )
    reply = await control.complete(
        [{"role": "system", "content": "（旧合同：无术语级出口）"}], caller="answer"
    )
    assert reply.content == _FABRICATED_BODY
    assert "材料中未见该表述" not in reply.content


# ---------- 4 正例回归：`Q43`（数字锚）／`A-反2`（对象锚）判定不变 ----------


async def test_q43_numeric_and_a_fan2_object_positive_unchanged() -> None:
    """验收②｜正例回归：引述物是**数字**（`Q43`）或**对象**（`A-反2`）时材料可核 ⇒ 照常作答，
    术语级出口**不误触发**（条件＝材料查无对应登记）。

    `EB11-臆造上下文归因.md` §一-5：`Q43` 题面同样引述报告里的说法，但其引述物是**数字**（可被
    证伪、材料可核）——本票出口只对「材料中查无对应登记」的**表述／口径**开口，故正例行为不变。
    """
    # `Q43` 形：数字锚（材料含该数字 ⇒ 照常作答）
    q43_state, q43 = await _run_case(
        question="月报里说含水率降了 0.8 个点，这个数是打哪儿来的？",
        subtask="含水率下降 0.8 个百分点的出处",
        understand=_understand("问 0.8 个点的出处。", subjects=[], terms=[]),
        fragment=_frag(
            "《B-渤中34-5油田生产月报-202608》：含水率下降 0.8 个百分点，"
            "系注水结构调整所致。",
            "frag-q43",
            report="《B-渤中34-5油田生产月报-202608》",
        ),
        term="0.8",
        covered_body="该 0.8 个百分点出自月报原文 [1]。",
    )
    q43_answer = q43_state.answer or ""
    assert "该 0.8 个百分点出自月报原文" in q43_answer
    assert _ABSENCE_BODY not in q43_answer
    # 合同仍携术语级出口（在场而不误触发——判别力来自条件，不是出口缺席）
    assert _TERM_ABSENCE_VERBATIM in q43.contract_texts[0]

    # `A-反2` 形：对象锚（材料覆盖该对象 ⇒ 照常作答）
    fan2_state, fan2 = await _run_case(
        question="邻井 W-12 井初期日产油多少？",
        subtask="W-12 井初期日产油",
        understand=_understand("问 W-12 井初期日产油。", subjects=["W-12"], terms=[]),
        fragment=_frag(
            "邻井 W-12 井初期日产油 12.5 吨，生产稳定。",
            "frag-fan2",
            report="《B-渤中34-5油田完井工程报告-202608》",
        ),
        term="W-12",
        covered_body="W-12 井初期日产油 12.5 吨 [1]。",
    )
    fan2_answer = fan2_state.answer or ""
    assert "W-12 井初期日产油 12.5 吨" in fan2_answer
    assert _ABSENCE_BODY not in fan2_answer
    assert _TERM_ABSENCE_VERBATIM in fan2.contract_texts[0]

    # **判定不变**（追加前／后同判）：同一替身、同一材料段——合同携／不携术语级出口，覆盖题两形
    # 都出同一答复（追加句是**条件化**的：材料覆盖 ⇒ 出口不适用；红→绿只发生在「查无登记」面）。
    contract_with = answer_system_contract()
    contract_without = contract_with.replace(_TERM_ABSENCE_VERBATIM, "")
    assert _TERM_ABSENCE_VERBATIM not in contract_without  # 对照面＝追加前形态
    for completer, material, expected in (
        (q43, "含水率下降 0.8 个百分点", "该 0.8 个百分点出自月报原文 [1]。"),
        (fan2, "邻井 W-12 井初期日产油 12.5 吨", "W-12 井初期日产油 12.5 吨 [1]。"),
    ):
        for system in (contract_with, contract_without):
            reply = await completer.complete(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": "用户问题：正例形\n" + _MATERIAL_HEAD + material},
                ],
                caller="answer",
            )
            assert reply.content == expected

"""V2-111 链选择收窄（族② knowledge 链规则段一句窄口逐字稿）验收。

票面＝`tickets/v2/V2-111-链选择收窄.md`。验收四条：①逐字稿在场且**恰一份**；
②`Q11`／`Q26`／`Q31`／`Q35`／`Q41` 形**离线复现**（直接 data 链并注记）；
③`Q40`／`Q47`／`Q48`（已走 data 链）行为**不回退**；④全量闸绿（跑批面在回报）。

**边界**（票面 §边界红线）：只许动 `runtimev2/prompts/`、对应 specs 与测试；**不做路由机制改造**
——原「路由错位」3/5 已被 EB11 真因复核**证伪**（`Q40`／`Q47`／`Q48` 确有 `data_query` 事件）；
真需收窄的是 `Q11`／`Q26`／`Q31`／`Q35`／`Q41`（EB11 帧内**全程只走报告链、零 `data_query`**）。
与 V2-110 同族②（同改 `CLARIFY_EMISSION_CONTRACT`）⇒ **追加非置换**：V2-110 已落 **ask 段**，
本票只落 **knowledge 链规则段段尾**（真源 `docs/runtime-refactor/design/统筹方案-作答提示词.md`
§五·4 族②串行 110→111、后票 diff 只许追加）。

**离线复现机制**（与 V2-110／V2-101／V2-109／V2-121 同款）：**提示词条件化替身**——同一 `decision`
替身按实收 **system 规章段**是否携本票逐字稿自决发哪组链；**前**腿显式回置置换前合同
（`_LEGACY_CONTRACT`）＝EB11 病灶形（井号题全程报告链），**后**腿走生产装配面
`clarify_system_contract`＝本票形（窄口命中 ⇒ 直走 data 链并注记）。两腿都真跑 `clarify()`（澄清
相位本体），断言落点＝`state.question_group` 的 `chain` 提议＋发射注记出流的 `decision_note` 通知
（`_ship_decision_note`——「并注记」的机读信号面）。零触网、零真实 LLM。

**窄口判据面**（票面逐字稿两合取条件）＝井号 ∈ 数据面 agg 白名单 **∧** 报告库确无该井材料；
两条件不齐 ⇒ 不走 data 链（`Q41` 的报告侧井 `Y-21` 仍 knowledge 链——「不做全量路由改造」的
机读反证）。
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from appv2.infra.clock import freeze
from appv2.runtimev2.clarification import clarify
from appv2.runtimev2.clarification.constants import (
    MAX_SUBTASKS,
    NOTICE_DECISION_NOTE,
)
from appv2.runtimev2.clarification.models import ClarifyFinal
from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter, set_completer
from appv2.runtimev2.parsing import CHAIN_KINDS
from appv2.runtimev2.prompts import (
    CLARIFY_EMISSION_CONTRACT,
    PHASE_CLARIFY,
    assemble_decision_package,
    clarify_system_contract,
)
from appv2.runtimev2.state import RunState
from appv2.tools import normalize_well_id

# ---------- 逐字稿（票面 §逐字稿——照抄，零改写；一句） ----------

_NARROW_GATE_VERBATIM = (
    "题面点名的井号若命中数据面白名单、且报告库确无该井材料，直接走 data 链并在答案"
    "注明口径来源；不得先检索报告再答「材料里没有」。"
)
# 单源探针（源码里连续成段的一段——常量内由相邻字面拼成，源码扫描取其中连续段）。
_SINGLE_SOURCE_PROBE = (
    "题面点名的井号若命中数据面白名单、且报告库确无该井材料，直接走 data 链并在答案注明口径来源；"
)


def _ticket_verbatim_block() -> str | None:
    """票面 §逐字稿 代码块原文（`tickets/v2/V2-111-链选择收窄.md`）。"""
    if not _TICKET.exists():
        return None
    matched = re.search(r"## 逐字稿.*?```\n(.*?)```", _TICKET.read_text("utf-8"), re.S)
    return matched.group(1).strip() if matched else None


# knowledge 链规则段定位件（段头／段尾／后继段头——追加位＝段尾、后继段之前）。
_KNOWLEDGE_SEGMENT_HEAD = "knowledge 链规则："
_KNOWLEDGE_SEGMENT_TAIL = "——两分支不得混淆。"
# 后继段头（「回捞白场」段——与 knowledge 链规则段同在一行，段间无换行：段尾「。」直连该件）。
_KNOWLEDGE_SEGMENT_NEXT_MARKER = "回捞白场："
# V2-110 落点（ask 段）边界件（段面互不重叠的机读面——`test_v2_v110_ask_option_discipline.py`
# 同款定位）。
_ASK_SEGMENT_HEAD = "- 反问："
_ASK_SEGMENT_NEXT_MARKER = "\n发射判据："

# 置换前合同（对照腿：显式回置旧形——施工后常量已携逐字稿，故对照面须显式去之；
# 与 V2-109／V2-110 同款：对照＝旧合同字面，非空转）。
_LEGACY_CONTRACT = CLARIFY_EMISSION_CONTRACT.replace(_NARROW_GATE_VERBATIM, "")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIMEV2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
# 票面（施工基准——逐字稿块逐字比对面；票面归档则本断言自动跳过）。
_TICKET = _REPO_ROOT / "tickets" / "v2" / "V2-111-链选择收窄.md"

# ---------- EB11 病灶帧（前腿链证据逐字——真源 `eval/suite-147/results/frames/`） ----------
# 五题「全程只走报告链、零 data_query」（EB11 归因 §S4 症状 A「我核（按 tool 事件）」）：
# Q11(N-02)＝doc_retrieve×3／Q26(Z-16)＝doc_retrieve×1／Q31(N-01)＝doc_retrieve×1／
# Q35(N-O2→N-02)＝doc_retrieve×1／Q41(N-02/Z-16/Y-21)＝doc_retrieve×1。
_EB11_FRAME_LEGACY_KNOWLEDGE_ONLY: Mapping[str, tuple[str, ...]] = {
    "Q11": ("doc_retrieve", "doc_retrieve", "doc_retrieve"),
    "Q26": ("doc_retrieve",),
    "Q31": ("doc_retrieve",),
    "Q35": ("doc_retrieve",),
    "Q41": ("doc_retrieve",),
}
# 三题「已走 data 链」（判分「报告链错位」名单被真因复核证伪——不得因本票回退）：
# Q40(N-01/Z-16)＝data_query×2／Q47(N-02)＝data_query＋doc_retrieve×2／
# Q48(N-03)＝doc_retrieve→data_query（混合）。
_EB11_FRAME_ALREADY_DATA: Mapping[str, tuple[str, ...]] = {
    "Q40": ("data_query", "data_query"),
    "Q47": ("data_query", "doc_retrieve", "doc_retrieve"),
    "Q48": ("doc_retrieve", "data_query"),
}

# ---------- 题干逐字（EB11 真源 `eval/suite-147/answers/50-员工模拟-*.md`） ----------

_Q11_QUESTION = "明早队里碰头，我得带上N-02这月躺了几回、检泵作业用了几天、还有措施增油顶上多少。"
_Q26_QUESTION = "哈哈你们这玩意儿还挺能唠。行，顺手帮我瞅瞅Z-16上旬干得咋样呗。"
_Q31_QUESTION = "烦死了矿里又催材料！快说N-01这个月产量到底完成多少了！"
_Q35_QUESTION = "帮我看看N-O2最近躺没躺井"
_Q41_QUESTION = "比比N-02、Y-21、Z-16这几口，谁含水控制得最好？"
_Q40_QUESTION = "N-01和Z-16比，上个月谁更能打？"
_Q47_QUESTION = "要是N-02再躺上一个月，咱区块月产量得掉多少？"
_Q48_QUESTION = "听说N-03上个月爆管停产了？要是真停了一个月损失得有多大？"

# ---------- 数据面 agg 白名单 × 报告库材料（窄口两合取条件的判据面） ----------
# agg 白名单＝数据面 N/Z 系生产井（`oil_production_daily.csv`／`well_info.csv` 面；
# EB11 §S4 症状 A「Z/N 系井却全程只走报告链」）。
_AGG_WELL_WHITELIST: tuple[str, ...] = ("N-01", "N-02", "N-03", "Z-16")
# 报告库有材料的井＝W/Y 系（EB11 `eval/README.md:172`「两组零重叠」——报告语料零 N/Z 系记录）。
_REPORT_LIBRARY_WELLS: tuple[str, ...] = ("Y-21", "Y-22", "W-21", "W-24", "W-33")


def _gate_applies(well_id: str) -> bool:
    """窄口条件（票面逐字稿两合取）：井号命中数据面白名单 **∧** 报告库确无该井材料。"""
    return well_id in _AGG_WELL_WHITELIST and well_id not in _REPORT_LIBRARY_WELLS


# ---------- 台账 fixture（槽位对账段一判据面：指标 slot 名逐字；EB11 问数册 5 行） ----------
# 绑定态照 EB11 台账：三绑定（日产油量／日产液量／油压）＋含水率／配产量**在册未绑定**。
_METRIC_BINDINGS: Mapping[str, str] = {
    "日产油量": "已绑定",
    "日产液量": "已绑定",
    "油压": "已绑定",
    "含水率": "未绑定",
    "配产量": "未绑定",
}
_WATERMARK = "2026-08-31"
# 执行日（EB11 批锚点 2026-10-18）。
_TODAY = date(2026, 10, 18)
_TODAY_ISO = "2026-10-18T09:00:00"

# 窗（水位内最近整月／旬——EB11 标准答案窗）。
_WINDOW_AUG = "2026-08-01~2026-08-31"
_WINDOW_AUG_HEAD = "2026-08-01~2026-08-10"
# knowledge 链合法注释形（无台账命中——槽位对账段一闭世界字面）。
_KNOWLEDGE_NOTE = "无台账命中｜未绑定｜窗未定"
# 窄口命中时的发射注记（「并在答案注明口径来源」的澄清侧机读承载——`decision_note` 通知）。
_CHAIN_NOTE = "报告库确无该井材料，按数据链取值（口径来源：数据面 agg 白名单）"


def _dump() -> dict[str, Any]:
    """台账投影 fixture（形＝`appv2/tools/ledger.py` dump schema；含水位键）。"""
    metrics = [
        {
            "slot": slot,
            "name": slot,
            "binding_state": "bound" if binding == "已绑定" else "unbound",
            "calibers": [],
            "default_caliber": None,
            "value": f"{slot}（绑定态：{binding}）",
            "source_id": f"sem.metric.{slot}",
            "version": "v1",
            "grain": "单井",
        }
        for slot, binding in _METRIC_BINDINGS.items()
    ]
    return {
        "metrics": metrics,
        "terms": [],
        "objects": [],
        "relations": [],
        "families": [],
        "aliases": {},
        "families_map": {},
        "cards": [],
        "watermark": _WATERMARK,
    }


def _state(**overrides: Any) -> RunState:
    fields: dict[str, Any] = {
        "run_id": "run-v111",
        "question": _Q11_QUESTION,
        "understanding": "问井上的记录与生产情况",
        "ledger_dump": _dump(),
    }
    fields.update(overrides)
    return RunState(**fields)


# ---------- 发射构造（EB11 病灶形 vs 窄口形） ----------


def _subtask(
    subtask_id: str, question: str, *, chain: str, ledger_notes: str
) -> dict[str, Any]:
    return {
        "id": subtask_id,
        "question": question,
        "ledger_notes": ledger_notes,
        "chain": chain,
    }


def _knowledge_subtask(subtask_id: str, question: str) -> dict[str, Any]:
    return _subtask(subtask_id, question, chain="knowledge", ledger_notes=_KNOWLEDGE_NOTE)


def _data_subtask(
    subtask_id: str, question: str, *, slot: str, window: str = _WINDOW_AUG
) -> dict[str, Any]:
    binding = _METRIC_BINDINGS[slot]
    return _subtask(
        subtask_id,
        question,
        chain="data",
        ledger_notes=f"{slot}｜{binding}｜{window}",
    )


def _decompose_emission(*subtasks: Mapping[str, Any], note: str = "") -> str:
    payload: dict[str, Any] = {
        "action": "decompose",
        "question_group": {"subtasks": [dict(subtask) for subtask in subtasks]},
    }
    if note:
        payload["note"] = note
    return json.dumps(payload, ensure_ascii=False)


# ---------- 提示词条件化替身（前／后两腿同面，分流唯一依据＝system 规章段文本） ----------


class _ChainChoiceCompleter(ScriptedCompleter):
    """链选择替身（**提示词条件化**）：发哪组链只看**实收 system 规章段**是否携本票逐字稿。

    携（新合同）⇒ 发 `grounded`（窄口命中 ⇒ 直走 data 链并注记）；不携（置换前合同）⇒ 发
    `legacy`（EB11 病灶形：井号题全程报告链）——同一替身零固定序列，故前／后两腿可直接对照。
    `system_override`＝对照腿显式注入的置换前规章段（缺省＝生产装配面
    `clarify_system_contract`——即 `clarify()` 的实收 system 条）。
    """

    def __init__(
        self,
        *,
        legacy: str,
        grounded: str,
        system_override: str | None = None,
    ) -> None:
        super().__init__({})
        self._legacy = legacy
        self._grounded = grounded
        self._system_override = system_override
        self.contract_texts: list[str] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        caller: str,
        run_id: str = "",
    ) -> ModelReply:
        self.calls.append((caller, [dict(message) for message in messages]))
        system = self._system_override
        if system is None:
            # V2-134（承载位回链）：规章段已并入 user 首入包 ⇒ 探针改收 user 面文本
            system = "\n".join(
                str(message.get("content", ""))
                for message in messages
                if message.get("role") == "user"
            )
        self.contract_texts.append(system)
        content = self._grounded if _NARROW_GATE_VERBATIM in system else self._legacy
        return ModelReply(
            content=content,
            caller=caller,
            run_id=run_id,
            prompt_tokens=1,
            completion_tokens=1,
            cached_tokens=0,
            usage_estimated=True,
        )


@contextmanager
def _phase(completer: _ChainChoiceCompleter) -> Iterator[_ChainChoiceCompleter]:
    """剧本化 completer 注入（`decision` 桶——澄清相位唯一模型调用桶）＋时钟冻结。"""
    previous = set_completer(completer)
    try:
        with freeze(_TODAY_ISO):
            yield completer
    finally:
        set_completer(previous)


def _run_clarify(
    completer: _ChainChoiceCompleter, *, question: str
) -> tuple[Any, RunState]:
    """澄清相位真跑（`clarify()`——零触网、零真实 LLM）。"""
    state = _state(question=question)
    with _phase(completer):
        outcome = clarify(state)
    return outcome, state


def _subtasks(state: RunState) -> tuple[Mapping[str, Any], ...]:
    group = state.question_group
    assert isinstance(group, Mapping), group
    rows = group.get("subtasks")
    assert isinstance(rows, list) and rows, group
    return tuple(row for row in rows if isinstance(row, Mapping))


def _chains(state: RunState) -> tuple[str, ...]:
    """子问题链提议序列（`chain` 键——相位①产物；工具收口归相位②）。"""
    return tuple(str(row.get("chain") or "") for row in _subtasks(state))


def _decision_notes(state: RunState) -> tuple[str, ...]:
    """发射注记出流（`decision_note` 通知——「并注记」的机读信号面，行为 3）。"""
    return tuple(
        str(entry.get("content") or "")
        for entry in state.notices
        if entry.get("type") == NOTICE_DECISION_NOTE
    )


def _well_rows(state: RunState, well_id: str) -> tuple[Mapping[str, Any], ...]:
    """点名该井的子问题行（窄口条件一的落点面）。"""
    return tuple(row for row in _subtasks(state) if well_id in str(row.get("question") or ""))


# ---------- ① 逐字稿在场且恰一份（段尾追加、单源、不入 user 动态段） ----------


def test_chain_narrow_gate_verbatim_in_knowledge_segment_single_source() -> None:
    """验收①｜逐字稿＝票面照抄、置族② `CLARIFY_EMISSION_CONTRACT` 的 **knowledge 链规则段段尾**
    （紧接段尾「——两分支不得混淆。」之后、后继段「回捞白场：」之前）、**恰一份**、单源。

    判据四面：①段尾追加位逐字（段尾件＋逐字稿＋后继段头，段内其余字面零改）；②随澄清**规章段**
    （system 参）恰一份；③**不入 user 动态段**（`assemble_decision_package` 零命中——规章件不入链）；
    ④runtimev2 面内恰 `constants.py` 一处字面定义（消费方零副本）。
    """
    # ① 段尾追加位（照抄票面；段内其余字面零改）
    assert _NARROW_GATE_VERBATIM.count("。") == 1  # 一句（分号前后两分句，尾句号恰一）
    assert CLARIFY_EMISSION_CONTRACT.count(_NARROW_GATE_VERBATIM) == 1
    # 票面 §逐字稿块逐字（施工基准即票面，块文本逐字在场且恰一份）
    ticket_block = _ticket_verbatim_block()
    if ticket_block is not None:
        assert ticket_block == _NARROW_GATE_VERBATIM
        assert CLARIFY_EMISSION_CONTRACT.count(ticket_block) == 1
    assert (
        _KNOWLEDGE_SEGMENT_TAIL + _NARROW_GATE_VERBATIM + _KNOWLEDGE_SEGMENT_NEXT_MARKER
    ) in CLARIFY_EMISSION_CONTRACT
    # 追加非置换：knowledge 链规则段既有字面零改（段头／段内两处相邻字面／段尾照旧在场）
    assert _KNOWLEDGE_SEGMENT_HEAD in CLARIFY_EMISSION_CONTRACT
    assert "不问口径支；口径支歧义不归本相位" in CLARIFY_EMISSION_CONTRACT
    assert "无时间词的数据链问题＝默认近 30 天直发，禁反问时间窗" in CLARIFY_EMISSION_CONTRACT
    assert "回捞白场：" in CLARIFY_EMISSION_CONTRACT
    # 段面互不重叠：本票逐字稿**不入 ask 段**（V2-110 落点），且在 ask 段之后
    assert _ASK_SEGMENT_HEAD in CLARIFY_EMISSION_CONTRACT
    ask_segment = CLARIFY_EMISSION_CONTRACT[
        CLARIFY_EMISSION_CONTRACT.index(_ASK_SEGMENT_HEAD) : CLARIFY_EMISSION_CONTRACT.index(
            _ASK_SEGMENT_NEXT_MARKER
        )
    ]
    assert _NARROW_GATE_VERBATIM not in ask_segment
    assert CLARIFY_EMISSION_CONTRACT.index(_NARROW_GATE_VERBATIM) > CLARIFY_EMISSION_CONTRACT.index(
        _ASK_SEGMENT_NEXT_MARKER
    )
    # ② 承载位＝澄清规章段（system 参）：逐字稿恰一份
    contract = clarify_system_contract(MAX_SUBTASKS)
    assert contract.count(_NARROW_GATE_VERBATIM) == 1
    assert _NARROW_GATE_VERBATIM in contract
    # ③ V2-134（承载位回链）：并入 user 首入包（逐字稿恰一份）
    package = assemble_decision_package(
        _state(),
        phase=PHASE_CLARIFY,
        guide_text="",
        today=_TODAY,
        max_subtasks=MAX_SUBTASKS,
    )
    assert package.count(_NARROW_GATE_VERBATIM) == 1
    # ④ 单源：runtimev2 面内恰一处字面定义（消费方零副本）
    assert _SINGLE_SOURCE_PROBE in _NARROW_GATE_VERBATIM
    holders = sorted(
        path.name
        for path in _RUNTIMEV2_DIR.rglob("*.py")
        if _SINGLE_SOURCE_PROBE in path.read_text("utf-8")
    )
    assert holders == ["constants.py"], holders


# ---------- 窄口语义：两合取条件（不做全量路由改造） ----------


def test_narrow_gate_is_conjunctive_not_full_routing_rewrite() -> None:
    """窄口＝**两合取条件**（井号命中白名单 **∧** 报告库确无该井材料）——**不做全量路由改造**。

    判据四面：①段尾追加的恰是本票逐字稿；②两合取条件字面同现（「若…且…」结构）；③窄口非全量
    ——逐字稿零全量量词（「一律／所有／凡是」类）；④knowledge 链默认规则**原样在场**（追加非置换
    ——data 链只是窄口，默认链选择不动）＋`chain` 两值闭世界不动
    （`parsing.CHAIN_KINDS`＝{data, knowledge}）。

    判据面取**合同自身文本**（段尾追加位切段）——非测试局部常量，故本测对施工前合同即红。
    """
    # ① 段尾追加位＝本票逐字稿（从合同里切出，非测试局部常量）
    appended = CLARIFY_EMISSION_CONTRACT[
        CLARIFY_EMISSION_CONTRACT.index(_KNOWLEDGE_SEGMENT_TAIL)
        + len(_KNOWLEDGE_SEGMENT_TAIL) : CLARIFY_EMISSION_CONTRACT.index(
            _KNOWLEDGE_SEGMENT_NEXT_MARKER
        )
    ]
    assert appended == _NARROW_GATE_VERBATIM
    # ② 两合取条件同现（缺一即非窄口）
    assert "题面点名的井号若命中数据面白名单" in appended
    assert "且报告库确无该井材料" in appended
    assert "直接走 data 链并在答案注明口径来源" in appended
    assert "不得先检索报告再答「材料里没有」" in appended
    # ③ 窄口非全量（零全量量词）
    assert not [
        token for token in ("一律", "所有", "凡是", "任何井号", "全部走") if token in appended
    ]
    # ④ 默认 knowledge 链规则零改（追加非置换）；对照腿＝去窄口后的旧合同（非空转）
    assert _NARROW_GATE_VERBATIM not in _LEGACY_CONTRACT
    assert (
        "knowledge 链规则：问文档所载内容（非台账指标的数值取数）＝单子问题组直发"
        "（chain=knowledge, tool=doc_retrieve）" in _LEGACY_CONTRACT
    )
    assert _KNOWLEDGE_SEGMENT_TAIL in _LEGACY_CONTRACT
    assert _LEGACY_CONTRACT.index(_KNOWLEDGE_SEGMENT_TAIL) < _LEGACY_CONTRACT.index(
        _KNOWLEDGE_SEGMENT_NEXT_MARKER
    )
    assert CHAIN_KINDS == frozenset({"data", "knowledge"})


# ---------- ② 五题形离线复现：窄口命中 ⇒ 直走 data 链并注记 ----------


def _assert_narrow_gate_before_after(
    *,
    question: str,
    legacy_emission: str,
    grounded_emission: str,
    well_id: str,
    legacy_tools: Sequence[str],
) -> RunState:
    """前／后两腿同跑：前腿（置换前合同）＝EB11 病灶（全程报告链、零注记）；后腿（本票形）
    ＝窄口命中 ⇒ 点名该井的子问题**直走 data 链**＋`decision_note` 注记（口径来源）。
    """
    assert well_id in _AGG_WELL_WHITELIST
    assert _gate_applies(well_id), well_id  # 窄口两条件齐（井号命中白名单 ∧ 报告库无该井材料）
    assert set(legacy_tools) == {"doc_retrieve"}  # EB11 帧证据：五题全程只走报告链

    legacy = _ChainChoiceCompleter(
        legacy=legacy_emission,
        grounded=grounded_emission,
        system_override=_LEGACY_CONTRACT,
    )
    outcome_before, state_before = _run_clarify(legacy, question=question)
    assert isinstance(outcome_before, ClarifyFinal)
    assert _NARROW_GATE_VERBATIM not in legacy.contract_texts[0]
    assert _KNOWLEDGE_SEGMENT_TAIL in legacy.contract_texts[0]  # 确为同一合同的置换前形
    chains_before = _chains(state_before)
    assert "data" not in chains_before  # EB11 病灶复现：零 data 链提议
    assert set(chains_before) == {"knowledge"}
    assert _decision_notes(state_before) == ()  # 病灶形零注记

    after = _ChainChoiceCompleter(legacy=legacy_emission, grounded=grounded_emission)
    outcome_after, state_after = _run_clarify(after, question=question)
    assert isinstance(outcome_after, ClarifyFinal)
    assert _NARROW_GATE_VERBATIM in after.contract_texts[0]
    well_rows = _well_rows(state_after, well_id)
    assert well_rows, _subtasks(state_after)
    assert all(row.get("chain") == "data" for row in well_rows)  # 直走 data 链
    assert _CHAIN_NOTE in _decision_notes(state_after)  # 并注记（口径来源）
    return state_after


def test_q11_shape_packaged_well_question_data_chain_with_note_before_and_after_offline() -> None:
    """验收②｜`Q11` 形（多事打包·`N-02`）离线复现：EB11 `run-57bc0328` 三子问题全
    `doc_retrieve`（零 `data_query`）→ 窄口命中 ⇒ 点名 `N-02` 的子问题直走 data 链并注记。"""
    legacy = _decompose_emission(
        _knowledge_subtask("s1", "N-02 本月躺井次数"),
        _knowledge_subtask("s2", "N-02 检泵作业天数"),
        _knowledge_subtask("s3", "N-02 措施增油量"),
    )
    grounded = _decompose_emission(
        _data_subtask("s1", "N-02 2026-08 逐日产量与停产计量日核查", slot="日产油量"),
        note=_CHAIN_NOTE,
    )
    state_after = _assert_narrow_gate_before_after(
        question=_Q11_QUESTION,
        legacy_emission=legacy,
        grounded_emission=grounded,
        well_id="N-02",
        legacy_tools=_EB11_FRAME_LEGACY_KNOWLEDGE_ONLY["Q11"],
    )
    # 注记逐字＝口径来源形（票面「并在答案注明口径来源」的澄清侧承载）
    assert "口径来源" in _decision_notes(state_after)[0]


def test_q26_shape_agg_well_production_data_chain_with_note_before_and_after_offline() -> None:
    """验收②｜`Q26` 形（伪装寒暄·`Z-16` 上旬）离线复现：EB11 `run-424075be` 单子问题
    `doc_retrieve`（零 `data_query`）→ 窄口命中 ⇒ 直走 data 链（水位内窗）并注记。"""
    legacy = _decompose_emission(_knowledge_subtask("s1", "Z-16 上旬生产表现"))
    grounded = _decompose_emission(
        _data_subtask(
            "s1",
            "Z-16 2026-08-01~08-10 日产油量与日产液量",
            slot="日产油量",
            window=_WINDOW_AUG_HEAD,
        ),
        note=_CHAIN_NOTE,
    )
    _assert_narrow_gate_before_after(
        question=_Q26_QUESTION,
        legacy_emission=legacy,
        grounded_emission=grounded,
        well_id="Z-16",
        legacy_tools=_EB11_FRAME_LEGACY_KNOWLEDGE_ONLY["Q26"],
    )


def test_q31_shape_agg_well_output_data_chain_with_note_before_and_after_offline() -> None:
    """验收②｜`Q31` 形（情绪化催促·`N-01` 当月产量）离线复现：EB11 `run-29a0d405` 单子问题
    `doc_retrieve`（零 `data_query`）→ 窄口命中 ⇒ 直走 data 链并注记。"""
    legacy = _decompose_emission(_knowledge_subtask("s1", "N-01 当月产量完成率"))
    grounded = _decompose_emission(
        _data_subtask("s1", "N-01 2026-08 日产油量与配产量", slot="日产油量"),
        note=_CHAIN_NOTE,
    )
    _assert_narrow_gate_before_after(
        question=_Q31_QUESTION,
        legacy_emission=legacy,
        grounded_emission=grounded,
        well_id="N-01",
        legacy_tools=_EB11_FRAME_LEGACY_KNOWLEDGE_ONLY["Q31"],
    )


def test_q35_shape_misspelled_well_data_chain_with_note_before_and_after_offline() -> None:
    """验收②｜`Q35` 形（输入瑕疵 `N-O2`→`N-02`）离线复现：EB11 `run-d2731dc9` 单子问题
    `doc_retrieve`（零 `data_query`）→ 纠正井号后窄口命中 ⇒ 直走 data 链并注记。

    井号归一单点不动（`normalize_well_id` 不猜 O→0——错字形不可归一＝空串，纠正归模型侧），
    故窄口只对**纠正后**的 `N-02` 生效。
    """
    assert normalize_well_id("N-O2") == ""  # 不猜测归一（RULE-PETRO-005 单点）
    assert normalize_well_id("n-2") == "N-02"
    assert "N-O2" not in _AGG_WELL_WHITELIST
    assert _gate_applies("N-02")
    legacy = _decompose_emission(_knowledge_subtask("s1", "N-O2 最近躺没躺井"))
    grounded = _decompose_emission(
        _data_subtask("s1", "N-02 近期逐日产量与停产计量日核查", slot="日产油量"),
        note=_CHAIN_NOTE,
    )
    _assert_narrow_gate_before_after(
        question=_Q35_QUESTION,
        legacy_emission=legacy,
        grounded_emission=grounded,
        well_id="N-02",
        legacy_tools=_EB11_FRAME_LEGACY_KNOWLEDGE_ONLY["Q35"],
    )


def test_q41_shape_cross_source_data_chain_for_whitelist_well_not_report_side_offline() -> None:
    """验收②｜`Q41` 形（跨源对比·`N-02`／`Z-16` agg 侧＋`Y-21` 报告侧）离线复现：
    EB11 `run-755299af` 单子问题 `doc_retrieve`（零 `data_query`）→ 窄口**只收命中白名单的井**
    ⇒ agg 侧走 data 链并注记；报告侧 `Y-21`（报告库有该井材料）仍 knowledge 链——**不做全量
    路由改造**的机读反证（分源列明、零静默丢源）。"""
    assert _gate_applies("N-02") and _gate_applies("Z-16")
    assert not _gate_applies("Y-21")  # 报告库有 Y-21 材料 ⇒ 窄口不命中
    legacy = _decompose_emission(_knowledge_subtask("s1", "N-02、Y-21、Z-16 含水率对比排序"))
    grounded = _decompose_emission(
        _data_subtask("s1", "N-02、Z-16 2026-08 月均含水率（agg 侧）", slot="含水率"),
        _knowledge_subtask("s2", "Y-21 完井报告含水记录（报告侧）"),
        note=_CHAIN_NOTE,
    )
    state_after = _assert_narrow_gate_before_after(
        question=_Q41_QUESTION,
        legacy_emission=legacy,
        grounded_emission=grounded,
        well_id="N-02",
        legacy_tools=_EB11_FRAME_LEGACY_KNOWLEDGE_ONLY["Q41"],
    )
    # 分源列明：agg 侧（N-02/Z-16）走 data 链、报告侧（Y-21）仍 knowledge 链
    agg_rows = _well_rows(state_after, "Z-16")
    report_rows = _well_rows(state_after, "Y-21")
    assert agg_rows and report_rows
    assert all(row.get("chain") == "data" for row in agg_rows)
    assert all(row.get("chain") == "knowledge" for row in report_rows)


# ---------- ③ 三题（已走 data 链）行为不回退 ----------


def _assert_already_data_no_regression(
    *,
    question: str,
    emission: str,
    qid: str,
) -> None:
    """前／后两腿同跑：`Q40`／`Q47`／`Q48` 在 EB11 帧内**已走 data 链**（`data_query` 事件在场）
    ——新合同下链序列**逐位不回退**（`data` 链仍在、零新增知识链置换）。"""
    tools = _EB11_FRAME_ALREADY_DATA[qid]
    assert "data_query" in tools  # EB11 帧证据：已走 data 链（判分「错位」名单被真核证伪）
    legacy = _ChainChoiceCompleter(
        legacy=emission,
        grounded=emission,
        system_override=_LEGACY_CONTRACT,
    )
    outcome_before, state_before = _run_clarify(legacy, question=question)
    assert isinstance(outcome_before, ClarifyFinal)
    assert _NARROW_GATE_VERBATIM not in legacy.contract_texts[0]
    chains_before = _chains(state_before)
    assert "data" in chains_before

    after = _ChainChoiceCompleter(legacy=emission, grounded=emission)
    outcome_after, state_after = _run_clarify(after, question=question)
    assert isinstance(outcome_after, ClarifyFinal)
    assert _NARROW_GATE_VERBATIM in after.contract_texts[0]
    chains_after = _chains(state_after)
    assert chains_after == chains_before  # 逐位不回退
    assert "data" in chains_after
    # 窄口命中面：这些井号同属白名单 ∧ 报告库无该井材料（窄口指向同一方向，非改道）
    for well_id in ("N-01", "N-02", "N-03", "Z-16"):
        assert _gate_applies(well_id)


def test_q40_shape_already_data_chain_no_regression_offline() -> None:
    """验收③｜`Q40` 形（`N-01`／`Z-16` 对比）不回退：EB11 `run-6d45ac69` `data_query`×2
    → 新合同下链序列逐位相同（仍 data 链）。"""
    emission = _decompose_emission(
        _data_subtask("s1", "N-01 2026-08 日产油量合计", slot="日产油量"),
        _data_subtask("s2", "Z-16 2026-08 日产油量合计", slot="日产油量"),
    )
    _assert_already_data_no_regression(
        question=_Q40_QUESTION, emission=emission, qid="Q40"
    )


def test_q47_shape_already_data_chain_no_regression_offline() -> None:
    """验收③｜`Q47` 形（`N-02` 再躺一个月影响）不回退：EB11 `run-665af2b6`
    `data_query`＋`doc_retrieve`×2（混合形）→ 新合同下链序列逐位相同（data 链仍在）。"""
    emission = _decompose_emission(
        _data_subtask("s1", "N-02 2026-08 月产油基线", slot="日产油量"),
        _knowledge_subtask("s2", "区块月产量基线"),
        _knowledge_subtask("s3", "停产损失折算口径"),
    )
    _assert_already_data_no_regression(
        question=_Q47_QUESTION, emission=emission, qid="Q47"
    )


def test_q48_shape_already_data_chain_no_regression_offline() -> None:
    """验收③｜`Q48` 形（`N-03` 爆管停产损失）不回退：EB11 `run-dea50406`
    `doc_retrieve`→`data_query`（混合形）→ 新合同下链序列逐位相同（data 链仍在）。"""
    emission = _decompose_emission(
        _knowledge_subtask("s1", "N-03 爆管停产记录核实"),
        _data_subtask("s2", "N-03 停产计量日核查", slot="日产油量"),
    )
    _assert_already_data_no_regression(
        question=_Q48_QUESTION, emission=emission, qid="Q48"
    )

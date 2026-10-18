"""V2-110 澄清选项设计纪律（族② ask 段两句逐字稿）验收。

票面＝`tickets/v2/V2-110-澄清选项设计纪律.md`。验收四条：①两句逐字稿在场且**恰一份**；
②`Q05`／`Q39` 形**离线复现**（不出现库外井号／必落水位外的默认项）；③分油田题
（`B-正2`／`B-正6`）选项到油田粒度或改全覆盖；④全量闸绿（跑批面在回报）。

**边界**（票面 §边界红线）：只许动 `runtimev2/prompts/`、`runtimev2/clarification/`（选项构造面）、
对应 specs 与测试；**不动台账数据源**（数据源对齐归数据面——L2 已裁略过）。本票只落两条**逻辑
不变量**：①选项值须能被下游作用域**原样消费**；②选定后不得**静默丢源**。本票**只改族②
`CLARIFY_EMISSION_CONTRACT` 的 ask 段**（段内追加两句、其余字面零改）；同改本常量的邻票
（V2-111 knowledge 链规则段）⇒ 族②两票**串行 110→111**、后票 diff 只许追加（真源
`docs/runtime-refactor/design/统筹方案-作答提示词.md` §五·4）。

**离线复现机制**（与 V2-101／V2-109／V2-121 同款）：**提示词条件化替身**——同一 `decision` 替身
按实收 **system 规章段**是否携本票逐字稿自决发哪组选项；**前**腿显式回置置换前合同
（`_LEGACY_CONTRACT`）＝EB11 病灶形，**后**腿走生产装配面 `clarify_system_contract`＝本票形。
两腿都真跑 `clarify()`（澄清相位本体），断言落点＝`state.pending_ask` 的 ask 帧选项。
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from appv2.infra.clock import freeze
from appv2.runtimev2.clarification import clarify, object_ambiguity_ask
from appv2.runtimev2.clarification.constants import MAX_SUBTASKS
from appv2.runtimev2.clarification.models import ClarifyAsk, ClarifyFinal
from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter, set_completer
from appv2.runtimev2.prompts import (
    CLARIFY_EMISSION_CONTRACT,
    PHASE_CLARIFY,
    assemble_decision_package,
    clarify_system_contract,
)
from appv2.runtimev2.state import ALL_FIELDS_OPTION, RunState
from appv2.tools import (
    OILFIELD_INSTANCES_CAP,
    metric_requires_subject,
    normalize_well_id,
    oilfield_instances,
    roster_entries,
    roster_lookup,
)

# ---------- 逐字稿（票面 §逐字稿——照抄，零改写；两句） ----------

_ASK_OPTION_VALUE_LINE = (
    "选项值必须是下游可直接消费的取值：不得含库内不存在的示例井号，"
    "不得提供必然落在数据水位之外的默认项。"
)
_ASK_OPTION_GROUNDING_LINE = (
    "分油田题的选项须列到油田粒度；无法列全时不要弹选项，改为全覆盖并分源列明。"
)
# 票面 §逐字稿块内两句**逐行**（行间换行照抄——块文本逐字＝本常量）。
_ASK_OPTION_DISCIPLINE_VERBATIM = _ASK_OPTION_VALUE_LINE + "\n" + _ASK_OPTION_GROUNDING_LINE
# 单源探针（源码里连续成段的一段——第二句在常量内是**单个**字面）。
_SINGLE_SOURCE_PROBE = _ASK_OPTION_GROUNDING_LINE


def _ticket_verbatim_block() -> str | None:
    """票面 §逐字稿 代码块原文（`tickets/v2/V2-110-澄清选项设计纪律.md`）。"""
    if not _TICKET.exists():
        return None
    matched = re.search(r"## 逐字稿.*?```\n(.*?)```", _TICKET.read_text("utf-8"), re.S)
    return matched.group(1).strip() if matched else None


# ask 段前句（段内其余字面零改的定位件——追加位＝该句之后）。
_ASK_SEGMENT_PRIOR_SENTENCE = "或目标/对象/口径真歧义（用户补一句话即可解——拍板⑥澄清分级②）。"
# ask 段后继件（追加位＝该件之前；ask 段收尾后接「发射判据：」行）。
_ASK_SEGMENT_NEXT_MARKER = "\n发射判据："

# 置换前合同（对照腿：显式回置旧形——施工后常量已携逐字稿，故对照面须显式去之；
# 与 V2-109 `_LEGACY_CONTRACT` 同款：对照＝旧合同字面，非空转）。
_LEGACY_CONTRACT = CLARIFY_EMISSION_CONTRACT.replace(_ASK_OPTION_DISCIPLINE_VERBATIM, "")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIMEV2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
# 票面（施工基准——逐字稿块逐字比对面；票面归档则本断言自动跳过）。
_TICKET = _REPO_ROOT / "tickets" / "v2" / "V2-110-澄清选项设计纪律.md"

# ---------- EB11 病灶帧（前腿选项逐字——真源 eval/suite-147/results/frames/） ----------
# `EB11-C-Q05.json`（run-40112f6d 第 3 张卡：库内不存在的示例井号 A12H／A12H-1／B01）。
_LEGACY_Q05_PROMPT = "您选了「告诉井号」——麻烦您把井号发一下，比如 A12H、A12H-1 这种格式。"
_LEGACY_Q05_OPTIONS = ("A12H", "A12H-1", "B01", "其他井号（请直接补充）")
# `EB11-C-Q39.json`（选项默认窗「近30天」——执行日锚回看必落水位外：水位止于 2026-08-31，
# 窗 2026-09-08~2026-10-07 全在水位之外 ⇒ 引擎新鲜度闸拦停）。
_LEGACY_Q39_PROMPT = "「干得最差」可以指好几种差法——您想按哪种给井排雷？"
_LEGACY_Q39_OPTIONS = (
    "日产油量最低（近30天默认）",
    "抽油机时率最低（躺井/停产多）",
    "产量完成率最低（欠产严重）",
    "综合含水率最高（高含水低效井）",
)
# `EB11-A-B-正2.json`／`EB11-A-B-正6.json`（分油田题选项用**区块粒度合并**「渤中油田」，
# 而材料里是油田粒度「渤中 34-5」「渤中 34-8」）。
_LEGACY_FIELD_PROMPT = "这道题问的是「检泵周期」——系统里有多个油田的数据。请确认要查哪一个："
_LEGACY_FIELD_OPTIONS = ("渤中油田", "渤南油田", "渤西油田", "都要（分源对比）")

# ---------- 台账／名录 fixture（库内名字面——「可被下游原样消费」的判据面） ----------

_Q05_QUESTION = "他昨天提的那个事儿后来咋样了？就井上那事儿。"
_Q39_QUESTION = "咱区块哪口井干得最差？给我个数。"
_B2_QUESTION = "杆断的是哪几口井？平均检泵周期多少？"
_B6_QUESTION = "近三年 8 月平均检泵周期的变化趋势？"

_METRIC_ROW: dict[str, Any] = {
    "slot": "检泵周期",
    "name": "检泵周期",
    "binding_state": "bound",
    "calibers": [],
    "default_caliber": None,
    "value": "检泵周期（单位 天）",
    "source_id": "sem.metric.检泵周期",
    "version": "v1",
    "grain": "单井",
}
# 库内井（台账对象面——下游查证/取数可原样消费的名字）。
_LIBRARY_WELLS: tuple[str, ...] = ("W-21", "W-22", "W-24")
# 库内油田（**油田粒度**——材料侧真形「渤中 34-5」「渤中 34-8」，非区块粒度合并）。
_LIBRARY_FIELDS: tuple[str, ...] = ("渤中34-5", "渤中34-8")
# 数据水位（EB11 Q39 病灶帧同值：汇总层止于 2026-08-31）。
_WATERMARK = "2026-08-31"
# 执行日（EB11 Q39 病灶帧锚点：窗 2026-09-08~2026-10-07 ⇒ 锚 2026-10-08）。
_TODAY = date(2026, 10, 8)
_TODAY_ISO = "2026-10-08T09:00:00"

# 「无据时的出路」形（非名字、非窗——下游按用户补充说明消费；票面「无法列全时…改全覆盖」的
# 同族出口）。
_ESCAPE_OPTIONS: tuple[str, ...] = ("直接补充说明",)

_NOTE = "检泵周期｜已绑定｜2026-06-01~2026-08-31"


def _objects() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for well in _LIBRARY_WELLS:
        rows.append(
            {"obj": f"{well} 井", "value": f"{well} 井", "source_id": f"sem.object.{well}"}
        )
    for field in _LIBRARY_FIELDS:
        rows.append(
            {
                "obj": f"{field}油田",
                "value": f"{field}油田",
                "source_id": f"sem.object.{field}",
            }
        )
    return rows


def _dump() -> dict[str, Any]:
    """台账投影 fixture（形＝`appv2/tools/ledger.py` dump schema；含水位键）。"""
    return {
        "metrics": [dict(_METRIC_ROW)],
        "terms": [],
        "objects": _objects(),
        "relations": [],
        "families": [],
        "aliases": {},
        "families_map": {},
        "cards": [],
        "watermark": _WATERMARK,
    }


def _state(**overrides: Any) -> RunState:
    fields: dict[str, Any] = {
        "run_id": "run-v110",
        "question": _Q05_QUESTION,
        "understanding": "问井上那事儿的后续",
        "ledger_dump": _dump(),
    }
    fields.update(overrides)
    return RunState(**fields)


def _roster(state: RunState) -> tuple[tuple[str, str], ...]:
    """库内井名录面（台账对象行「〈井号〉井」形——下游查证可原样消费的名单）。

    比对单点复用 `tools.roster_entries`／`tools.roster_lookup`（RULE-PETRO-005 归一与名录
    比对——零第二份算法）。
    """
    rows = state.ledger_dump.get("objects") or []
    pairs = [
        (str(row.get("obj") or "").removesuffix("井").strip(), "")
        for row in rows
        if str(row.get("obj") or "").endswith("井")
    ]
    return roster_entries(pairs)


# ---------- 下游可消费性判据（本票两条逻辑不变量的机读面） ----------

# 井号形（含 `A12H` 这类尾字母形——EB11 Q05 病灶形）：纯 ASCII 记号、无中文、无空格。
_WELL_SHAPED = re.compile(r"^[A-Za-z]{1,4}-?\d{1,3}[A-Za-z]?(?:-[A-Za-z0-9]{1,4})?$")
# 相对窗（「近N天」——闭世界只识别不解析，V2-107）。
_RELATIVE_DAYS = re.compile(r"近\s*(\d{1,3})\s*天")


def _offending_well_options(
    options: Sequence[str], roster: Sequence[tuple[str, str]]
) -> tuple[str, ...]:
    """井号形选项 ∩ 库内名录之外（**库外井号**——用户选了也调不出材料 ⇒ 不可原样消费）。"""
    return tuple(
        option
        for option in options
        if _WELL_SHAPED.match(option) and roster_lookup(option, roster) is None
    )


def _well_options_consumable(
    options: Sequence[str], roster: Sequence[tuple[str, str]]
) -> bool:
    """井号形选项**全部** ∈ 库内名录（无据出路形不在此面——非名字）。"""
    return not _offending_well_options(options, roster)


def _window_beyond_watermark(option: str, *, today: date, watermark: date) -> bool:
    """选项里的相对窗**整体**晚于数据水位（必落水位外——下游取不到数）。

    判据＝窗上沿锚执行日、窗下沿＝执行日−N 天；窗下沿 > 水位 ⇒ 整窗在水位之外
    （EB11 Q39：水位 2026-08-31、执行日 2026-10-08、近 30 天 ⇒ 窗 2026-09-08~2026-10-07）。
    """
    matched = _RELATIVE_DAYS.search(option)
    if matched is None:
        return False
    return today - timedelta(days=int(matched.group(1))) > watermark


def _field_options_offending(options: Sequence[str]) -> tuple[str, ...]:
    """油田选择形选项 ∩ 库内**油田粒度**名单之外（**区块粒度合并**形——如「渤中油田」）。

    库内名单＝材料/台账侧的油田粒度真形（「渤中34-5」「渤中34-8」）；「渤中油田」既非库内
    名字、又把两个油田并成一个 ⇒ 下游无法按源取数（选定后静默丢源）。
    """
    library = {f"{field}油田" for field in _LIBRARY_FIELDS}
    return tuple(
        option
        for option in options
        if option.endswith("油田") and option not in library
    )


def _ask_emission(prompt: str, options: Sequence[str]) -> str:
    return json.dumps(
        {"action": "ask", "ask": {"prompt": prompt, "options": list(options)}},
        ensure_ascii=False,
    )


def _decompose_emission(*subtasks: Mapping[str, Any]) -> str:
    rows = [dict(subtask) for subtask in subtasks]
    return json.dumps(
        {"action": "decompose", "question_group": {"subtasks": rows}}, ensure_ascii=False
    )


# ---------- 提示词条件化替身（前／后两腿同面，分流唯一依据＝system 规章段文本） ----------


class _AskOptionCompleter(ScriptedCompleter):
    """选项纪律替身（**提示词条件化**）：发哪组选项只看**实收 system 规章段**是否携本票逐字稿。

    携（新合同）⇒ 发 `grounded`（库内名字／水位内窗／油田粒度或全覆盖形）；不携（置换前合同）
    ⇒ 发 `ungrounded`（EB11 病灶形）——同一替身零固定序列，故前／后两腿可直接对照。
    `system_override`＝对照腿显式注入的置换前规章段（缺省＝生产装配面
    `clarify_system_contract`——即 `clarify()` 的实收 system 条）。
    """

    def __init__(
        self,
        *,
        grounded: str,
        ungrounded: str,
        system_override: str | None = None,
    ) -> None:
        super().__init__({})
        self._grounded = grounded
        self._ungrounded = ungrounded
        self._system_override = system_override
        self.system_contracts: list[str] = []

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
            system = "\n".join(
                str(message.get("content", ""))
                for message in messages
                if message.get("role") == "system"
            )
        self.system_contracts.append(system)
        content = (
            self._grounded
            if _ASK_OPTION_DISCIPLINE_VERBATIM in system
            else self._ungrounded
        )
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
def _phase(completer: _AskOptionCompleter) -> Iterator[_AskOptionCompleter]:
    """剧本化 completer 注入（`decision` 桶——澄清相位唯一模型调用桶）＋时钟冻结。"""
    previous = set_completer(completer)
    try:
        with freeze(_TODAY_ISO):
            yield completer
    finally:
        set_completer(previous)


def _run_clarify(
    completer: _AskOptionCompleter, *, question: str
) -> tuple[Any, RunState]:
    """澄清相位真跑（`clarify()`——零触网、零真实 LLM）。"""
    state = _state(question=question)
    with _phase(completer):
        outcome = clarify(state)
    return outcome, state


def _ask_options(state: RunState) -> tuple[str, ...]:
    """挂起帧的选项（`pending_ask` 投影——下游恢复腿的消费面）。"""
    frame = state.pending_ask
    assert isinstance(frame, Mapping), frame
    options = frame.get("options")
    assert isinstance(options, (list, tuple)), frame
    return tuple(str(option) for option in options)


# ---------- ① 逐字稿在场且恰一份（段内追加、单源、不入 user 动态段） ----------


def test_ask_option_discipline_verbatim_in_ask_segment_single_source() -> None:
    """验收①｜两句逐字稿＝票面照抄、置族② `CLARIFY_EMISSION_CONTRACT` 的 **ask 段内**
    （紧接「…拍板⑥澄清分级②）。」之后、段收尾「- 发射判据：」之前）、**恰一份**、单源。

    判据四面：①ask 段内追加位逐字（前句＋逐字稿＋段后继件，段内其余字面零改）；②随澄清**规章段**
    （system 参）恰一份；③**不入 user 动态段**（`assemble_decision_package` 零命中——规章件不入链）；
    ④runtimev2 面内恰 `constants.py` 一处字面定义（消费方零副本）。
    """
    # ① ask 段内追加位（照抄票面；段内其余字面零改）
    assert _ASK_OPTION_DISCIPLINE_VERBATIM.count("。") == 2  # 两句各一尾句号
    assert CLARIFY_EMISSION_CONTRACT.count(_ASK_OPTION_DISCIPLINE_VERBATIM) == 1
    # 票面 §逐字稿块逐字（含行间换行——施工基准即票面，块文本逐字在场且恰一份）
    ticket_block = _ticket_verbatim_block()
    if ticket_block is not None:
        assert ticket_block == _ASK_OPTION_DISCIPLINE_VERBATIM
        assert CLARIFY_EMISSION_CONTRACT.count(ticket_block) == 1
    assert (
        _ASK_SEGMENT_PRIOR_SENTENCE
        + _ASK_OPTION_DISCIPLINE_VERBATIM
        + _ASK_SEGMENT_NEXT_MARKER
    ) in CLARIFY_EMISSION_CONTRACT
    # 追加非置换：ask 段既有字面仍在（白场两形／选项个数闭世界）
    assert "仅限两种白场：无场景词＋阈值判断形（口径支待用户选），" in CLARIFY_EMISSION_CONTRACT
    assert "2~4 个" in CLARIFY_EMISSION_CONTRACT
    # ② 承载位＝澄清规章段（system 参）：逐字稿恰一份
    contract = clarify_system_contract(MAX_SUBTASKS)
    assert contract.count(_ASK_OPTION_DISCIPLINE_VERBATIM) == 1
    assert _ASK_OPTION_DISCIPLINE_VERBATIM in contract
    # ③ 不入 user 动态段（规章件不入链）
    package = assemble_decision_package(
        _state(),
        phase=PHASE_CLARIFY,
        guide_text="",
        today=_TODAY,
        max_subtasks=MAX_SUBTASKS,
    )
    assert _ASK_OPTION_DISCIPLINE_VERBATIM not in package
    # ④ 单源：runtimev2 面内恰一处字面定义（消费方零副本）
    # 探针＝源码里**连续字面**的一段（逐字稿在常量里由相邻字面拼成——源码扫描取其中连续段；
    # 「恰一份」的语义面由上面 `count == 1` 把守）。
    assert _SINGLE_SOURCE_PROBE in _ASK_OPTION_DISCIPLINE_VERBATIM
    holders = sorted(
        path.name
        for path in _RUNTIMEV2_DIR.rglob("*.py")
        if _SINGLE_SOURCE_PROBE in path.read_text("utf-8")
    )
    assert holders == ["constants.py"], holders


# ---------- ② `Q05` 形：库外示例井号（前腿复现 → 后腿不出现） ----------


def test_q05_shape_library_external_well_id_before_and_after_offline() -> None:
    """验收②｜`Q05` 形**离线复现**（提示词条件化替身 × 澄清相位真跑）。

    **前**（置换前合同）：替身按「system 规章段不携本票逐字稿」发 EB11 病灶形选项
    （`A12H`／`A12H-1`／`B01`——库内不存在的示例井号）⇒ 下游可消费性判据咬住（用户选了也调不出
    材料；真机 `run-40112f6d` 三轮反问后钻取空转的提示词病根）。
    **后**（新合同）：同一替身按「system 规章段携本票逐字稿」发库内井号形选项＋无据出路 ⇒
    库外井号为零，且每个井号形选项 ∈ 库内名录（**可被下游原样消费**）。
    """
    # 前腿：置换前合同 ⇒ EB11 病灶形选项（库外井号在场）
    legacy = _AskOptionCompleter(
        grounded=_ask_emission(
            "请确认要查哪口井：",
            (*_LIBRARY_WELLS, *_ESCAPE_OPTIONS),
        ),
        ungrounded=_ask_emission(_LEGACY_Q05_PROMPT, _LEGACY_Q05_OPTIONS),
        system_override=_LEGACY_CONTRACT,
    )
    outcome_before, state_before = _run_clarify(legacy, question=_Q05_QUESTION)
    assert isinstance(outcome_before, ClarifyAsk)
    assert _ASK_OPTION_DISCIPLINE_VERBATIM not in legacy.system_contracts[0]
    assert _ASK_SEGMENT_PRIOR_SENTENCE in legacy.system_contracts[0]  # 确为同一合同的置换前形
    options_before = _ask_options(state_before)
    assert options_before == _LEGACY_Q05_OPTIONS  # EB11 病灶帧选项逐字
    offending_before = _offending_well_options(options_before, _roster(state_before))
    assert offending_before == ("A12H", "A12H-1", "B01")  # 库外井号（病灶复现）

    # 后腿：新合同（生产装配面）⇒ 库内井号形选项，库外井号为零
    after = _AskOptionCompleter(
        grounded=_ask_emission(
            "请确认要查哪口井：",
            (*_LIBRARY_WELLS, *_ESCAPE_OPTIONS),
        ),
        ungrounded=_ask_emission(_LEGACY_Q05_PROMPT, _LEGACY_Q05_OPTIONS),
    )
    outcome_after, state_after = _run_clarify(after, question=_Q05_QUESTION)
    assert isinstance(outcome_after, ClarifyAsk)
    assert _ASK_OPTION_DISCIPLINE_VERBATIM in after.system_contracts[0]
    options_after = _ask_options(state_after)
    assert _offending_well_options(options_after, _roster(state_after)) == ()
    assert _well_options_consumable(options_after, _roster(state_after))
    # 井号形选项逐个可归一到库内名录（下游查证面单点：`roster_lookup`）
    well_options = [option for option in options_after if _WELL_SHAPED.match(option)]
    assert well_options == list(_LIBRARY_WELLS)
    for option in well_options:
        assert roster_lookup(option, _roster(state_after)) is not None
    # 选项个数闭世界（2~4）不破
    assert 2 <= len(options_after) <= 4


# ---------- ② `Q39` 形：必落水位外的默认项（前腿复现 → 后腿不出现） ----------


def test_q39_shape_default_outside_watermark_before_and_after_offline() -> None:
    """验收②｜`Q39` 形**离线复现**（提示词条件化替身 × 澄清相位真跑）。

    **前**（置换前合同）：替身发 EB11 病灶形选项「日产油量最低（近30天默认）」⇒ 该默认窗
    （执行日 2026-10-08 锚回看 30 天＝2026-09-08~2026-10-07）**整体晚于**数据水位 2026-08-31
    ⇒ 必落水位外（真机：引擎新鲜度闸拦停、零结果）。
    **后**（新合同）：同一替身发水位内锚定形（「水位内最近可得窗」——V2-107 拦停替代形）⇒
    选项里没有任何**必然**落水位外的默认窗。
    """
    watermark = date.fromisoformat(_WATERMARK)
    # 前腿：置换前合同 ⇒ 「近30天默认」必落水位外
    legacy = _AskOptionCompleter(
        grounded=_ask_emission(
            _LEGACY_Q39_PROMPT,
            (
                "日产油量最低（水位内最近可得窗）",
                "抽油机时率最低（水位内最近可得窗）",
                "产量完成率最低",
                "综合含水率最高",
            ),
        ),
        ungrounded=_ask_emission(_LEGACY_Q39_PROMPT, _LEGACY_Q39_OPTIONS),
        system_override=_LEGACY_CONTRACT,
    )
    outcome_before, state_before = _run_clarify(legacy, question=_Q39_QUESTION)
    assert isinstance(outcome_before, ClarifyAsk)
    options_before = _ask_options(state_before)
    assert options_before == _LEGACY_Q39_OPTIONS  # EB11 病灶帧选项逐字
    beyond_before = [
        option
        for option in options_before
        if _window_beyond_watermark(option, today=_TODAY, watermark=watermark)
    ]
    assert beyond_before == ["日产油量最低（近30天默认）"]  # 必落水位外的默认项（病灶复现）

    # 后腿：新合同 ⇒ 无必落水位外的默认项
    after = _AskOptionCompleter(
        grounded=_ask_emission(
            _LEGACY_Q39_PROMPT,
            (
                "日产油量最低（水位内最近可得窗）",
                "抽油机时率最低（水位内最近可得窗）",
                "产量完成率最低",
                "综合含水率最高",
            ),
        ),
        ungrounded=_ask_emission(_LEGACY_Q39_PROMPT, _LEGACY_Q39_OPTIONS),
    )
    outcome_after, state_after = _run_clarify(after, question=_Q39_QUESTION)
    assert isinstance(outcome_after, ClarifyAsk)
    assert _ASK_OPTION_DISCIPLINE_VERBATIM in after.system_contracts[0]
    options_after = _ask_options(state_after)
    assert [
        option
        for option in options_after
        if _window_beyond_watermark(option, today=_TODAY, watermark=watermark)
    ] == []
    # 水位锚定形在场（「水位内最近可得窗」——不是把窗删掉了事）
    assert "水位内最近可得窗" in "".join(options_after)


# ---------- ③ 分油田题：到油田粒度（`B-正2` 形） ----------


def test_partition_field_options_to_oilfield_granularity_not_block_offline() -> None:
    """验收③｜`B-正2` 形**离线复现**：分油田题选项须列到**油田粒度**。

    **前**（置换前合同）：EB11 病灶形选项＝**区块粒度合并**（「渤中油田」把 34-5／34-8 并成一个，
    且不在库内油田名单里）⇒ 下游无法按源取数（选定后静默丢源）。
    **后**（新合同）：选项＝库内**油田粒度**名（「渤中34-5油田」「渤中34-8油田」）＋全覆盖出口
    ⇒ 每个油田选择形选项 ∈ 库内油田名单。
    """
    # 前腿：置换前合同 ⇒ 区块粒度合并形
    legacy = _AskOptionCompleter(
        grounded=_ask_emission(
            _LEGACY_FIELD_PROMPT,
            (*[f"{field}油田" for field in _LIBRARY_FIELDS], ALL_FIELDS_OPTION),
        ),
        ungrounded=_ask_emission(_LEGACY_FIELD_PROMPT, _LEGACY_FIELD_OPTIONS),
        system_override=_LEGACY_CONTRACT,
    )
    outcome_before, state_before = _run_clarify(legacy, question=_B2_QUESTION)
    assert isinstance(outcome_before, ClarifyAsk)
    options_before = _ask_options(state_before)
    assert options_before == _LEGACY_FIELD_OPTIONS  # EB11 病灶帧选项逐字
    assert _field_options_offending(options_before) == (
        "渤中油田",
        "渤南油田",
        "渤西油田",
    )  # 区块粒度合并／库外油田名（病灶复现）

    # 后腿：新合同 ⇒ 油田粒度＋全覆盖出口
    after = _AskOptionCompleter(
        grounded=_ask_emission(
            _LEGACY_FIELD_PROMPT,
            (*[f"{field}油田" for field in _LIBRARY_FIELDS], ALL_FIELDS_OPTION),
        ),
        ungrounded=_ask_emission(_LEGACY_FIELD_PROMPT, _LEGACY_FIELD_OPTIONS),
    )
    outcome_after, state_after = _run_clarify(after, question=_B2_QUESTION)
    assert isinstance(outcome_after, ClarifyAsk)
    assert _ASK_OPTION_DISCIPLINE_VERBATIM in after.system_contracts[0]
    options_after = _ask_options(state_after)
    assert _field_options_offending(options_after) == ()
    assert [f"{field}油田" for field in _LIBRARY_FIELDS] == [
        option for option in options_after if option.endswith("油田")
    ]
    assert options_after[-1] == ALL_FIELDS_OPTION  # 全覆盖出口（选定后不静默丢源）
    assert 2 <= len(options_after) <= 4


# ---------- ③ 分油田题：无法列全 ⇒ 不弹、改全覆盖并分源列明（`B-正6` 形） ----------


def test_partition_field_cannot_enumerate_all_sources_full_coverage_offline() -> None:
    """验收③｜`B-正6` 形**离线复现**：无法列全时不弹选项，改**全覆盖并分源列明**。

    **前**（置换前合同）：仍弹区块粒度选项（列不全且合并源）——静默丢源。
    **后**（新合同）：替身不发 `ask`，改发 `decompose`——子问题**逐源**列明（渤中34-5／渤中34-8
    各一条），零 ask 帧、零丢源。
    """
    per_source = tuple(
        {
            "id": f"s{index}",
            "question": f"{field}油田 近三年 8 月平均检泵周期变化趋势",
            "ledger_notes": _NOTE,
            "chain": "data",
        }
        for index, field in enumerate(_LIBRARY_FIELDS, start=1)
    )
    # 前腿：置换前合同 ⇒ 仍弹区块粒度选项（列不全＋合并源）
    legacy = _AskOptionCompleter(
        grounded=_decompose_emission(*per_source),
        ungrounded=_ask_emission(_LEGACY_FIELD_PROMPT, _LEGACY_FIELD_OPTIONS),
        system_override=_LEGACY_CONTRACT,
    )
    outcome_before, state_before = _run_clarify(legacy, question=_B6_QUESTION)
    assert isinstance(outcome_before, ClarifyAsk)
    assert _ask_options(state_before) == _LEGACY_FIELD_OPTIONS

    # 后腿：新合同 ⇒ 不弹、全覆盖并分源列明
    after = _AskOptionCompleter(
        grounded=_decompose_emission(*per_source),
        ungrounded=_ask_emission(_LEGACY_FIELD_PROMPT, _LEGACY_FIELD_OPTIONS),
    )
    outcome_after, state_after = _run_clarify(after, question=_B6_QUESTION)
    assert isinstance(outcome_after, ClarifyFinal)
    assert state_after.pending_ask is None  # 零 ask 帧（不弹选项）
    subtasks = state_after.question_group["subtasks"]
    assert len(subtasks) == len(_LIBRARY_FIELDS)
    # 分源列明：库内每个油田各占一条子问题（零丢源）
    for field in _LIBRARY_FIELDS:
        assert any(f"{field}油田" in str(row["question"]) for row in subtasks), field
    assert len(subtasks) <= MAX_SUBTASKS


# ---------- 程序侧对象歧义 ask（选项构造面）：选项可原样消费＋全覆盖出口恒在 ----------


def test_program_ask_options_downstream_consumable_and_full_coverage_exit() -> None:
    """程序侧 `object_ambiguity_ask` 回归：选项＝**库内实例原样**（零自造名、零区块粒度合并）
    ＋「都要（分源对比）」**全覆盖出口**；实例超选项封顶时也不静默丢源。

    判据三面：①选项逐字＝实例名单＋`ALL_FIELDS_OPTION`（下游恢复腿按实例名原样映射
    `state.subjects`——`tests/domains/test_v2_subject_ask.py::test_resume_instance_choice_lands_subject`）；
    ②实例数 > `OILFIELD_INSTANCES_CAP` 时**全覆盖出口仍在**（未列出的实例由「都要（分源对比）」
    承载——哨兵 `ALL_FIELDS_SENTINEL` 落下游分源装配，同件
    `::test_resume_all_choice_lands_sentinel`）；③零库外油田名／零区块粒度合并（本票不变量②）。
    """
    instances = tuple(f"{field}油田" for field in _LIBRARY_FIELDS)
    state = _state(terms=("检泵周期",))
    ask = object_ambiguity_ask(
        state,
        grain_requires_subject=metric_requires_subject,
        subject_instances=lambda: instances,
    )
    assert ask is not None
    assert ask.options == [*instances, ALL_FIELDS_OPTION]
    assert _field_options_offending(ask.options) == ()
    assert state.pending_subject_options == instances

    # 实例超封顶（无法列全）：读面封顶后全覆盖出口仍在、不静默丢源
    many = tuple(f"油田{index}" for index in range(1, OILFIELD_INSTANCES_CAP + 3))
    capped_instances = oilfield_instances(many)  # 生产绑定＝读面封顶（≤3）
    assert len(capped_instances) == OILFIELD_INSTANCES_CAP
    capped_state = _state(terms=("检泵周期",))
    capped = object_ambiguity_ask(
        capped_state,
        grain_requires_subject=metric_requires_subject,
        subject_instances=lambda: capped_instances,
    )
    assert capped is not None
    assert capped.options == [*capped_instances, ALL_FIELDS_OPTION]
    assert capped.options[-1] == ALL_FIELDS_OPTION  # 全覆盖出口（「都要（分源对比）」）
    assert len(capped.options) <= 4  # 选项个数闭世界（2~4）
    # 选项逐个 ∈ 库内实例 ∪ 全覆盖出口（零自造名——下游可原样消费；未列出的实例由
    # 全覆盖出口的哨兵承载——`ALL_FIELDS_SENTINEL` 落下游分源装配，零静默丢源）
    assert set(capped.options) <= set(capped_instances) | {ALL_FIELDS_OPTION}


# ---------- 与邻票 V2-111 的族②同常量面：只许追加、段面互不重叠 ----------


def test_v110_appended_only_and_disjoint_from_v111_segment() -> None:
    """族②同常量两票（V2-110 → V2-111）**串行且后票只许追加**：本票逐字稿只落 ask 段，
    不入 knowledge 链规则段（V2-111 落点——`_ASK_SEGMENT_NEXT_MARKER` 之后的段面）。

    V2-111 逐字稿（票面 §逐字稿——只读引用，本票不改该段任何字面）。
    """
    v111_verbatim = (
        "题面点名的井号若命中数据面白名单、且报告库确无该井材料，直接走 data 链并在答案"
        "注明口径来源；不得先检索报告再答「材料里没有」。"
    )
    # ① 本票逐字稿只落 ask 段（V2-111 落点＝knowledge 链规则段，在 ask 段之后）
    ask_segment = CLARIFY_EMISSION_CONTRACT[
        CLARIFY_EMISSION_CONTRACT.index("- 反问：") : CLARIFY_EMISSION_CONTRACT.index(
            _ASK_SEGMENT_NEXT_MARKER
        )
    ]
    assert _ASK_OPTION_DISCIPLINE_VERBATIM in ask_segment
    assert _ASK_OPTION_DISCIPLINE_VERBATIM not in CLARIFY_EMISSION_CONTRACT[
        CLARIFY_EMISSION_CONTRACT.index(_ASK_SEGMENT_NEXT_MARKER) :
    ]
    # ② 两票逐字稿互不为子串（各是一份完整独立文本）
    assert v111_verbatim not in _ASK_OPTION_DISCIPLINE_VERBATIM
    assert _ASK_OPTION_DISCIPLINE_VERBATIM not in v111_verbatim
    # ③ 追加非置换：ask 段内既有判据（禁再 discover／对称面禁 ask 两半句）字面零改
    assert "发射判据：台账命中＋窗已定＝分解完毕，禁再 discover；" in CLARIFY_EMISSION_CONTRACT
    assert "对称面——窗可锚定＝禁 ask" in CLARIFY_EMISSION_CONTRACT
    # ④ 程序侧井号归一单点仍单源（本票不动台账数据源／不加第二份井号算法）
    assert normalize_well_id("w-11") == "W-11"

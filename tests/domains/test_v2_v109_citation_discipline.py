"""V2-109 答案引标纪律（每条含数值／事实断言的句子带 `[n]`）验收。

票面＝`tickets/v2/V2-109-答案引标纪律.md`。验收四条：①逐字稿在场且**恰一份**（文本断言）；
②EB12 帧内 `cited=[]` 的答案数显著下降（与 EB11 对照——离线构造面在本件）；③
`ANSWER_REQUIREMENTS` **条数不变**（置换非追加）；④全量闸绿（跑批面在回报）。

**边界**（票面 §边界红线）：只许动 `runtimev2/prompts/`、对应 specs 与测试；不改条数、不新增词表。
本票只改**族⑥ `ANSWER_REQUIREMENTS` 第 ① 条**——**逐字置换**（票面 §逐字稿照抄、零改写；旧
「逐条事实断言带 [n] 引标（n＝观察材料序号）；」退役），②–⑩条文本与顺序零改。同改
`ANSWER_REQUIREMENTS` 的邻票面分工（真源 `docs/runtime-refactor/design/统筹方案-作答提示词.md`
§五·5）：**V2-101** 改
族⑤ `ANSWER_DRAFT_CONTRACT` 段首、**V2-121** 追加该常量中段、**V2-124** 追加该常量段尾——三票皆
不动族⑥，本票不动族⑤ ⇒ 同常量面零重叠。

**与 V2-103 叠加覆盖零支撑面**：V2-103 把**无引标数字行**的比对域扩到本轮窗内全观测（核验面）；
本票在**提示词面**抬带标率（模型稿带引标 ⇒ 答案正文自带可解析引标、`citation_chunks` 辖域可解）。
两票叠加＝`数-排1` 形（EB11 `run-098e7ab2`：单句无引标草稿 ⇒ `supported=0/rewritten=1/cited=[]`
零交付）的**离线构造面**：提示词条件化替身（同一替身按实收 system 规章段是否携本票逐字稿自决
带不带标）＋核验真跑——携（新合同）⇒ 正文含 `[1]`（`citation_chunks` 辖域可解）；不携（置换前
合同）⇒ 正文零引标（核验面经 V2-103 扩窗后可保留该行并按命中支回填 `verdict.cited`——**答案正文
带标率**与**核验面 `cited` 落账**两事分列）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from appv2.runtimev2.answering import answer
from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter, set_completer
from appv2.runtimev2.prompts import (
    ANSWER_DRAFT_CONTRACT,
    ANSWER_REQUIREMENTS,
    answer_system_contract,
)
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.verification import verify
from appv2.runtimev2.verification.rules import citation_chunks

# ---------- 逐字稿（票面 §逐字稿——照抄，零改写） ----------

_CITATION_DISCIPLINE_VERBATIM = (
    "每条含数值或事实断言的句子都必须带 [n] 引标；无引标的断言句不得进答案。"
)

# 置换前第 ① 条字面（V2-109 施工前的 `ANSWER_REQUIREMENTS` 第 1 条——退役面）。
_OLD_FIRST_ITEM = "逐条事实断言带 [n] 引标（n＝观察材料序号）；"

# ②–⑩ 条逐字（置换面外——票面「其后 ②–⑩ 字面与顺序零改」；真源＝施工前常量字面）。
_REQUIREMENTS_TAIL: tuple[str, ...] = (
    "材料未覆盖的部分不得断言、如实说明未覆盖；",
    "材料含多个来源（不同报告／油田／井）时逐个来源分别作答（不冲突也要分别列出，不以反问代替作答）；",
    "作答后仍有未覆盖的来源或指代不明处，如实点名未覆盖来源（含检索窗注记的未进窗来源）"
    "并请用户补充检索或指明对象，不静默略过；",
    "引擎的降级/未绑定/拦停注记必须如实转述进对应子问题条目（不得静默丢弃）；",
    "引用观察材料请摘录必要短语并带引标，禁整段照搬原文充当回答；",
    "「理解：／指标候选：」及任何动作 JSON 是过程产物，出现在答案中即废品；",
    "核验元数据（血缘卡五要素、来源表、数据批次）不写进答案正文——它们在界面"
    "『引用与口径』侧栏逐字展示；答案只在用户需要时带一句口径（如单位）；",
    "面向油田业务用户作答：系统内部词首次出现时紧跟一句括号里的白话解释——如"
    "『口径（这个数是按什么规则算的）』『台账（平台里登记指标和术语的名册）』；同一词后文"
    "可直接使用。不要把内部说法整句甩给用户（『召回 51 支/送窗 12 支』应写成"
    "『检索到 51 条材料，其中 12 条用进了答案』）；",
    "材料未覆盖所问时：先从已给材料中答出可能与问题相关的内容，再给用户一句更容易查到结果的"
    "提问建议（如补充井号、时间范围或报告名称）。",
)

# 邻票面逐字稿（只读引用——作「同常量面零重叠」对照；本票不改这些常量任何字面）。
# V2-101 段首（族⑤ `ANSWER_DRAFT_CONTRACT` 第 1 句）。
_V101_VERBATIM = (
    "缺位只锚本轮材料：写「本次材料未覆盖」，不得写「报告/资料库未载」或「没有任何一条材料提及」。"
)
# V2-121 中段（族⑤ 术语级缺位出口句）。
_V121_VERBATIM = (
    "【术语级缺位出口】若所问口径/表述在材料中查无对应登记，直接写"
    "「材料中未见该表述，无法给出其口径」，不得自拟定义或算法。"
)
# V2-124 段尾（族⑤ 推断去处句）。
_V124_VERBATIM = (
    "【推断去处】推断句须写明推断依据与不确定性（「据此推断」「若…则」），不得作为事实断言陈述。"
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIMEV2_DIR = _REPO_ROOT / "appv2" / "runtimev2"


# ---------- 1 逐字稿在场且恰一份（第 ① 条置换形） ----------


def test_citation_discipline_verbatim_first_item_and_single_source() -> None:
    """验收①｜逐字稿＝票面照抄、置 `ANSWER_REQUIREMENTS` **第 ① 条**（置换非追加）、随规章段
    **恰一份**、runtimev2 面内单源。

    判据三面：①第 ① 条＝逐字稿（`startswith`）；②旧第 ① 条字面**退役**（`not in`——「置换」而非
    追加）；③逐字稿随 `answer_system_contract()` 的【答案要求】清单恰一份，且 runtimev2 面内恰
    `constants.py` 一处字面定义（消费方零副本）。
    """
    # ① 第 ① 条＝逐字稿（照抄票面，零改写）
    assert ANSWER_REQUIREMENTS.startswith(_CITATION_DISCIPLINE_VERBATIM)
    assert ANSWER_REQUIREMENTS.count(_CITATION_DISCIPLINE_VERBATIM) == 1
    # ② 旧第 ① 条退役（逐字置换）
    assert _OLD_FIRST_ITEM not in ANSWER_REQUIREMENTS
    # 承载位＝作答规章段（system 参）：逐字稿恰一份；末段＝起草答案合同收尾（既有判据不破）
    contract = answer_system_contract()
    assert contract.count(_CITATION_DISCIPLINE_VERBATIM) == 1
    assert f"【答案要求】{ANSWER_REQUIREMENTS}" in contract
    assert contract.endswith(ANSWER_DRAFT_CONTRACT)
    # 单源：runtimev2 面内恰一处字面定义（消费方零副本）
    holders = sorted(
        path.name
        for path in _RUNTIMEV2_DIR.rglob("*.py")
        if _CITATION_DISCIPLINE_VERBATIM in path.read_text("utf-8")
    )
    assert holders == ["constants.py"], holders


# ---------- 2 条数不变（置换非追加）＋②–⑩ 字面零改 ----------


def test_answer_requirements_item_count_unchanged() -> None:
    """验收③｜**条数不变**：置换后仍 10 条（①–⑩）；②–⑩ 逐条字面零改、顺序固定。

    条数判据按**逐条列名**落（非 `count("；")` 单值）：①–⑨ 条间分隔 9 ＋ ① 内文 1 ＋ ⑧ 内文 1
    ＋ ⑨ 内文 1 ＝ 12 个「；」（V2-109 第 ① 条内文新增一「；」——分隔符与条内标点两事，故计数
    与逐条列名同测）。**未新增词表**（票面 §边界红线）：逐字稿两分句均为既有字面元素重组，零新
    业务名词。
    """
    items = ANSWER_REQUIREMENTS.split("；")
    # ①–⑨ 尾「；」切出 10 片；末片＝⑩（无尾「；」但内含 0 处——①／⑧／⑨ 内文「；」各自多切一片）
    # 故切片数＝10（条）＋1（① 内文）＋1（⑧ 内文）＝12 片（⑨ 内文「；」在片 10 内，不再多切）。
    assert len(items) == 12, items
    # ① 条（含内文「；」——前两片合起来＝第 ① 条）
    assert items[0] == "每条含数值或事实断言的句子都必须带 [n] 引标"
    assert items[1].startswith("无引标的断言句不得进答案。")
    # ②–⑩ 逐条字面零改、顺序固定（tail 逐条 `in` ＋ 相对序）
    positions: list[int] = []
    for tail in _REQUIREMENTS_TAIL:
        assert tail in ANSWER_REQUIREMENTS, tail
        positions.append(ANSWER_REQUIREMENTS.index(tail))
    assert positions == sorted(positions) and len(set(positions)) == len(positions)
    # 条数不变（置换非追加）：十条正文＝①＋②–⑩（首条正文＝逐字稿，其余＝tail 逐字）
    assert ANSWER_REQUIREMENTS.startswith(
        _CITATION_DISCIPLINE_VERBATIM + "".join(_REQUIREMENTS_TAIL)
    )
    # 末条＝⑩（尾「。」——非末条尾字「；」体例不破）
    assert ANSWER_REQUIREMENTS.endswith(_REQUIREMENTS_TAIL[-1])
    assert not ANSWER_REQUIREMENTS.endswith("；")
    assert ANSWER_REQUIREMENTS.count("；") == 11  # ①–⑨条间分隔 9 ＋ ①内文 1 ＋ ⑧内文 1


# ---------- 3 同常量面零重叠（与 V2-101／121／124 逐字稿互斥） ----------


def test_citation_discipline_disjoint_from_v101_v121_v124() -> None:
    """验收①边界｜本票只改族⑥ `ANSWER_REQUIREMENTS`；V2-101／121／124 三票只改族⑤
    `ANSWER_DRAFT_CONTRACT`——**同常量面零重叠**（三票逐字稿与本票逐字稿全文互不为子串、
    且三票逐字稿不在本票落点）。

    V2-101 改段首、V2-121 追加中段、V2-124 追加段尾（真源方案 §五·5）——三票逐字稿皆属族⑤，
    本票逐字稿属族⑥，两常量面不相交。
    """
    for other in (_V101_VERBATIM, _V121_VERBATIM, _V124_VERBATIM):
        # ① 两票逐字稿全文互不为子串（各是一份完整独立文本，非彼此复制）
        assert other not in _CITATION_DISCIPLINE_VERBATIM
        assert _CITATION_DISCIPLINE_VERBATIM not in other
        # ② 邻票逐字稿不在本票落点（族⑥ `ANSWER_REQUIREMENTS`——三票只改族⑤）
        assert other not in ANSWER_REQUIREMENTS
    # 三票逐字稿仍在族⑤（既有面不回退——本票不动族⑤任何字面；承载位＝作答规章段 system 参）
    for other in (_V101_VERBATIM, _V121_VERBATIM, _V124_VERBATIM):
        assert other in ANSWER_DRAFT_CONTRACT
        assert other in answer_system_contract()
    # 本票逐字稿不渗入族⑤（只落族⑥单点）
    assert _CITATION_DISCIPLINE_VERBATIM not in ANSWER_DRAFT_CONTRACT
    # 族⑤去重面不破：V1 句首答案规则句群仍不在（由族⑥单点承接）
    assert "起草答案：逐条事实断言" not in ANSWER_DRAFT_CONTRACT


# ---------- 4 离线构造：EB11 `数-排1` 形 `cited=[]` 面（提示词条件化替身 × 核验真跑） ----------

# `数-排1` 形题面（EB11 `run-098e7ab2`：`eval/suite-147/results/frames/EB11-B-数-排1.json`）。
_QUESTION = "去年日产油量最高的井是哪口？"
_SUBTASK = "去年日产油量最高的井"
_WINDOW_NOTE = "召回 1 支/送窗 1 支"
# 权威排名行（窗内观察——`agg_row` 承载片段；内容逐字取自 EB11 帧）。
_OBS_CONTENT = "井号=Z-16；区块=渤中；日产油量合计（吨）=5839.63"
# 同一断言的两形：无引标（置换前合同的交付形）／带引标（本票纪律形）。
_ASSERTION_UNCITED = "去年日产油量最高的是 Z-16 井，合计 5839.63 吨。"
_ASSERTION_CITED = "去年日产油量最高的是 Z-16 井，合计 5839.63 吨[1]。"


def _obs(
    *,
    index: int = 1,
    content: str = _OBS_CONTENT,
    source: str = "agg.fct_daily_metering",
) -> dict[str, Any]:
    """窗内观察 fixture（材料面字段形：`index`／`locator.kind`／`content`／出处）。"""
    return {
        "index": index,
        "locator": {"kind": "agg_row"},
        "content": content,
        "source": source,
        "source_id": f"obs-{index}",
    }


def _state(*, draft: str = "", observations: Any = None, **over: Any) -> RunState:
    values: dict[str, Any] = {
        "run_id": "run-v109",
        "question": _QUESTION,
        "actor": "laowang",
        "draft": draft,
        "observations": [_obs()] if observations is None else observations,
    }
    values.update(over)
    return RunState(**values)


@dataclass
class _Session:
    """一次作答相位会话（剧本化 completer ＋ per-run 总线）。"""

    bus: EventBus
    completer: ScriptedCompleter
    supplements: list[dict[str, Any]] = field(default_factory=list)


@contextmanager
def _phase(completer: ScriptedCompleter) -> Any:
    """剧本化 completer（同面替身，离线零触网）＋ per-run 总线。"""
    previous = set_completer(completer)
    try:
        yield _Session(bus=EventBus(), completer=completer)
    finally:
        set_completer(previous)


# 置换前规章段（**对照面**——施工后常量已携逐字稿，故对照面须显式回置旧第 ① 条字面；与
# V2-101 `_OLD_FIRST_SENTENCE` 同款：对照＝旧合同字面，非空转）。
_LEGACY_CONTRACT = answer_system_contract().replace(
    _CITATION_DISCIPLINE_VERBATIM, _OLD_FIRST_ITEM
)


class _CitationDisciplineCompleter(ScriptedCompleter):
    """引标纪律替身（**提示词条件化**）：交付形只看**实收 system 规章段**是否携本票逐字稿。

    携（新合同）⇒ 出**带标**断言（`_ASSERTION_CITED`）；不携（置换前合同）⇒ 出**无标**断言
    （`_ASSERTION_UNCITED`）——同一替身零固定序列，分流唯一依据＝合同文本，故置换前后红→绿可
    直接对照（与 V2-101 `_AbsenceScopeCompleter` 同款机制）。`system_override`＝对照腿显式注入的
    置换前规章段（缺省＝生产装配面 `answer_system_contract()`）。
    """

    def __init__(
        self,
        script: Mapping[str, Sequence[str]],
        *,
        cited: str,
        uncited: str,
        system_override: str | None = None,
    ) -> None:
        super().__init__(script)
        self._cited = cited
        self._uncited = uncited
        self._system_override = system_override
        self.contract_texts: list[str] = []

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
        system = self._system_override
        if system is None:
            # V2-134（承载位回链）：规章段已并入 user 首入包 ⇒ 探针改收 user 面文本
            system = "\n".join(
                str(message.get("content", ""))
                for message in messages
                if message.get("role") == "user"
            )
        self.contract_texts.append(system)
        content = self._cited if _CITATION_DISCIPLINE_VERBATIM in system else self._uncited
        return ModelReply(
            content=content,
            caller=caller,
            run_id=run_id,
            prompt_tokens=1,
            completion_tokens=1,
            cached_tokens=0,
            usage_estimated=True,
        )


def _answered_state(
    completer: _CitationDisciplineCompleter,
) -> tuple[RunState, _Session]:
    """起草相位真跑（`answer()`）——返回（核验前状态，会话）。"""
    state = _state(
        subtask_results=[{"id": "s1", "question": _SUBTASK, "status": "ok"}],
    )
    with _phase(completer) as session:
        answer(state, bus=session.bus, supplements=session.supplements)
    return state, session


def test_eb11_cited_empty_before_and_after_offline() -> None:
    """验收②｜EB11 `数-排1` 形 `cited=[]` 面**离线构造**（提示词条件化替身 × 核验真跑）。

    **前（置换前合同）**：对照腿显式回置旧第 ① 条字面（`_LEGACY_CONTRACT`）⇒ 替身按「system
    规章段不携本票逐字稿」出**无引标**断言 ⇒ 交付答案文本零引标（正是 EB11 `run-098e7ab2` 真机
    缺陷面的提示词病根：`cited=[]` 的答案**正文**没有任何 `[n]`；核验面经 V2-103 扩窗后可保留该行
    并按命中支回填 `verdict.cited`——两事分列，见下）。
    **后（新合同）**：同一替身按「system 规章段携本票逐字稿」出**带引标**断言 ⇒ 交付答案文本含
    `[1]`（带标率面改善；核验面两跑同判 supported/cited——本票只抬带标率，不动核验判据）。

    **与 V2-103 叠加覆盖零支撑面**：本件判据在**提示词面**（答案正文带标率），V2-103 在**核验面**
    （无引标数字行比对域扩窗）——本件不复制 V2-103 的扩窗断言（各票面自守）。
    """
    # 前（置换前合同＝system 无本票逐字稿）：无引标断言 ⇒ 正文零引标（`[n]` 缺席）
    before = _CitationDisciplineCompleter(
        {},
        cited=_ASSERTION_CITED,
        uncited=_ASSERTION_UNCITED,
        system_override=_LEGACY_CONTRACT,
    )
    state_before, _session_before = _answered_state(before)
    assert _CITATION_DISCIPLINE_VERBATIM not in before.contract_texts[0]
    assert _OLD_FIRST_ITEM in before.contract_texts[0]
    assert state_before.draft == _ASSERTION_UNCITED  # 起草面＝无标形（置换前合同的交付形）
    assert "[1]" not in state_before.draft
    verdict_before = verify(state_before, bus=EventBus())
    # 核验面（V2-103 扩窗后）：窗内命中 ⇒ 保留＋回填 cited；**正文文本仍零引标**（提示词病根）
    assert state_before.draft == _ASSERTION_UNCITED
    assert verdict_before.cited == [1]
    assert "[1]" not in state_before.draft

    # 后（新合同＝system 携本票逐字稿）：带引标断言 ⇒ 正文含 [1]（带标率改善）
    after = _CitationDisciplineCompleter({}, cited=_ASSERTION_CITED, uncited=_ASSERTION_UNCITED)
    state_after, _session_after = _answered_state(after)
    assert _CITATION_DISCIPLINE_VERBATIM in after.contract_texts[0]
    assert state_after.draft == _ASSERTION_CITED
    assert "[1]" in state_after.draft
    verdict_after = verify(state_after, bus=EventBus())
    assert state_after.draft == _ASSERTION_CITED  # 逐字保留（不删句、不改写）
    assert verdict_after.supported == 1
    assert verdict_after.rewritten == 0
    assert verdict_after.cited == [1]
    assert verdict_after.ok is True
    # 核验判据零改（两跑同判 supported/cited）——本票只动提示词面
    assert (verdict_after.supported, verdict_after.cited) == (
        verdict_before.supported,
        verdict_before.cited,
    )
    # `cited=[]` 的**判据机制面**（引标可解析性）：`citation_chunks` 只认 ASCII 数字形引标——
    # 置换前正文零引标 ⇒ 行内零引标辖域（`cited` 只能靠 V2-103 窗内回填）；本票正文带 `[1]` ⇒
    # 引标辖域可解析（答案面自带可解析引标——`cited=[]` 帧的答案面病根消除）。
    assert citation_chunks(_ASSERTION_CITED) == [(1, _ASSERTION_UNCITED.rstrip("。"))]
    assert citation_chunks(_ASSERTION_UNCITED) == []


def test_eb11_uncited_assertion_without_window_hit_still_deleted() -> None:
    """验收②对照｜真无据形（窗内确无该记号）**仍删**——本票只抬带标率，不放松防蒙混。

    核验面判据零改（V2-103 扩窗后仍要求数值记号全等命中）：无引标断言窗内零命中 ⇒ 照删、
    `cited=[]`（pin-10「不得 `cited=[]` 且数字在场」不放宽）。本票在**起草面**以提示词纪律预防该
    形进入答案（无引标断言句不得进答案）。
    """
    fabricated = "去年日产油量最高的是 X-99 井，合计 9999.99 吨。"
    # 窗内有观察但无该记号（X-99／9999.99 全等零命中——防蒙混面）
    state = _state(
        draft=fabricated,
        observations=[_obs(content="井号=Z-16；区块=渤中；日产油量合计（吨）=5839.63")],
    )
    verdict = verify(state, bus=EventBus())
    assert state.draft == ""
    assert verdict.supported == 0
    assert verdict.rewritten == 1
    assert verdict.cited == []
    assert verdict.ok is False

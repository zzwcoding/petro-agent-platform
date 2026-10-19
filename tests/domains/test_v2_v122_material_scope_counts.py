"""V2-122 材料范围限定与计数如实（S2＋S5＋S9；并入原 V2-114）验收。

票面＝`tickets/v2/V2-122-材料范围限定与计数如实.md`（含「Kimi 评审修正」节）。验收四条：
①计数一致（池 45／窗 6 场景，交付面注记数字＝实际——三处不实形各 1 测）；②`A-正6`／`Q41` 形
离线复现（不再出现「没有任何一条材料提及」的库级否定）；③分源分栏渲染在场（多来源题材料段
分栏文本断言）；④全量闸绿（跑批面在回报）。

**边界**（票面 §边界红线）：只许动 `tools/handlers.py`（注记）／`retrieval/domain.py`（note 单点）／
`runtimev2/answering/`／`runtimev2/context/`／`runtimev2/prompts/`／对应 specs 与测试。本件不碰召回
算法、不碰 transport 帧闭世界。

**与 V2-101 的分工**（票面 Kimi 评审修正 3）：V2-101 管**首句措辞**（落 `ANSWER_DRAFT_CONTRACT`），
本票管**范围与计数**（落 `retrieval.domain.build_window_note` 注记尾）——两票逐字稿互斥不重复。
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from appv2.infra.clock import freeze
from appv2.retrieval import FAMILY_MONTHLY, RetrievalBundle
from appv2.retrieval import Observation as RetrievalObservation
from appv2.retrieval.domain import (
    NOTE_COUNT_TRUTHFUL,
    NOTE_SCOPE_DIRECTIVE,
    build_window_note,
)
from appv2.runtimev2.answering.constants import PAYLOAD_PHASE_DRAFT
from appv2.runtimev2.context import DEFAULT_MAX_OBSERVATIONS, render_materials
from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter
from appv2.runtimev2.persistence import RunStore
from appv2.runtimev2.prompts import (
    ANSWER_COVERAGE_LINE,
    ANSWER_DRAFT_CONTRACT,
    answer_system_contract,
)
from appv2.runtimev2.state import RunState
from appv2.tools import FakeRetrievalEngine
from appv2.tools.schema import (
    SEND_BUDGET_CAP,
    SEND_BUDGET_PER_SUBTASK,
    resolve_send_budget,
)
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

_V122_VERBATIM = (
    "【范围限定】你的断言与否定只对已见材料成立：不得因「未见」而断言材料中不存在；"
    "需说明「本次材料未覆盖」，不得升格为「报告/资料库未载」。",
    "【计数如实】注记中的「检索到 N 条／用进 M 条」为本次真实计数，必须与实际一致。",
)

# V2-101 首句逐字稿（**只读引用**——两票互斥断言的对照面；本票不改其落点）。
_V101_VERBATIM = (
    "缺位只锚本轮材料：写「本次材料未覆盖」，不得写「报告/资料库未载」或「没有任何一条材料提及」。"
)

# 库级否定两形（EB11 交付面病灶——本票验收②的禁形）。
_LIBRARY_NEGATION_PHRASES = ("报告/资料库未载", "没有任何一条材料提及")

# EB11 三处计数不实形（核实报告 §③-1）：（池 recalled，窗 sent，模型自称的错值）
_COUNT_SHAPES = (
    ("a_zheng6", 45, 6, 51),
    ("q41", 63, 6, 51),
    ("a_zheng2", 48, 6, 12),
)

_ROOT = Path(__file__).resolve().parents[2]


def _indices(text: str) -> list[int]:
    """渲染文本中的 `[n]` 引标序号列（块形 `[{index}]（` 抽取）。"""
    return [int(m) for m in re.findall(r"\[(\d+)\]（", text)]


def _obs(
    index: int,
    kind: str,
    *,
    content: str = "正文",
    source: str = "",
    well: str = "",
) -> dict[str, Any]:
    """观察 fixture（材料面字段形：`index`／`locator.kind`／`content`／出处）。"""
    return {
        "index": index,
        "locator": {"kind": kind},
        "content": content,
        "source": source,
        "well": well,
    }


# =====================================================================
# 1 注记尾接两条范围指令（逐字照抄＋旧段逐字零改＋单源）
# =====================================================================


def test_note_scope_and_count_directives_verbatim_tail() -> None:
    """验收①／②基底｜两条逐字稿＝票面照抄，尾接于注记串尾（旧段逐字零改）。"""
    assert NOTE_SCOPE_DIRECTIVE == _V122_VERBATIM[0]
    assert NOTE_COUNT_TRUTHFUL == _V122_VERBATIM[1]
    note = build_window_note(45, 6)
    assert note == (
        "共检索到 45 条材料，6 条用进了答案"
        "；另有 39 条已找到但未用进答案（受送入答案的数量限制）"
        "；" + _V122_VERBATIM[0]
        + "；" + _V122_VERBATIM[1]
    )


def test_note_legacy_segments_verbatim_before_tail() -> None:
    """旧段（主段／差额段／同窗段／缺位段／扩席段）逐字零改——两条指令只作尾接。"""
    note = build_window_note(
        21, 4, sources=("A", "B"), missing=("C",), extra="扩席实录"
    )
    assert note.startswith(
        "共检索到 21 条材料，4 条用进了答案"
        "；另有 17 条已找到但未用进答案（受送入答案的数量限制）"
        "；以下材料来源说法不一，各保留了代表条目：A、B"
        "；以下来源因数量限制未纳入：C"
        "；扩席实录"
    )
    assert note.endswith(_V122_VERBATIM[0] + "；" + _V122_VERBATIM[1])
    # 每票逐字稿恰一份（不重复堆叠）
    assert note.count(_V122_VERBATIM[0]) == 1
    assert note.count(_V122_VERBATIM[1]) == 1


def test_note_directives_single_source_in_domain() -> None:
    """措辞单点＝`retrieval/domain.py` 恰一处定义（消费方零副本）。"""
    for head in ("【范围限定】", "【计数如实】"):
        hits = sorted(
            path.name
            for path in (_ROOT / "appv2").rglob("*.py")
            if head in path.read_text("utf-8")
        )
        assert hits == ["domain.py"], (head, hits)
    # 段头逐字亦在 `build_window_note` 组装串内（本票落点＝注记尾，非提示词合同）
    domain_source = (_ROOT / "appv2" / "retrieval" / "domain.py").read_text("utf-8")
    assert "return note + \"；\" + NOTE_SCOPE_DIRECTIVE + \"；\" + NOTE_COUNT_TRUTHFUL" in (
        domain_source
    )


def test_v122_texts_mutually_exclusive_with_v101() -> None:
    """与 V2-101 互斥不重复：本票逐字稿不在其落点（作答规章段），其逐字稿不渗入本票落点。"""
    for line in _V122_VERBATIM:
        assert line not in _V101_VERBATIM
        assert _V101_VERBATIM not in line
        assert line not in ANSWER_DRAFT_CONTRACT
        assert line not in answer_system_contract()
    assert "【范围限定】" not in answer_system_contract()
    assert "【计数如实】" not in answer_system_contract()
    domain_source = (_ROOT / "appv2" / "retrieval" / "domain.py").read_text("utf-8")
    assert _V101_VERBATIM not in domain_source


# =====================================================================
# 2 计数一致三测（EB11 三处不实形；交付面注记数字＝实际）
# =====================================================================


def _frag(text: str, fragment_id: str, *, report: str, index: int) -> RetrievalObservation:
    section = "第一章 井基本情况"
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=0.9,
        leg="keyword",
        family=FAMILY_MONTHLY,
        fragment_id=fragment_id,
        report_id=f"rep-{index}",
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


def _count_bundle(recalled: int, sent: int) -> RetrievalBundle:
    """计数场景 bundle：池 `recalled`／窗 `sent`（注记数字由同一单点产文）。"""
    observations = [
        _frag(f"W-11 井材料第 {i} 支", f"frag-{i}", report="《A-W11井完井工程报告》", index=i)
        for i in range(1, sent + 1)
    ]
    return RetrievalBundle(
        observations=observations,
        window_note=build_window_note(recalled, sent),
        recalled=recalled,
        sent=sent,
    )


_UNDERSTAND = json.dumps(
    {
        "route": "full",
        "text": "问 W-11 井基本情况。",
        "metric_candidates": [],
        "subjects": ["W-11"],
        "terms": [],
    },
    ensure_ascii=False,
)
_SUBTASK = "W-11 井的井别与投产日"
_NO_HIT_NOTE = "无台账命中｜未绑定｜窗未定"
_ANSWER = "本次材料未覆盖 W-11 井的井别与投产日。[1]"


def _script() -> dict[str, Sequence[str]]:
    return {
        "understand": [_UNDERSTAND],
        "decision": [
            v2_decompose(
                subtask_id="s1", question=_SUBTASK, ledger_notes=_NO_HIT_NOTE, chain="knowledge"
            ),
            v2_matches(v2_knowledge_match(subtask_id="s1", question=_SUBTASK)),
        ],
        "answer": [_ANSWER],
    }


def _draft_payload(state: RunState) -> Mapping[str, Any]:
    for step in state.steps:
        payload = step.get("payload")
        if isinstance(payload, Mapping) and payload.get("phase") == PAYLOAD_PHASE_DRAFT:
            return payload
    raise AssertionError("起草步 payload 不在场")


def _answer_user_text(completer: ScriptedCompleter, turn: int = 0) -> str:
    """本轮作答 user 条**动态段**（V2-134：规章段已并入同条 ⇒ 探针剥去规章前缀再比字面）。"""
    messages = completer.messages_of("answer")[turn]
    content = next(
        (
            str(message.get("content", ""))
            for message in reversed(messages)
            if message.get("role") == "user"
        ),
        "",
    )
    return content.replace(answer_system_contract(), "", 1).lstrip("\n")


async def _run_count_shape(recalled: int, sent: int) -> tuple[ScriptedCompleter, RunState]:
    dump = v2_ledger_dump()
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = FakeRetrievalEngine(bundle=_count_bundle(recalled, sent))
    completer = ScriptedCompleter(_script())
    with freeze("2026-10-08T09:00:00"):
        runtime, _channel = v2_runtime(
            script={}, registry=v2_registry(retrieval=retrieval), completer=completer
        )
        events = await v2_run(runtime, "W-11 井的基本情况与用途？")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    return completer, RunStore().load(events[-1].data["run_id"])


async def test_count_truthful_a_zheng6_shape() -> None:
    """验收①-1｜`A-正6` 形（真池 45／真窗 6；模型自称 51）：注记与机读键皆 45/6。"""
    recalled, sent, wrong = _COUNT_SHAPES[0][1], _COUNT_SHAPES[0][2], _COUNT_SHAPES[0][3]
    completer, state = await _run_count_shape(recalled, sent)
    user = _answer_user_text(completer)
    assert "共检索到 45 条材料，6 条用进了答案" in user
    assert "51" not in user
    payload = _draft_payload(state)
    assert payload["window_note_counts"] == {"recalled": recalled, "sent": sent}
    assert payload["window_note_counts"]["recalled"] != wrong
    # 并键登记：窗面计数（window_materials）与池面计数（window_note_counts）两物各表——非同源混写
    assert payload["window_materials"]["total"] == sent
    assert payload["window_materials"]["rendered"] == sent


async def test_count_truthful_q41_shape() -> None:
    """验收①-2｜`Q41` 形（真池 63／真窗 6；模型自称 51）：注记与机读键皆 63/6。"""
    recalled, sent, wrong = _COUNT_SHAPES[1][1], _COUNT_SHAPES[1][2], _COUNT_SHAPES[1][3]
    completer, state = await _run_count_shape(recalled, sent)
    user = _answer_user_text(completer)
    assert "共检索到 63 条材料，6 条用进了答案" in user
    assert "51" not in user
    payload = _draft_payload(state)
    assert payload["window_note_counts"] == {"recalled": recalled, "sent": sent}
    assert payload["window_note_counts"]["recalled"] != wrong


async def test_count_truthful_a_zheng2_shape() -> None:
    """验收①-3｜`A-正2` 形（真池 48／真窗 6；模型自称「12 条用进」）：机读键 sent＝6。"""
    recalled, sent, wrong = _COUNT_SHAPES[2][1], _COUNT_SHAPES[2][2], _COUNT_SHAPES[2][3]
    completer, state = await _run_count_shape(recalled, sent)
    user = _answer_user_text(completer)
    assert "共检索到 48 条材料，6 条用进了答案" in user
    assert "其中 12 条" not in user
    payload = _draft_payload(state)
    assert payload["window_note_counts"] == {"recalled": recalled, "sent": sent}
    assert payload["window_note_counts"]["sent"] != wrong


def test_window_note_counts_single_source_registration() -> None:
    """Kimi 评审修正 1｜`window_note_counts` 并键登记、禁第三真源：值源＝
    `RetrievalBundle.recalled/sent`（与注记产文同一单点），键名字面全仓恰一处定义
    （`tools/handlers.py`），消费方只引常量。
    """
    literal = '"window_note_counts"'
    holders = sorted(
        path.relative_to(_ROOT).as_posix()
        for path in (_ROOT / "appv2").rglob("*.py")
        if literal in path.read_text("utf-8")
    )
    assert holders == ["appv2/tools/handlers.py"], holders
    handlers = (_ROOT / "appv2" / "tools" / "handlers.py").read_text("utf-8")
    assert handlers.count(literal) == 1
    # 读面单点（装配）＝degradation 一处；落面单点（payload）＝core 一处（皆引常量，零副本）
    degradation = (
        _ROOT / "appv2" / "runtimev2" / "answering" / "degradation.py"
    ).read_text("utf-8")
    core = (_ROOT / "appv2" / "runtimev2" / "answering" / "core.py").read_text("utf-8")
    assert degradation.count("def window_note_counts(") == 1
    assert core.count("window_note_counts(state.observations)") == 1
    # 键名常量两面各引（import＋用点；docstring 提及不计入判据——只核代码行）
    assert "from appv2.tools.handlers import WINDOW_NOTE_COUNTS_KEY" in degradation
    assert "from appv2.tools.handlers import WINDOW_NOTE_COUNTS_KEY" in core


# =====================================================================
# 3 `A-正6`／`Q41` 形库级否定消除（离线复现）
# =====================================================================


class _ScopeDirectiveCompleter(ScriptedCompleter):
    """范围指令替身（**注记条件化**）：交付话术只看**实收 user 动态段**（引擎注记块）是否携本票
    `NOTE_SCOPE_DIRECTIVE`。携（新注记）⇒ 出「本次材料未覆盖」；不携（旧注记）⇒ 出库级否定形——
    同一替身零固定序列，分流唯一依据＝注记文本，故尾接前后红→绿可直接对照。
    """

    def __init__(
        self, script: Mapping[str, Sequence[str]], *, scoped: str, library_level: str
    ) -> None:
        super().__init__(script)
        self._scoped = scoped
        self._library_level = library_level
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
        user = "\n".join(
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "user"
        )
        self.contract_texts.append(user)
        content = self._scoped if NOTE_SCOPE_DIRECTIVE in user else self._library_level
        return ModelReply(
            content=content,
            caller=caller,
            run_id=run_id,
            prompt_tokens=1,
            completion_tokens=1,
            cached_tokens=0,
            usage_estimated=True,
        )


_SCOPED_ABSENCE = "本次材料未覆盖 W-111 井的井别、所属区块油田、投产日、状态与生产定位。"
_LIBRARY_NEGATION = "没有任何一条材料提及 W-111 井的井别、所属区块油田、投产日、状态或生产定位。"
_OLD_NOTE_45 = (
    "共检索到 45 条材料，6 条用进了答案"
    "；另有 39 条已找到但未用进答案（受送入答案数量的限制）"
)


async def _run_absence_shape(recalled: int, sent: int) -> _ScopeDirectiveCompleter:
    dump = v2_ledger_dump()
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = FakeRetrievalEngine(bundle=_count_bundle(recalled, sent))
    completer = _ScopeDirectiveCompleter(
        {
            "understand": [
                json.dumps(
                    {
                        "route": "full",
                        "text": "问 W-111 井基本情况与用途。",
                        "metric_candidates": [],
                        "subjects": ["W-111"],
                        "terms": [],
                    },
                    ensure_ascii=False,
                )
            ],
            "decision": [
                v2_decompose(
                    subtask_id="s1",
                    question="W-111 井的井别与投产日",
                    ledger_notes=_NO_HIT_NOTE,
                    chain="knowledge",
                ),
                v2_matches(
                    v2_knowledge_match(subtask_id="s1", question="W-111 井的井别与投产日")
                ),
            ],
        },
        scoped=_SCOPED_ABSENCE,
        library_level=_LIBRARY_NEGATION,
    )
    with freeze("2026-10-08T09:00:00"):
        runtime, _channel = v2_runtime(
            script={}, registry=v2_registry(retrieval=retrieval), completer=completer
        )
        events = await v2_run(
            runtime, "W-111 井的基本情况与用途（井别／所属区块油田／投产状态／生产定位）？"
        )
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    state: RunState = RunStore().load(events[-1].data["run_id"])
    # 范围指令确在**模型可见**的 user 动态段（引擎注记块）——本票的收口载体
    assert NOTE_SCOPE_DIRECTIVE in _answer_user_text(completer, 0)
    assert NOTE_COUNT_TRUTHFUL in _answer_user_text(completer, 0)
    # 交付面＝本轮缺位话术；**零**库级否定（两形皆禁）
    answer = state.answer or ""
    draft = state.draft or ""
    assert "本次材料未覆盖" in answer
    assert "本次材料未覆盖" in draft
    for phrase in _LIBRARY_NEGATION_PHRASES:
        assert phrase not in answer, phrase
        assert phrase not in draft, phrase
    return completer


async def test_a_zheng6_shape_library_negation_eliminated() -> None:
    """验收②-1｜`A-正6` 形离线复现：注记携范围指令 ⇒ 交付「本次材料未覆盖」、零库级否定。"""
    await _run_absence_shape(45, 6)


async def test_q41_shape_library_negation_eliminated() -> None:
    """验收②-2｜`Q41` 形离线复现：同上（真池 63／真窗 6）。"""
    await _run_absence_shape(63, 6)


async def test_library_negation_control_when_directive_absent() -> None:
    """红→绿对照（非空转）：同一替身＋**旧注记**（无范围指令）⇒ 出库级否定——
    红→绿由注记文本唯一决定。"""
    control = _ScopeDirectiveCompleter({}, scoped=_SCOPED_ABSENCE, library_level=_LIBRARY_NEGATION)
    reply = await control.complete(
        [{"role": "user", "content": _OLD_NOTE_45}], caller="answer"
    )
    assert reply.content == _LIBRARY_NEGATION
    assert "本次材料未覆盖" not in reply.content
    # 新注记（同一替身）⇒ 本轮缺位话术
    fresh = await control.complete(
        [{"role": "user", "content": build_window_note(45, 6)}], caller="answer"
    )
    assert fresh.content == _SCOPED_ABSENCE


# =====================================================================
# 4 分源分栏（S9——多来源题材料段分栏在场）
# =====================================================================


def _report_obs(index: int, source: str, *, content: str = "") -> dict[str, Any]:
    return _obs(index, "fragment", content=content or f"{source} 片段 {index}", source=source)


def test_source_columns_present_for_multi_source() -> None:
    """验收③｜多来源题：检索族按来源分栏——块头在场、块内支序＝入栈序、组序＝首见序。"""
    rows = [
        _report_obs(1, "报告A", content="A 第一支"),
        _report_obs(2, "报告B", content="B 第一支"),
        _report_obs(3, "报告A", content="A 第二支"),
        _report_obs(4, "报告B", content="B 第二支"),
    ]
    text, meta = render_materials(rows, max_observations=DEFAULT_MAX_OBSERVATIONS)
    assert "【来源分栏】报告A" in text
    assert "【来源分栏】报告B" in text
    # 分块序＝来源首见序；块内支序＝原稳定序（只分组、不改组内序）
    assert _indices(text) == [1, 3, 2, 4]
    # 分栏不改三机检字段与 [n]（序号＝观察自带全局序号）
    assert meta["material_total"] == 4 and meta["material_rendered"] == 4
    assert meta["material_truncated"] is False


def test_source_columns_absent_for_single_source_zero_drift() -> None:
    """验收③／零漂移｜单来源（或零检索族）＝零块头（逐字与本批前一致）。"""
    single = [_report_obs(1, "报告A"), _report_obs(2, "报告A")]
    text, _ = render_materials(single, max_observations=DEFAULT_MAX_OBSERVATIONS)
    assert "【来源分栏】" not in text
    assert _indices(text) == [1, 2]


def test_source_columns_toggle_off_is_verbatim_pre_change() -> None:
    """零改证明｜`source_columns=False` ⇒ 输出逐字＝分栏前形（多来源亦不分块、
    保持信任级稳定序）。"""
    rows = [
        _report_obs(1, "报告A", content="A 第一支"),
        _report_obs(2, "报告B", content="B 第一支"),
        _report_obs(3, "报告A", content="A 第二支"),
    ]
    off, off_meta = render_materials(
        rows, max_observations=DEFAULT_MAX_OBSERVATIONS, source_columns=False
    )
    assert off == (
        "\n观察材料：\n"
        "[1]（report｜报告A）A 第一支\n"
        "[2]（report｜报告B）B 第一支\n"
        "[3]（report｜报告A）A 第二支"
    )
    assert _indices(off) == [1, 2, 3]
    assert off_meta["material_total"] == 3


def test_source_columns_do_not_change_disclosure_or_machine_fields() -> None:
    """分栏只插块头行：披露行逐字与三机检字段零改（截断场景）。"""
    rows = [_report_obs(i + 1, f"报告{i % 3}") for i in range(30)]
    text, meta = render_materials(rows, max_observations=10)
    assert (
        "\n（材料披露：检索片段共 30 支，本轮渲染前 10 支——未渲染片段不在"
        "本轮视野，不得对其断言；权威行集与台账卡已全量渲染。）" in text
    )
    assert meta["material_truncated"] is True
    assert meta["material_rendered"] == 10
    assert meta["material_total"] == 30


# =====================================================================
# 5 L1 `budget` 与 L3 帽（Kimi 评审修正 2——同源或登记两值理由）
# =====================================================================


def test_l1_l3_budget_same_source_two_values_registered() -> None:
    """Kimi 评审修正 2｜L1 `budget` 与 L3 帽**同源单点**（`tools/schema.py`）＋**两值不同物**登记：
    L1 预算＝per-call 送窗预算 `resolve_send_budget(count)`（单支＝6、上限即帽）；L3 帽＝
    `DEFAULT_MAX_OBSERVATIONS`＝`SEND_BUDGET_CAP`（导入别名）——两值非同一量、共享同一数值单点。"""
    assert SEND_BUDGET_PER_SUBTASK == 6
    assert SEND_BUDGET_CAP == 24
    assert resolve_send_budget(1) == 6  # L1 单支预算（≠ L3 帽 24）
    assert resolve_send_budget(4) == 24  # L1 预算上限＝同一帽值
    assert resolve_send_budget(99) == 24  # 上界钳制
    assert DEFAULT_MAX_OBSERVATIONS == SEND_BUDGET_CAP == 24  # L3 帽＝同一单点别名
    assert resolve_send_budget(1) != DEFAULT_MAX_OBSERVATIONS  # 两值不同物


# =====================================================================
# 6 与 V2-119 的口径不回归（分栏不改覆盖信号）
# =====================================================================


async def test_source_columns_do_not_change_coverage_signal() -> None:
    """分栏只插块头行、不改覆盖检测（V2-119 口径复跑：零支撑子问题提示行仍恰一份）。

    场景＝`A-正6` 形（题面主体 W-111、窗内只有 W-11 材料）——覆盖信号判零支撑（多来源窗
    分栏后仍零支撑，块头行的来源名不引入 W-111 记号）。
    """
    dump = v2_ledger_dump()
    wire_ledger_projection(V2LedgerPort(dump))
    rows = [
        _frag(
            "W-11 井位于渤中34-5油田，为常规定向生产井。",
            "frag-w11",
            report="《A-W11井完井工程报告》",
            index=1,
        ),
        _frag(
            "W-11 井完钻井深 2996 米，投产日期 2025-03-12。",
            "frag-w11b",
            report="《A-W11井完井工程报告》",
            index=2,
        ),
        _frag(
            "Y-21 井检泵作业周期 5.0 天。",
            "frag-y21",
            report="《Y-21井完井工程报告》",
            index=3,
        ),
    ]
    bundle = RetrievalBundle(
        observations=rows,
        window_note=build_window_note(45, 3),
        recalled=45,
        sent=3,
    )
    retrieval = FakeRetrievalEngine(bundle=bundle)
    completer = ScriptedCompleter(
        {
            "understand": [
                json.dumps(
                    {
                        "route": "full",
                        "text": "问 W-111 井基本情况。",
                        "metric_candidates": [],
                        "subjects": ["W-111"],
                        "terms": [],
                    },
                    ensure_ascii=False,
                )
            ],
            "decision": [
                v2_decompose(
                    subtask_id="s1",
                    question="W-111 井的井别与投产日",
                    ledger_notes=_NO_HIT_NOTE,
                    chain="knowledge",
                ),
                v2_matches(
                    v2_knowledge_match(subtask_id="s1", question="W-111 井的井别与投产日")
                ),
            ],
            "answer": [_SCOPED_ABSENCE],
        }
    )
    with freeze("2026-10-08T09:00:00"):
        runtime, _channel = v2_runtime(
            script={}, registry=v2_registry(retrieval=retrieval), completer=completer
        )
        events = await v2_run(
            runtime, "W-111 井的基本情况与用途（井别／所属区块油田／投产状态／生产定位）？"
        )
    assert events[-1].data["status"] == "completed"
    user = _answer_user_text(completer)
    # 多来源窗确已分栏（两来源）——分栏后覆盖信号仍判零支撑（提示行恰一份）
    assert "【来源分栏】" in user
    assert ANSWER_COVERAGE_LINE.format(id="s1") in user
    assert user.count(ANSWER_COVERAGE_LINE.format(id="s1")) == 1

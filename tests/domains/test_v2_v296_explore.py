"""V2-96 作答侧有界再探（D5，方案 A）验收——八组（票面 `tickets/v2/V2-96-作答侧有界再探.md`）。

票面测试标识逐字（`test_` 前缀为本仓 pytest 收集口径，其余逐字一致）：

1. `::parse_explore_valid_and_invalid`（闭世界/条数/必填/越界）；
2. `::answer_explore_does_not_emit_draft`（命中 explore → 零 text 帧、无草稿）；
3. `::explore_round_cap_and_force_answer`（第 2 轮仍 explore → 强制作答＋缺口文案）；
4. `::explore_fingerprint_rejects_repeat`；
5. `::fetch_section_unknown_report_rejected`（只许已见来源）；
6. `::fetch_report_truncates_and_discloses`（截断+披露逐字）；
7. 端到端（脚本化 completer）：B-正6 形「作答说不够→doc_retrieve 补到八章→再作答出 386/415/428」；
8. 预算/时长不破（≤2 轮、300s）。

真源：`docs/runtime-refactor/接手-召回全链路最终决议与运行流程-20261018.md` §五。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import fields
from typing import Any

from appv2.infra.clock import freeze
from appv2.retrieval import (
    FAMILY_MONTHLY,
    FragmentRecord,
    InMemoryFragmentLibrary,
    LocalHashEmbedder,
    RetrievalBundle,
    RetrievalEngine,
)
from appv2.retrieval import (
    Observation as RetrievalObservation,
)
from appv2.runtimev2.answering.constants import PAYLOAD_EXPLORE_KEY
from appv2.runtimev2.parsing import Explore, explore_schema_feedback, parse_explore
from appv2.runtimev2.state import (
    INTENT,
    INTENT_EXPLORE,
    INTENT_VERIFY,
    MAX_EXPLORE_ROUNDS,
    TOTAL_SECONDS,
    Budget,
    RunState,
)
from appv2.tools import (
    FETCH_REPORT,
    ToolContext,
    ToolRegistry,
)
from appv2.tools.schema import FETCH_CAP_CHARS
from tests.domains.test_v2_answering import (
    _frames,
    _obs,
    _of,
    _phase,
    _state,
)
from tests.domains.test_v2_four_phase import (
    V2_UNDERSTAND,
    V2LedgerPort,
    v2_decompose,
    v2_knowledge_match,
    v2_ledger_dump,
    v2_ledger_note,
    v2_matches,
    v2_run,
    v2_runtime,
    v2_steps,
    wire_ledger_projection,
)

# ---------- 共用件 ----------

_REPORT = "《B-渤中34-5油田躺井治理与检泵作业月报-202608》"
_REASON = "缺三、检泵作业明细表内容"
_QUERY = "W-24 井 抽油杆 断点 米数"


def _explore(*requests: dict[str, Any], reason: str = _REASON) -> str:
    return json.dumps(
        {"action": "explore", "reason": reason, "requests": list(requests)},
        ensure_ascii=False,
    )


def _frag(
    text: str,
    fragment_id: str,
    *,
    report: str = _REPORT,
    section: str | None = "三、检泵作业明细",
    report_id: str = "rep-bz345",
) -> RetrievalObservation:
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=0.9,
        leg="keyword",
        family=FAMILY_MONTHLY,
        fragment_id=fragment_id,
        report_id=report_id,
        report=report,
        library_id="lib-monthly",
        library="月报库",
        section=section,
        locator={
            "library": "月报库",
            "report": report,
            "section": section or "",
            "fragment_id": fragment_id,
        },
    )


def _bundle(*obs: RetrievalObservation) -> RetrievalBundle:
    return RetrievalBundle(
        observations=list(obs),
        window_note=f"召回 {len(obs)} 支/送窗 {len(obs)} 支",
        recalled=len(obs),
        sent=len(obs),
    )


class _QueueRetrieval:
    """按次出列检索面（末位驻留）——再探触发新召回的被控源。"""

    def __init__(self, bundles: Sequence[RetrievalBundle]) -> None:
        self._bundles = list(bundles)
        self.needs: list[Any] = []
        self.retrieve_calls = 0
        self.fetch_section_calls = 0
        self.fetch_report_calls = 0

    async def retrieve(self, need: Any) -> RetrievalBundle:
        self.retrieve_calls += 1
        self.needs.append(need)
        if len(self._bundles) > 1:
            return self._bundles.pop(0)
        return self._bundles[0]

    async def graph(self, need: Any) -> RetrievalBundle:
        return _bundle()

    async def fetch_section(
        self, report: str, section: str | None = None, *, cap_chars: int = 0
    ) -> RetrievalBundle:
        self.fetch_section_calls += 1
        return _bundle()

    async def fetch_report(self, report: str, *, cap_chars: int = 0) -> RetrievalBundle:
        self.fetch_report_calls += 1
        return _bundle()


def _explore_steps(run_id: str) -> list[dict[str, Any]]:
    """再探轮步 payload 的 `explore` 面（每轮一条）。"""
    found: list[dict[str, Any]] = []
    for row in v2_steps(run_id):
        payload = row.payload or {}
        face = payload.get(PAYLOAD_EXPLORE_KEY)
        if isinstance(face, dict) and "round" in face:
            found.append(face)
    return found


def _registry_with(retrieval: Any) -> ToolRegistry:
    from appv2.tools import FakeKnowledgeStore, FakeQueryEngine

    return ToolRegistry(
        knowledge=FakeKnowledgeStore(), query=FakeQueryEngine(), retrieval=retrieval
    )


# ---------- 1 解析：闭世界/条数/必填/越界 ----------


def test_parse_explore_valid_and_invalid() -> None:
    """组 1｜作答第二出口解析：`tool` 闭世界、每轮 1..2 条、必填、越界即拒。"""
    valid = _explore(
        {"tool": "doc_retrieve", "query": _QUERY, "anchors": ["W-24"]},
        {"tool": "fetch_section", "report_id": _REPORT, "section": "三、检泵作业明细"},
    )
    exp = parse_explore(valid)
    assert isinstance(exp, Explore)
    assert exp.reason == _REASON
    assert [item["tool"] for item in exp.requests] == ["doc_retrieve", "fetch_section"]
    assert exp.raw.strip() == valid.strip()  # requests 原文（照抄面）随定型载荷携带
    assert exp.as_payload()["requests"][0]["query"] == _QUERY

    # fetch_report 合法（max_chars 可空）
    assert parse_explore(_explore({"tool": "fetch_report", "report_id": _REPORT})) is not None

    # 越界/缺必填各形：`parse_explore` 返 None 且拒因面非空（回喂用）
    bad = [
        json.dumps({"action": "finalize", "answer": "正常答案"}, ensure_ascii=False),
        json.dumps({"action": "explore", "reason": "", "requests": [{"tool": "doc_retrieve", "query": "x"}]}, ensure_ascii=False),  # noqa: E501
        json.dumps({"action": "explore", "reason": "r", "requests": []}, ensure_ascii=False),
        json.dumps({"action": "explore", "reason": "r", "requests": [{"tool": "doc_retrieve", "query": "a"}, {"tool": "doc_retrieve", "query": "b"}, {"tool": "doc_retrieve", "query": "c"}]}, ensure_ascii=False),  # noqa: E501
        json.dumps({"action": "explore", "reason": "r", "requests": [{"tool": "sql_exec", "query": "x"}]}, ensure_ascii=False),  # noqa: E501
        json.dumps({"action": "explore", "reason": "r", "requests": [{"tool": "doc_retrieve", "query": "  "}]}, ensure_ascii=False),  # noqa: E501
        json.dumps({"action": "explore", "reason": "r", "requests": [{"tool": "fetch_section"}]}, ensure_ascii=False),  # noqa: E501
    ]
    for raw in bad:
        assert parse_explore(raw) is None, raw
    # 非 explore 形（正常答案／散文／非 JSON）＝零拒因（不误伤答案面）
    for raw in ("答案正文", "正常答案 [1]", "no json here"):
        assert parse_explore(raw) is None
        assert explore_schema_feedback(raw) == ""
    # explore 尝试但不合 schema → 拒因一句
    assert explore_schema_feedback(bad[1])
    assert "reason" in explore_schema_feedback(bad[1])
    assert "requests" in explore_schema_feedback(bad[2])


# ---------- 2 命中 explore → 零 text 帧、无草稿 ----------


async def test_answer_explore_does_not_emit_draft() -> None:
    """组 2｜作答命中 `explore` → 不落答案、零 text 帧、`next_intent="explore"`（行为面）。"""
    state = _state(observations=[_obs(1, "fragment", content="月报正文", source=_REPORT)])
    reply = _explore({"tool": "doc_retrieve", "query": _QUERY})
    with _phase(reply) as session:
        draft = session.call(state)
    frames = await _frames(session.bus)

    assert draft.segments == [] and draft.citations == [] and draft.gaps == []
    assert _of(frames, "text") == []  # 零 text 帧
    assert _of(frames, "citation") == []
    assert state.draft == "" and state.answer == ""  # 不落答案
    assert state.next_intent == INTENT_EXPLORE
    assert isinstance(state.pending_explore, dict)
    assert state.pending_explore["requests"][0]["query"] == _QUERY
    # 起草标记不在场（重入作答仍走起草段——不是收口段）
    assert not any(
        isinstance(entry, dict) and entry.get("title") == "起草答案"
        for entry in state.process_notes
    )
    # 步 payload 携 explore 意图（requests 原文）
    assert any(
        (step.get("payload") or {}).get(PAYLOAD_EXPLORE_KEY) for step in state.steps
    )


# ---------- 3 第 2 轮仍 explore → 强制作答 ----------


async def test_explore_round_cap_and_force_answer() -> None:
    """组 3｜`explore_rounds` 到顶（2）仍 explore → 强制作答；正文含「已试 N 次检索、仍缺 X」。"""
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="月报第三章检泵作业明细",
        ledger_notes=note,
        chain="knowledge",
    )
    explore = _explore({"tool": "doc_retrieve", "query": _QUERY})
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            clarify,
            v2_matches(v2_knowledge_match(subtask_id="s1", question="检泵作业明细")),
        ],
        # 三次都出 explore：第 1/2 次真执行；第 3 次（到顶后）→ 强制作答兜底正文
        "answer": [explore, explore, explore],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = _QueueRetrieval([_bundle(_frag("月报第三章检泵作业明细正文。", "frag-3"))])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script, registry=_registry_with(retrieval)
        )
        events = await v2_run(runtime, "月报第三章检泵作业明细")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    state = v2_run_store_load(run_id)
    assert state.explore_rounds == MAX_EXPLORE_ROUNDS == 2
    rounds = _explore_steps(run_id)
    assert len(rounds) == 2  # 恰 2 轮执行留痕
    assert all(face["round"] in (1, 2) for face in rounds)
    # 强制作答正文（程序兜底——模型仍出 explore 时）
    assert "已试 2 次补充检索" in (state.answer or "")
    assert "仍缺" in (state.answer or "")


def v2_run_store_load(run_id: str) -> RunState:
    from appv2.runtimev2.persistence import RunStore as V2RunStore

    return V2RunStore().load(run_id)


# ---------- 4 指纹拒重 ----------


async def test_explore_fingerprint_rejects_repeat() -> None:
    """组 4｜重复指纹（`tool`＋`query`／`report_id+section`）→ 拒、零新观察、拒因回喂。"""
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="月报第三章检泵作业明细",
        ledger_notes=note,
        chain="knowledge",
    )
    same = _explore({"tool": "doc_retrieve", "query": _QUERY})
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            clarify,
            v2_matches(v2_knowledge_match(subtask_id="s1", question="检泵作业明细")),
        ],
        "answer": [same, same, "答案：第三章检泵作业明细见材料 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = _QueueRetrieval([_bundle(_frag("月报第三章检泵作业明细正文。", "frag-3"))])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script, registry=_registry_with(retrieval)
        )
        events = await v2_run(runtime, "月报第三章检泵作业明细")
    run_id = events[-1].data["run_id"]
    rounds = _explore_steps(run_id)
    assert len(rounds) == 2
    second = next(face for face in rounds if face["round"] == 2)
    assert second["hits"] == 0  # 零新观察（拒重）
    assert second["rejected"], second
    assert "重复" in json.dumps(second["rejected"], ensure_ascii=False)
    assert retrieval.retrieve_calls == 2  # 批次一次＋第 1 轮一次；第 2 轮同参零派遣（指纹防重）
    # 拒因回喂：增量消息里逐条照抄被拒请求＋拒因
    increment = [
        message["content"]
        for message in v2_run_store_load(run_id).messages
        if "补充检索（第 2/2 次" in str(message.get("content", ""))
    ]
    assert increment and "重复" in increment[0]


# ---------- 5 fetch_section 只许已见来源 ----------


async def test_fetch_section_unknown_report_rejected() -> None:
    """组 5｜`fetch_*` 的 `report_id` 必须是窗口里出现过的来源——未见即拒（不静默）。"""
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="月报第三章检泵作业明细",
        ledger_notes=note,
        chain="knowledge",
    )
    ask_unseen = _explore({"tool": "fetch_section", "report_id": "《从未出现过的报告》"})
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            clarify,
            v2_matches(v2_knowledge_match(subtask_id="s1", question="检泵作业明细")),
        ],
        "answer": [ask_unseen, "答案：月报正文见材料 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = _QueueRetrieval([_bundle(_frag("月报第三章检泵作业明细正文。", "frag-3"))])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script, registry=_registry_with(retrieval)
        )
        events = await v2_run(runtime, "月报第三章检泵作业明细")
    assert events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    face = _explore_steps(run_id)[0]
    assert face["hits"] == 0
    assert "已见" in json.dumps(face["rejected"], ensure_ascii=False)
    assert retrieval.fetch_section_calls == 0  # 未见来源零派遣
    state = v2_run_store_load(run_id)
    assert all(
        "从未出现过的报告" not in json.dumps(row, ensure_ascii=False)
        for row in state.observations
    )


# ---------- 6 fetch_report 截断＋披露逐字 ----------


async def test_fetch_report_truncates_and_discloses() -> None:
    """组 6｜`fetch_report` 截断+披露逐字（受 `fetch_cap`）。

    Observation 形带 report/section/fragment_id（票面验收面）。
    """
    from appv2.retrieval.domain import FETCH_TRUNCATION_MARK, NOTE_FETCH_TRUNCATED

    long_text = "抽油杆断点数据行" * (FETCH_CAP_CHARS // 4)
    library = InMemoryFragmentLibrary(
        [
            FragmentRecord(
                fragment_id="frag-a",
                report_id="rep-bz345",
                report=_REPORT,
                section="一、概况",
                library_id="lib-monthly",
                library="月报库",
                family=FAMILY_MONTHLY,
                text=long_text,
            )
        ]
    )
    engine = RetrievalEngine(library=library, embedder=LocalHashEmbedder())
    bundle = await engine.fetch_report(_REPORT, cap_chars=200)
    assert bundle.window_note == NOTE_FETCH_TRUNCATED.format(
        total=len(long_text), kept=200
    )
    assert len(bundle.observations) == 1
    obs = bundle.observations[0]
    assert obs.text.endswith(FETCH_TRUNCATION_MARK)
    assert len(obs.text) <= 200 + len(FETCH_TRUNCATION_MARK)

    # 工具面：Observation 形带 report/section/fragment_id；registry 可调
    registry = _registry_with(engine)
    result = await registry.call(
        FETCH_REPORT, {"report_id": _REPORT}, ToolContext(actor="dev-u1", budget=6)
    )
    assert result.status == "ok"
    locator = result.observations[0].locator
    assert locator["report"] == _REPORT
    assert locator["fragment_id"] == "frag-a"
    assert locator["section"] == "一、概况"
    assert result.observations[-1].locator["notice_type"] == "window_note"

    # fetch_section：按节取；节空＝代表节（表格承载优先）
    section = await engine.fetch_section(_REPORT, "一、概况", cap_chars=FETCH_CAP_CHARS)
    assert len(section.observations) == 1
    empty = await engine.fetch_section(_REPORT, "不存在的节", cap_chars=FETCH_CAP_CHARS)
    assert empty.observations == []


# ---------- 7 端到端（B-正6 形） ----------


async def test_explore_end_to_end_doc_retrieve_new_recall() -> None:
    """组 7｜端到端：作答说不够→doc_retrieve 补到八章→再作答出 386/415/428（B-正6 形）。"""
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="月报第八章抽油杆断点三处米数",
        ledger_notes=note,
        chain="knowledge",
    )
    explore = _explore({"tool": "doc_retrieve", "query": "第八章 抽油杆 断点 米数"})
    answer = "第八章三处抽油杆断点分别为 386 米、415 米、428 米 [3]。"
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            clarify,
            v2_matches(v2_knowledge_match(subtask_id="s1", question="第八章断点米数")),
        ],
        "answer": [explore, answer],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = _QueueRetrieval(
        [
            _bundle(_frag("月报第一章概况正文。", "frag-1", section="一、概况")),
            _bundle(
                _frag(
                    "第八章抽油杆断点：386 米、415 米、428 米。",
                    "frag-8",
                    section="八、抽油杆断点",
                )
            ),
        ]
    )
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script, registry=_registry_with(retrieval)
        )
        events = await v2_run(runtime, "月报第八章抽油杆断点三处米数")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    state = v2_run_store_load(run_id)
    # 新召回真入 L2（八章片段在场、序号续排）
    assert any(
        str((row.get("locator") or {}).get("fragment_id")) == "frag-8"
        for row in state.observations
    )
    assert retrieval.retrieve_calls == 2  # 批次一次＋再探一次
    assert state.explore_rounds == 1
    assert state.rounds == 1  # 再探不占澄清轮
    face = _explore_steps(run_id)[0]
    assert face["round"] == 1 and face["hits"] == 1
    assert face["executed"][0]["tool"] == "doc_retrieve"
    # 新观察复用 observation 帧（不新增帧型）
    new_frames = [
        event.data
        for event in events
        if event.event == "observation" and "386" in str(event.data.get("content", ""))
    ]
    assert new_frames, [event.event for event in events]
    assert new_frames[0]["index"] == 3  # 序号续排（新观察复用 observation 帧，不新增帧型）
    # 交付面出 386/415/428
    assert "386" in (state.answer or "")
    assert "415" in (state.answer or "")
    assert "428" in (state.answer or "")
    # 追加 user 增量：头部「补充检索（第 1/2 次，还剩 1 次）」＋requests 原文
    increments = [
        str(message.get("content", ""))
        for message in state.messages
        if "补充检索（第 1/2 次" in str(message.get("content", ""))
    ]
    assert increments and "还剩 1 次" in increments[0]
    assert "第八章 抽油杆 断点 米数" in increments[0]


# ---------- 8 预算/时长不破 ----------


def test_explore_budget_and_seconds_unbroken() -> None:
    """组 8｜再探预算独立（≤2 轮、每轮 ≤2 请求）、总时长 300s 不变、Budget 键集不扩。"""
    from appv2.runtimev2.parsing import EXPLORE_REQUEST_MAX, EXPLORE_REQUEST_MIN

    assert MAX_EXPLORE_ROUNDS == 2
    assert (EXPLORE_REQUEST_MIN, EXPLORE_REQUEST_MAX) == (1, 2)
    assert TOTAL_SECONDS == 300.0
    assert Budget().seconds == 300.0
    assert len(fields(Budget)) == 7  # 七键闭世界不扩
    assert INTENT_EXPLORE in INTENT and len(INTENT) == 12
    # 越界条数照拒（3 条＝越界）
    three = _explore(
        {"tool": "doc_retrieve", "query": "a"},
        {"tool": "doc_retrieve", "query": "b"},
        {"tool": "doc_retrieve", "query": "c"},
    )
    assert parse_explore(three) is None


# ---------- 附：拒因回喂恰一次（票面任务段；非八组点名，机检补位） ----------


async def test_explore_schema_feedback_retry_once_then_force() -> None:
    """explore 尝试不合 schema → 回喂拒因恰一次；仍不合 → 强制作答（不判 failed）。"""
    invalid = json.dumps(
        {"action": "explore", "reason": "", "requests": [{"tool": "doc_retrieve", "query": "x"}]},
        ensure_ascii=False,
    )
    valid = _explore({"tool": "doc_retrieve", "query": _QUERY})
    observations = [_obs(1, "fragment", content="月报正文", source=_REPORT)]

    # ① 回喂一次后合规：恰 2 次模型调用，落 pending_explore
    state = _state(observations=list(observations))
    with _phase(invalid, valid) as session:
        draft = session.call(state)
    assert session.completer.counts()["answer"] == 2
    assert draft.segments == []
    assert state.next_intent == INTENT_EXPLORE and state.pending_explore

    # ② 两次皆不合：仍恰 2 次模型调用（不无限回喂），强制作答正文落草稿、不判 failed
    state2 = _state(observations=list(observations))
    with _phase(invalid, invalid) as session2:
        draft2 = session2.call(state2)
    frames2 = await _frames(session2.bus)
    assert session2.completer.counts()["answer"] == 2
    assert draft2.segments and "已回喂拒因恰一次仍不合" in state2.draft
    assert state2.next_intent == INTENT_VERIFY
    assert state2.pending_explore is None
    assert _of(frames2, "text")  # 强制作答正文照常逐段推

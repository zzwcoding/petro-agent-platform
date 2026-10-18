"""V2-123 材料期 vs 执行日标注（S4）——材料头两字段＋期错位注记＋材料期约束合同句。

真源：`tickets/v2/V2-123-材料期与执行日标注.md`（§逐字稿两处，施工照抄）＋
`docs/runtime-refactor/design/统筹方案-供给窗口.md` §V2-123 ＋ L0 裁定 **D-g**
（`execution_date` 时间量**经注入参**、`context` **不读时钟**）。

判据面（票面验收 1／3 的机检化）：
1. 材料头 label 追加「报表期／执行日」两字段（additive）——**缺期材料如实缺行**、
   缺执行日（缺省空串）＝材料头无执行日段；
2. 材料报表期**晚于**执行日 → 该材料块尾接期错位注记（逐字，不静默）；
3. `Q07` 形（2027-01 未来期材料 vs 2026-10-08 执行日）离线复现：未来期材料被
   **显式标期**＋期错位注记在场＋「不得据此断言执行日时点的状态或『当前』情况」
   合同句在作答规章段在场（模型面约束的可机检代理）；
4. 执行日注入链全腿覆盖（V2-123＋L0 授权扩张）：组合根 → `RunExecutor` → `LoopDeps` →
   作答／再探增量／回炉三条材料渲染腿均携「报表期／执行日／期错位注记」。
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from appv2.runtimev2.answering import answer
from appv2.runtimev2.answering.constants import DRAFT_STEP_KIND
from appv2.runtimev2.context import (
    DEFAULT_MAX_OBSERVATIONS,
    render_materials,
    report_period,
)
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.prompts import answer_system_contract
from appv2.runtimev2.prompts.constants import (
    ANSWER_DRAFT_CONTRACT,
    ANSWER_PERIOD_CONTRACT,
    CONTRACT_CONSTANT_FAMILIES,
)
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EventBus

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
_MATERIALS = _V2_DIR / "context" / "materials.py"

_EXECUTION_DATE = "2026-10-08"
# Q07 形材料（`EB11-臆造上下文归因.md` §一-3：D/34-8-202701 检泵作业明细表）——
# 报表期 2027-01 **晚于**执行日 2026-10-08。
_FUTURE_REPORT = "渤中34-8油田躺井治理与检泵作业月报-202701"
_PAST_REPORT = "B-渤中34-5油田躺井治理与检泵作业月报-202608"

# 票面 §逐字稿（施工照抄；测试侧同源引用被测常量，逐字比对）
_PERIOD_CONTRACT_VERBATIM = (
    "【材料期约束】材料报表期晚于执行日时，只能作为「该期资料」如实引用，"
    "不得据此断言执行日时点的状态或「当前」情况。"
)
_PERIOD_MISMATCH_NOTE_VERBATIM = "【材料期】该材料报表期晚于执行日——只能作为「该期资料」引用。"

_MODEL_CALLER = "answer"


def _obs(
    index: int,
    kind: str,
    *,
    content: str = "",
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


def _signature_shape(func: Any) -> tuple[tuple[str, str, bool], ...]:
    """函数签名形状（`(名, kind, 必填?)` 元组——`test_v2_context` 同款判据）。"""
    shape: list[tuple[str, str, bool]] = []
    for name, param in inspect.signature(func).parameters.items():
        required = param.default is inspect.Parameter.empty
        shape.append((name, param.kind.name, required))
    return tuple(shape)


def _payloads(state: RunState, phase: str) -> list[Mapping[str, Any]]:
    """答案面步 payload 列（按 `phase` 取值筛——本块机读面）。"""
    out: list[Mapping[str, Any]] = []
    for step in state.steps:
        payload = step.get("payload")
        if isinstance(payload, Mapping) and payload.get("phase") == phase:
            out.append(payload)
    return out


# ---------- 1 材料头两字段（additive；缺期如实缺行；缺执行日零漂移） ----------


def test_material_head_carries_period_and_execution_date() -> None:
    """行 1｜材料头 label 追加「报表期：…｜执行日：…」两段（票面验收 1）。"""
    text, meta = render_materials(
        [_obs(1, "fragment", content="Y-21　检泵（杆断）", source=_PAST_REPORT, well="W-21")],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert text == (
        "\n观察材料：\n"
        f"[1]（report｜{_PAST_REPORT}｜W-21｜报表期：2026-08｜执行日：{_EXECUTION_DATE}）"
        "Y-21　检泵（杆断）"
    )
    assert meta["material_periods"] == {"1": "2026-08"}


def test_material_head_period_day_form() -> None:
    """行 1b｜报表期支持 `-YYYYMMDD` 形（保形为 `YYYY-MM-DD`——纯字符扫描）。"""
    text, meta = render_materials(
        [_obs(2, "fragment", content="完井参数", source="A-W11井完井工程报告-20270106")],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert "｜报表期：2027-01-06｜执行日：2026-10-08）" in text
    assert meta["material_periods"] == {"2": "2027-01-06"}


def test_material_head_missing_period_row_absent() -> None:
    """行 1c｜**缺期材料如实缺行**（无报表期段、其余字段照常；票面验收 1 后半）。"""
    text, meta = render_materials(
        [_obs(3, "metric", content="日产油量（吨）：21.16", source="台账·指标", well="K12-3")],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert text == (
        "\n观察材料：\n"
        f"[3]（ledger｜台账·指标｜K12-3｜执行日：{_EXECUTION_DATE}）日产油量（吨）：21.16"
    )
    assert "报表期" not in text
    assert meta["material_periods"] == {}


def test_material_head_execution_date_absent_period_only() -> None:
    """行 1d｜执行日缺省空串＝材料头无「执行日」段（报表期段仍按名尾取；期错位比对不成立）。"""
    rows = [_obs(4, "fragment", content="正文", source=_PAST_REPORT, well="W-21")]
    default, default_meta = render_materials(rows, max_observations=DEFAULT_MAX_OBSERVATIONS)
    explicit, _ = render_materials(
        rows, max_observations=DEFAULT_MAX_OBSERVATIONS, execution_date=""
    )
    assert default == explicit
    assert default == (
        "\n观察材料：\n"
        f"[4]（report｜{_PAST_REPORT}｜W-21｜报表期：2026-08）正文"
    )
    assert "执行日" not in default
    assert _PERIOD_MISMATCH_NOTE_VERBATIM not in default
    assert default_meta["material_periods"] == {"4": "2026-08"}
    # 无期来源（台账/图谱等）＋缺执行日＝label 与本批前逐字一致（真零漂移面）
    plain, _ = render_materials(
        [_obs(5, "graph", content="图谱无锚边", source="报告A")],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert plain == "\n观察材料：\n[5]（report｜报告A）图谱无锚边"


# ---------- 2 期错位注记（确定性比对；不静默） ----------


def test_period_mismatch_note_present_for_future_period() -> None:
    """行 2｜材料报表期**晚于**执行日 → 该块尾接期错位注记（逐字；票面验收 3）。"""
    text, meta = render_materials(
        [_obs(14, "fragment", content="本月实施检泵作业 5 井次", source=_FUTURE_REPORT)],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert text == (
        "\n观察材料：\n"
        f"[14]（report｜{_FUTURE_REPORT}｜报表期：2027-01｜执行日：{_EXECUTION_DATE}）"
        "本月实施检泵作业 5 井次\n"
        f"{_PERIOD_MISMATCH_NOTE_VERBATIM}"
    )
    assert text.count(_PERIOD_MISMATCH_NOTE_VERBATIM) == 1
    assert meta["material_periods"] == {"14": "2027-01"}


def test_period_mismatch_note_absent_for_earlier_or_same_period() -> None:
    """行 2b｜**不**晚于执行日＝零注记（早于／同月／相等日／缺执行日／执行日非日期形）。"""
    earlier, _ = render_materials(
        [_obs(1, "fragment", content="八月月报", source=_PAST_REPORT)],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert _PERIOD_MISMATCH_NOTE_VERBATIM not in earlier

    # 同月（2026-10 报表期含执行日 2026-10-08）＝不晚于
    same_month, _ = render_materials(
        [_obs(1, "fragment", content="十月月报", source="月报-202610")],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert _PERIOD_MISMATCH_NOTE_VERBATIM not in same_month

    # 相等日（YYYYMMDD＝执行日）＝不晚于
    same_day, _ = render_materials(
        [_obs(1, "fragment", content="当日", source="动态-20261008")],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert _PERIOD_MISMATCH_NOTE_VERBATIM not in same_day

    # 无执行日＝无可比对锚（不猜、不注记）
    no_exec, _ = render_materials(
        [_obs(1, "fragment", content="未来期", source=_FUTURE_REPORT)],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert _PERIOD_MISMATCH_NOTE_VERBATIM not in no_exec

    # 执行日非日期形（无数字位）＝零注记（不静默造比较）
    bad_exec, _ = render_materials(
        [_obs(1, "fragment", content="未来期", source=_FUTURE_REPORT)],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date="未定",
    )
    assert _PERIOD_MISMATCH_NOTE_VERBATIM not in bad_exec


# ---------- 3 报表期解析单点（纯字符扫描；缺期空串） ----------


def test_report_period_extraction_forms() -> None:
    """行 3｜报告名尾 `-YYYYMM`／`-YYYYMMDD` → 期形；其余＝空串（如实缺行）。"""
    assert report_period(_PAST_REPORT) == "2026-08"
    assert report_period(_FUTURE_REPORT) == "2027-01"
    assert report_period("A-W11井完井工程报告-20270106") == "2027-01-06"
    assert report_period(f"《{_FUTURE_REPORT}》") == "2027-01"  # 书名号包裹＝名本体
    for missing in ("台账·指标", "报告A", "", "月报-2026", "月报-20260", "月报-202608.txt"):
        assert report_period(missing) == "", missing


def test_report_period_single_source_and_signature() -> None:
    """行 3b｜报表期解析在 runtimev2 面内**恰一处**定义（materials.py）；签名 additive。"""
    sites: list[str] = []
    for path in sorted(_V2_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                node.name == "report_period"
            ):
                sites.append(path.name)
    assert sites == ["materials.py"], sites
    assert _signature_shape(render_materials) == (
        ("observations", "POSITIONAL_OR_KEYWORD", True),
        ("max_observations", "KEYWORD_ONLY", True),
        ("anchors", "KEYWORD_ONLY", False),
        ("execution_date", "KEYWORD_ONLY", False),  # V2-123 additive 可选参（缺省空串）
    )


# ---------- 4 合同句（逐字稿；入族；规章段在场；末段不破） ----------


def test_answer_period_contract_verbatim_and_family() -> None:
    """行 4｜材料期约束合同句＝票面逐字稿，入族⑤ `answer_draft`，随作答规章段在场。"""
    assert ANSWER_PERIOD_CONTRACT == _PERIOD_CONTRACT_VERBATIM
    assert "ANSWER_PERIOD_CONTRACT" in CONTRACT_CONSTANT_FAMILIES["answer_draft"]
    contract = answer_system_contract()
    assert contract.count(ANSWER_PERIOD_CONTRACT) == 1
    assert contract.endswith(ANSWER_DRAFT_CONTRACT)  # 末段＝起草答案合同收尾（既有判据不破）
    assert "不得据此断言执行日时点的状态或「当前」情况" in contract


# ---------- 5 Q07 形端到端（离线；未来期材料不得断言「当前状态」的可机检代理） ----------


def test_q07_shape_future_period_material_is_marked_not_current() -> None:
    """行 5｜`Q07` 形：2027-01 检泵明细 vs 执行日 2026-10-08——标期＋错位注记＋合同句在场。

    `EB11-臆造上下文归因.md` §一-3 病灶＝「以 2027-01 月报断言执行日时点『当前状态』」。
    离线可机检面（零 LLM）＝①材料头把该材料标为 `报表期：2027-01｜执行日：2026-10-08`；
    ②期错位注记逐字在场（不得据以断言执行日时点状态）；③作答规章段携材料期约束合同句。
    """
    text, meta = render_materials(
        [
            _obs(
                14,
                "fragment",
                content="Y-21　检泵（杆断）　486　5.0　56.4",
                source=_FUTURE_REPORT,
            ),
            _obs(
                15,
                "fragment",
                content="本月实施检泵作业 5 井次",
                source=_FUTURE_REPORT,
            ),
        ],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    # ① 未来期被显式标期（不再是无期的「材料」）
    assert "｜报表期：2027-01｜执行日：2026-10-08）" in text
    # ② 期错位注记逐字在场（逐支各一条——两支未来期材料）
    assert text.count(_PERIOD_MISMATCH_NOTE_VERBATIM) == 2
    assert meta["material_periods"] == {"14": "2027-01", "15": "2027-01"}
    # ③ 作答规章段携材料期约束（模型面「不得据此断言执行日时点状态」）
    assert ANSWER_PERIOD_CONTRACT in answer_system_contract()
    # 对照：同形材料若报表期不晚于执行日 → 零错位注记（判据有判别力）
    control, _ = render_materials(
        [_obs(14, "fragment", content="Y-21　检泵（杆断）　486　5.0　56.4", source=_PAST_REPORT)],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert _PERIOD_MISMATCH_NOTE_VERBATIM not in control


def test_answer_injects_execution_date_into_material_head() -> None:
    """行 5b｜`answer` 的 `execution_date` 注入参透传到材料段＋答案步 payload 机读键。"""
    state = RunState(
        run_id="run-v123-01",
        question="Y-21 这口躺了几天了？啥时候能扶起来？",
        actor="laowang",
        observations=[
            _obs(
                14,
                "fragment",
                content="Y-21　检泵（杆断）　486　5.0　56.4",
                source=_FUTURE_REPORT,
            )
        ],
    )
    completer = ScriptedCompleter({_MODEL_CALLER: ["结论：见材料 [14]。"]})
    previous = set_completer(completer)
    try:
        answer(
            state,
            bus=EventBus(),
            max_observations=DEFAULT_MAX_OBSERVATIONS,
            execution_date=_EXECUTION_DATE,
        )
    finally:
        set_completer(previous)

    window = str(state.messages[-1]["content"])
    assert "｜报表期：2027-01｜执行日：2026-10-08）" in window
    assert _PERIOD_MISMATCH_NOTE_VERBATIM in window
    payload = _payloads(state, "draft")[0]
    assert payload["material_periods"] == {"14": "2027-01"}
    assert DRAFT_STEP_KIND  # 步型单点在场（防扫描空转）


# ---------- 6 生产链：组合根 → RunExecutor → LoopDeps → 作答相位 → 材料头 ----------


async def test_execution_date_reaches_material_head_through_executor() -> None:
    """行 6｜生产链证据（编排侧）：`RunExecutor(execution_date=…)` → `LoopDeps` → 作答相位 →
    材料头「报表期／执行日」两段＋期错位注记（零 LLM 剧本化端到端）。"""
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
        wire_ledger_projection,
    )
    from tests.domains.test_v2_v296_explore import (
        _bundle,
        _frag,
        _QueueRetrieval,
        _registry_with,
    )

    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="月报检泵作业明细",
        ledger_notes=note,
        chain="knowledge",
    )
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            clarify,
            v2_matches(v2_knowledge_match(subtask_id="s1", question="检泵作业明细")),
        ],
        "answer": ["答案：见材料 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    retrieval = _QueueRetrieval(
        [_bundle(_frag("Y-21　检泵（杆断）　486　5.0　56.4", "frag-3", report=_FUTURE_REPORT))]
    )
    runtime, completer = v2_runtime(
        script=script,
        registry=_registry_with(retrieval),
        execution_date=_EXECUTION_DATE,
    )
    events = await v2_run(runtime, "月报检泵作业明细")
    assert events[-1].data["status"] == "completed"

    calls = completer.messages_of("answer")
    assert calls, "作答相位零模型调用——链路未达"
    prompt = "\n".join(str(message["content"]) for message in calls[-1])
    assert "｜报表期：2027-01｜执行日：2026-10-08）" in prompt
    assert _PERIOD_MISMATCH_NOTE_VERBATIM in prompt


def test_create_app_resolves_execution_date_once_from_today() -> None:
    """行 6b｜组合根**只解析一次** `today`：同一值既喂 §A `{today}` 又作 `execution_date`
    （单一真源；防 §A 与材料头两版并存——EB11 §五-5）。"""
    from datetime import date as _date

    from appv2.api import app as app_module
    from appv2.api.app import create_app
    from appv2.runtimev2.gateway_adapter import ScriptedCompleter

    today_calls: list[int] = []

    def _today() -> _date:
        today_calls.append(1)
        return _date(2026, 10, 8)

    monkey = {
        "compose_production_registry": lambda **kw: object(),
        "compose_production_ledger_dump": lambda **kw: (lambda: {}),
        "compose_production_watermark": lambda **kw: (lambda: None),
        "compose_production_data_wells": lambda **kw: (lambda: []),
        "compose_production_field_instances": lambda **kw: None,
        "compose_production_guide_text": lambda **kw: (
            "§A 窗词锚定（执行日 " + kw["today"]().isoformat() + "）"
        ),
    }
    saved = {name: getattr(app_module, name) for name in monkey}
    for name, replacement in monkey.items():
        setattr(app_module, name, replacement)
    try:
        app = create_app(
            db=object(),  # type: ignore[arg-type]  # 组合根只透传（本测不触库）
            completer=ScriptedCompleter({}),
            today=_today,
        )
    finally:
        for name, original in saved.items():
            setattr(app_module, name, original)

    executor = app.state.agent_runtime._executor
    assert today_calls == [1], today_calls  # 只解析一次（不重复读钟）
    assert executor._execution_date == "2026-10-08"
    assert executor._guide_text == "§A 窗词锚定（执行日 2026-10-08）"  # §A 与材料头同值


def test_create_app_execution_date_passthrough_additive() -> None:
    """行 6c｜非生产装配（registry 注入）：`execution_date` 显式透传；缺省空串＝零漂移。"""
    from appv2.api.app import create_app
    from appv2.runtimev2.gateway_adapter import ScriptedCompleter

    default_app = create_app(
        db=object(),  # type: ignore[arg-type]
        registry=object(),  # type: ignore[arg-type]
        completer=ScriptedCompleter({}),
    )
    assert default_app.state.agent_runtime._executor._execution_date == ""

    explicit_app = create_app(
        db=object(),  # type: ignore[arg-type]
        registry=object(),  # type: ignore[arg-type]
        completer=ScriptedCompleter({}),
        execution_date=_EXECUTION_DATE,
    )
    assert explicit_app.state.agent_runtime._executor._execution_date == _EXECUTION_DATE


# ---------- 7 全腿覆盖：再探增量材料段／回炉材料段（L0 授权扩张） ----------


def test_explore_increment_material_head_carries_execution_date() -> None:
    """行 7｜再探增量材料段同携「报表期／执行日／期错位注记」（`explore_increment` 单点）。"""
    from appv2.runtimev2.orchestration.explore import explore_increment

    state = RunState(
        run_id="run-v123-explore",
        question="月报检泵作业明细",
        actor="laowang",
    )
    text = explore_increment(
        state,
        exp={"raw": ""},
        requests=[{"tool": "doc_retrieve", "query": "检泵作业明细"}],
        executed=[{"tool": "doc_retrieve", "status": "ok", "observations": 1}],
        rejected=[],
        appended=[
            _obs(
                14,
                "fragment",
                content="Y-21　检泵（杆断）　486　5.0　56.4",
                source=_FUTURE_REPORT,
                well="Y-21",
            )
        ],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
        execution_date=_EXECUTION_DATE,
    )
    assert "｜报表期：2027-01｜执行日：2026-10-08）" in text
    assert _PERIOD_MISMATCH_NOTE_VERBATIM in text
    # 对照：缺执行日（缺省）＝增量材料段无执行日段、零注记（零漂移面）
    plain = explore_increment(
        state,
        exp={"raw": ""},
        requests=[{"tool": "doc_retrieve", "query": "检泵作业明细"}],
        executed=[],
        rejected=[],
        appended=[
            _obs(
                14,
                "fragment",
                content="Y-21　检泵（杆断）　486　5.0　56.4",
                source=_FUTURE_REPORT,
                well="Y-21",
            )
        ],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert "执行日" not in plain and _PERIOD_MISMATCH_NOTE_VERBATIM not in plain


def test_repair_materials_head_carries_execution_date() -> None:
    """行 7b｜回炉材料段同携「报表期／执行日／期错位注记」（`run_repair` 真调用＋prompt 取证）。"""
    import json

    from appv2.runtimev2.orchestration.constants import PAYLOAD_REPAIR_REQUEST_KEY
    from appv2.runtimev2.orchestration.repair import run_repair

    state = RunState(
        run_id="run-v123-repair",
        question="Y-21 这口躺了几天了？",
        actor="laowang",
        draft="Y-21 井日产油量为 99.5 吨[14]。",
        observations=[
            _obs(
                14,
                "fragment",
                content="Y-21　检泵（杆断）　486　5.0　56.4",
                source=_FUTURE_REPORT,
                well="Y-21",
            )
        ],
    )
    completer = ScriptedCompleter(
        {"answer": [json.dumps({"lines": [{"index": 1, "action": "drop"}]})]}
    )
    previous = set_completer(completer)
    try:
        run_repair(state, execution_date=_EXECUTION_DATE)
    finally:
        set_completer(previous)

    faces = [
        step["payload"]
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and PAYLOAD_REPAIR_REQUEST_KEY in step["payload"]
    ]
    assert faces, "回炉步未落账——链路未达"
    prompt = str(faces[0][PAYLOAD_REPAIR_REQUEST_KEY]["prompt"])
    assert "｜报表期：2027-01｜执行日：2026-10-08）" in prompt
    assert _PERIOD_MISMATCH_NOTE_VERBATIM in prompt


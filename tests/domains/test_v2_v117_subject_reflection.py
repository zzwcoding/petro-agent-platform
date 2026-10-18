"""V2-117 主体反思与下游加权 验收（票面＝`tickets/v2/V2-117-主体反思与下游加权.md`）。

四条验收逐条机检：

1. `NQ-M8` 形离线复现（34-8 题面 ＋ 只召回 34-5 材料 ⇒ 不得用 W-41 作答、如实说「本主体未
   覆盖」）——`test_nq_m8_shape_*`；
2. 跨主体对照题（C-正3 未点名主体／D-诱14 点名 34-5 分源列明）不受损——`test_cross_subject_*`；
3. `subject_reflection` 落状态位与 step payload——`test_reflect_and_record_*`；
4. 下游三处加权各自单点：检索排序提权（`promote_subject_hits`）／L3 送窗席位（主体保底席）／
   核验归属（件四主体扩面）——`test_retrieval_*`／`test_l3_*`／`test_subject_attribution_*`。

另钉 Kimi 评审修正 1（调用点不得跨相位直引：反思函数落 orchestration，execution 不 import
clarification）——`test_reflection_call_site_not_cross_phase`。
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from appv2.retrieval import FragmentRecord, Hit
from appv2.retrieval.domain import enriched_index_text, promote_subject_hits
from appv2.runtimev2.context import render_materials
from appv2.runtimev2.orchestration.constants import PAYLOAD_SUBJECT_REFLECTION_KEY
from appv2.runtimev2.orchestration.subjects import (
    reflect_and_record,
    reflect_subjects,
    subject_needles,
)
from appv2.runtimev2.state import (
    SUBJECT_FOREIGN,
    SUBJECT_MATCH,
    SUBJECT_UNKNOWN,
    RunState,
)
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.verification import (
    PAYLOAD_FIELD_MISMATCH_KEY,
    PAYLOAD_SUBJECT_MISMATCH_KEY,
    PAYLOAD_ZERO_DELIVERY_KEY,
    verify,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

# NQ-M8 形两来源（真机帧逐字：34-8 侧为本题主体，34-5 侧为错源）
_SOURCE_34_8 = "《渤中34-8油田躺井治理与检泵作业月报-202701》"
_SOURCE_34_5 = "《B-渤中34-5油田躺井治理与检泵作业月报-202608》"


def _obs(
    index: int,
    *,
    content: str,
    source: str,
    kind: str = "fragment",
    well: str | None = None,
) -> dict[str, Any]:
    """观察 fixture（材料面字段形：`index`／`locator.kind`／`content`／`source`／`well`）。"""
    row: dict[str, Any] = {
        "index": index,
        "locator": {"kind": kind, "report": source},
        "content": content,
        "source": source,
        "source_id": f"frag-{index}",
    }
    if well is not None:
        row["well"] = well
    return row


def _state(**over: Any) -> RunState:
    values: dict[str, Any] = {"run_id": "run-v117", "actor": "laowang"}
    values.update(over)
    return RunState(**values)


def _seat_indices(text: str) -> list[int]:
    """渲染文本中的 `[n]` 引标序号列（块形 `[{index}]（` 抽取——确定性）。"""
    seats: list[int] = []
    cursor = 0
    while True:
        found = text.find("[", cursor)
        if found < 0:
            return seats
        end = text.find("]（", found)
        if end < 0:
            return seats
        token = text[found + 1 : end]
        if token.isdigit():
            seats.append(int(token))
        cursor = end + 1


# ══════════ 1 主体反思判据（逐来源：属／不属／未知） ══════════


def test_reflect_subjects_per_source_verdicts() -> None:
    """验收 3｜逐来源反思判值：属（题面主体命中）／不属（自带其它主体）／未知（无主体面）。

    判据面＝来源的报告名／油田标签／井号与题面主体的一致性（确定性、零语义）；判据本体＝
    `appv2.text_tokens` 边界／全等 ＋ `appv2.tools` 取词单点。
    """
    state = _state(
        question="Y-41 井本月抽油杆断裂躺井并加装气锚——真实状态如何？",
        subjects=("Y-41",),
    )
    observations = [
        _obs(
            1,
            content="Y-41 井气锁（套压高）2027-01-06，已排 2 月上旬气锚加装",
            source=_SOURCE_34_8,
        ),
        _obs(2, content="W-41 井光杆密封盒刺漏，属光杆密封盒刺漏类预警", source=_SOURCE_34_5),
        _obs(3, content="本制度规定月报编制与报送要求", source="《制度文件-2026》"),
    ]
    result = reflect_subjects(state, observations)

    assert result == {
        _SOURCE_34_8: SUBJECT_MATCH,
        _SOURCE_34_5: SUBJECT_FOREIGN,
        "《制度文件-2026》": SUBJECT_UNKNOWN,
    }
    # 逐来源聚合：同源多支取最强命中（属 ＞ 不属 ＞ 未知）
    merged = reflect_subjects(
        state,
        [
            _obs(1, content="W-41 井光杆密封盒刺漏", source=_SOURCE_34_5),
            _obs(2, content="Y-41 井气锁 2027-01-06", source=_SOURCE_34_5),
        ],
    )
    assert merged == {_SOURCE_34_5: SUBJECT_MATCH}

    # 题面主体面：`state.subjects` 归一形过取词单点；空 subjects ⇒ 空针（审静默——不误伤）
    assert subject_needles(state) == ("Y-41",)
    silent = reflect_subjects(
        _state(question="两口欠注井分别是什么原因、什么对策？", subjects=()),
        observations,
    )
    assert set(silent.values()) == {SUBJECT_UNKNOWN}


def test_reflect_and_record_state_and_step_payload() -> None:
    """验收 3｜结果落状态位（additive）＋最近一步 payload（`subject_reflection` 键）。"""
    state = _state(
        question="Y-41 井本月真实状态？",
        subjects=("Y-41",),
        observations=[
            _obs(1, content="W-41 井光杆密封盒刺漏", source=_SOURCE_34_5),
            _obs(2, content="Y-41 井气锁 2026-12-30", source=_SOURCE_34_8),
        ],
        steps=[{"seq": 1, "step": "execute", "payload": {"phase": "execution"}}],
    )
    result = reflect_and_record(state)

    assert state.subject_reflection == result
    assert result == {_SOURCE_34_5: SUBJECT_FOREIGN, _SOURCE_34_8: SUBJECT_MATCH}
    assert state.steps[-1]["payload"][PAYLOAD_SUBJECT_REFLECTION_KEY] == result
    # 零步／步 payload 形态不合 ⇒ 如实跳过（不发明步、不炸）
    bare = _state(question="Y-41 井本月真实状态？", subjects=("Y-41",))
    assert reflect_and_record(bare) == {}
    assert bare.subject_reflection == {}


def test_reflection_call_site_not_cross_phase() -> None:
    """Kimi 评审修正 1｜调用点不得跨相位直引：反思落 orchestration、execution 不引 clarification。

    `execution/core.py` 曾拟直引 clarification 抽取值（违 R1 `allow_indirect_imports=false`）；
    修法＝反思函数落 `orchestration.subjects`（本块调相位公开入口＋读全状态的唯一组合面）。
    """
    execution_dir = _REPO_ROOT / "appv2" / "runtimev2" / "execution"
    imported: set[str] = set()
    for path in sorted(execution_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
    assert not [
        module
        for module in imported
        if module == "appv2.runtimev2.clarification"
        or module.startswith("appv2.runtimev2.clarification.")
    ], "execution 直引 clarification（违 R1）"

    subjects_module = _REPO_ROOT / "appv2" / "runtimev2" / "orchestration" / "subjects.py"
    tree = ast.parse(subjects_module.read_text(encoding="utf-8"))
    defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert {"reflect_subjects", "reflect_and_record", "subject_needles"} <= defined


# ══════════ 2 验收 1：NQ-M8 形（错源顶替 ⇒ 拒收 ⇒ 本主体未覆盖兜底） ══════════


def test_nq_m8_shape_cross_subject_line_rejected_with_fallback() -> None:
    """验收 1｜NQ-M8 形离线复现：34-8 题面（题眼 Y-41）＋只召回 34-5 材料 ⇒ 不得用 W-41 作答。

    交付面只剩标题＋兜底正证据声明（「本主体未覆盖（题眼所辖：Y-41）——本轮窗内材料均属
    渤中34-5油田」）；机读面：`subject_attribution_mismatch` 与 `zero_delivery_fallback` 在场。
    """
    observations = [
        _obs(
            1,
            content="W-41 井光杆密封盒刺漏，预警类型：光杆密封盒刺漏；首次发现 2026-08-12",
            source=_SOURCE_34_5,
        )
    ]
    question = "Y-41 井本月抽油杆在第 41 根处断裂躺井并加装气锚——给出 Y-41 井在报告中的真实状态。"
    heading = "一、Y-41 井真实状态"
    cross_subject = "- 该井本月属光杆密封盒刺漏类预警，首次发现 2026-08-12 [1]。"
    state = _state(
        question=question,
        subjects=("Y-41",),
        draft="\n".join([heading, cross_subject]),
        observations=observations,
    )
    state.subject_reflection = reflect_subjects(state)

    verdict = verify(state, bus=EventBus())

    # 拒收（删句族处置）＋零交付兜底（V2-106 兜底面复用——本票不重复兜底，只扩判据面）
    assert cross_subject not in state.draft
    assert state.draft.splitlines()[0] == heading
    assert "本主体未覆盖" in state.draft
    assert "Y-41" in state.draft  # 兜底声明的题眼所辖主体面（V2-117 `_scope_text` 回落）
    assert "渤中34-5油田" in state.draft  # 被拒材料自带油田（已试什么）
    assert verdict.rewritten == 1 and verdict.supported == 0

    payload = _step_payload(state)
    assert payload[PAYLOAD_SUBJECT_MISMATCH_KEY] == [1]
    assert payload[PAYLOAD_FIELD_MISMATCH_KEY] == []
    assert payload[PAYLOAD_ZERO_DELIVERY_KEY] is True

    # 对照面：题面主体材料在位（34-8 侧承载 Y-41）⇒ 不拒收（不误伤——判据只咬主体不一致）
    aligned = _state(
        question=question,
        subjects=("Y-41",),
        draft="\n".join([heading, "- 该井气锁（套压高），已排 2 月上旬气锚加装 [1]。"]),
        observations=[
            _obs(1, content="Y-41 功图“气锁”特征（套压高）2027-01-06", source=_SOURCE_34_8)
        ],
    )
    aligned.subject_reflection = reflect_subjects(aligned)
    aligned_verdict = verify(aligned, bus=EventBus())
    assert aligned_verdict.rewritten == 0
    assert _step_payload(aligned)[PAYLOAD_SUBJECT_MISMATCH_KEY] == []


def test_nq_m8_shape_mixed_line_any_aligned_not_rejected() -> None:
    """验收 1 收窄面｜混引不误伤：本行被引里**有一支**判「属」⇒ 不拒（跨主体对照题红线）。"""
    observations = [
        _obs(1, content="Y-41 井气锁 2027-01-06", source=_SOURCE_34_8),
        _obs(2, content="W-41 井光杆密封盒刺漏", source=_SOURCE_34_5),
    ]
    state = _state(
        question="Y-41 井本月真实状态？",
        subjects=("Y-41",),
        draft="对照：Y-41 侧气锁 2027-01-06 [1]；34-5 侧近号井 W-41 光杆密封盒刺漏 [2]。",
        observations=observations,
    )
    state.subject_reflection = reflect_subjects(state)
    verdict = verify(state, bus=EventBus())

    assert verdict.rewritten == 0
    assert _step_payload(state)[PAYLOAD_SUBJECT_MISMATCH_KEY] == []


def test_subject_attribution_rejects_unknown_only_source_untouched() -> None:
    """验收 1 审静默面｜泛制度类来源（判值「未知」）不作拒收依据（不误伤）。"""
    state = _state(
        question="Y-41 井本月真实状态？",
        subjects=("Y-41",),
        draft="月报编制要求见制度 [1]。",
        observations=[
            _obs(1, content="本制度规定月报编制与报送要求", source="《制度文件-2026》")
        ],
    )
    state.subject_reflection = reflect_subjects(state)
    assert state.subject_reflection == {"《制度文件-2026》": SUBJECT_UNKNOWN}
    verdict = verify(state, bus=EventBus())
    assert verdict.rewritten == 0
    assert _step_payload(state)[PAYLOAD_SUBJECT_MISMATCH_KEY] == []


# ══════════ 3 验收 2：跨主体对照题不受损（C-正3／D-诱14 形） ══════════


def test_cross_subject_c_zheng3_no_named_subject_silent() -> None:
    """验收 2｜C-正3 形（题面未点名主体：两油田四井并列）：空针 ⇒ 审静默、分源列明不受损。"""
    observations = [
        _obs(
            1,
            content="Y-24 井层间矛盾型欠注：I 层吸水占全井 58%、III 层仅 12%",
            source=_SOURCE_34_8,
        ),
        _obs(
            2,
            content="W-51 井层间矛盾，吸水剖面严重不均；I 层吸水 62%",
            source=_SOURCE_34_5,
        ),
    ]
    draft = "\n".join(
        [
            "**两口欠注井分别是什么原因、什么对策**",
            "两份报告各自给出原因初判——下面按来源分别列出：",
            "- 《渤中34-8…》Y-24 井：层间矛盾型欠注 [1]。",
            "- 《B-渤中34-5…》W-51 井：层间矛盾型欠注 [2]。",
        ]
    )
    state = _state(question="两口欠注井分别是什么原因、什么对策？", subjects=(), draft=draft,
                   observations=observations)
    state.subject_reflection = reflect_subjects(state)
    verdict = verify(state, bus=EventBus())

    assert state.subject_reflection == {
        _SOURCE_34_8: SUBJECT_UNKNOWN,
        _SOURCE_34_5: SUBJECT_UNKNOWN,
    }
    assert state.draft.splitlines()[1:] == draft.splitlines()[1:]  # 分源列明逐字保留
    assert verdict.rewritten == 0
    assert _step_payload(state)[PAYLOAD_SUBJECT_MISMATCH_KEY] == []


def test_cross_subject_d_you14_named_field_sources_aligned() -> None:
    """验收 2｜D-诱14 形（点名「渤中34-5油田」＋W-56）：34-5 侧来源判「属」⇒ 不拒收。"""
    question = (
        "渤中34-5 油田三季度哪几口注水井欠注？每口的配注、实注、欠注率分别是多少？"
        "W-56 井 8 月停注 6 天，它算不算欠注？"
    )
    observations = [
        _obs(
            1,
            content="三季度 14 口注水井中 2 口欠注：W-51 62%/28%/10%、W-52 54%/33%/13%",
            source="《C-渤中34-5油田三季度注水调整与生产运行分析》",
        ),
        _obs(
            2,
            content="W-56 井 8 月停注 6 天，按制度不计欠注",
            source="《C-渤中34-5油田三季度注水调整与生产运行分析》",
        ),
    ]
    draft = "\n".join(
        [
            "**欠注井识别**",
            "三季度渤中 34-5 油田 14 口注水井中有 2 口欠注，分别为 W-51 和 W-52 [1]。",
            "W-56 井 8 月停注 6 天，按制度不计欠注 [2]。",
        ]
    )
    state = _state(
        question=question, subjects=("渤中34-5油田",), draft=draft, observations=observations
    )
    state.subject_reflection = reflect_subjects(state)
    verdict = verify(state, bus=EventBus())

    assert state.subject_reflection == {
        "《C-渤中34-5油田三季度注水调整与生产运行分析》": SUBJECT_MATCH
    }
    assert verdict.rewritten == 0
    assert state.draft.splitlines()[1:] == draft.splitlines()[1:]


def test_cross_subject_two_fields_four_wells_both_aligned() -> None:
    """验收 2｜题面点名两主体（两油田四井并列）：两来源各判「属」⇒ 双源并列可答。"""
    state = _state(
        question="渤中34-8 油田的 Y-24 井与渤中34-5 油田的 W-51 井各自欠注原因是什么？",
        subjects=("渤中34-8油田", "渤中34-5油田"),
        draft=(
            "Y-24 井：层间矛盾型欠注 [1]；W-51 井：层间矛盾型欠注 [2]。"
        ),
        observations=[
            _obs(1, content="Y-24 井层间矛盾型欠注：III 层仅 12%", source=_SOURCE_34_8),
            _obs(2, content="W-51 井层间矛盾，I 层吸水 62%", source=_SOURCE_34_5),
        ],
    )
    state.subject_reflection = reflect_subjects(state)
    assert set(state.subject_reflection.values()) == {SUBJECT_MATCH}
    verdict = verify(state, bus=EventBus())
    assert verdict.rewritten == 0
    assert _step_payload(state)[PAYLOAD_SUBJECT_MISMATCH_KEY] == []


def test_subject_reflection_all_fields_sentinel_silent() -> None:
    """验收 2｜「都要（分源对比）」哨兵＝多主体并列、无单一主体面 ⇒ 空针审静默（不阻断并列）。"""
    state = _state(
        question="三季度欠注井的配注与实注分别是多少？",
        subjects=("__all_fields__",),
        observations=[_obs(1, content="W-51 配注 80 实注 27", source=_SOURCE_34_5)],
    )
    assert subject_needles(state) == ()
    assert reflect_subjects(state) == {_SOURCE_34_5: SUBJECT_UNKNOWN}


# ══════════ 4 下游加权（1）检索排序：主体命中候选分池序内提权 ══════════


def _hit(fragment_id: str, family: str, text: str, *, report: str = "报告A") -> Hit:
    fragment = FragmentRecord(
        fragment_id=fragment_id,
        report_id=report,
        report=report,
        section=None,
        library_id="lib",
        library="lib",
        family=family,
        text=text,
    )
    return Hit(fragment=fragment, score=1.0, leg="keyword")


def test_retrieval_promote_subject_hits_within_family_pool() -> None:
    """验收 4a｜检索排序：主体命中候选在**分池序内**提权（稳定分区、不改融合序公式）。

    族出场序不动（monthly 先于 dynamic）；族内命中者前移、其余保持原相对序；tokens 空＝原样。
    """
    ranked = [
        (_hit("m1", "monthly", "泛片段一"), 0.9),
        (_hit("m2", "monthly", "Y-41 井气锁"), 0.8),
        (_hit("m3", "monthly", "泛片段二"), 0.7),
        (_hit("d1", "dynamic", "Y-41 井生产动态"), 0.6),
        (_hit("d2", "dynamic", "泛片段三"), 0.5),
    ]
    def text_of(hit: Hit) -> str:
        return enriched_index_text(hit.fragment)

    promoted = promote_subject_hits(ranked, ("Y-41",), text_of=text_of)
    assert [hit.fragment.fragment_id for hit, _ in promoted] == ["m2", "m1", "m3", "d1", "d2"]

    # 报告名面命中同样提权（三面任一——与题眼锚保底同判据单点）
    by_report = promote_subject_hits(
        [(_hit("m1", "monthly", "泛", report="《A-月报》"), 0.9),
         (_hit("m2", "monthly", "泛", report=_SOURCE_34_8), 0.8)],
        ("渤中34-8油田",),
        text_of=text_of,
    )
    assert [hit.fragment.fragment_id for hit, _ in by_report] == ["m2", "m1"]

    # 零漂移面：tokens 空／无命中 ⇒ 原序原对象
    assert promote_subject_hits(ranked, (), text_of=text_of) is ranked
    untouched = promote_subject_hits(ranked, ("W-999",), text_of=text_of)
    assert [hit.fragment.fragment_id for hit, _ in untouched] == ["m1", "m2", "m3", "d1", "d2"]


# ══════════ 5 下游加权（2）L3 送窗席位：主体保底席（插在题眼保底之后、来源保底之前） ══════════


def test_l3_subject_source_seat_before_generic_source_seat() -> None:
    """验收 4b｜主体来源的保底席优先于泛来源（L3 席序：④b 主体保底 → ⑤ 来源保底）。

    fixture 判别力：A 侧（index1 泛、index2 主体）＋ B 侧（index3 泛、index4 泛、index5 主体）
    ＋ C 侧（index6 泛）、帽 5。题眼保底（①）先落 index2；来源保底（⑤）按出现序只会给 B 侧
    **首个未选**＝index4；主体保底席（④b）令 B 侧的**主体命中支** index5 先占席（入窗者 5 而非 4）。
    """
    rows = [
        _obs(1, content="泛片段一", source="报告A"),
        _obs(2, content="Y-41 井气锁", source="报告A"),
        _obs(3, content="泛片段二", source="报告B"),
        _obs(4, content="泛片段三", source="报告B"),
        _obs(5, content="Y-41 井已排气锚加装", source="报告B"),
        _obs(6, content="泛片段四", source="报告C"),
    ]
    text, meta = render_materials(
        rows, max_observations=5, anchors=(("subject", "Y-41"),)
    )
    seats = _seat_indices(text)
    assert 5 in seats and 4 not in seats  # 主体保底席先于泛来源保底席
    assert len(seats) == 5 and meta["material_rendered"] == 5
    assert 2 in seats  # 题眼保底席（①）不动

    # 对照面：无主体锚（本通道零动作）⇒ 来源保底席取 B 侧首个未选 index4、index5 不进窗
    naive, _ = render_materials(
        rows, max_observations=5, anchors=(("number", "999"),)
    )
    naive_seats = _seat_indices(naive)
    assert 4 in naive_seats and 5 not in naive_seats
    # 席序面：主体保底席不占单源上限、不改总帽
    assert meta["material_total"] == 6


# ══════════ 6 下游加权（3）核验归属：件四主体扩面 ══════════


def test_subject_attribution_mismatch_field_scope_still_independent() -> None:
    """验收 4c｜两维度**分列且不互相并入**：油田归属先咬者落 `field_attribution_mismatch`；
    主体归属在**字段面不咬**时独立落 `subject_attribution_mismatch`（同拒收族、两键各有独立值源）。
    """
    # ① 字段面先咬（题面点名 34-8 油田、无井号主体）：field 键落值、subject 键空
    field_state = _state(
        question="渤中34-8 油田的修井船日合计多少天？",
        subjects=(),
        draft="- 修井机归属：渤海 302 承担 W-21，月度船日 22.5 天 [1]。",
        observations=[
            _obs(
                1,
                content="W-21、W-22 由渤海 302 修井机承担，月度船日 22.5 天",
                source=_SOURCE_34_5,
            )
        ],
    )
    field_state.subject_reflection = reflect_subjects(field_state)
    verify(field_state, bus=EventBus())
    field_payload = _step_payload(field_state)
    assert field_payload[PAYLOAD_FIELD_MISMATCH_KEY] == [1]
    assert field_payload[PAYLOAD_SUBJECT_MISMATCH_KEY] == []

    # ② 主体面独立咬（题面只点名井号 Y-41、字段面点不出油田）：subject 键落值、field 键空
    subject_state = _state(
        question="Y-41 井本月真实状态？",
        subjects=("Y-41",),
        draft="- 该井本月属光杆密封盒刺漏类预警 [1]。",
        observations=[_obs(1, content="W-41 井光杆密封盒刺漏", source=_SOURCE_34_5)],
    )
    subject_state.subject_reflection = reflect_subjects(subject_state)
    verify(subject_state, bus=EventBus())
    subject_payload = _step_payload(subject_state)
    assert subject_payload[PAYLOAD_FIELD_MISMATCH_KEY] == []
    assert subject_payload[PAYLOAD_SUBJECT_MISMATCH_KEY] == [1]


def test_subject_attribution_split_note_identity_face_spares_line() -> None:
    """验收 4c 收窄面｜行内写明来源**身份面**主体（分源说明）⇒ 不拒（同件四收窄面②）。"""
    observations = [
        _obs(1, content="W-41 井光杆密封盒刺漏", source=_SOURCE_34_5),
    ]
    state = _state(
        question="Y-41 井本月真实状态？",
        subjects=("Y-41",),
        draft="- 另注（材料为渤中34-5油田月报）：W-41 井光杆密封盒刺漏 [1]。",
        observations=observations,
    )
    state.subject_reflection = reflect_subjects(state)
    assert state.subject_reflection == {_SOURCE_34_5: SUBJECT_FOREIGN}
    verdict = verify(state, bus=EventBus())
    assert verdict.rewritten == 0
    assert _step_payload(state)[PAYLOAD_SUBJECT_MISMATCH_KEY] == []


def test_subject_attribution_silent_without_reflection() -> None:
    """验收 4c 审静默面｜`state.subject_reflection` 空（材料未到／无主体）⇒ 本闸零动作。"""
    state = _state(
        question="Y-41 井本月真实状态？",
        subjects=("Y-41",),
        draft="- 该井本月属光杆密封盒刺漏类预警 [1]。",
        observations=[_obs(1, content="W-41 井光杆密封盒刺漏", source=_SOURCE_34_5)],
    )
    verdict = verify(state, bus=EventBus())
    assert verdict.rewritten == 0
    assert _step_payload(state)[PAYLOAD_SUBJECT_MISMATCH_KEY] == []


def test_subject_attribution_data_rows_out_of_scope() -> None:
    """验收 4c 辖域面｜权威表行（`agg_row`）不入主体归属辖域（与行为 5 归属审同辖域）。

    判据面是「来源的**报告名**／油田标签／井号」——只对**文档材料来源**成立；表行来源＝表名，
    其主体归属由上游闸（单井槽位闸等）管（真机形＝`tests/domains/test_v2_f2_convergence.py`
    的 A-正8／D-诱10：题面点名主体而窗内只有 agg 行，本闸不越界咬数据行）。
    """
    state = _state(
        question="邻井 W-07 井初期日产油多少？现在呢？",
        subjects=("W-07",),
        draft="s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。",
        observations=[
            _obs(
                1,
                content="井号=N-01；日产油量（吨）=21.16",
                source="agg.fct_daily_metering",
                kind="agg_row",
            )
        ],
    )
    state.subject_reflection = reflect_subjects(state)
    assert state.subject_reflection == {"agg.fct_daily_metering": SUBJECT_FOREIGN}
    verdict = verify(state, bus=EventBus())
    assert verdict.rewritten == 0
    assert "21.16" in state.draft
    assert _step_payload(state)[PAYLOAD_SUBJECT_MISMATCH_KEY] == []


def test_reflect_subjects_other_class_only_is_unknown() -> None:
    """验收 4c 精度面｜**同类**才判「不属」：题面点井号、来源只带别类主体（另一油田名）⇒ 未知。

    井可能就属该油田，形态面判不了——保守落「未知」（审静默，不误伤）。
    """
    state = _state(question="Y-41 井本月真实状态？", subjects=("Y-41",))
    other_class = _obs(
        1,
        content="三季度注水调整与生产运行分析（无井号点名）",
        source="《C-渤中34-5油田三季度注水调整与生产运行分析》",
    )
    assert reflect_subjects(state, [other_class]) == {
        "《C-渤中34-5油田三季度注水调整与生产运行分析》": SUBJECT_UNKNOWN
    }
    # 同类（另一口井）⇒ 不属（NQ-M8 形判据面）
    same_class = _obs(1, content="W-41 井光杆密封盒刺漏", source="《B-渤中34-5油田月报-202608》")
    assert reflect_subjects(state, [same_class]) == {
        "《B-渤中34-5油田月报-202608》": SUBJECT_FOREIGN
    }
    # 油田题（题面点油田名）＋另一油田名 ⇒ 不属（同类实体面）
    field_state = _state(question="渤中34-8 油田日产油量？", subjects=("渤中34-8油田",))
    assert reflect_subjects(field_state, [other_class]) == {
        "《C-渤中34-5油田三季度注水调整与生产运行分析》": SUBJECT_FOREIGN
    }


def _step_payload(state: RunState) -> dict[str, Any]:
    """核验步 payload（相位标记＝`verify`——本块恰一条步；同 `test_v2_verification` 取法）。"""
    payloads = [
        dict(step["payload"])
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and step["payload"].get("phase") == "verify"
    ]
    assert len(payloads) == 1, f"核验步记录不唯一：{payloads}"
    return payloads[0]

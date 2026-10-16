"""context 块验收（RT-W3-02a：骨架＋六函数功能行为簇＋本块全部 4 条 pin 行）。

票面对象＝`specs/context.md`「验收测试」表第 1–12、19 行（逐字，测试标识同规格列——
`test_` 前缀为本仓 pytest 收集口径，其余逐字一致；`#` 保留规格表行序、不重编）；
第 13–18、20、21 行归 `RT-W3-02b-context.md`（本件不写）。
测试网钉＝pin-09（渲染面三落点：行 5／6／19）／pin-08（渲染帽分形面，行 4）／
pin-22（视图不改原史，行 9）／pin-30（compaction 半面，行 9）——四钉全在本票。
「钉落点对读」两行（pin-24／pin-26 不落本块）＝核实在案（本块零合同、零标记、零追加时点；
`dialogue` 写口不在本块——见 `test_ledger_load_via_tools_take_once` 尾注与测试网钉注）。

真源指针：行为 1–6／8–11＝`specs/context.md` 行为约定；渲染色字逐字稿＝
`appv2/runtime/context.py`（材料段）／`appv2/runtime/graph.py:1278-1302`（过程档案）／
`tickets/v2/V2-79d-compaction摘要化.md` §1.1／§1.2（compaction 摘要头与截数 120）；
`selected_reason` 逐字稿＝`tickets/v2/V2-61-材料承载分形渲染.md` 附 A；三来源行真源＝
`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` R-B2-05；字段形状＝`specs/state.md`。

**装载入口形＝前置核定项（未获核定）**：规格风险 5——loader 的 tools 公开面调用形未落定、
tools 装载入口形＝「阶段 5 context 施工票前置核定」（流水 43⑥）。故本件按票面「装载面只出端口＋
注入缝」施工：行 11／12 的装载语义（取一次／写回／副本／失败 fail-fast／合法空不触发失败腿）经
**注入端口**全量落绿，「经 tools 公开面」的真实现形不在本件发明（按票面停报 L0）。
"""

from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from appv2.runtimev2.context import (
    DEFAULT_DIALOGUE_VIEW_TOKENS,
    DEFAULT_MAX_OBSERVATIONS,
    PROCESS_NOTES_BUDGET,
    RESIDENT_SOURCE_ROWS,
    TRUST_AGG,
    TRUST_LEDGER,
    TRUST_REPORT,
    LedgerLoadError,
    compact_messages,
    compile_manifest,
    load_ledger_dump,
    render_materials,
    render_process_notes,
    trust_of,
    wire_ledger_projection,
)
from appv2.runtimev2.state import DIALOGUE_ORIGINS, RunState

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTEXT_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "context"

# 材料段披露行逐字（`appv2/runtime/context.py` 承载位形——迁移照抄、零改写）。
_DISCLOSURE_HEAD = "（材料披露："
# 过程档案披露行逐字（`appv2/runtime/graph.py` `_render_process_notes` 承载位形）。
_PROCESS_NOTES_DISCLOSURE = "-（过程档案摘要有界截断——已渲染 {n}/{total} 条）"
# compaction 摘要头逐字（V2-79d §1.1／§1.2——截数 120 真源 A-P5b3-13）。
_SUMMARY_HEAD = "（前情摘要——旧轮原文已压缩，完整原史在会话档案可查）"
# 装载失败稳定提示（fail-fast——行为 11；用户面帧面归发射方）。
_FAILURE_HINT = "台账投影装载失败——本轮无法取得台账材料，run 已失败收场（未带缺台账的投影续跑）"

# 合同／相位包条目标记（非对话来源——结构化标记键 `origin`，永不摘除）。
_PHASE_CONTRACT_ORIGIN = "phase_contract"


def _obs(
    index: int,
    kind: str,
    *,
    content: str = "正文",
    source: str = "",
    well: str = "",
    source_id: str = "",
    version: str | None = None,
) -> dict[str, Any]:
    """观察 fixture（材料面字段形——`index`／`locator.kind`／`source`／`well`／`content`）。"""
    return {
        "index": index,
        "locator": {"kind": kind},
        "content": content,
        "source": source,
        "well": well,
        "source_id": source_id,
        "version": version,
    }


def _indices(text: str) -> list[int]:
    """渲染文本中的 `[n]` 引标序号列（块形 `[{index}]（` 抽取）。"""
    import re

    return [int(m) for m in re.findall(r"\[(\d+)\]（", text)]


def _fragments(count: int, *, start: int = 1) -> list[dict[str, Any]]:
    return [
        _obs(start + i, "fragment", content=f"检索片段{i}", source="kb", source_id=f"kb-{i}")
        for i in range(count)
    ]


def _context_sources() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_CONTEXT_DIR.rglob("*.py"))
    ]


class _Port:
    """装载端口替身（注入缝的测试面——真实现形待核定，见文件头注）。"""

    def __init__(self, result: Mapping[str, Any] | None) -> None:
        self.result = result
        self.calls = 0

    async def fetch(self) -> Mapping[str, Any] | None:
        self.calls += 1
        return self.result


@pytest.fixture(autouse=True)
def _reset_projection_port() -> Iterator[None]:
    wire_ledger_projection(None)
    yield
    wire_ledger_projection(None)


# ---------- 1 材料段渲染形逐字迁移（行为 1——pin-09 渲染面底座） ----------


def test_material_segment_verbatim_render() -> None:
    """行 1 材料段渲染形逐字迁移：段头／块形／空段跳过／空材料「（无）」（行为 1）。"""
    text, meta = render_materials(
        [
            _obs(7, "metric", content="日产油量（吨）：21.16", source="台账·指标", well="K12-3"),
        ],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    # 段头逐字＋块形：index＝观察自带全局序号（非渲染位次）、label＝信任级｜来源｜井
    assert text == "\n观察材料：\n[7]（ledger｜台账·指标｜K12-3）日产油量（吨）：21.16"
    assert text.startswith("\n观察材料：\n")
    assert meta == {"material_truncated": False, "material_rendered": 1, "material_total": 1}

    # 空段跳过（来源/井空白串经 `.strip()` 归一后跳过——只剩信任级段）
    blank, _ = render_materials(
        [_obs(1, "graph", content="图谱无锚边", source="  ", well="")],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert "观察材料：\n[1]（report）图谱无锚边" in blank

    # `content` 缺失＝空串（现状缺省——真源 R-K-20）
    missing, _ = render_materials(
        [{"index": 2, "locator": {"kind": "term"}}], max_observations=DEFAULT_MAX_OBSERVATIONS
    )
    assert missing == "\n观察材料：\n[2]（ledger）"

    # 空材料集正文＝逐字「（无）」
    empty, empty_meta = render_materials([], max_observations=DEFAULT_MAX_OBSERVATIONS)
    assert empty == "\n观察材料：\n（无）"
    assert empty_meta == {"material_truncated": False, "material_rendered": 0, "material_total": 0}

    # 三段全空＝空括号（）：迁移照抄保留该写法，公开面无可达入口（信任级段恒非空——
    # 闭世界查表恒返三档之一）＝死分支，现状固有、迁移不修（规格行为 1 原注）。
    for kind in ("agg_row", "metric", "fragment"):
        assert trust_of({"locator": {"kind": kind}}) != ""

    # 错误契约：`index` 缺失／非整数形（观察面形态违约）→ 抛参数错误（V1 裸 KeyError 收口）
    with pytest.raises(ValueError):
        render_materials([{"locator": {"kind": "term"}}], max_observations=24)
    with pytest.raises(ValueError):
        render_materials(
            [{"index": "缺形", "locator": {"kind": "term"}}], max_observations=24
        )


# ---------- 2 信任级映射闭世界＋notice 排除（行为 2） ----------


def test_trust_mapping_closed_world() -> None:
    """行 2 十 kind 三族、异常输入落 `report`、notice 排除（行为 2）。"""
    closed = {
        "agg_row": TRUST_AGG,
        "lineage": TRUST_AGG,
        "metric": TRUST_LEDGER,
        "term": TRUST_LEDGER,
        "object": TRUST_LEDGER,
        "relation": TRUST_LEDGER,
        "family_annotation": TRUST_LEDGER,
        "fragment": TRUST_REPORT,
        "graph": TRUST_REPORT,
    }
    for kind, trust in closed.items():
        assert trust_of({"locator": {"kind": kind}}) == trust, kind
    # notice 名义入表（material 段整体排除）
    assert trust_of({"locator": {"kind": "notice"}}) == "notice"
    # 三种异常输入统一落 report（不抛错）
    assert trust_of({}) == TRUST_REPORT
    assert trust_of({"locator": {}}) == TRUST_REPORT
    assert trust_of({"locator": {"kind": "未登记"}}) == TRUST_REPORT

    # notice 排除：不进渲染文本、不计任何计数
    text, meta = render_materials(
        [
            _obs(1, "agg_row", content="合计 100"),
            _obs(2, "notice", content="窗口缺参反问（元信息）"),
        ],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert "[2]" not in text and "元信息" not in text
    assert meta == {"material_truncated": False, "material_rendered": 1, "material_total": 1}


# ---------- 3 排序＝信任级稳定序（行为 3） ----------


def test_trust_order_stable() -> None:
    """行 3 同 rank 保持入栈序、两跑同序（行为 3）。"""
    observations = [
        _obs(1, "fragment"),
        _obs(2, "metric"),
        _obs(3, "graph"),
        _obs(4, "agg_row"),
        _obs(5, "term"),
        _obs(6, "lineage"),
    ]
    text, _ = render_materials(observations, max_observations=DEFAULT_MAX_OBSERVATIONS)
    # 权威（4、6）→ 台账（2、5）→ 检索（1、3）；组内保持入栈序
    assert _indices(text) == [4, 6, 2, 5, 1, 3]
    assert render_materials(observations, max_observations=DEFAULT_MAX_OBSERVATIONS)[0] == text


# ---------- 4 分承载体预算：权威/台账全量无帽、检索族超帽才截断（行为 4——pin-08） ----------


def test_carrier_fractal_budget() -> None:
    """行 4 pin-08 渲染帽分形面（行为 4）。"""
    # 权威/台账族超帽 → 全量渲染、零披露、material_truncated=False
    authority = [
        _obs(i + 1, "agg_row", content=f"行 {i + 1}", source="agg.fct_daily_metering")
        for i in range(40)
    ]
    text, meta = render_materials(authority, max_observations=24)
    assert len(_indices(text)) == 40
    assert _DISCLOSURE_HEAD not in text
    assert meta == {"material_truncated": False, "material_rendered": 40, "material_total": 40}

    # 检索族超帽 → 只渲染帽内支、披露在场（帽只作用检索族）
    text, meta = render_materials(_fragments(30), max_observations=24)
    assert len(_indices(text)) == 24
    assert _DISCLOSURE_HEAD in text
    assert meta == {"material_truncated": True, "material_rendered": 24, "material_total": 30}


# ---------- 5 截断披露行逐字在场、未截断零残留（行为 5——pin-09 之一） ----------


def test_truncation_disclosure_line_verbatim() -> None:
    """行 5 披露行逐字＋两个计数正确；未截断零残留（行为 5）。"""
    text, meta = render_materials(_fragments(30), max_observations=10)
    assert (
        "\n（材料披露：检索片段共 30 支，本轮渲染前 10 支——未渲染片段不在"
        "本轮视野，不得对其断言；权威行集与台账卡已全量渲染。）" in text
    )
    assert meta["material_truncated"] is True and meta["material_rendered"] == 10
    # 计数与元数据一致：检索支数＝总、实渲支数＝帽
    assert meta["material_total"] == 30

    clean, clean_meta = render_materials(_fragments(3), max_observations=10)
    assert _DISCLOSURE_HEAD not in clean and "截断" not in clean
    assert clean_meta["material_truncated"] is False


# ---------- 6 Manifest 三机检字段（四态）＋selected_reason 逐字（行为 6——pin-09 之二） ----------


def test_manifest_material_fields_and_reason() -> None:
    """行 6 四态三字段逐条对＋`selected_reason` 逐字（行为 6；无 compaction 态逐字）。"""
    # 零材料步（仅生于理解步——文案恒为「理解步」）
    zero = compile_manifest([], step="understand", max_observations=24)
    assert (zero.material_total, zero.material_rendered, zero.material_truncated) == (0, 0, False)
    assert zero.selected_reason == "步骤 understand：理解步零材料渲染"

    # 全量态
    full = compile_manifest(
        [*[_obs(1, "agg_row"), _obs(2, "lineage")], *_fragments(3, start=3)],
        step="answer",
        max_observations=24,
    )
    assert (full.material_total, full.material_rendered, full.material_truncated) == (5, 5, False)
    assert full.selected_reason == (
        "步骤 answer：信任级降序稳定排序；权威 2 支全量；检索片段 3 支全量（合计入选 5/5）"
    )

    # 检索截断态
    cut = compile_manifest(_fragments(5), step="answer", max_observations=2)
    assert (cut.material_total, cut.material_rendered, cut.material_truncated) == (5, 2, True)
    assert cut.selected_reason == (
        "步骤 answer：信任级降序稳定排序；权威 0 支全量；检索片段帽 2 支截断（2/5）"
        "（合计入选 2/5）"
    )

    # 权威超帽态（帽不作用权威族）
    over = compile_manifest(
        [
            _obs(i + 1, "agg_row", content=f"行 {i + 1}")
            for i in range(30)
        ],
        step="answer",
        max_observations=24,
    )
    assert (over.material_total, over.material_rendered, over.material_truncated) == (
        30,
        30,
        False,
    )
    assert over.selected_reason == (
        "步骤 answer：信任级降序稳定排序；权威 30 支全量；检索片段 0 支全量（合计入选 30/30）"
    )


# ---------- 7 每次调用 Manifest 在场且材料标来源（行为 7） ----------


def test_manifest_present_source_rows() -> None:
    """行 7 四列表同长、来源逐条对应、常驻来源行按呼叫分型、零材料亦在场（行为 7）。"""
    observations = [
        _obs(4, "agg_row", content="合计", source_id="agg.fct_daily_metering", version="v1"),
        _obs(5, "metric", content="台账卡", source_id="metric-1"),
        _obs(6, "fragment", content="片段", source_id="kb-1"),
    ]
    answer = compile_manifest(observations, step="answer", max_observations=24)
    assert answer.source_type == ["agg_row", "metric", "fragment"]
    assert answer.source_id == ["agg.fct_daily_metering", "metric-1", "kb-1"]
    assert answer.version == ["v1", None, None]
    assert answer.trust_level == [TRUST_AGG, TRUST_LEDGER, TRUST_REPORT]
    # 空串如实（图谱无锚边形——V1 事实面）
    assert answer.source_id == [
        str(obs.get("source_id", "")) for obs in observations
    ]

    # 常驻来源行按呼叫分型：decision／clarify／toolmatch 首入且投影非空 → 恰 3 行
    dump: dict[str, Any] = {"metrics": [{"slot": "日产油量"}], "cards": ["agg"]}
    for step in ("decision", "clarify", "toolmatch"):
        first = compile_manifest(observations, step=step, max_observations=24, ledger_dump=dump)
        assert len(first.source_type) == len(first.source_id) == len(first.version) == 3 + 3
        assert list(RESIDENT_SOURCE_ROWS.items()) == [
            ("ledger_dump", "ledger_full_dump"),
            ("alias_dump", "ledger_aliases"),
            ("schema_card", "schema_cards"),
        ]
        assert first.source_type[-3:] == list(RESIDENT_SOURCE_ROWS)
        assert first.source_id[-3:] == list(RESIDENT_SOURCE_ROWS.values())
        assert first.version[-3:] == [None, None, None]
        assert first.trust_level[-3:] == [TRUST_LEDGER] * 3
    # answer 轮零常驻行（ledger_dump=None）
    assert len(answer.source_type) == 3

    # 台账空投影 → 零台账来源行且材料字段不受影响
    empty_dump = compile_manifest(
        observations, step="decision", max_observations=24, ledger_dump={}
    )
    assert len(empty_dump.source_type) == 3
    assert (empty_dump.material_total, empty_dump.material_rendered) == (3, 3)

    # 零材料步 → 0/0/False 且四列表空（Manifest 仍在场）
    zero = compile_manifest([], step="understand", max_observations=24)
    assert zero.source_type == zero.source_id == zero.version == zero.trust_level == []

    # 截断态 → 来源行只含实渲支
    cut = compile_manifest(_fragments(5), step="answer", max_observations=2)
    assert len(cut.source_id) == 2 and cut.material_total == 5

    # as_dict 全键恒出（十键）
    assert set(answer.as_dict()) == {
        "source_type",
        "source_id",
        "version",
        "trust_level",
        "selected_reason",
        "token_count",
        "transform",
        "material_total",
        "material_rendered",
        "material_truncated",
    }


# ---------- 8 过程档案摘要段有界（行为 8） ----------


def _notes_state(count: int, *, phase: str = "decision") -> RunState:
    return RunState(
        process_notes=[
            {"phase": phase, "title": f"第 {i} 步", "digest": f"结果 {i}" * 4} for i in range(count)
        ]
    )


def test_process_notes_bounded_summary() -> None:
    """行 8 零档案零段／有界／披露行逐字／全入预算无披露（行为 8）。"""
    # 零档案＝零段（调用方跳过——首轮零噪声）
    assert render_process_notes(RunState(), budget=PROCESS_NOTES_BUDGET) == ""

    # 全入预算 → 全行、零披露行（头注逐字在场）
    full = render_process_notes(_notes_state(3), budget=PROCESS_NOTES_BUDGET)
    assert full.startswith("【本 run 已做（过程档案摘要——防重参考，不是作答材料）】\n")
    assert full.count("\n- [") == 3
    assert "有界截断" not in full

    # 超预算 → 披露行逐字＋`n` 与已渲行数一致
    bounded = render_process_notes(_notes_state(20), budget=120)
    rendered = bounded.count("\n- [")
    assert _PROCESS_NOTES_DISCLOSURE.format(n=rendered, total=20) in bounded
    assert rendered < 20

    # 两跑逐字相等（确定性）
    assert render_process_notes(_notes_state(20), budget=120) == bounded

    # phase 缺失＝`?`（现状缺省回落——迁移照抄）
    missing = render_process_notes(
        RunState(process_notes=[{"title": "无相位", "digest": "d"}]), budget=PROCESS_NOTES_BUDGET
    )
    assert "\n- [?] 无相位｜d" in missing


# ---------- 9 compaction：超窗视图（行为 9——pin-22／pin-30） ----------


def _long(tag: str, length: int) -> str:
    return tag + "字" * (length - len(tag))


def _chain() -> list[dict[str, str]]:
    """超窗链 fixture：角色红线＋相位合同包＋两轮对话＋当前轮（预算 120 下压缩第 1 轮对）。"""
    return [
        {"role": "system", "content": "角色红线", "origin": "system_redline"},
        {"role": "user", "content": "相位合同包", "origin": _PHASE_CONTRACT_ORIGIN},
        {"role": "user", "content": _long("第一轮问", 200), "origin": "user_verbatim"},
        {"role": "assistant", "content": _long("第一轮答", 200), "origin": "assistant_final"},
        {"role": "user", "content": _long("第二轮问", 200), "origin": "user_verbatim"},
        {"role": "assistant", "content": _long("第二轮答", 200), "origin": "assistant_final"},
        {"role": "user", "content": _long("本轮问", 40), "origin": "user_verbatim"},
    ]


def test_compaction_overwindow_model_view() -> None:
    """行 9 超窗视图：摘要置位／最新轮恒在场／单巨轮零压缩／合同不摘／原史零覆盖／
    披露账目（行为 9——pin-22 视图面／pin-30 compaction 半面）。
    """
    chain = _chain()
    before = deepcopy(chain)
    view, account = compact_messages(chain, dialogue_view_tokens=120)
    # 摘要＝system 消息、置于角色红线 system 之后、近期轮之前
    assert view[0] == chain[0]
    assert view[1]["role"] == "system" and view[1]["content"].startswith(_SUMMARY_HEAD)
    # 最旧对话轮对（第一轮 user＋assistant）摘要化：问原文／答首行（单行上限 120 截数）
    assert f"\n问：{_long('第一轮问', 200)[:120]}" in "\n" + view[1]["content"]
    assert f"\n答：{_long('第一轮答', 200)[:120]}" in "\n" + view[1]["content"]
    # 保留近轮逐字（第二轮对＋当前轮全量在场）
    assert view[-3:] == chain[-3:]
    # 最新轮恒在场（保留窗至少 1 轮）；合同／相位包条全数保留（原地）
    assert view[-1] == chain[-1]
    assert {"role": "user", "content": "相位合同包", "origin": _PHASE_CONTRACT_ORIGIN} in view
    # 原史零覆盖（只作用于模型视图）
    assert chain == before
    # 披露账目在场（合成位：材料面 selected_reason 之后以「；」追加）
    reason = compile_manifest([], step="answer", max_observations=24).selected_reason
    assert account == (
        "对话层 compaction：5 轮→保留 3 轮＋前情摘要（预算 120，原史在会话档案全量可查）"
    )
    assert f"{reason}；{account}".endswith(account)
    # 截数 120：摘要行单行上限（问原文截 120／答取首行截 120）
    long_chain = [
        {"role": "system", "content": "角色红线"},
        {"role": "user", "content": _long("旧问", 600), "origin": "user_verbatim"},
        {"role": "assistant", "content": _long("旧答", 600), "origin": "assistant_final"},
        {"role": "user", "content": _long("本轮问", 40), "origin": "user_verbatim"},
    ]
    capped, _ = compact_messages(long_chain, dialogue_view_tokens=20)
    summary_lines = [line for line in capped[1]["content"].split("\n") if line.startswith("问：")]
    assert len(summary_lines) == 1 and len(summary_lines[0]) == len("问：") + 120
    # 答首行取值（多行内容取首行）
    multi = [
        {"role": "system", "content": "角色红线"},
        {"role": "user", "content": _long("旧问", 200), "origin": "user_verbatim"},
        {
            "role": "assistant",
            "content": "首行答案" + "填" * 100 + "\n第二行不入摘要",
            "origin": "assistant_final",
        },
        {"role": "user", "content": _long("本轮问", 40), "origin": "user_verbatim"},
    ]
    first_line_view, _ = compact_messages(multi, dialogue_view_tokens=15)
    assert "答：首行答案" in first_line_view[1]["content"]
    assert "第二行不入摘要" not in first_line_view[1]["content"]

    # 最新轮单轮超预算仍恒在场（含单巨轮＝原样放行零压缩）
    giant = [
        {"role": "system", "content": "角色红线"},
        {"role": "user", "content": _long("巨轮", 5000), "origin": "user_verbatim"},
    ]
    giant_view, giant_account = compact_messages(
        giant, dialogue_view_tokens=DEFAULT_DIALOGUE_VIEW_TOKENS
    )
    assert giant_view == giant and giant_account == ""


# ---------- 10 compaction：预算内原样返回、披露为空（行为 10 前置——零漂移） ----------


def test_compaction_within_budget_no_drift() -> None:
    """行 10 预算内原样返回、披露为空（零漂移）；形态越界抛参数错误（行为 9／错误契约）。"""
    chain = [
        {"role": "system", "content": "角色红线"},
        {"role": "user", "content": "问", "origin": "user_verbatim"},
        {"role": "assistant", "content": "答", "origin": "assistant_final"},
    ]
    before = deepcopy(chain)
    view, account = compact_messages(chain, dialogue_view_tokens=DEFAULT_DIALOGUE_VIEW_TOKENS)
    assert view == chain and account == ""
    # 视图为副本（改视图不改入参——零写入）
    view[0]["content"] = "改"
    assert chain == before

    # 形态越界（非正整数）→ 抛参数错误，不吞错
    for illegal in (0, -1, True, "8192"):
        with pytest.raises(ValueError):
            compact_messages(chain, dialogue_view_tokens=illegal)  # type: ignore[arg-type]

    # 识别面词表＝`dialogue` 条目来源闭世界（结构化标记键 `origin`——流水 49③；零内容子串识别）
    assert DIALOGUE_ORIGINS == {"user_verbatim", "assistant_final", "clarify_approval_replay"}


# ---------- 11 投影取得：取一次、返回值副本（行为 10） ----------


async def test_ledger_load_via_tools_take_once() -> None:
    """行 11 已有投影（含空投影）零工具调用、空→恰一次取得＋写回、返回值副本（行为 10）。

    取得路径唯一＝注入端口（装载入口形待核定——见文件头注；未接线时不静默兜底，见下断言）。
    """
    dump: dict[str, Any] = {"metrics": [{"slot": "日产油量"}], "aliases": {"日产": "日产油量"}}
    port = _Port(dump)
    wire_ledger_projection(port)

    # 已有投影 → 零工具调用、原样返回
    state = RunState(ledger_dump=deepcopy(dump))
    loaded = await load_ledger_dump(state)
    assert port.calls == 0 and loaded == dump
    # 返回值副本语义（改返回值不改 state）
    loaded["metrics"] = []
    loaded["新增"] = 1
    assert state.ledger_dump == dump

    # 空投影 {}＝已取之空态（不再取）
    empty_state = RunState(ledger_dump={})
    assert await load_ledger_dump(empty_state) == {} and port.calls == 0

    # 空 state → 恰一次取得＋写回 state
    fresh = RunState()
    got = await load_ledger_dump(fresh)
    assert port.calls == 1 and fresh.ledger_dump == dump and got == dump
    got["metrics"] = []  # 副本语义（写回值与返回值互不串改）
    assert fresh.ledger_dump == dump
    # 再取一次 → 复用（仍零新调用）
    assert await load_ledger_dump(fresh) == dump and port.calls == 1

    # 取得路径唯一：未接线（注入缝空）→ 不静默兜底、不冒充已取得（fail-fast）
    wire_ledger_projection(None)
    with pytest.raises(LedgerLoadError):
        await load_ledger_dump(RunState())


# ---------- 12 取得失败＝fail-fast（行为 11） ----------


async def test_ledger_load_failure_run_failed_honest() -> None:
    """行 12 失败＝fail-fast 终局＋稳定错误提示在场＋留痕可查；合法空不触发失败腿（行为 11）。"""
    # 判据面一：工具面返回 failed 态（端口返 None）
    wire_ledger_projection(_Port(None))
    failed_state = RunState(run_id="run-fail")
    with pytest.raises(LedgerLoadError) as none_exc:
        await load_ledger_dump(failed_state)
    assert str(none_exc.value) == _FAILURE_HINT  # 稳定错误提示（机读可查的留痕载体）
    assert failed_state.ledger_dump is None  # 不写空投影、不冒充已取得（无静默兜底）

    # 判据面二：调用异常捕获面（原始异常文本只经异常链留痕，不进稳定提示）
    class _Boom:
        async def fetch(self) -> Mapping[str, Any] | None:
            raise RuntimeError("引擎 500：连接被拒")

    wire_ledger_projection(_Boom())
    with pytest.raises(LedgerLoadError) as boom_exc:
        await load_ledger_dump(RunState())
    assert str(boom_exc.value) == _FAILURE_HINT  # 两路同一稳定提示
    assert "引擎 500" not in str(boom_exc.value)
    assert boom_exc.value.__cause__ is not None and "引擎 500" in str(boom_exc.value.__cause__)

    # 合法空结果 fixture：与失败不同路（工具成功返回空 ≠ 失败——原样取得＋写回）
    port = _Port({})
    wire_ledger_projection(port)
    legal = RunState()
    assert await load_ledger_dump(legal) == {}
    assert port.calls == 1 and legal.ledger_dump == {}


# ---------- 19 截断机读信号两面在场、本块零 emit（行为 5／6／不降级节——pin-09 之三） ----------


def test_truncation_signal_no_emit() -> None:
    """行 19 披露行＋字段两面在同一次调用内同场；本块源码零 emit（行为 5／6／不降级节）。"""
    observations = _fragments(30)
    text, meta = render_materials(observations, max_observations=10)
    manifest = compile_manifest(observations, step="answer", max_observations=10)
    assert _DISCLOSURE_HEAD in text  # 模型面（a）
    assert meta["material_truncated"] is True  # 机读字段（b）
    assert manifest.material_truncated is True and "帽 10 支截断" in manifest.selected_reason

    # 本块零 emit（帧面归发射方——AST 扫描）
    sources = _context_sources()
    assert sources, "扫描面为空——看守失效"
    emit_sites = [
        (path.name, node.lineno)
        for path, tree in sources
        for node in ast.walk(tree)
        if (isinstance(node, ast.Attribute) and node.attr == "emit")
        or (isinstance(node, ast.Name) and node.id == "emit")
    ]
    assert emit_sites == [], f"本块出现 emit 位点：{emit_sites}"

    # 探测器非空转（`emit` 位点必须被抓）
    forged = ast.parse("bus.emit('notice', {})\n")
    assert [
        node.lineno
        for node in ast.walk(forged)
        if isinstance(node, ast.Attribute) and node.attr == "emit"
    ] == [1]


# ---------- 附：消费面指针（登记件——本票不实现） ----------

# ①`specs/prompts.md` 行为 16⑤：已做段由调用方传入 `render_process_notes` 产物文本原样在场
#   （渲染归本块、拼接归调用方——本块不追加、不改写）；
# ②`specs/answering.md` 行为 4：材料面 Manifest 由本块编译、随步落地（缺位＝判失败）；
#   材料截断 notice 帧与用户面披露文本＝发射方义务（本块零帧）；
# ③`specs/bookkeeping.md` 行为 7／8：`messages` 物理追加与合同标记写入＝其唯一写口
#   （pin-24／pin-26 不落本块：本块零合同、零标记、零追加时点——`dialogue` 写口不在本块）。

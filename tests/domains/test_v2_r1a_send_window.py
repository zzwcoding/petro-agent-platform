"""V2-45 R1a 送窗动态配额钉测（族 B 三层组合之「装得下」——P-044 开发拍）。

票面任务四条逐条落测：
- 配额动态化：ToolContext.budget 缺省 4 → 按调用上下文赋值——问题组子问题数
  ×每子问题基线 6、上限 24（resolve_send_budget 单点＋runtime _ctx_of 接线）；
- 表类整行集：明细/表格类问句（题面词面判定）下，目标表格所在片段的同报告
  同 section 整组补席进窗、不计入单支配额（window 超出 budget——增量如实）；
- 题眼锚保底：多来源竞争下「题眼锚命中的来源」至少 1 席位（消灭 Q14 族 B
  「目标报告零席位＝缺位来源」形——Q14D-NQ-D9 帧的确定性缩影）；
- window_note 数字如实：扩席后「召回 N 支/送窗 M 支」照实按实走计数
  （M＝实际送窗支数，含锚保底与整组增量），缺位来源不再列已保席来源。

红线钉：不动排序/召回——供给层只动席位分配；配额路径（族分池/余量补给/
缺位枚举）无锚非扩席场景零漂移。

fixture 家族布点＝Q14 零席位形的成因缩影：C 报告（dynamic 族·hints 命中）
独占配额，目标报告 34-8（monthly 族·被挤）在召回池内但零席位——与
Q14D-NQ-D9 帧「缺位来源（预算未及）：《渤中34-8油田一季度注采调整…》」
同形。全片段文本命中题眼锚「34-8」；表格支（5.2 配注调整表）含「Y-24」。
"""

from __future__ import annotations

from typing import Any

from appv2.retrieval import (
    FragmentRecord,
    Hit,
    InMemoryFragmentLibrary,
    LocalHashEmbedder,
    RetrievalEngine,
    RetrievalNeed,
    anchor_seat_tokens,
    is_table_rowset_question,
    supply_window,
)
from appv2.tools import resolve_send_budget

# ---------- fixture：双报告竞争语料（Q14 族 B 帧形的确定性缩影） ----------

_LIB_C = ("lib-c", "渤中34-5动态分析库", "dynamic")
_LIB_T = ("lib-t", "渤中34-8动态分析库", "monthly")
_RPT_C = ("rpt-c", "C-渤中34-5油田三季度注水调整与生产运行分析")
_RPT_T = ("rpt-t", "渤中34-8油田一季度注采调整与生产运行分析")
_TARGET_REPORT = _RPT_T[1]

# 目标报告（34-8）的 5.2 配注调整表整组——表格承载片段＋同 section 解读支
# （版式照 eval 语料：全角缩进数字行）。
_TABLE_SECTION = "5.2 四月配注调整与计划注水量"
_TABLE_TEXT = (
    "5.2 四月配注调整与计划注水量\n"
    "　　井号　　　原配注(m³/d)　新配注(m³/d)　执行日期\n"
    "　　Y-24　　　320　　　　　 380　　　　　 4 月 12 日\n"
    "　　Y-26　　　260　　　　　 320　　　　　 4 月 20 日\n"
    "其余 7 口维持不变。4 月计划注水量 11.0 万方。"
)
_TABLE_MATE_TEXT = (
    "环比解读：注水增幅大于产液增幅，季度注采比回升 0.02；"
    "Y-24 与 Y-26 两行执行日期极易对调，核对以配注调整表为准。"
)


def _frag(
    fid: str,
    lib: tuple[str, str, str],
    rpt: tuple[str, str],
    section: str,
    text: str,
) -> FragmentRecord:
    return FragmentRecord(
        fragment_id=fid,
        report_id=rpt[0],
        report=rpt[1],
        section=section,
        library_id=lib[0],
        library=lib[1],
        family=lib[2],
        text=text,
    )


def _fragments() -> list[FragmentRecord]:
    """六支片段：C 报告（dynamic·hints 命中位）三支＋34-8 目标组三支。

    目标报告全部片段文本命中题眼锚「34-8」；表格支与解读支同 section
    （整组判定键）、文本命中「Y-24」。
    """
    return [
        _frag("f-c1", _LIB_C, _RPT_C, "1.1 主要生产指标",
              "三季度综合含水率 79.0% 降至 78.3%，W-13、W-16 井组周期注水调整。"),
        _frag("f-c2", _LIB_C, _RPT_C, "2.1 注水月度数据",
              "月注采比 0.98 进入 0.95～1.05 区间，注水量 9.26 万m³。"),
        _frag("f-c3", _LIB_C, _RPT_C, "4.1 累积亏空",
              "渤中34-5 油田累积亏空 −41.3 万方，地层压力 19.6 MPa。"),
        _frag("f-t0", _LIB_T, _RPT_T, "全文档摘要",
              "渤中34-8 油田一季度注采调整方案摘要：月注采比逐月回升至 1.03。"),
        _frag("f-t1", _LIB_T, _RPT_T, _TABLE_SECTION, _TABLE_TEXT),
        _frag("f-t2", _LIB_T, _RPT_T, _TABLE_SECTION, _TABLE_MATE_TEXT),
    ]


def _engine() -> RetrievalEngine:
    return RetrievalEngine(
        library=InMemoryFragmentLibrary(_fragments()),
        embedder=LocalHashEmbedder(),
    )


def _ranked_all() -> list[tuple[Hit, float]]:
    """融合序替身（直接驱动 supply_window——seed 序给单调递减分）。"""
    return [
        (Hit(frag, 1.0 / (i + 1), "keyword"), 1.0 / (i + 1))
        for i, frag in enumerate(_fragments())
    ]


# ---------- 钉一：送窗预算动态化（数值面单点） ----------


def test_resolve_send_budget_scales_with_subtasks_and_caps() -> None:
    """子问题数×基线 6，上限 24；单支＝基线（≥ 旧缺省 4 只扩不缩）。"""
    assert resolve_send_budget(1) == 6  # 单支问句：4 → 6（族 B 主面第一扩）
    assert resolve_send_budget(2) == 12
    assert resolve_send_budget(3) == 18
    assert resolve_send_budget(4) == 24  # MAX_SUBTASKS_CONTRACT=4 恰触上限
    assert resolve_send_budget(6) == 24  # 越界子问题数钳在上限
    assert resolve_send_budget(0) == 6  # 边界兜底：至少按 1 支计


def test_ctx_of_budget_follows_question_group_size() -> None:
    """runtime 接线：_ctx_of 预算随问题组子问题数扩（batch 相位逐支共享组尺寸）。"""
    from appv2.runtime.graph import _ctx_of
    from appv2.runtime.state import RunState

    def _group(n: int) -> dict[str, Any]:
        return {
            "subtasks": [
                {"id": f"s{i}", "question": f"子问{i}", "chain": "knowledge",
                 "tool": "doc_retrieve", "ledger_notes": ""}
                for i in range(n)
            ]
        }

    assert _ctx_of(RunState(run_id="run-x", question_group=_group(4))).budget == 24
    assert _ctx_of(RunState(run_id="run-x", question_group=_group(2))).budget == 12
    # 无问题组（legacy 单发射）＝按 1 支计——基线 6。
    assert _ctx_of(RunState(run_id="run-y")).budget == 6


# ---------- 钉二：题型词面（表类解锁判定＋题眼锚集） ----------


def test_is_table_rowset_question_wording() -> None:
    """表格/明细名词形命中；动词性「表示/表达」与无表问句不误判。"""
    assert is_table_rowset_question("5.2 配注调整表中 Y-24 与 Y-26 两行都出现了数字 320")
    assert is_table_rowset_question("第十章对照表中 Y-23 井的完井方式各是多少？")
    assert is_table_rowset_question("1.3 节这个数字的算式不在任何表格里")
    assert is_table_rowset_question("去年各井每天的日产油量明细")
    assert not is_table_rowset_question("有人表示地层压力随之回升了 0.2 MPa")
    assert not is_table_rowset_question("报告是如何表达这一趋势的？")
    assert not is_table_rowset_question("W-22 井杆断的根因是什么？")


def test_anchor_seat_tokens_asset_wording_only() -> None:
    """题眼锚集＝显式锚＋问句资产编号 token；纯数字/单位词/语义词不进保底集。"""
    tokens = anchor_seat_tokens(
        "5.2 配注调整表中 Y-24 与 Y-26 两行都出现了数字 320，原配注 260 提至 380",
        anchors=("34-8",),
    )
    assert tokens == ("34-8", "Y-24", "Y-26")  # 显式锚在前，问句资产号随后去重
    # 纯数字（320/260/380）、单位词（MPa）、无编号语义词均不触发保底。
    assert anchor_seat_tokens("地层压力回升 0.2 MPa，注采比 320 与 12 mm 油嘴") == ()
    assert anchor_seat_tokens("注采比是多少", anchors=("注采比",)) == ()


# ---------- 钉三：题眼锚保底（多来源竞争——目标报告零席位形的消灭） ----------


def test_supply_window_plain_hinted_path_unchanged() -> None:
    """无锚回归钉：hints 挤占下目标家族零席位＝缺位（Q14 旧形保持零漂移）。"""
    supply = supply_window(_ranked_all(), 2, ("dynamic",))
    assert [p[0].fragment.fragment_id for p in supply.window] == ["f-c1", "f-c2"]
    assert supply.anchor_seated == ()
    assert supply.rowset_added == 0
    assert supply.missing_sources == [_TARGET_REPORT]


def test_supply_window_anchor_seat_guarantee_beats_zero_seat() -> None:
    """锚命中来源零席位→保底 ≥1 席（追加于配额外）；缺位枚举不再列它。"""
    ranked = _ranked_all()
    plain = supply_window(ranked, 2, ("dynamic",))
    assert _TARGET_REPORT in plain.missing_sources  # 前置：零席位形在场

    guaranteed = supply_window(ranked, 2, ("dynamic",), anchors=("34-8",))
    reports = {p[0].fragment.report for p in guaranteed.window}
    assert _TARGET_REPORT in reports
    assert _TARGET_REPORT not in guaranteed.missing_sources
    assert guaranteed.anchor_seated == (_TARGET_REPORT,)
    # 保底席位是追加席：窗支数 3 > 预算 2（扩席如实，不挤占既有族分池代表支）。
    assert len(guaranteed.window) == 3
    # 保底支取该来源融合序最优一支（f-t0 在 ranked 中先于 f-t1/f-t2）。
    assert guaranteed.window[-1][0].fragment.fragment_id == "f-t0"


def test_supply_window_anchor_multiple_tokens_one_source_one_seat() -> None:
    """多锚命中同一来源：保底恰 1 席，不重复追加（来源级去重）。"""
    supply = supply_window(_ranked_all(), 2, ("dynamic",), anchors=("34-8", "Y-24"))
    reports = [p[0].fragment.report for p in supply.window]
    assert reports.count(_TARGET_REPORT) == 1
    assert _TARGET_REPORT not in supply.missing_sources


async def test_retrieve_no_false_guarantee_for_non_anchor_sources() -> None:
    """引擎面端到端（保底不误发）：零席位来源若非题眼锚命中——不保席、缺位如实。

    问句资产号「34-8」只命中目标报告；C 报告零席位系预算未及且不锚命中——
    保底不得为它发明席位（缺位枚举照旧机读）。锚 token 从问句经
    anchor_seat_tokens 流入供给层的接线由表类引擎钉（rowset 目标锚条件）
    同路覆盖。
    """
    bundle = await _engine().retrieve(
        RetrievalNeed(
            question="渤中34-8 油田一季度注采调整情况如何",
            family_hints=("dynamic",),
            budget=1,
        )
    )
    note = bundle.window_note
    assert "题眼锚保底席位" not in note  # 34-8 命中的目标报告已获席——保底未触发
    assert "缺位来源（预算未及）：C-渤中34-5油田三季度注水调整与生产运行分析" in note


# ---------- 钉四：表类整行集（目标表格片段整组进窗——不计入配额） ----------


def test_supply_window_rowset_group_enters_whole() -> None:
    """表类问句：目标表格承载片段的同报告同 section 整组补席（增量如实）。"""
    supply = supply_window(
        _ranked_all(), 2, ("dynamic",), anchors=("Y-24",), rowset_question=True
    )
    window_ids = [p[0].fragment.fragment_id for p in supply.window]
    # 目标表格支 f-t1 与同 section 解读支 f-t2 全组在窗（表内行＋表外解读）。
    assert "f-t1" in window_ids
    assert "f-t2" in window_ids
    # 整组增量不计入单支配额：窗支数＝配额 2＋保底 1＋整组增量 1＝4。
    assert len(window_ids) == 4
    assert supply.rowset_added == 1
    assert supply.anchor_seated == (_TARGET_REPORT,)


def test_supply_window_rowset_requires_table_question() -> None:
    """非表类问句：同语料同锚——无整组扩席（行集规则只随题型解锁）。"""
    supply = supply_window(_ranked_all(), 2, ("dynamic",), anchors=("Y-24",))
    window_ids = [p[0].fragment.fragment_id for p in supply.window]
    assert "f-t1" in window_ids  # 锚保底照在
    assert "f-t2" not in window_ids  # 整组通道关闭
    assert supply.rowset_added == 0


def test_supply_window_rowset_requires_anchor_hit_on_table() -> None:
    """锚在场时目标表格片段须锚命中（防无关报告的高位表格片被误当目标）。

    锚「34-8」命中目标组摘要支（f-t0——保底进窗）但表格支 f-t1 文本不含
    该锚——整组不误扩（rowset_added=0）；锚条件命中的整组扩席另钉
    （rowset_group_enters_whole——「Y-24」命中表格支文本）。
    """
    supply = supply_window(
        _ranked_all(), 2, ("dynamic",), anchors=("34-8",), rowset_question=True
    )
    window_ids = [p[0].fragment.fragment_id for p in supply.window]
    assert "f-t0" in window_ids  # 锚保底照在（摘要支命中 34-8）
    assert "f-t1" not in window_ids  # 表格支不含 34-8——整组不扩
    assert supply.rowset_added == 0


async def test_retrieve_rowset_window_note_truthful() -> None:
    """引擎面端到端：表类问句整组进窗，window_note 数字照实按实走（送窗 M＞配额）。"""
    bundle = await _engine().retrieve(
        RetrievalNeed(
            question="渤中34-8 油田 5.2 配注调整表中 Y-24 与 Y-26 的执行日期",
            family_hints=("dynamic",),
            budget=2,
        )
    )
    window_ids = [obs.fragment_id for obs in bundle.observations]
    assert "f-t1" in window_ids and "f-t2" in window_ids
    # 数字如实：送窗 M＝实际支数（含整组增量）；扩席留痕机读（本形下目标
    # 报告经族配额已获席——保底未触发，整组扩席段在场）。
    note = bundle.window_note
    # 实走计数（V2-47 R1b 随动：前缀进 BM25——原零分切片经索引文本前缀词面
    # 获非零分，召回池 5→6；窗构成不变——f-t1/f-t2/整组扩席同形）。
    assert note.startswith("召回 6 支/送窗 3 支；已召回未送窗 3 支")  # 实走计数
    assert "表类整行集进窗 +1 支" in note
    assert any("Y-24" in obs.text for obs in bundle.observations)  # 表格行真支在窗
    assert "缺位来源" not in note  # 目标报告已获席——无缺位可列

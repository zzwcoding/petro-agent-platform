"""V2-45 R1a 送窗动态配额钉测（族 B 三层组合之「装得下」——P-044 开发拍）。

票面任务四条逐条落测：
- 配额动态化：ToolContext.budget 缺省 4 → 按调用上下文赋值——问题组子问题数
  ×每子问题基线 6、上限 24（resolve_send_budget 单点＋runtime _ctx_of 接线）；
- 表类整行集：明细/表格类问句（题面词面判定）下，目标表格所在片段的同报告
  同 section 整组补席进窗、不计入单支配额（window 超出 budget——增量如实）；
- 题眼锚保底：多来源竞争下「题眼锚命中的来源」至少 1 席位（消灭 Q14 族 B
  「目标报告零席位＝缺位来源」形——Q14D-NQ-D9 帧的确定性缩影）；
- window_note 数字如实：扩席后「共检索到 N 条材料，M 条用进了答案」照实按实走
  计数（M＝实际在窗条数，含锚保底与整组增量），已保席来源不再列未纳入名单。

红线钉：不动排序/召回——供给层只动席位分配；配额路径（族分池/余量补给/
缺位枚举）无锚非扩席场景零漂移。

fixture 家族布点＝Q14 零席位形的成因缩影：C 报告（dynamic 族·hints 命中）
独占配额，目标报告 34-8（monthly 族·被挤）在召回池内但零席位——与
Q14D-NQ-D9 帧「缺位来源（预算未及）：《渤中34-8油田一季度注采调整…》」
同形。全片段文本命中题眼锚「34-8」；表格支（5.2 配注调整表）含「Y-24」。

V2-82d 追加（末节）：题眼锚保底的命中面从 `frag.text` 扩为
text ∪ report ∪ well——题面点名的主体常只落在报告名（油田名）或本体标签
（well 井号）里，text-only 判据下保底席配不上。
"""

from __future__ import annotations

from dataclasses import replace
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
    well: str | None = None,
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
        well=well,
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


def test_supply_window_anchor_seat_dropped_when_budget_full() -> None:
    """V2-89b 改判（原 `anchor_seat_guarantee_beats_zero_seat`）：族配额吃满预算→
    锚保底候选**计入 budget**被丢（超预算不再追加），`over_budget` 机读位如实。

    旧行为（V2-45 R1a）下保底席是「追加席不计配额」——窗支数 3 > 预算 2；D3 真
    封顶后同一场景窗支数＝预算 2，锚命中来源零席位如实进缺位枚举。
    """
    ranked = _ranked_all()
    plain = supply_window(ranked, 2, ("dynamic",))
    assert _TARGET_REPORT in plain.missing_sources  # 前置：零席位形在场

    capped = supply_window(ranked, 2, ("dynamic",), anchors=("34-8",))
    assert len(capped.window) == 2  # 真封顶（旧形 3 > 预算 2）
    assert capped.anchor_seated == ()  # 超预算不再追加（保底席被丢）
    assert capped.over_budget is True  # 归因机读位
    assert _TARGET_REPORT in capped.missing_sources  # 零席位如实缺位（不静默）


# ---------- V2-89b：预算有余时追加席照常进窗（正面对照面） ----------

# 三族语料（dynamic/monthly/blank）＋目标报告（monthly·T-77）——族配额每族 1 席
# 时预算有余（budget 4 → 余 1；budget 6 → 余 3），锚/行集/展开三通道各有候选。
_CAP_LIB_D = ("lib-cap-d", "库丁动态分析库", "dynamic")
_CAP_LIB_M = ("lib-cap-m", "库戊月报库", "monthly")
_CAP_LIB_B = ("lib-cap-b", "库己台账库", "blank")
_CAP_RPT_D = ("rpt-cap-d", "丁-生产动态分析")
_CAP_RPT_M = ("rpt-cap-m", "戊-注采调整月报")
_CAP_RPT_M2 = ("rpt-cap-m2", "庚-注水月度分析")
_CAP_RPT_B = ("rpt-cap-b", "己-台账登记")
_CAP_RPT_T = ("rpt-cap-t", "T-77 井专项分析报告")
_CAP_WELL_TAG = "W-22井·数值模拟平台"
_CAP_TABLE_SECTION = "3 配注调整表"
_CAP_TABLE_TEXT = (
    "3 配注调整表\n"
    "　　井号　　　原配注(m³/d)　新配注(m³/d)\n"
    "　　Y-24　　　320　　　　　 380\n"
    "　　Y-26　　　260　　　　　 320\n"
)


def _capped_fragments() -> list[FragmentRecord]:
    """三族＋目标报告语料（目标支正文不含锚词——报告名/well 标签是命中面）。

    融合序：三族首位（f-cap-d1/m1/b1）→ 余量候补（f-cap-m2）→ 目标报告 T-77
    的支（f-cap-t1 报告名含 `T-77`、well 标签含 `W-22`，正文两者都不含——
    V2-82d 三面命中面；f-cap-t3/f-cap-t4 为表格承载支与其同 section 解读支）。
    目标支排在余量候补之后——预算有余时的保底席只能由锚/行集通道产出（可判）。
    """
    return [
        _frag("f-cap-d1", _CAP_LIB_D, _CAP_RPT_D, "1 概况", "丁报告正文：含水 79%。"),
        _frag("f-cap-m1", _CAP_LIB_M, _CAP_RPT_M, "1 概况", "戊月报正文：注采比 0.98。"),
        _frag("f-cap-b1", _CAP_LIB_B, _CAP_RPT_B, "1 概况", "己台账正文：登记 3 条。"),
        _frag("f-cap-m2", _CAP_LIB_M, _CAP_RPT_M2, "1 概况", "庚月报正文：注水 9.26 万方。"),
        _frag("f-cap-t1", _CAP_LIB_M, _CAP_RPT_T, "1 概况",
              "该井情况：检泵周期 215 天。", well=_CAP_WELL_TAG),
        _frag("f-cap-t3", _CAP_LIB_M, _CAP_RPT_T, _CAP_TABLE_SECTION, _CAP_TABLE_TEXT),
        _frag("f-cap-t4", _CAP_LIB_M, _CAP_RPT_T, _CAP_TABLE_SECTION,
              "解读：Y-24 与 Y-26 两行执行日期极易对调。"),
    ]


def _capped_ranked_all() -> list[tuple[Hit, float]]:
    """融合序替身（seed 序给单调递减分）。"""
    return [
        (Hit(frag, 1.0 / (i + 1), "keyword"), 1.0 / (i + 1))
        for i, frag in enumerate(_capped_fragments())
    ]


def _capped_engine() -> RetrievalEngine:
    return RetrievalEngine(
        library=InMemoryFragmentLibrary(_capped_fragments()),
        embedder=LocalHashEmbedder(),
    )


# 引擎面留痕可见性语料（B-正6 缩影）：题面点名的主体只落报告名——三族竞争下
# 目标报告（monthly·T-77）非族首，锚保底在预算内进窗。
_NOTE_LIB_D = ("lib-note-d", "库丁动态分析库", "dynamic")
_NOTE_LIB_M = ("lib-note-m", "库庚月报库", "monthly")
_NOTE_LIB_B = ("lib-note-b", "库己台账库", "blank")
_NOTE_RPT_D = ("rpt-note-d", "丁-生产动态分析")
_NOTE_RPT_M = ("rpt-note-m", "庚-注水月度分析")
_NOTE_RPT_B = ("rpt-note-b", "己-台账登记")
_NOTE_RPT_T = ("rpt-note-t", "T-77 井专项分析报告")


def _note_fragments() -> list[FragmentRecord]:
    """四支语料：三族族首（正文强命中题面）＋目标报告支（正文不含锚词）。"""
    return [
        _frag("f-note-d1", _NOTE_LIB_D, _NOTE_RPT_D, "1 概况",
              "注水月度数据：月注采比 0.98。"),
        _frag("f-note-m1", _NOTE_LIB_M, _NOTE_RPT_M, "1 概况",
              "注水月度数据：注水量 9.26 万方，注水月度计划完成率 102%。"),
        _frag("f-note-b1", _NOTE_LIB_B, _NOTE_RPT_B, "1 概况",
              "注水月度台账：登记 3 条。"),
        _frag("f-note-t1", _NOTE_LIB_M, _NOTE_RPT_T, "1 概况",
              "该井情况：检泵周期 215 天。"),
    ]


async def _note_engine() -> RetrievalEngine:
    """语料向量预嵌（向量腿参与融合序——族首＝强命中题面的三族支，非目标支）。"""
    embedder = LocalHashEmbedder()
    seeds = _note_fragments()
    vectors = await embedder.embed([seed.text for seed in seeds])
    frags = [
        replace(seed, embedding=vector)
        for seed, vector in zip(seeds, vectors, strict=True)
    ]
    return RetrievalEngine(
        library=InMemoryFragmentLibrary(frags), embedder=LocalHashEmbedder()
    )


def test_supply_window_anchor_seat_within_budget() -> None:
    """V2-89b 正面对照：预算有余（三族各 1 席 → 余 1）→ 锚保底席照常进窗。

    真封顶只丢「超预算」的追加席——预算内的保底机制零回归（`over_budget=False`）。
    """
    ranked = _capped_ranked_all()
    plain = supply_window(ranked, 4, ())
    assert [p[0].fragment.fragment_id for p in plain.window] == [
        "f-cap-d1", "f-cap-m1", "f-cap-b1", "f-cap-m2",
    ]
    assert _CAP_RPT_T[1] in plain.missing_sources  # 前置：目标报告零席位（余量给了庚报告）

    supply = supply_window(ranked, 4, (), anchors=("T-77",))
    assert len(supply.window) == 4  # 预算 3 席＋保底 1 席（守预算）
    assert supply.anchor_seated == (_CAP_RPT_T[1],)
    assert supply.over_budget is False  # 预算内追加——不记超预算
    assert supply.window[-1][0].fragment.fragment_id == "f-cap-t1"
    assert _CAP_RPT_T[1] not in supply.missing_sources


def test_supply_window_anchor_multiple_tokens_one_source_one_seat() -> None:
    """多锚命中同一来源：保底恰 1 席，不重复追加（来源级去重——预算内）。"""
    supply = supply_window(
        _capped_ranked_all(), 4, (), anchors=("T-77", "专项分析")
    )
    reports = [p[0].fragment.report for p in supply.window]
    assert reports.count(_CAP_RPT_T[1]) == 1
    assert _CAP_RPT_T[1] not in supply.missing_sources


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
    # 34-8 命中的目标报告已获席——保底未触发（无扩席实录段）
    assert "以下条目因直接命中提问关键词获得保留" not in note
    assert "以下来源因数量限制未纳入：C-渤中34-5油田三季度注水调整与生产运行分析" in note


# ---------- 钉四：表类整行集（目标表格片段整组进窗——不计入配额） ----------


def test_supply_window_rowset_group_enters_whole() -> None:
    """V2-89b 改判：表类问句——目标表格片段的同报告同 section 整组补席**守预算**。

    预算 6（三族配额 3 席＋锚保底 1 席＋余 2）下：锚「Y-24」把表格支 f-cap-t3
    保底进窗，行集通道再把同 section 解读支 f-cap-t4 补入（+1 条）；窗支数 ≤ 预算。
    """
    supply = supply_window(
        _capped_ranked_all(), 6, (), anchors=("Y-24",), rowset_question=True
    )
    window_ids = [p[0].fragment.fragment_id for p in supply.window]
    # 目标表格支 f-cap-t3 与同 section 解读支 f-cap-t4 全组在窗（表内行＋表外解读）。
    assert "f-cap-t3" in window_ids
    assert "f-cap-t4" in window_ids
    assert len(window_ids) <= 6  # 真封顶（含全部追加席）
    assert supply.rowset_added == 1
    assert supply.anchor_seated == (_CAP_RPT_T[1],)
    assert supply.over_budget is False


def test_supply_window_rowset_requires_table_question() -> None:
    """非表类问句：同语料同锚——无整组扩席（行集规则只随题型解锁）。"""
    supply = supply_window(_capped_ranked_all(), 6, (), anchors=("Y-24",))
    window_ids = [p[0].fragment.fragment_id for p in supply.window]
    assert "f-cap-t3" in window_ids  # 锚保底照在
    assert "f-cap-t4" not in window_ids  # 整组通道关闭
    assert supply.rowset_added == 0


def test_supply_window_rowset_requires_anchor_hit_on_table() -> None:
    """锚在场时目标表格片段须锚命中（防无关报告的高位表格片被误当目标）。

    锚「T-77」命中目标报告名（f-cap-t1 保底进窗）但表格支 f-cap-t3 文本不含
    该锚——整组不误扩（rowset_added=0）；预算 4 恰容配额 3＋保底 1，余量无位
    ——表格支不得借余量进窗（判据可判）。
    """
    supply = supply_window(
        _capped_ranked_all(), 4, (), anchors=("T-77",), rowset_question=True
    )
    window_ids = [p[0].fragment.fragment_id for p in supply.window]
    assert "f-cap-t1" in window_ids  # 锚保底照在（报告名命中 T-77）
    assert "f-cap-t3" not in window_ids  # 表格支不含 T-77——整组不扩
    assert supply.rowset_added == 0


async def test_retrieve_rowset_window_note_truthful() -> None:
    """引擎面端到端：表类问句整组进窗，window_note 数字照实按实走（守预算）。

    V2-89b 改判：预算 3（两族配额 2 席＋余 1）下整组解读支补入——送窗 M＝实际
    支数且恒 ≤ 预算；旧形「送窗 M＞配额」的扩席不封顶已按 D3 收正（本形旧断言
    为「3 条用进了答案」但窗支数 4——超预算；现窗支数＝3）。
    """
    bundle = await _engine().retrieve(
        RetrievalNeed(
            question="渤中34-8 油田 5.2 配注调整表中 Y-24 与 Y-26 的执行日期",
            budget=3,
        )
    )
    window_ids = [obs.fragment_id for obs in bundle.observations]
    assert len(window_ids) == 3  # 真封顶（配额 2＋整组增量 1＝预算）
    assert "f-t1" in window_ids and "f-t2" in window_ids
    note = bundle.window_note
    assert note.startswith("共检索到 6 条材料，3 条用进了答案")  # 实走计数
    assert "目标表格的整组数据行已进窗（+1 条，不占送入答案的数量）" in note
    assert bundle.rowset_added == 1
    assert bundle.over_budget is False
    assert any("Y-24" in obs.text for obs in bundle.observations)  # 表格行真支在窗
    assert "未纳入" not in note  # 两报告均已获席——无未纳入来源可列


# ---------- 钉五（V2-82d）：题面主体保底席位（命中面 text ∪ report ∪ well） ----------

# 语料布点＝B6 病灶确定性缩影：题面点名的主体只落在报告名（油田名）或 well
# 本体标签（井号）里，切片正文一律不含锚词——text-only 判据下保底席配不上。
_D_LIB_DYN = ("lib-d1", "渤中34-5动态分析库", "dynamic")
_D_LIB_MON = ("lib-d2", "渤中34-5综合月报库", "monthly")
_RPT_COMP = ("rpt-comp", "O-三季度注水情况专项分析")
_RPT_OWN = ("rpt-own", "渤中34-5油田开发动态分析")
_RPT_WELL = ("rpt-well", "杆断根因专项分析")
_WELL_TAG = "W-22井·数值模拟平台"
_OWN_NEEDLE = "34-5"
_WELL_NEEDLE = "W-22"


def _d_fragments() -> list[FragmentRecord]:
    """四支片段：dynamic 族竞争报告两支（题面词面强命中）＋monthly 族主体承载支两支。

    主体承载支的正文都不含锚词——油田名只在报告名、井号只在 well 标签
    （f-po1/f-pw1 正文逐字无「34-5」/「W-22」）。
    """
    return [
        _frag("f-pc1", _D_LIB_DYN, _RPT_COMP, "1.1 主要生产指标",
              "三季度注水情况：月注采比 0.98 进入 0.95～1.05 区间，注水量 9.26 万m³。"),
        _frag("f-pc2", _D_LIB_DYN, _RPT_COMP, "2.1 注水月度数据",
              "注水情况说明：三季度注水量按月分配，计划完成率 102%。"),
        _frag("f-po1", _D_LIB_MON, _RPT_OWN, "全文档摘要",
              "本报告由地质所与工艺所联合编制，数据经三级审核后发布。"),
        _frag("f-pw1", _D_LIB_MON, _RPT_WELL, "4.1 杆断根因",
              "该井检泵周期 215 天，杆管偏磨为主要根因。", well=_WELL_TAG),
    ]


def _d_ranked_all() -> list[tuple[Hit, float]]:
    """融合序替身（直接驱动 supply_window——seed 序给单调递减分）。"""
    return [
        (Hit(frag, 1.0 / (i + 1), "keyword"), 1.0 / (i + 1))
        for i, frag in enumerate(_d_fragments())
    ]


def _d_engine() -> RetrievalEngine:
    return RetrievalEngine(
        library=InMemoryFragmentLibrary(_d_fragments()),
        embedder=LocalHashEmbedder(),
    )


def test_supply_window_anchor_seat_hits_report_name() -> None:
    """切片正文不含锚词、报告名含 → 该来源仍获保底席（V2-82d 三面命中面主钉）。

    V2-89b 改判：预算 4（三族各 1 席 → 余 1）——保底席在预算内照常进窗。
    """
    ranked = _capped_ranked_all()
    plain = supply_window(ranked, 4, ())
    assert _CAP_RPT_T[1] in plain.missing_sources  # 前置：主体承载来源零席位形在场
    # 前置：目标支正文不含锚词——报告名是唯一命中面（text-only 判据下必不保底）。
    own = [f for f in _capped_fragments() if f.fragment_id == "f-cap-t1"]
    assert own and all("T-77" not in f.text for f in own)
    assert all(f.well is None or "T-77" not in f.well for f in own)

    supply = supply_window(ranked, 4, (), anchors=("T-77",))
    assert supply.anchor_seated == (_CAP_RPT_T[1],)  # 留痕记账面（引擎侧原样渲染）
    assert _CAP_RPT_T[1] not in supply.missing_sources
    # 保底支＝该来源融合序最优一支（f-cap-t1 在 ranked 中先于 f-cap-t3/f-cap-t4）。
    assert [p[0].fragment.fragment_id for p in supply.window][-1] == "f-cap-t1"


def test_supply_window_anchor_seat_hits_well_label() -> None:
    """井号锚只落在 frag.well 本体标签里 → 该来源获保底席（预算内）。"""
    ranked = _capped_ranked_all()
    plain = supply_window(ranked, 4, ())
    assert _CAP_RPT_T[1] in plain.missing_sources

    well_frag = next(f for f in _capped_fragments() if f.fragment_id == "f-cap-t1")
    assert well_frag.well == _CAP_WELL_TAG
    # 前置：正文与报告名都不含井号——well 标签是唯一命中面。
    assert "W-22" not in well_frag.text.casefold()
    assert "W-22" not in well_frag.report.casefold()

    supply = supply_window(ranked, 4, (), anchors=("W-22",))
    assert supply.anchor_seated == (_CAP_RPT_T[1],)
    assert _CAP_RPT_T[1] not in supply.missing_sources
    assert [p[0].fragment.fragment_id for p in supply.window][-1] == "f-cap-t1"


def test_supply_window_anchor_seat_text_face_unchanged() -> None:
    """命中面放宽是超集：正文词面命中照旧保底（旧判据零回归——预算内）。"""
    supply = supply_window(_capped_ranked_all(), 6, (), anchors=("Y-24",))
    assert supply.anchor_seated == (_CAP_RPT_T[1],)
    # 表格支文本含 Y-24——保底支取该来源融合序最优命中支（f-cap-t3）。
    assert [p[0].fragment.fragment_id for p in supply.window][-1] == "f-cap-t3"


async def test_retrieve_numeric_core_anchor_hits_report_name_note_visible() -> None:
    """引擎面端到端（B-正6 缩影）：题面点名油田→资产编号形锚命中报告名→保底进窗＋留痕可见。

    锚「T-77」由题面词面确定性产出（问句资产编号形）；报告名含该编号即视为
    命中——行为可解释：报告名是出处链一级键，题面点名的主体落在报告名上就是
    该来源的题眼命中（目标支正文不含该词——text-only 判据下此来源零席位）。
    三族竞争下目标报告（monthly·T-77）非族首——预算 4（三族各 1 席＋余 1）
    保底席进窗；预算 3（吃满）则被丢并如实缺位（V2-89b D3 两侧对照）。
    """
    assert anchor_seat_tokens("注水月度 T-77 情况如何") == ("T-77",)
    engine = await _note_engine()
    bundle = await engine.retrieve(
        RetrievalNeed(question="注水月度 T-77 情况如何", budget=4)
    )
    window_ids = [obs.fragment_id for obs in bundle.observations]
    assert len(window_ids) == 4  # 真封顶（三族 3 席＋保底 1 席）
    assert "f-note-t1" in window_ids  # 点名的报告切片保底进窗
    # 扩席实录可见（锚保底段＝用户语逐字）
    assert "以下条目因直接命中提问关键词获得保留：T-77 井专项分析报告" in bundle.window_note
    assert bundle.anchor_seated == 1
    assert bundle.over_budget is False

    # 预算吃满侧：配额 3 席＝预算 3 → 保底候选被丢，over_budget 如实、零席位入缺位。
    capped = await engine.retrieve(
        RetrievalNeed(question="注水月度 T-77 情况如何", budget=3)
    )
    assert len(capped.observations) == 3
    assert capped.over_budget is True
    assert capped.anchor_seated == 0
    assert "以下条目因直接命中提问关键词获得保留" not in capped.window_note
    assert "以下来源因数量限制未纳入：T-77 井专项分析报告" in capped.window_note

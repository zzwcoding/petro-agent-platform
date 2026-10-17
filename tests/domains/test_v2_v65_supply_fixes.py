"""V2-65 供给面两闸钉测（问题块退赛＋代表席摘要优先——Owner 2026-10-12 拍板 1+2）。

附 A（问题块退赛）：kb_fragment.type='问题块'（入库 enrich 批生成的「这份报告
可能被问的 10 个问题」展示面专用切片）不参加检索排序——通篇问句零答案内容、
逐字包含报告关键题眼，融合分天然抢占代表席（V264F1 实锤：12 支占语料 8%，
抢走 6 席中 3 席；B-正1 帧 34-8 月报唯一席位即一支问题块）。判定用结构字段
frag_type，零语义。

附 B（代表席摘要优先）：每来源队列若含节级摘要支（node_kind=section_summary
结构标记，零语义），以其为队首——代表席＝摘要席，进窗即触发既有 R1b 节内
整组展开（1 席撬一节，数据正文随摘要进窗）。无摘要支队列原样（零漂移）。

红线钉：不动排序/召回算法本体；无问题块无摘要支的语料，选窗输出逐支不变。
"""

from __future__ import annotations

from appv2.retrieval import (
    NODE_SECTION_SUMMARY,
    NODE_SLICE,
    QUESTION_BLOCK_TYPE,
    FragmentRecord,
    Hit,
    InMemoryFragmentLibrary,
    LocalHashEmbedder,
    RetrievalEngine,
    RetrievalNeed,
    source_diversify,
)

_LIB = ("lib-1", "完井报告类", "completion")
_RPT_A = ("rpt-a", "《A-W11井完井工程报告》")
_RPT_T = ("rpt-t", "渤中34-8油田一季度注采调整与生产运行分析")


def _frag(
    fid: str,
    section: str,
    text: str,
    *,
    report: tuple[str, str] = _RPT_A,
    family: str = "completion",
    node_kind: str = NODE_SLICE,
    frag_type: str = "原文块",
) -> FragmentRecord:
    return FragmentRecord(
        fragment_id=fid,
        report_id=report[0],
        report=report[1],
        section=section,
        library_id=_LIB[0],
        library=_LIB[1],
        family=family,
        text=text,
        node_kind=node_kind,
        frag_type=frag_type,
    )


def _ranked(frags: list[FragmentRecord]) -> list[tuple[Hit, float]]:
    """融合序替身（seed 序给单调递减分——与 r1a 钉测同形）。"""
    return [
        (Hit(frag, 1.0 / (i + 1), "keyword"), 1.0 / (i + 1))
        for i, frag in enumerate(frags)
    ]


# ---------- 附 A：问题块退赛（engine 语料装配单点过滤） ----------


def test_fragment_record_frag_type_default_zero_drift() -> None:
    """frag_type 缺省＝内容主型——既有构造面（切片/摘要节点）零漂移。"""
    assert _frag("f-a", "s", "正文").frag_type == "原文块"
    assert _frag(
        "ensum", "s", "节级摘要", node_kind=NODE_SECTION_SUMMARY
    ).frag_type == "原文块"


async def test_question_block_never_enters_window() -> None:
    """问题块词面最贴题也不进窗（不召回/不送窗）——f-q 若参赛必夺首席。"""
    frags = [
        _frag("f-a", "章节 02 完井液", "完井液密度实测：二开 1.08、三开 1.05 g/cm³。"),
        _frag("f-b", "章节 02 完井液 ＞ 2.2 设计对照", "完井液密度设计值 1.10 g/cm³。"),
        _frag(
            "f-q",
            "问题块·第1批",
            "完井液密度各是多少？选择依据是什么？",
            frag_type=QUESTION_BLOCK_TYPE,
        ),
    ]
    engine = RetrievalEngine(
        library=InMemoryFragmentLibrary(frags), embedder=LocalHashEmbedder()
    )
    bundle = await engine.retrieve(RetrievalNeed(question="完井液密度各是多少", budget=6))
    ids = {obs.fragment_id for obs in bundle.observations}
    assert "f-q" not in ids  # 问题块退赛——即便词面最贴也不进窗
    assert ids == {"f-a", "f-b"}  # 其余语料照常参赛
    assert bundle.window_note.startswith("共检索到 2 条材料")  # 计数照实（不含退赛支）


# ---------- 附 B：代表席摘要优先（source_diversify 单点） ----------


def test_source_diversify_summary_head_wins_representative_seat() -> None:
    """摘要支居融合序中游仍夺代表席——队首置换，非摘要成员相对序不动。"""
    w1 = _frag("w1", "章节 01", "正文一。")
    w_sum = _frag("w-sum", "章节 02", "节级摘要：本章要点。", node_kind=NODE_SECTION_SUMMARY)
    w2 = _frag("w2", "章节 03", "正文二。")
    y1 = _frag("y1", "章节 01", "另一报告正文。", report=_RPT_T, family="monthly")
    # 融合序：w1, w_sum, w2, y1（摘要居中游）——cap=2 → 每源 1 席。
    members = _ranked([w1, w_sum, w2, y1])
    picked = source_diversify(members, 2)
    assert [p[0].fragment.fragment_id for p in picked] == ["w-sum", "y1"]


def test_source_diversify_no_summary_zero_drift() -> None:
    """无摘要支：队列原样——输出与旧算法逐支一致（零漂移钉）。"""
    w1 = _frag("w1", "章节 01", "正文一。")
    w2 = _frag("w2", "章节 02", "正文二。")
    y1 = _frag("y1", "章节 01", "另一报告正文。", report=_RPT_T, family="monthly")
    picked = source_diversify(_ranked([w1, w2, y1]), 2)
    assert [p[0].fragment.fragment_id for p in picked] == ["w1", "y1"]


async def test_summary_representative_seat_triggers_expansion() -> None:
    """引擎级：摘要支夺代表席后 R1b 节内展开随席触发（1 席撬一节）。"""
    frags = [
        _frag("f-c1", "章节 01 概述", "完井液密度实测：二开 1.08、三开 1.05。"),
        _frag(
            "f-t1", "章节 02 注水月度 ＞ 2.1 数据表",
            "2.1 数据表：月注采比 0.98。", report=_RPT_T, family="monthly",
        ),
        _frag(
            "f-t2", "章节 02 注水月度 ＞ 2.2 解读",
            "2.2 解读：注采比回升 0.02。", report=_RPT_T, family="monthly",
        ),
        _frag(
            "ensum-t", "章节 02 注水月度",
            "节级摘要：月度注采比与配注要点汇总。",
            report=_RPT_T, family="monthly", node_kind=NODE_SECTION_SUMMARY,
        ),
    ]
    engine = RetrievalEngine(
        library=InMemoryFragmentLibrary(frags), embedder=LocalHashEmbedder()
    )
    bundle = await engine.retrieve(RetrievalNeed(question="完井液密度与注采比", budget=2))
    ids = {obs.fragment_id for obs in bundle.observations}
    assert "ensum-t" in ids  # 摘要支夺 monthly 族代表席
    assert {"f-t1", "f-t2"} <= ids  # 同节切片经 R1b 展开补席（追加席不计配额）
    assert "命中的章节摘要已展开为节内材料" in bundle.window_note  # 扩席实录如实


async def test_engine_without_summary_zero_drift() -> None:
    """零漂移钉：同语料去摘要支——窗构成回旧形（无展开段）。"""
    frags = [
        _frag("f-c1", "章节 01 概述", "完井液密度实测：二开 1.08、三开 1.05。"),
        _frag(
            "f-t1", "章节 02 注水月度 ＞ 2.1 数据表",
            "2.1 数据表：月注采比 0.98。", report=_RPT_T, family="monthly",
        ),
        _frag(
            "f-t2", "章节 02 注水月度 ＞ 2.2 解读",
            "2.2 解读：注采比回升 0.02。", report=_RPT_T, family="monthly",
        ),
    ]
    engine = RetrievalEngine(
        library=InMemoryFragmentLibrary(frags), embedder=LocalHashEmbedder()
    )
    bundle = await engine.retrieve(RetrievalNeed(question="完井液密度与注采比", budget=2))
    ids = {obs.fragment_id for obs in bundle.observations}
    assert len(ids) == 2  # 两族各一席——无展开追加席
    assert ids <= {"f-c1", "f-t1", "f-t2"}  # 月度族代表席＝切片（融合序定，非摘要）
    assert "命中的章节摘要已展开为节内材料" not in bundle.window_note  # 无展开段（零漂移）

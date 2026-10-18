"""V2-04 retrieval 检索引擎验收——specs/retrieval.md「验收测试」表六条逐条落测。

六条对应（票面验收表，1:1 同名）：
- rerank_fallback：LLM 精排挂（调用抛错/解析坏）→确定性配额兜底结果仍可用——
  与无精排引擎产出同序同集（回退＝融合序，W-F34-2 回退不炸链）；精排面
  至多两次 LLM 调用（批量排序＋来源置信度，specs/retrieval.md 不做什么节）。
- contradiction_same_window：同型双报告 A-W11/Y-21 同主题（防砂方式与精度，
  两报告参数互斥：150 微米/占船日 3.5 天 vs 175 微米/占船日 4.0 天）→两报告
  各≥1 支同窗并立，window_note 点名两来源——供给层硬规则（代码不依赖 LLM
  自觉，Q11 P0-2 同型抢锚病灶的治侧面）。
- window_note_explicit：检索 21 条材料用进答案 4 条→window_note 如实含「共检索到
  21 条材料，4 条用进了答案」数字（截断显式——agent 据此区分「没有」与「没送」）。
- provenance_chain：每支 Observation 出处链完整（fragment→report→library
  三级逐级在场）＋family 标注（库 biz_template 透传）＋locator 携 library/
  报告名（同型文档来源标注——锚错 A-W11 vs Y-21 可被核验步发现）。
- family_supply：family_hints 驱动供给——完井族题（hints=[completion]）送窗
  3+1 分池（月报族保底 1 席不被挤占）；无 hints 同题同预算→两族均分——
  族配额行为两侧对照。
- graph_surface：图谱面邻域边证据带出处（边锚片段台账 fail-closed 校验——
  失锚边拦截并计数）；图谱源挂/未接线→空集回退不炸（observations 空列＋
  window_note 如实声明，零异常）。

fixture＝V1 片段库抽样（eval/reports 与 eval/drafts-q4/reports 三份真报告逐字
摘录：A-W11 井完井工程报告·渤中34-5／Y-21 井完井工程报告·渤中34-8／渤中34-5
油田 2026 年 8 月躺井治理与检泵作业月报——业务事实零发明，含票面点名的同型
双报告 A-W11/Y-21 对）；embedder＝LocalHashEmbedder 桩（V1 同款确定性哈希
向量——非语义向量，测试底座）；图谱源/精排 completer＝测试桩（V1 先例——
caller 分流应答）。真 MiniMax 冒烟另 gated（RETRIEVAL_SMOKE=1，不进门禁）。
"""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import date
from typing import Any

import pytest

from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
from appv2.retrieval import (
    FAMILY_ALL,
    NODE_SECTION_SUMMARY,
    NODE_SLICE,
    FragmentRecord,
    GraphEdgeRecord,
    Hit,
    InMemoryFragmentLibrary,
    LocalHashEmbedder,
    RetrievalEngine,
    RetrievalNeed,
    supply_window,
)
from appv2.retrieval.domain import SECTION_EXPAND_CAP
from appv2.tools import dump_from_store, inject_retrieval_anchors

# ---------- fixture：V1 片段库抽样（三报告真摘录，逐字取自 eval 报告文本） ----------

_LIB_A = ("lib-comp-a", "渤中34-5完井工程库", "completion")
_LIB_Y = ("lib-comp-y", "渤中34-8完井工程库", "completion")
_LIB_M = ("lib-monthly-b", "渤中34-5躺井月报库", "monthly")
_RPT_A = ("rpt-a", "A-W11井完井工程报告")
_RPT_Y = ("rpt-y", "Y-21井完井工程报告")
_RPT_M = ("rpt-m", "B-渤中34-5油田躺井治理与检泵作业月报-202608")

_MONTHLY_HEAD = "渤中 34-5 油田 2026 年 8 月躺井治理与检泵作业月报："


def _frag(
    fid: str,
    lib: tuple[str, str, str],
    rpt: tuple[str, str],
    section: str,
    text: str,
    node_kind: str = NODE_SLICE,
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
        node_kind=node_kind,
    )


def _fragment_seeds() -> list[FragmentRecord]:
    """21 支片段种子（真报告逐字摘录——A-W11 八支／Y-21 九支／月报四支）。

    摘录源：eval/reports/A-W11井完井工程报告.txt、eval/drafts-q4/reports/
    Y-21井完井工程报告.txt、eval/reports/B-渤中34-5油田躺井治理与检泵作业
    月报-202608.txt（月报各支携报告题头原句前缀——检索面可命中的真实出处名）。
    """
    return [
        # —— A-W11（渤中34-5·completion 族）——
        _frag("f-a1", _LIB_A, _RPT_A, "第四章 4.2 防砂方式与参数",
              "防砂方式：精密冲缝筛管适度防砂（不砾石充填）。筛管类型：精密冲缝筛管"
              "（Star-PS 型）；防砂精度：150 微米（0.15 毫米）。本井未采用砾石充填："
              "一是油层均质性较好，二是充填作业占船日 3.5 天，经济性评价不划算。"),
        _frag("f-a2", _LIB_A, _RPT_A, "第七章 诱导求产与初期产能",
              "12 mm 油嘴制度下折算日产油 386 m³/d（地面原油密度 0.865 t/m³，折算约"
              " 334 吨/日），生产压差 1.85 MPa，采油指数 208.6 m³/(d·MPa)，与邻井"
              " W-09 井初期产能相当。"),
        _frag("f-a3", _LIB_A, _RPT_A, "第三章 3.2 射孔参数",
              "全井射孔总厚度 28.0 米，按孔密 16 孔/米计算，设计总孔数 448 发，"
              "实发 448 发，发射率 100%。射孔方式：油管输送射孔（TCP）＋加压点火。"),
        _frag("f-a4", _LIB_A, _RPT_A, "第五章 完井管柱",
              "井下安全阀 SCSSV（285.3 米，液控，地面功能试验合格）；永久式封隔器"
              "坐封深度 1482.6 米，液压坐封，坐封压力 21 MPa，验封合格。"),
        _frag("f-a5", _LIB_A, _RPT_A, "第二章 2.2 完井液配方与维护",
              "完井液采用过滤海水＋氯化钾（KCl 浓度 3%）＋缓蚀剂 0.3%＋防膨剂 1.5%"
              " 体系，含油量检测小于 10 mg/L，悬浮固体颗粒粒径中值小于 2 微米。"),
        _frag("f-a6", _LIB_A, _RPT_A, "第六章 6.1 完井液漏失及堵漏",
              "第三段射孔起爆后循环时发生漏失，漏速由 2.1 m³/h 上升至最高 11.5 m³/h，"
              "累计漏失完井液 115 立方米。处理措施：配堵漏浆段塞式泵入漏层后静止"
              " 4 小时，循环压力恢复正常。"),
        _frag("f-a7", _LIB_A, _RPT_A, "第十章 邻井完井情况对照",
              "W-09 井未下防砂筛管（地层评价结论当时偏乐观），生产两年余未见出砂；"
              "W-07 井历史上曾发生筛管堵塞（2024 年 3 月），处理方式为酸洗解堵。"),
        _frag("f-a9", _LIB_A, _RPT_A, "第一章 1.1 井位与井别",
              "W-11 井位于渤中 34-5 油田三号构造高部位，CEP-C 生产平台西侧井槽 8 号位。"
              "本井为生产井，井型为常规定向井，设计井深 2530 米（垂深 2360 米）。"),
        # —— Y-21（渤中34-8·completion 族——与 A-W11 同型双报告）——
        _frag("f-y1", _LIB_Y, _RPT_Y, "第四章 4.2 防砂方式与参数",
              "防砂方式：精密冲缝筛管适度防砂（不砾石充填）。筛管类型：精密冲缝筛管"
              "（Star-PSⅡ 型）；防砂精度：175 微米（0.175 毫米）。本井不用砾石充填："
              "充填作业占船日 4.0 天，经济性不划算。"),
        _frag("f-y2", _LIB_Y, _RPT_Y, "第七章 7.3 诱导求产与工作制度确定",
              "12 mm 油嘴制度下日产液量 285 方，折算日产油 278.4 m³/d（地面原油密度"
              " 0.872 t/m³，折合日产油量 242.8 吨），生产压差 2.32 MPa，采油指数"
              " 120.0 m³/(d·MPa)，含水 2.3%。"),
        _frag("f-y3", _LIB_Y, _RPT_Y, "第三章 3.2 射孔参数（TCP）",
              "全井射孔总厚度 40.0 米，按孔密 16 孔/米计设计总孔数 640 发（三支枪"
              " 224、192、224 发），实发 640 发，发射率 100%。射孔方式：油管输送"
              "射孔（TCP）＋环空加压点火。"),
        _frag("f-y4", _LIB_Y, _RPT_Y, "第九章 结论与建议（4）",
              "注水井 Y-16 井计划 2026 年 12 月转注，分层配注 F1:200;F2:150（合计"
              " 350 m³/d），预计 Y-21 井 2027 年二季度起受效，地层压力保持率不低于"
              " 90%。"),
        _frag("f-y5", _LIB_Y, _RPT_Y, "第二章 2.1 各阶段钻井液性能（实际）",
              "四开钻穿 Es2 油层前实测地层压力 27.16 MPa（油层中深 2826 米，压力系数"
              " 0.98），据此定完井段密度 1.02 g/cm³，实现近平衡微正压。"),
        _frag("f-y6", _LIB_Y, _RPT_Y, "第六章 6.2 酸化施工泵压异常",
              "酸化挤注初期排量 0.5 m³/min 时，井口油压由 12.4 MPa 快速升至 23.6 MPa，"
              "判断为射孔压实带与完井液滤饼固相封堵孔眼、酸液未突破。处理：排量降至"
              " 0.25 m³/min、限压 24 MPa 憋压 30 分钟。"),
        _frag("f-y7", _LIB_Y, _RPT_Y, "第七章 7.2 酸化前后产能对比",
              "同一 8 mm 油嘴制度下，折算日产油由 156 m³/d 提高至 194 m³/d，增幅"
              " 24.4%；采油指数由 62.9 提高至 119.8 m³/(d·MPa)，提高 90.5%；表皮"
              "系数由 +3.2 降至 −1.5。"),
        _frag("f-y8", _LIB_Y, _RPT_Y, "第一章 1.1 井位与井别",
              "Y-21 井位于渤中 34-8 油田一号构造东高点，CEP-D 生产平台东侧井槽 12 号位。"
              "本井为生产井，常规定向井，设计井深 2980 米（垂深 2760 米）。"),
        _frag("f-y9", _LIB_Y, _RPT_Y, "第九章 结论与建议（3）",
              "酸化解堵使采油指数提高 90.5%，验证「射孔＋适度防砂＋土酸解堵」组合"
              "对本油田 Es2 疏松细砂储层的适应性。"),
        # —— B 月报（渤中34-5·monthly 族）——
        _frag("f-m1", _LIB_M, _RPT_M, "三、检泵作业明细",
              _MONTHLY_HEAD + "当月实施检泵作业 5 井次：W-21 检泵（杆断）检泵周期"
              " 512 天、作业费用 52.3 万元；W-23 检泵（泵漏）348 天；W-31 检泵"
              "（泵漏）466 天。"),
        _frag("f-m2", _LIB_M, _RPT_M, "一、月度生产与躺井总体情况",
              _MONTHLY_HEAD + "本月渤中 34-5 油田平均开井数 156 口，当月发生躺井"
              " 7 井次，躺井率 4.5%，抽油机时率 94.2%。"),
        _frag("f-m3", _LIB_M, _RPT_M, "二、躺井原因分类统计",
              _MONTHLY_HEAD + "杆断 3 井次（W-21、W-22、W-24），占躺井比例 42.9%；"
              "泵漏 2 井次（W-23、W-31）；其他 2 井次（W-32 皮带断、W-41 光杆密封盒"
              "刺漏）。"),
        _frag("f-m4", _LIB_M, _RPT_M, "一、月度生产与躺井总体情况（同比）",
              _MONTHLY_HEAD + "同比看，去年 8 月躺井 9 井次、躺井率 5.8%，今年同比"
              "下降 1.3 个百分点；环比 7 月（6 井次、3.8%）上升 0.7 个百分点。"),
    ]


async def _library() -> InMemoryFragmentLibrary:
    """片段库 fixture（向量预嵌——db 侧语义；embedder 桩与引擎同款确定性哈希）。"""
    embedder = LocalHashEmbedder()
    seeds = _fragment_seeds()
    vectors = await embedder.embed([seed.text for seed in seeds])
    frags = [
        replace(seed, embedding=vector) for seed, vector in zip(seeds, vectors, strict=True)
    ]
    return InMemoryFragmentLibrary(frags, edges=_graph_edges())


def _graph_edges() -> list[GraphEdgeRecord]:
    """图谱边 fixture（邻域——边出处按 V1 形状携 chunk_id/report_id；e2 失锚）。"""
    return [
        GraphEdgeRecord(
            entity_from="Y-16", rel="转注受效", entity_to="Y-21",
            evidence="注水井 Y-16 井计划 2026 年 12 月转注，预计 Y-21 井 2027 年"
                     "二季度起受效",
            chunk_id="f-y4", report_id=_RPT_Y[0], report=_RPT_Y[1],
            library_id=_LIB_Y[0], library=_LIB_Y[1], family=_LIB_Y[2],
        ),
        GraphEdgeRecord(  # 失锚边——chunk_id 不在片段台账（fail-closed 拦截对象）
            entity_from="Y-16", rel="历史配注", entity_to="Y-19",
            evidence="Y-16 井历史配注（台账外引用——锚不上片段）",
            chunk_id="f-missing", report_id=_RPT_Y[0], report=_RPT_Y[1],
            library_id=_LIB_Y[0], library=_LIB_Y[1], family=_LIB_Y[2],
        ),
        GraphEdgeRecord(  # 问句未点名——不在邻域
            entity_from="W-07", rel="筛管堵塞史", entity_to="W-11",
            evidence="W-07 井历史上曾发生筛管堵塞，处理方式为酸洗解堵",
            chunk_id="f-a7", report_id=_RPT_A[0], report=_RPT_A[1],
            library_id=_LIB_A[0], library=_LIB_A[1], family=_LIB_A[2],
        ),
    ]


async def _engine(**kwargs: Any) -> RetrievalEngine:
    library = await _library()
    kwargs.setdefault("graph", library)  # 内存库同时供图谱源（单测双面一对象）
    return RetrievalEngine(library=library, embedder=LocalHashEmbedder(), **kwargs)


# ---------- 精排/图谱测试桩 ----------


class _BoomCompleter:
    """精排 completer 桩：每次调用抛错（LLM 精排挂——回退路径的被测对象）。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def complete(self, alias: str, messages: list[dict[str, str]], *, caller: str,
                       **params: Any) -> Any:
        self.calls.append(caller)
        raise RuntimeError("上游精排服务挂（测试桩）")


class _GarbageCompleter:
    """精排 completer 桩：调用成功但内容不可解析（批量序/置信度双双解析坏）。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def complete(self, alias: str, messages: list[dict[str, str]], *, caller: str,
                       **params: Any) -> Any:
        self.calls.append(caller)

        class _Reply:
            content = "抱歉，我无法作答。"  # 无编号/无 JSON——两解析面都坏

        return _Reply()


class _BoomGraph:
    """图谱源桩：读图抛错（图存储不可用——空集回退被测对象）。"""

    async def graph_edges(self) -> list[GraphEdgeRecord]:
        raise RuntimeError("图存储不可用（测试桩）")


# ---------- 验收①：LLM 精排挂→确定性配额兜底结果仍可用 ----------


async def test_rerank_fallback() -> None:
    question = "完井防砂方式与防砂精度"
    need = RetrievalNeed(question=question, budget=4)

    baseline = await (await _engine()).retrieve(need)  # 无精排＝确定性配额基准

    # （a）completer 调用抛错：不炸链，兜底产出与基准同序同集（回退＝融合序）。
    boom = _BoomCompleter()
    bundle = await (await _engine(completer=boom)).retrieve(need)
    assert bundle.observations, "精排挂后兜底窗为空——回退不可用"
    assert bundle.observations == baseline.observations
    assert bundle.window_note == baseline.window_note
    assert len(boom.calls) == 2  # 批量排序＋来源置信度——精排面至多两次调用

    # （b）completer 应答不可解析：同款回退（解析坏按融合序放行，不炸链）。
    garbage = _GarbageCompleter()
    bundle2 = await (await _engine(completer=garbage)).retrieve(need)
    assert bundle2.observations == baseline.observations
    assert len(garbage.calls) == 2

    # （c）兜底窗本身仍守供给硬规则：同型双报告各≥1 支（确定性配额≠放弃分池；
    # 月报支可经向量腿同窗——哈希桩字符级命中所致，非回退缺陷）。
    reports = {obs.report for obs in bundle.observations}
    assert "A-W11井完井工程报告" in reports
    assert "Y-21井完井工程报告" in reports


# ---------- 验收②：同型两报告同主题→矛盾来源同窗并立 ----------


async def test_contradiction_same_window() -> None:
    engine = await _engine()
    bundle = await engine.retrieve(
        RetrievalNeed(question="完井防砂方式与防砂精度", budget=4)
    )
    reports = {obs.report for obs in bundle.observations}
    # 同型双报告（渤中34-5 A-W11 vs 渤中34-8 Y-21）各≥1 支进窗。
    assert "A-W11井完井工程报告" in reports
    assert "Y-21井完井工程报告" in reports
    # 矛盾参数两侧并立：150 微米（A-W11）与 175 微米（Y-21）同时在窗——
    # 供给层硬规则实现「同型报告不互相挤占、各留代表支」。
    window_text = "\n".join(obs.text for obs in bundle.observations)
    assert "150 微米" in window_text
    assert "175 微米" in window_text
    # window_note 点名两来源说法不一并立（如实声明——不靠生成端自觉）。
    assert "以下材料来源说法不一，各保留了代表条目：" in bundle.window_note
    assert "A-W11井完井工程报告" in bundle.window_note
    assert "Y-21井完井工程报告" in bundle.window_note


# ---------- 验收③：检索 21 条用进答案 4 条→window_note 如实含 N/M 数字 ----------


async def test_window_note_explicit() -> None:
    engine = await _engine()
    # 问句覆盖全部 21 支片段的判别单元（每支至少共享一个检索单元——含 Y-21
    # 转注受效支的转注/配注/受效单元）——召回池＝全集 21 支，送窗预算 4。
    bundle = await engine.retrieve(
        RetrievalNeed(
            question="完井 射孔 防砂 酸化 检泵 躺井 油嘴 封隔器 筛管 完井液 漏失"
                     " 油田 转注 配注 受效",
            budget=4,
        )
    )
    assert len(bundle.observations) == 4  # 用进答案数 M＝预算 4
    # 截断显式：检索/用进答案数字如实并排（specs/retrieval.md 行为约定 3 口径；
    # V2-82e 起措辞＝出厂即用户语）。
    assert "共检索到 21 条材料，4 条用进了答案" in bundle.window_note
    assert "另有 17 条已找到但未用进答案（受送入答案的数量限制）" in bundle.window_note
    assert (bundle.recalled, bundle.sent) == (21, 4)  # 计数结构化字段（V2-82e additive）
    # 三来源全部代表在窗（预算 4 ≥ 来源 3）——无未纳入枚举。
    assert "未纳入" not in bundle.window_note
    # 注记产文零旧行话字眼（V2-82e 验收 grep 断言——L0 改稿后「送窗/口径」亦清零）。
    assert not any(term in bundle.window_note for term in ("支", "召回", "送窗", "口径"))
    reports = {obs.report for obs in bundle.observations}
    assert len(reports) == 3


# ---------- 验收④：Observation 出处链完整＋family 标注 ----------


async def test_provenance_chain() -> None:
    engine = await _engine()
    bundle = await engine.retrieve(
        RetrievalNeed(question="完井防砂方式与防砂精度", budget=4)
    )
    assert bundle.observations
    for obs in bundle.observations:
        # 出处链三级逐级在场：fragment→report→library（specs 接口定义节原形）。
        assert obs.fragment_id, "缺 fragment 级出处"
        assert obs.report_id and obs.report, "缺 report 级出处"
        assert obs.library_id and obs.library, "缺 library 级出处"
        assert obs.section
        # family 标注＝库 biz_template 透传（闭世界四族——kb_library CHECK 同域）。
        assert obs.family in FAMILY_ALL
        # locator 携 library/报告名（同型文档来源标注——锚错可被核验步发现）。
        assert obs.locator["fragment_id"] == obs.fragment_id
        assert obs.locator["report"] == obs.report
        assert obs.locator["library"] == obs.library
        assert obs.locator["section"] == obs.section
        # score 恒原始腿分、leg 两路闭世界（精排只重排不改分——V1 同尺）。
        assert obs.score > 0.0
        assert obs.leg in ("vector", "keyword")
        assert obs.kind == "fragment"
    # 首支出处逐字段对上 fixture 真值（抽样核对——链条不是空转形状）。
    by_id = {seed.fragment_id: seed for seed in _fragment_seeds()}
    for obs in bundle.observations:
        seed = by_id[obs.fragment_id]
        assert (obs.report_id, obs.report) == (seed.report_id, seed.report)
        assert (obs.library_id, obs.library, obs.family) == (
            seed.library_id, seed.library, seed.family,
        )
        assert obs.text == seed.text
    # schema 定稿面：Need 闭世界校验（空白问句/零预算/未知族构造即拒）。
    with pytest.raises(ValueError):
        RetrievalNeed(question="   ")
    with pytest.raises(ValueError):
        RetrievalNeed(question="防砂", budget=0)
    with pytest.raises(ValueError):
        RetrievalNeed(question="防砂", family_hints=("nope",))


async def test_table_bearing_locator_marker() -> None:
    """V2-93：表格承载片段 locator 打 `table_bearing: True`（判据单点＝`domain._is_table_bearing`
    ——缩进数字行 ≥2）；非表格支不带该键（旧形零漂移）；切片不带 `node_kind`（V2-47 R1b 原形）。"""
    engine = await _engine()
    table = _frag(
        "f-tab",
        _LIB_M,
        _RPT_M,
        "三、检泵作业明细表",
        "检泵作业明细表：\n  443 井 2026-08-01 检泵\n  444 井 2026-08-02 检泵",
    )
    plain = _frag("f-plain", _LIB_M, _RPT_M, "一、概况", "本月躺井 3 井次。")
    table_obs = engine._fragment_observation(Hit(table, 1.0, "keyword"))
    plain_obs = engine._fragment_observation(Hit(plain, 1.0, "keyword"))
    assert table_obs.locator.get("table_bearing") is True
    assert "table_bearing" not in plain_obs.locator
    assert "node_kind" not in table_obs.locator  # 切片不带摘要机读位（旧形零漂移）


# ---------- 验收⑤：family_hints 驱动供给（完井族题不挤占月报族配额） ----------


async def test_family_supply() -> None:
    engine = await _engine()
    question = "渤中34-5油田完井防砂与检泵作业"
    hinted = await engine.retrieve(
        RetrievalNeed(question=question, family_hints=("completion",), budget=4)
    )
    by_family = {obs.family: 0 for obs in hinted.observations}
    for obs in hinted.observations:
        by_family[obs.family] += 1
    # 完井族题：completion 族拿大头（3 席），月报族保底 1 席不被挤占。
    assert by_family == {"completion": 3, "monthly": 1}

    # 对照组：同一问句同一预算、无族提示——两族均分（各 2 席）。
    plain = await engine.retrieve(RetrievalNeed(question=question, budget=4))
    plain_by_family: dict[str, int] = {}
    for obs in plain.observations:
        plain_by_family[obs.family] = plain_by_family.get(obs.family, 0) + 1
    assert plain_by_family == {"completion": 2, "monthly": 2}

    # 族提示在窗上的效果：hinted 下完井族席位多于月报族（供给策略本体化生效）。
    assert by_family["completion"] > by_family["monthly"]


# ---------- 验收⑥：图谱面——邻域边证据带出处，失败回退空集不炸 ----------


async def test_graph_surface() -> None:
    # （a）邻域遍历：问句点名实体（Y-16/Y-21）→一跳边；边出处 fail-closed——
    # 锚不上片段台账的边拦截计数，绝不带病出窗。
    engine = await _engine()
    bundle = await engine.graph(RetrievalNeed(question="Y-16 转注后 Y-21 何时受效？"))
    assert len(bundle.observations) == 1  # e1 在窗；e2 失锚被拦；e3 不在邻域
    obs = bundle.observations[0]
    assert obs.kind == "graph"
    assert obs.leg == "graph"
    assert obs.fragment_id == "f-y4"
    assert obs.report == "Y-21井完井工程报告"
    assert obs.library == "渤中34-8完井工程库"
    assert obs.locator["report"] == obs.report
    assert obs.locator["fragment_id"] == "f-y4"
    assert "失锚" in bundle.window_note  # 拦截留痕（fail-closed 计数）
    assert "共检索到 2 条材料，1 条用进了答案" in bundle.window_note  # 截断显式同尺

    # （b）图谱源挂：空集回退不炸（零异常＋如实声明）。
    broken = RetrievalEngine(
        library=await _library(), embedder=LocalHashEmbedder(), graph=_BoomGraph()
    )
    empty = await broken.graph(RetrievalNeed(question="Y-16 转注后 Y-21 何时受效？"))
    assert empty.observations == []
    assert "空集回退" in empty.window_note

    # （c）图谱缝未接线：同款空集回退（诚实缺位——不发明边）。
    unwired_engine = RetrievalEngine(
        library=await _library(), embedder=LocalHashEmbedder(), graph=None
    )
    unwired = await unwired_engine.graph(
        RetrievalNeed(question="Y-16 转注后 Y-21 何时受效？")
    )
    assert unwired.observations == []
    assert "空集回退" in unwired.window_note


# ---------- V2-82c：术语锚扩展→关键词腿（问别名、切片存正名） ----------

# 台账投影真源同产线一路（快照→读面→dump_from_store）——术语锚扩展的 dump 源。
LEDGER_DUMP = dump_from_store(
    InMemoryKnowledgeStore(question_array_snapshot(), today=date(2026, 10, 8))
)

# 切片种子用报告名（索引前缀进 BM25 词面——报告名不含问句单元，基线零命中可判）。
_RPT_TERM = ("rpt-term", "B-渤中34-5油田躺井治理月报-202608")


class _BoomEmbedder:
    """embedder 桩：调用抛错（向量腿按空腿——隔离关键词腿的被测面，V2-82c）。"""

    async def embed(self, texts: Any) -> Any:
        raise RuntimeError("embedder 不可用")


async def test_term_anchor_extension_recalls_canonical_fragment() -> None:
    """问别名（停产待检泵）＋切片存正名（躺井）：术语锚扩展经既有注入管道入关键词腿召回。

    基线与扩展同题对照——基线问句与切片零共享检索单元（关键词腿零命中），扩展后
    「躺井」入锚（别名→规范名），关键词腿命中入窗（术语加权的最小可判面）。
    """
    seeds = [
        _frag("f-t1", _LIB_M, _RPT_TERM, "一、月度躺井总体情况",
              "一、月度躺井治理总体情况：本月新增躺井 3 井次，其中 2 井次为杆断。"),
        _frag("f-a3", _LIB_A, _RPT_A, "第三章 3.2 射孔参数",
              "全井射孔总厚度 28.0 米，按孔密 16 孔/米计算，设计总孔数 448 发。"),
    ]
    engine = RetrievalEngine(
        library=InMemoryFragmentLibrary(seeds), embedder=_BoomEmbedder()
    )
    question = "W-41 井停产待检泵了吗？"

    # （a）基线：无锚——问句与两切片零共享检索单元→关键词腿零召回、窗空。
    base = await engine.retrieve(RetrievalNeed(question=question, budget=2))
    assert base.observations == []
    assert "共检索到 0 条材料" in base.window_note

    # （b）术语锚扩展：台账别名「停产待检泵」命中→规范名「躺井」入锚（既有注入管道）。
    merged = inject_retrieval_anchors({"question": question}, dump=LEDGER_DUMP)
    assert "躺井" in merged["anchors"]

    # （c）扩展后：关键词腿命中正名切片→入召回入窗（题面未出现「躺井」二字）。
    anchored = await engine.retrieve(
        RetrievalNeed(
            question=question, budget=2, anchors=tuple(merged["anchors"])
        )
    )
    assert [obs.fragment_id for obs in anchored.observations] == ["f-t1"]
    assert anchored.window_note.startswith("共检索到 1 条材料，1 条用进了答案")


# ---------- V2-89b：L1 预算真封顶＋`over_budget` 归因 ----------

# 扩席三通道齐备语料（锚保底/表类整行集/节级摘要展开都有候选）：C 报告（dynamic
# 族·hints 命中位）三支＋34-8 目标组（monthly 族）摘要支＋表格支＋同节解读支。
_BUD_LIB_C = ("lib-bud-c", "渤中34-5动态分析库", "dynamic")
_BUD_LIB_T = ("lib-bud-t", "渤中34-8动态分析库", "monthly")
_BUD_RPT_C = ("rpt-bud-c", "C-渤中34-5油田三季度注水调整与生产运行分析")
_BUD_RPT_T = ("rpt-bud-t", "渤中34-8油田一季度注采调整与生产运行分析")
_BUD_SECTION = "5.2 四月配注调整与计划注水量"
_BUD_TABLE_TEXT = (
    "5.2 四月配注调整与计划注水量\n"
    "　　井号　　　原配注(m³/d)　新配注(m³/d)　执行日期\n"
    "　　Y-24　　　320　　　　　 380　　　　　 4 月 12 日\n"
    "　　Y-26　　　260　　　　　 320　　　　　 4 月 20 日\n"
)
_BUD_QUESTION = "渤中34-8 油田 5.2 配注调整表中 Y-24 与 Y-26 的执行日期"


def _budget_corpus() -> list[FragmentRecord]:
    """扩席三通道候选齐备的六支语料（R1a 同形——锚/行集/展开都够候选）。"""
    return [
        _frag("f-bc1", _BUD_LIB_C, _BUD_RPT_C, "1.1 主要生产指标",
              "三季度综合含水率 79.0% 降至 78.3%。"),
        _frag("f-bc2", _BUD_LIB_C, _BUD_RPT_C, "2.1 注水月度数据",
              "月注采比 0.98，注水量 9.26 万m³。"),
        _frag("f-bc3", _BUD_LIB_C, _BUD_RPT_C, "4.1 累积亏空",
              "渤中34-5 油田累积亏空 −41.3 万方。"),
        _frag("ensum-bt", _BUD_LIB_T, _BUD_RPT_T, _BUD_SECTION,
              "节级摘要：四月配注调整与计划注水量要点汇总。",
              node_kind=NODE_SECTION_SUMMARY),
        _frag("f-bt1", _BUD_LIB_T, _BUD_RPT_T, _BUD_SECTION, _BUD_TABLE_TEXT),
        _frag("f-bt2", _BUD_LIB_T, _BUD_RPT_T, _BUD_SECTION,
              "环比解读：Y-24 与 Y-26 两行执行日期极易对调。"),
    ]


def _budget_ranked() -> list[tuple[Hit, float]]:
    """融合序替身（seed 序给单调递减分——直接驱动 supply_window）。"""
    return [
        (Hit(frag, 1.0 / (i + 1), "keyword"), 1.0 / (i + 1))
        for i, frag in enumerate(_budget_corpus())
    ]


async def _budget_engine() -> RetrievalEngine:
    embedder = LocalHashEmbedder()
    seeds = _budget_corpus()
    vectors = await embedder.embed([seed.text for seed in seeds])
    frags = [
        replace(seed, embedding=vector)
        for seed, vector in zip(seeds, vectors, strict=True)
    ]
    return RetrievalEngine(
        library=InMemoryFragmentLibrary(frags), embedder=LocalHashEmbedder()
    )


async def test_supply_window_never_exceeds_budget() -> None:
    """V2-89b D3 真封顶：扩席三通道候选齐备 → 窗支数恒 ≤ budget（engine 端到端）。

    构造＝题面同时解锁锚保底（34-8/Y-24/Y-26 资产编号）、表类整行集（「表中」
    词面）与节级摘要展开（窗内摘要支），三通道都有候选要追加；旧行为下窗支数
    超预算（锚保底/行集/展开各追加、实录「不占送入答案的数量」）——本钉以
    `len(observations) <= budget` 机检真封顶。
    """
    engine = await _budget_engine()
    budget = 2
    bundle = await engine.retrieve(
        RetrievalNeed(
            question=_BUD_QUESTION, family_hints=("dynamic",), budget=budget
        )
    )
    assert len(bundle.observations) <= budget  # 真封顶（含全部追加席）
    assert bundle.sent == len(bundle.observations)  # 计数结构化字段同实走
    assert bundle.over_budget is True  # 有追加席候选因预算被丢（归因机读位）


def test_over_budget_flag_true_when_dropped() -> None:
    """V2-89b：有追加席候选被预算丢 → `over_budget=True`；预算有余 → `False`。

    - 丢席形：hints=dynamic 使族配额吃满预算（2）——锚/行集/展开候选全部被丢；
    - 对照形：同语料同锚、预算 3 无 hints（两族各 1 席）→ 余量补给填满，无追加
      席候选被丢 → `over_budget=False`（标记不虚报）。
    """
    ranked = _budget_ranked()
    dropped = supply_window(
        ranked, 2, ("dynamic",),
        anchors=("34-8", "Y-24"), rowset_question=True, corpus=_budget_corpus(),
    )
    assert len(dropped.window) == 2  # 配额吃满预算
    assert dropped.over_budget is True
    assert dropped.rowset_added == 0  # 行集候选被丢（超预算不再追加）

    roomy = supply_window(ranked, 3, (), anchors=("34-8",))
    assert len(roomy.window) == 3
    assert roomy.over_budget is False


def test_section_expansion_capped_by_budget_and_upper_bound() -> None:
    """V2-89b：节内展开加上界——展开补席 ≤ 剩余预算且 ≤ `SECTION_EXPAND_CAP`。

    单族语料：召回池只含概况支＋节级摘要支（摘要支进窗），同节 10 支切片**未
    召回**（只在全语料 corpus 里）——展开通道从全语料取材，补席总数恒守
    `SECTION_EXPAND_CAP`（6）与预算双上界。
    """
    section = "第九章 检泵作业明细"
    slices = [
        _frag(f"f-x{i}", _BUD_LIB_T, _BUD_RPT_T, f"{section} ＞ {i} 支",
              f"第 {i} 支检泵明细：周期 {500 + i} 天。")
        for i in range(1, 11)
    ]
    summary = _frag("ensum-s", _BUD_LIB_T, _BUD_RPT_T, section,
                    "节级摘要：检泵明细要点。", node_kind=NODE_SECTION_SUMMARY)
    profile = _frag("f-s1", _BUD_LIB_T, _BUD_RPT_T, "第一章 概况", "概况：开井 156 口。")
    corpus = [profile, summary, *slices]
    ranked = [
        (Hit(frag, 1.0 / (i + 1), "keyword"), 1.0 / (i + 1))
        for i, frag in enumerate([profile, summary])
    ]
    supply = supply_window(ranked, 24, ("monthly",), corpus=corpus)
    assert len(supply.window) <= 24  # 预算真封顶
    assert supply.summary_expanded == SECTION_EXPAND_CAP  # 展开通道上界（10 支候选取 6）
    expanded_ids = {
        pair[0].fragment.fragment_id for pair in supply.window
    } - {"f-s1", "ensum-s"}
    assert len(expanded_ids) == SECTION_EXPAND_CAP  # 未召回节内切片按上界补席
    # 小预算：展开同时守剩余预算（补席数 ≤ budget - 已占席）。
    tight = supply_window(ranked, 4, ("monthly",), corpus=corpus)
    assert len(tight.window) <= 4
    assert tight.summary_expanded <= 2  # 4 - 2 已占席


# ---------- 真 MiniMax 冒烟（RETRIEVAL_SMOKE=1 门控——不进常规门禁） ----------


@pytest.mark.skipif(
    os.environ.get("RETRIEVAL_SMOKE") != "1",
    reason="真网关冒烟需 RETRIEVAL_SMOKE=1（真 MiniMax 线路——不进常规门禁）",
)
async def test_real_gateway_rerank_smoke(tmp_path: Any) -> None:
    """真装配冒烟：精排走 appv2 gateway（petro-main＝MiniMax-M3，B6 唯一出口）。

    跑法：RETRIEVAL_SMOKE=1 uv run pytest tests/domains/test_v2_retrieval.py -q
    凭证经 config/models.yaml ${MINIMAX_*} 占位符自 .env 解析；记账落 sqlite
    tmp 网关库；片段向量仍 LocalHashEmbedder（冒烟只验 complete 面——零嵌入成本）。
    """
    from appv2.infra.config import load_models_config
    from appv2.infra.db import ConnectionManager, DatabaseSpec
    from appv2.infra.gateway import GatewayService
    from appv2.infra.gateway.store import ensure_gateway_tables
    from appv2.infra.llm_client import LlmClient

    load_models_config()  # 真注册表（.env 凭证——MiniMax 线路）
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "v2-retrieval-smoke.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    try:
        await ensure_gateway_tables(manager.engine())
        gateway = GatewayService(manager, LlmClient())
        engine = RetrievalEngine(
            library=await _library(),
            embedder=LocalHashEmbedder(),
            completer=gateway,
        )
        bundle = await engine.retrieve(
            RetrievalNeed(question="完井防砂方式与防砂精度", budget=4)
        )
        assert bundle.observations, "真网关精排后窗为空"
        assert "共检索到" in bundle.window_note and "用进了答案" in bundle.window_note
        assert 0 < bundle.sent <= bundle.recalled  # 计数结构化字段随行（V2-82e additive）
        reports = {obs.report for obs in bundle.observations}
        assert "A-W11井完井工程报告" in reports and "Y-21井完井工程报告" in reports
    finally:
        await manager.dispose()

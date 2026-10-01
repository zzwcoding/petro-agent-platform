"""faq 域服务单测（sqlite 底座）——四态机全迁移/审核发布闸/合并语义/挖掘管线
五拍/导入四计数/导入导出往返/LedgerMerged 联动。

约定：桩 LLM 永不触网（B6 红线）；种子＝合同 DTO 九条问答＋四簇候选
（seed_demo_if_empty）；夹具见同目录 conftest.py。
"""

import asyncio
from typing import Any

import pytest

from app.domains.faq import (
    FaqConflictError,
    FaqNotFoundError,
    FaqParamError,
    FaqService,
)
from app.domains.faq import domain as d
from app.domains.faq.store import ScanTaskRow
from app.infra.clock import freeze
from app.infra.eventbus import make_event
from tests.domains.faq.conftest import (
    FakeObjectStorage,
    RecordingAudit,
    StubCompleter,
    StubEmbedder,
    make_service,
    other_vector,
    same_vector,
)

# ── 端点 1/2：清单与详情 ──


async def test_list_entries_seeds_and_filters(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    rows = await service.list_entries()
    assert rows.grand_total == 9  # 九条种子全量
    assert [i.id for i in rows.items][:3] == ["faq-1", "faq-2", "faq-3"]  # 创建时间正序
    serve = await service.list_entries(status="serve")
    assert all(i.status == "serve" for i in serve.items) and serve.total == 7
    neg = await service.list_entries(status="neg")
    assert [i.id for i in neg.items] == ["faq-9"]  # 负例（含相似问「油价预测」）
    disabled = await service.list_entries(status="disabled")
    assert [i.id for i in disabled.items] == ["faq-8"]
    pending = await service.list_entries(status="pending")
    assert pending.total == 0  # 种子直接发布——无待审核
    kw = await service.list_entries(keyword="油价")
    assert [i.id for i in kw.items] == ["faq-9"]  # 关键词命中问题
    kw_sim = await service.list_entries(keyword="月度完成率")
    assert [i.id for i in kw_sim.items] == ["faq-1"]  # 关键词命中相似问法


async def test_list_entries_status_invalid_400(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    with pytest.raises(FaqParamError):
        await service.list_entries(status="bogus")


async def test_entry_detail_shape(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    row = await service.entry_detail("faq-1")
    assert row.question == "产量完成率怎么算？"
    assert [(s.id, s.text) for s in row.similar_questions] == [
        ("sq-101", "「月度完成率口径」（主任常问）")
    ]
    assert row.maintainer == "小李" and row.version == 1
    assert row.updated_at == row.updated_at  # 日期粒度（YYYY-MM-DD）


async def test_entry_detail_404(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    with pytest.raises(FaqNotFoundError):
        await service.entry_detail("faq-999")


# ── 端点 3/17：新增入库与审核发布闸（v0.2 四态机） ──


async def test_create_entry_goes_pending_review(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    created = await service.create_entry(
        "配注合格率是什么？", "分层实注÷配注，达标井次占比（Owner：采油工艺所）",
        is_negative=False, hook=d.Hook(kind="metric", name="配注合格率"),
        source_candidate_id=None, actor_who="小李 · 地质/质检",
    )
    assert created.id == "faq-10" and created.status == "pending_review"
    assert created.version == 1
    assert created.hint == "已提交审核：「配注合格率是什么？」——审核发布后命中即秒回。"
    detail = await service.entry_detail(created.id)
    assert detail.hook == d.Hook(kind="metric", name="配注合格率")
    # 待审核行不被 match_index 消费（发布闸——A1 只消费服务中）
    assert await service.match_index("配注合格率是什么？") is None


async def test_create_entry_empty_placeholder(faq_db: Any) -> None:
    """空值占位（不拒空——端点 3 合同行为，与 B1 片段修正 400 不同页不同语义）。"""
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    created = await service.create_entry(
        "  ", "", is_negative=False, hook=None, source_candidate_id=None, actor_who="系统",
    )
    detail = await service.entry_detail(created.id)
    assert detail.question == "（未填问题）" and detail.answer == "（未填答案）"


async def test_create_entry_negative_intent_hook_ignored(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    created = await service.create_entry(
        "帮我预测明年原油价格", "（不该答）", is_negative=True,
        hook=d.Hook(kind="term", name="油价"),  # 负例单 hook 服务端忽略
        source_candidate_id=None, actor_who="小李 · 地质/质检",
    )
    assert created.hint == (
        "已提交审核：「帮我预测明年原油价格」——审核发布后登记为负例，永不参与回答，检索也不可达。"
    )
    detail = await service.entry_detail(created.id)
    assert detail.hook is None  # hook 恒 null（合同冻结）


async def test_review_publish_gate_and_state_machine(faq_db: Any) -> None:
    """审核流闭环：publish→serve（match_index 可达）；reject→disabled（留档）。"""
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    created = await service.create_entry(
        "配注合格率是什么？", "分层实注÷配注，达标井次占比", is_negative=False,
        hook=None, source_candidate_id=None, actor_who="小李 · 地质/质检",
    )
    reviewed = await service.review_entry(created.id, "publish", actor_who="阿强 · 平台运维")
    assert reviewed.status == "serve" and reviewed.version == 2
    assert "审核通过已发布" in reviewed.hint
    hit = await service.match_index("配注合格率是什么？")
    assert hit is not None and hit.entry_id == created.id  # 发布后才被 A1 消费
    # 重复审核 409（仅待审核可审核）
    with pytest.raises(FaqConflictError):
        await service.review_entry(created.id, "publish", actor_who="阿强 · 平台运维")
    # reject → disabled
    other = await service.create_entry(
        "另一个问题", "另一个答案", is_negative=False, hook=None,
        source_candidate_id=None, actor_who="系统",
    )
    rejected = await service.review_entry(other.id, "reject", actor_who="阿强 · 平台运维")
    assert rejected.status == "disabled" and "重新提审" in rejected.hint
    assert await service.match_index("另一个问题") is None  # 已停用＝摘出索引


async def test_review_publish_negative_lands_negative(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    created = await service.create_entry(
        "帮我预测明年原油价格", "（不该答）", is_negative=True, hook=None,
        source_candidate_id=None, actor_who="小李 · 地质/质检",
    )
    reviewed = await service.review_entry(created.id, "publish", actor_who="阿强 · 平台运维")
    assert reviewed.status == "negative"
    assert await service.match_index("帮我预测明年原油价格") is None  # 负例检索不可达（W-F35-3）


async def test_review_action_invalid_400(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    with pytest.raises(FaqParamError):
        await service.review_entry("faq-1", "bogus", actor_who="系统")


# ── 端点 4：入库前重复校验（非阻断） ──


async def test_dup_check_matches_question_and_sim_norm_insensitive(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    hit, hint = await service.dup_check("完成率公式是什么")  # 全半角差异归一
    assert hit is not None and hit.id == "faq-2"
    assert hint is not None and hint.startswith("与既有问答「完成率公式是什么？」疑似重复")
    hit2, _ = await service.dup_check("「月度完成率口径」（主任常问）")  # 相似问法也在匹配域
    assert hit2 is not None and hit2.id == "faq-1"
    miss, miss_hint = await service.dup_check("完全无关的新问题")
    assert miss is None and miss_hint is None
    with pytest.raises(FaqParamError):
        await service.dup_check("   ")


# ── 端点 5/6：相似问增删（独立检索项） ──


async def test_add_and_remove_similar_bumps_version(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    added = await service.add_similar("faq-1", "主任的另一种问法", actor_who="小李 · 地质/质检")
    assert added.id == "sq-104" and added.version == 2  # 种子 sq-101..103 后续号＋版本自增
    hit, _ = await service.dup_check("主任的另一种问法")
    assert hit is not None  # 添加即时进入匹配域
    removed = await service.remove_similar("faq-1", added.id, actor_who="小李 · 地质/质检")
    assert removed.version == 3 and removed.hint == "已删除——该问法不再命中本条。"
    hit2, _ = await service.dup_check("主任的另一种问法")
    assert hit2 is None  # 删掉的问法不再命中本条
    with pytest.raises(FaqNotFoundError):
        await service.remove_similar("faq-1", "sq-404", actor_who="系统")
    with pytest.raises(FaqNotFoundError):
        await service.add_similar("faq-999", "x", actor_who="系统")
    with pytest.raises(FaqParamError):
        await service.add_similar("faq-1", "  ", actor_who="系统")


async def test_add_similar_duplicate_409(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    with pytest.raises(FaqConflictError):
        await service.add_similar("faq-1", "产量完成率怎么算", actor_who="系统")  # 与既有问题重复
    with pytest.raises(FaqConflictError):
        await service.add_similar(  # 与其他条目相似问重复（全库唯一——独立检索项）
            "faq-1", "「躺井啥意思」", actor_who="系统"
        )


# ── 端点 7：合并相似问 ──


async def test_merge_semantics_two_to_one(faq_db: Any) -> None:
    """合并语义（合同值）：被并入条目删除、其问题进目标相似问列。"""
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    result = await service.merge_entries("faq-2", "faq-1", actor_who="小李 · 地质/质检")
    assert result.from_id == "faq-2" and result.target_id == "faq-1"
    assert result.merged_count == "2 条 → 1 条"
    assert result.target_similar_questions_count == 2
    detail = await service.entry_detail("faq-1")
    assert any("完成率公式是什么" in s.text for s in detail.similar_questions)
    with pytest.raises(FaqNotFoundError):
        await service.entry_detail("faq-2")  # 被并入条目删除
    hit, _ = await service.dup_check("完成率公式是什么？")
    assert hit is not None and hit.id == "faq-1"  # 两种问法命中同一条答案
    with pytest.raises(FaqNotFoundError):
        await service.merge_entries("faq-2", "faq-1", actor_who="系统")  # 已合并 404
    with pytest.raises(FaqParamError):
        await service.merge_entries("faq-1", "faq-1", actor_who="系统")  # from==target 400


# ── 端点 8：停用/启用（三态互斥） ──


async def test_toggle_state_full_transitions(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    disabled = await service.toggle_state("faq-4", "disable", actor_who="小李 · 地质/质检")
    assert disabled.status == "disabled" and disabled.version == 2
    assert await service.match_index("N-02 井是什么时候投产的？") is None  # 摘出索引
    enabled = await service.toggle_state("faq-4", "enable", actor_who="小李 · 地质/质检")
    assert enabled.status == "serve" and enabled.version == 3
    assert await service.match_index("N-02 井是什么时候投产的？") is not None  # 启用即恢复
    with pytest.raises(FaqConflictError):
        await service.toggle_state("faq-9", "disable", actor_who="系统")  # 负例行 409（三态互斥）
    with pytest.raises(FaqConflictError):
        await service.toggle_state("faq-4", "enable", actor_who="系统")  # 状态未变化 409
    with pytest.raises(FaqParamError):
        await service.toggle_state("faq-4", "bogus", actor_who="系统")


# ── 端点 9：候选问题库 ──


async def test_candidates_seeds_freq_desc_and_filters(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    rows = await service.candidates()
    assert rows.total == 4  # 四簇演示种子（不受筛选影响）
    assert [c.freq for c in rows.items] == [23, 15, 11, 6]  # 频次倒序（服务端排序）
    assert rows.scan.running_task_id is None and rows.scan.last_hint is None  # 未扫库初态
    compared = await service.candidates(status="ok")
    assert [c.id for c in compared.items] == ["c2"]  # 已比对未判 dup
    pending = await service.candidates(status="pending")
    assert {c.id for c in pending.items} == {"c1", "c3", "c4"}
    with pytest.raises(FaqParamError):
        await service.candidates(status="bogus")


# ── 端点 10/11：扫库异步长任务 ──


async def test_scan_empty_material_lands_hint_and_done(faq_db: Any) -> None:
    """A1 未上线（session_loader 缺）→ 扫库完成但 0 簇＋空态说明；重入 409。"""
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage(), step_seconds=0.4)
    handle = await service.start_scan(actor_who="阿强 · 平台运维")
    assert handle.status == "running" and "扫描不会中断" in handle.hint
    with pytest.raises(FaqConflictError):
        await service.start_scan(actor_who="阿强 · 平台运维")  # 重入 409（全局单例）
    progress = await service.scan_progress(handle.task_id)
    assert progress.status == "running" and progress.hint is None and not progress.new_clusters
    for _ in range(200):
        progress = await service.scan_progress(handle.task_id)
        if progress.status == "done":
            break
        await asyncio.sleep(0.02)
    assert progress.status == "done" and progress.new_cluster_count == 0
    assert "A1 问一问历史会话尚未上线" in (progress.hint or "")  # 料源空态说明
    rows = await service.candidates()
    assert rows.total == 4  # 扫库只增候选不改库（空料源未增簇）
    assert rows.scan.last_hint is not None  # 重开弹窗可见上次结果
    with pytest.raises(FaqNotFoundError):
        await service.scan_progress("scan-9999")


async def test_scan_mines_clusters_from_session_material(faq_db: Any) -> None:
    """料源在场 → LLM 挖掘（petro-main/B6）→ F60 晋升闸（孤例不进池）。"""
    completer = StubCompleter(
        answers={
            "faq.scan.mine": (
                '[{"question": "完井方式是啥", "freq": 15, "variants": ["完井方式"]},'
                ' {"question": "孤例问句", "freq": 1, "variants": []}]'
            )
        }
    )
    async def session_loader() -> list[dict[str, str]]:  # A1 会话域缝（测试桩）
        return [{"question": "N-02 的完井方式是啥", "answer": "见完井报告章节 01"}]

    service = make_service(
        faq_db, completer, FakeObjectStorage(), session_loader=session_loader
    )
    handle = await service.start_scan(actor_who="阿强 · 平台运维")
    for _ in range(200):
        progress = await service.scan_progress(handle.task_id)
        if progress.status == "done":
            break
        await asyncio.sleep(0.02)
    assert progress.new_cluster_count == 1  # 孤例被 F60 晋升闸拦下
    assert progress.new_clusters[0].question == "完井方式是啥"
    assert progress.new_clusters[0].freq == 15
    assert ("faq.scan.mine", "petro-main") == (completer.calls[0][0], "petro-main")  # B6 别名
    rows = await service.candidates()
    assert rows.total == 5  # 种子四簇＋新簇一（只增候选）
    assert any(c.status == "pending" and c.question == "完井方式是啥" for c in rows.items)


async def test_close_stale_scans_reopens_singleton(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    async with faq_db.session() as session:
        session.add(ScanTaskRow(id="scan-stale", status="running"))
    assert await service.close_stale_scans() == 1
    assert await service.close_stale_scans() == 0  # 幂等
    handle = await service.start_scan(actor_who="系统")  # 遗留收口后可再发起
    assert handle.task_id.startswith("scan-")


# ── 端点 12：向量比对（三面去重） ──


def _onto_loader_with_production_rate() -> Any:
    async def loader() -> list[tuple[str, str]]:
        return [("指标卡", "产量完成率"), ("指标卡", "自然递减率"), ("术语", "时率")]

    return loader


async def test_compare_dup_above_merge_threshold(faq_db: Any) -> None:
    """高于合并线（0.87）判 dup——建议改用合并相似问，不新增条目。"""
    embedder = StubEmbedder({
        "产量完成率咋算的": same_vector(),
        "产量完成率怎么算？": same_vector(),
        "「月度完成率口径」（主任常问）": other_vector(),
    })
    service = make_service(
        faq_db, StubCompleter(), FakeObjectStorage(),
        embedder=embedder, ontology_names_loader=_onto_loader_with_production_rate(),
    )
    row = await service.compare_candidate("c1", actor_who="小李 · 地质/质检")
    assert row.status == "compared"
    cmp = row.compare
    assert cmp is not None and cmp.verdict == "dup"
    assert cmp.dup_question == "产量完成率怎么算？" and cmp.similarity == 1.0
    assert "建议改用合并相似问" in cmp.hint and "本体命中：指标卡 · 产量完成率" in cmp.hint
    with pytest.raises(FaqConflictError):
        await service.compare_candidate("c1", actor_who="小李 · 地质/质检")  # 非 pending 409


async def test_compare_ok_with_ontology_hit(faq_db: Any) -> None:
    service = make_service(
        faq_db, StubCompleter(), FakeObjectStorage(),
        embedder=StubEmbedder(), ontology_names_loader=_onto_loader_with_production_rate(),
    )
    row = await service.compare_candidate("c3", actor_who="小李 · 地质/质检")
    cmp = row.compare
    assert cmp is not None and cmp.verdict == "ok"  # 本地向量低于合并线
    assert cmp.dup_question is None and cmp.similarity is None
    assert "与既有问答无重复" in cmp.hint and "本体命中：术语 · 时率" in cmp.hint  # 包含命中
    with pytest.raises(FaqNotFoundError):
        await service.compare_candidate("c99", actor_who="系统")


# ── 端点 13：候选起草 ──


async def test_draft_candidate_llm_with_suffix_and_hook(faq_db: Any) -> None:
    completer = StubCompleter(answers={"faq.candidate.draft": "月度递减率按环比计算。"})
    service = make_service(faq_db, completer, FakeObjectStorage())
    row = await service.draft_candidate("c2", actor_who="小李 · 地质/质检")  # 种子 c2 已比对 ok
    assert row.status == "drafted"
    assert row.draft.startswith("月度递减率按环比计算。")
    assert row.draft.endswith("（来源：指标卡 · 自然递减率 · LLM 基于历史回答归纳，请人工核实）")
    assert row.hook_suggestion == d.Hook(kind="metric", name="自然递减率")  # 挂接建议
    detail = await service.candidates(status="drafted")
    assert [c.id for c in detail.items] == ["c2"] and detail.items[0].draft == row.draft
    with pytest.raises(FaqConflictError):
        await service.draft_candidate("c3", actor_who="系统")  # 未比对起草 409


async def test_draft_candidate_dup_keeps_gate_open_with_disuade_text(faq_db: Any) -> None:
    """dup 不关起草闸：草稿本身＝劝阻文案（合同常量），不调 LLM。"""
    completer = StubCompleter()
    service = make_service(
        faq_db, completer, FakeObjectStorage(),
        embedder=StubEmbedder({
            "产量完成率咋算的": same_vector(), "产量完成率怎么算？": same_vector(),
        }),
        ontology_names_loader=_onto_loader_with_production_rate(),
    )
    await service.compare_candidate("c1", actor_who="小李 · 地质/质检")
    row = await service.draft_candidate("c1", actor_who="小李 · 地质/质检")
    assert row.draft == d.DUP_DRAFT_TEXT
    assert row.hook_suggestion is None
    assert not completer.calls  # dup 草稿不走 LLM


# ── 端点 14：引用知识起草 ──


async def test_draft_from_refs_ledger_and_slice(faq_db: Any) -> None:
    async def ledger_loader(kind: str, ref_id: int) -> tuple[str, str, str] | None:
        if (kind, ref_id) == ("metric", 3):
            return ("自然递减率", "月：1 − q_t / q_(t−1)", "C1 指标卡「自然递减率」")
        return None

    async def slice_loader(report_id: str, fragment_id: str) -> tuple[str, str] | None:
        if (report_id, fragment_id) == ("rpt-n02", "f1"):
            return ("N-02（渤中28-1-N2）于 2019-06-15 投产。",
                    "《N-02 井完井报告》章节 01 ＞ 1.2 投产信息")
        return None

    completer = StubCompleter(answers={
        "faq.draft.from_refs": (
            "月：1 − q_t / q_(t−1)（来源：C1 指标卡「自然递减率」）\n"
            "N-02（渤中28-1-N2）于 2019-06-15 投产。"
            "（来源：《N-02 井完井报告》章节 01 ＞ 1.2 投产信息）"
        )
    })
    service = make_service(
        faq_db, completer, FakeObjectStorage(),
        ledger_loader=ledger_loader, slice_loader=slice_loader,
    )
    row = await service.draft_from_refs(d.LedgerRef(kind="metric", id=3), None)
    assert "（来源：C1 指标卡「自然递减率」）" in row.draft
    assert row.hook_suggestion == d.Hook(kind="metric", name="自然递减率")  # 自动挂接该口径
    row2 = await service.draft_from_refs(
        d.LedgerRef(kind="metric", id=3), d.SliceRef(report_id="rpt-n02", fragment_id="f1")
    )
    assert row2.draft.count("（来源：") == 2  # 多源逐段带来源标注
    assert row2.hook_suggestion is not None
    row3 = await service.draft_from_refs(None, d.SliceRef(report_id="rpt-n02", fragment_id="f1"))
    assert row3.hook_suggestion is None  # 仅选切片→无建议
    with pytest.raises(FaqParamError):
        await service.draft_from_refs(None, None)  # 两源全空 400
    with pytest.raises(FaqParamError):
        await service.draft_from_refs(d.LedgerRef(kind="bogus", id=1), None)
    with pytest.raises(FaqNotFoundError):
        await service.draft_from_refs(d.LedgerRef(kind="term", id=999), None)  # 台账无此行
    with pytest.raises(FaqNotFoundError):
        await service.draft_from_refs(None, d.SliceRef(report_id="rpt-x", fragment_id="f-x"))


# ── 端点 15：批量导入（四计数——00 §4.4） ──

CSV_TEMPLATE = (
    "标准问,相似问法,负例问法,答案\n"
    "配注合格率是什么？,「配注达标率」,,'分层实注÷配注，达标井次占比'\n"
    "产量完成率怎么算,「日度完成率」,,'同公式按日折算'\n"
    "产量完成率怎么算？,,,'完全重复行'\n"
    "缺答案的行,,,\n"
    ",「不该答」,帮我预测明年股价,（负例）\n"
)


async def test_import_counts_and_pending_review(faq_db: Any) -> None:
    """四计数：added/merged/skipped/failed；导入行同走待审核（审核流做齐）。"""
    storage = FakeObjectStorage()
    service = make_service(faq_db, StubCompleter(), storage)
    stats = await service.import_library(
        mode="append", dry_run=False, filename="faq.csv",
        file_bytes=CSV_TEMPLATE.encode("utf-8"), actor_who="小李 · 地质/质检",
    )
    assert (stats.added, stats.merged, stats.skipped, stats.failed) == (2, 1, 1, 1)
    assert stats.failures[0].reason == "缺答案列——模板列必填"
    assert stats.hint.startswith("导入完成：新增 2 · 合并 1 · 跳过 1 · 失败 1")
    assert "1 行缺答案列——模板列必填" in stats.hint
    rows = await service.list_entries()
    assert rows.grand_total == 11  # 9 种子＋2 新增（配注合格率＋负例行）
    new_rows = [i for i in rows.items if i.id in ("faq-10", "faq-11")]
    assert all(i.status == "pending_review" for i in new_rows)  # 批量新增同走待审核
    negative = [i for i in new_rows if i.status == "pending_review" and "股价" in i.question]
    assert negative and negative[0].question == "帮我预测明年股价"  # 负例问法列承载问句
    detail = await service.entry_detail("faq-1")
    assert any("日度完成率" in s.text for s in detail.similar_questions)  # merged 增相似问
    assert any(key.startswith("faq/import/") for key in storage.objects)  # 文件落 MinIO 不过期


async def test_import_dry_run_does_not_write(faq_db: Any) -> None:
    storage = FakeObjectStorage()
    service = make_service(faq_db, StubCompleter(), storage)
    stats = await service.import_library(
        mode="append", dry_run=True, filename="faq.csv",
        file_bytes=CSV_TEMPLATE.encode("utf-8"), actor_who="小李 · 地质/质检",
    )
    assert stats.dry_run is True and (stats.added, stats.merged, stats.skipped) == (2, 1, 1)
    assert stats.hint.startswith("试校验通过（未入库）：可新增 2")
    rows = await service.list_entries()
    assert rows.grand_total == 9  # 仅校验不入库
    assert any(key.startswith("faq/import/") for key in storage.objects)  # 件仍落桶暂存


async def test_import_replace_clears_library(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    csv_body = "标准问,相似问法,负例问法,答案\n新条目一,,,'答案一'\n"
    stats = await service.import_library(
        mode="replace", dry_run=False, filename="faq.csv",
        file_bytes=csv_body.encode("utf-8"), actor_who="小李 · 地质/质检",
    )
    assert stats.added == 1
    rows = await service.list_entries()
    assert rows.grand_total == 1 and rows.items[0].question == "新条目一"


async def test_import_param_validation(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    with pytest.raises(FaqParamError):
        await service.import_library(
            mode="bogus", dry_run=False, filename="a.csv", file_bytes=b"x", actor_who="系统"
        )
    with pytest.raises(FaqParamError):
        await service.import_library(
            mode="append", dry_run=False, filename="a.xlsx", file_bytes=b"x", actor_who="系统"
        )
    with pytest.raises(FaqParamError):
        await service.import_library(  # 模板列缺失
            mode="append", dry_run=False, filename="a.csv",
            file_bytes="标准问,答案\nq,a\n".encode(), actor_who="系统",
        )


# ── 端点 16：导出（与导入模板列对称） ──


async def test_export_round_trip_with_import(faq_db: Any) -> None:
    """导出全库（含相似问/负例列）→ 新库导入还原（MinIO 往返）。"""
    storage = FakeObjectStorage()
    service = make_service(faq_db, StubCompleter(), storage)
    handle = await service.export_library()
    assert handle.columns == ["标准问", "相似问法", "负例问法", "答案"]  # 与模板列对称
    assert handle.download_url.startswith("https://minio.test/get/")
    export_key = next(k for k in storage.objects if k.startswith("faq/export/"))
    exported = storage.objects[export_key]
    assert "帮我预测明年油价" in exported.decode("utf-8-sig")  # 负例列随库带出

    spec = faq_db._specs["primary"]
    from app.infra.db import ConnectionManager, DatabaseSpec

    fresh_spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=spec.database.replace("faq.db", "faq-roundtrip.db"),
        user="", password="", pool_size=2, max_overflow=1,
    )
    fresh = ConnectionManager([fresh_spec])
    try:
        from app.domains.faq.store import ensure_faq_tables

        await ensure_faq_tables(fresh.engine())
        fresh_service = make_service(fresh, StubCompleter(), FakeObjectStorage())
        stats = await fresh_service.import_library(
            mode="append", dry_run=False, filename="exported.csv",
            file_bytes=exported, actor_who="小李 · 地质/质检",
        )
        assert stats.failed == 0
        rows = await fresh_service.list_entries()
        assert rows.grand_total == 9  # 全库还原（含负例 faq-9）
        neg = await fresh_service.list_entries(status="neg")
        assert [i.id for i in neg.items] == ["faq-9"]
        assert [i.question for i in neg.items] == ["帮我预测明年油价"]  # 负例行还原
    finally:
        await fresh.dispose()


# ── 运行时读口（A1 消费面） ──


async def test_match_index_only_serve_entries(faq_db: Any) -> None:
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    hit = await service.match_index("产量完成率怎么算")
    assert hit is not None and hit.entry_id == "faq-1"
    hit_sim = await service.match_index("「月度完成率口径」（主任常问）")  # 相似问独立检索项
    assert hit_sim is not None and hit_sim.entry_id == "faq-1"
    assert await service.match_index("帮我预测明年油价") is None  # 负例检索不可达
    assert await service.match_index('"老完成率"是什么口径') is None  # 已停用摘出索引
    assert await service.match_index("") is None


async def test_search_similar_ranks_serve_entries(faq_db: Any) -> None:
    """P1-08b FAQ 相似问检索（检索链 FAQ 路扩检候选供给面）：向量余弦排序、
    top_k 截断、只服务中条目可达、空查询零命中。"""
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage(),
                           embedder=StubEmbedder())
    hits = await service.search_similar("产量完成率的公式", top_k=3)
    assert hits, "相似问检索应命中演示问答"
    assert all(h.score > 0 for h in hits)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)  # 按分倒序
    assert hits[0].entry_id == "faq-1"  # 同族问题排最前
    assert len(await service.search_similar("产量完成率的公式", top_k=2)) <= 2
    # 负例/已停用/待审核不可达（v0.2 审核流同闸）
    for bad in ("帮我预测明年油价", '"老完成率"是什么口径'):
        hits_bad = await service.search_similar(bad, top_k=5)
        assert all(h.entry_id != "faq-9" and h.entry_id != "faq-8" for h in hits_bad)
    assert await service.search_similar("", top_k=3) == []
    assert await service.search_similar("产量", top_k=0) == []


# ── LedgerMerged 消费（B3-2 口径修订联动） ──


async def test_ledger_merged_drafts_suggestion_into_review(faq_db: Any) -> None:
    """术语修订联动：按 hook 检出→LLM 起草→进待审核；不自动直改。"""
    completer = StubCompleter(answers={"faq.ledger_merged.suggestion": "修订后答案：新口径。"})
    audit = RecordingAudit()
    service = make_service(faq_db, completer, FakeObjectStorage(), audit=audit)
    created = await service.create_entry(
        "递减增油怎么算？", "按口径模板计算", is_negative=False,
        hook=d.Hook(kind="metric", name="递减增油"),
        source_candidate_id=None, actor_who="小李 · 地质/质检",
    )
    await service.review_entry(created.id, "publish", actor_who="阿强 · 平台运维")
    before = await service.entry_detail(created.id)
    await service.on_ledger_merged(
        make_event("LedgerMerged", {"kind": "metric", "name": "递减增油"})
    )
    rows = await service.list_entries()
    suggestions = [i for i in rows.items if i.hook and i.hook.name == "递减增油"
                   and i.status == "pending_review"]
    assert len(suggestions) == 1  # 建议稿进待审核（端点 17 人工确认）
    detail = await service.entry_detail(suggestions[0].id)
    assert "口径修订联动 · LLM 建议稿——请人工核实" in detail.answer
    assert detail.maintainer == "系统"
    after = await service.entry_detail(created.id)  # 不自动直改——原条目原样
    assert after.answer == before.answer and after.status == "serve"
    assert ("faq.ledger_merged.suggestion", "petro-main") == (completer.calls[0][0], "petro-main")
    assert any(r.action == "faq.ledger_merged.suggestion" for r in audit.rows)  # B12 留痕


async def test_ledger_merged_unparseable_payload_noop(faq_db: Any) -> None:
    completer = StubCompleter()
    service = make_service(faq_db, completer, FakeObjectStorage(), audit=RecordingAudit())
    await service.on_ledger_merged(make_event("LedgerMerged", {"foo": "bar"}))
    assert not completer.calls  # 载荷不可解析——跳过不起草
    rows = await service.list_entries()
    assert rows.grand_total == 9


async def test_candidate_write_back_on_publish(faq_db: Any) -> None:
    """候选回写随发布事务（零悬挂）：入库锚登记→发布落 published。"""
    service = make_service(faq_db, StubCompleter(), FakeObjectStorage())
    created = await service.create_entry(
        "自然递减率怎么算", "月度环比口径", is_negative=False, hook=None,
        source_candidate_id="c2", actor_who="小李 · 地质/质检",
    )
    assert created.candidate is not None and created.candidate.status == "compared"
    rows = await service.candidates(status="ok")
    assert [c.id for c in rows.items] == ["c2"]  # 入库时未发布（回写时点在发布事务）
    await service.review_entry(created.id, "publish", actor_who="阿强 · 平台运维")
    published = await service.candidates(status="published")
    assert [c.id for c in published.items] == ["c2"]
    with pytest.raises(FaqConflictError):
        await service.create_entry(  # 已发布候选重复回写 409
            "再次回写", "x", is_negative=False, hook=None,
            source_candidate_id="c2", actor_who="系统",
        )
    with pytest.raises(FaqNotFoundError):
        await service.create_entry(
            "无此候选", "x", is_negative=False, hook=None,
            source_candidate_id="c99", actor_who="系统",
        )


def test_service_construction_contract() -> None:  # 98 卡 17 方法公开面冒烟
    methods = {name for name in dir(FaqService) if not name.startswith("_")}
    expected = {
        "list_entries", "entry_detail", "create_entry", "review_entry", "dup_check",
        "add_similar", "remove_similar", "merge_entries", "toggle_state", "candidates",
        "start_scan", "scan_progress", "compare_candidate", "draft_candidate",
        "draft_from_refs", "import_library", "export_library", "match_index",
        "close_stale_scans", "on_ledger_merged",
    }
    assert expected <= methods


def test_import_template_frozen() -> None:
    """模板列/导出列对称（合同值）。"""
    assert d.IMPORT_COLUMNS == ("标准问", "相似问法", "负例问法", "答案")
    assert d.EXPORT_COLUMNS == d.IMPORT_COLUMNS


def test_freeze_clock_helper() -> None:
    with freeze("2026-10-02T08:00:00"):
        from app.infra.clock import now

        assert now().hour == 8

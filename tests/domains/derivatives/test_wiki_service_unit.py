"""wiki 支路服务单测——生成/重建触发、版本治理、修正三联动、重铸闭环。

装配：sqlite 底座＋真实 KbService＋桩 LLM；IngestCompleted/FragmentRevised
订阅照 main.py lifespan 接线（B9 缝真跑）。私有属性直查（_store/_gateway/
_recasts）仅限测试观测。
"""

from typing import Any

import pytest

from app.domains.derivatives import (
    DESC_FIRST,
    DESC_RECAST,
    DESC_REINGEST,
    OPERATOR_SYSTEM,
    SOURCE_AUTO,
    SOURCE_ROLLBACK,
    WikiConflictError,
    WikiNotFoundError,
    WikiParamError,
)
from app.domains.kb import (
    KbConflictError,
    KbParamError,
    KbService,
)
from app.infra.eventbus import make_event
from tests.domains.derivatives.conftest import (
    WIKI_STUB_ANSWER,
    FakeObjectStorage,
    StubCompleter,
    make_report,
    wait_until,
)


def _stub(kb: KbService) -> StubCompleter:
    return kb._gateway


async def _page(derivatives: Any, report_id: str) -> Any:
    return await derivatives._store.page_by_report(report_id)


async def _wait_page(derivatives: Any, report_id: str, *, v: int) -> Any:
    async def _ready() -> bool:
        page = await _page(derivatives, report_id)
        return page is not None and (page.current_version or 0) >= v

    await wait_until(_ready)
    page = await _page(derivatives, report_id)
    assert page is not None
    return page


async def _wait_wiki_calls(stub: StubCompleter, count: int) -> None:
    await wait_until(
        lambda: _sync(len([c for c, _ in stub.calls if c == "wiki.gen"]) >= count)
    )


async def _sync(value: bool) -> bool:
    return value


async def _task_done(kb: KbService, task_id: str) -> bool:
    progress = await kb.ingest_task(task_id)
    return progress.state in ("done", "failed", "stuck")


async def test_ingest_with_wiki_on_generates_page_v1(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    _lib, report_id, task_id = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    detail = await derivatives.page_detail(page.id)
    # slug 稳定性＝id 承载；来源/操作人/经由单号（B4 端点 2/3）
    assert page.id == f"wiki-{report_id.removeprefix('rpt-')}"
    assert page.source_report_id == report_id
    assert detail.generation_source == SOURCE_AUTO
    assert detail.operator == OPERATOR_SYSTEM
    assert detail.slug == page.id
    assert detail.content and "<!--WIKI-END-->" not in detail.content  # 哨兵不入库
    assert any(caller == "wiki.gen" for caller, _content in _stub(kb).calls)  # B6
    versions = await derivatives.versions(page.id)
    assert versions[0].task_no == task_id
    assert versions[0].desc == DESC_FIRST
    assert versions[0].current is True
    # B1 端点 1 wiki 字段与 B4 current_version 同源同值（投影回写口）
    ledger = await kb.list_reports()
    row = next(r for r in ledger if r.id == report_id)
    assert row.wiki == "v1"


async def test_claims_fail_closed_and_glossary_fixed_at_generation(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    _lib, report_id, _task = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    detail = await derivatives.page_detail(page.id)
    # 桩稿含 [[claim:f1]]（有效）与 [[claim:f999]]（伪造——fail-closed 剥除）
    assert "[[claim:f999]]" not in detail.content
    assert "[[claim:f1]]" in detail.content
    assert {c["claim_id"] for c in detail.claims} == {"c1"}
    assert all(c["evidence_chunk_ids"] for c in detail.claims)
    # 台账挂接：名册词「综合含水率」挂、生成时固化 card 投影（kind/ref_id/card）
    words = {g["word"]: g for g in detail.glossary_terms}
    assert "综合含水率" in words and words["综合含水率"]["kind"] == "metric"
    assert words["综合含水率"]["ref_id"] == 5
    assert words["综合含水率"]["card"]["unit"] == "%"
    assert "[[term:综合含水率]]" in detail.content


async def test_ingest_with_wiki_off_generates_nothing(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    _lib, report_id, _task = await make_report(
        kb, storage,
        lib_config={"semantic": True, "keyword": True, "wiki": False, "graph": False},
    )
    assert await _page(derivatives, report_id) is None
    # 直调未知 id 404（含 wiki 开关关未生成——B4 错误码草案）
    with pytest.raises(WikiNotFoundError):
        await derivatives.page_detail(f"wiki-{report_id.removeprefix('rpt-')}")


async def test_reingest_reuses_same_page_and_appends_version(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    _lib, report_id, task_id = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    # 重跑＝一次新入库（source=重跑定型）→ 事件真跑 → 同页原地更新、版本+1
    await kb.retry_ingest(task_id, "xiaoli · 地质/质检")
    tasks = await kb.list_ingest_tasks("重跑定型")
    await wait_until(lambda: _task_done(kb, tasks[0].id))
    page2 = await _wait_page(derivatives, report_id, v=2)
    assert page2.id == page.id  # slug 不随重建变化
    versions = await derivatives.versions(page.id)
    assert [v.v for v in versions] == [1, 2]  # 版本只追加
    assert versions[1].desc == DESC_REINGEST
    assert versions[0].current is False and versions[1].current is True


async def test_fragment_revision_three_linkage(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """修正一片段→三联动真跑：记版＋索引重建（重嵌）＋问题块重生＋wiki v+1。"""
    _lib, report_id, _task = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    detail = await kb.report_detail(report_id)
    frag = detail.fragments[0]
    # 乐观锁：base_version 落后 409；空文本 400
    with pytest.raises(KbConflictError):
        await kb.revise_fragment(report_id, frag.id, base_version=99,
                                 text="x", actor_who="xiaoli · 地质/质检")
    with pytest.raises(KbParamError):
        await kb.revise_fragment(report_id, frag.id, base_version=frag.version,
                                 text="  ", actor_who="xiaoli · 地质/质检")
    receipt = await kb.revise_fragment(
        report_id, frag.id, base_version=frag.version,
        text=frag.text + "（勘误：补状态注记）", actor_who="xiaoli · 地质/质检",
    )
    assert receipt.version == 2
    assert [v.v for v in receipt.versions] == [1, 2]  # v1 原始不可变＋逐次记版
    assert receipt.versions[0].note == "原始解析"
    assert receipt.versions[1].note == "人工修正"
    assert receipt.rebuild.triggered is True
    assert receipt.rebuild.hint == "已保存——将重建检索索引。"
    assert receipt.activity_row.action == "修正片段"
    # 重建折算「片段修正」任务并跑完（索引重建＋问题块重生——enrich 不失败）
    await wait_until(lambda: _task_done(kb, receipt.task_id))
    progress = await kb.ingest_task(receipt.task_id)
    assert progress.source == "片段修正"
    assert progress.state == "done"
    assert all(n.state == "finish" for n in progress.nodes)
    # 修正片段文本已更新（重嵌以最新文本为输入）
    revised = next(f for f in (await kb.report_detail(report_id)).fragments
                   if f.id == frag.id)
    assert revised.text.endswith("（勘误：补状态注记）")
    # wiki 重铸联动：FragmentRevised→重铸→版本+1 来源「自动重建」（既有来源态）
    page2 = await _wait_page(derivatives, report_id, v=2)
    assert page2.id == page.id
    versions = await derivatives.versions(page.id)
    assert versions[1].desc == DESC_RECAST
    assert versions[1].source == SOURCE_AUTO
    assert versions[1].task_no == receipt.task_id
    # 活动流同事务记「修正＋触发百科重铸」（B1 端点 4）
    acts = await kb.library_activities(_lib)
    assert any("修正片段" in a.action and "触发百科重铸" in a.target for a in acts)


async def test_recast_failure_does_not_block_revision(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """重铸失败不阻塞修正：记活动流＋版本不前进（半页不落库）、修正照常定型。"""
    _lib, report_id, _task = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    stub = _stub(kb)
    stub.answers["wiki.gen"] = RuntimeError("模型超时")  # 重铸必失败
    detail = await kb.report_detail(report_id)
    frag = detail.fragments[0]
    receipt = await kb.revise_fragment(
        report_id, frag.id, base_version=frag.version,
        text=frag.text + "（勘误）", actor_who="xiaoli · 地质/质检",
    )
    await wait_until(lambda: _task_done(kb, receipt.task_id))
    page_after = await _page(derivatives, report_id)
    assert page_after.current_version == 1  # 版本不前进——半页不落库
    assert page_after.id == page.id
    acts = await kb.library_activities(_lib)
    assert any(a.action == "百科重铸失败" for a in acts)


async def test_rollback_append_semantics_and_guards(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    _lib, report_id, task_id = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    # 制造 v2（重跑重建——事件真跑）
    await kb.retry_ingest(task_id, "xiaoli · 地质/质检")
    tasks = await kb.list_ingest_tasks("重跑定型")
    await wait_until(lambda: _task_done(kb, tasks[0].id))
    await _wait_page(derivatives, report_id, v=2)
    # 404：页面不存在/目标版本不存在
    with pytest.raises(WikiNotFoundError):
        await derivatives.rollback("wiki-none", 1, "xiaoli · 地质/质检")
    with pytest.raises(WikiNotFoundError):
        await derivatives.rollback(page.id, 99, "xiaoli · 地质/质检")
    # 400：等于当前版
    with pytest.raises(WikiParamError):
        await derivatives.rollback(page.id, 2, "xiaoli · 地质/质检")
    # 回滚到 v1＝追加 v3（来源「回滚」、指针前进、历史不变）
    receipt = await derivatives.rollback(page.id, 1, "xiaoli · 地质/质检")
    assert receipt.current_version == 3
    assert receipt.new_version.source == SOURCE_ROLLBACK
    assert receipt.new_version.operator == "xiaoli · 地质/质检"
    assert receipt.new_version.task_no is None  # 回滚无经由单号
    assert receipt.new_version.current is True
    assert "内容恢复自 v1" in receipt.banner
    versions = await derivatives.versions(page.id)
    assert [v.v for v in versions] == [1, 2, 3]
    assert versions[1].current is False and versions[2].current is True
    assert versions[0].desc == DESC_FIRST  # 历史版本永不变改
    # 投影回写同步（B1 wiki 字段）
    ledger = await kb.list_reports()
    row = next(r for r in ledger if r.id == report_id)
    assert row.wiki == "v3"
    # 防呆 409：目标版内容与当前版逐字相同（v3 即 v1 快照，再滚 v1）
    with pytest.raises(WikiConflictError):
        await derivatives.rollback(page.id, 1, "xiaoli · 地质/质检")
    # 回滚本身也可再回滚（滚到 v2——内容不同于 v3）
    receipt2 = await derivatives.rollback(page.id, 2, "xiaoli · 地质/质检")
    assert receipt2.current_version == 4
    assert receipt2.new_version.source == SOURCE_ROLLBACK


async def test_read_faces_version_snapshot(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """?version=N 任意版快照：content/claims/glossary/updated/来源/操作人/状态固化。"""
    _lib, report_id, _task = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    v1 = await derivatives.page_detail(page.id)
    _stub(kb).answers["wiki.gen"] = "改写后的第二版正文[[claim:f1]]。\n<!--WIKI-END-->"
    await derivatives.on_ingest_completed(
        make_event(
            "IngestCompleted",
            {"task_id": "task-manual", "report_id": report_id, "lib_id": _lib,
             "doc": "", "source": "重跑定型", "config_snapshot": {"wiki": True}},
        )
    )
    await _wait_page(derivatives, report_id, v=2)
    v2 = await derivatives.page_detail(page.id)
    assert "改写后的第二版正文" in v2.content
    assert v2.current_version == 2
    # 历史版快照原样（不回溯改旧版）
    v1_again = await derivatives.page_detail(page.id, version=1)
    assert v1_again.content == v1.content
    assert v1_again.generation_source == v1.generation_source
    assert v1_again.claims == v1.claims
    assert v1_again.glossary_terms == v1.glossary_terms
    # 目录行与筛选
    pages = await derivatives.list_pages()
    item = next(p for p in pages if p.id == page.id)
    assert item.current_version == 2 and item.version_count == 2
    assert item.title
    assert await derivatives.list_pages(lib="不存在的库") == []


async def test_wiki_generation_abandons_half_page(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """截断纪律：续写 3 轮仍未收束→放弃本次写入、不落半页（F50 票 104）。"""
    stub = _stub(kb)
    stub.answers["wiki.gen"] = "未写完的半页正文"  # 无哨兵——续写 3 轮后放弃
    _lib, report_id, _task = await make_report(kb, storage)
    await _wait_wiki_calls(stub, 1 + 3)  # 首次＋最多续写 3 轮
    await wait_until(lambda: _sync(not derivatives._recasts.tasks))
    assert await _page(derivatives, report_id) is None  # 半页不落库
    assert len([c for c, _ in stub.calls if c == "wiki.gen"]) == 4


async def test_wiki_prompt_carries_evidence_ids_and_sentinel(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """提示词＝模板约束载体：片段号清单（防伪造锚）＋哨兵纪律＋按库取向。"""
    _lib, report_id, _task = await make_report(kb, storage)
    await _wait_page(derivatives, report_id, v=1)
    wiki_calls = [content for caller, content in _stub(kb).calls if caller == "wiki.gen"]
    assert wiki_calls and "[[claim:" in wiki_calls[0]
    assert "<!--WIKI-END-->" in wiki_calls[0]
    assert "完井报告" in wiki_calls[0]  # completion 取向提示
    # 桩应答未被改动（哨兵来自 stub 脚本——WIKI_STUB_ANSWER）
    assert WIKI_STUB_ANSWER.startswith("## 概述")

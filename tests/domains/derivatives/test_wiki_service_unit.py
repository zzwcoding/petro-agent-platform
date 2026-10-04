"""wiki 支路服务单测——生成/重建触发、覆盖语义（v0.4）、修正三联动、重铸闭环。

装配：sqlite 底座＋真实 KbService＋桩 LLM；IngestCompleted/FragmentRevised
订阅照 main.py lifespan 接线（B9 缝真跑）。私有属性直查（_store/_gateway/
_recasts）仅限测试观测。

B4 v0.4（Owner 2026-10-04 拍板撤版本历史）：重建＝覆盖当前版——
current_version＝重建计数单调 +1、wiki_page_version 版本表写路径撤除
（表保留不删，本组测试以「版本表恒无行」反 append-only 断言钉死）。
"""

from typing import Any

import pytest
from sqlalchemy import select

from app.domains.derivatives import (
    OPERATOR_SYSTEM,
    SOURCE_AUTO,
    WikiNotFoundError,
)
from app.domains.derivatives.store import WikiPageVersionRow
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


async def _version_rows(derivatives: Any, page_id: str) -> list[Any]:
    """版本表直查（反 append-only 断言用——v0.4 写路径撤除后恒空）。"""
    db = derivatives._store._db
    async with db.readonly() as session:
        rows = (
            (
                await session.execute(
                    select(WikiPageVersionRow).where(
                        WikiPageVersionRow.page_id == page_id
                    )
                )
            )
            .scalars()
            .all()
        )
    return list(rows)


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
    _lib, report_id, _task = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    detail = await derivatives.page_detail(page.id)
    # slug 稳定性＝id 承载；生成来源/操作人＝v0.4 单态派生
    assert page.id == f"wiki-{report_id.removeprefix('rpt-')}"
    assert page.source_report_id == report_id
    assert detail.generation_source == SOURCE_AUTO
    assert detail.operator == OPERATOR_SYSTEM
    assert detail.slug == page.id
    assert detail.content and "<!--WIKI-END-->" not in detail.content  # 哨兵不入库
    assert any(caller == "wiki.gen" for caller, _content in _stub(kb).calls)  # B6
    # 反 append-only：版本表写路径撤除（v0.4）——建页也不落版本行
    assert await _version_rows(derivatives, page.id) == []
    # B1 端点 1 wiki 字段与 B4 current_version 同源同值（重建计数投影回写口）
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


async def test_reingest_overwrites_current_version(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """覆盖语义（B4 v0.4 票面 (a)）：同一报告两次生成→重建计数 +1、内容＝
    新版、版本表无新行（append-only 撤除钉死）。"""
    _lib, report_id, task_id = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    old_content = page.content
    # 重跑＝一次新入库（source=重跑定型）→ 事件真跑 → 同页原地覆盖、计数 +1
    _stub(kb).answers["wiki.gen"] = "改写后的第二版正文[[claim:f1]]。\n<!--WIKI-END-->"
    await kb.retry_ingest(task_id, "xiaoli · 地质/质检")
    tasks = await kb.list_ingest_tasks("重跑定型")
    await wait_until(lambda: _task_done(kb, tasks[0].id))
    page2 = await _wait_page(derivatives, report_id, v=2)
    assert page2.id == page.id  # slug 不随重建变化
    assert page2.current_version == 2  # 重建计数单调 +1
    assert "改写后的第二版正文" in page2.content  # 当前版＝新版
    assert old_content != page2.content  # 覆盖（非另落一行）
    # 反 append-only：版本表无新行（v0.4 版本历史撤除）
    assert await _version_rows(derivatives, page.id) == []
    # B1 台账 wiki 字段随覆盖同步（同源同值＝重建计数）
    ledger = await kb.list_reports()
    row = next(r for r in ledger if r.id == report_id)
    assert row.wiki == "v2"


async def test_fragment_revision_three_linkage(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """修正一片段→三联动真跑：记版＋索引重建（重嵌）＋问题块重生＋wiki 覆盖重建。"""
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
    assert [v.v for v in receipt.versions] == [1, 2]  # 片段 v1 原始不可变＋逐次记版
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
    # wiki 重铸联动：FragmentRevised→重铸→覆盖当前版（重建计数 +1，非版本追加）
    page2 = await _wait_page(derivatives, report_id, v=2)
    assert page2.id == page.id
    assert page2.current_version == 2
    assert await _version_rows(derivatives, page.id) == []  # 版本表仍无行
    # 活动流同事务记「修正＋触发百科重铸」（B1 端点 4）
    acts = await kb.library_activities(_lib)
    assert any("修正片段" in a.action and "触发百科重铸" in a.target for a in acts)


async def test_recast_failure_keeps_current_version(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """重铸失败不阻塞修正：记活动流＋当前版保持旧内容（半页不落库）、修正照常定型。"""
    _lib, report_id, _task = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    old_content = page.content
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
    assert page_after.current_version == 1  # 重建计数不前进——半页不落库
    assert page_after.content == old_content  # 当前版保持旧内容
    assert page_after.id == page.id
    acts = await kb.library_activities(_lib)
    assert any(a.action == "百科重铸失败" for a in acts)


async def test_read_faces_current_version_and_directory(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """读面（B4 v0.4 端点 1/2）：恒当前版（无 ?version=N）；目录筛选服务端算。"""
    _lib, report_id, _task = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    _stub(kb).answers["wiki.gen"] = "改写后的第二版正文[[claim:f1]]。\n<!--WIKI-END-->"
    await derivatives.on_ingest_completed(
        make_event(
            "IngestCompleted",
            {"task_id": "task-manual", "report_id": report_id, "lib_id": _lib,
             "doc": "", "source": "重跑定型", "config_snapshot": {"wiki": True}},
        )
    )
    await _wait_page(derivatives, report_id, v=2)
    detail = await derivatives.page_detail(page.id)
    assert "改写后的第二版正文" in detail.content
    assert detail.current_version == 2
    assert detail.status == "正常"  # 当前版无 [[flag:]] → 正常（服务端判定）
    # ?version=N 读法随 v0.4 撤除——残留参数即残面（签名无 version 形参）
    with pytest.raises(TypeError):
        await derivatives.page_detail(page.id, version=1)  # type: ignore[call-arg]
    # 目录行与筛选（keyword 匹配题名/来源报告/所属库；lib 筛选）
    pages = await derivatives.list_pages()
    item = next(p for p in pages if p.id == page.id)
    assert item.current_version == 2
    assert item.status == "正常"
    assert item.title
    assert not hasattr(item, "version_count")  # v0.4 撤 version_count（DTO 两级）
    assert await derivatives.list_pages(lib="不存在的库") == []


async def test_directory_status_two_states_by_flag(
    kb: KbService, derivatives: Any, storage: FakeObjectStorage,
) -> None:
    """状态两态（服务端算）：当前版正文有 [[flag:]] → 字段待核对，无 → 正常。"""
    _lib, report_id, _task = await make_report(kb, storage)
    page = await _wait_page(derivatives, report_id, v=1)
    detail = await derivatives.page_detail(page.id)
    assert detail.status == "正常"
    _stub(kb).answers["wiki.gen"] = (
        "平台 CEP-B[[flag:与井档案不符，待核对]]与井档案对不上。\n<!--WIKI-END-->"
    )
    await derivatives.on_ingest_completed(
        make_event(
            "IngestCompleted",
            {"task_id": "task-manual-2", "report_id": report_id, "lib_id": _lib,
             "doc": "", "source": "重跑定型", "config_snapshot": {"wiki": True}},
        )
    )
    await _wait_page(derivatives, report_id, v=2)
    detail2 = await derivatives.page_detail(page.id)
    assert detail2.status == "字段待核对"  # 有未消除修订提示
    assert "[[flag:与井档案不符，待核对]]" in detail2.content
    pages = await derivatives.list_pages()
    item = next(p for p in pages if p.id == page.id)
    assert item.status == "字段待核对"  # 目录状态同源（服务端按当前版判定）


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

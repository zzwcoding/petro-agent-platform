"""B2 切片管理域单测（P1-04）——sqlite 底座（kb conftest 夹具）。

覆盖（B2-答案出处.md v0.3 行为规则）：
- 端点 1 两读法分派（按报告整组取数整表返回／全库扁平清单分页必带缺 400）、
  type 筛越界 400、keyword 匹配域（命中句/井号/章节路径）、DTO 无 context（INV）；
- 端点 2 回捞语义分派（父块正文／摘要·问题块说明行）与父块寻址 404；
- 端点 3 标记入队（F62 同事务「标记问题片段」）＋待质检复核态重复 409；
- 端点 4 队列列表（state 筛在途态、终态不出列、越界 400、标记时间倒序）；
- 端点 5 复核状态机（confirm→已修正；reject 必带理由空 400→已驳回）；
- 端点 6 销记（仅已驳回态；队列零悬挂）＋重新标记闭环（旧驳回单转已销记）。
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.domains.kb import KbParamError
from app.domains.kb import domain as d
from app.domains.kb.store import (
    FragmentRow,
    FragmentVersionRow,
    LibraryRow,
    ReportRow,
)


@pytest.fixture
async def seeded(kb_db: Any) -> AsyncIterator[Any]:
    """直种子：一库一报告＋mixed 父子块＋摘要/问题块＋图片说明块（免跑管线）。"""
    manager = kb_db
    async with manager.session() as session:
        session.add(LibraryRow(id="lib-1", name="完井报告库", biz_template="completion"))
        await session.flush()
        session.add(
            ReportRow(id="rpt-1", lib_id="lib-1", doc="《N-02 井完井报告》", object_key="k/a")
        )
        session.add(
            ReportRow(id="rpt-2", lib_id="lib-1", doc="《渤中28-1 月报》", object_key="k/b")
        )
        await session.flush()
        rows = [
            FragmentRow(id="f0", report_id="rpt-1", type="原文块", section="父块·章节 01",
                        current_version=1, is_parent_only=True),  # 父块（不对外寻址）
            FragmentRow(id="f1", report_id="rpt-1", type="原文块", section="章节 01 井基本情况",
                        well="N-02", current_version=1, is_parent_only=False),
            FragmentRow(id="f2", report_id="rpt-1", type="图片说明块", section="章节 03 图件",
                        well="N-02", current_version=1, is_parent_only=False),
            FragmentRow(id="f3", report_id="rpt-1", type="摘要块", section="全文档摘要",
                        current_version=1, is_parent_only=False),
            FragmentRow(id="f4", report_id="rpt-1", type="问题块", section="问题块·第1批",
                        current_version=1, is_parent_only=False),
            FragmentRow(id="f5", report_id="rpt-2", type="原文块", section="章节 02 检泵",
                        well="N-11", current_version=1, is_parent_only=False),
        ]
        for row in rows:
            session.add(row)
        await session.flush()
        versions = [
            FragmentVersionRow(fragment_id="f0", v=1,
                               text="章节 01 全文：N-02（渤中28-1-N2）于 2019-06-15 投产。"
                                    "位于渤南区块 CEP-A 平台。",
                               context_text=None),
            FragmentVersionRow(
                fragment_id="f1", v=1, text="N-02（渤中28-1-N2）于 2019-06-15 投产。",
                context_text="f0",  # mixed 父块锚
            ),
            FragmentVersionRow(fragment_id="f2", v=1, text="图 3-7 岩性柱状图说明。",
                               context_text="f0"),
            FragmentVersionRow(fragment_id="f3", v=1, text="全文档摘要文本。", context_text=None),
            FragmentVersionRow(fragment_id="f4", v=1, text="N-02 井的完井方式是什么？",
                               context_text=None),
            FragmentVersionRow(
                fragment_id="f5", v=1, text="N-11 井检泵 2026-08-28 起。", context_text=None
            ),
        ]
        for row in versions:
            session.add(row)
        await session.flush()
    yield manager


async def test_1_report_mode_returns_children_only(seeded: Any) -> None:
    """按报告读法：整表返回＋只给子块（父块 f0 不出列——INV）＋DTO 无 context。"""
    from app.domains.kb import KbService

    service = KbService(seeded, None, None)
    out = await service.list_fragments("rpt-1")
    assert [i.id for i in out.items] == ["f1", "f2", "f3", "f4"]
    assert out.total == 4 and out.page is None
    first = out.items[0]
    assert first.report_id == "rpt-1" and first.report == "《N-02 井完井报告》"
    assert first.well == "N-02" and first.type == "原文块"
    assert first.hit == "N-02（渤中28-1-N2）于 2019-06-15 投产。"
    assert not hasattr(first, "context")  # INV 落点：列表 DTO 无 context 字段


async def test_1_library_mode_requires_paging(seeded: Any) -> None:
    """全库扁平清单读法：page/pageSize 必带缺任一 400；合法分页回显信封。"""
    from app.domains.kb import KbService

    service = KbService(seeded, None, None)
    with pytest.raises(KbParamError):
        await service.list_fragments(None)
    with pytest.raises(KbParamError):
        await service.list_fragments(None, page=1)
    out = await service.list_fragments(None, page=2, page_size=2)
    assert out.total == 5  # 全库片段数（跨报告一维、不与单卷 refs 对应）
    assert out.page == 2 and out.page_size == 2
    assert [i.id for i in out.items] == ["f3", "f4"]


async def test_1_type_and_keyword_filters(seeded: Any) -> None:
    """type 五枚举筛＋越界 400；keyword 匹配域＝命中句/井号/章节路径（忽略大小写）。"""
    from app.domains.kb import KbService

    service = KbService(seeded, None, None)
    out = await service.list_fragments("rpt-1", type="摘要块")
    assert [i.id for i in out.items] == ["f3"]
    with pytest.raises(KbParamError):
        await service.list_fragments("rpt-1", type="图片块")
    by_well = await service.list_fragments("rpt-1", keyword="n-02")
    assert [i.id for i in by_well.items] == ["f1", "f2", "f4"]  # 忽略大小写包含（井号＋命中句）
    by_section = await service.list_fragments(None, keyword="检泵", page=1, page_size=10)
    assert [i.id for i in by_section.items] == ["f5"]  # 章节路径命中
    by_hit = await service.list_fragments("rpt-1", keyword="完井方式")
    assert [i.id for i in by_hit.items] == ["f4"]  # 命中句命中


async def test_1_report_not_found_404(seeded: Any) -> None:
    from app.domains.kb import KbNotFoundError, KbService

    service = KbService(seeded, None, None)
    with pytest.raises(KbNotFoundError):
        await service.list_fragments("rpt-none")


async def test_2_context_dispatch_by_type(seeded: Any) -> None:
    """回捞语义按 type 分派：原文/图片说明块＝父块正文（context ⊇ hit）；
    摘要块/问题块＝产物说明行（无父块唯一例外——页面 ctx 原值照抄）。"""
    from app.domains.kb import KbService

    service = KbService(seeded, None, None)
    ctx = await service.fragment_context("f1")
    assert ctx.id == "f1" and ctx.type == "原文块"
    assert ctx.hit in ctx.context  # 父块正文包含命中切片（真实系统语义）
    assert ctx.context.startswith("章节 01 全文")
    ctx2 = await service.fragment_context("f2")
    assert ctx2.context.startswith("章节 01 全文")  # F36 回读父块正文（与 F30 会师）
    ctx3 = await service.fragment_context("f3")
    assert ctx3.context == d.SUMMARY_CONTEXT_NOTE
    ctx4 = await service.fragment_context("f4")
    assert ctx4.context == d.QUESTION_CONTEXT_NOTE


async def test_2_context_404_parent_not_addressable(seeded: Any) -> None:
    from app.domains.kb import KbNotFoundError, KbService

    service = KbService(seeded, None, None)
    with pytest.raises(KbNotFoundError):
        await service.fragment_context("f0")  # 父块不对外寻址（F30）
    with pytest.raises(KbNotFoundError):
        await service.fragment_context("f-none")


async def test_3_mark_enqueues_with_activity_and_409(seeded: Any) -> None:
    """标记入队：只标记不直改＋hint 服务端返回＋F62 同事务「标记问题片段」；
    待质检复核态重复标记 409（部分唯一索引同判据）。"""
    from app.domains.kb import KbConflictError, KbNotFoundError, KbService

    service = KbService(seeded, None, None)
    view = await service.report_fragment_issue("f1", "小李 · 地质/质检")
    assert view.state == "待质检复核"
    assert view.fragment_label == "《N-02 井完井报告》 · 章节 01 井基本情况"
    assert view.marked_by == "小李 · 地质/质检"
    assert view.hint == d.MARK_HINT
    # 同事务 F62 留痕（B1 挂账收口批 action 值域）
    acts = await service.library_activities("lib-1")
    assert any(a.action == "标记问题片段" and "章节 01" in a.target for a in acts)
    with pytest.raises(KbConflictError) as ei:
        await service.report_fragment_issue("f1", "阿强")
    assert ei.value.code == "kb_issue_duplicate"
    with pytest.raises(KbNotFoundError):
        await service.report_fragment_issue("f-none", "阿强")


async def test_4_queue_list_state_filter_and_order(seeded: Any) -> None:
    """队列列表：state=all 亦只出两在途态（终态不出列）；标记时间倒序；越界 400。"""
    from app.domains.kb import KbParamError, KbService

    service = KbService(seeded, None, None)
    first = await service.report_fragment_issue("f1", "小李")
    second = await service.report_fragment_issue("f5", "小李")
    rows = await service.list_issue_reports("all")
    assert [r.id for r in rows] == [second.id, first.id]  # 标记时间倒序
    pending = await service.list_issue_reports("待质检复核")
    assert len(pending) == 2
    # 终态（已修正）不出列
    row = await service._issues.get(first.id)
    row.state = "已修正"
    await service._issues.save(row)
    assert [r.id for r in await service.list_issue_reports("all")] == [second.id]
    with pytest.raises(KbParamError):
        await service.list_issue_reports("已修正")  # 终态查询归后续批（错误码草案 400）


async def test_5_review_confirm_and_reject_state_machine(seeded: Any) -> None:
    """复核状态机：confirm→已修正；reject 必带理由（空 400）→已驳回带理由；
    仅待质检复核态可复核（重复 409）；单不存在 404。"""
    from app.domains.kb import KbConflictError, KbNotFoundError, KbParamError, KbService

    service = KbService(seeded, None, None)
    a = await service.report_fragment_issue("f1", "小李")
    b = await service.report_fragment_issue("f5", "小李")
    confirmed = await service.review_issue_report(a.id, "confirm", None, "阿强")
    assert confirmed.state == "已修正"
    with pytest.raises(KbParamError) as ei:
        await service.review_issue_report(b.id, "reject", "  ", "阿强")
    assert ei.value.code == "kb_issue_reject_reason_required"  # 驳回须写理由
    with pytest.raises(KbParamError):
        await service.review_issue_report(b.id, "verify", None, "阿强")  # action 越界
    rejected = await service.review_issue_report(
        b.id, "reject", "检泵日期与台账对不上，请核对后重新标记", "阿强"
    )
    assert rejected.state == "已驳回"
    assert rejected.reject_reason == "检泵日期与台账对不上，请核对后重新标记"
    with pytest.raises(KbConflictError) as ei:  # 重复复核 409
        await service.review_issue_report(b.id, "confirm", None, "阿强")
    assert ei.value.code == "kb_issue_state"
    with pytest.raises(KbConflictError):  # 已修正终态再复核 409
        await service.review_issue_report(a.id, "confirm", None, "阿强")
    with pytest.raises(KbNotFoundError):
        await service.review_issue_report("iss-none", "confirm", None, "阿强")


async def test_6_close_and_remark_loop(seeded: Any) -> None:
    """销记仅已驳回态（其他态 409）；重新标记＝新单入队＋旧驳回单转已销记——队列零悬挂。"""
    from app.domains.kb import KbConflictError, KbService

    service = KbService(seeded, None, None)
    a = await service.report_fragment_issue("f1", "小李")
    with pytest.raises(KbConflictError):  # 待质检复核态不可销记
        await service.close_issue_report(a.id, "小李")
    await service.review_issue_report(a.id, "reject", "切错了请重标", "阿强")
    closed = await service.close_issue_report(a.id, "小李")
    assert closed.state == "已销记 · 不修正"  # 端点 6 合同展示串
    row = await service._issues.get(a.id)
    assert row.state == "已销记"  # 落库四态 CHECK 值
    # 队列不出终态——零悬挂
    assert await service.list_issue_reports("all") == []
    # 重新标记闭环：旧驳回单（重新标记路径）转已销记＋新单入队
    b = await service.report_fragment_issue("f5", "小李")
    await service.review_issue_report(b.id, "reject", "理由", "阿强")
    again = await service.report_fragment_issue("f5", "小李")
    assert again.state == "待质检复核"
    old = await service._issues.get(b.id)
    assert old.state == "已销记"  # 旧驳回单随新标记转已销记
    assert len(await service.list_issue_reports("待质检复核")) == 1

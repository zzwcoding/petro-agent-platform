"""kb 域服务单测（sqlite 底座）——两拍/管线五步/定型语义/路由两拍/台账/活动流。

约定：桩 LLM 永不触网（B6 红线）；「直传」由 FakeObjectStorage.put 模拟客户端
落桶（未 put 即 confirm 409 判据源——00 §7.1）。夹具见同目录 conftest.py。
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import pytest

from app.domains.kb import (
    MODE_TEXT,
    KbConflictError,
    KbNotFoundError,
    KbParamError,
    KbService,
)
from app.domains.kb import domain as d
from app.domains.kb.store import (
    FragmentStore,
    IngestTaskRow,
    ReportRow,
    ReportStore,
    TaskStore,
    UploadStore,
)
from app.infra.clock import freeze, now

# 素材注源：设定书 §A.1 井档案样本（N-02 · 渤中28-1-N2 · EW · 2019-06-15 · CEP-A）
# ＋页面 RAW_TEXT 同源口径——业务事实零新增。
DEMO_TEXT = (
    "N-02 井完井报告\n"
    "1 基本情况\n"
    "N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW），"
    "2019-06-15 投产，当前状态生产中。\n"
    "2 完井段\n"
    "完井段详见射孔与防砂参数表，防砂方式筛管完井。\n"
)
BAD_BYTES = b"\xff\xfe\x00\x9b binary scan"  # 非 UTF-8——解析步人话失败素材
LIB_NAME = "完井报告库"
ACTOR = "阿强 · 平台运维"


async def wait_until(
    predicate: Callable[[], Awaitable[bool]], *, deadline_s: float = 5.0
) -> None:
    """轮询等待（管线任务体为 asyncio task——demo 量级亚秒完成）。"""
    import asyncio
    import time

    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if await predicate():
            return
        await asyncio.sleep(0.02)
    raise TimeoutError("条件等待超时")


def _done(service: KbService, task_id: str) -> Callable[[], Awaitable[bool]]:
    async def _check() -> bool:
        task = await service.ingest_task(task_id)
        return task.state in ("done", "failed")

    return _check


async def _make_lib(service: KbService, name: str = LIB_NAME) -> str:
    receipt = await service.create_library(name, "completion", ACTOR)
    return receipt.lib_id


async def _ingest(
    service: KbService,
    storage: Any,
    lib_id: str,
    filename: str = "N-02 井完井报告.pdf",
    content: bytes = DEMO_TEXT.encode("utf-8"),
) -> str:
    receipt = await service.upload_init(filename, 2048, lib_id, ACTOR)
    upload = await UploadStore(service._db).get(receipt.upload_id)
    assert upload is not None
    await storage.put(upload.object_key, content)
    confirm = await service.upload_confirm(receipt.upload_id, ACTOR)
    await wait_until(_done(service, confirm.task_id))
    return confirm.task_id


class TestCreateLibrary:
    async def test_create_shape_and_template(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        receipt = await service.create_library("措施效果库", "completion", ACTOR)
        assert receipt.lib_id.startswith("lib-")
        assert receipt.status == "active"
        assert receipt.config["graph"] is True  # completion 四开关全开（含图谱）
        assert receipt.activity_row.action == "新建库"
        assert "完井报告类" in receipt.activity_row.target

    async def test_create_blank_uses_default_profile(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        receipt = await service.create_library("空白库", "blank", ACTOR)
        assert receipt.config["graph"] is False  # 平台默认档：图谱关

    async def test_empty_name_400(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        with pytest.raises(KbParamError):
            await service.create_library("   ", "completion", ACTOR)

    async def test_bad_template_400(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        with pytest.raises(KbParamError):
            await service.create_library("X库", "wiki", ACTOR)

    async def test_duplicate_name_409(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        await _make_lib(service)
        with pytest.raises(KbConflictError) as excinfo:
            await service.create_library(f" {LIB_NAME} ", "monthly", ACTOR)
        assert excinfo.value.code == "kb_lib_name_duplicate"


class TestUploadTwoBeat:
    async def test_direct_lib_receipt(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        receipt = await service.upload_init("报告 A.pdf", 1024, lib_id, ACTOR)
        assert receipt.upload_id.startswith("up-")
        assert receipt.lib_id == lib_id and receipt.lib_name == LIB_NAME
        assert receipt.put_url.startswith("https://minio.test/put/")
        assert receipt.bucket == "报告原文"  # 显示名照抄（B1 出入对账 8）
        assert receipt.dup_warning is None

    async def test_unknown_lib_404(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        with pytest.raises(KbNotFoundError):
            await service.upload_init("报告 A.pdf", 1024, "lib-none", ACTOR)

    async def test_disabled_lib_400_with_code(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        await service.save_library_config(
            lib_id,
            switches={"semantic": True, "keyword": True, "wiki": True, "graph": True},
            mode="smart", add_summary=True, add_questions=True,
            status="disabled", actor_who=ACTOR,
        )
        with pytest.raises(KbParamError) as excinfo:
            await service.upload_init("报告 A.pdf", 1024, lib_id, ACTOR)
        assert excinfo.value.code == "kb_lib_disabled"

    async def test_dup_warning_non_blocking(self, kb_service: Any) -> None:
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)
        await _ingest(service, storage, lib_id, "N-02 井完井报告.pdf")
        second = await service.upload_init("N-02井完井报告.docx", 4096, lib_id, ACTOR)
        assert second.dup_warning is not None
        assert "疑似重复" in second.dup_warning
        # 非阻断：仍可 confirm 入库
        upload = await UploadStore(service._db).get(second.upload_id)
        assert upload is not None
        await storage.put(upload.object_key, DEMO_TEXT.encode("utf-8"))
        confirm = await service.upload_confirm(second.upload_id, ACTOR)
        assert confirm.task_id

    async def test_confirm_before_landing_409(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        receipt = await service.upload_init("报告 A.pdf", 1024, lib_id, ACTOR)
        with pytest.raises(KbConflictError) as excinfo:
            await service.upload_confirm(receipt.upload_id, ACTOR)
        assert excinfo.value.code == "kb_object_not_landed"

    async def test_confirm_twice_409(self, kb_service: Any) -> None:
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)
        receipt = await service.upload_init("报告 A.pdf", 1024, lib_id, ACTOR)
        upload = await UploadStore(service._db).get(receipt.upload_id)
        assert upload is not None
        await storage.put(upload.object_key, DEMO_TEXT.encode("utf-8"))
        await service.upload_confirm(receipt.upload_id, ACTOR)
        with pytest.raises(KbConflictError) as excinfo:
            await service.upload_confirm(receipt.upload_id, ACTOR)
        assert excinfo.value.code == "kb_upload_confirmed"


class TestPipelineAndLedger:
    async def test_five_steps_done_with_vectors(self, kb_service: Any) -> None:
        service, _, _, bus = kb_service
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, kb_service[1], lib_id)
        progress = await service.ingest_task(task_id)
        assert progress.state == "done"
        assert [n.key for n in progress.nodes] == ["parse", "chunk", "embed", "index", "enrich"]
        assert all(n.state == "finish" for n in progress.nodes)
        assert progress.nodes[1].note is not None
        assert progress.nodes[1].note.startswith("切段方式：智能切段")
        assert "关系图谱 ✓" in (progress.nodes[3].note or "")  # completion 模板图谱开
        assert progress.nodes[4].note is None  # 步 5 无说明行
        # 台账：refs＞0、状态已入库、详情恒 v1 原始解析
        reports = await service.list_reports()
        assert len(reports) == 1 and reports[0].status == "已入库" and reports[0].refs > 0
        detail = await service.report_detail(reports[0].id)
        assert detail.fragments and detail.fragments[0].versions[0].note == "原始解析"
        assert detail.fragments[0].versions[0].v == 1
        # 向量半边（sqlite JSON 近似）可查
        frags = await FragmentStore(service._db).for_report(reports[0].id)
        assert any(f.embedding for f in frags)
        # 产物两卡（随快照两复选）
        additions = await service.ingest_additions(task_id)
        assert additions.summary is not None and "N-02" in additions.summary["text"]
        assert additions.questions is not None and len(additions.questions["items"]) == 2
        # IngestCompleted 已发布（derivatives 订阅缝——B9 不直调）
        assert any(e.name == "IngestCompleted" for e in bus.published)

    async def test_config_freeze_semantics(self, kb_service: Any) -> None:
        """定型语义：入库后改配置→已定型快照不变；重跑＝按当前配置重新定型。"""
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id)
        before = await service.ingest_task(task_id)
        await service.save_library_config(
            lib_id,
            switches={"semantic": True, "keyword": True, "wiki": True, "graph": False},
            mode="fixed", add_summary=False, add_questions=False,
            status=None, actor_who=ACTOR,
        )
        after = await service.ingest_task(task_id)
        assert after.config_snapshot == before.config_snapshot  # 快照不被热切换
        retried = await service.retry_ingest(task_id, ACTOR)
        assert retried.config_snapshot["mode"] == "fixed"  # 重跑＝重新定型
        assert retried.config_snapshot["add_summary"] is False
        assert retried.source == "重跑定型"
        await wait_until(_done(service, retried.id))
        new_additions = await service.ingest_additions(retried.id)
        assert new_additions.summary is None and new_additions.questions is None

    async def test_failed_task_step_alignment(self, kb_service: Any) -> None:
        """失败语义：stop_at＝步短名、current_step＝对应序号（更正项⑪）＋人话原因。"""
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        task_id = await _ingest(
            service, kb_service[1], lib_id, "坏文件.pdf", BAD_BYTES
        )
        progress = await service.ingest_task(task_id)
        assert progress.state == "failed"
        assert progress.stop_at == "解析"
        assert progress.current_step == 0
        assert progress.reason is not None and "文本类报告" in progress.reason
        error_nodes = [n for n in progress.nodes if n.state == "error"]
        assert error_nodes and "可重试；仍失败请报修" in (error_nodes[0].note or "")
        tasks = await service.list_ingest_tasks("上传入库")
        assert any(t.id == task_id and t.stop_at == "解析" for t in tasks)
        # 台账两态：failed（无运行/卡住任务在挂）→「已入库」标（合同两态）
        reports = await service.list_reports()
        assert reports[0].status == "已入库"


class TestRetryAndStuck:
    async def test_retry_running_409(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        report = await ReportStore(service._db).create(
            ReportRow(id="rpt-x", lib_id=lib_id, doc="《X》", object_key="k")
        )
        await TaskStore(service._db).create(
            IngestTaskRow(
                id="task-run", upload_id=None, report_id=report.id, lib_id=lib_id,
                state="running", source="上传入库", current_step=0,
                nodes=[], config_snapshot={}, started_at=now(),
            )
        )
        with pytest.raises(KbConflictError):
            await service.retry_ingest("task-run", ACTOR)

    async def test_retry_unknown_404(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        with pytest.raises(KbNotFoundError):
            await service.retry_ingest("task-none", ACTOR)

    async def test_stuck_sweep_and_ledger_status(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        report = await ReportStore(service._db).create(
            ReportRow(id="rpt-y", lib_id=lib_id, doc="《Y》", object_key="k")
        )
        with freeze("2026-01-01T00:00:00"):
            await TaskStore(service._db).create(
                IngestTaskRow(
                    id="task-old", upload_id=None, report_id=report.id, lib_id=lib_id,
                    state="running", source="上传入库", current_step=2,
                    nodes=[], config_snapshot={}, started_at=datetime(2026, 1, 1),
                )
            )
        assert await service.sweep_stuck() == 1
        row = await TaskStore(service._db).get("task-old")
        assert row is not None and row.state == "stuck"
        # 台账两态：stuck 任务在挂 → 「入库中」
        assert await service._ledger_status(report.id) == "入库中"


class TestTaskSourceFilter:
    async def test_source_filter(self, kb_service: Any) -> None:
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id)
        retried = await service.retry_ingest(task_id, ACTOR)
        await wait_until(_done(service, retried.id))
        uploads = await service.list_ingest_tasks("上传入库")
        reruns = await service.list_ingest_tasks("重跑定型")
        assert all(t.source == "上传入库" for t in uploads)
        assert any(t.id == retried.id for t in reruns)
        assert all(t.source == "重跑定型" for t in reruns)
        with pytest.raises(KbParamError):
            await service.list_ingest_tasks("越界值")

    async def test_additions_not_ready_409(self, kb_service: Any) -> None:
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id)
        assert (await service.ingest_task(task_id)).state == "done"
        await service.ingest_additions(task_id)
        reports = await ReportStore(service._db).all()
        await TaskStore(service._db).create(
            IngestTaskRow(
                id="task-running2", upload_id=None, report_id=reports[0].id,
                lib_id=lib_id, state="running", source="上传入库", current_step=0,
                nodes=[], config_snapshot={}, started_at=now(),
            )
        )
        with pytest.raises(KbConflictError):
            await service.ingest_additions("task-running2")


class TestLibrariesAndActivities:
    async def test_library_list_switches_from_last_run(self, kb_service: Any) -> None:
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)  # completion → 图谱开
        await _ingest(service, storage, lib_id)
        row = next(lib for lib in await service.list_libraries() if lib.id == lib_id)
        assert row.last_ingestion is not None
        assert row.last_ingestion["switches"]["graph"] is True
        # 改配置不影响快照（两态分离）
        await service.save_library_config(
            lib_id,
            switches={"semantic": True, "keyword": True, "wiki": True, "graph": False},
            mode="smart", add_summary=True, add_questions=True,
            status=None, actor_who=ACTOR,
        )
        row_after = next(
            lib for lib in await service.list_libraries() if lib.id == lib_id
        )
        assert row_after.last_ingestion is not None
        assert row_after.last_ingestion["switches"]["graph"] is True

    async def test_graph_filter_and_keyword(self, kb_service: Any) -> None:
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)
        await _ingest(service, storage, lib_id)
        on = await service.list_libraries(graph="on")
        off = await service.list_libraries(graph="off")
        assert any(lib.id == lib_id for lib in on)
        assert all(lib.id != lib_id for lib in off)
        assert await service.list_libraries(keyword="不存在") == []
        with pytest.raises(KbParamError):
            await service.list_libraries(graph="both")

    async def test_activities_readonly_rows(self, kb_service: Any) -> None:
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)
        await _ingest(service, storage, lib_id)
        await service.save_library_config(
            lib_id,
            switches={"semantic": True, "keyword": True, "wiki": True, "graph": True},
            mode="mixed", add_summary=True, add_questions=True,
            status=None, actor_who=ACTOR,
        )
        rows = await service.library_activities(lib_id)
        actions = [r.action for r in rows]
        assert actions[0] == "修改库配置"  # 时间倒序
        assert "上传报告" in actions and "新建库" in actions
        assert rows[0].target and "下次入库生效" in rows[0].target

    async def test_disable_enable_flow(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        saved = await service.save_library_config(
            lib_id,
            switches={"semantic": True, "keyword": True, "wiki": True, "graph": False},
            mode="smart", add_summary=True, add_questions=True,
            status="disabled", actor_who=ACTOR,
        )
        assert saved.status == "disabled"
        assert saved.hint == "已保存——开关在下次入库时生效，正在处理的报告不受影响。"
        assert "停用库" in {r.action for r in await service.library_activities(lib_id)}
        enabled = await service.save_library_config(
            lib_id,
            switches={"semantic": True, "keyword": True, "wiki": True, "graph": False},
            mode="smart", add_summary=True, add_questions=True,
            status="active", actor_who=ACTOR,
        )
        assert enabled.status == "active"
        assert "启用库" in {r.action for r in await service.library_activities(lib_id)}

    async def test_config_validation_400(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        base = {"semantic": True, "keyword": True, "wiki": True, "graph": False}
        with pytest.raises(KbParamError):
            await service.save_library_config(
                lib_id, switches=base, mode="越界", add_summary=True,
                add_questions=True, status=None, actor_who=ACTOR,
            )
        with pytest.raises(KbParamError):
            await service.save_library_config(
                lib_id, switches={"semantic": True}, mode="smart", add_summary=True,
                add_questions=True, status=None, actor_who=ACTOR,
            )
        with pytest.raises(KbParamError):
            await service.save_library_config(
                lib_id, switches=base, mode="smart", add_summary=True,
                add_questions=True, status="archived", actor_who=ACTOR,
            )

    async def test_library_config_read_with_saved_at(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        lib_id = await _make_lib(service)
        view = await service.library_config(lib_id)
        assert view.switches["graph"] is True and view.saved_at is None
        await service.save_library_config(
            lib_id,
            switches={"semantic": True, "keyword": True, "wiki": True, "graph": False},
            mode="mixed", add_summary=False, add_questions=True,
            status=None, actor_who=ACTOR,
        )
        view2 = await service.library_config(lib_id)
        assert view2.mode == "mixed" and view2.saved_by == ACTOR


class TestRouting:
    async def test_route_suggestion_two_beat(self, kb_service: Any) -> None:
        service, storage, completer, _ = kb_service
        lib_id = await _make_lib(service)
        receipt = await service.upload_init(
            "完井总结.pdf", 1024, None, ACTOR, suggested_topic="完井投产情况"
        )
        assert receipt.routing is not None
        assert receipt.routing.mode == "existing"
        assert receipt.routing.lib_id == lib_id
        assert receipt.routing.confidence is not None
        # 建议归库随受理登记（lib_id＝建议库）；confirm 即人确认执行——路由定型
        upload = await UploadStore(service._db).get(receipt.upload_id)
        assert upload is not None
        assert upload.lib_id == lib_id
        await storage.put(upload.object_key, DEMO_TEXT.encode("utf-8"))
        confirm = await service.upload_confirm(receipt.upload_id, ACTOR)
        assert confirm.lib_id == lib_id
        upload_after = await UploadStore(service._db).get(receipt.upload_id)
        assert upload_after is not None
        assert upload_after.routed_lib_id == lib_id  # confirm 定型路由三列
        assert upload_after.route_confirmed_by == ACTOR
        assert any(caller == "kb.route" for caller, _ in completer.calls)

    async def test_route_new_lib_suggestion_carries_template(self, kb_service: Any) -> None:
        service, _, completer, _ = kb_service
        completer.answers["kb.route"] = (
            '{"mode": "new", "template": "monthly", "reason": "月报话题", "confidence": 0.6}'
        )
        receipt = await service.upload_init("2026-08 月报.pdf", 1024, None, ACTOR)
        assert receipt.routing is not None
        assert receipt.routing.mode == "new" and receipt.routing.template == "monthly"

    async def test_route_llm_failure_degrades_to_manual(self, kb_service: Any) -> None:
        service, storage, completer, _ = kb_service
        completer.answers["kb.route"] = RuntimeError("上游不可用")
        receipt = await service.upload_init("任意报告.pdf", 1024, None, ACTOR)
        assert receipt.routing is not None
        assert receipt.routing.mode is None
        assert "手动指定" in (receipt.routing.reason or "")
        # 分析失败 → 目标库未定：空体确认 409（路由未定型），人带 lib_id 确认即执行
        lib_id = await _make_lib(service)
        upload = await UploadStore(service._db).get(receipt.upload_id)
        assert upload is not None and upload.lib_id is None
        await storage.put(upload.object_key, DEMO_TEXT.encode("utf-8"))
        with pytest.raises(KbConflictError) as excinfo:
            await service.upload_confirm(receipt.upload_id, ACTOR)
        assert excinfo.value.code == "kb_route_unresolved"
        confirm = await service.upload_confirm(receipt.upload_id, ACTOR, lib_id=lib_id)
        assert confirm.lib_id == lib_id

    async def test_route_filename_fallback_topic(self, kb_service: Any) -> None:
        service, _, completer, _ = kb_service
        await _make_lib(service)
        await service.upload_init("生产月报.pdf", 100, None, ACTOR)  # 无 topic——文件名兜底
        assert any(
            "生产月报" in content for caller, content in completer.calls
            if caller == "kb.route"
        )


def test_mode_texts_cover_three_modes() -> None:
    assert set(MODE_TEXT) == {"smart", "fixed", "mixed"}


class TestIndexSearch:
    async def test_index_search_two_legs_merge(self, kb_service: Any) -> None:
        """P1-08a 报告索引检索读面：向量腿＋trigram 关键词腿同池去重、按分倒序。"""
        service, storage, _, _ = kb_service
        lib_id = await _make_lib(service)
        await _ingest(service, storage, lib_id)
        hits = await service.index_search("渤中28-1")
        assert hits, "trigram 关键词腿应命中演示文本"
        assert all(h.leg in ("vector", "keyword") for h in hits)
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True)
        # 同片段只留高分腿（同池去重）
        assert len({h.fragment_id for h in hits}) == len(hits)
        full = await service.index_search("N-02 完井报告")
        assert full and full[0].report  # 报告名随命中面携出（装配候选标签消费）
        assert len(await service.index_search("渤海", top_k=2)) <= 2

    async def test_index_search_empty_corpus(self, kb_service: Any) -> None:
        service, _, _, _ = kb_service
        assert await service.index_search("任何问题") == []

    async def test_trigram_coverage_full_substring_is_one(self) -> None:
        """全问句子串命中→覆盖率 1.0（pg_trgm 子串匹配的阶段 1 语义代理）。"""
        assert d.trigram_coverage("渤中28-1 投产", "渤中28-1 投产于 2019-06") == 1.0
        assert d.trigram_coverage("完全无关的问句", "渤中28-1 投产于 2019-06") < 0.5

"""domains.kb.service —— 知识管线域服务：编排 store/对象存储/gateway/embedder（语义在 domain.py）。

公开面照 98 §3.4 卡 B1 面＋v0.3 建库批：create_library / list_reports /
report_detail / download_url / revise_fragment（壳——修正动作归 P1-02b）/
upload_init / upload_confirm / list_ingest_tasks / ingest_task / ingest_additions /
retry_ingest / list_libraries / library_config / save_library_config /
library_activities / record_activity（B9 例外族写口，供 P1-04/P1-05 事务内追加）。

管线编排（00 §5 异步任务惯例——gateway drill 先例同构）：
- 任务体＝进程内 asyncio task；受理（confirm）即落行开跑、200 同步返回（B1 特例）；
- 五步推进写 nodes jsonb＋current_step（note 服务端按 config_snapshot 组装）；
- 失败＝按阶段定位（stop_at＝五步短名）＋人话原因（不发明错误码数字——F32 红线）；
  failed 的 current_step＝stop_at 对应步序号（B1 更正项⑪）；
- 跳过＝配置性支路不跑不花钱（semantic 关→不写向量；keyword 关→不建倒排；
  wiki/graph 支路本票留缝——derivatives 经 IngestCompleted 事件订阅，B9）；
- 富化子任务失败不阻塞整卷完成（F32）；
- 重跑＝一次新入库（新任务行 source=重跑定型，按当前待生效配置重新定型快照；
  stuck 重试内含停止——取消旧 asyncio task）；
- stuck＝超时无进展后台巡检（阈值 STUCK_SWEEP_SECONDS；lifespan 启动收口＋周期巡检）。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.gateway import Completion
from app.domains.kb import domain as d
from app.domains.kb.store import (
    ActivityStore,
    FragmentRow,
    FragmentStore,
    FragmentVersionRow,
    IngestTaskRow,
    IssueReportRow,
    IssueStore,
    LibraryConfigRow,
    LibraryRow,
    LibraryStore,
    ReportRow,
    ReportStore,
    TaskStore,
    UploadRow,
    UploadStore,
)
from app.infra.clock import DISPLAY_FMT, now
from app.infra.config import load_entity_type_names
from app.infra.db import ConnectionManager
from app.infra.eventbus import EventBus, make_event
from app.infra.object_storage import REPORTS_BUCKET, ObjectStorage

LOGGER = logging.getLogger("domains.kb")

# LLM 出口（B6）：别名照 P1-00 拍板基线（起草/生成一律 petro-main）。
ROUTE_ALIAS = "petro-main"
INGEST_ALIAS = "petro-main"


class Completer(Protocol):
    """LLM 出口 seam（生产装配＝GatewayService——B6 唯一出口；测试注桩）。"""

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Completion: ...


@dataclass
class _TaskRuntime:
    """进程内任务体登记（stuck 重试内含停止——取消句柄）。"""

    tasks: dict[str, asyncio.Task[None]]


class KbService:
    """kb 域服务（编排；合同语义在 domain.py，持久在 store.py）。"""

    def __init__(
        self,
        db: ConnectionManager,
        gateway: Completer,
        storage: ObjectStorage,
        *,
        embedder: d.EmbeddingBackend | None = None,
        eventbus: EventBus | None = None,
        step_seconds: float = 0.0,
        extract_snapshot_loader: Callable[[str], Awaitable[dict[str, Any] | None]]
        | None = None,
    ) -> None:
        self._db = db
        self._gateway = gateway
        self._storage = storage
        self._embedder: d.EmbeddingBackend = embedder or d.LocalHashEmbedder()
        self._eventbus = eventbus
        self._step_seconds = step_seconds
        self._libs = LibraryStore(db)
        self._uploads = UploadStore(db)
        self._tasks = TaskStore(db)
        self._reports = ReportStore(db)
        self._fragments = FragmentStore(db)
        self._issues = IssueStore(db)
        self._activities = ActivityStore(db)
        self._runtime = _TaskRuntime(tasks={})
        self._rebuild_context: dict[str, str] = {}
        # 抽取设置快照装载（B5 端点 3 注记——confirm 时刻一并定型入
        # kb_ingest_task.extract_snapshot；main.py 组合根注入 derivatives 提供
        # 的装载函数——B9：kb 禁 import derivatives，运行期只见 callable）。
        self._extract_snapshot_loader = extract_snapshot_loader

    # ---------- 端点 15：建库（v0.3 建库批） ----------

    async def create_library(
        self, lib_name: str, biz_template: str, actor_who: str
    ) -> d.CreateLibReceipt:
        name = (lib_name or "").strip()
        if not name:
            raise d.KbParamError("库名不能为空")
        if biz_template not in d.BIZ_TEMPLATES:
            raise d.KbParamError(
                f"biz_template 越界：{biz_template}（允许值 {'|'.join(d.BIZ_TEMPLATES)}）"
            )
        if await self._libs.by_name(name) is not None:
            raise d.KbConflictError("库名与现有库重复，请换一个名称", code="kb_lib_name_duplicate")
        lib = LibraryRow(
            id=d.new_lib_id(), name=name, biz_template=biz_template, status="active"
        )
        profile = d.TEMPLATE_CONFIGS[biz_template]
        config = LibraryConfigRow(
            lib_id=lib.id,
            semantic=profile["semantic"],
            keyword=profile["keyword"],
            wiki=profile["wiki"],
            graph=profile["graph"],
            mode=profile["mode"],
            add_summary=profile["add_summary"],
            add_questions=profile["add_questions"],
        )
        target = f"{name} · 业务模板：{d.TEMPLATE_LABELS[biz_template]}（默认配置已生成）"
        lib = await self._libs.create_library_with_config(
            lib, config, activity=(actor_who, "新建库", target)
        )
        return d.CreateLibReceipt(
            lib_id=lib.id,
            lib_name=lib.name,
            biz_template=biz_template,
            status=lib.status,
            config=dict(profile),
            activity_row=d.ActivityRow(time=now().strftime(DISPLAY_FMT), who=actor_who,
                                       action="新建库", target=target),
        )

    # ---------- 端点 5：直传受理（两拍第一拍） ----------

    async def upload_init(
        self,
        filename: str,
        size: int,
        lib_id: str | None,
        actor_who: str,
        *,
        suggested_topic: str | None = None,
    ) -> d.UploadReceipt:
        filename = (filename or "").strip()
        if not filename or size <= 0:
            raise d.KbParamError("filename/size 形状非法")
        suggestion: d.RouteSuggestion | None = None
        target_lib: LibraryRow | None = None
        if lib_id:
            # 人工直指定目标库——跳过话题分析（路由专节合同）。
            target_lib = await self._libs.get(lib_id)
            if target_lib is None:
                raise d.KbNotFoundError(f"目标库不存在：{lib_id}")
            if target_lib.status != "active":
                raise d.KbParamError(
                    "目标库已停用，不接新入库（启用后恢复受理）", code="kb_lib_disabled"
                )
        else:
            # 入库路由：LLM＋本体话题分析（全局默认能力——不依赖目标库配置）；
            # LLM 只建议、人确认后执行（建议随受理响应返回，confirm 定型）。
            suggestion = await self._analyze_route(filename, suggested_topic)
            if suggestion is not None and suggestion.mode == "existing" and suggestion.lib_id:
                target_lib = await self._libs.get(suggestion.lib_id)
                if target_lib is None or target_lib.status != "active":
                    suggestion = d.RouteSuggestion(
                        mode=None, topic=suggestion.topic,
                        reason="建议归库不可用（不存在或已停用）",
                    )
                    target_lib = None
        dup_warning = await self._dup_warning(filename, target_lib.id if target_lib else None)
        object_key = f"reports/{d.new_upload_id()}/{filename}"
        put_url = await self._storage.presign_put(object_key)
        at = now()
        row = UploadRow(
            id=d.new_upload_id(),
            filename=filename,
            size=size,
            lib_id=target_lib.id if target_lib else None,
            bucket=REPORTS_BUCKET,
            status="pending",
            expires_at=at + timedelta(seconds=60 * 30),
            suggested_topic=suggested_topic,
            object_key=object_key,
        )
        await self._uploads.create(row)
        return d.UploadReceipt(
            upload_id=row.id,
            lib_id=target_lib.id if target_lib else None,
            lib_name=target_lib.name if target_lib else None,
            dup_warning=dup_warning,
            put_url=put_url,
            expires_at=(at + timedelta(seconds=60 * 30)).strftime(DISPLAY_FMT),
            bucket=d.BUCKET_DISPLAY,
            routing=suggestion,
        )

    async def _analyze_route(
        self, filename: str, suggested_topic: str | None
    ) -> d.RouteSuggestion | None:
        """话题分析（gateway.complete petro-main＋entity_types.json 词表辅助）。"""
        libs = {lib.name: lib.id for lib in await self._libs.all() if lib.status == "active"}
        topic = (suggested_topic or "").strip() or filename
        prompt = d.ROUTE_PROMPT_TEMPLATE.format(
            libs="、".join(libs) or "（暂无）",
            entity_types="、".join(load_entity_type_names()),
            topic=topic,
            filename=filename,
        )
        try:
            completion = await self._gateway.complete(
                ROUTE_ALIAS, [{"role": "user", "content": prompt}], caller="kb.route"
            )
        except Exception as exc:  # 路由分析失败不拦受理——建议不可用，请手动指定
            LOGGER.warning("kb 入库路由话题分析失败：%s", exc)
            return d.RouteSuggestion(
                mode=None, topic=topic, reason="话题分析不可用，请手动指定目标库"
            )
        suggestion = d.parse_route_suggestion(completion.content, libs)
        if suggestion.topic is None:
            suggestion = d.RouteSuggestion(
                mode=suggestion.mode, topic=topic, lib_id=suggestion.lib_id,
                lib_name=suggestion.lib_name, template=suggestion.template,
                reason=suggestion.reason, confidence=suggestion.confidence,
            )
        return suggestion

    async def _dup_warning(self, filename: str, lib_id: str | None) -> str | None:
        """同名重复检测（非阻断——确认权在人；比对口径差异登记票面）。"""
        normalized = d.normalize_filename(filename)
        if not normalized:
            return None
        for report in await self._reports.all():
            if lib_id is not None and report.lib_id != lib_id:
                continue
            stem = report.doc.strip("《》")
            if d.normalize_filename(stem) == normalized:
                return f"{d.DUP_WARNING}已有同名报告《{stem}》。"
        return None

    # ---------- 端点 6：确认入库（两拍第二拍——定型点） ----------

    async def upload_confirm(
        self, upload_id: str, actor_who: str, *, lib_id: str | None = None
    ) -> d.ConfirmReceipt:
        """确认入库：核实落桶（HEAD）→ 建 report/task → config_snapshot 定型 → 开跑。

        lib_id 形参＝路由确认通道（入库路由专节：路由确认并入 confirm 定型链路；
        人确认的建议库/人工改选经此携带；缺省＝受理已定目标库——差异登记票面）。
        """
        upload = await self._uploads.get(upload_id)
        if upload is None:
            raise d.KbNotFoundError(f"上传受理单不存在（含已过期清理）：{upload_id}")
        if upload.status == "confirmed":
            raise d.KbConflictError("直传凭证已用——请重新受理", code="kb_upload_confirmed")
        if upload.status == "expired" or now() > upload.expires_at:
            await self._expire(upload)
            raise d.KbConflictError("直传凭证已过期——请重新受理", code="kb_upload_expired")
        target_lib_id = lib_id or upload.lib_id
        if target_lib_id is None:
            raise d.KbConflictError(
                "路由未定型：本次受理未确定目标库——请带确认库号（lib_id）确认，"
                "或重新受理并指定目标库",
                code="kb_route_unresolved",
            )
        lib = await self._libs.get(target_lib_id)
        if lib is None:
            raise d.KbNotFoundError(f"目标库不存在：{target_lib_id}")
        if lib.status != "active":
            raise d.KbConflictError(
                f"目标库「{lib.name}」已停用，不接新入库", code="kb_lib_disabled"
            )
        if not await self._storage.exists(upload.object_key):
            raise d.KbConflictError(
                "对象尚未落桶——请先完成直传再确认入库", code="kb_object_not_landed"
            )
        snapshot = await self._snapshot_of(lib.id)
        extract_snapshot = await self._extract_snapshot_of(lib.id)
        report = ReportRow(
            id=d.new_report_id(),
            lib_id=lib.id,
            doc=d.doc_display(upload.filename),
            object_key=upload.object_key,
        )
        task = IngestTaskRow(
            id=d.new_task_id(),
            upload_id=upload.id,
            report_id=report.id,
            lib_id=lib.id,
            state="running",
            source="上传入库",
            current_step=0,
            nodes=[n.as_dict() for n in self._build_nodes()],
            config_snapshot=dict(snapshot),
            extract_snapshot=extract_snapshot,
            started_at=now(),
        )
        target = f"{report.doc}"
        task = await self._tasks.confirm_upload(
            upload, report, task,
            routed_lib_id=lib.id, confirmed_by=actor_who,
            activity=(actor_who, "上传报告", target),
        )
        self._spawn_pipeline(task.id)
        return d.ConfirmReceipt(
            task_id=task.id,
            upload_id=upload.id,
            doc=report.doc,
            lib_id=lib.id,
            lib_name=lib.name,
            source=task.source,
            state=task.state,
            current_step=int(task.current_step),
            config_snapshot=dict(snapshot),
        )

    async def _expire(self, upload: UploadRow) -> None:
        upload.status = "expired"
        upload.updated_at = now()
        async with self._db.session() as session:
            await session.merge(upload)

    async def _snapshot_of(self, lib_id: str) -> dict[str, Any]:
        """待生效配置 → 定型快照（confirm 时刻；config_snapshot 合同键集）。"""
        row = await self._libs.config_of(lib_id)
        if row is None:
            return dict(d.DEFAULT_CONFIG)
        return {
            "semantic": row.semantic,
            "keyword": row.keyword,
            "wiki": row.wiki,
            "graph": row.graph,
            "mode": row.mode,
            "add_summary": row.add_summary,
            "add_questions": row.add_questions,
        }

    async def _extract_snapshot_of(self, lib_id: str) -> dict[str, Any] | None:
        """抽取设置定型快照（confirm 时刻一并快照——B5 端点 3 注记；99 §2.5
        kb_ingest_task.extract_snapshot 列）。装载器未注入/装载失败 → None
        （graph 支路回退当前待生效配置——历史任务行同象）。"""
        if self._extract_snapshot_loader is None:
            return None
        try:
            return await self._extract_snapshot_loader(lib_id)
        except Exception:
            LOGGER.exception("抽取设置快照装载失败 lib=%s（定型为空）", lib_id)
            return None

    # ---------- 端点 7：任务列表（source 筛参——v0.2 拍板） ----------

    async def list_ingest_tasks(self, source: str | None = None) -> list[d.TaskView]:
        if source not in (None, "all") and source not in d.SOURCE_VALUES:
            raise d.KbParamError(
                f"source 越界：{source}（允许值 all|{'|'.join(d.SOURCE_VALUES)}）"
            )
        rows = await self._tasks.all()
        if source not in (None, "all"):
            rows = [row for row in rows if row.source == source]
        out: list[d.TaskView] = []
        for row in rows:
            lib = await self._libs.get(row.lib_id)
            report = await self._reports.get(row.report_id)
            out.append(
                d.TaskView(
                    id=row.id,
                    doc=report.doc if report else "",
                    lib_id=row.lib_id,
                    lib_name=lib.name if lib else "",
                    source=row.source,
                    state=row.state,
                    current_step=int(row.current_step),
                    stop_at=row.stop_at,
                    reason=row.reason,
                )
            )
        return out

    # ---------- 端点 8：轮询（五步节点＋服务端组装说明） ----------

    async def ingest_task(self, task_id: str) -> d.TaskProgress:
        row = await self._tasks.get(task_id)
        if row is None:
            raise d.KbNotFoundError(f"入库任务不存在：{task_id}")
        lib = await self._libs.get(row.lib_id)
        return self._task_progress(row, lib.name if lib else "")

    def _task_progress(self, row: IngestTaskRow, lib_name: str) -> d.TaskProgress:
        nodes = [
            d.TaskNode(key=n["key"], label=n["label"], state=n["state"], note=n.get("note"))
            for n in row.nodes
        ]
        return d.TaskProgress(
            id=row.id,
            state=row.state,
            source=row.source,
            current_step=int(row.current_step),
            stop_at=row.stop_at,
            reason=row.reason,
            nodes=nodes,
            config_snapshot=dict(row.config_snapshot),
        )

    def _build_nodes(self) -> list[d.TaskNode]:
        return [d.TaskNode(key=key, label=d.STEP_LABELS[key]) for key in d.STEP_KEYS]

    # ---------- 端点 9：索引期加法产物（done 后可读） ----------

    async def ingest_additions(self, task_id: str) -> d.AdditionsView:
        row = await self._tasks.get(task_id)
        if row is None:
            raise d.KbNotFoundError(f"入库任务不存在：{task_id}")
        if row.state != "done":
            raise d.KbConflictError("任务未完成——产物在 done 后可读", code="kb_additions_not_ready")
        report = await self._reports.get(row.report_id)
        doc = report.doc if report else ""
        snapshot = row.config_snapshot
        summary: dict[str, Any] | None = None
        questions: dict[str, Any] | None = None
        if snapshot.get("add_summary", True):
            for frag in await self._fragments.for_report(row.report_id):
                if frag.type == "摘要块":
                    text = await self._fragment_text(frag)
                    summary = {"type": "摘要块", "title": "全文档摘要（自动生成）", "text": text}
                    break
        if snapshot.get("add_questions", True):
            items: list[str] = []
            for frag in await self._fragments.for_report(row.report_id):
                if frag.type == "问题块":
                    text = await self._fragment_text(frag)
                    items.extend(line.strip() for line in text.splitlines() if line.strip())
            if items:
                questions = {
                    "type": "问题块",
                    "title": "这份报告可能被问的 10 个问题（自动生成）",
                    "items": items,
                }
        return d.AdditionsView(task_id=row.id, doc=doc, summary=summary, questions=questions)

    async def _fragment_text(self, frag: FragmentRow) -> str:
        versions = await self._fragments.versions_of([frag.id])
        rows = versions.get(frag.id, [])
        return rows[-1].text if rows else ""

    # ---------- 端点 10：重试/重跑（stuck 内含停止；重跑＝重新定型） ----------

    async def retry_ingest(self, task_id: str, actor_who: str) -> d.TaskProgress:
        old = await self._tasks.get(task_id)
        if old is None:
            raise d.KbNotFoundError(f"入库任务不存在：{task_id}")
        if old.state == "running":
            raise d.KbConflictError("任务处理中，不可重试（重试仅对 failed/stuck/done 开放）")
        # stuck 内含停止：先终止旧执行（进程内任务体），再重建管线。
        running = self._runtime.tasks.pop(task_id, None)
        if running is not None and not running.done():
            running.cancel()
        lib = await self._libs.get(old.lib_id)
        if lib is None:
            raise d.KbNotFoundError(f"目标库不存在：{old.lib_id}")
        snapshot = await self._snapshot_of(lib.id)  # 重跑＝按当前待生效配置重新定型
        task = IngestTaskRow(
            id=d.new_task_id(),
            upload_id=old.upload_id,
            report_id=old.report_id,
            lib_id=old.lib_id,
            state="running",
            source="重跑定型",
            current_step=0,
            nodes=[n.as_dict() for n in self._build_nodes()],
            config_snapshot=snapshot,
            extract_snapshot=await self._extract_snapshot_of(lib.id),
            started_at=now(),
        )
        task = await self._tasks.create(task)
        self._spawn_pipeline(task.id)
        return self._task_progress(task, lib.name)

    # ---------- 端点 1/2/3：台账/详情/下载直链 ----------

    async def list_reports(
        self, lib: str | None = None, keyword: str | None = None
    ) -> list[d.ReportLedgerRow]:
        libs = {row.id: row for row in await self._libs.all()}
        target_lib_id: str | None = None
        if lib not in (None, "all"):
            target = next((row for row in libs.values() if row.name == lib), None)
            if target is None:
                raise d.KbParamError(f"lib 筛选值不存在：{lib}（允许值 all|现有库名）")
            target_lib_id = target.id
        needle = (keyword or "").strip().casefold()
        out: list[d.ReportLedgerRow] = []
        for report in await self._reports.all():
            lib_row = libs.get(report.lib_id)
            if target_lib_id is not None and report.lib_id != target_lib_id:
                continue
            if needle and needle not in report.doc.casefold() and (
                lib_row is None or needle not in lib_row.name.casefold()
            ):
                continue
            out.append(
                d.ReportLedgerRow(
                    id=report.id,
                    doc=report.doc,
                    lib_id=report.lib_id,
                    lib=lib_row.name if lib_row else "",
                    refs=await self._fragments.count_by_report(report.id),
                    wiki=(
                        f"v{report.wiki_current_version}"
                        if report.wiki_current_version is not None
                        else None
                    ),
                    status=await self._ledger_status(report.id),
                )
            )
        return out

    async def _ledger_status(self, report_id: str) -> str:
        """台账两态（端点 1）：存在运行/疑似卡住任务即「入库中」，否则「已入库」。"""
        latest = await self._tasks.latest_for_report(report_id)
        if latest is not None and latest.state in ("running", "stuck"):
            return "入库中"
        return "已入库"

    async def report_detail(self, report_id: str) -> d.ReportDetail:
        report = await self._reports.get(report_id)
        if report is None:
            raise d.KbNotFoundError(f"报告不存在：{report_id}")
        lib = await self._libs.get(report.lib_id)
        fragments: list[d.FragmentRow] = []
        frags = await self._fragments.for_report(report_id)
        version_map = await self._fragments.versions_of([f.id for f in frags])
        for frag in frags:
            if frag.is_parent_only:
                continue  # 父块不对外寻址（F30）
            versions = version_map.get(frag.id, [])
            fragments.append(
                d.FragmentRow(
                    id=frag.id,
                    type=frag.type,
                    path=frag.section or "正文",
                    text=versions[-1].text if versions else "",
                    version=frag.current_version,
                    versions=[
                        d.FragmentVersionRow(v=ver.v, text=ver.text, note=ver.note)
                        for ver in versions
                    ],
                )
            )
        refs = await self._fragments.count_by_report(report_id)
        return d.ReportDetail(
            id=report.id,
            doc=report.doc,
            lib_id=report.lib_id,
            lib=lib.name if lib else "",
            subject=report.subject,
            refs=refs,
            wiki=(
                f"v{report.wiki_current_version}"
                if report.wiki_current_version is not None
                else None
            ),
            status=await self._ledger_status(report_id),
            related_objects=list(report.related_objects),
            fragments=fragments,
        )

    async def download_url(self, report_id: str) -> tuple[str, str]:
        """返回 (download_url, expires_at 展示串)——GET 直链小时级（00 §7.2）。"""
        report = await self._reports.get(report_id)
        if report is None:
            raise d.KbNotFoundError(f"报告不存在：{report_id}")
        url = await self._storage.presign_get(report.object_key)
        expires_at = (now() + timedelta(hours=1)).strftime(DISPLAY_FMT)
        return url, expires_at

    # ---------- 端点 4：片段人工修正（F30 增补——乐观锁＋记版＋索引重建） ----------

    async def revise_fragment(
        self, report_id: str, fragment_id: str, base_version: int, text: str,
        actor_who: str,
    ) -> d.ReviseReceipt:
        """片段人工修正：乐观锁（base_version 落后 409）＋逐次记版（v1 原始
        不可变）＋重建折算「片段修正」入库任务（向量重嵌该片段＋问题块重生）
        ＋FragmentRevised 事件（wiki 重铸联动——derivatives 订阅，B9）。"""
        report = await self._reports.get(report_id)
        if report is None:
            raise d.KbNotFoundError(f"报告不存在：{report_id}")
        frag = await self._fragments.get(fragment_id)
        if frag is None or frag.report_id != report_id:
            raise d.KbNotFoundError(f"片段不存在：{fragment_id}")
        stripped = (text or "").strip()
        if not stripped:
            raise d.KbParamError("修正内容不能为空（修正须有内容）")
        if base_version != frag.current_version:
            raise d.KbConflictError(
                "别人已改过这段，请刷新后再改", code="kb_fragment_version_conflict"
            )
        new_v = frag.current_version + 1
        # 父块锚随版本携行（mixed 子块的回捞锚——修正不丢父块指向，B2 端点 2 依赖）
        prev_versions = (await self._fragments.versions_of([fragment_id])).get(fragment_id, [])
        parent_anchor = prev_versions[-1].context_text if prev_versions else None
        version = FragmentVersionRow(
            fragment_id=fragment_id, v=new_v, text=stripped,
            context_text=parent_anchor, note="人工修正",
        )
        frag.hit_text = stripped  # 命中文本随当前版本推进（关键词路读面消费）
        frag, version = await self._fragments.revise(frag, version)
        target = f"{report.doc} · {frag.section or '正文'}（修正＋触发百科重铸）"
        activity_row = await self._activities.append(
            report.lib_id, who=actor_who, action="修正片段", target=target
        )
        # 修正触发的重建算入库任务（v0.2 拍板）——按当前待生效配置重新定型。
        snapshot = await self._snapshot_of(report.lib_id)
        task = IngestTaskRow(
            id=d.new_task_id(),
            upload_id=None,
            report_id=report_id,
            lib_id=report.lib_id,
            state="running",
            source="片段修正",
            current_step=0,
            nodes=[n.as_dict() for n in self._build_nodes()],
            config_snapshot=dict(snapshot),
            started_at=now(),
        )
        task = await self._tasks.create(task)
        self._spawn_rebuild(task.id, fragment_id)
        await self._emit_fragment_revised(task, fragment_id)
        versions = (await self._fragments.versions_of([fragment_id])).get(fragment_id, [])
        return d.ReviseReceipt(
            id=fragment_id,
            version=frag.current_version,
            versions=[
                d.FragmentVersionRow(v=ver.v, text=ver.text, note=ver.note)
                for ver in versions
            ],
            rebuild=d.RebuildInfo(triggered=True, hint=d.REBUILD_HINT),
            activity_row=d.ActivityRow(
                time=activity_row.time.strftime(DISPLAY_FMT),
                who=activity_row.who,
                action=activity_row.action,
                target=activity_row.target,
            ),
            task_id=task.id,
        )

    async def _emit_fragment_revised(self, task: IngestTaskRow, fragment_id: str) -> None:
        """FragmentRevised 领域事件（98 §8——derivatives wiki 重铸订阅；B9 不直调）。"""
        event = make_event(
            "FragmentRevised",
            {
                "task_id": task.id,
                "report_id": task.report_id,
                "lib_id": task.lib_id,
                "fragment_id": fragment_id,
            },
            aggregate=f"kb_fragment:{fragment_id}",
        )
        if self._eventbus is not None:
            await self._eventbus.publish(event)

    async def publish_wiki_version(self, report_id: str, version: int) -> None:
        """B9 例外族公开投影口：derivatives 重建/回滚后回写 wiki_current_version
        （B1 端点 1 `wiki` 字段与 B4 current_version 同源同值——禁他模块直写本表）。"""
        async with self._db.session() as session:
            row = await session.get(ReportRow, report_id)
            if row is not None:
                row.wiki_current_version = version
                row.updated_at = now()
                await session.flush()

    # ---------- 重建任务体（source=片段修正——不重切、重嵌、问题块重生） ----------

    def _spawn_rebuild(self, task_id: str, fragment_id: str) -> None:
        """片段修正重建任务体：进程内登记修正片段（重嵌定位——挂差异登记：
        任务行无 fragment 列，进程内上下文承载，重启丢失不影响正确性）。"""
        self._rebuild_context[task_id] = fragment_id
        task = asyncio.create_task(self._run_rebuild(task_id))
        self._runtime.tasks[task_id] = task
        task.add_done_callback(lambda _t: self._runtime.tasks.pop(task_id, None))

    async def _run_rebuild(self, task_id: str) -> None:
        row = await self._tasks.get(task_id)
        if row is None:
            return
        fragment_id = self._rebuild_context.get(task_id, "")
        snapshot = dict(row.config_snapshot)
        nodes = [
            d.TaskNode(key=n["key"], label=n["label"], state=n["state"], note=n.get("note"))
            for n in row.nodes
        ]
        try:
            for step_index, key in enumerate(d.STEP_KEYS):
                node = nodes[step_index]
                node.state = d.NODE_PROCESS
                node.note = (
                    d.REBUILD_CHUNK_NOTE if key == "chunk"
                    else self._node_note(key, snapshot, "")
                )
                row.current_step = step_index
                row.nodes = [n.as_dict() for n in nodes]
                await self._tasks.save(row)
                await self._run_rebuild_step(key, row, snapshot, fragment_id)
                node.state = d.NODE_FINISH
                row.nodes = [n.as_dict() for n in nodes]
                await self._tasks.save(row)
                if self._step_seconds:
                    await asyncio.sleep(self._step_seconds)
            row.state = "done"
            row.finished_at = now()
            await self._tasks.save(row)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._fail_task(row, nodes, exc)
        finally:
            self._rebuild_context.pop(task_id, None)
            self._runtime.tasks.pop(task_id, None)

    async def _run_rebuild_step(
        self, key: str, row: IngestTaskRow, snapshot: dict[str, Any], fragment_id: str
    ) -> None:
        if key == "parse":
            report = await self._reports.get(row.report_id)
            if report is None or not await self._storage.exists(report.object_key):
                raise RuntimeError("报告原件缺失（数据不一致）")
            return
        if key == "chunk":
            return  # 修正不重切——人工修正后的片段保持（REBUILD_CHUNK_NOTE 同象）
        if key == "embed":
            if not snapshot.get("semantic") or not fragment_id:
                return
            frag = await self._fragments.get(fragment_id)
            if frag is None:
                return
            text = await self._fragment_text(frag)
            vectors = await self._embedder.embed([text])
            await self._fragments.set_embeddings([(fragment_id, vectors[0])])
            return
        if key == "index":
            if snapshot.get("keyword"):
                for frag in await self._fragments.for_report(row.report_id):
                    if not frag.is_parent_only:
                        text = await self._fragment_text(frag)
                        d.tokenize(text)
            return
        # enrich：问题块重生（修正定型后该片段所属问题块重新生成——v0.2 拍板；
        # 重生失败随富化语义不阻塞修正）
        if snapshot.get("add_questions") and fragment_id:
            await self._regen_question_batch(row.report_id, fragment_id, snapshot)

    async def _regen_question_batch(
        self, report_id: str, fragment_id: str, snapshot: dict[str, Any]
    ) -> None:
        """问题块重生：该片段所属批次（每 20 段一批——F37）整批重生成置换。"""
        frags = [
            f for f in await self._fragments.for_report(report_id)
            if f.type == "原文块" and not f.is_parent_only
        ]
        idx = next((i for i, f in enumerate(frags) if f.id == fragment_id), None)
        if idx is None:
            return
        batch_no = idx // d.QUESTIONS_BATCH_SIZE + 1
        section = f"问题块·第{batch_no}批"
        batch = frags[batch_no - 1: batch_no + d.QUESTIONS_BATCH_SIZE - 1]
        report = await self._reports.get(report_id)
        assert report is not None
        texts = [await self._fragment_text(f) for f in batch]
        questions = await self._llm_questions(report.doc, texts)
        await self._replace_derived_chunk(report_id, "问题块", section,
                                          "\n".join(questions), snapshot)

    async def _replace_derived_chunk(
        self, report_id: str, frag_type: str, section: str, text: str,
        snapshot: dict[str, Any],
    ) -> None:
        """派生块置换（问题块重生——记版语义随整卷重跑置换先例，不入片段版本轴）。"""
        seq = await self._fragments.next_fragment_seq()
        frag_id = d.new_fragment_id(seq)
        frag = FragmentRow(
            id=frag_id, report_id=report_id, type=frag_type,
            section=section, hit_text=text, current_version=1, is_parent_only=False,
        )
        version = FragmentVersionRow(
            fragment_id=frag_id, v=1, text=text, context_text=None, note="原始解析"
        )
        async with self._db.session() as session:
            old = (
                (
                    await session.execute(
                        select(FragmentRow).where(
                            FragmentRow.report_id == report_id,
                            FragmentRow.type == frag_type,
                            FragmentRow.section == section,
                        )
                    )
                )
                .scalars()
                .all()
            )
            if old:
                old_ids = [row.id for row in old]
                await session.execute(
                    delete(FragmentVersionRow).where(
                        FragmentVersionRow.fragment_id.in_(old_ids)
                    )
                )
                for row in old:
                    await session.delete(row)
                await session.flush()  # 版本行先删——FK 依赖片段
            session.add(frag)
            await session.flush()
            session.add(version)
            await session.flush()
        if snapshot.get("semantic"):
            vectors = await self._embedder.embed([text])
            await self._fragments.set_embeddings([(frag_id, vectors[0])])

    # ---------- 端点 11：库列表（开关快照＝最近一次入库所用——两态分离） ----------

    async def list_libraries(
        self, graph: str | None = None, keyword: str | None = None
    ) -> list[d.LibraryView]:
        if graph not in (None, "all", "on", "off"):
            raise d.KbParamError(f"graph 越界：{graph}（允许值 all|on|off）")
        needle = (keyword or "").strip().casefold()
        out: list[d.LibraryView] = []
        for lib in await self._libs.all():
            last: dict[str, Any] | None = None
            latest = await self._latest_task_for_lib(lib.id)
            if latest is not None:
                report = await self._reports.get(latest.report_id)
                snapshot = latest.config_snapshot
                last = {
                    "doc": report.doc if report else "",
                    "switches": {
                        key: bool(snapshot.get(key)) for key in d.SWITCH_KEYS
                    },
                }
            if graph == "on" and not (last or {}).get("switches", {}).get("graph"):
                continue
            if graph == "off" and (last or {}).get("switches", {}).get("graph"):
                continue
            if needle and needle not in lib.name.casefold() and (
                last is None or needle not in str(last.get("doc", "")).casefold()
            ):
                continue
            out.append(
                d.LibraryView(
                    id=lib.id,
                    name=lib.name,
                    biz_template=lib.biz_template,
                    status=lib.status,
                    last_ingestion=last,
                    annotations={},  # 「省抽取费」为演示注记，不入真实实现（差异登记）
                )
            )
        return out

    async def _latest_task_for_lib(self, lib_id: str) -> IngestTaskRow | None:
        for row in await self._tasks.all():
            if row.lib_id == lib_id:
                return row
        return None

    # ---------- 端点 12/13：库配置读写（下次入库定型不热切换） ----------

    async def library_config(self, lib_id: str) -> d.LibraryConfigView:
        lib = await self._libs.get(lib_id)
        if lib is None:
            raise d.KbNotFoundError(f"库不存在：{lib_id}")
        row = await self._libs.config_of(lib_id)
        if row is None:
            profile = d.TEMPLATE_CONFIGS.get(lib.biz_template, d.DEFAULT_CONFIG)
            return d.LibraryConfigView(
                id=lib.id, name=lib.name,
                switches={key: bool(profile[key]) for key in d.SWITCH_KEYS},
                mode=str(profile["mode"]),
                add_summary=bool(profile["add_summary"]),
                add_questions=bool(profile["add_questions"]),
                saved_at=None, saved_by=None,
            )
        return d.LibraryConfigView(
            id=lib.id,
            name=lib.name,
            switches={
                "semantic": row.semantic, "keyword": row.keyword,
                "wiki": row.wiki, "graph": row.graph,
            },
            mode=row.mode,
            add_summary=row.add_summary,
            add_questions=row.add_questions,
            saved_at=row.saved_at.strftime(DISPLAY_FMT) if row.saved_at else None,
            saved_by=row.saved_by,
        )

    async def save_library_config(
        self,
        lib_id: str,
        *,
        switches: dict[str, bool],
        mode: str,
        add_summary: bool,
        add_questions: bool,
        status: str | None,
        actor_who: str,
    ) -> d.SaveReceipt:
        """保存待生效配置（下次入库定型、不做运行时热切换——F32 合同语义）；
        v0.3：可选 status 承载停用/启用（同事务记 F62）。"""
        lib = await self._libs.get(lib_id)
        if lib is None:
            raise d.KbNotFoundError(f"库不存在：{lib_id}")
        if mode not in d.MODES:
            raise d.KbParamError(f"mode 越界：{mode}（允许值 {'|'.join(d.MODES)}）")
        if set(switches) != set(d.SWITCH_KEYS):
            raise d.KbParamError(
                f"switches 缺键/多键：{sorted(switches)}（需要 {list(d.SWITCH_KEYS)}）"
            )
        if status is not None and status not in d.LIB_STATUSES:
            raise d.KbParamError(
                f"status 越界：{status}（允许值 {'|'.join(d.LIB_STATUSES)}）"
            )
        activity_target = self._config_target(lib.name, switches, mode,
                                              add_summary, add_questions)
        row, activity_row = await self._libs.save_config_with_activity(
            lib_id,
            switches=switches, mode=mode,
            add_summary=add_summary, add_questions=add_questions,
            actor_who=actor_who,
            activity=(actor_who, "修改库配置", activity_target),
        )
        final_status = lib.status
        if status is not None and status != lib.status:
            if status == "disabled":
                target = f"{lib.name} · 停止接收新入库，已有内容保留可查"
                updated = await self._libs.set_status_with_activity(
                    lib_id, "disabled", activity=(actor_who, "停用库", target)
                )
            else:
                target = f"{lib.name} · 恢复接收新入库"
                updated = await self._libs.set_status_with_activity(
                    lib_id, "active", activity=(actor_who, "启用库", target)
                )
            final_status = updated.status if updated else final_status
        return d.SaveReceipt(
            id=lib_id,
            saved_at=(row.saved_at or now()).strftime(DISPLAY_FMT),
            saved_by=row.saved_by or actor_who,
            status=final_status,
            hint=d.SAVE_HINT,
            activity_row=d.ActivityRow(
                time=activity_row.time.strftime(DISPLAY_FMT),
                who=activity_row.who,
                action=activity_row.action,
                target=activity_row.target,
            ),
        )

    def _config_target(
        self, lib_name: str, switches: dict[str, bool], mode: str,
        add_summary: bool, add_questions: bool,
    ) -> str:
        """活动流 target 按变更内容拼装（端点 13 注记——展示串读侧拼装口径）。"""
        parts = [f"{lib_name}"]
        switch_names = {
            "semantic": "语义", "keyword": "关键词", "wiki": "百科页", "graph": "关系图谱"
        }
        changed = [
            f"{'开启' if on else '关闭'}{switch_names[key]}开关"
            for key, on in switches.items()
        ]
        if changed:
            parts.append("、".join(changed))
        parts.append(f"切段方式：{d.MODE_TEXT[mode].split('——')[0]}（256–1024 字）")
        flags = []
        flags.append("摘要生成" if add_summary else "摘要不生成")
        flags.append("问题生成" if add_questions else "问题不生成")
        parts.append("索引期加法：" + " · ".join(flags))
        parts.append("下次入库生效")
        return " · ".join(parts)

    # ---------- 端点 14：库活动流（F62 只读） ----------

    async def library_activities(self, lib_id: str) -> list[d.ActivityRow]:
        lib = await self._libs.get(lib_id)
        if lib is None:
            raise d.KbNotFoundError(f"库不存在：{lib_id}")
        rows = await self._activities.list_by_lib(lib_id)
        return [
            d.ActivityRow(
                time=row.time.strftime(DISPLAY_FMT),
                who=row.who,
                action=row.action,
                target=row.target,
            )
            for row in rows
        ]

    async def record_activity(
        self, lib_id: str, *, who: str, action: str, target: str,
        session: AsyncSession | None = None,
    ) -> None:
        """B9 例外族写口：跨页留痕（B2 标记/B5 抽取设置）经此同域追加，不直写表。

        session 注入（P1-05b 审查裁决「保存同事务」）：调用方（derivatives
        图支路保存）传入其事务持有的 AsyncSession 时，活动行随该会话 flush，
        与调用方写集同 commit/同 rollback——保存与活动行无丢失窗口；缺省
        自开轻会话（B2 标记等原调用面不变）。B9 边界不破：本方法仍只收
        lib_id/四元组＋会话对象，调用方不见 kb 表模型。
        """
        await self._activities.append(
            lib_id, who=who, action=action, target=target, session=session
        )

    # ---------- B2 切片管理（B2-答案出处.md v0.3——六端点语义） ----------

    def _fragment_hit(self, frag: FragmentRow, versions: list[FragmentVersionRow]) -> str:
        """hit＝命中切片的展示文本（当前版本文本——hit 口径关单：检索/回跳按切块）。"""
        return versions[-1].text if versions else ""

    async def _fragment_item(
        self, frag: FragmentRow, report: ReportRow | None,
        versions: list[FragmentVersionRow],
    ) -> d.FragmentListItem:
        return d.FragmentListItem(
            id=frag.id,
            report_id=frag.report_id,
            report=report.doc if report else "",
            well=frag.well,
            section=frag.section,
            type=frag.type,
            hit=self._fragment_hit(frag, versions),
        )

    async def list_fragments(
        self,
        report_id: str | None,
        *,
        type: str | None = None,
        keyword: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> d.FragmentList:
        """片段台账列表（B2 端点 1 两读法分派）：report_id 携带＝按报告整组取数
        （整表返回）；缺省＝全库扁平清单（page/pageSize 必带缺任一 400）。
        列表只给子块（INV——DTO 无 context 字段）。"""
        ftype = type or "all"
        if ftype != "all" and ftype not in d.FRAGMENT_TYPES:
            raise d.KbParamError(
                f"type 越界：{ftype}（允许值 all|{'|'.join(d.FRAGMENT_TYPES)}）"
            )
        needle = (keyword or "").strip().casefold()

        async def _matches(item: d.FragmentListItem) -> bool:
            # 关键词匹配域＝命中句/井号/章节路径（忽略大小写包含——合同常量）
            if not needle:
                return True
            hay = f"{item.hit}{item.well or ''}{item.section or ''}".casefold()
            return needle in hay

        if report_id is None:
            # 全库扁平清单读法（B3 slice_ref 下拉数据源——跨报告一维清单）
            if page is None or page_size is None or page < 1 or page_size < 1:
                raise d.KbParamError(
                    "全库片段清单必须携带 page/pageSize（缺任一 400）"
                )
            reports = {row.id: row for row in await self._reports.all()}
            frags = await self._fragments.list_children()
            version_map = await self._fragments.versions_of([f.id for f in frags])
            items: list[d.FragmentListItem] = []
            for frag in frags:
                item = await self._fragment_item(
                    frag, reports.get(frag.report_id), version_map.get(frag.id, [])
                )
                if ftype == "all" or frag.type == ftype:
                    if await _matches(item):
                        items.append(item)
            total = len(items)
            start = (page - 1) * page_size
            return d.FragmentList(
                items=items[start : start + page_size],
                total=total,
                page=page,
                page_size=page_size,
            )

        report = await self._reports.get(report_id)
        if report is None:
            raise d.KbNotFoundError(f"报告不存在：{report_id}")
        frags = [
            f for f in await self._fragments.for_report(report_id) if not f.is_parent_only
        ]
        version_map = await self._fragments.versions_of([f.id for f in frags])
        out: list[d.FragmentListItem] = []
        for frag in frags:
            if ftype != "all" and frag.type != ftype:
                continue
            item = await self._fragment_item(frag, report, version_map.get(frag.id, []))
            if await _matches(item):
                out.append(item)
        return d.FragmentList(items=out, total=len(out))

    async def dedup_corpus(self) -> list[str]:
        """知识库面向量语料（P1-06 B3 端点 12 三面去重——kb 公开缝供出，
        faq 不直查 kb 表）：已向量化子块的命中句清单（faq 侧另行向量化比对）。"""
        frags = await self._fragments.list_children()
        return [
            frag.hit_text
            for frag in frags
            if frag.embedding is not None and frag.hit_text
        ]

    # ---------- 运行时读（chat 消费，不经 HTTP——P1-08a 六路装配报告索引路） ----------

    async def index_search(self, question: str, *, top_k: int = 5) -> list[d.IndexHit]:
        """报告索引检索读面（98 §3.4 卡运行时读缝——chat 六路装配消费）。

        两腿＝检索瀑布 S4 两路（F58）：
        - 向量腿：问题向量化 × 已向量化子块余弦（EmbeddingBackend 缝——P1-04
          收尾裁决①「P1-08b 用现有 EmbeddingBackend 缝」）；
        - 关键词腿：trigram 子串覆盖率（P1-04 裁决②——pg_trgm GIN 索引随 P1-10
          上，本读面查询语义不变）。
        同片段两腿取高分腿（同池去重），按分倒序 top_k。
        """
        frags = await self._fragments.list_children()
        if not frags or not question.strip():
            return []
        reports = {row.id: row for row in await self._reports.all()}
        probe = (await self._embedder.embed([question.strip()]))[0]
        best: dict[str, d.IndexHit] = {}
        for frag in frags:
            text = frag.hit_text or ""
            score = 0.0
            leg = ""
            if frag.embedding is not None:
                vector_score = d.cosine_similarity(probe, frag.embedding)
                if vector_score > score:
                    score, leg = vector_score, "vector"
            if text:
                keyword_score = d.trigram_coverage(question, text)
                if keyword_score > score:
                    score, leg = keyword_score, "keyword"
            if score <= 0.0 or leg == "":
                continue
            hit = d.IndexHit(
                fragment_id=frag.id,
                report_id=frag.report_id,
                report=reports[frag.report_id].doc if frag.report_id in reports else "",
                section=frag.section,
                snippet=text[:80],
                score=score,
                leg=leg,
                text=text[:500],
            )
            current = best.get(frag.id)
            if current is None or hit.score > current.score:
                best[frag.id] = hit
        return sorted(best.values(), key=lambda h: h.score, reverse=True)[:top_k]

    async def index_search_dual(
        self, question: str, *, vector_top_k: int, keyword_top_k: int
    ) -> tuple[list[d.IndexHit], list[d.IndexHit]]:
        """双路召回读面（检索瀑布 S4——P1-08b 检索链消费）：向量腿与关键词腿
        并发（asyncio.gather），各自按分倒序取 topK（D2 params.semantic_top_k /
        keyword_top_k 驱动），合并策略由消费方按配置执行（rrf_rank/concat）。
        """
        frags = await self._fragments.list_children()
        if not frags or not question.strip():
            return [], []
        reports = {row.id: row for row in await self._reports.all()}

        def _hit(frag: FragmentRow, score: float, leg: str) -> d.IndexHit:
            text = frag.hit_text or ""
            return d.IndexHit(
                fragment_id=frag.id,
                report_id=frag.report_id,
                report=reports[frag.report_id].doc if frag.report_id in reports else "",
                section=frag.section,
                snippet=text[:80],
                score=score,
                leg=leg,
                text=text[:500],
            )

        async def vector_leg() -> list[d.IndexHit]:
            probe = (await self._embedder.embed([question.strip()]))[0]
            scored = [
                (frag, d.cosine_similarity(probe, frag.embedding))
                for frag in frags
                if frag.embedding is not None
            ]
            scored = [pair for pair in scored if pair[1] > 0.0]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            return [_hit(frag, score, "vector") for frag, score in scored[:vector_top_k]]

        async def keyword_leg() -> list[d.IndexHit]:
            scored = [
                (frag, d.trigram_coverage(question, frag.hit_text or ""))
                for frag in frags
                if frag.hit_text
            ]
            scored = [pair for pair in scored if pair[1] > 0.0]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            return [_hit(frag, score, "keyword") for frag, score in scored[:keyword_top_k]]

        vector_hits, keyword_hits = await asyncio.gather(vector_leg(), keyword_leg())
        return vector_hits, keyword_hits

    async def fragment_anchor(self, fragment_id: str) -> d.FragmentAnchor | None:
        """片段锚校验（P1-08b citation fail-closed 读面——chat 消费）：片段必须
        真实存在且对外可寻址（父块不对外寻址——F30），返回其报告归属。"""
        frag = await self._fragments.get(fragment_id)
        if frag is None or frag.is_parent_only:
            return None
        report = await self._reports.get(frag.report_id)
        return d.FragmentAnchor(
            fragment_id=frag.id,
            report_id=frag.report_id,
            report=report.doc if report is not None else "",
            section=frag.section,
        )

    async def fragment_context(self, fragment_id: str) -> d.FragmentContext:
        """父块回捞（B2 端点 2——按 type 分派语义）：原文块/图片说明块/图片文字块
        ＝父块正文（F30 与 F36 回捞会师；mixed 子块经版本行父块锚到达）；摘要块/
        问题块＝产物说明行（无父块的唯一例外，如实照抄）；无父块锚的原文块＝
        本块全文（context ⊇ hit 兜底，不虚构父段）。"""
        frag = await self._fragments.get(fragment_id)
        if frag is None or frag.is_parent_only:
            # 父块不对外寻址（F30）——不存在与不可寻址同象 404
            raise d.KbNotFoundError(f"片段不存在：{fragment_id}")
        versions = (await self._fragments.versions_of([fragment_id])).get(fragment_id, [])
        hit = self._fragment_hit(frag, versions)
        if frag.type == "摘要块":
            context = d.SUMMARY_CONTEXT_NOTE
        elif frag.type == "问题块":
            context = d.QUESTION_CONTEXT_NOTE
        else:
            parent_anchor = versions[-1].context_text if versions else None
            parent_text: str | None = None
            if parent_anchor:
                parent = await self._fragments.get(parent_anchor)
                if parent is not None:
                    pvers = (await self._fragments.versions_of([parent_anchor])).get(
                        parent_anchor, []
                    )
                    parent_text = self._fragment_hit(parent, pvers) or None
            context = parent_text if parent_text else hit  # context ⊇ hit 兜底
        return d.FragmentContext(id=frag.id, type=frag.type, hit=hit, context=context)

    async def _issue_label(self, frag: FragmentRow, report: ReportRow | None) -> str:
        """fragment_label（端点 3/4 同源同构）：{报告名} · {章节路径}。"""
        return f"{report.doc if report else ''} · {frag.section or '正文'}"

    async def _issue_view(
        self, row: IssueReportRow, *, hint: str | None = None
    ) -> d.IssueReportView:
        frag = await self._fragments.get(row.fragment_id)
        report = await self._reports.get(frag.report_id) if frag else None
        return d.IssueReportView(
            id=row.id,
            fragment_id=row.fragment_id,
            report_id=frag.report_id if frag else "",
            fragment_label=await self._issue_label(frag, report) if frag else "",
            state=row.state,
            marked_by=row.marked_by,
            marked_at=row.marked_at.strftime(DISPLAY_FMT) if row.marked_at else "",
            reject_reason=row.reject_reason,
            hint=hint,
        )

    async def report_fragment_issue(
        self, fragment_id: str, actor_who: str
    ) -> d.IssueReportView:
        """标记问题片段（B2 端点 3——只标记不直改）：进质检复核队列＋同事务记
        F62「标记问题片段」（B1 挂账收口批 action 值域）；待质检复核态重复 409；
        已驳回态重新标记＝旧驳回单转已销记＋新单入队（队列零悬挂）。"""
        frag = await self._fragments.get(fragment_id)
        if frag is None or frag.is_parent_only:
            raise d.KbNotFoundError(f"片段不存在：{fragment_id}")
        report = await self._reports.get(frag.report_id)
        if report is None:
            raise d.KbNotFoundError(f"报告不存在：{frag.report_id}")
        label = await self._issue_label(frag, report)
        row = await self._issues.mark_fragment(
            fragment_id,
            marked_by=actor_who,
            lib_id=report.lib_id,
            activity=(actor_who, d.MARK_ACTIVITY_ACTION, label),
        )
        await self._emit_fragment_marked(row, frag)
        return await self._issue_view(row, hint=d.MARK_HINT)

    async def _emit_fragment_marked(
        self, row: IssueReportRow, frag: FragmentRow
    ) -> None:
        """FragmentMarked 领域事件（98 §8——域内消费即 IssueReport 入队；B9 缝外零订阅）。"""
        event = make_event(
            "FragmentMarked",
            {"issue_id": row.id, "fragment_id": frag.id, "report_id": frag.report_id},
            aggregate=f"kb_fragment:{frag.id}",
        )
        if self._eventbus is not None:
            await self._eventbus.publish(event)

    async def list_issue_reports(self, state: str | None) -> list[d.IssueReportView]:
        """质检复核队列列表（B2 端点 4）：state=all|待质检复核|已驳回——终态
        默认不出列、state=all 亦只出两在途态（队列只管未决单）；标记时间倒序。"""
        if state in (None, "all"):
            states = list(d.ISSUE_OPEN_STATES)
        elif state in d.ISSUE_OPEN_STATES:
            states = [state]
        else:
            raise d.KbParamError(
                f"state 越界：{state}（允许值 all|{'|'.join(d.ISSUE_OPEN_STATES)}；"
                "终态查询归后续批按需增设）"
            )
        rows = await self._issues.list_by_states(states)
        return [await self._issue_view(row) for row in rows]

    async def review_issue_report(
        self, issue_id: str, action: str, reason: str | None, actor_who: str
    ) -> d.IssueReportView:
        """复核确认/驳回（B2 端点 5）：仅待质检复核态可复核（重复 409）；驳回
        必带理由（缺 400——「驳回须写理由」A3 分治同款）回标记人。"""
        row = await self._issues.get(issue_id)
        if row is None:
            raise d.KbNotFoundError(f"标记单不存在：{issue_id}")
        if action not in ("confirm", "reject"):
            raise d.KbParamError(f"action 越界：{action}（允许值 confirm|reject）")
        if row.state != "待质检复核":
            raise d.KbConflictError(
                f"仅「待质检复核」态可复核（当前 {row.state}）", code="kb_issue_state"
            )
        at = now()
        if action == "confirm":
            # 确认转修正流：修正动作＝B1 端点 4（页面引导跳修正——确认单即落终态）
            row.state = "已修正"
        else:
            text = (reason or "").strip()
            if not text:
                raise d.KbParamError(
                    "驳回必须写明理由（空理由 400）",
                    code="kb_issue_reject_reason_required",
                )
            row.state = "已驳回"
            row.reject_reason = text
        row.reviewed_by = actor_who
        row.reviewed_at = at
        await self._issues.save(row)
        return await self._issue_view(row)

    async def close_issue_report(self, issue_id: str, actor_who: str) -> d.IssueReportView:
        """驳回后销记（B2 端点 6）：仅已驳回态可销记（其他态 409）——队列零悬挂
        兜底；终态「已销记」，响应展示串「已销记 · 不修正」（合同端点 6 示例）。"""
        row = await self._issues.get(issue_id)
        if row is None:
            raise d.KbNotFoundError(f"标记单不存在：{issue_id}")
        if row.state != "已驳回":
            raise d.KbConflictError(
                f"仅「已驳回」态可销记（当前 {row.state}）", code="kb_issue_state"
            )
        row.state = "已销记"
        await self._issues.save(row)
        view = await self._issue_view(row)
        return d.IssueReportView(
            id=view.id,
            fragment_id=view.fragment_id,
            report_id=view.report_id,
            fragment_label=view.fragment_label,
            state="已销记 · 不修正",
            marked_by=view.marked_by,
            marked_at=view.marked_at,
            reject_reason=view.reject_reason,
            hint=view.hint,
        )

    # ---------- stuck 收口（00 §5.2-6：超时无进展后台巡检） ----------

    async def sweep_stuck(self) -> int:
        """巡检收口：running 且 updated_at 早于阈值 → stuck（幂等；启动巡检＋周期巡检共用）。"""
        closed = await self._tasks.mark_stale_stuck(
            before=now() - timedelta(seconds=d.STUCK_SWEEP_SECONDS),
            summary="长时间无进展，已自动转「疑似卡住」——可重试（内含停止语义）",
        )
        if closed:
            LOGGER.warning("kb stuck 巡检：%d 条 running 任务收口 stuck", closed)
        return closed

    # ---------- 管线任务体（五步——异步编排） ----------

    def _spawn_pipeline(self, task_id: str) -> None:
        task = asyncio.create_task(self._run_pipeline(task_id))
        self._runtime.tasks[task_id] = task
        task.add_done_callback(lambda _t: self._runtime.tasks.pop(task_id, None))

    def _node_note(self, key: str, snapshot: dict[str, Any], lib_name: str) -> str | None:
        if key == "parse":
            return d.PARSE_NOTE
        if key == "chunk":
            return d.chunk_note(str(snapshot["mode"]))
        if key == "embed":
            return d.EMBED_NOTE
        if key == "index":
            return d.index_note(lib_name, snapshot)
        return None  # 步 5 无说明行（产物卡即说明——页面 taskStepRows 仅四行）

    async def _run_pipeline(self, task_id: str) -> None:
        row = await self._tasks.get(task_id)
        if row is None:
            return
        lib = await self._libs.get(row.lib_id)
        lib_name = lib.name if lib else ""
        snapshot = dict(row.config_snapshot)
        nodes = [
            d.TaskNode(key=n["key"], label=n["label"], state=n["state"], note=n.get("note"))
            for n in row.nodes
        ]
        try:
            for step_index, key in enumerate(d.STEP_KEYS):
                node = nodes[step_index]
                node.state = d.NODE_PROCESS
                node.note = self._node_note(key, snapshot, lib_name)
                row.current_step = step_index
                row.nodes = [n.as_dict() for n in nodes]
                await self._tasks.save(row)
                await self._run_step(key, row, snapshot, nodes, step_index)
                node.state = d.NODE_FINISH
                row.nodes = [n.as_dict() for n in nodes]
                row.current_step = step_index
                await self._tasks.save(row)
                if self._step_seconds:
                    await asyncio.sleep(self._step_seconds)
            row.state = "done"
            row.finished_at = now()
            report = await self._reports.get(row.report_id)
            await self._tasks.finish_with_activity(
                row,
                activity=(
                    "系统 · 知识管线",
                    "入库完成",
                    f"{report.doc if report else ''} · 五步全过，索引已按库配置写入",
                ),
            )
            await self._emit_ingest_completed(row)
        except asyncio.CancelledError:  # stuck 重试内含停止——旧执行被取消
            raise
        except Exception as exc:
            await self._fail_task(row, nodes, exc)
        finally:
            self._runtime.tasks.pop(task_id, None)

    async def _fail_task(
        self, row: IngestTaskRow, nodes: list[d.TaskNode], exc: Exception
    ) -> None:
        LOGGER.exception("kb 入库任务失败 task=%s", row.id)
        stop_index = max(int(row.current_step), 0)
        stop_key = d.STEP_KEYS[stop_index]
        reason = str(exc) or exc.__class__.__name__
        for node in nodes:
            if node.state == d.NODE_PROCESS:
                node.state = d.NODE_ERROR
                node.note = d.FAILURE_TEMPLATE.format(
                    stop_at=d.STEP_SHORT_NAMES[stop_key], reason=reason
                )
        row.state = "failed"
        row.stop_at = d.STEP_SHORT_NAMES[stop_key]
        row.current_step = stop_index  # failed 的 current_step＝stop_at 步序号（更正项⑪）
        row.reason = reason
        row.nodes = [n.as_dict() for n in nodes]
        row.finished_at = now()
        report = await self._reports.get(row.report_id)
        failed_target = (
            f"{report.doc if report else ''} · "
            f"停在「{d.STEP_SHORT_NAMES[stop_key]}」：{reason}"
        )
        await self._tasks.finish_with_activity(
            row,
            activity=("系统 · 知识管线", "入库失败", failed_target),
        )

    async def _run_step(
        self,
        key: str,
        row: IngestTaskRow,
        snapshot: dict[str, Any],
        nodes: list[d.TaskNode],
        step_index: int,
    ) -> str:
        """执行一步；返回文本全文（parse 产出，enrich 复用）。失败抛异常（→failed）。"""
        if key == "parse":
            report = await self._reports.get(row.report_id)
            if report is None:
                raise RuntimeError("报告行缺失（数据不一致）")
            data = await self._storage.get_bytes(report.object_key)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise RuntimeError(
                    "暂只支持文本类报告解析（PDF/图片解析随后续批落地）"
                ) from exc
            if not text.strip():
                raise RuntimeError("未读出正文文字——文件内容为空")
            return text
        if key == "chunk":
            report = await self._reports.get(row.report_id)
            assert report is not None
            data = await self._storage.get_bytes(report.object_key)
            text = data.decode("utf-8", errors="replace")
            pieces = d.chunk_text(text, str(snapshot["mode"]))
            if not pieces:
                raise RuntimeError("切段结果为空——报告无可索引正文")
            await self._persist_chunks(row.report_id, pieces)
            return text
        if key == "embed":
            if not snapshot.get("semantic"):
                return ""  # 语义支路关——直接跳过、不跑不花钱（F32 分发枢纽）
            await self._embed_report(row.report_id)
            return ""
        if key == "index":
            if snapshot.get("keyword"):
                # 倒排半边：确定性分词（BM25 落法悬置 99 §6-5——本票不落第二份存储，
                # 分词口径随 99 收口批对齐；语义半边向量已在 embed 步写入 pgvector）。
                frags = await self._fragments.for_report(row.report_id)
                for frag in frags:
                    if not frag.is_parent_only:
                        text = await self._fragment_text(frag)
                        d.tokenize(text)
            return ""
        # enrich（索引期加法——两复选随快照；子任务失败不阻塞整卷）
        report = await self._reports.get(row.report_id)
        assert report is not None
        data = await self._storage.get_bytes(report.object_key)
        text = data.decode("utf-8", errors="replace")
        await self._enrich(row, report, snapshot, text)
        return text

    async def _persist_chunks(self, report_id: str, pieces: list[tuple[str, str]]) -> None:
        seq = await self._fragments.next_fragment_seq()
        rows: list[FragmentRow] = []
        versions: list[FragmentVersionRow] = []
        parent_ids: dict[str, str] = {}
        for section, piece in pieces:
            is_parent = section.startswith("父块·")
            frag_id = d.new_fragment_id(seq)
            seq += 1
            rows.append(
                FragmentRow(
                    id=frag_id,
                    report_id=report_id,
                    type="原文块",
                    section=section,
                    hit_text=piece,
                    current_version=1,
                    is_parent_only=is_parent,
                )
            )
            if is_parent:
                parent_ids[section] = frag_id
                versions.append(
                    FragmentVersionRow(
                        fragment_id=frag_id, v=1, text=piece,
                        context_text=None, note="原始解析",
                    )
                )
            else:
                parent_anchor = None
                if section in parent_ids:
                    parent_anchor = parent_ids[section]
                versions.append(
                    FragmentVersionRow(
                        fragment_id=frag_id, v=1, text=piece,
                        context_text=parent_anchor, note="原始解析",
                    )
                )
        await self._fragments.replace_report_fragments(report_id, rows, versions)

    async def _embed_report(self, report_id: str) -> None:
        frags = [f for f in await self._fragments.for_report(report_id) if not f.is_parent_only]
        if not frags:
            return
        texts = [await self._fragment_text(f) for f in frags]
        vectors = await self._embedder.embed(texts)
        await self._fragments.set_embeddings(
            list(zip([f.id for f in frags], vectors, strict=True))
        )

    async def _enrich(
        self, row: IngestTaskRow, report: ReportRow,
        snapshot: dict[str, Any], text: str,
    ) -> None:
        """索引期加法（F37）：摘要 ×1＋每 20 段问题一批——chunk 入索引带类型标。"""
        seq = await self._fragments.next_fragment_seq()
        if snapshot.get("add_summary", True):
            try:
                summary = await self._llm_summary(report.doc, text)
                await self._append_derived_chunk(
                    report.id, seq, "摘要块", "全文档摘要", summary, snapshot
                )
                seq += 1
            except Exception as exc:
                # 富化子任务失败不阻塞整卷（F32）——记日志不置 failed
                LOGGER.warning("kb 摘要子任务失败 task=%s：%s", row.id, exc)
        if snapshot.get("add_questions", True):
            frags = [
                f for f in await self._fragments.for_report(report.id)
                if f.type == "原文块" and not f.is_parent_only
            ]
            batch_no = 0
            for start in range(0, len(frags), d.QUESTIONS_BATCH_SIZE):
                batch = frags[start : start + d.QUESTIONS_BATCH_SIZE]
                texts = [await self._fragment_text(f) for f in batch]
                batch_no += 1
                try:
                    questions = await self._llm_questions(report.doc, texts)
                    section = f"问题块·第{batch_no}批"
                    await self._append_derived_chunk(
                        report.id, seq, "问题块", section,
                        "\n".join(questions), snapshot,
                    )
                    seq += 1
                except Exception as exc:
                    LOGGER.warning("kb 问题子任务失败 task=%s：%s", row.id, exc)

    async def _append_derived_chunk(
        self, report_id: str, seq: int, frag_type: str, section: str, text: str,
        snapshot: dict[str, Any],
    ) -> None:
        frag_id = d.new_fragment_id(seq)
        frag = FragmentRow(
            id=frag_id, report_id=report_id, type=frag_type,
            section=section, current_version=1, is_parent_only=False,
        )
        version = FragmentVersionRow(
            fragment_id=frag_id, v=1, text=text, context_text=None, note="原始解析"
        )
        # 追加语义（不置换既有片段）；片段行先落——版本行 FK 依赖片段
        async with self._db.session() as session:
            session.add(frag)
            await session.flush()
            session.add(version)
            await session.flush()
        if snapshot.get("semantic"):
            vectors = await self._embedder.embed([text])
            await self._fragments.set_embeddings([(frag_id, vectors[0])])

    async def _llm_summary(self, doc: str, text: str) -> str:
        content = text[:6000]
        completion = await self._gateway.complete(
            INGEST_ALIAS,
            [{
                "role": "user",
                "content": f"请为报告{doc}生成一段 120 字以内的中文全文档摘要，"
                           "只输出摘要正文，不要客套：\n\n" + content,
            }],
            caller="kb.ingest.summary",
        )
        return completion.content.strip()

    async def _llm_questions(self, doc: str, chunk_texts: list[str]) -> list[str]:
        joined = "\n\n".join(chunk_texts)[:6000]
        completion = await self._gateway.complete(
            INGEST_ALIAS,
            [{
                "role": "user",
                "content": f"根据报告{doc}的以下片段，生成 10 个「可能被问的问题」。"
                           "要求：每行一个问题、以？结尾、不要编号、不要多余说明：\n\n" + joined,
            }],
            caller="kb.ingest.questions",
        )
        questions = [
            line.strip().lstrip("0123456789.、） ")
            for line in completion.content.strip().splitlines()
            if line.strip()
        ]
        return questions or [completion.content.strip()]

    async def _emit_ingest_completed(self, row: IngestTaskRow) -> None:
        """IngestCompleted 领域事件（98 §8——derivatives 订阅的缝；B9 不直调）。"""
        report = await self._reports.get(row.report_id)
        event = make_event(
            "IngestCompleted",
            {
                "task_id": row.id,
                "report_id": row.report_id,
                "lib_id": row.lib_id,
                "doc": report.doc if report else "",
                "source": row.source,
                "config_snapshot": dict(row.config_snapshot),
                "extract_snapshot": dict(row.extract_snapshot)
                if row.extract_snapshot
                else None,
            },
            aggregate=f"kb_report:{row.report_id}",
        )
        if self._eventbus is not None:
            await self._eventbus.publish(event)

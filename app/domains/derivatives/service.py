"""domains.derivatives.service —— 派生物域服务：wiki 支路编排（生成/重铸/读面/回滚）。

公开面照 98 §3.5 derivatives 卡＋B4 合同四端点：
- 事件订阅（B9——kb 不直调 derivatives，派生物只经事件触发）：
  `on_ingest_completed`（入库/重跑定型→wiki 生成/重建）；
  `on_fragment_revised`（片段修正→重铸队列→版本+1 来源「自动重建」；
  失败不阻塞修正——记 B1 活动流，可手动重跑）。
- 生成支路（PRD F50 工序）：块拼回全文（相邻重叠去重）→图片块连图注回读
  →32K 截断→LLM 模板重写（模板＝提示词约束按库业务模板投影，产出自由
  markdown 零固定节；截断纪律＝最多续写 3 轮、未完放弃本次写入不落半页）
  →claims 锚校验（fail-closed）→台账挂接（台账无账不挂）→落版本快照。
- 读面（B4 端点 1/2/3）：目录/全文 ?version=N/版本列表；写面（端点 4）：
  回滚＝追加「回滚」来源新版本、指针前进、防呆 409。

选型说明（票面「asyncio 任务族或管线第六步」）：**事件订阅＋asyncio 任务族**，
不进五步管线——①五步节点名为 B1 合同冻结值，wiki 不占步位；②B9 边界：
wiki 是 derivatives 聚合，kb 只发事件；③生成失败不阻塞入库任务（富化失败
不阻塞整卷先例）。重铸队列＝进程内按报告去重的任务族（同报告重铸在途时
合并为完成后补跑一次——量级演示级，跨进程队列随接线批）。

边界：B9（→kb 仅报告读面/record_activity/投影回写公开口）、B5（sem_* 只经
semantics 读接口）、B6（LLM 只走 gateway.complete）、B12（api 层审计，域不
反向依赖 security）、B14（时间只经 infra.clock）。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.domains.derivatives import domain as d
from app.domains.derivatives.store import (
    WikiPageRow,
    WikiPageVersionRow,
    WikiStore,
)
from app.infra.clock import DISPLAY_FMT, now
from app.infra.eventbus import DomainEvent

LOGGER = logging.getLogger("domains.derivatives")

# LLM 出口（B6）：百科生成＝起草/生成族——petro-main（P1-00 拍板基线）。
WIKI_ALIAS = "petro-main"
WIKI_CALLER = "wiki.gen"

# 证据块类型（拼回素材）：原文块＋图片块连图注回读；摘要块/问题块为索引期
# 加法产物（重写≠检索的素材边界——不进拼回稿）。
EVIDENCE_TYPES: tuple[str, ...] = ("原文块", "图片说明块", "图片文字块")
_EXCERPT_CHARS = 200


class Completer(Protocol):
    """LLM 出口 seam（生产装配＝GatewayService——B6 唯一出口；测试注桩）。"""

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any: ...


class KbFacade(Protocol):
    """kb 公开面（B9 例外族：报告读面＋活动流写口＋wiki 版号投影回写）。"""

    async def report_detail(self, report_id: str) -> Any: ...

    async def record_activity(
        self, lib_id: str, *, who: str, action: str, target: str
    ) -> None: ...

    async def publish_wiki_version(self, report_id: str, version: int) -> None: ...

    async def list_libraries(
        self, graph: str | None = None, keyword: str | None = None
    ) -> list[Any]: ...


class SemanticsFacade(Protocol):
    """semantics 读接口（B5：下游运行时读走读接口不直查 sem_*）。"""

    async def list_terms(self, **kw: Any) -> Any: ...

    async def list_metrics(self, **kw: Any) -> Any: ...


@dataclass
class _RecastRuntime:
    """重铸队列（进程内）：同报告在途合并＋完成后补跑一次。"""

    tasks: dict[str, asyncio.Task[None]]
    pending: set[str]


class DerivativesService:
    """derivatives 域服务（wiki 支路；图支路归 P1-05）。"""

    def __init__(
        self,
        db: Any,
        gateway: Completer,
        kb: KbFacade,
        semantics: SemanticsFacade | None = None,
    ) -> None:
        self._gateway = gateway
        self._kb = kb
        self._semantics = semantics
        self._store = WikiStore(db)
        self._recasts = _RecastRuntime(tasks={}, pending=set())

    # ---------- 事件订阅（main.py lifespan 装配；B9 缝） ----------

    async def on_ingest_completed(self, event: DomainEvent) -> None:
        """IngestCompleted→wiki 支路（开关关→不生成；开关开→异步生成/重建）。"""
        payload = event.payload
        if not payload.get("config_snapshot", {}).get("wiki"):
            return  # 开关关→不生成（B4 生产/消费边界：目录不出现、直调 404）
        await self._spawn_generation(
            str(payload["report_id"]),
            str(payload["lib_id"]),
            task_no=str(payload["task_id"]),
            desc=d.DESC_REINGEST if payload.get("source") == "重跑定型" else d.DESC_FIRST,
        )

    async def on_fragment_revised(self, event: DomainEvent) -> None:
        """FragmentRevised→该报告 wiki 页进重铸队列（复用生成管线；失败不阻塞）。"""
        payload = event.payload
        report_id = str(payload["report_id"])
        self._enqueue_recast(report_id, str(payload["lib_id"]),
                             str(payload.get("task_id") or ""))

    def _enqueue_recast(self, report_id: str, lib_id: str, task_no: str) -> None:
        """重铸队列：在途合并（完成后补跑一次），量级演示级。"""
        running = self._recasts.tasks.get(report_id)
        if running is not None and not running.done():
            self._recasts.pending.add(report_id)
            return
        self._spawn_recast(report_id, lib_id, task_no)

    def _spawn_recast(self, report_id: str, lib_id: str, task_no: str) -> None:
        async def _run() -> None:
            try:
                await self._generate(
                    report_id, lib_id, task_no=task_no or None, desc=d.DESC_RECAST,
                    failure_activity=True,
                )
            finally:
                self._recasts.tasks.pop(report_id, None)
                if report_id in self._recasts.pending:
                    self._recasts.pending.discard(report_id)
                    self._spawn_recast(report_id, lib_id, task_no)

        self._recasts.tasks[report_id] = asyncio.create_task(_run())

    async def _spawn_generation(
        self, report_id: str, lib_id: str, *, task_no: str, desc: str
    ) -> None:
        try:
            await self._generate(report_id, lib_id, task_no=task_no, desc=desc)
        except Exception:  # 生成失败不阻塞入库任务（任务体已 done——只记日志）
            LOGGER.exception("wiki 生成失败 report=%s task=%s", report_id, task_no)

    # ---------- 生成支路（F50 工序） ----------

    async def _generate(
        self,
        report_id: str,
        lib_id: str,
        *,
        task_no: str | None,
        desc: str,
        failure_activity: bool = False,
    ) -> None:
        """拼回→截断→LLM 重写→锚校验→挂接→落版本；失败可记活动流。"""
        try:
            detail = await self._kb.report_detail(report_id)
            evidence = [
                (f.type, f.path, f.text)
                for f in detail.fragments
                if f.type in EVIDENCE_TYPES and f.text
            ]
            if not evidence:
                LOGGER.warning("wiki 生成跳过：无可拼回素材 report=%s", report_id)
                return
            valid_ids = {f.id for f in detail.fragments}
            full = d.reconstruct_content(evidence)
            source_text = d.truncate_for_wiki(full)
            content = await self._llm_rewrite(detail.doc, lib_id, detail.fragments,
                                              source_text)
            content = d.strip_sentinel(content)
            content, claims = d.extract_claims(content, valid_ids, claim_id_prefix="c")
            content, glossary = await self._attach_glossary(content)
            await self._persist_version(
                report_id=report_id, lib_id=lib_id, title=detail.doc,
                content=content, claims=claims, glossary=glossary,
                source=d.SOURCE_AUTO, desc=desc, operator=d.OPERATOR_SYSTEM,
                task_no=task_no,
            )
        except Exception as exc:
            LOGGER.exception("wiki 生成失败 report=%s", report_id)
            if failure_activity:
                # 重铸失败不阻塞修正（富化失败不阻塞整卷先例）——记 B1 活动流；
                # 半页不落库：版本不追加、当前版不动，可经 B1 端点 10 重跑触发。
                try:
                    await self._kb.record_activity(
                        lib_id, who=d.OPERATOR_SYSTEM, action="百科重铸失败",
                        target=f"报告 {report_id} · 百科页重铸未完成：{exc}",
                    )
                except Exception:
                    LOGGER.exception("wiki 重铸失败留痕失败 report=%s", report_id)
            return

    async def _llm_rewrite(
        self, doc: str, lib_id: str, fragments: list[Any], source_text: str
    ) -> str:
        """LLM 模板重写（32K 稿；最多续写 3 轮、未完放弃本次写入不落半页）。"""
        biz_template = await self._lib_template(lib_id)
        evidence = [f for f in fragments if f.type in EVIDENCE_TYPES and f.text]
        fragment_lines = [
            (f.id, f.path, f.type, f.text[:_EXCERPT_CHARS]) for f in evidence
        ]
        messages = [{
            "role": "user",
            "content": d.build_wiki_prompt(doc, biz_template, fragment_lines, source_text),
        }]
        completion = await self._gateway.complete(
            WIKI_ALIAS, messages, caller=WIKI_CALLER
        )
        content: str = completion.content
        rounds = 0
        while d.looks_unfinished(content) and rounds < d.WIKI_CONTINUE_ROUNDS:
            rounds += 1
            completion = await self._gateway.complete(
                WIKI_ALIAS,
                [{"role": "user", "content": d.build_continue_prompt(content)}],
                caller=WIKI_CALLER,
            )
            content = f"{content.rstrip()}\n{completion.content}"
        if d.looks_unfinished(content):
            # 未完放弃本次写入（F50 票 104）——半页不落库。
            raise RuntimeError(
                f"百科页生成未完（续写 {rounds} 轮仍未收束）——本次写入已放弃"
            )
        return content

    async def _lib_template(self, lib_id: str) -> str:
        """库业务模板投影（WikiConfig 提示词取向落地面——挂差异登记）。"""
        try:
            libs = await self._kb.list_libraries()
        except Exception:
            return "blank"
        for lib in libs:
            if lib.id == lib_id:
                return str(lib.biz_template)
        return "blank"

    async def _attach_glossary(self, content: str) -> tuple[str, list[dict[str, Any]]]:
        """台账挂接（词表＝C1 台账名册＋别名：术语名＋指标槽位纯名；无账不挂）。"""
        if self._semantics is None:
            return content, []
        registry = d.GlossaryRegistry()
        try:
            terms = await self._semantics.list_terms(page=1, page_size=1000)
            for row in terms.items:
                card = {
                    "type": row.type,
                    "def": row.def_,
                    "status": row.status,
                    "owner": row.owner,
                }
                registry.words[row.term] = d.GlossaryCard(kind="term", ref_id=row.id,
                                                          card=card)
            metrics = await self._semantics.list_metrics(page=1, page_size=1000)
            for row in metrics.items:
                card = {
                    "slot_name": row.slot_name,
                    "def": row.def_,
                    "grain": row.grain,
                    "unit": row.unit,
                    "status": list(row.status),
                    "owner": row.owner,
                    "source": row.source,
                }
                registry.words[row.slot_name] = d.GlossaryCard(kind="metric",
                                                               ref_id=row.id,
                                                               card=card)
        except Exception as exc:  # 台账读面不可用→不挂（无账不挂的降级面）
            LOGGER.warning("wiki 台账挂接词表不可用，本次生成不挂接：%s", exc)
            return content, []
        return d.linkify_glossary(content, registry)

    async def _persist_version(
        self,
        *,
        report_id: str,
        lib_id: str,
        title: str,
        content: str,
        claims: list[d.ClaimRow],
        glossary: list[dict[str, Any]],
        source: str,
        desc: str,
        operator: str | None,
        task_no: str | None,
    ) -> WikiPageVersionRow:
        """落版本快照（版本只追加）＋wiki 版号投影回写（B9 例外族公开口）。"""
        claims_payload = [
            {"claim_id": c.claim_id, "text": c.text,
             "evidence_chunk_ids": list(c.evidence_chunk_ids)}
            for c in claims
        ]
        page = await self._store.page_by_report(report_id)
        if page is None:
            page = WikiPageRow(
                id=d.page_slug_for_report(report_id),
                title=title,
                digest=d.derive_digest(content),
                lib_id=lib_id,
                source_report_id=report_id,
                current_version=1,
                updated_at=now(),
            )
            version = WikiPageVersionRow(
                page_id=page.id, v=1, content=content,
                claims=claims_payload, glossary_terms=glossary,
                source=source, desc=desc, operator=operator, task_no=task_no,
            )
            page, version = await self._store.create_page_with_version(page, version)
        else:
            version = WikiPageVersionRow(
                page_id=page.id, v=(page.current_version or 0) + 1, content=content,
                claims=claims_payload, glossary_terms=glossary,
                source=source, desc=desc, operator=operator, task_no=task_no,
            )
            page, version = await self._store.append_version(
                page.id, version, title=title, digest=d.derive_digest(content)
            )
        await self._kb.publish_wiki_version(report_id, version.v)
        return version

    # ---------- B4 端点 1：目录 ----------

    async def list_pages(
        self, lib: str | None = None, keyword: str | None = None
    ) -> list[d.WikiPageListItem]:
        needle = (keyword or "").strip().casefold()
        out: list[d.WikiPageListItem] = []
        for page in await self._store.all_pages():
            report = await self._kb.report_detail(page.source_report_id)
            lib_name = report.lib
            if lib not in (None, "all") and lib_name != lib:
                continue
            if needle and needle not in page.title.casefold() and (
                needle not in report.doc.casefold() and needle not in lib_name.casefold()
            ):
                continue
            current = await self._store.version(page.id, page.current_version or 1)
            count = len(await self._store.versions_of(page.id))
            out.append(
                d.WikiPageListItem(
                    id=page.id,
                    title=page.title,
                    lib=lib_name,
                    source_report_id=page.source_report_id,
                    source_report_doc=report.doc,
                    current_version=page.current_version or 1,
                    version_count=count,
                    updated=(page.updated_at or page.created_at).strftime(DISPLAY_FMT),
                    status=d.page_status_of(current.content if current else ""),
                )
            )
        return out

    # ---------- B4 端点 2：全文（?version=N 任意版快照） ----------

    async def page_detail(
        self, page_id: str, *, version: int | None = None
    ) -> d.WikiPageDetail:
        page = await self._store.page(page_id)
        if page is None:
            raise d.WikiNotFoundError(f"百科页不存在（含 wiki 开关关未生成）：{page_id}")
        target_v = version if version is not None else page.current_version
        if target_v is None:
            raise d.WikiNotFoundError(f"百科页尚无已生成版本：{page_id}")
        row = await self._store.version(page_id, target_v)
        if row is None:
            raise d.WikiNotFoundError(f"版本不存在：v{target_v}")
        report = await self._kb.report_detail(page.source_report_id)
        count = len(await self._store.versions_of(page_id))
        return d.WikiPageDetail(
            id=page.id,
            title=page.title,
            lib=report.lib,
            slug=page.id,  # slug 稳定性＝id 承载（99 §2.7）
            digest=page.digest,
            source_report_id=page.source_report_id,
            source_report_doc=report.doc,
            current_version=page.current_version or 1,
            version_count=count,
            updated=row.created_at.strftime(DISPLAY_FMT),
            status=d.page_status_of(row.content),
            generation_source=row.source,
            operator=row.operator,
            related_objects=self._related_objects(report),
            content=row.content,
            claims=list(row.claims),
            glossary_terms=list(row.glossary_terms),
        )

    def _related_objects(self, report: Any) -> list[d.RelatedObjectView]:
        """关联对象投影（井档案只读投影——不建仓；summary 未回填报空串）。"""
        return [
            d.RelatedObjectView(
                type=obj.get("type", ""), id=obj.get("id", ""),
                summary=report.subject or "", links=list(d.RELATED_OBJECT_LINKS),
            )
            for obj in report.related_objects
        ]

    # ---------- B4 端点 3：版本列表 ----------

    async def versions(self, page_id: str) -> list[d.WikiVersionItem]:
        page = await self._store.page(page_id)
        if page is None:
            raise d.WikiNotFoundError(f"百科页不存在（含 wiki 开关关未生成）：{page_id}")
        rows = await self._store.versions_of(page_id)
        return [
            d.WikiVersionItem(
                v=row.v,
                date=row.created_at.strftime(DISPLAY_FMT),
                source=row.source,
                desc=row.desc,
                operator=row.operator,
                task_no=row.task_no,
                current=row.v == page.current_version,
            )
            for row in rows
        ]

    # ---------- B4 端点 4：一键回滚（追加语义＋防呆） ----------

    async def rollback(
        self, page_id: str, target_version: int, actor_who: str
    ) -> d.RollbackReceipt:
        page = await self._store.page(page_id)
        if page is None:
            raise d.WikiNotFoundError(f"百科页不存在（含 wiki 开关关未生成）：{page_id}")
        if not target_version:
            raise d.WikiParamError("target_version 必填")
        current_v = page.current_version
        if current_v is None:
            raise d.WikiNotFoundError(f"百科页尚无已生成版本：{page_id}")
        if target_version == current_v:
            raise d.WikiParamError(f"目标版 v{target_version} 即当前版——无可回滚")
        target = await self._store.version(page_id, target_version)
        if target is None:
            raise d.WikiNotFoundError(f"目标版本不存在：v{target_version}")
        current = await self._store.version(page_id, current_v)
        if current is not None and current.content == target.content:
            raise d.WikiConflictError(
                "当前已是回滚后的版本（目标版内容与当前版逐字相同）"
                "——回滚本身也记成一次新提交，可继续回滚到更早版本"
            )
        new_v = current_v + 1
        version = WikiPageVersionRow(
            page_id=page_id, v=new_v, content=target.content,
            claims=list(target.claims), glossary_terms=list(target.glossary_terms),
            source=d.SOURCE_ROLLBACK, desc=d.ROLLBACK_DESC_TEMPLATE.format(
                target=target_version
            ),
            operator=actor_who, task_no=None,  # 回滚无经由单号（B4 经由单号列口径）
        )
        page, version = await self._store.append_version(page_id, version)
        await self._kb.publish_wiki_version(page.source_report_id, new_v)
        return d.RollbackReceipt(
            page_id=page_id,
            current_version=new_v,
            new_version=d.WikiVersionItem(
                v=new_v,
                date=version.created_at.strftime(DISPLAY_FMT),
                source=version.source,
                desc=version.desc,
                operator=version.operator,
                task_no=None,
                current=True,
            ),
            status=d.page_status_of(version.content),
            banner=d.rollback_banner(new_v, target_version),
        )

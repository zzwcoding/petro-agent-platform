"""domains.derivatives.service —— 派生物域服务：wiki 支路编排（生成/重铸/读面）。

公开面照 98 §3.5 derivatives 卡＋B4 合同 v0.4 两读端点：
- 事件订阅（B9——kb 不直调 derivatives，派生物只经事件触发）：
  `on_ingest_completed`（入库/重跑定型→wiki 生成/重建）；
  `on_fragment_revised`（片段修正→重铸队列→覆盖当前版；失败不阻塞修正
  ——记 B1 活动流，可手动重跑）。
- 生成支路（PRD F50 工序）：块拼回全文（相邻重叠去重）→图片块连图注回读
  →32K 截断→LLM 模板重写（模板＝提示词约束按库业务模板投影，产出自由
  markdown 零固定节；截断纪律＝最多续写 3 轮、未完放弃本次写入不落半页）
  →claims 锚校验（fail-closed）→台账挂接（台账无账不挂）→覆盖当前版。
- 覆盖语义（B4 v0.4——Owner 2026-10-04 拍板"版本历史直接去掉"）：重建
  **覆盖当前版**（页级行原地更新、current_version＝重建计数单调 +1），
  不留历史、不可回滚；重铸失败当前版保持旧内容（半页不落库语义不变）。
- 读面（B4 端点 1/2）：目录（lib/keyword 筛选＋status 服务端按当前版
  [[flag:]] 判定）/全文（元数据字段表＋content＋claims[]＋glossary_terms[]，
  恒当前版、无 ?version=N）。

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

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.derivatives import domain as d
from app.domains.derivatives.store import (
    ExtractConfigRow,
    ExtractConfigStore,
    WikiPageRow,
    WikiStore,
)
from app.domains.semantics import term_expiry
from app.infra.clock import DISPLAY_FMT, now
from app.infra.config import load_ontology_export
from app.infra.eventbus import DomainEvent
from app.infra.graph_store import GraphStore

LOGGER = logging.getLogger("domains.derivatives")

# LLM 出口（B6）：百科生成＝起草/生成族——petro-main（P1-00 拍板基线）。
WIKI_ALIAS = "petro-main"
WIKI_CALLER = "wiki.gen"

# 图支路（B5）：抽取与示例起草同为起草/生成族——petro-main（B5 抽取设置
# few-shot 配置进 prompt；三源辅助③「LLM 起草」真实实现走统一出口）。
GRAPH_EXTRACT_ALIAS = "petro-main"
GRAPH_EXTRACT_CALLER = "graph.extract"
GRAPH_DRAFT_CALLER = "graph.draft"

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
    """kb 公开面（B9 例外族：报告读面＋活动流写口＋wiki 重建计数投影回写）。"""

    async def report_detail(self, report_id: str) -> Any: ...

    async def record_activity(
        self, lib_id: str, *, who: str, action: str, target: str,
        session: AsyncSession | None = None,
    ) -> None: ...

    async def publish_wiki_version(self, report_id: str, version: int) -> None: ...

    async def list_libraries(
        self, graph: str | None = None, keyword: str | None = None
    ) -> list[Any]: ...

    async def library_config(self, lib_id: str) -> Any: ...


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
        graph: GraphStore | None = None,
        branch_reporter: Any = None,
    ) -> None:
        self._gateway = gateway
        self._kb = kb
        self._semantics = semantics
        self._graph = graph  # 图存储 seam（生产装配 Neo4jGraphStore——main.py）
        self._branch_reporter = branch_reporter  # G-02 支路进度回写缝（callable，可 None）
        self._store = WikiStore(db)
        self._extract_configs = ExtractConfigStore(db)
        self._recasts = _RecastRuntime(tasks={}, pending=set())

    # ---------- 事件订阅（main.py lifespan 装配；B9 缝） ----------

    async def on_ingest_completed(self, event: DomainEvent) -> None:
        """IngestCompleted→wiki 支路＋graph 支路（开关关→支路不跑不花钱）。

        graph 支路（B5/B1 跨页锚点）：config_snapshot.graph=true 时按
        extract_snapshot（confirm 时刻定型——B5 端点 3 注记）逐 chunk LLM 抽
        三元组、过铁律三闸后入图；拦下记 blocked-edges 对账镜像。失败不阻塞
        入库任务（任务体已 done——富化失败不阻塞整卷先例）。
        """
        payload = event.payload
        task_id = str(payload.get("task_id") or "")
        if payload.get("config_snapshot", {}).get("wiki"):
            await self._spawn_generation(
                str(payload["report_id"]),
                str(payload["lib_id"]),
                task_id=task_id,
            )
        if payload.get("config_snapshot", {}).get("graph"):
            self._spawn_graph_extract(
                str(payload["report_id"]),
                str(payload["lib_id"]),
                task_no=str(payload.get("task_id") or ""),
                extract_snapshot=payload.get("extract_snapshot") or None,
                task_id=task_id,
            )

    async def on_fragment_revised(self, event: DomainEvent) -> None:
        """FragmentRevised→该报告 wiki 页进重铸队列（复用生成管线；失败不阻塞）。"""
        payload = event.payload
        report_id = str(payload["report_id"])
        self._enqueue_recast(report_id, str(payload["lib_id"]))

    def _enqueue_recast(self, report_id: str, lib_id: str) -> None:
        """重铸队列：在途合并（完成后补跑一次），量级演示级。"""
        running = self._recasts.tasks.get(report_id)
        if running is not None and not running.done():
            self._recasts.pending.add(report_id)
            return
        self._spawn_recast(report_id, lib_id)

    def _spawn_recast(self, report_id: str, lib_id: str) -> None:
        async def _run() -> None:
            try:
                await self._generate(report_id, lib_id, failure_activity=True)
            finally:
                self._recasts.tasks.pop(report_id, None)
                if report_id in self._recasts.pending:
                    self._recasts.pending.discard(report_id)
                    self._spawn_recast(report_id, lib_id)

        self._recasts.tasks[report_id] = asyncio.create_task(_run())

    async def _spawn_generation(
        self, report_id: str, lib_id: str, task_id: str = ""
    ) -> None:
        reporter = self._branch_reporter

        async def _report_wiki(state: str, detail: str | None = None) -> None:
            if reporter is None or not task_id:
                return
            try:  # 回写失败不影响支路（与 graph 侧 _report 同款设防）
                await reporter(task_id, "wiki", state, detail)
            except Exception:  # 清理面静默（回写失败不掩盖支路状态）
                LOGGER.exception("wiki 支路进度回写失败 task=%s", task_id)

        await _report_wiki("running")
        try:
            await self._generate(report_id, lib_id)
            await _report_wiki("done")
        except Exception:  # 生成失败不阻塞入库任务（任务体已 done——只记日志）
            LOGGER.exception("wiki 生成失败 report=%s", report_id)
            await _report_wiki("failed", detail="百科生成异常——见后端日志")

    # ---------- 生成支路（F50 工序） ----------

    async def _generate(
        self,
        report_id: str,
        lib_id: str,
        *,
        failure_activity: bool = False,
    ) -> None:
        """拼回→截断→LLM 重写→锚校验→挂接→覆盖当前版；失败可记活动流。"""
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
            )
        except Exception as exc:
            LOGGER.exception("wiki 生成失败 report=%s", report_id)
            if failure_activity:
                # 重铸失败不阻塞修正（富化失败不阻塞整卷先例）——记 B1 活动流；
                # 半页不落库：本次覆盖不发生、当前版保持旧内容，可经 B1 端点 10
                # 重跑触发。
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
            today = now().date()  # B14 时间单点——读侧派生不入库
            terms = await self._semantics.list_terms(page=1, page_size=1000)
            for row in terms.items:
                # expires_display＝C1 端点 2 行同形补键（W-B4.rev F6——M-09③）：
                # term_expiry 单源派生（禁用词「—（已禁用）」/无期「长期」族/
                # 已届满「<ISO>（已届满）」/其余 ISO 原样），不在本域重写规则。
                _, expires_display = term_expiry(row.status_key, row.expires_at, today)
                card = {
                    "type": row.type,
                    "def": row.def_,
                    "status": row.status,
                    "owner": row.owner,
                    "expires_display": expires_display,
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
    ) -> int:
        """覆盖当前版（B4 v0.4 行为规则 1）＋wiki 重建计数投影回写（B9 例外族）。

        - 首次生成：建页（slug 稳定性＝id 承载）落 v1；
        - 重建：页级行原地更新（content/digest/claims/glossary_terms/updated_at），
          `current_version` 单调 +1（＝重建计数，与 B1 台账 `wiki` 字段同源）；
        - **版本表不再追加**（wiki_page_version 写路径 v0.4 撤除——Owner 拍板
          撤版本历史，表保留不删留档）；
        - 半页不落库语义不变：本方法只在生成全程成功后被调用，失败在调用前
          短路、当前版保持旧内容。
        """
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
                content=content,
                claims=claims_payload,
                glossary_terms=glossary,
                updated_at=now(),
            )
            page = await self._store.insert_page(page)
        else:
            page = await self._store.overwrite_current(
                page.id,
                title=title,
                digest=d.derive_digest(content),
                content=content,
                claims=claims_payload,
                glossary_terms=glossary,
            )
        current = page.current_version or 1
        await self._kb.publish_wiki_version(report_id, current)
        return current

    # ---------- B4 端点 1：目录 ----------

    async def count_pages(self) -> int:
        """全量页数（筛选前先数——B4 v0.4 端点 1 DTO 注记「total＝全量计数；
        『筛选结果 X / Y 条』＝前端按 items 长度＋total 拼」，P2-04 修复拍 F2）。"""
        return len(await self._store.all_pages())

    async def list_pages(
        self, lib: str | None = None, keyword: str | None = None
    ) -> list[d.WikiPageListItem]:
        """百科页目录（lib/keyword 服务端筛选；keyword 匹配题名/来源报告/所属库
        三字段；按 updated 倒序；status 服务端按当前版正文 [[flag:]] 判定）。"""
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
            out.append(
                d.WikiPageListItem(
                    id=page.id,
                    title=page.title,
                    lib=lib_name,
                    source_report_id=page.source_report_id,
                    source_report_doc=report.doc,
                    current_version=page.current_version or 1,
                    updated=(page.updated_at or page.created_at).strftime(DISPLAY_FMT),
                    status=d.page_status_of(page.content or ""),
                )
            )
        return out

    # ---------- B4 端点 2：全文（恒当前版——v0.4 撤 ?version=N） ----------

    async def page_detail(self, page_id: str) -> d.WikiPageDetail:
        """百科页全文（元数据字段表＋自由 markdown 正文＋claims＋glossary_terms；
        恒返回当前版快照；generation_source/operator 按 v0.4 单态派生不落列）。"""
        page = await self._store.page(page_id)
        if page is None:
            raise d.WikiNotFoundError(f"百科页不存在（含 wiki 开关关未生成）：{page_id}")
        if page.current_version is None:  # 建页即 v1——防御性不可达分支
            raise d.WikiNotFoundError(f"百科页尚无已生成版本：{page_id}")
        report = await self._kb.report_detail(page.source_report_id)
        return d.WikiPageDetail(
            id=page.id,
            title=page.title,
            lib=report.lib,
            slug=page.id,  # slug 稳定性＝id 承载（99 §2.7）
            digest=page.digest,
            source_report_id=page.source_report_id,
            source_report_doc=report.doc,
            current_version=page.current_version,
            updated=(page.updated_at or page.created_at).strftime(DISPLAY_FMT),
            status=d.page_status_of(page.content or ""),
            generation_source=d.SOURCE_AUTO,
            operator=d.OPERATOR_SYSTEM,
            related_objects=self._related_objects(report),
            content=page.content or "",
            claims=list(page.claims or []),
            glossary_terms=list(page.glossary_terms or []),
        )

    def _related_objects(self, report: Any) -> list[d.RelatedObjectView]:
        """关联对象投影（B4 v0.3 同形状；井档案只读投影——不建仓）。

        V1 阶段取页内存关联（derivatives 生成时已有的对象识别——kb 报告读面
        related_objects 直出）；A2 井档案接线后切同源 well_info 投影（挂账
        P2-04 票面点名），不许为此私建井表读缝；summary 未回填报空串。
        """
        return [
            d.RelatedObjectView(
                type=obj.get("type", ""), id=obj.get("id", ""),
                summary=report.subject or "", links=list(d.RELATED_OBJECT_LINKS),
            )
            for obj in report.related_objects
        ]

    # ---------- graph 子域（B5-关系图谱.md v0.2——P1-05） ----------

    def _spawn_graph_extract(
        self,
        report_id: str,
        lib_id: str,
        *,
        task_no: str,
        extract_snapshot: dict[str, Any] | None,
        task_id: str = "",
    ) -> None:
        """graph 抽取任务族（进程内 asyncio——失败不阻塞入库任务）。

        报告级防重入登记在此统一（E3——入库触发与手动重抽两路共用）：
        启动即登记（report_id→task_no，task_no 兼作来源标记——"reextract"＝
        手动重抽、其余＝入库任务号）；支路收尾即解除（asyncio done 语义——
        正常/失败/取消均触发回调，含异常路径清理，防泄漏假阳性）。
        """
        self._graph_tasks = [
            t for t in getattr(self, "_graph_tasks", []) if not t.done()
        ]
        if not hasattr(self, "_graph_running"):
            self._graph_running: dict[str, str] = {}
        self._graph_running[report_id] = task_no
        reporter = self._branch_reporter

        async def _report(state: str, detail: str | None = None,
                          extra: dict[str, Any] | None = None) -> None:
            if reporter is not None and task_id:
                try:
                    await reporter(task_id, "graph", state, detail, extra)
                except Exception:  # 回写失败不影响支路（G-02 非关键面）
                    LOGGER.exception("graph 支路进度回写失败 task=%s", task_id)

        async def _run() -> None:
            await _report("running")
            try:
                stats = await self._extract_for_report(
                    report_id, lib_id, task_no=task_no,
                    extract_snapshot=extract_snapshot, task_id=task_id,
                )
                await _report("done", extra=stats or None)
            except Exception:
                LOGGER.exception(
                    "graph 抽取失败 report=%s task=%s", report_id, task_no
                )
                await _report("failed", detail="图谱抽取异常——见后端日志")

        task = asyncio.create_task(_run())
        self._graph_tasks.append(task)
        task.add_done_callback(
            lambda _t: getattr(self, "_graph_running", {}).pop(report_id, None)
        )

    async def reextract_graph(self, report_id: str, lib_id: str) -> dict[str, Any]:
        """图谱支路重跑（G-06——补 M-06 无重跑端点缺口；报告级防重入）。

        抽取设置沿用该库现行待生效配置（未保存过→出厂默认投影）；失败不阻塞
        调用方——支路自身异常自捕获（与入库触发路径同款）。
        防重入＝报告级（E3）：该报告任何图谱支路在跑（入库触发或手动重抽）
        一律拒——两态文案可辨；400 语义暂保持（409 归一归 DE-12）。
        """
        await self._kb.report_detail(report_id)  # 404 早抛（报告不存在）
        running = getattr(self, "_graph_running", {}).get(report_id)
        if running is not None:
            from app.domains.derivatives.domain import GraphParamError

            where = "重抽在跑" if running == "reextract" else "入库支路在跑"
            raise GraphParamError(f"该报告图谱支路已在运行中——{where}，防重入拒")
        self._spawn_graph_extract(
            report_id, lib_id, task_no="reextract", extract_snapshot=None
        )
        return {"report_id": report_id, "lib_id": lib_id, "spawned": True}

    async def _extract_for_report(
        self,
        report_id: str,
        lib_id: str,
        *,
        task_no: str,
        extract_snapshot: dict[str, Any] | None,
        task_id: str = "",
    ) -> dict[str, Any]:
        """图谱支路（F40）：chunk 挑选闸→LLM 按 ExtractConfig 抽三元组→三道闸
        →过闸写图＋拦下记 blocked-edges（namespace=库）。

        - ExtractConfig＝confirm 时刻定型快照（extract_snapshot——B5 端点 3
          注记；缺省回退当前待生效配置/出厂默认——重跑定型前的历史任务行）；
        - chunk 挑选闸：无正文的块不送抽取（防复读 few-shot、防重复计费）；
        - 三道闸＝铁律合同常量（类型闸/依据闸/弃权闸——domain.gate_triples）。
        """
        if self._graph is None:
            raise RuntimeError("图存储未装配——graph 支路不可用（装配缺失）")
        cfg = (
            d.config_from_snapshot(extract_snapshot)
            if extract_snapshot
            else await self._load_config_for_lib(lib_id)
        )
        detail = await self._kb.report_detail(report_id)
        evidence_chunks = [f for f in detail.fragments if f.text]  # chunk 挑选闸
        LOGGER.info(
            "graph 抽取开始 report=%s lib=%s task=%s chunks=%d",
            report_id, lib_id, task_no, len(evidence_chunks),
        )
        reporter = self._branch_reporter
        total = len(evidence_chunks)
        edges_passed = 0
        blocked_total = 0
        for idx, frag in enumerate(evidence_chunks, start=1):
            if reporter is not None and task_id:
                try:
                    await reporter(task_id, "graph", "running",
                                   extra={"chunks_done": idx - 1, "chunks_total": total,
                                          "edges": edges_passed, "blocked": blocked_total})
                except Exception:  # 回写失败不影响抽取
                    LOGGER.exception("graph 支路进度回写失败 task=%s", task_id)
            prompt = d.build_extract_prompt(cfg, section=frag.path, chunk_text=frag.text)
            completion = await self._gateway.complete(
                GRAPH_EXTRACT_ALIAS,
                [{"role": "user", "content": prompt}],
                caller=GRAPH_EXTRACT_CALLER,
            )
            candidates = d.parse_triples(completion.content)
            passed, blocked = d.gate_triples(
                candidates, cfg,
                chunk_text=frag.text, chunk_id=frag.id, report_id=report_id,
            )
            for edge in passed:
                await self._graph.upsert_node(
                    lib_id, node_id=edge.from_, label=edge.from_,
                    node_type=edge.from_type, short=edge.from_, sub=edge.from_type,
                )
                await self._graph.upsert_node(
                    lib_id, node_id=edge.to, label=edge.to,
                    node_type=edge.to_type, short=edge.to, sub=edge.to_type,
                )
                await self._graph.upsert_edge(
                    lib_id, key=edge.key, from_id=edge.from_, rel=edge.rel,
                    to_id=edge.to, note=edge.note, evidence=edge.evidence,
                    chunk_id=edge.chunk_id, report_id=edge.report_id,
                )
            for item in blocked:
                await self._graph.record_blocked(
                    lib_id, key=item.key, from_id=item.from_,
                    from_type=item.from_type, rel=item.rel, to_id=item.to,
                    to_type=item.to_type, reason_code=item.reason_code,
                    reason=item.reason, report_id=item.report_id,
                    report_title=detail.doc, chunk_id=item.chunk_id,
                    blocked_at=now().strftime(DISPLAY_FMT),
                )
            edges_passed += len(passed)
            blocked_total += len(blocked)
            LOGGER.info(
                "graph 抽取 chunk=%s 过闸 %d 拦下 %d", frag.id, len(passed), len(blocked)
            )

        return {
            "chunks_total": total, "chunks_done": total,
            "edges": edges_passed, "blocked": blocked_total,
        }

    async def _load_config_for_lib(self, lib_id: str) -> d.ExtractConfig:
        """当前待生效配置（未保存过→出厂默认＝本体对号表投影）。"""
        row = await self._extract_configs.config_of(lib_id)
        if row is not None:
            return d.config_from_snapshot(_row_snapshot(row))
        return d.default_extract_config(*_ontology_catalogs())

    async def _require_lib(self, lib_id: str) -> Any:
        """库定位（B5 错误码草案：库不存在 404——端点 1/2/3/4 同）。"""
        try:
            return await self._kb.library_config(lib_id)
        except Exception as exc:
            raise d.GraphNotFoundError(f"库不存在：{lib_id}") from exc

    # ---- B5 端点 1：整图读（整图一次给——邻接过滤为前端本地计算） ----

    async def graph_net(self, lib_id: str) -> d.GraphNet:
        lib = await self._require_lib(lib_id)
        switches = getattr(lib, "switches", {}) or {}
        if not switches.get("graph", False):
            # 开关关闭期间一律空态（既有图数据的保留/清理属图存储生命周期批）。
            return d.GraphNet(
                lib_id=lib_id, lib_name=lib.name, nodes=[], edges=[],
                legend=[], stats={"nodes": 0, "edges": 0},
            )
        if self._graph is None:
            raise RuntimeError("图存储未装配——graph 支路不可用（装配缺失）")
        data = await self._graph.read_net(lib_id)
        nodes = [
            d.GraphNodeView(
                id=str(n.get("id", "")), label=str(n.get("label", "")),
                type=str(n.get("type", "")), short=str(n.get("short", "")),
                sub=str(n.get("sub", "")),
            )
            for n in data["nodes"]
        ]
        edges = [
            d.GraphEdgeView(
                key=str(e["key"]), from_=str(e["from"]), rel=str(e["rel"]),
                to=str(e["to"]), note=e.get("note"),
                evidence_chunk_id=str(e.get("chunk_id", "")),
                report_id=str(e.get("report_id", "")),
            )
            for e in data["edges"]
        ]
        counts: dict[str, int] = {}
        for node in nodes:
            counts[node.type] = counts.get(node.type, 0) + 1
        legend = [d.LegendItem(type=t, count=c) for t, c in counts.items()]
        return d.GraphNet(
            lib_id=lib_id, lib_name=lib.name, nodes=nodes, edges=edges,
            legend=legend,
            stats={"nodes": len(nodes), "edges": len(edges)},
        )

    # ---- B5 端点 2：抽取设置读 ----

    async def get_extract_config(self, lib_id: str) -> d.ExtractConfigView:
        lib = await self._require_lib(lib_id)
        row = await self._extract_configs.config_of(lib_id)
        config = (
            d.config_from_snapshot(_row_snapshot(row)) if row is not None
            else d.default_extract_config(*_ontology_catalogs())
        )
        return d.ExtractConfigView(
            lib_id=lib_id, lib_name=lib.name, config=config,
            saved_at=row.saved_at.strftime(DISPLAY_FMT) if row and row.saved_at else None,
            saved_by=row.saved_by if row else None,
        )

    # ---- B5 端点 3：抽取设置保存（对号强校两态＋同事务记 B1 活动流） ----

    async def save_extract_config(
        self, lib_id: str, payload: dict[str, Any], actor_who: str, *,
        strong_check: bool = True,
    ) -> d.ExtractConfigSaveReceipt:
        """保存待生效配置（下次入库定型、不热切换、正在处理任务不受影响）。

        - 形状校验（四段/空清单/缺 rel/重复 rel）→ 400；
        - 对号强校两态（B5 端点 3 注记——防施工卡死的两句都写）：
          strong_check=True＝**接线后**（P1-01 导出物就绪——阶段 1 内已接线，
          生产常态）：实体类型/关系标签对本体对号表强校，对不上拒存 400 带
          对号明细（逐项未收录词条＋最接近台账词条）；
          strong_check=False＝**接线前**过渡态（仅形状校验照跑）——参数保留
          承载过渡两态，生产恒 True。
        - 同事务记 B1 库活动流一条（F62 跨页留痕：action「修改抽取设置」，
          target 按变更内容拼装——B9 例外族经 kb.record_activity 写口）。

        同事务选型（P1-05b 审查裁决，两案取一）：**session 由调用方经
        callable 参数注入**，不取「kb 侧另立 in_tx 变体」——理由：①事务边界
        归属写集所有者（配置保存的事务在 ExtractConfigStore.save 内），活动行
        以参与者身份进入该事务，与 kb 自身 save_config_with_activity 的
        「保存＋活动行同会话」同构；②kb 公开面单写口不加面——record_activity
        增可选 session 参（缺省自开轻会话，B2 标记等原调用零改动），另立
        in_tx 变体等于同一写面两个 seam，且其签名同样要收 session，纯增面；
        ③B9 边界不破——callable 仍由组合根注入（main.py 把 KbService 装进
        DerivativesService），derivatives 不见 kb 表模型，kb 只多收一个会话
        对象。
        """
        lib = await self._require_lib(lib_id)
        cfg = d.config_from_payload(payload)
        if strong_check:
            entity_catalog, relation_catalog = _ontology_catalogs()
            mismatches = d.ontology_check(
                cfg,
                entity_catalog=[str(r["name"]) for r in entity_catalog],
                relation_catalog=[str(r["name"]) for r in relation_catalog],
            )
            if mismatches:
                raise d.GraphOntologyMismatchError(mismatches)
        target = (
            f"{lib.name} · 实体类型 {len(cfg.entity_types)} 类 · "
            f"关系标签 {len(cfg.relation_tags)} 个"
        )

        async def _record_activity_in_tx(session: AsyncSession) -> None:
            await self._kb.record_activity(
                lib_id, who=actor_who, action="修改抽取设置", target=target,
                session=session,
            )

        row = await self._extract_configs.save(
            lib_id, cfg, actor_who=actor_who, record_activity=_record_activity_in_tx
        )
        return d.ExtractConfigSaveReceipt(
            lib_id=lib_id,
            saved_at=row.saved_at.strftime(DISPLAY_FMT) if row.saved_at else "",
            saved_by=row.saved_by or actor_who,
            hint=d.SAVE_HINT,
        )

    # ---- B5 端点 4：被拦边清单（纯只读——治理复盘/E3 天然消费） ----

    async def blocked_edges(self, lib_id: str) -> d.BlockedEdgesPage:
        lib = await self._require_lib(lib_id)
        if self._graph is None:
            raise RuntimeError("图存储未装配——graph 支路不可用（装配缺失）")
        rows = await self._graph.list_blocked(lib_id)
        views = [
            d.BlockedEdgeView(
                key=str(r.get("key", "")), from_=str(r.get("from", "")),
                from_type=str(r.get("from_type", "")), rel=str(r.get("rel", "")),
                to=str(r.get("to", "")), to_type=str(r.get("to_type", "")),
                reason_code=str(r.get("reason_code", "")),
                reason=str(r.get("reason", "")),
                report_id=str(r.get("report_id", "")),
                report_title=str(r.get("report_title", "")),
                chunk_id=r.get("chunk_id") or None,
                blocked_at=str(r.get("blocked_at", "")),
            )
            for r in rows
        ]
        return d.BlockedEdgesPage(
            lib_id=lib_id, lib_name=lib.name, blocked_edges=views,
            stats={"blocked": len(views)},
        )

    # ---- LLM 起草示例（三源辅助③——真实实现走 gateway.complete） ----

    async def draft_example(
        self, lib_id: str, *, rel: str, sentence: str | None = None
    ) -> d.DraftedExample:
        """起草 few-shot 示例对（人不从零造示例——示例靠系统辅助生成、人核对）。

        - 带原句：为该句配三元组（从报告库选句源——三元组侧预填建议值）；
        - 只带关系词：按库配置起草一对示例（LLM 起草源）。
        """
        await self._require_lib(lib_id)
        rel = rel.strip()
        if not rel:
            raise d.GraphParamError("关系词必填（LLM 起草按关系词对号）")
        if sentence:
            ask = (
                f"下面是报告里的一句原句。请判断它表达了什么实体关系（关系标签"
                f"提示：{rel}），输出一行「起点 —关系→ 终点」形态的三元组，"
                f"不要输出其他任何文字。\n\n原句：{sentence}"
            )
        else:
            ask = d.DRAFT_PROMPT_TEMPLATE.format(rel=rel)
        completion = await self._gateway.complete(
            GRAPH_EXTRACT_ALIAS,
            [{"role": "user", "content": ask}],
            caller=GRAPH_DRAFT_CALLER,
        )
        text, triple = d.parse_draft(completion.content)
        return d.DraftedExample(sentence=text, triple=triple)


def _row_snapshot(row: ExtractConfigRow) -> dict[str, Any]:
    """kb_extract_config 行 → ExtractConfig 快照形状（列名与快照键同构）。"""
    return {
        "entity_types": list(row.entity_types),
        "relation_tags": list(row.relation_tags),
        "few_shot_examples": list(row.few_shot_examples),
        "custom_instructions": row.custom_instructions,
    }


def _ontology_catalogs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """P1-01 导出物装载（config/entity_types.json＋relation_types.json——对号
    强校数据源；文件缺失/损坏显式报错，禁静默放行）。"""
    return (
        load_ontology_export("entity_types"),
        load_ontology_export("relation_types"),
    )


async def load_extract_config_snapshot(db: Any, lib_id: str) -> dict[str, Any]:
    """抽取设置定型快照装载（B5 端点 3 注记：图谱支路的配置快照形状＝端点 2
    DTO 减 lib_id/saved_at/saved_by，由服务端在 B1 confirm 时刻一并快照入
    kb_ingest_task.extract_snapshot）。

    kb 经 main.py 组合根注入本函数使用（B9：kb 禁 import derivatives——
    装配期注入 Protocol callable，运行期 kb 只见异步函数）。
    """
    row = await ExtractConfigStore(db).config_of(lib_id)
    if row is not None:
        return _row_snapshot(row)
    return d.default_extract_config(*_ontology_catalogs()).as_snapshot()

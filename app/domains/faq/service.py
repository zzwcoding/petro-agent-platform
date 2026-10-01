"""domains.faq.service —— FAQ 域服务：编排 store/台账读缝/切片读缝/gateway/embedder/对象存储。

公开面照 98 §3.3 卡 B3 面（17 方法）：list_entries / entry_detail / create_entry /
review_entry / dup_check / add_similar / remove_similar / merge_entries /
toggle_state / candidates / start_scan / scan_progress / compare_candidate /
draft_candidate / draft_from_refs / import_library / export_library ＋运行时读
match_index（chat 消费，不经 HTTP）＋LedgerMerged 订阅口 on_ledger_merged。

- 审核流（B3 v0.2——Owner 2026-10-01 拍板）：新增/修改先进 pending_review，
  review_entry publish 才落 serve/negative 并被 A1 消费；reject 落 disabled
  （留档可改后重新提审——合同补全语义最保守落点）；候选回写随发布事务
  （source_entry_id 锚——99 faq_candidate.source_entry_id 列）。
- 索引可见性：本票落内存态 match_index 读口（只认 serve 条目）；chunk_type=faq
  双写物理索引归 A1/索引融合批（98 卡 seam 悬置——差异登记票面）。
- 扫库＝异步长任务（00 §5 惯例——kb 任务体同构）：受理 202→进程内 asyncio
  task→done 落痕；重入 409；料源＝A1 历史会话（session_loader 缝——A1 未上线
  前注入 None，空态说明收场）；挖掘模型 petro-main（B3-10 拍板，B6 记账）。
- LedgerMerged 联动（B3-2 拍板）：按 hook 检出受影响条目→LLM 起草修订/停用
  建议→落待审核行进审核流；不自动直改（确认权在人）。
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import math
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.faq import domain as d
from app.domains.faq.store import (
    CandidateRow,
    CandidateStore,
    EntryRow,
    EntryStore,
    ScanTaskRow,
    ScanTaskStore,
    SimilarRow,
)
from app.domains.security.domain import AuditRow
from app.infra.clock import DISPLAY_FMT, now
from app.infra.db import ConnectionManager
from app.infra.eventbus import DomainEvent, make_event
from app.infra.object_storage import GET_TTL_SECONDS, ObjectStorage

LOGGER = logging.getLogger("domains.faq")

# LLM 出口（B6）：起草/挖掘模型＝petro-main（D1 别名——Owner 2026-10-01 拍板 B3-10）。
DIGEST_ALIAS = "petro-main"

# F60 晋升闸初值（孤例不进池——阈值数值开放问题 5 悬置半边，实施批校准；本票落 2）。
SCAN_MIN_FREQ = 2

_SIM_SEPARATOR_PATTERN = r"[；、|]"  # 导入相似问多值分隔（合同未冻结——多分隔符兼容）
_ONTO_HIT_FLOOR = 0.6  # 本体命中展示线（无命中展示形态页面无此态——开放问题 4）


class Completer(Protocol):
    """LLM 出口 seam（生产装配＝GatewayService——B6 唯一出口；测试注桩）。"""

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any: ...


class AuditSink(Protocol):
    """B12 审计写口缝（装配根注入 SecurityService——faq 不反向构造）。"""

    async def audit(self, row: AuditRow, *, session: AsyncSession | None = None) -> None: ...


class EmbeddingBackend(Protocol):
    """向量化 seam（结构同 kb.domain.EmbeddingBackend——同一缝的域侧视图）。"""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


# 组合根注入缝（B9 同款：faq 不 import semantics/kb，运行期只见 callable）——
# 返回形状：台账口径 (name, def_text, source_label)；切片 (text, source_label)；
# 本体去重面 [(face_label, name)]；知识库去重面 [display_text]；
# A1 历史会话 [{question, answer}]（A1 未上线＝None）。
LedgerLoader = Callable[[str, int], Awaitable[tuple[str, str, str] | None]]
SliceLoader = Callable[[str, str], Awaitable[tuple[str, str] | None]]
OntologyNamesLoader = Callable[[], Awaitable[list[tuple[str, str]]]]
KbCorpusLoader = Callable[[], Awaitable[list[str]]]
SessionLoader = Callable[[], Awaitable[list[dict[str, str]] | None]]


def _cosine(a: list[float], b: list[float]) -> float:
    """占位向量余弦（384 维本地确定性向量——维度待 embedding 模型回填，99 待办）。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = float(sum(x * y for x, y in zip(a, b, strict=True)))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass
class _ScanRuntime:
    """进程内扫库任务体登记（防双起——重入 409 之外的内存保险）。"""

    tasks: dict[str, asyncio.Task[None]]


class FaqService:
    """faq 域服务（编排；合同语义在 domain.py，持久在 store.py）。"""

    def __init__(
        self,
        db: ConnectionManager,
        gateway: Completer,
        storage: ObjectStorage,
        *,
        embedder: EmbeddingBackend | None = None,
        eventbus: Any | None = None,
        audit: AuditSink | None = None,
        ledger_loader: LedgerLoader | None = None,
        slice_loader: SliceLoader | None = None,
        ontology_names_loader: OntologyNamesLoader | None = None,
        kb_corpus_loader: KbCorpusLoader | None = None,
        session_loader: SessionLoader | None = None,
        step_seconds: float = 0.0,
    ) -> None:
        self._db = db
        self._gateway = gateway
        self._storage = storage
        self._embedder = embedder
        self._eventbus = eventbus
        self._audit = audit
        self._ledger_loader = ledger_loader
        self._slice_loader = slice_loader
        self._ontology_names_loader = ontology_names_loader
        self._kb_corpus_loader = kb_corpus_loader
        self._session_loader = session_loader
        self._step_seconds = step_seconds
        self._entries = EntryStore(db)
        self._candidates = CandidateStore(db)
        self._scans = ScanTaskStore(db)
        self._runtime = _ScanRuntime(tasks={})

    # ---------- 端点 1：问答清单 ----------

    async def list_entries(self, *, status: str = "all", keyword: str = "") -> d.FaqList:
        """问答清单（状态筛＋关键词搜问题/答案/相似问法；创建时间正序——合同排序）。"""
        if status not in d.ENTRY_STATUS_FILTERS:
            raise d.FaqParamError(
                f"status 越界：{status}（允许值 {'|'.join(d.ENTRY_STATUS_FILTERS)}）"
            )
        entries = await self._entries.all_entries()
        sims = await self._entries.all_sims()
        sims_by_entry: dict[str, list[str]] = {}
        for sim in sims:
            sims_by_entry.setdefault(sim.entry_id, []).append(sim.text)
        needle = keyword.strip().casefold()

        def matches(entry: EntryRow) -> bool:
            if status == "serve" and entry.status != "serve":
                return False
            if status == "pending" and entry.status != "pending_review":
                return False
            if status == "neg" and not entry.is_negative:
                return False
            if status == "disabled" and entry.status != "disabled":
                return False
            if not needle:
                return True
            hay = entry.question + entry.answer + "".join(sims_by_entry.get(entry.id, []))
            return needle in hay.casefold()

        rows = [e for e in entries if matches(e)]
        items = [
            d.FaqItem(
                id=e.id,
                question=e.question,
                answer=e.answer,
                similar_questions=sims_by_entry.get(e.id, []),
                status=e.status,
                hook=e.hook(),
            )
            for e in rows
        ]
        return d.FaqList(items=items, total=len(items), grand_total=len(entries))

    # ---------- 端点 2：详情 ----------

    async def entry_detail(self, entry_id: str) -> d.FaqDetail:
        """问答详情（相似问含 id 寻址键＋维护人/更新日期/版本——详情底行支撑）。"""
        entry = await self._entries.get(entry_id)
        if entry is None:
            raise d.FaqNotFoundError(f"问答条目不存在：{entry_id}")
        sims = await self._entries.sims_of(entry_id)
        return d.FaqDetail(
            id=entry.id,
            question=entry.question,
            answer=entry.answer,
            status=entry.status,
            hook=entry.hook(),
            similar_questions=[d.SimilarRef(id=s.id, text=s.text) for s in sims],
            maintainer=entry.maintainer,
            updated_at=entry.updated_at.date().isoformat(),  # 日期粒度照抄（R2 展示串读侧拼装）
            version=entry.version,
        )

    # ---------- 端点 3：新增问答（v0.2 先进待审核） ----------

    async def create_entry(
        self,
        question: str,
        answer: str,
        *,
        is_negative: bool,
        hook: d.Hook | None,
        source_candidate_id: str | None,
        actor_who: str,
    ) -> d.FaqCreated:
        """新增入库：空值占位不拒空；负例登记意向随行；恒落 pending_review。

        候选回写（source_candidate_id）：同事务登记 source_entry_id 回写锚
        （99 faq_candidate.source_entry_id 列），审核发布（端点 17）事务内落
        published——零悬挂；候选不存在 404、已发布 409。
        """
        q = question.strip() or d.EMPTY_QUESTION_PLACEHOLDER
        a = answer.strip() or d.EMPTY_ANSWER_PLACEHOLDER
        if is_negative:
            hook = None  # 负例行 hook 恒 null（服务端忽略负例单的 hook——合同冻结）
        candidate_ref: d.CandidateRef | None = None
        cand: CandidateRow | None = None
        async with self._db.transaction() as session:
            eid = await self._entries.next_entry_id(session)
            if source_candidate_id:
                cand = await self._candidates.get(source_candidate_id, session)
                if cand is None:
                    raise d.FaqNotFoundError(f"候选不存在：{source_candidate_id}")
                if cand.status == "published":
                    raise d.FaqConflictError(
                        f"候选已发布：{source_candidate_id}（禁止重复回写）",
                        code="faq_candidate_published",
                    )
            entry = EntryRow(
                id=eid,
                question=q,
                question_norm=d.normalize_text(q),
                norm_hash=d.norm_hash(q),
                answer=a,
                status="pending_review",
                is_negative=is_negative,
                hook_kind=hook.kind if hook else None,
                hook_name=hook.name if hook else None,
                version=1,
                maintainer=actor_who,
            )
            await self._entries.insert_entry(entry, session)
            if cand is not None:
                # 回写锚——条目 INSERT 落库后再 dirty（无 relationship 的 UOW 不保证
                # FK 插序，回写锚 UPDATE 先发即撞 faq_candidate_source_entry_id_fkey
                # ——P1-02a flush 排序先例同款，真库红绿实证）
                cand.source_entry_id = eid
                candidate_ref = d.CandidateRef(id=cand.id, status=cand.status)
        template = (
            d.CREATED_NEGATIVE_HINT_TEMPLATE if is_negative else d.CREATED_HINT_TEMPLATE
        )
        return d.FaqCreated(
            id=eid,
            status="pending_review",
            version=1,
            hint=template.format(question=q),
            candidate=candidate_ref,
        )

    # ---------- 端点 4：入库前重复校验（非阻断） ----------

    async def dup_check(self, question: str) -> tuple[d.DupHit | None, str | None]:
        """归一化比对既有问题＋相似问法；命中给 hint（非阻断——确认权在人）。"""
        if not question.strip():
            raise d.FaqParamError("question 空白——无可校验对象")
        norm = d.normalize_text(question)
        entries = await self._entries.all_entries()
        by_id = {e.id: e for e in entries}
        for sim in await self._entries.all_sims():  # 先查相似问（更具体的问法命中）
            entry = by_id.get(sim.entry_id)
            if entry is not None and sim.text_norm == norm:
                return d.DupHit(id=entry.id, question=entry.question), (
                    d.DUP_HINT_TEMPLATE.format(question=entry.question)
                )
        for entry in entries:
            if entry.question_norm == norm:
                return d.DupHit(id=entry.id, question=entry.question), (
                    d.DUP_HINT_TEMPLATE.format(question=entry.question)
                )
        return None, None

    # ---------- 端点 5/6：相似问增删（独立检索项，即时生效） ----------

    async def add_similar(
        self, entry_id: str, text: str, *, actor_who: str
    ) -> d.SimilarAdded:
        """添加相似问法（独立检索项）；与既有问法归一化重复 409（服务端兜底）。"""
        if not text.strip():
            raise d.FaqParamError("text 空白——无可添加的相似问法")
        async with self._db.transaction() as session:
            entry = await self._entries.get(entry_id, session)
            if entry is None:
                raise d.FaqNotFoundError(f"问答条目不存在：{entry_id}")
            sims = await self._entries.sims_of(entry_id, session)
            norm = d.normalize_text(text)
            # 独立检索项全库唯一：本条问题/相似问＋库内任一问题/相似问归一化重复
            # 均拒绝（重复添加同一问法无意义——服务端兜底，合同 409）
            all_entries = await self._entries.all_entries(session)
            all_sims = await self._entries.all_sims(session)
            if entry.question_norm == norm or any(s.text_norm == norm for s in sims) or any(
                e.question_norm == norm for e in all_entries
            ) or any(s.text_norm == norm for s in all_sims):
                raise d.FaqConflictError(
                    f"与既有问法归一化重复：{text}", code="faq_similar_duplicate"
                )
            sim_id = await self._entries.next_sim_id(session)
            clean = text.strip()
            await self._entries.insert_sim(
                SimilarRow(id=sim_id, entry_id=entry_id, text=clean, text_norm=norm),
                session,
            )
            await self._entries.bump_version(entry, session)
            return d.SimilarAdded(id=sim_id, text=clean, version=entry.version)

    async def remove_similar(
        self, entry_id: str, sim_id: str, *, actor_who: str
    ) -> d.VersionBumped:
        """删除相似问法：删掉即不再命中本条（分离索引即时生效）。"""
        async with self._db.transaction() as session:
            entry = await self._entries.get(entry_id, session)
            if entry is None:
                raise d.FaqNotFoundError(f"问答条目不存在：{entry_id}")
            sims = await self._entries.sims_of(entry_id, session)
            if not any(s.id == sim_id for s in sims):
                raise d.FaqNotFoundError(f"相似问法不存在：{sim_id}")
            await self._entries.delete_sim(sim_id, entry_id, session)
            await self._entries.bump_version(entry, session)
            return d.VersionBumped(version=entry.version, hint=d.SIMILAR_DELETE_HINT)

    # ---------- 端点 7：合并相似问 ----------

    async def merge_entries(
        self, from_id: str, target_id: str, *, actor_who: str
    ) -> d.MergeResult:
        """合并语义（合同值）：被并入条目删除、其问题进目标相似问列；2 条 → 1 条。"""
        if from_id == target_id:
            raise d.FaqParamError("from_id 与 target_id 相同——无可合并对象")
        async with self._db.transaction() as session:
            source = await self._entries.get(from_id, session)
            target = await self._entries.get(target_id, session)
            if source is None:
                raise d.FaqNotFoundError(f"被并入条目不存在（含已合并）：{from_id}")
            if target is None:
                raise d.FaqNotFoundError(f"目标条目不存在：{target_id}")
            source_sims = await self._entries.sims_of(from_id, session)
            target_sims = await self._entries.sims_of(target_id, session)
            occupied = {target.question_norm} | {s.text_norm for s in target_sims}
            moved = 0
            for text in [source.question] + [s.text for s in source_sims]:
                # 被并入方相似问随问题一并迁移（合并语义"命中同一条答案"；
                # 合同只言明问题去向——差异登记票面疑点清单）
                norm = d.normalize_text(text)
                if norm in occupied:
                    continue
                sim_id = await self._entries.next_sim_id(session)
                await self._entries.insert_sim(
                    SimilarRow(id=sim_id, entry_id=target_id, text=text, text_norm=norm),
                    session,
                )
                occupied.add(norm)
                moved += 1
            await self._entries.delete_entry(from_id, session)
            await self._entries.bump_version(target, session)
            hint = d.MERGE_HINT_TEMPLATE.format(
                from_question=source.question, target_question=target.question
            )
            return d.MergeResult(
                from_id=from_id,
                target_id=target_id,
                merged_count="2 条 → 1 条",
                target_similar_questions_count=len(target_sims) + moved,
                hint=hint,
            )

    # ---------- 端点 8：停用/启用 ----------

    async def toggle_state(
        self, entry_id: str, action: str, *, actor_who: str
    ) -> d.FaqStateView:
        """停用（摘出索引可随时启用）/启用（恢复参与回答）；负例行 409；无变化 409。"""
        if action not in ("disable", "enable"):
            raise d.FaqParamError(f"action 越界：{action}（允许值 disable|enable）")
        async with self._db.transaction() as session:
            entry = await self._entries.get(entry_id, session)
            if entry is None:
                raise d.FaqNotFoundError(f"问答条目不存在：{entry_id}")
            if action == "disable":
                if entry.is_negative:
                    raise d.FaqConflictError(
                        "负例条目无停用/启用入口（三态互斥——检索也不可达）",
                        code="faq_negative_toggle",
                    )
                if entry.status != "serve":
                    raise d.FaqConflictError(
                        f"状态未变化：{entry.status} 无需停用", code="faq_state_noop"
                    )
                entry.status = "disabled"
            else:
                if entry.status != "disabled":
                    raise d.FaqConflictError(
                        f"状态未变化：{entry.status} 无需启用", code="faq_state_noop"
                    )
                entry.status = "serve"
            await self._entries.bump_version(entry, session)
            return d.FaqStateView(id=entry.id, status=entry.status, version=entry.version)

    # ---------- 端点 17：审核发布/驳回 ----------

    async def review_entry(
        self, entry_id: str, action: str, *, actor_who: str
    ) -> d.FaqReviewed:
        """审核流（v0.2）：publish 按登记类型落 serve/negative、候选回写 published；
        reject 落 disabled（留档可改后重新提审）。"""
        if action not in ("publish", "reject"):
            raise d.FaqParamError(f"action 越界：{action}（允许值 publish|reject）")
        async with self._db.transaction() as session:
            entry = await self._entries.get(entry_id, session)
            if entry is None:
                raise d.FaqNotFoundError(f"问答条目不存在：{entry_id}")
            if entry.status != "pending_review":
                raise d.FaqConflictError(
                    f"仅待审核条目可审核：当前 {entry.status}", code="faq_review_state"
                )
            if action == "publish":
                entry.status = "negative" if entry.is_negative else "serve"
                for cand in await self._candidates.by_source_entry(entry_id, session):
                    if cand.status != "published":
                        cand.status = "published"  # 候选回写随发布事务（零悬挂）
            else:
                entry.status = "disabled"
            await self._entries.bump_version(entry, session)
            status = entry.status
            question = entry.question
            version = entry.version
        if action == "publish" and self._eventbus is not None:
            await self._eventbus.publish(
                make_event(
                    "FaqPublished",
                    {"entry_id": entry_id, "status": status},
                    aggregate=f"faq_entry:{entry_id}",
                )
            )
        if action == "reject":
            hint = d.REVIEW_REJECT_HINT_TEMPLATE.format(question=question)
        elif status == "negative":
            hint = d.REVIEW_PUBLISH_NEGATIVE_HINT_TEMPLATE.format(question=question)
        else:
            hint = d.REVIEW_PUBLISH_SERVE_HINT_TEMPLATE.format(question=question)
        return d.FaqReviewed(id=entry_id, status=status, version=version, hint=hint)

    # ---------- 端点 9：候选问题库 ----------

    async def candidates(self, *, status: str = "all") -> d.CandidateList:
        """候选清单（状态筛＋扫库态随行；total 恒全量、频次倒序——服务端排序）。"""
        if status not in d.CANDIDATE_FILTERS:
            raise d.FaqParamError(
                f"status 越界：{status}（允许值 {'|'.join(d.CANDIDATE_FILTERS)}）"
            )
        rows = await self._candidates.all()
        items = [self._candidate_item(r) for r in rows if self._candidate_matches(r, status)]
        running = await self._scans.running()
        latest_done = await self._scans.latest_done()
        return d.CandidateList(
            items=items,
            total=len(rows),
            scan=d.ScanPanel(
                running_task_id=running.id if running else None,
                last_hint=latest_done.hint if latest_done else None,
            ),
        )

    @staticmethod
    def _candidate_matches(row: CandidateRow, status: str) -> bool:
        """候选筛选语义（合同常量：dup＝非待比对且比对结论疑似重复；ok 含草稿态）。"""
        verdict = (row.compare or {}).get("verdict")
        if status == "all":
            return True
        if status == "pending":
            return row.status == "pending"
        if status == "dup":
            return row.status != "pending" and verdict == "dup"
        if status == "ok":
            return row.status in ("compared", "drafted") and verdict != "dup"
        if status == "drafted":
            return row.status == "drafted"
        if status == "published":
            return row.status == "published"
        return False

    @staticmethod
    def _candidate_item(row: CandidateRow) -> d.CandidateItem:
        compare = None
        if row.compare:
            compare = d.CompareResult(
                verdict=row.compare.get("verdict", ""),
                dup_question=row.compare.get("dup_question"),
                similarity=row.compare.get("similarity"),
                onto_hit=row.compare.get("onto_hit"),
                hint=row.compare.get("hint", ""),
            )
        return d.CandidateItem(
            id=row.id,
            question=row.question,
            variants=list(row.variants),
            freq=row.freq,
            window=row.window,
            status=row.status,
            compare=compare,
            draft=row.draft,
            hook=row.hook(),
        )

    # ---------- 端点 10/11：扫库异步长任务 ----------

    async def start_scan(self, *, actor_who: str) -> d.ScanHandle:
        """扫库受理（202）：全局单例——已有进行中任务再受理 409；只增候选不改库。"""
        running = await self._scans.running()
        if running is not None or self._runtime.tasks:
            raise d.FaqConflictError(
                "已有进行中的扫库任务——完成后才能再次发起", code="faq_scan_running"
            )
        task_id = d.new_scan_task_id(now())
        seq = 1
        taken = set(await self._scans.all_ids())
        while task_id in taken:
            seq += 1
            task_id = f"{d.new_scan_task_id(now())}-{seq}"
        await self._scans.insert(ScanTaskRow(id=task_id, status="running"))
        self._runtime.tasks[task_id] = asyncio.create_task(self._run_scan(task_id))
        return d.ScanHandle(task_id=task_id, status="running", hint=d.SCAN_RUNNING_HINT)

    async def scan_progress(self, task_id: str) -> d.ScanProgress:
        """扫库轮询：running 时空载荷；done 带新增簇＋完成提示（服务端组装）。"""
        row = await self._scans.get(task_id)
        if row is None:
            raise d.FaqNotFoundError(f"扫库任务不存在（或已过期清理）：{task_id}")
        clusters = [
            d.NewCluster(id=c["id"], question=c["question"], freq=int(c["freq"]))
            for c in row.new_clusters
        ]
        return d.ScanProgress(
            task_id=row.id,
            status=row.status,
            new_cluster_count=row.new_cluster_count,
            new_clusters=clusters if row.status == "done" else [],
            hint=row.hint if row.status == "done" else None,
        )

    async def close_stale_scans(self) -> int:
        """崩溃重启的遗留 running 扫库行收口为 done（幂等——否则 running 恒真、
        所有 start_scan 永久 409；gateway close_stale_drills 同款处置）。"""
        row = await self._scans.running()
        if row is None:
            return 0
        async with self._db.transaction() as session:
            stored = await session.get(ScanTaskRow, row.id)
            if stored is None or stored.status != "running":
                return 0
            stored.status = "done"
            stored.new_cluster_count = 0
            stored.new_clusters = []
            stored.hint = "应用重启——上次扫描中断收口，可重新发起扫库。"
            stored.finished_at = now()
            stored.updated_at = now()
        return 1

    async def _run_scan(self, task_id: str) -> None:
        """任务体：A1 历史会话 → LLM 挖掘（petro-main）→ 候选簇入库（pending）。"""
        try:
            if self._step_seconds:
                await asyncio.sleep(self._step_seconds)
            material: list[dict[str, str]] = []
            if self._session_loader is not None:
                material = list(await self._session_loader() or [])
            clusters: list[d.NewCluster] = []
            hint: str | None = None
            if material:
                clusters = await self._mine_clusters(material)
            else:
                hint = d.SCAN_EMPTY_MATERIAL_HINT  # A1 未上线——料源空态说明
            payload: list[dict[str, Any]] = []
            async with self._db.transaction() as session:
                taken = [row.id for row in await self._candidates.all(session)]
                for cluster in clusters:
                    cid = d.new_candidate_id(taken)
                    taken.append(cid)
                    await self._candidates.insert(
                        CandidateRow(
                            id=cid,
                            question=cluster.question,
                            variants=[],
                            freq=cluster.freq,
                            window=d.SCAN_WINDOW,
                            status="pending",
                        ),
                        session,
                    )
                    payload.append(
                        {"id": cid, "question": cluster.question, "freq": cluster.freq}
                    )
                row = await session.get(ScanTaskRow, task_id)
                if row is not None:
                    row.status = "done"
                    row.new_cluster_count = len(payload)
                    row.new_clusters = payload
                    row.hint = hint or d.scan_done_hint(clusters)
                    row.finished_at = now()
        except Exception as exc:
            LOGGER.exception("扫库任务失败：%s", task_id)
            async with self._db.transaction() as session:
                row = await session.get(ScanTaskRow, task_id)
                if row is not None:
                    row.status = "done"
                    row.new_cluster_count = 0
                    row.new_clusters = []
                    row.hint = f"扫描完成：本次新增 0 个候选簇——挖掘调用失败（{exc}），可重试。"
                    row.finished_at = now()
        finally:
            self._runtime.tasks.pop(task_id, None)
            if self._eventbus is not None:
                await self._eventbus.publish(
                    make_event(
                        "ScanCompleted",
                        {"task_id": task_id},
                        aggregate=f"faq_scan_task:{task_id}",
                    )
                )

    async def _mine_clusters(self, material: list[dict[str, str]]) -> list[d.NewCluster]:
        """LLM 看历史会话挖候选簇（B3-5 拍板；F60 晋升闸初值 SCAN_MIN_FREQ）。"""
        lines = "\n".join(
            f"- 问：{m.get('question', '')}｜答：{m.get('answer', '')}" for m in material
        )
        completion = await self._gateway.complete(
            DIGEST_ALIAS,
            [
                {"role": "system", "content": "你是油田数据问答平台的问句挖掘助手。"},
                {
                    "role": "user",
                    "content": (
                        "以下近 30 天用户真实提问及其回答，请聚类归纳成候选 FAQ 簇，"
                        '按 JSON 数组输出，元素形如 {"question": 簇代表问句, '
                        '"freq": 近30天出现次数, "variants": [同簇变体]}；只输出 JSON。\n\n'
                        + lines
                    ),
                },
            ],
            caller="faq.scan.mine",
        )
        body = str(getattr(completion, "content", completion))
        start, end = body.find("["), body.rfind("]")
        clusters: list[d.NewCluster] = []
        if start < 0 or end <= start:
            LOGGER.warning("扫库挖掘应答不可解析，按 0 簇处理")
            return clusters
        try:
            for item in json.loads(body[start : end + 1]):
                freq = int(item.get("freq", 0))
                question = str(item.get("question", "")).strip()
                if freq < SCAN_MIN_FREQ or not question:
                    continue  # F60：簇频次过阈值才进池——孤例不进池
                clusters.append(d.NewCluster(id="", question=question, freq=freq))
        except (ValueError, TypeError):
            LOGGER.warning("扫库挖掘应答不可解析，按 0 簇处理")
        return clusters

    # ---------- 端点 12：向量比对（三面去重——人工触发） ----------

    async def compare_candidate(self, candidate_id: str, *, actor_who: str) -> d.CandidateItem:
        """三面去重：既有问答/知识库（向量，高于合并线判 dup）＋本体（命中展示）。"""
        row = await self._candidates.get(candidate_id)
        if row is None:
            raise d.FaqNotFoundError(f"候选不存在：{candidate_id}")
        if row.status != "pending":
            raise d.FaqConflictError(
                f"仅待比对候选可比对：当前 {row.status}", code="faq_compare_state"
            )
        query = row.question
        faq_sim, faq_label = await self._best_match(query, await self._faq_face_texts())
        kb_sim, kb_label = await self._best_match(query, await self._kb_face_texts())
        dup_sim, dup_question = faq_sim, faq_label
        if kb_sim > dup_sim:
            dup_sim, dup_question = kb_sim, kb_label
        onto_hit = await self._ontology_hit(query)
        verdict = "dup" if dup_sim >= d.MERGE_THRESHOLD else "ok"
        if verdict == "dup":
            hint = (
                f"向量比对：与「{dup_question}」相似度 {dup_sim:.2f}——高于合并线，"
                "建议改用合并相似问，不新增条目。"
            )
        else:
            hint = "向量比对：与既有问答无重复。"
        if onto_hit:
            hint += f"本体命中：{onto_hit}。"
        compare = {
            "verdict": verdict,
            "dup_question": dup_question if verdict == "dup" else None,
            "similarity": round(dup_sim, 4) if verdict == "dup" else None,
            "onto_hit": onto_hit,
            "hint": hint,
        }
        async with self._db.transaction() as session:
            stored = await self._candidates.get(candidate_id, session)
            if stored is None:
                raise d.FaqNotFoundError(f"候选不存在：{candidate_id}")
            stored.status = "compared"
            stored.compare = compare
            stored.updated_at = now()
        row.status = "compared"
        row.compare = compare
        return self._candidate_item(row)

    async def _faq_face_texts(self) -> list[tuple[str, str]]:
        """既有问答面：只取索引可见（服务中）条目的问题＋相似问法。"""
        entries = await self._entries.all_entries()
        sims = await self._entries.all_sims()
        sims_by_entry: dict[str, list[str]] = {}
        for sim in sims:
            sims_by_entry.setdefault(sim.entry_id, []).append(sim.text)
        texts: list[tuple[str, str]] = []
        for entry in entries:
            if entry.status != "serve":
                continue
            texts.append((entry.question, entry.question))
            texts.extend((s, entry.question) for s in sims_by_entry.get(entry.id, []))
        return texts

    async def _kb_face_texts(self) -> list[tuple[str, str]]:
        """知识库面：kb 公开缝供出已向量化片段（faq 不直查 kb 表——聚合边界）。"""
        if self._kb_corpus_loader is None:
            return []
        return [(text, text) for text in await self._kb_corpus_loader()]

    async def _ontology_hit(self, query: str) -> str | None:
        """本体面命中展示串（值域：指标卡 · X / 术语 · X / 井对象 · X）。"""
        if self._ontology_names_loader is None:
            return None
        names = await self._ontology_names_loader()
        best: tuple[float, str] | None = None
        for label, name in names:
            if not name:
                continue
            if name in query or query in name:
                score = 1.0
            elif self._embedder is not None:
                vecs = await self._embedder.embed([query, name])
                score = _cosine(vecs[0], vecs[1])
            else:
                score = 0.0
            if score >= _ONTO_HIT_FLOOR and (best is None or score > best[0]):
                best = (score, f"{label} · {name}")
        return best[1] if best else None

    async def _best_match(
        self, query: str, texts: list[tuple[str, str]]
    ) -> tuple[float, str | None]:
        """查询与文本集的最高相似度（无向量缝时 0——判 ok 不误杀）。"""
        if not texts or self._embedder is None:
            return 0.0, None
        vectors = await self._embedder.embed([query] + [t for t, _ in texts])
        query_vec = vectors[0]
        best: tuple[float, str | None] = (0.0, None)
        for vec, (text, label) in zip(vectors[1:], texts, strict=True):
            score = _cosine(query_vec, vec)
            if score > best[0]:
                best = (score, label or text)
        return best

    # ---------- 端点 13：候选 LLM 起草 ----------

    async def draft_candidate(self, candidate_id: str, *, actor_who: str) -> d.CandidateDraft:
        """起草：dup 不关起草闸（草稿即劝阻文案）；ok 走 LLM＋溯源后缀＋挂接建议。"""
        row = await self._candidates.get(candidate_id)
        if row is None:
            raise d.FaqNotFoundError(f"候选不存在：{candidate_id}")
        if row.status != "compared":
            raise d.FaqConflictError(
                f"仅已比对候选可起草：当前 {row.status}", code="faq_draft_state"
            )
        compare = row.compare or {}
        onto_hit = compare.get("onto_hit")
        if compare.get("verdict") == "dup":
            draft = d.DUP_DRAFT_TEXT
            hook_suggestion = None  # dup 草稿无挂接（合同——劝阻文案不带挂接建议）
        else:
            hook_suggestion = _hook_from_onto_hit(onto_hit)
            completion = await self._gateway.complete(
                DIGEST_ALIAS,
                [
                    {"role": "system", "content": "你是油田数据问答平台的 FAQ 起草助手。"},
                    {
                        "role": "user",
                        "content": (
                            f"候选问句：「{row.question}」"
                            + (f"（同簇变体：{'、'.join(row.variants)}）" if row.variants else "")
                            + (f"；本体命中：{onto_hit}" if onto_hit else "")
                            + "。请基于该问题的历史回答归纳一段可直接入库的答案，"
                            "简明、口径准确；只输出答案正文。"
                        ),
                    },
                ],
                caller="faq.candidate.draft",
            )
            body = str(getattr(completion, "content", completion)).strip()
            source_label = onto_hit or "历史回答"
            draft = f"{body}（来源：{source_label} · {d.DRAFT_SOURCE_SUFFIX}）"
        async with self._db.transaction() as session:
            stored = await self._candidates.get(candidate_id, session)
            if stored is None:
                raise d.FaqNotFoundError(f"候选不存在：{candidate_id}")
            stored.status = "drafted"
            stored.draft = draft
            if hook_suggestion is not None:
                stored.hook_kind = hook_suggestion.kind
                stored.hook_name = hook_suggestion.name
            stored.updated_at = now()
        row.status = "drafted"
        row.draft = draft
        return d.CandidateDraft(
            id=candidate_id, status="drafted", draft=draft, hook_suggestion=hook_suggestion
        )

    # ---------- 端点 14：引用知识起草（台账口径/切片原文，可组合） ----------

    async def draft_from_refs(
        self, ledger_ref: d.LedgerRef | None, slice_ref: d.SliceRef | None
    ) -> d.DraftResult:
        """起草三源双轨：服务端直取台账/切片（不信任前端文本）；两 ref 全空 400。"""
        if ledger_ref is None and slice_ref is None:
            raise d.FaqParamError("台账口径与切片原文至少选一——两源全空不可起草")
        segments: list[str] = []
        hook_suggestion: d.Hook | None = None
        if ledger_ref is not None:
            if ledger_ref.kind not in ("metric", "term"):
                raise d.FaqParamError(
                    f"ledger_ref.kind 越界：{ledger_ref.kind}（允许值 metric|term）"
                )
            if self._ledger_loader is None:
                raise d.FaqParamError("台账口径读缝未装配——无法直取台账定义")
            loaded = await self._ledger_loader(ledger_ref.kind, ledger_ref.id)
            if loaded is None:
                raise d.FaqNotFoundError(
                    f"台账口径不存在：{ledger_ref.kind} #{ledger_ref.id}"
                )
            name, def_text, source_label = loaded
            segments.append(f"{def_text}（来源：{source_label}）")
            hook_suggestion = d.Hook(kind=ledger_ref.kind, name=name)
        if slice_ref is not None:
            if self._slice_loader is None:
                raise d.FaqParamError("切片原文读缝未装配——无法直取片段")
            slice_loaded = await self._slice_loader(slice_ref.report_id, slice_ref.fragment_id)
            if slice_loaded is None:
                raise d.FaqNotFoundError(
                    f"切片不存在：{slice_ref.fragment_id}（报告 {slice_ref.report_id}）"
                )
            text, source_label = slice_loaded
            segments.append(f"{text}（来源：{source_label}）")
        completion = await self._gateway.complete(
            DIGEST_ALIAS,
            [
                {"role": "system", "content": "你是油田数据问答平台的 FAQ 起草助手。"},
                {
                    "role": "user",
                    "content": (
                        "请基于以下所选知识起草一段可直接入库的答案；"
                        "逐段保留「（来源：…）」标注，整合连贯，不新增未给事实；"
                        "只输出答案正文。\n\n" + "\n".join(segments)
                    ),
                },
            ],
            caller="faq.draft.from_refs",
        )
        return d.DraftResult(
            draft=str(getattr(completion, "content", completion)).strip(),
            hook_suggestion=hook_suggestion,
        )

    # ---------- 端点 15：批量导入（两模式＋试校验＋四计数——00 §4.4） ----------

    async def import_library(
        self,
        *,
        mode: str,
        dry_run: bool,
        filename: str,
        file_bytes: bytes,
        actor_who: str,
    ) -> d.ImportStats:
        """模板列＝标准问/相似问法（多值）/负例问法/答案；append 合并重复、
        replace 清空现库；dry_run 仅校验不入库；文件落 MinIO 不过期（B3-8）。"""
        if mode not in ("append", "replace"):
            raise d.FaqParamError(f"mode 越界：{mode}（允许值 append|replace）")
        if not filename.lower().endswith(".csv"):
            raise d.FaqParamError(
                "导入暂支持 CSV 模板（xlsx 承载结合实际框架定——B3 开放问题 8）"
            )
        key = f"faq/import/{now():%Y%m%d%H%M%S}-{filename}"
        await self._storage.put_bytes(key, file_bytes)  # 业务资产不设过期
        rows = _parse_import_csv(file_bytes)
        staged: list[tuple[str, list[str], bool, str]] = []  # (question, sims, negative, answer)
        failures: list[d.ImportRowFailure] = []
        for line_no, record in rows:
            std_q = (record.get("标准问") or "").strip()
            neg_q = (record.get("负例问法") or "").strip()
            sim_raw = record.get("相似问法") or ""
            sims = [
                part.strip() for part in re.split(_SIM_SEPARATOR_PATTERN, sim_raw)
                if part.strip()
            ]
            answer = (record.get("答案") or "").strip()
            if neg_q:
                question, is_negative = neg_q, True  # 负例行：负例问法列承载问句
            elif std_q:
                question, is_negative = std_q, False
            else:
                failures.append(d.ImportRowFailure(row=line_no, reason="缺标准问列——模板列必填"))
                continue
            if not answer:
                failures.append(d.ImportRowFailure(row=line_no, reason="缺答案列——模板列必填"))
                continue
            staged.append((question, sims, is_negative, answer))
        failed = len(failures)
        if dry_run:
            added, merged, skipped = await self._import_plan(staged)
            return d.ImportStats(
                dry_run=True, added=added, merged=merged, skipped=skipped, failed=failed,
                failures=failures,
                hint=_import_hint(True, added, merged, skipped, failed, failures),
            )
        async with self._db.transaction() as session:
            if mode == "replace":
                # 清空现库（先确认由前端确认弹窗承担——服务端收到即执行）；
                # 候选回写锚随条目删除悬空（扫库只增候选不改库——不级联清候选）。
                for entry in await self._entries.all_entries(session):
                    await self._entries.delete_entry(entry.id, session)
            added, merged, skipped = await self._import_apply(session, staged)
        return d.ImportStats(
            dry_run=False, added=added, merged=merged, skipped=skipped, failed=failed,
            failures=failures,
            hint=_import_hint(False, added, merged, skipped, failed, failures),
        )

    async def _import_plan(
        self, staged: list[tuple[str, list[str], bool, str]]
    ) -> tuple[int, int, int]:
        """试校验计数（不入库）：与库内/批内归一化对账。"""
        entries = await self._entries.all_entries()
        sims = await self._entries.all_sims()
        known: set[str] = {e.question_norm for e in entries} | {s.text_norm for s in sims}
        added = merged = skipped = 0
        for question, row_sims, _neg, _answer in staged:
            norm = d.normalize_text(question)
            if norm in known:
                new_sims = [s for s in row_sims if d.normalize_text(s) not in known]
                if new_sims:
                    merged += 1
                    known.update(d.normalize_text(s) for s in new_sims)
                else:
                    skipped += 1  # 归一化后完全重复——原样保留
                continue
            added += 1
            known.add(norm)
            known.update(d.normalize_text(s) for s in row_sims)
        return added, merged, skipped

    async def _import_apply(
        self,
        session: AsyncSession,
        staged: list[tuple[str, list[str], bool, str]],
    ) -> tuple[int, int, int]:
        """正式导入（同事务）：同义并入既有条目（相似问增列）、完全重复跳过。"""
        entries = await self._entries.all_entries(session)
        sims = await self._entries.all_sims(session)
        by_norm: dict[str, str] = {e.question_norm: e.id for e in entries}
        for sim in sims:
            by_norm.setdefault(sim.text_norm, sim.entry_id)
        known: set[str] = set(by_norm)
        added = merged = skipped = 0
        for question, row_sims, is_negative, answer in staged:
            norm = d.normalize_text(question)
            target_id = by_norm.get(norm)
            new_sims = [s for s in row_sims if d.normalize_text(s) not in known]
            if target_id is not None:
                entry = await self._entries.get(target_id, session)
                if entry is None:
                    raise d.FaqNotFoundError(f"条目不存在：{target_id}")
                if not new_sims:
                    skipped += 1  # 归一化后完全重复——原样保留
                    continue
                for text in new_sims:
                    sim_id = await self._entries.next_sim_id(session)
                    await self._entries.insert_sim(
                        SimilarRow(
                            id=sim_id, entry_id=target_id, text=text,
                            text_norm=d.normalize_text(text),
                        ),
                        session,
                    )
                    known.add(d.normalize_text(text))
                await self._entries.bump_version(entry, session)
                merged += 1  # 同义并入既有条目（未建新条目）
                continue
            eid = await self._entries.next_entry_id(session)
            await self._entries.insert_entry(
                EntryRow(
                    id=eid,
                    question=question,
                    question_norm=norm,
                    norm_hash=d.norm_hash(question),
                    answer=answer,
                    status="pending_review",  # 审核流做齐——批量新增同走待审核
                    is_negative=is_negative,
                    hook_kind=None,
                    hook_name=None,
                    version=1,
                    maintainer="导入",
                ),
                session,
            )
            known.add(norm)
            by_norm[norm] = eid
            for text in new_sims:
                sim_id = await self._entries.next_sim_id(session)
                await self._entries.insert_sim(
                    SimilarRow(
                        id=sim_id, entry_id=eid, text=text,
                        text_norm=d.normalize_text(text),
                    ),
                    session,
                )
                sim_norm = d.normalize_text(text)
                known.add(sim_norm)
                by_norm.setdefault(sim_norm, eid)
            added += 1
        return added, merged, skipped

    # ---------- 端点 16：导出全库 ----------

    async def export_library(self) -> d.DownloadHandle:
        """导出列与导入模板对称（含相似问/负例列）；预签名 GET 小时级有效、
        对象本体不过期（B3-8）；负例行问句落「负例问法」列。"""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(d.EXPORT_COLUMNS)
        entries = await self._entries.all_entries()
        sims = await self._entries.all_sims()
        sims_by_entry: dict[str, list[str]] = {}
        for sim in sims:
            sims_by_entry.setdefault(sim.entry_id, []).append(sim.text)
        for entry in entries:
            row_sims = d.SIM_SEPARATOR_EXPORT.join(sims_by_entry.get(entry.id, []))
            writer.writerow([
                "" if entry.is_negative else entry.question,
                row_sims,
                entry.question if entry.is_negative else "",
                entry.answer,
            ])
        key = f"faq/export/{now():%Y%m%d%H%M%S}-faq-all.csv"
        await self._storage.put_bytes(key, buf.getvalue().encode("utf-8-sig"))
        url = await self._storage.presign_get(key)
        expires_at = (now() + timedelta(seconds=GET_TTL_SECONDS)).strftime(DISPLAY_FMT)
        return d.DownloadHandle(
            download_url=url,
            expires_at=expires_at,
            columns=list(d.EXPORT_COLUMNS),
            hint="已导出 FAQ 全库（含相似问/负例列）——可线下编辑后重新导入。",
        )

    # ---------- 运行时读口（A1 消费，不经 HTTP） ----------

    async def match_index(self, text: str) -> d.FaqHit | None:
        """FAQ 索引读口（六路匹配器 FAQ 路——F56②）：只认服务中条目（v0.2 审核
        流）；归一化精确命中问题/相似问法；向量路随 A1 装配批接线（seam 留注）。"""
        norm = d.normalize_text(text)
        if not norm:
            return None
        entries = await self._entries.all_entries()
        by_id = {e.id: e for e in entries}
        for sim in await self._entries.all_sims():
            entry = by_id.get(sim.entry_id)
            if entry is not None and entry.status == "serve" and sim.text_norm == norm:
                return d.FaqHit(entry_id=entry.id, question=entry.question, answer=entry.answer)
        for entry in entries:
            if entry.status == "serve" and entry.question_norm == norm:
                return d.FaqHit(entry_id=entry.id, question=entry.question, answer=entry.answer)
        return None

    async def search_similar(self, text: str, top_k: int) -> list[d.FaqHit]:
        """FAQ 相似问检索（P1-08b 检索链 FAQ 路扩检——qa_behavior.faq_expand_rounds
        消费点的候选供给面）：服务中条目的问题＋相似问法与查询做向量余弦
        （LocalHashEmbedder 占位缝——与三面去重比对同源同实现），按分倒序取
        top_k；只服务中条目可达（待审核/已停用/负例均不可达——v0.2 审核流）。"""
        query = d.normalize_text(text)
        if not query or top_k <= 0 or self._embedder is None:
            return []
        entries = await self._entries.all_entries()
        sims = await self._entries.all_sims()
        sims_by_entry: dict[str, list[str]] = {}
        for sim in sims:
            sims_by_entry.setdefault(sim.entry_id, []).append(sim.text)
        serving = [e for e in entries if e.status == "serve"]
        if not serving:
            return []
        faces: list[tuple[str, str]] = []
        for entry in serving:
            faces.append((entry.question, entry.question))
            faces.extend((s, entry.question) for s in sims_by_entry.get(entry.id, []))
        vectors = await self._embedder.embed([query] + [t for t, _ in faces])
        query_vec = vectors[0]
        best: dict[str, tuple[float, str]] = {}
        for vec, (_face, label) in zip(vectors[1:], faces, strict=True):
            score = _cosine(query_vec, vec)
            current = best.get(label)
            if current is None or score > current[0]:
                best[label] = (score, label)
        ranked = sorted(best.items(), key=lambda pair: pair[1][0], reverse=True)[:top_k]
        by_question = {e.question: e for e in serving}
        out: list[d.FaqHit] = []
        for question, (score, _label) in ranked:
            hit_entry = by_question.get(question)
            if hit_entry is None:
                continue
            out.append(d.FaqHit(
                entry_id=hit_entry.id, question=hit_entry.question, answer=hit_entry.answer,
                score=round(score, 4),
            ))
        return out

    # ---------- LedgerMerged 消费（B3-2：口径修订联动） ----------

    async def on_ledger_merged(self, event: DomainEvent) -> None:
        """C1 口径修订生效 → 按 hook 检出受影响条目 → LLM 起草修订/停用建议 →
        落待审核行进审核流（端点 17 人工确认）；不自动直改。"""
        payload = dict(event.payload)
        kind = str(payload.get("kind", ""))
        name = str(payload.get("name") or payload.get("term") or payload.get("metric") or "")
        if kind not in ("metric", "term") or not name:
            LOGGER.warning("LedgerMerged 载荷不可解析，联动跳过：%s", payload)
            return
        entries = await self._entries.all_entries()
        affected = [
            e for e in entries
            if e.status == "serve" and e.hook_kind == kind and e.hook_name == name
        ]
        for entry in affected:
            completion = await self._gateway.complete(
                DIGEST_ALIAS,
                [
                    {"role": "system", "content": "你是油田数据问答平台的口径修订助手。"},
                    {
                        "role": "user",
                        "content": (
                            f"台账口径「{name}」（{kind}）已完成修订并生效。"
                            f"FAQ 条目「{entry.question}」的答案挂接该口径，当前答案："
                            f"「{entry.answer}」。请起草一条修订建议（修订后的答案，"
                            "或建议停用本条目），简明扼要；只输出建议正文。"
                        ),
                    },
                ],
                caller="faq.ledger_merged.suggestion",
            )
            body = str(getattr(completion, "content", completion)).strip()
            created = await self.create_entry(
                entry.question,
                f"{body}（口径修订联动 · LLM 建议稿——请人工核实）",
                is_negative=False,
                hook=d.Hook(kind=kind, name=name),
                source_candidate_id=None,
                actor_who="系统",
            )
            if self._audit is not None:
                await self._audit.audit(
                    AuditRow(
                        who="系统",
                        action="faq.ledger_merged.suggestion",
                        content=(
                            f"口径修订联动：台账「{name}」生效——为条目 {entry.id} "
                            f"起草建议稿 {created.id}（待审核），不自动直改"
                        ),
                        at=event.occurred_at,
                    )
                )


def _hook_from_onto_hit(onto_hit: Any) -> d.Hook | None:
    """本体命中展示串 → 挂接建议（指标卡/术语可挂；井对象无 hook 语义）。"""
    if not isinstance(onto_hit, str) or " · " not in onto_hit:
        return None
    label, name = onto_hit.split(" · ", 1)
    if label == "指标卡":
        return d.Hook(kind="metric", name=name)
    if label == "术语":
        return d.Hook(kind="term", name=name)
    return None


def _import_hint(
    dry_run: bool,
    added: int,
    merged: int,
    skipped: int,
    failed: int,
    failures: list[d.ImportRowFailure],
) -> str:
    """导入结果提示（合同模板——失败原因人话汇总；无失败省略括注）。"""
    prefix = "试校验通过（未入库）：可新增" if dry_run else "导入完成：新增"
    body = f"{prefix} {added} · 合并 {merged} · 跳过 {skipped} · 失败 {failed}"
    if failures:
        reasons: dict[str, int] = {}
        for failure in failures:
            reasons[failure.reason] = reasons.get(failure.reason, 0) + 1
        detail = "；".join(f"{count} 行{reason}" for reason, count in reasons.items())
        body += f"（失败原因：{detail}）"
    return body + "。"


def _parse_import_csv(file_bytes: bytes) -> list[tuple[int, dict[str, str]]]:
    """CSV 模板解析（utf-8/utf-8-sig 自适应；行号从模板数据行起计 1）。"""
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise d.FaqParamError("导入文件为空——模板列：标准问/相似问法/负例问法/答案")
    missing = [c for c in d.IMPORT_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise d.FaqParamError(
            f"模板列缺失：{'、'.join(missing)}（模板列：标准问/相似问法/负例问法/答案）"
        )
    return [
        (line_no, {k: (v or "") for k, v in row.items() if k})
        for line_no, row in enumerate(reader, start=1)
    ]

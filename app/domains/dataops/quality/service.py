"""domains.dataops.quality.service —— E2 质检台服务（薄编排：语义在 domain）。

公开面（E2 册 v0.5——M-05a 管理面＋M-05b 执行通道）：
- ``list_rules``：规则列表（端点 1——投影 quality_rule 种子，20 条含 13-20
  仅登记 enabled=false，判据权威源＝本体 M3，文本固化在 DP-05 迁移 0015）；
- ``set_rule_enabled``：规则启停（端点 2——写 quality_rule.enabled，停用＝
  任务跳过不删；数据面限写账号对此表只读，本域＝唯一写口，DP-05 同源裁决；
  B12 审计由 api 层在成功返回后落笔）；
- ``accept_task``：任务受理（端点 3——QT-YYYYMMDD-NN 当日序号＋running/step=0
  落行即触发面：任务表轮询形态，数据面 worker 按管道节奏拾取执行——DP-04
  交付形态适配，接口合同＝quality_task 行形零共享库；单任务进行中重入 409；
  重跑语义＝先撤「分发未认领」动态单再受理，v0.5 在途单保护）；
- ``get_task``：任务轮询（端点 4——running 直读；done 且 step=2（数据面跑批
  完、建单/分发未接续）→ 服务端接续＝命中逐条建单（挂单去重＋隔离行身份
  对位回挂）→ step=4 分发完成，接续＋认领＋步推进同事务原子（F4）；report
  展示串读侧拼装（DP-05 偏差 3 机器值→合同 DTO 形）；
- ``list_tasks``：任务历史（端点 5——完成记录 time 倒序，running 不进历史）；
- ``list_issues``：问题单列表（端点 6）；``transition_issue``：五态流转＋复扫
  （端点 7——rescan 执行缝：缺省未接 501，生产装配见 channel.py 适配器）；
- ``register_hit``：挂单语义（端点 4 接续与外部触发源共用——（规则＋对象＋
  数据日期）去重、在途单保护；并发窗 IntegrityError 单次重试自愈，F4）；
- ``freshness``／``list_quarantine``：水位 T-1 判定（端点 8）与隔离区
  append-only 读（端点 9）。

审计分工（B12/行为约定 5）：流转留痕行（quality_issue_transition）在本事务
落库；平台审计（security.audit）由 api 层成功路径统一写（retrieval/P0-05
gateway 先例——失败路径不达审计行）——任务受理/接续审计行随端点 3/4 落笔。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.domains.dataops.quality.domain import (
    DISTRIBUTION_OWNER,
    LANE_CLOSED,
    LANE_REVIEW,
    LANES,
    RESCAN_ACTION,
    WATER_LAYER_DISPLAY,
    WATER_TIER_ORDER,
    FollowupReceipt,
    FreshnessView,
    HitReceipt,
    IssueListPage,
    IssueView,
    QrowView,
    QualityCloseBlockedError,
    QualityIssueNotFoundError,
    QualityIssueStateError,
    QualityParamError,
    QualityRuleNotFoundError,
    QualityTaskChannelDeferredError,
    QualityTaskNotFoundError,
    QualityTaskRunningError,
    QuarantineView,
    RescanExecutor,
    RescanRequest,
    RuleToggleReceipt,
    RuleView,
    TaskAcceptedReceipt,
    TaskRecordView,
    TaskStatusView,
    TransitionReceipt,
    VerifyView,
    build_dedupe_key,
    freshness_judgment,
    hit_identity,
    hit_line,
    hit_render,
    is_verify_green,
    next_lane,
    rescan_note,
    scan_display,
    task_display_id,
)
from app.domains.dataops.quality.store import (
    QualityIssue,
    QualityStore,
    QualityTask,
    QuarantineRow,
)
from app.infra.clock import DISPLAY_FMT, now
from app.infra.db import ConnectionManager

_ISSUE_ID_MAX_LEN = 32  # quality_issue.id 列宽（DP-05 0015）


def _verify_view(verify: dict[str, object] | None) -> VerifyView | None:
    """verify jsonb → 值对象（键缺/形状坏如实 None——不造批次号）。"""
    if not verify:
        return None
    batch = verify.get("batch")
    note = verify.get("note")
    if not isinstance(batch, str) or not isinstance(note, str):
        return None
    return VerifyView(batch=batch, note=note)


def _payload_note(payload: dict[str, object] | None) -> str | None:
    """坏行自带说明（payload["note"] 键约定——非串值如实 None，不硬转）。"""
    note = (payload or {}).get("note")
    return note if isinstance(note, str) else None


class QualityService:
    """质检台服务（薄）：编排 store；状态机/判定语义在 domain。"""

    def __init__(
        self, db: ConnectionManager, rescan_executor: RescanExecutor | None = None
    ) -> None:
        self._db = db
        self._store = QualityStore(db)
        self._rescan = rescan_executor  # 增量复扫执行缝——缺省未接＝501（生产装配 channel.py）

    def bind_rescan_executor(self, executor: RescanExecutor) -> None:
        """复扫执行缝生产绑定（M-05b——组合根 main.py 专用两段装配；测试注入
        走构造参数替身）。绑定后复核态复扫走数据面质检通道适配器（B9 缝
        运行期只见 callable，形状不变——M-05a rev 偏差 4「只换注入不改形状」）。"""
        self._rescan = executor

    # ---------- 端点 1：规则列表 ----------

    async def list_rules(self) -> list[RuleView]:
        """规则全行投影（13-20 仅登记 enabled=false——DP-05 种子固化，读侧不加工）。"""
        return [
            RuleView(
                no=row.no, kind=row.kind, rule=row.rule, crit=row.crit,
                enabled=bool(row.enabled), action=row.action, auto_fix=bool(row.autofix),
            )
            for row in await self._store.list_rules()
        ]

    # ---------- 端点 2：规则启停 ----------

    async def set_rule_enabled(self, no: int, enabled: bool) -> RuleToggleReceipt:
        """启停（停用＝质检任务跳过不删——规则不删除；幂等重复置位照收）。"""
        if not await self._store.set_rule_enabled(no, enabled):
            raise QualityRuleNotFoundError(f"质检规则不存在：no={no}")
        return RuleToggleReceipt(no=no, enabled=enabled)

    # ---------- 端点 6：问题单列表 ----------

    async def list_issues(
        self,
        *,
        lane: int | None = None,
        rule_no: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> IssueListPage:
        """问题单分页（五态筛选＋规则筛选；V1 数据量小整表返回，信封先预留）。"""
        result = await self._store.page_issues(
            lane=lane, rule_no=rule_no, page=page, page_size=page_size
        )
        rows = list(result.items)
        crit_by_no = {
            row.no: row.crit for row in await self._store.list_rules()
        }
        qrows_map = await self._store.qrows_by_issue([row.id for row in rows])
        items = [
            self._issue_view(row, crit_by_no.get(row.rule_no), qrows_map.get(row.id, []))
            for row in rows
        ]
        return IssueListPage(
            lanes=LANES, items=items,
            page=result.page, page_size=result.page_size, total=result.total,
        )

    def _issue_view(
        self,
        row: QualityIssue,
        crit: str | None,
        qrows: list[QuarantineRow],
    ) -> IssueView:
        """问题单行投影：ai_note＝规则判据说明（服务端投影——v0.5 降级零 LLM）；
        qrows.note＝坏行 payload 自带说明（payload["note"] 键约定——隔离表无
        note 列（DP-05 列形），说明随坏行原样落 payload，无则如实 None）。"""
        ai_note = f"规则 {row.rule_no} 判据：{crit}" if crit is not None else None
        return IssueView(
            id=row.id, lane=int(row.lane), rule_no=int(row.rule_no),
            hit_count=int(row.hit_count), title=row.title, desc=row.desc,
            owner=row.owner,
            qrows=[QrowView(loc=q.loc, note=_payload_note(q.payload)) for q in qrows],
            ai_note=ai_note,
            verify=_verify_view(row.verify),
            close_note=row.close_note,
        )

    # ---------- 端点 7：五态流转＋复扫 ----------

    async def transition_issue(
        self, issue_id: str, operator: str, *, action: str | None = None
    ) -> TransitionReceipt:
        """流转到下一态（分发→认领→整改→复核→关闭；终态 409）。

        - ``action="rescan"``：复扫不是流转（lane 不变）——仅复核态可复扫
          （409）；执行缝缺省未接＝501（执行通道归 M-05b，不 mock 假结论）；
          接通后回填 verify（全绿哨兵/仍有命中＋明细）。
        - 推进到「复核」仅登记待复扫（verify 不动——v0.5 降级，自动复扫挂观察）。
        - 推进到「关闭」守卫：verify 复扫全绿或 close_note 免修原因，二者皆无
          422（合同端点 7 冻结状态码）。
        - 每次流转写留痕行（seq 递增，操作人/时间/前后态——与 A3 审计同口径）。
        """
        if action is not None and action != RESCAN_ACTION:
            raise QualityParamError(f"未知动作：{action!r}（仅支持 {RESCAN_ACTION!r}）")
        issue = await self._store.get_issue(issue_id)
        if issue is None:
            raise QualityIssueNotFoundError(f"问题单不存在：{issue_id}")
        if action == RESCAN_ACTION:
            return await self._rescan_issue(issue, operator)
        return await self._advance_issue(issue, operator)

    async def _advance_issue(self, issue: QualityIssue, operator: str) -> TransitionReceipt:
        """线性推进一态＋留痕行（同事务原子）。

        并发窗（M-07 F-02——M-05a rev F4 义务在流转写点的落地）：守卫与复检
        全部挪入写会话，行锁寻单（``session.get(..., with_for_update=True)``
        ——同域 register_hit ``find_by_dedupe_key`` 先例；sqlite 无此语义单写
        串行，PG 实锁）；锁内 lane 与受理快照不一致＝对手方已并发流转——本路
        409 拒绝，不双写 lane、不留同距留痕行（丢更新/留痕失真零发生）。
        """
        async with self._db.session() as session:
            managed = await session.get(QualityIssue, issue.id, with_for_update=True)
            assert managed is not None  # 闸后必在（同库同键）
            current = int(managed.lane)  # 锁内复检——现行值说话，非受理快照
            if current != int(issue.lane):
                raise QualityIssueStateError(
                    f"问题单 {issue.id} 状态已并发流转"
                    f"（受理快照 lane={int(issue.lane)}，锁内现行 lane={current}）"
                    "——请刷新后重试"
                )
            if current == LANE_CLOSED:
                raise QualityIssueStateError(
                    f"问题单 {issue.id} 已关闭——终态不可流转（留痕在案）"
                )
            target = next_lane(current)
            if target == LANE_CLOSED and not (
                is_verify_green(_verify_view(managed.verify)) or managed.close_note
            ):
                raise QualityCloseBlockedError(
                    f"问题单 {issue.id} 复验未全绿——修正批次复扫通过"
                    "（或记录免修关闭原因）后才可关闭"
                )
            managed.lane = target
            seq = await self._store.max_transition_seq(session, issue.id) + 1
            await self._store.append_transition(
                session, issue_id=issue.id, seq=seq,
                from_lane=current, to_lane=target, operator=operator,
            )
        return TransitionReceipt(
            issue_id=issue.id, lane=target, verify=_verify_view(managed.verify)
        )

    async def _rescan_issue(self, issue: QualityIssue, operator: str) -> TransitionReceipt:
        """人工触发复扫（lane 不变；verify 回填——全绿结论/仍有命中＋明细）。"""
        if int(issue.lane) != LANE_REVIEW:
            raise QualityIssueStateError(
                f"问题单 {issue.id} 仅复核态可复扫（当前 {LANES[int(issue.lane)]}）"
            )
        if self._rescan is None:
            raise QualityTaskChannelDeferredError(
                f"问题单 {issue.id} 复扫执行通道随数据面质检重建接通（M-05b）"
                "——不 mock 假复扫结论"
            )
        outcome = await self._rescan(
            RescanRequest(issue_id=issue.id, rule_no=int(issue.rule_no))
        )
        verify = {"batch": outcome.batch, "note": rescan_note(outcome.green, outcome.detail)}
        async with self._db.session() as session:
            managed = await session.get(QualityIssue, issue.id)
            assert managed is not None
            managed.verify = verify
        return TransitionReceipt(
            issue_id=issue.id, lane=int(issue.lane),
            verify=VerifyView(batch=outcome.batch, note=verify["note"]),
        )

    # ---------- 挂单语义（端点 4 接续与外部触发源共用） ----------

    async def register_hit(
        self,
        *,
        rule_no: int,
        object_key: str,
        data_date: str,
        title: str,
        desc: str | None = None,
        owner: str | None = None,
        quarantine_row_ids: list[int] | None = None,
    ) -> HitReceipt:
        """命中登记（挂单去重——v0.2/v0.5 行为约定 4）。

        同一问题按（规则＋对象＋数据日期）去重：既有单（任意在途态——在途单
        保护，跨轮不清）追加 hit_count+1 不新建；无既有单才建单（初始态分发 0，
        责任岗文案由触发源按规则配置给定——本域不发明岗位映射）。命中带隔离行
        时回挂 issue_id（qrows 可追溯）。建单/挂单留痕审计随触发源。
        并发窗（F4 义务）：行锁寻单（FOR UPDATE）＋同键/同号撞唯一键时整事务
        回滚单次重试——重试即走挂同单路径（对手方行已可见），两次皆撞如实抛。
        """
        dedupe_key = build_dedupe_key(rule_no, object_key, data_date)
        rule = await self._store.get_rule(rule_no)
        if rule is None:
            raise QualityRuleNotFoundError(f"命中规则不在规则库：rule_no={rule_no}")
        try:
            async with self._db.session() as session:
                return await self._register_hit_locked(
                    session, rule_no=rule_no, dedupe_key=dedupe_key, title=title,
                    desc=desc, owner=owner, quarantine_row_ids=quarantine_row_ids,
                )
        except IntegrityError:  # 并发建单撞 uq dedupe_key/单号 PK——重试一次自愈
            async with self._db.session() as session:
                return await self._register_hit_locked(
                    session, rule_no=rule_no, dedupe_key=dedupe_key, title=title,
                    desc=desc, owner=owner, quarantine_row_ids=quarantine_row_ids,
                )

    async def _register_hit_locked(
        self,
        session: Any,
        *,
        rule_no: int,
        dedupe_key: str,
        title: str,
        desc: str | None,
        owner: str | None,
        quarantine_row_ids: list[int] | None,
    ) -> HitReceipt:
        """挂单语义会话内体（public register_hit 与端点 4 接续共用——同事务
        原子；寻单带行锁——F4「守卫复检挪写会话/对 issue 行加锁」落点）。"""
        existing = await QualityStore.find_by_dedupe_key(
            session, dedupe_key, for_update=True
        )
        if existing is not None:
            existing.hit_count = int(existing.hit_count) + 1
            await QualityStore.attach_quarantine_rows(
                session, existing.id, list(quarantine_row_ids or [])
            )
            return HitReceipt(
                issue_id=existing.id, attached=True,
                hit_count=int(existing.hit_count), lane=int(existing.lane),
            )
        issue_id = await QualityStore.next_dynamic_issue_id(session)
        if len(issue_id) > _ISSUE_ID_MAX_LEN:  # pragma: no cover — 列宽内不可能
            raise QualityParamError(f"动态单号超列宽：{issue_id}")
        issue = QualityIssue(
            id=issue_id, lane=0, rule_no=rule_no, hit_count=1,
            dedupe_key=dedupe_key, title=title, desc=desc, owner=owner,
            ai_note=None, verify=None, close_note=None, created_at=now(),
        )
        await QualityStore.add_issue(session, issue)
        await QualityStore.attach_quarantine_rows(
            session, issue_id, list(quarantine_row_ids or [])
        )
        return HitReceipt(issue_id=issue_id, attached=False, hit_count=1, lane=0)

    # ---------- 端点 3：任务受理（任务表轮询形态——落行即触发面） ----------

    async def accept_task(self, *, clear_stale: bool = True) -> TaskAcceptedReceipt:
        """任务受理（端点 3——QT-YYYYMMDD-NN 当日序号；running/step=0 落行）。

        - 触发面：任务表轮询形态（DP-04 交付＝APScheduler worker 管道）——本
          受理行即数据面拾取请求（接口合同＝quality_task 行形，零共享库；拾取
          半边＝数据面 worker 按其管道节奏轮询 step=0 行，施工归数据面仓票）。
        - 单任务闸（合同端点 3「重入 409」）：守卫复检在写会话内（F4 义务；
          残余竞窗＝两并发受理皆见无在途——PK 兜底＋审计留痕，登记备案）。
        - 重跑语义（v0.5）：受理前撤「分发未认领」动态单（d 前缀＋lane 0），
          在途单/预置单不触碰；复扫通道受理走 clear_stale=False（复扫不是重跑）。
        - rules_count＝受理时刻启用集快照（行为约定 1「按发起时刻启用集执行」）。
        """
        day = now().strftime("%Y%m%d")
        try:
            async with self._db.session() as session:
                running = await QualityStore.running_task_ids(session)
                if running:
                    raise QualityTaskRunningError(
                        f"已有质检任务进行中：{'、'.join(running)}"
                        "——同一时刻最多一个任务进行中，重入 409"
                    )
                cleared = (
                    await QualityStore.clear_unclaimed_dynamic_issues(session)
                    if clear_stale
                    else 0
                )
                rules_count = await QualityStore.count_enabled_rules(session)
                seq = await QualityStore.count_tasks_of_day(session, day) + 1
                task_id = task_display_id(seq, day)
                session.add(QualityStore.new_task(task_id, rules_count=rules_count))
        except IntegrityError as exc:  # 并发受理撞当日序号 PK——同事务回滚无脏数据
            raise QualityTaskRunningError(
                "任务号并发取号碰撞（当日序号已被并发受理占用）——请重试"
            ) from exc
        return TaskAcceptedReceipt(task_id=task_id, rules_count=rules_count, cleared=cleared)

    # ---------- 端点 4：任务轮询（done→接续）与端点 5：历史 ----------

    async def get_task(self, task_id: str) -> TaskStatusView:
        """任务轮询（端点 4）：running 直读；done 且 step=2 → 接续后重读投影。

        接续（v0.5 行为约定 4 触发源）：命中逐条建单/挂单（身份对位回挂隔离行）
        ＋step→4——认领（条件 UPDATE 原子闸）、建单、步推进同事务提交（F4），
        并发轮询互斥（输者 followup=None 直读不重复建单）。
        """
        row = await self._store.get_task(task_id)
        if row is None:
            raise QualityTaskNotFoundError(f"质检任务不存在：{task_id}")
        followup: FollowupReceipt | None = None
        if row.status == "done" and int(row.step or 0) == 2:
            followup = await self._followup(task_id)
            row = await self._store.get_task(task_id)
            assert row is not None  # 接续事务后必在（同库同键）
        return TaskStatusView(
            task_id=row.id,
            status=row.status,
            step=int(row.step) if row.step is not None else None,
            task=self._task_record(row) if row.status == "done" else None,
            followup=followup,
        )

    async def list_tasks(self) -> list[TaskRecordView]:
        """任务历史（端点 5——完成记录倒序；running 在途不进历史，原型同形）。"""
        return [
            self._task_record(row) for row in await self._store.list_done_tasks()
        ]

    async def _followup(self, task_id: str) -> FollowupReceipt | None:
        """接续事务（DP-05 偏差 2 注记的 E2 侧 step 3/4：建单→分发一步落）。

        认领＝条件 UPDATE（done 且 step=2）原子闸，rowcount 说话：输者 None
        （他端已接续/在接续）；赢者同事务完成建单/挂单＋隔离行身份对位回挂＋
        step→4。异常即整事务回滚（step 退回 2——下次轮询重做，自愈无脏数据）。
        """
        async with self._db.session() as session:
            if not await QualityStore.claim_task_followup(session, task_id):
                return None
            row = await session.get(QualityTask, task_id)
            assert row is not None
            report = dict(row.report or {})
            entries = [e for e in report.get("hits", []) if isinstance(e, dict)]
            created = attached = linked = 0
            for entry in entries:
                rule_no = entry.get("rule_no")
                kind = entry.get("kind")
                if not isinstance(rule_no, int):
                    continue  # 形坏条目如实跳过（不硬转不造假单）
                by_key: dict[str, HitReceipt] = {}
                for loc in entry.get("sample") or []:
                    if not isinstance(loc, dict):
                        continue
                    ident = hit_identity(loc)
                    key = build_dedupe_key(rule_no, *ident)
                    if key in by_key:
                        continue
                    render = hit_render(loc)
                    by_key[key] = await self._register_hit_locked(
                        session, rule_no=rule_no, dedupe_key=key,
                        title=f"规则 {rule_no} · {kind or '命中'} · {render}",
                        desc=f"任务 {task_id} 命中定位：{render}",
                        owner=DISTRIBUTION_OWNER,
                        quarantine_row_ids=None,
                    )
                created += sum(1 for r in by_key.values() if not r.attached)
                attached += sum(1 for r in by_key.values() if r.attached)
                for qrow in await QualityStore.quarantine_rows_of_task_rule(
                    session, task_id, rule_no
                ):
                    qkey = build_dedupe_key(rule_no, *hit_identity(qrow.payload or {}))
                    receipt = by_key.get(qkey)
                    if receipt is not None:
                        qrow.issue_id = receipt.issue_id  # 回挂列＝唯一可写列
                        linked += 1
            await QualityStore.finish_task_followup(session, task_id)
        return FollowupReceipt(created=created, attached=attached, rows_linked=linked)

    def _task_record(self, row: QualityTask) -> TaskRecordView:
        """任务行 → 记录投影（report 机器值→合同 DTO 展示形——DP-05 偏差 3）。"""
        return TaskRecordView(
            id=row.id,
            time=row.time.strftime(DISPLAY_FMT),
            rules=int(row.rules_count) if row.rules_count is not None else None,
            hits=int(row.hits) if row.hits is not None else None,
            report=self._report_display(row.report),
        )

    @staticmethod
    def _report_display(report: dict[str, Any] | None) -> dict[str, Any] | None:
        """报告 jsonb → 合同端点 4 DTO 形（scanned/hits 展示串读侧拼装——键形
        照抄合同示例：range/scanned/quarantined_rows/rejected_batches/hits/verdict）。"""
        if report is None:
            return None
        entries = [e for e in (report.get("hits") or []) if isinstance(e, dict)]
        return {
            "range": report.get("range"),
            "scanned": scan_display(report.get("scanned_rows")),
            "quarantined_rows": report.get("quarantined_rows"),
            "rejected_batches": report.get("rejected_batches"),
            "hits": [hit_line(i, e) for i, e in enumerate(entries, 1)],
            "verdict": report.get("verdict"),
        }

    # ---------- 端点 8：水位 ----------

    async def freshness(self, today: date | None = None) -> list[FreshnessView]:
        """三 tier 水位（固定 tier 序；T-1 判定后端算——缺层如实不出现）。"""
        at = today or now().date()
        by_layer = {row.layer: row for row in await self._store.list_water_lines()}
        views: list[FreshnessView] = []
        for tier in WATER_TIER_ORDER:
            row = by_layer.get(tier)
            if row is None:
                continue  # 水位未回写层——如实缺行（不造达标假象）
            tag, color, _late = freshness_judgment(row.data_date, at)
            views.append(
                FreshnessView(
                    layer=WATER_LAYER_DISPLAY.get(tier, tier),  # 汇总层→汇总层（问数用）
                    to=f"到 {row.data_date.isoformat()}",
                    promise=row.promise,
                    tag=tag,
                    color=color,
                )
            )
        return views

    # ---------- 端点 9：隔离区 ----------

    async def list_quarantine(
        self,
        *,
        batch_id: str | None = None,
        rule_no: int | None = None,
        issue_id: str | None = None,
    ) -> list[QuarantineView]:
        """隔离区 append-only 读（三过滤可组合；created_at 展示串 R2）。"""
        return [
            QuarantineView(
                batch_id=row.batch_id, rule_no=int(row.rule_no), action=row.action,
                loc=row.loc, payload=dict(row.payload or {}), issue_id=row.issue_id,
                created_at=row.created_at.strftime(DISPLAY_FMT),
            )
            for row in await self._store.list_quarantine(
                batch_id=batch_id, rule_no=rule_no, issue_id=issue_id
            )
        ]

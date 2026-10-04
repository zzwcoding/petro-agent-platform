"""domains.dataops.quality.service —— E2 质检台管理面服务（薄编排：语义在 domain）。

公开面（E2 册 v0.5 管理面半边——M-05a；执行通道端点 3/4/5 归 M-05b）：
- ``list_rules``：规则列表（端点 1——投影 quality_rule 种子，20 条含 13-20
  仅登记 enabled=false，判据权威源＝本体 M3，文本固化在 DP-05 迁移 0015）；
- ``set_rule_enabled``：规则启停（端点 2——写 quality_rule.enabled，停用＝
  任务跳过不删；数据面限写账号对此表只读，本域＝唯一写口，DP-05 同源裁决；
  B12 审计由 api 层在成功返回后落笔）；
- ``list_issues``：问题单列表（端点 6——lane/rule_no 筛选＋分页预留信封；
  ai_note 服务端投影规则判据（v0.5 降级——零 LLM），qrows 由隔离区 issue_id
  回挂行装配）；
- ``transition_issue``：五态流转＋复扫动作（端点 7——复核仅登记/rescan 回填
  verify/关闭守卫 422/终态 409/流转留痕行）；
- ``register_hit``：挂单语义（v0.2/v0.5——（规则＋对象＋数据日期）去重，
  重复命中追加既有单 hit_count+1 不新建；无既有单才建单初始态分发）——
  服务端语义归本域状态机，触发源＝M-05b 执行通道；
- ``freshness``／``list_quarantine``：水位 T-1 判定（端点 8）与隔离区
  append-only 读（端点 9）。

审计分工（B12/行为约定 5）：流转留痕行（quality_issue_transition）在本事务
落库；平台审计（security.audit）由 api 层成功路径统一写（retrieval/P0-05
gateway 先例——失败路径不达审计行）。
"""

from __future__ import annotations

from datetime import date

from app.domains.dataops.quality.domain import (
    LANE_CLOSED,
    LANE_REVIEW,
    LANES,
    RESCAN_ACTION,
    WATER_LAYER_DISPLAY,
    WATER_TIER_ORDER,
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
    QuarantineView,
    RescanExecutor,
    RescanRequest,
    RuleToggleReceipt,
    RuleView,
    TransitionReceipt,
    VerifyView,
    build_dedupe_key,
    freshness_judgment,
    is_verify_green,
    next_lane,
    rescan_note,
)
from app.domains.dataops.quality.store import (
    QualityIssue,
    QualityStore,
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
    """质检台管理面服务（薄）：编排 store；状态机/判定语义在 domain。"""

    def __init__(
        self, db: ConnectionManager, rescan_executor: RescanExecutor | None = None
    ) -> None:
        self._db = db
        self._store = QualityStore(db)
        self._rescan = rescan_executor  # 增量复扫执行缝——M-05b 接数据面质检通道

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
        """线性推进一态＋留痕行（同事务原子）。"""
        current = int(issue.lane)
        if current == LANE_CLOSED:
            raise QualityIssueStateError(
                f"问题单 {issue.id} 已关闭——终态不可流转（留痕在案）"
            )
        target = next_lane(current)
        if target == LANE_CLOSED and not (
            is_verify_green(_verify_view(issue.verify)) or issue.close_note
        ):
            raise QualityCloseBlockedError(
                f"问题单 {issue.id} 复验未全绿——修正批次复扫通过"
                "（或记录免修关闭原因）后才可关闭"
            )
        async with self._db.session() as session:
            managed = await session.get(QualityIssue, issue.id)
            assert managed is not None  # 闸后必在（同库同键）
            managed.lane = target
            seq = await self._store.max_transition_seq(session, issue.id) + 1
            await self._store.append_transition(
                session, issue_id=issue.id, seq=seq,
                from_lane=current, to_lane=target, operator=operator,
            )
        return TransitionReceipt(issue_id=issue.id, lane=target, verify=_verify_view(issue.verify))

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

    # ---------- 挂单语义（M-05b 执行通道触发源消费） ----------

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
        时回挂 issue_id（qrows 可追溯）。建单/挂单留痕审计随触发源（M-05b）。
        """
        dedupe_key = build_dedupe_key(rule_no, object_key, data_date)
        rule = await self._store.get_rule(rule_no)
        if rule is None:
            raise QualityRuleNotFoundError(f"命中规则不在规则库：rule_no={rule_no}")
        async with self._db.session() as session:
            existing = await self._store.find_by_dedupe_key(session, dedupe_key)
            if existing is not None:
                existing.hit_count = int(existing.hit_count) + 1
                await self._store.attach_quarantine_rows(
                    session, existing.id, list(quarantine_row_ids or [])
                )
                return HitReceipt(
                    issue_id=existing.id, attached=True,
                    hit_count=int(existing.hit_count), lane=int(existing.lane),
                )
            issue_id = await self._store.next_dynamic_issue_id(session)
            if len(issue_id) > _ISSUE_ID_MAX_LEN:  # pragma: no cover — 列宽内不可能
                raise QualityParamError(f"动态单号超列宽：{issue_id}")
            issue = QualityIssue(
                id=issue_id, lane=0, rule_no=rule_no, hit_count=1,
                dedupe_key=dedupe_key, title=title, desc=desc, owner=owner,
                ai_note=None, verify=None, close_note=None, created_at=now(),
            )
            await self._store.add_issue(session, issue)
            await self._store.attach_quarantine_rows(
                session, issue_id, list(quarantine_row_ids or [])
            )
            return HitReceipt(issue_id=issue_id, attached=False, hit_count=1, lane=0)

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

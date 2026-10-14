"""domains.gateway.service —— 网关域服务：编排 llm_client seam 与 store（语义在 domain.py）。

V2 复制层（V2-01 自 V1 app/domains/gateway/service.py 复制清理——仅模块
路径 app.* → appv2.*，语义逐字节同形；V1 业务域 caller 残留零——complete
caller 由调用方传入归因，域内仅自产 caller="gateway.drill"）。

公开面照 98 §3.12 卡 D1 面：complete / models / gateway_config /
save_gateway_config / spend_logs / spend_stats（D1 v0.2 端点 8——D5 归并）/
start_drill / drill / drill_history。（D5 面 10 方法随 D5 撤页归并收编——
聚合读面归端点 8，预算双阈值读写归端点 2/3 config 族。）

运行态与持久态分工：
- RouterState（冷却/熔断位）＝进程内运行态（熔断位单向置位不自动恢复；
  进程重启即清——账本是持久真源，冷却语义本就是「一段时间内」）；
- gateway_spend_record / gateway_drill_run / gateway_budget_config＝PG 持久态。
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import ValidationError

from appv2.infra.clock import ISO_FMT, now
from appv2.infra.config import (
    GatewayParamsSpec,
    get_models_config,
    read_models_yaml_text,
    upsert_gateway_params,
)
from appv2.infra.db import ConnectionManager
from appv2.infra.gateway import domain as d
from appv2.infra.gateway.calllog import record_call
from appv2.infra.gateway.store import BudgetStore, DrillRun, DrillStore, SpendRecord, SpendStore
from appv2.infra.llm_client import LlmCompletion, UpstreamUnavailable

LOGGER = logging.getLogger("domains.gateway")

# 域级参数键：complete(**params) 里归网关域消费（记账备注/归属槽），不转发上游
# （litellm 不识未知业务键——转发前剥除，P0-05 审查收口；run_id 归属槽 V2-33
# ——run 归属链写账，调用面 GraphRunExecutor 经 completer 协议上行）。
_DOMAIN_ONLY_PARAMS: frozenset[str] = frozenset({"note", "run_id"})

# 进程崩溃重启后遗留 running 演练行的收口 summary（lifespan 启动时调用一次，
# 幂等；双态合同 running|done 不新增第三态——收口即 done 带人话原因）。
_STALE_DRILL_SUMMARY = "进程中断收口：平台重启前演练任务未及终态，按双态合同收口 done"


class CompletionBackend(Protocol):
    """上游调用 seam（生产装配＝infra.llm_client.LlmClient；测试注入桩——B6 唯一消费方）。"""

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        timeout_seconds: float,
        max_tokens: int = 4096,
        **params: Any,
    ) -> LlmCompletion: ...


class _DynamicGate:
    """全局 LLM 并发门——动态尺寸版（DE-14）：acquire 时刻读当前配置判额。

    替换 asyncio.Semaphore 直用（G-06 原门尺寸在首次 complete 构造时定格，
    改 stream.llm_max_concurrency 需重启——挂账清单 §E1）：
    - 放大：即时生效——每次 acquire 先按现配置对账等待队列（_wake），有额即放。
    - 缩小：已在途调用不中断（照常释放）；新调用按新额排队——release 时按
      新额从队首依次占额唤醒（FIFO 公平，不插队）。
    - 排队语义与 G-06 一致：超限排队等而非挂死（不拒绝、不报错）。

    并发正确性建立在事件循环单线程模型上：acquire 快路径／_wake／release 均
    无 await（同步段原子），唯一挂起点是排队等 future。唤醒即占额（releaser
    代排队者 +1 再 set_result）——醒来即已持额，无唤醒后重判竞态。取消安全：
    排队中被取消摘队即可（额度未占）；已被占额唤醒后取消则回吐额度再让位。

    配置读取走 get_models_config() 内存缓存（廉路径，DE-14 票面裁决：不节流）。
    """

    def __init__(self, limit_fn: Callable[[], int]) -> None:
        self._limit_fn = limit_fn
        self._in_flight = 0
        self._waiters: deque[asyncio.Future[None]] = deque()

    def _limit(self) -> int:
        return max(1, int(self._limit_fn()))

    def current_limit(self) -> int:
        """当前生效上限（随配置热加载变动——测试与诊断面）。"""
        return self._limit()

    def locked(self) -> bool:
        """无即时可用额度（asyncio.Semaphore 同名语义——满额即锁）。"""
        return self._in_flight >= self._limit()

    async def acquire(self) -> None:
        self._wake()  # 先对账队列：放大生效点（新额先把队首等待者放进——FIFO 不插队）
        if self._in_flight < self._limit() and not self._waiters:
            self._in_flight += 1
            return
        fut: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._waiters.append(fut)
        try:
            await fut
        except asyncio.CancelledError:
            if fut.cancelled():
                # 仍在排队即被取消：额度未占，摘队即可（_wake 也会跳过已 done 的 future）
                if fut in self._waiters:
                    self._waiters.remove(fut)
            else:
                # 已被占额唤醒但任务随即取消：回吐额度并让下一位（防额度泄漏）
                self._in_flight -= 1
                self._wake()
            raise

    def release(self) -> None:
        self._in_flight -= 1
        self._wake()

    def _wake(self) -> None:
        """按当前限额从队首依次占额唤醒（FIFO；排队期间已取消者跳过不占额）。"""
        while self._waiters and self._in_flight < self._limit():
            fut = self._waiters.popleft()
            if fut.done():  # 排队期间被取消——额度留给在队者
                continue
            self._in_flight += 1
            fut.set_result(None)

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(self, *exc_info: object) -> None:
        self.release()


class GatewayService:
    """网关域服务（运行时唯一 LLM 出口 complete 在此——B6 的域侧守门人）。"""

    def __init__(
        self,
        db: ConnectionManager,
        backend: CompletionBackend,
        *,
        config_path: Path | None = None,
        drill_step_seconds: float = 0.6,
    ) -> None:
        self._db = db
        self._backend = backend
        self._config_path = config_path
        self._drill_step_seconds = drill_step_seconds
        self._spend = SpendStore(db)
        self._drills = DrillStore(db)
        self._budget = BudgetStore(db)
        self._router = d.RouterState()
        self._fault_alias: str | None = None  # 演练注入：临时摘主模型路由（ADR-0003 裁决 13）
        self._llm_gate: _DynamicGate | None = None  # G-06 全局 LLM 并发闸（DE-14 动态尺寸——懒建）
        self._drill_tasks: set[asyncio.Task[None]] = set()
        self._drill_gate = asyncio.Lock()  # 重入 409 的进程内双保险（DB 判据为准）

    # ---------- 运行时唯一 LLM 出口（98 §3.12 complete——B6） ----------

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> d.Completion:
        """全平台模型调用唯一入口：别名路由→fallback→记账→熔断判据。

        - 切换判据（椒图蓝本）：网络错/超时/5xx 切备；4xx/429 不切（直抛调用方）；
          per-attempt 超时＝config.request_timeout；同别名重试 num_retries 次
          （重试耗尽才计一次别名失败——LiteLLM Router allowed_fails 口径）。
        - 记账自动落（调用粒度账本唯一）；落账后查预算双阈值，触顶置熔断位
          （改路由不拒绝——后续调用整体改降级组 petro-lite，在途照跑完）。
        - params 的 run_id（V2-33）＝run 归属槽：记账落 SpendRecord.run_id 既有列
          （零迁移），空串/缺省归一 NULL；域级键剥除后不转发上游。
        """
        config = get_models_config()
        requested = alias or config.routing.default
        at = now()
        candidates = self._router.route_candidates(
            config.routing.fallback_order,
            groups={m.alias: m.group for m in config.models},
            requested=requested,
            at=at,
        )
        if not candidates:
            raise d.NoAvailableRoute(requested)

        timeout = float(config.gateway.request_timeout)
        retries = config.gateway.num_retries
        if self._llm_gate is None:
            # DE-14：动态并发门懒建——尺寸不定格，acquire 时刻读现配置判额
            # （改 stream.llm_max_concurrency 热加载后即生效，无需重启）。
            self._llm_gate = _DynamicGate(
                lambda: get_models_config().stream.llm_max_concurrency
            )
        gate = self._llm_gate
        # 域级键剥除后再转发上游（note＝记账备注槽归网关域消费，litellm 不识）
        forward = {k: v for k, v in params.items() if k not in _DOMAIN_ONLY_PARAMS}
        attempted: list[str] = []  # 本次调用内失败/被摘的别名（切换留痕）
        last_error: UpstreamUnavailable | None = None
        for candidate in candidates:
            if self._fault_alias is not None and candidate == self._fault_alias:
                # 演练注入：主模型路由被摘——不产生上游流量，计一次别名失败
                attempted.append(self._deploy(candidate))
                self._router.record_failure(
                    candidate, config.gateway.allowed_fails, config.gateway.cooldown_seconds, now()
                )
                LOGGER.warning("gateway 演练注入：别名 %s 路由摘除（计失败）", candidate)
                continue
            answer: LlmCompletion | None = None
            for _attempt in range(1 + retries):
                try:
                    # G-06：全局并发闸在此收口——排队等而非挂死（含支路并发）；
                    # DE-14：尺寸随配置热加载（acquire 判现额，缩不中断在途）。
                    async with gate:
                        try:
                            answer = await self._backend.complete(
                                candidate,
                                messages,
                                timeout_seconds=timeout,
                                **forward,
                            )
                        except Exception as exc:
                            # V2-80f 调用留痕：失败尝试（429/超时/5xx）同样全量记录。
                            record_call(
                                alias=candidate,
                                caller=caller,
                                run_id=str(params.get("run_id") or ""),
                                messages=messages,
                                requested=requested,
                                error=f"{type(exc).__name__}: {exc}",
                            )
                            raise
                        # V2-80f 调用留痕：发送 messages＋返回全文（旁路观测——
                        # 写失败降级不影响调用；LLM_CALL_LOG=off 关闭）。
                        record_call(
                            alias=candidate,
                            caller=caller,
                            run_id=str(params.get("run_id") or ""),
                            messages=messages,
                            requested=requested,
                            content=answer.content,
                            prompt_tokens=answer.prompt_tokens,
                            completion_tokens=answer.completion_tokens,
                            duration_ms=answer.duration_ms,
                        )
                    break
                except UpstreamUnavailable as exc:  # 网络错/超时/5xx——可重试可切备
                    last_error = exc
                    LOGGER.warning(
                        "gateway 上游不可用 alias=%s（%s），第 %d 次尝试",
                        candidate,
                        exc.reason,
                        _attempt + 1,
                    )
            if answer is None:  # 重试耗尽：计一次别名失败，切下一候选
                attempted.append(self._deploy(candidate))
                self._router.record_failure(
                    candidate, config.gateway.allowed_fails, config.gateway.cooldown_seconds, now()
                )
                continue
            return await self._settle(
                requested=requested,
                served_alias=candidate,
                answer=answer,
                attempted=attempted,
                caller=caller,
                params=params,
            )
        raise d.NoAvailableRoute(requested) from last_error

    async def _settle(
        self,
        *,
        requested: str,
        served_alias: str,
        answer: LlmCompletion,
        attempted: list[str],
        caller: str,
        params: dict[str, Any],
    ) -> d.Completion:
        """成功应答收口：记账落账→熔断判据→业务应答。"""
        config = get_models_config()
        prices = config.prices.get("default")
        if prices is None:
            # Owner 裁决单价是唯一计价真源（models.yaml prices.default）——缺失即
            # 部署配置错误，fail-fast 拒绝记账（静默兜底硬编码＝真源出现第二份）。
            raise RuntimeError(
                "models.yaml prices.default 缺失——Owner 裁决单价真源未装配，拒绝记账"
                "（部署配置错误，修复 models.yaml 后重试）"
            )
        cost = d.cost_yuan(
            answer.prompt_tokens,
            answer.completion_tokens,
            d.PriceSpec(
                input_per_mtok=prices.input_per_mtok,
                output_per_mtok=prices.output_per_mtok,
            ),
        )
        model_key = "main" if served_alias == config.routing.default else "backup"
        at = now()
        run_id = str(params.get("run_id") or "").strip()  # V2-33 归属槽：空串归一 NULL
        row = SpendRecord(
            id=d.new_call_id(),
            time=at,
            model_key=model_key,
            alias=served_alias,
            input_tokens=answer.prompt_tokens,
            output_tokens=answer.completion_tokens,
            # 非流式调用 TTFT 不可观测——first_ms 落 total_ms 同值（差异登记 README P0-05）
            first_ms=answer.duration_ms,
            total_ms=answer.duration_ms,
            cost_yuan=cost,
            fallback=served_alias != requested,
            note=d.default_note(caller, params.get("note")),
            caller=caller,  # 调用方归因落列（D1 v0.2 端点 4/8——complete 受理即归因）
            run_id=run_id or None,  # run 归属链写账（既有列零迁移——V2-33 补环）
            served_model=answer.model,
            attempted_fallbacks=attempted or None,
        )
        await self._spend.add(row)
        self._router.record_success(served_alias)
        await self._maybe_latch_fuse(cost)
        return d.Completion(
            content=answer.content,
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
            usage_estimated=answer.usage_estimated,
            call_id=row.id,
            cost_yuan=cost,
            fallback=row.fallback,
            served_alias=served_alias,
        )

    async def _maybe_latch_fuse(self, call_cost: float) -> None:
        """预算双阈值判据（F2 改注；触顶＝改路由不拒绝，熔断位单向置位不自动恢复）。"""
        if self._router.fuse_latched:
            return
        per_call_limit, monthly_limit = await self._budget.limits()
        tripped = call_cost > per_call_limit
        if not tripped:
            tripped = await self._spend.month_total(now()) > monthly_limit
        if tripped:
            self._router.fuse_latched = True
            # 领域事件 FuseTripped 的进程内落点（→链路 fused 留痕随 D5 面批）
            LOGGER.warning(
                "FuseTripped：花费触顶（单笔 %.4f / 上限 %.2f）——后续调用改路由降级组 %s",
                call_cost,
                per_call_limit,
                d.DEGRADE_GROUP,
            )

    def _deploy(self, alias: str) -> str:
        """别名 → 部署形 provider/model（切换留痕 failed_deploy/failover_target 口径）。"""
        for entry in get_models_config().models:
            if entry.alias == alias:
                return f"{entry.provider}/{entry.model}"
        return alias

    # ---------- D1 网关面（端点 1–7） ----------

    def models(self) -> d.ModelRegistryView:
        """D1 端点 1：模型清单＋网关运行态（页头徽标——三态判定单源在 RouterState.status）。"""
        config = get_models_config()
        status = self._router.status(
            config.routing.default, config.routing.fallback_order, now()
        )
        return d.project_models(
            config.models,
            config.routing.default,
            config.routing.fallback_order,
            status=status,
        )

    async def gateway_config(self) -> d.GatewayParamsView:
        """D1 端点 2：读取调用参数＋预算双阈值＋配置文件全文（密钥保持 ${VAR} 占位符）。"""
        spec = get_models_config().gateway
        per_call, monthly = await self._budget.limits()
        return d.GatewayParamsView(
            params=d.GatewayParams(
                allowed_fails=spec.allowed_fails,
                cooldown_seconds=spec.cooldown_seconds,
                num_retries=spec.num_retries,
                request_timeout=spec.request_timeout,
            ),
            budget=d.BudgetThresholds(
                per_call_cost_limit_yuan=per_call,
                gateway_budget_yuan_per_month=monthly,
            ),
            yaml=read_models_yaml_text(self._config_path),
        )

    async def save_gateway_config(
        self, params: d.GatewayParams, budget: d.BudgetThresholds
    ) -> d.GatewayParamsView:
        """D1 端点 3：校验→写回 models.yaml gateway 段→热加载；预算双阈值落单例行。

        生效语义（00 §13 档①直改即生效）：对后续调用生效、不回溯在途；预算
        双阈值直接保存即生效（D1 v0.2——complete 每次现读判据）；热加载失败
        即抛 ConfigWriteError（api 层映射 500 需回滚提示）。
        """
        validated_budget = d.BudgetThresholds.validated(budget.as_mapping())
        validated = d.GatewayParams.validated(params.as_mapping())
        try:
            spec: GatewayParamsSpec = upsert_gateway_params(
                validated.as_mapping(), self._config_path
            ).gateway
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            # 写失败与热加载失败（yaml 坏/模型校验不过）同收口——500 需回滚提示；
            # 原子替换下文件仍是旧全文（P0-05 审查收口），可安全回退重试
            raise d.ConfigWriteError(f"配置写回失败：{exc}") from exc
        await self._budget.save(
            validated_budget.per_call_cost_limit_yuan,
            validated_budget.gateway_budget_yuan_per_month,
        )
        per_call, monthly = await self._budget.limits()  # 保存后快照为唯一真值
        return d.GatewayParamsView(params=d.GatewayParams(
            allowed_fails=spec.allowed_fails,
            cooldown_seconds=spec.cooldown_seconds,
            num_retries=spec.num_retries,
            request_timeout=spec.request_timeout,
        ), budget=d.BudgetThresholds(
            per_call_cost_limit_yuan=per_call,
            gateway_budget_yuan_per_month=monthly,
        ), yaml=read_models_yaml_text(self._config_path))

    async def spend_logs(
        self,
        spend_filter: d.SpendFilter,
        *,
        page: int = 1,
        page_size: int = 15,
    ) -> d.SpendLogPage:
        """D1 端点 4：记账流水分页（排序恒 time 倒序；数据形状红线在 SpendView）。"""
        result = await self._spend.page(spend_filter.validated(), page=page, page_size=page_size)
        return d.SpendLogPage(
            items=result.items,
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    async def spend_stats(
        self,
        stats_filter: d.SpendStatsFilter,
        *,
        page: int = 1,
        page_size: int = 15,
    ) -> d.SpendStatsPage:
        """D1 端点 8（D5 归并）：花费聚合/趋势读面——账本唯一真源的聚合投影。"""
        return await self._spend.stats(
            stats_filter.validated(), page=page, page_size=page_size
        )

    # ---------- 故障演练（D1 端点 5/6/7——演练即真实流量） ----------

    async def start_drill(self) -> d.DrillHandle:
        """D1 端点 5：受理 202；重入 409。演练任务由服务端驱动（00 §5 双态）。"""
        async with self._drill_gate:
            if await self._drills.has_running():
                raise d.DrillConflictError("已有进行中的演练任务（重入 409）")
            config = get_models_config()
            params = config.gateway
            run = DrillRun(
                id=d.new_drill_id(),
                status="running",
                nodes=[n.as_dict() for n in d.build_drill_nodes(params.allowed_fails)],
                started_at=now(),
            )
            await self._drills.create(run)
            # 受理时配置快照整体传任务体：节点列按受理时 allowed_fails 构建，
            # 任务体索引必须与节点列同源（运行时热加载改配置不影响已受理演练
            # ——防「节点列旧/索引新」的 IndexError 竞态，P0-05 审查收口）。
            task = asyncio.create_task(self._run_drill(run.id, params, config.routing.default))
            self._drill_tasks.add(task)
            task.add_done_callback(self._drill_tasks.discard)
            return d.DrillHandle(drill_id=run.id)

    async def close_stale_drills(self) -> int:
        """启动收口：遗留 running 演练行（进程崩溃重启的僵尸）→ done＋人话 summary。

        演练任务体是进程内 asyncio task（98 §4 说演练是 infra.queue 消费方
        ——P0-08 才建，先手搓，差异登记 README P0-05）：进程死了任务必死，
        DB 行却遗留 running → has_running() 恒真 → 所有 start_drill 永久
        409。lifespan 启动时收口一次；幂等（无 running 行即 0），重复调用安全。
        """
        closed = await self._drills.close_stale_running(summary=_STALE_DRILL_SUMMARY)
        if closed:
            LOGGER.warning("gateway 启动收口：%d 条遗留 running 演练行置 done", closed)
        return closed

    async def drill(self, drill_id: str) -> d.DrillProgress:
        """D1 端点 6：轮询进度与结果（不存在/已过期 → DrillNotFoundError→404）。"""
        run = await self._drills.get(drill_id)
        if run is None:
            raise d.DrillNotFoundError(f"演练任务不存在：{drill_id}")
        return d.DrillProgress(
            drill_id=run.id,
            status=run.status,  # type: ignore[arg-type]  # CHECK 约束保双态
            nodes=list(run.nodes),
            result=run.result,
        )

    async def drill_history(self) -> list[d.DrillSummary]:
        """D1 端点 7：演练历史倒序（summary 含阈值与冷却参数）。"""
        return await self._drills.history()

    async def _run_drill(self, drill_id: str, params: GatewayParamsSpec, main: str) -> None:
        """演练任务体：注入 N 次主用失败→冷却→备用真应答一次→落两笔账。

        节点节奏由本任务驱动（step 缺省 0.6s/步，测试可注入 0——演示节奏
        不入合同，00 §5.2）；注入步不产生上游流量，最后一步是真实调用。
        params/main＝受理时快照（start_drill 传入）——节点列按受理时
        allowed_fails 构建，索引同源；不回读运行时配置（热加载竞态隔离）。
        """
        run = await self._drills.get(drill_id)
        if run is None:  # 理论不可达（受理即落行）
            return
        nodes = [d.DrillNode(**node) for node in run.nodes]
        try:
            self._fault_alias = main  # 平台侧开关：临时摘主模型路由（ADR-0003 裁决 13）

            # ① N 次注入失败：驱动 allowed_fails 状态机直至主用进冷却（无上游流量）
            cooldown_tripped = False
            for i, node in enumerate(nodes[: params.allowed_fails]):
                node.state = d.NODE_PROCESS
                await self._save_nodes(run, nodes)
                tripped = self._router.record_failure(
                    main, params.allowed_fails, params.cooldown_seconds, now()
                )
                cooldown_tripped = cooldown_tripped or tripped
                node.state = d.NODE_ERROR
                node.note = f"演练注入：主模型路由摘除，第 {i + 1} 次失败（无上游流量）"
                await self._save_nodes(run, nodes)
                await asyncio.sleep(self._drill_step_seconds)

            # ② 主备切换：真实调用一次（主用冷却中→备用承载）——记账由 complete 自动落
            fallback_node = nodes[params.allowed_fails]
            fallback_node.state = d.NODE_PROCESS
            await self._save_nodes(run, nodes)
            completion = await self.complete(
                main, [{"role": "user", "content": d.DRILL_PROMPT}],
                caller="gateway.drill", max_tokens=1024,
            )
            fallback_node.state = d.NODE_FINISH
            served = self._deploy(completion.served_alias)
            fallback_node.note = (
                f"主用进入冷却 {params.cooldown_seconds}s，备用 {served} 应答正常"
            )
            await self._save_nodes(run, nodes)
            if not cooldown_tripped and not completion.fallback:
                raise RuntimeError("演练未产生主备切换（路由状态机未触发冷却）")

            # ③ 记账落账节点：取刚落的账本行（done 落两笔账之第一笔）
            ledger_node = nodes[params.allowed_fails + 1]
            ledger_view = await self._spend.get(completion.call_id)
            if ledger_view is None:
                raise RuntimeError(f"演练记账行缺失：{completion.call_id}")
            ledger_node.state = d.NODE_FINISH
            ledger_node.note = f"记账流水 +1（fallback=true，¥{completion.cost_yuan:.4g}）"
            await self._save_nodes(run, nodes)

            # ④ 结果与历史（第二笔账）：consecutive_fails/cooldown_sec 取配置值
            # （受理快照）——合同原文
            at = now()
            result = d.DrillResult(
                conclusion=(
                    f"主用停机期间备用应答正常：注入 {params.allowed_fails} 次失败后主用进入冷却 "
                    f"{params.cooldown_seconds}s，流量自动切换至备用线路，"
                    "演练期间账本落备用应答流水 1 条。"
                ),
                fallback=d.FallbackDetail(
                    time=at.strftime(ISO_FMT),
                    event="fallback_triggered",
                    request_alias=main,
                    failed_deploy=self._deploy(main),
                    failover_target=self._deploy(completion.served_alias),
                    consecutive_fails=params.allowed_fails,
                    cooldown_sec=params.cooldown_seconds,
                ),
                ledger_row=ledger_view,
            )
            run.result = result.as_dict()
            run.summary = (
                f"演练：主用连续失败 {params.allowed_fails} 次（阈值 {params.allowed_fails}，"
                f"冷却 {params.cooldown_seconds}s）→ 备用应答正常，账本 +1 条备用流水"
                f"（¥{completion.cost_yuan:.4g}）"
            )
        except Exception as exc:
            LOGGER.exception("gateway 演练失败 drill=%s", drill_id)
            for node in nodes:
                if node.state == d.NODE_PROCESS:
                    node.state = d.NODE_ERROR
                    node.note = f"失败：{exc}"
            run.result = None
            run.summary = (
                f"演练失败：{exc}（阈值 {params.allowed_fails}，冷却 {params.cooldown_seconds}s）"
            )
        finally:
            self._fault_alias = None  # 演练开关复位
            run.status = "done"
            run.finished_at = now()
            run.nodes = [n.as_dict() for n in nodes]
            await self._drills.save(run)

    async def _save_nodes(self, run: DrillRun, nodes: list[d.DrillNode]) -> None:
        run.nodes = [n.as_dict() for n in nodes]
        await self._drills.save(run)

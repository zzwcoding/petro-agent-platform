"""domains.gateway.service —— 网关域服务：编排 llm_client seam 与 store（语义在 domain.py）。

公开面照 98 §3.12 卡 D1 面：complete / models / gateway_config /
save_gateway_config / spend_logs / start_drill / drill / drill_history。
（D5 面 10 方法属阶段 1 D5 页票——本票不越界。）

运行态与持久态分工：
- RouterState（冷却/熔断位）＝进程内运行态（熔断位单向置位不自动恢复；
  进程重启即清——账本是持久真源，冷却语义本就是「一段时间内」）；
- gateway_spend_record / gateway_drill_run / gateway_budget_config＝PG 持久态。
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Protocol

from app.domains.gateway import domain as d
from app.domains.gateway.store import BudgetStore, DrillRun, DrillStore, SpendRecord, SpendStore
from app.infra.clock import ISO_FMT, now
from app.infra.config import (
    GatewayParamsSpec,
    get_models_config,
    read_models_yaml_text,
    upsert_gateway_params,
)
from app.infra.db import ConnectionManager
from app.infra.llm_client import LlmCompletion, UpstreamUnavailable

LOGGER = logging.getLogger("domains.gateway")


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
                    answer = await self._backend.complete(
                        candidate,
                        messages,
                        timeout_seconds=timeout,
                        **params,
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
        cost = d.cost_yuan(
            answer.prompt_tokens,
            answer.completion_tokens,
            d.PriceSpec(
                input_per_mtok=prices.input_per_mtok if prices else 1.0,
                output_per_mtok=prices.output_per_mtok if prices else 3.0,
            ),
        )
        model_key = "main" if served_alias == config.routing.default else "backup"
        at = now()
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
        """D1 端点 1：模型清单＋网关运行态（页头徽标）。"""
        config = get_models_config()
        at = now()
        in_cooldown = [self._router.in_cooldown(a, at) for a in config.routing.fallback_order]
        status = "running"
        if all(in_cooldown) and in_cooldown:
            status = "down"
        elif self._router.in_cooldown(config.routing.default, at):
            status = "degraded"
        return d.project_models(
            config.models,
            config.routing.default,
            config.routing.fallback_order,
            status=status,
        )

    def gateway_config(self) -> d.GatewayParamsView:
        """D1 端点 2：读取调用参数＋配置文件全文（密钥保持 ${VAR} 占位符）。"""
        spec = get_models_config().gateway
        return d.GatewayParamsView(
            params=d.GatewayParams(
                allowed_fails=spec.allowed_fails,
                cooldown_seconds=spec.cooldown_seconds,
                num_retries=spec.num_retries,
                request_timeout=spec.request_timeout,
            ),
            yaml=read_models_yaml_text(self._config_path),
        )

    def save_gateway_config(self, params: d.GatewayParams) -> d.GatewayParamsView:
        """D1 端点 3：校验→写回 models.yaml gateway 段→热加载→返回保存后快照。

        生效语义（00 §13 档①直改即生效）：对后续调用生效、不回溯在途；
        热加载失败即抛 ConfigWriteError（api 层映射 500 需回滚提示）。
        """
        validated = d.GatewayParams.validated(params.as_mapping())
        try:
            spec: GatewayParamsSpec = upsert_gateway_params(
                validated.as_mapping(), self._config_path
            ).gateway
        except OSError as exc:
            raise d.ConfigWriteError(f"配置写回失败：{exc}") from exc
        return d.GatewayParamsView(params=d.GatewayParams(
            allowed_fails=spec.allowed_fails,
            cooldown_seconds=spec.cooldown_seconds,
            num_retries=spec.num_retries,
            request_timeout=spec.request_timeout,
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

    # ---------- 故障演练（D1 端点 5/6/7——演练即真实流量） ----------

    async def start_drill(self) -> d.DrillHandle:
        """D1 端点 5：受理 202；重入 409。演练任务由服务端驱动（00 §5 双态）。"""
        async with self._drill_gate:
            if await self._drills.has_running():
                raise d.DrillConflictError("已有进行中的演练任务（重入 409）")
            params = get_models_config().gateway
            run = DrillRun(
                id=d.new_drill_id(),
                status="running",
                nodes=[n.as_dict() for n in d.build_drill_nodes(params.allowed_fails)],
                started_at=now(),
            )
            await self._drills.create(run)
            task = asyncio.create_task(self._run_drill(run.id))
            self._drill_tasks.add(task)
            task.add_done_callback(self._drill_tasks.discard)
            return d.DrillHandle(drill_id=run.id)

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

    async def _run_drill(self, drill_id: str) -> None:
        """演练任务体：注入 N 次主用失败→冷却→备用真应答一次→落两笔账。

        节点节奏由本任务驱动（step 缺省 0.6s/步，测试可注入 0——演示节奏
        不入合同，00 §5.2）；注入步不产生上游流量，最后一步是真实调用。
        """
        run = await self._drills.get(drill_id)
        if run is None:  # 理论不可达（受理即落行）
            return
        config = get_models_config()
        params = config.gateway
        main = config.routing.default
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

            # ④ 结果与历史（第二笔账）：consecutive_fails/cooldown_sec 取当前配置值——合同原文
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

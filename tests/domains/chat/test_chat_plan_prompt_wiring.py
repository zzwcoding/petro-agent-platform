"""L-02 提示词构建与影子接线测试——构建器/gateway 接线/跨问熔断/影子日志增强。

票面（tickets/phase3/L-02-提示词构建与影子接线.md）验收对应：
- 提示词构建器：三入参→messages 形状；台账投影只含 MEASURE_COLUMNS 键集；
  时间/条数词表与 DATA_QUESTION_RE 同源（改一词两处同步回归）；golden 缺省空不炸；
- gateway 接线（替身 Completer，零真模型调用）：caller 恒＝chat.intent.plan；
  超时/坏 JSON/越界三路兜底返回 None；
- 跨问熔断：连续 N 次/滑动失败率超阈触发；熔断后短路（替身不再被调）；配置缺省
  None＝不启用；恢复＝重启（进程内旗标）；
- 影子日志：JSONL 字段超集（latency_ms/tokens/bucket）；双分桶判例各一；
  tmp_path 注入落盘；FX-09 守护改写为断言装配。

影子期铁律：LLM#plan 产物只落日志不进生效路，SSE 帧零影子内容（既有测试零断言
改动全绿＝现网行为零变化）。测试全程替身喂 LLM，零真模型调用。
"""

import asyncio
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.domains.chat import chains as chains_mod
from app.domains.chat import domain as d
from app.domains.chat import service as service_mod
from app.infra.clock import now
from app.infra.config import InfraSettings
from app.infra.db import ConnectionManager
from tests.domains.chat.conftest import AQIANG, Seams, collect, make_service

SHADOW_LOGGER = "domains.chat"


def _today() -> date:
    return now().date()


_OIL_CARD = d.MetricCard(slot_name="日产油量", name="★日产油量", calibers=[])
_UNBOUND_CARD = d.MetricCard(slot_name="产量完成率", name="★产量完成率", calibers=[])


def _ok_payload(
    *, direction: str = "desc", metric_slot: str = "日产油量",
) -> dict[str, Any]:
    """合法 Draft 载荷（与「哪几口井采得最狠」的确定性解析一致——比对三态＝一致）。"""
    return {
        "metric_slot": metric_slot,
        "window": {
            "start": (_today() - timedelta(days=30)).isoformat(),
            "end": _today().isoformat(),
        },
        "limit_requested": None,
        "ranking": False,
        "direction": direction,
    }


class _StubCompleter:
    """替身 Completer（gateway.complete B6 形状——收参断言＋可编程回包）。"""

    def __init__(
        self, content: str = "", *, delay: float = 0.0, fail: bool = False,
        tokens: tuple[int, int] | None = (120, 30),
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.content = content
        self.delay = delay
        self.fail = fail
        self.tokens = tokens

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        self.calls.append({"alias": alias, "messages": messages, "caller": caller})
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("上游失败（替身）")
        if self.tokens is None:
            return SimpleNamespace(content=self.content)
        return SimpleNamespace(
            content=self.content,
            prompt_tokens=self.tokens[0],
            completion_tokens=self.tokens[1],
        )


def _plain_drafter(payload: dict[str, Any] | None, calls: list[str]) -> Any:
    """无遥测属性的裸替身 drafter（观测点取数缺属性→null 的判例载体）。"""

    async def drafter(question: str) -> Any:
        calls.append(question)
        return None if payload is None else d.QueryPlanDraft.from_payload(payload)

    return drafter


def _chain_ctx(question: str, *, metric_cards: list[d.MetricCard]) -> d.ChainContext:
    return d.ChainContext(
        run_id="run-shadow-test", question=question, actor_who=AQIANG,
        assembly=d.AssemblyResult(
            anchor_line=None, slots="", terms=[], candidates=[], lanes=[],
            metric_cards=metric_cards,
        ),
    )


def _deps_with(
    seams: Seams, *, drafter: Any = None, sink: Any = None,
) -> chains_mod.ChainDeps:
    """直构链体注入缝（Seams 假缝镜像组合根——按需挂 drafter/影子日志落盘缝）。"""
    return chains_mod.ChainDeps(
        config_loader=seams.load_config,
        metrics_loader=seams.load_metrics,
        terms_loader=seams.load_terms,
        faq_matcher=seams.match_faq,
        faq_searcher=seams.search_faq_similar,
        index_searcher_dual=seams.search_index_dual,
        graph_searcher=seams.search_graph,
        anchor_loader=seams.load_anchor,
        completer=seams,
        query_executor=seams.execute_query,
        waterline_loader=seams.load_waterline,
        plan_drafter=drafter,
        shadow_log_sink=sink,
    )


def _wired_service(
    chat_db: ConnectionManager, seams: Seams, tmp_path: Path, *, completer: Any = None
) -> service_mod.ChatService:
    """ChatService 直构（生产装配点真实形状——影子日志路径注 tmp_path 零仓库污染）。"""
    return service_mod.ChatService(
        chat_db,
        config_loader=seams.load_config,
        metrics_loader=seams.load_metrics,
        terms_loader=seams.load_terms,
        faq_matcher=seams.match_faq,
        faq_searcher=seams.search_faq_similar,
        index_searcher=seams.search_index,
        index_searcher_dual=seams.search_index_dual,
        graph_searcher=seams.search_graph,
        anchor_loader=seams.load_anchor,
        completer=seams if completer is None else completer,
        query_executor=seams.execute_query,
        waterline_loader=seams.load_waterline,
        shadow_log_path=tmp_path / "shadow-plan.jsonl",
    )


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    return [json.loads(line) for line in text.splitlines()] if text else []


def _shadow_log_records(caplog: Any) -> list[Any]:
    return [
        record for record in caplog.records
        if record.name == SHADOW_LOGGER and "[shadow-plan]" in record.getMessage()
    ]


# ---------- 交付物①：提示词构建器（纯函数——三入参→messages） ----------


class TestPlanPromptBuilder:
    def test_three_inputs_build_system_user_messages(self) -> None:
        """三入参（问句＋台账投影＋golden 少样本）→ messages＝[system, user] 形状。"""
        projection = d.PlanPromptProjection(
            metrics=("日产油量",), time_words=("上个月",), count_words=("前 10",),
        )
        samples = (
            {"question": "上个月日产油量最高的前 5 口井", "draft": '{"metric_slot": "日产油量"}'},
        )
        messages = service_mod.build_plan_messages(
            "哪几口井采得最狠", projection, samples, today=date(2026, 10, 7),
        )
        assert [m["role"] for m in messages] == ["system", "user"]
        assert messages[0]["content"] == service_mod.PLAN_SYSTEM_PROMPT
        user = messages[1]["content"]
        assert "哪几口井采得最狠" in user
        assert "2026-10-07" in user  # 今天日期（窗口推算基准）
        assert "日产油量" in user and "上个月" in user and "前 10" in user
        assert "上个月日产油量最高的前 5 口井" in user  # 少样本问句
        assert '{"metric_slot": "日产油量"}' in user  # 少样本草案

    def test_golden_samples_default_empty_no_crash(self) -> None:
        """golden 缺省空——构建不炸，messages 形状不变（样本数据 L-04 交付后接入）。"""
        messages = service_mod.build_plan_messages(
            "上个月产油情况如何", d.default_plan_projection(), today=date(2026, 10, 7),
        )
        assert len(messages) == 2
        assert "上个月产油情况如何" in messages[1]["content"]

    def test_projection_metrics_only_measure_columns_keys(self) -> None:
        """台账投影·可出数指标＝MEASURE_COLUMNS 键集（零第二份可出数指标源）。"""
        assert d.default_plan_projection().metrics == tuple(d.MEASURE_COLUMNS)
        assert set(d.default_plan_projection().metrics) == set(d.MEASURE_COLUMNS)

    def test_word_tables_single_source_with_data_question_re(self) -> None:
        """词表同源回归：展示词表逐词仍被 DATA_QUESTION_RE 命中（改一词两处须同步）；
        正则文本冻结＝既定路由行为零变化（DATA_QUESTION_RE 由词族常量拼装——无第二份）。"""
        for word in (*d.PLAN_TIME_WORDS_DISPLAY, *d.PLAN_COUNT_WORDS_DISPLAY):
            assert d.DATA_QUESTION_RE.search(word) is not None, f"词表词失配：{word}"
        assert d.DATA_QUESTION_RE.pattern == (
            r"昨天|前天|今天|本月|这个月|上月|上个月|今年|去年|最近|近[0-9一二两三四五六七八九十]"
            r"|最高|最低|最大|最小|排名|TOP|top|前\s*[0-9一二两三四五六七八九十]"
            r"|[0-9一二两三四五六七八九十]+\s*口"
        )

    def test_builtin_fewshots_are_valid_payloads(self) -> None:
        """内置少样本常量（golden 未就绪档）逐条是合法 Draft 载荷且指标在册。"""
        for sample in service_mod.PLAN_FEWSHOT_FALLBACK:
            draft = d.QueryPlanDraft.from_payload(json.loads(sample["draft"]))
            assert draft.metric_slot in d.MEASURE_COLUMNS
            assert sample["question"]


# ---------- 交付物②：gateway 接线（替身 Completer——零真模型调用） ----------


class TestGatewayWiring:
    async def test_caller_constant_and_call_shape(self) -> None:
        """caller 恒＝chat.intent.plan（替身收参断言）；alias=petro-main；messages 形状。"""
        stub = _StubCompleter(content=json.dumps(_ok_payload()))
        drafter = service_mod.ShadowPlanDrafter(stub)
        draft = await drafter("哪几口井采得最狠")
        assert draft is not None and draft.metric_slot == "日产油量"
        assert len(stub.calls) == 1
        call = stub.calls[0]
        assert call["caller"] == d.CALLER_INTENT_PLAN == "chat.intent.plan"
        assert call["alias"] == chains_mod.MAIN_ALIAS
        assert [m["role"] for m in call["messages"]] == ["system", "user"]
        assert "哪几口井采得最狠" in call["messages"][1]["content"]

    def test_plan_timeout_constant_matches_verdict(self) -> None:
        """超时常量 8.0 秒与 verdict 同值（票内定案）。"""
        assert d.INTENT_PLAN_TIMEOUT_SECONDS == 8.0
        assert d.INTENT_PLAN_TIMEOUT_SECONDS == d.INTENT_VERDICT_TIMEOUT_SECONDS

    async def test_timeout_returns_none_and_counts_failure(
        self, monkeypatch: Any
    ) -> None:
        """超时兜底（替身延迟桩）：返回 None＋计一次失败。"""
        monkeypatch.setattr(d, "INTENT_PLAN_TIMEOUT_SECONDS", 0.05)
        stub = _StubCompleter(content=json.dumps(_ok_payload()), delay=0.5)
        breaker = service_mod.PlanBreaker(consecutive_failures=1)
        drafter = service_mod.ShadowPlanDrafter(stub, breaker=breaker)
        assert await drafter("q") is None
        assert breaker.tripped is True  # 失败计数已落（N=1 触发）
        assert drafter.last_telemetry is not None
        assert drafter.last_telemetry.prompt_tokens is None  # 未拿到应答——token 记 null

    async def test_bad_json_returns_none(self) -> None:
        """JSON 解析坏（宽容剥离救不回）→ None→确定性快路。"""
        stub = _StubCompleter(content="前置杂文 {不是 JSON}")
        drafter = service_mod.ShadowPlanDrafter(stub)
        assert await drafter("q") is None
        assert drafter.last_telemetry is not None
        assert drafter.last_telemetry.latency_ms is not None

    async def test_fenced_json_stripped_leniently(self) -> None:
        """代码围栏包裹的合法 JSON——_parse_intent_json 同款宽容剥离放行。"""
        fenced = "```json\n" + json.dumps(_ok_payload()) + "\n```"
        stub = _StubCompleter(content=fenced)
        drafter = service_mod.ShadowPlanDrafter(stub)
        draft = await drafter("哪几口井采得最狠")
        assert draft is not None and draft.ranking is False

    async def test_out_of_whitelist_returns_none(self) -> None:
        """越界·白名单外未知键（Draft schema 拒）→ None→确定性快路。"""
        stub = _StubCompleter(content=json.dumps({**_ok_payload(), "sql": "SELECT 1"}))
        drafter = service_mod.ShadowPlanDrafter(stub)
        assert await drafter("q") is None

    async def test_validator_reject_returns_none(self) -> None:
        """越界·validator 拒（metric_slot 不在 MEASURE_COLUMNS——不在目录不代答）→ None。"""
        stub = _StubCompleter(content=json.dumps(_ok_payload(metric_slot="完井数")))
        drafter = service_mod.ShadowPlanDrafter(stub)
        assert await drafter("q") is None

    async def test_upstream_failure_returns_none(self) -> None:
        """上游调用抛错→ None（不许问挂——三重兜底第三路）。"""
        stub = _StubCompleter(content=json.dumps(_ok_payload()), fail=True)
        drafter = service_mod.ShadowPlanDrafter(stub)
        assert await drafter("q") is None

    async def test_success_telemetry_tokens_read_from_completion(self) -> None:
        """token 成本从 completer 返回对象属性读取（延迟/tokens 落遥测）。"""
        stub = _StubCompleter(content=json.dumps(_ok_payload()))
        drafter = service_mod.ShadowPlanDrafter(stub)
        await drafter("哪几口井采得最狠")
        telemetry = drafter.last_telemetry
        assert telemetry is not None
        assert telemetry.prompt_tokens == 120
        assert telemetry.completion_tokens == 30
        assert telemetry.latency_ms is not None
        assert telemetry.breaker_tripped is False

    async def test_missing_token_attributes_recorded_null(self) -> None:
        """替身回包无 tokens 属性→记 null——不因取数失败断流。"""
        stub = _StubCompleter(content=json.dumps(_ok_payload()), tokens=None)
        drafter = service_mod.ShadowPlanDrafter(stub)
        assert await drafter("q") is not None
        assert drafter.last_telemetry is not None
        assert drafter.last_telemetry.prompt_tokens is None
        assert drafter.last_telemetry.completion_tokens is None


# ---------- 交付物③：跨问熔断（机制 7——阈值不预设，缺省 None＝不启用） ----------


class TestPlanBreaker:
    def test_consecutive_failures_trip(self, caplog: Any) -> None:
        """连续 N 次失败触发熔断位＋告警（LOGGER.warning）。"""
        caplog.set_level(logging.WARNING, logger=SHADOW_LOGGER)
        breaker = service_mod.PlanBreaker(consecutive_failures=3)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.tripped is False
        breaker.record_failure()
        assert breaker.tripped is True
        warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any("熔断" in message for message in warnings)

    def test_success_resets_consecutive_counter(self) -> None:
        breaker = service_mod.PlanBreaker(consecutive_failures=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()  # 成功清零连续失败计数
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.tripped is False

    def test_sliding_failure_rate_trip(self) -> None:
        """滑动窗口失败率超阈（严格大于）触发——窗口计满才判。"""
        breaker = service_mod.PlanBreaker(
            consecutive_failures=None, failure_rate_threshold=0.5, window_size=4,
        )
        breaker.record_success()
        breaker.record_success()
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.tripped is False  # 0.50＝阈值——未「超」阈不触发
        breaker.record_failure()  # 窗口滑为 [s,f,f,f]＝0.75＞0.5
        assert breaker.tripped is True

    def test_rate_not_evaluated_until_window_full(self) -> None:
        """滑动窗口计满才判失败率（未满不判——防小样本误跳闸）。"""
        breaker = service_mod.PlanBreaker(failure_rate_threshold=0.1, window_size=4)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.tripped is False  # 窗口未满（3/4）不判失败率
        breaker.record_failure()  # 第 4 次失败——满窗 1.0 > 0.1 → 触发
        assert breaker.tripped is True

    def test_rate_below_threshold_no_trip(self) -> None:
        breaker = service_mod.PlanBreaker(failure_rate_threshold=0.9, window_size=4)
        breaker.record_success()
        breaker.record_success()
        breaker.record_success()
        breaker.record_failure()
        assert breaker.tripped is False  # 0.25 < 0.9

    def test_default_none_disabled_never_trips(self) -> None:
        """配置缺省 None/None＝熔断不启用（L-03 出数后 Owner 拍板回填——开放问题 4）。"""
        breaker = service_mod.PlanBreaker()
        for _ in range(100):
            breaker.record_failure()
        assert breaker.tripped is False

    def test_no_auto_recovery_restart_is_the_only_way(self) -> None:
        """熔断位单向置位：成功/失败都不解除；恢复＝重启进程（新实例＝干净旗标）。"""
        breaker = service_mod.PlanBreaker(consecutive_failures=1)
        breaker.record_failure()
        assert breaker.tripped is True
        breaker.record_success()
        assert breaker.tripped is True  # 不自动恢复
        fresh = service_mod.PlanBreaker(consecutive_failures=1)  # 重启＝新进程内实例
        assert fresh.tripped is False


class TestPlanBreakerConfig:
    def test_settings_keys_default_none(self) -> None:
        """Settings 面两可选键缺省 None＝熔断不启用（additive——不动既有配置面）。"""
        settings = InfraSettings(
            plan_breaker_consecutive_failures=None, plan_breaker_failure_rate_threshold=None,
        )
        assert settings.plan_breaker_consecutive_failures is None
        assert settings.plan_breaker_failure_rate_threshold is None

    def test_settings_keys_env_injection(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("PLAN_BREAKER_CONSECUTIVE_FAILURES", "3")
        monkeypatch.setenv("PLAN_BREAKER_FAILURE_RATE_THRESHOLD", "0.5")
        settings = InfraSettings()
        assert settings.plan_breaker_consecutive_failures == 3
        assert settings.plan_breaker_failure_rate_threshold == 0.5

    def test_from_settings_builds_disabled_breaker_by_default(self) -> None:
        breaker = service_mod.plan_breaker_from_settings()
        assert breaker.tripped is False


class TestBreakerShortCircuit:
    async def test_tripped_breaker_short_circuits_completer(self) -> None:
        """熔断后 LLM#plan 直接短路跳过（替身不再被调）＋遥测标 breaker=tripped。"""
        stub = _StubCompleter(content=json.dumps(_ok_payload()), fail=True)
        breaker = service_mod.PlanBreaker(consecutive_failures=1)
        drafter = service_mod.ShadowPlanDrafter(stub, breaker=breaker)
        assert await drafter("问句一") is None  # 调用失败→触发 N=1
        assert breaker.tripped is True
        assert await drafter("问句二") is None  # 短路
        assert await drafter("问句三") is None  # 短路
        assert len(stub.calls) == 1  # 熔断后替身不再被调（快路-only）
        assert drafter.last_telemetry is not None
        assert drafter.last_telemetry.breaker_tripped is True


# ---------- 交付物④：影子日志增强（字段超集＋双分桶＋JSONL 落盘） ----------


class TestShadowLogSink:
    def test_default_path_constant(self) -> None:
        assert service_mod.SHADOW_LOG_DEFAULT_PATH == "logs/shadow-plan.jsonl"
        assert service_mod.ShadowLogSink().path == Path("logs/shadow-plan.jsonl")

    def test_write_failure_swallowed_no_raise(self, tmp_path: Path, caplog: Any) -> None:
        """JSONL 落盘失败（目录被文件占位）只告警不断流——影子观测不炸主链。"""
        caplog.set_level(logging.WARNING, logger=SHADOW_LOGGER)
        blocker = tmp_path / "blocked"
        blocker.write_text("占位文件", encoding="utf-8")
        sink = service_mod.ShadowLogSink(blocker / "shadow.jsonl")
        record = d.ShadowPlanRecord(
            run_id="r", trigger="词面不齐", draft_state="一致", elapsed_ms=1,
        )
        sink.write(record)  # 不抛
        assert any("落盘失败" in r.getMessage() for r in caplog.records)


class TestShadowLogEnhancement:
    async def test_jsonl_superset_fields_with_telemetry(
        self, seams: Seams, tmp_path: Path, caplog: Any
    ) -> None:
        """JSONL 一行含字段超集（L-01 四要素＋latency_ms/tokens/bucket/breaker/question/ts）；
        LOGGER 行双写且向后兼容原六字段；过宽桶判例（触发但快路可解）。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        seams.waterline = d.WaterlineFace(
            layer="汇总层", data_date=_today() - timedelta(days=1),
            promise="T-1", tag="达标（承诺 T-1）", late_days=0,
        )
        sink = service_mod.ShadowLogSink(tmp_path / "shadow-plan.jsonl")
        stub = _StubCompleter(content=json.dumps(_ok_payload()))
        drafter = service_mod.ShadowPlanDrafter(stub)  # 缺省 None/None 熔断不启用
        deps = _deps_with(seams, drafter=drafter, sink=sink)
        events = await collect(chains_mod.query_chain(
            deps, _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD]),
        ))
        records = _jsonl_records(tmp_path / "shadow-plan.jsonl")
        assert len(records) == 1
        row = records[0]
        assert set(row) >= {
            "ts", "run_id", "question", "trigger", "draft_state", "elapsed_ms",
            "divergent", "note", "latency_ms", "prompt_tokens", "completion_tokens",
            "bucket", "breaker",
        }
        assert row["run_id"] == "run-shadow-test"
        assert row["question"] == "哪几口井采得最狠"
        assert row["trigger"] == "词面不齐"
        assert row["draft_state"] == "一致"
        assert row["bucket"] == d.PLAN_BUCKET_OVERWIDE  # 过宽桶：触发谓词 True 且比对一致
        assert row["prompt_tokens"] == 120  # 遥测从 completer 返回对象属性读取
        assert row["completion_tokens"] == 30
        assert isinstance(row["latency_ms"], int)
        assert row["breaker"] is None
        assert row["ts"]
        # LOGGER 行双写：原六字段保留（向后兼容）＋新增字段附尾。
        log_records = _shadow_log_records(caplog)
        assert len(log_records) == 1
        message = log_records[0].getMessage()
        assert "\n" not in message  # 结构化单行
        for token in (
            "run_id=run-shadow-test", "trigger=词面不齐", "draft_state=一致",
            "elapsed_ms=", "divergent=-", "note=", "latency_ms=",
            "prompt_tokens=120", "completion_tokens=30",
            f"bucket={d.PLAN_BUCKET_OVERWIDE}", "breaker=-",
        ):
            assert token in message, token
        # 影子零生效：SSE 帧零影子内容。
        assert all("shadow" not in str(event.data) for event in events)

    async def test_plain_stub_without_telemetry_records_nulls(
        self, seams: Seams, tmp_path: Path
    ) -> None:
        """drafter 无遥测属性（裸替身形状）→ latency/tokens 记 null——不因取数失败断流。"""
        seams.waterline = d.WaterlineFace(
            layer="汇总层", data_date=_today() - timedelta(days=1),
            promise="T-1", tag="达标（承诺 T-1）", late_days=0,
        )
        sink = service_mod.ShadowLogSink(tmp_path / "shadow-plan.jsonl")
        calls: list[str] = []
        deps = _deps_with(seams, drafter=_plain_drafter(_ok_payload(), calls), sink=sink)
        await collect(chains_mod.query_chain(
            deps, _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD]),
        ))
        row = _jsonl_records(tmp_path / "shadow-plan.jsonl")[0]
        assert row["latency_ms"] is None
        assert row["prompt_tokens"] is None
        assert row["completion_tokens"] is None
        assert row["draft_state"] == "一致"

    async def test_diverge_not_marked_overwide(self, seams: Seams, tmp_path: Path) -> None:
        """过宽桶只在比对「一致」时标——分歧态不进桶（触发有覆盖增值）。"""
        sink = service_mod.ShadowLogSink(tmp_path / "shadow-plan.jsonl")
        stub = _StubCompleter(content=json.dumps(_ok_payload(direction="asc")))
        deps = _deps_with(seams, drafter=service_mod.ShadowPlanDrafter(stub), sink=sink)
        await collect(chains_mod.query_chain(
            deps, _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD]),
        ))
        row = _jsonl_records(tmp_path / "shadow-plan.jsonl")[0]
        assert row["draft_state"] == "分歧"
        assert row["bucket"] is None

    async def test_over_narrow_bucket_on_askback(self, seams: Seams, tmp_path: Path) -> None:
        """过窄桶判例：触发谓词 False 且本问最终落缺参澄清（「最近」模糊窗 askback）——
        快路信号判齐但快路没真正出数；无 drafter 也落行（落盘缝独立观测）。"""
        sink = service_mod.ShadowLogSink(tmp_path / "shadow-plan.jsonl")
        calls: list[str] = []
        deps = _deps_with(seams, drafter=_plain_drafter(None, calls), sink=sink)
        events = await collect(chains_mod.query_chain(
            deps, _chain_ctx("日产油量最近怎么样", metric_cards=[_OIL_CARD]),
        ))
        assert any(event.event == "clarify" for event in events)  # askback 在场（缺参澄清）
        assert calls == []  # 谓词未触发——drafter 不被调
        rows = _jsonl_records(tmp_path / "shadow-plan.jsonl")
        assert len(rows) == 1
        assert rows[0]["bucket"] == d.PLAN_BUCKET_OVERNARROW
        assert rows[0]["trigger"] is None  # 触发谓词 False
        assert rows[0]["draft_state"] == "不可比"
        assert "缺参" in str(rows[0]["note"])

    async def test_predicate_true_downgrade_no_double_line(
        self, seams: Seams, tmp_path: Path
    ) -> None:
        """谓词已触发的降级问句只在 N7.1 观测点落一行（过窄钩子不双记——降级路谓词
        恒已触发：指标未绑定＝解析缺件）。"""
        sink = service_mod.ShadowLogSink(tmp_path / "shadow-plan.jsonl")
        calls: list[str] = []
        deps = _deps_with(seams, drafter=_plain_drafter(None, calls), sink=sink)
        await collect(chains_mod.query_chain(
            deps, _chain_ctx("上个月产量完成率排名前三", metric_cards=[_UNBOUND_CARD]),
        ))
        rows = _jsonl_records(tmp_path / "shadow-plan.jsonl")
        assert len(rows) == 1
        assert rows[0]["trigger"] == "解析缺件"
        assert rows[0]["bucket"] is None
        assert calls == ["上个月产量完成率排名前三"]

    async def test_no_shadow_seams_silent(self, seams: Seams, tmp_path: Path) -> None:
        """缝全未装配（生产缺省形状之外的兜底确认）——零日志零落盘。"""
        deps = _deps_with(seams)
        await collect(chains_mod.query_chain(
            deps, _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD]),
        ))
        assert not (tmp_path / "shadow-plan.jsonl").exists()


# ---------- 生产装配点接线（FX-09 守护改写为断言装配） ----------


class TestCompositionRootShadowWiring:
    def test_production_composition_root_wires_shadow_plan_drafter(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """FX-09 守护改写（L-02 票面义务）：生产装配点（ChatService.__init__ →
        ChainDeps 构造）已接线影子 drafter——非 None 且指向影子实现。"""
        service = make_service(chat_db, seams)
        drafter = service._deps.plan_drafter
        assert drafter is not None
        assert isinstance(drafter, service_mod.ShadowPlanDrafter)

    def test_production_composition_root_wires_shadow_log_sink(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        service = make_service(chat_db, seams)
        assert isinstance(service._deps.shadow_log_sink, service_mod.ShadowLogSink)

    def test_production_breaker_defaults_disabled(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """生产装配的熔断器缺省不启用（Settings 两键 None）——L-03 出数后 Owner 回填。"""
        service = make_service(chat_db, seams)
        drafter = service._deps.plan_drafter
        assert drafter is not None
        assert drafter._breaker.tripped is False

    def test_no_completer_keeps_plan_drafter_none(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """completer 未装配（替身缺席的极简单测形状）＝drafter 缝保持 None（恒静默）。"""
        service = service_mod.ChatService(
            chat_db,
            config_loader=seams.load_config,
            metrics_loader=seams.load_metrics,
            terms_loader=seams.load_terms,
            faq_matcher=seams.match_faq,
            faq_searcher=seams.search_faq_similar,
            index_searcher=seams.search_index,
            index_searcher_dual=seams.search_index_dual,
            graph_searcher=seams.search_graph,
            anchor_loader=seams.load_anchor,
            completer=None,
        )
        assert service._deps.plan_drafter is None

    async def test_production_wiring_routes_plan_caller_end_to_end(
        self, chat_db: ConnectionManager, seams: Seams, tmp_path: Path
    ) -> None:
        """端到端：生产装配问句触发影子路——completer 收到 caller=chat.intent.plan；
        影子行落注入路径（tmp_path）；SSE 帧零影子内容（现网行为零变化）。"""
        seams.index_vector = [
            d.IndexHitFace(
                fragment_id="f1", report_id="rpt-1", report="N-02 完井报告",
                section="01 井基本情况", snippet="检泵周期记录", score=0.7, leg="vector",
                text="N-02 井检泵周期记录——报告库检索片段",
            ),
        ]
        service = _wired_service(chat_db, seams, tmp_path)
        events = await collect(service.ask(
            "上个月产量完成率排名前三", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        assert "chat.intent.plan" in seams.completions  # 归因记账（B6 统一出口）
        rows = _jsonl_records(tmp_path / "shadow-plan.jsonl")
        assert len(rows) == 1
        assert rows[0]["trigger"] == "解析缺件"
        assert all("shadow" not in str(event.data) for event in events)

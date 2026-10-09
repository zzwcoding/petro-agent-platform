"""V2-39 测评时钟冻结——EVAL_FROZEN_DATE 缝解析钉＋冻结态四窗词钉＋真实时钟回归钉。

被测件＝appv2.runtime.eval_clock（V2-39 新缝——评测/冒烟面统一注入冻结时钟）。
纪律边界：生产面时钟语义零改动——infra.clock B14 单点实现不动，覆写走构造
注入（today= 缝）；env 只被评测/冒烟具显式解析后经构造缝传入，生产装配路径
（today=None→infra.clock 实时）永不读 env——本文件「env 不泄漏」钉看守该性质。

- resolve_eval_frozen_date：EVAL_FROZEN_DATE 解析单点——未设/空串→冻结水位日
  2026-08-31（Owner 2026-10-09 拍板：该日下四窗词锚定全部干净通过，测评信号
  不被新鲜度注记噪声污染）；显式 "real"→None（回真实时钟做对照）；显式 ISO
  日期→该日；非法值→ValueError fail-fast（不静默回落——P-035 装配纪律同款）。
- eval_frozen_today：组合根 today 缝注入形——冻结日→恒值 callable；real→None
  （调用方把 None 传构造缝→infra.clock 真实时钟）。

冻结态四窗词钉（票面任务③前半）：「近3天/近30天/本月/去年」在冻结执行日
2026-08-31 锚定的窗全部干净过新鲜度闸（水位同为 2026-08-31）——零拦停
（非 freshness_block）零改绑（rebind_notice 为 None），闸后出数收口；血缘③
窗锚定随冻结日（「近 3 天」[2026-08-28, 2026-08-31) 等）。同日 T-1 判定＝
达标（freshness_judgment 纯函数钉——水位注记噪声消失）。

真实时钟态回归钉（票面任务③后半）：today=None（infra.clock 实时）下闸语义
行为不变——水位固定 2026-08-31 落后实时，近3天/近30天/本月窗整体晚于水位→
照旧拦停；去年窗整体在水位前→照旧出数（是否改绑随真实日期合法漂移，钉只锁
「不被拦停」这一稳定性质）。env 单独在场（未过构造缝）不得改变生产行为。

执行缝＝桩执行器（闸钉只看闸结果与窗锚定，不依赖数据面行集——CSV 快照无
2026-08 行，桩单行使闸后路径可达）。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest

from appv2.infra import clock
from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
from appv2.query import (
    LINEAGE_KEY_FILTER,
    OUTCOME_FRESHNESS_BLOCK,
    OUTCOME_ROWS,
    QueryEngine,
    QueryResult,
    SqlPlan,
    WatermarkFace,
    build_query_plan,
)
from appv2.query.pg_waterline import freshness_judgment
from appv2.runtime.eval_clock import (
    EVAL_FROZEN_DATE_DEFAULT,
    EVAL_FROZEN_DATE_ENV,
    EVAL_FROZEN_DATE_REAL,
    eval_frozen_today,
    resolve_eval_frozen_date,
)

# 冻结点＝水位日 2026-08-31（票面拍板落字——常量真源在 eval_clock，此处照抄钉值）。
FROZEN = date(2026, 8, 31)
WATERMARK = date(2026, 8, 31)

METRIC = "日产油量"

# 四窗词钉面（票面原文词形＋钉值锚定——parse_time_window 确定性词表）：
# 「近3天」[08-28, 08-31)／「近30天」[08-01, 08-31)／「本月」[08-01, 08-31)／
# 「去年」[2025-01-01, 2026-01-01)——全在水位 08-31 前（窗尾−1 天 ≤ 水位），
# 零拦停零改绑。（票面「近30天 [07-31, 08-30)／本月 [08-01, 09-01)」为词面
# 端点笔误——实际锚定随 parse_time_window 合同：近 N 天＝[today−N, today)、
# 本月＝[月初, today)；「零拦零改绑」结论两形一致。）
FOUR_WINDOW_WORDS: tuple[tuple[str, str, str], ...] = (
    ("近3天", "近 3 天", "[2026-08-28, 2026-08-31)"),
    ("近30天", "近 30 天", "[2026-08-01, 2026-08-31)"),
    ("本月", "本月至今", "[2026-08-01, 2026-08-31)"),
    ("去年", "去年", "[2025-01-01, 2026-01-01)"),
)


class _GateStubExecutor:
    """闸钉桩执行器——恒回单行（闸钉只看闸结果与窗锚定，不依赖数据面行集）。"""

    def execute(self, plan: SqlPlan) -> QueryResult:
        return QueryResult(
            columns=(("well_id", "井号"), ("value", "值")),
            rows=({"well_id": "N-01", "value": 1},),
        )


def _engine(today: Callable[[], date] | None) -> QueryEngine:
    """闸钉引擎：水位读缝钉 2026-08-31；today 缺省 None＝infra.clock 实时（生产同形）。"""
    return QueryEngine(
        knowledge=InMemoryKnowledgeStore(question_array_snapshot(), today=FROZEN),
        executor=_GateStubExecutor(),
        waterline=lambda: WatermarkFace(
            data_date=WATERMARK, promise="T-1", tag="落后 38 天（超期）",
        ),
        today=today,
    )


def _frozen_plan(question: str) -> Any:
    return build_query_plan(metric_slot=METRIC, question=question, today=FROZEN)


def _real_plan(question: str) -> Any:
    """真实时钟锚定的计划（与 today=None 引擎同钟——clock.now().date()）。"""
    return build_query_plan(metric_slot=METRIC, question=question, today=clock.now().date())


# ---------- 缝解析钉（resolve_eval_frozen_date） ----------


class TestResolveEvalFrozenDate:
    def test_unset_defaults_to_waterline_day(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(EVAL_FROZEN_DATE_ENV, raising=False)
        assert resolve_eval_frozen_date() == FROZEN

    def test_default_constant_is_waterline_day(self) -> None:
        """缺省冻结点常量＝2026-08-31（水位日——票面拍板落字）。"""
        assert EVAL_FROZEN_DATE_DEFAULT == FROZEN

    def test_empty_string_treated_as_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, "")
        assert resolve_eval_frozen_date() == FROZEN

    def test_explicit_date_parsed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, "2026-08-15")
        assert resolve_eval_frozen_date() == date(2026, 8, 15)

    def test_real_sentinel_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, EVAL_FROZEN_DATE_REAL)
        assert resolve_eval_frozen_date() is None

    def test_invalid_value_fails_fast(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, "yesterday")
        with pytest.raises(ValueError, match=EVAL_FROZEN_DATE_ENV):
            resolve_eval_frozen_date()


# ---------- 组合根注入形钉（eval_frozen_today） ----------


class TestEvalFrozenToday:
    def test_frozen_returns_constant_callable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(EVAL_FROZEN_DATE_ENV, raising=False)
        today = eval_frozen_today()
        assert today is not None
        assert today() == FROZEN

    def test_real_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """real→None：调用方把 None 传构造缝→infra.clock 真实时钟（对照态）。"""
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, EVAL_FROZEN_DATE_REAL)
        assert eval_frozen_today() is None


# ---------- 冻结态四窗词钉（票面任务③前半——闸零拦零改绑） ----------


class TestFrozenFourWindowWords:
    @pytest.mark.parametrize(("word", "label", "window"), FOUR_WINDOW_WORDS)
    def test_window_word_passes_gate_clean(
        self, monkeypatch: pytest.MonkeyPatch, word: str, label: str, window: str
    ) -> None:
        monkeypatch.delenv(EVAL_FROZEN_DATE_ENV, raising=False)
        engine = _engine(lambda: FROZEN)
        outcome = engine.run(_frozen_plan(f"{word}各井的日产油量是多少？"))
        # 闸零拦：非 freshness_block（真实出数收口）。
        assert outcome.kind == OUTCOME_ROWS, (
            f"冻结态窗词「{word}」被闸拦：{outcome.kind}——{outcome.reason or outcome.message}"
        )
        # 零改绑：窗全在水位前，rebind_notice 必缺。
        assert outcome.rebind_notice is None
        # 窗锚定随冻结日（血缘③过滤条件行）。
        assert outcome.lineage is not None
        filter_line = next(
            line for line in outcome.lineage if line.key == LINEAGE_KEY_FILTER
        )
        assert label in filter_line.value
        assert window in filter_line.value

    def test_frozen_watermark_judgment_is_ok(self) -> None:
        """同日 T-1 判定＝达标——水位注记噪声消失（评测评能力不测数据面进度）。"""
        tag, late_days = freshness_judgment(WATERMARK, FROZEN)
        assert late_days == 0
        assert "达标" in tag


# ---------- 真实时钟态回归钉（票面任务③后半——生产行为不变） ----------


class TestRealClockRegression:
    @pytest.mark.parametrize("word", ["近3天", "近30天", "本月"])
    def test_real_clock_recent_windows_still_block(
        self, monkeypatch: pytest.MonkeyPatch, word: str
    ) -> None:
        """实时钟下近3天/近30天/本月窗整体晚于固定水位→照旧拦停（闸语义零漂移）。"""
        monkeypatch.delenv(EVAL_FROZEN_DATE_ENV, raising=False)
        engine = _engine(None)  # today=None＝infra.clock 实时（生产缺省同形）
        outcome = engine.run(_real_plan(f"{word}各井的日产油量是多少？"))
        assert outcome.kind == OUTCOME_FRESHNESS_BLOCK
        assert outcome.watermark_date == WATERMARK
        assert outcome.rows is None  # 拦停零数值（不冒充）

    def test_real_clock_last_year_still_not_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """实时钟下去年窗整体在水位前→照旧出数（改绑随真实日期合法漂移，不锁形）。"""
        monkeypatch.delenv(EVAL_FROZEN_DATE_ENV, raising=False)
        engine = _engine(None)
        outcome = engine.run(_real_plan("去年各井的日产油量是多少？"))
        assert outcome.kind == OUTCOME_ROWS

    def test_env_alone_never_leaks_into_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """env 在场但未经构造缝注入→生产行为零变化（eval 缝不泄漏钉）。"""
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, FROZEN.isoformat())
        engine = _engine(None)  # 生产装配形：today=None，永不读 env
        outcome = engine.run(_real_plan("近3天各井的日产油量是多少？"))
        assert outcome.kind == OUTCOME_FRESHNESS_BLOCK  # 实时钟判定不被 env 翻转

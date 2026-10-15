"""冻结钟处理自证（harness 件 frozen_clock——EVAL_FROZEN_DATE 缝，pin-27 参照）。

缝形照抄旧钉 tests/domains/test_v2_eval_clock.py 的解析/注入两钉（缺省 2026-08-31、
"real"→None、非法 fail-fast；env 只经解析面进构造缝）。冻结点真源与纪律见
frozen_clock 模块 docstring——本件只锁替身缝行为，不改生产钟语义。
"""

from __future__ import annotations

from datetime import date

import pytest

from tests.runtimev2.frozen_clock import (
    EVAL_FROZEN_DATE_DEFAULT,
    EVAL_FROZEN_DATE_ENV,
    EVAL_FROZEN_DATE_REAL,
    eval_frozen_today,
    resolve_eval_frozen_date,
)

FROZEN = date(2026, 8, 31)


class TestResolveEvalFrozenDate:
    def test_unset_defaults_to_frozen_day(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(EVAL_FROZEN_DATE_ENV, raising=False)
        assert resolve_eval_frozen_date() == FROZEN

    def test_default_constant_is_frozen_day(self) -> None:
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


class TestEvalFrozenToday:
    def test_frozen_returns_constant_callable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(EVAL_FROZEN_DATE_ENV, raising=False)
        today = eval_frozen_today()
        assert today is not None
        assert today() == FROZEN
        assert today() == today()  # 恒值——多次调用同日

    def test_real_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, EVAL_FROZEN_DATE_REAL)
        assert eval_frozen_today() is None

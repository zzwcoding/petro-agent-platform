"""rerun.py 计费归集纯函数测试（红先绿后——V2-30 · P-025）。

被测件＝eval/results/tools/rerun.py 内计费归集纯函数（跑批脚本本体照
rerun.py 惯例不进 tests/——tests/tools/test_ask_parse_v2.py 同款先例）。

背景（Q12 对账挂账 5 清偿）：跑批后按题归集网关 spend 账本
（PG gateway_spend_record）计费。账本 run_id 列已建但服务侧 _settle
不落值（现状恒空）——归集键＝题级时间窗〔ask_started_at, ask_ended_at〕
＋caller 前缀（v2 基缺省 v2.runtime.）；run_id（session 帧）照常留档
jsonl 行，供服务侧盖章后复核。

四组测试：账本行聚合（sums/by_caller/call_ids/run_id 留档/Decimal 成本）/
PG 连接参数装配（环境量＞.env＞缺省，端口转 int）/.env 解析（注释与裸行
跳过）/时间窗助手（微秒往返＋margin 外扩）＋批次计费摘要（ok/errors 分计）。

V2-33 增两组：归集查询计划（ledger_query_plan——run_id 直查主路/缺 run_id
窗兜底）与归集派发（collect_spend——直查命中/直查零行退窗注记/无 run_id
只走窗/摘要 items 带 method）。
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "eval" / "results" / "tools" / "rerun.py"

_spec = importlib.util.spec_from_file_location("eval_rerun", TOOL)
assert _spec is not None and _spec.loader is not None
rerun = importlib.util.module_from_spec(_spec)
sys.modules["eval_rerun"] = rerun
_spec.loader.exec_module(rerun)


def _ledger_row(
    cid: str,
    caller: str,
    cost: str,
    inp: int,
    out: int,
    *,
    fallback: bool = False,
    run_id: str | None = None,
) -> dict:
    return {
        "id": cid,
        "time": datetime(2026, 10, 9, 10, 0, 0),
        "caller": caller,
        "alias": "MiniMax-M3",
        "model_key": "main",
        "input_tokens": inp,
        "output_tokens": out,
        "cost_yuan": Decimal(cost),
        "fallback": fallback,
        "run_id": run_id,
    }


# ---------- 账本行聚合（aggregate_ledger_rows） ----------


class TestAggregateLedgerRows:
    def test_sums_tokens_cost_and_call_ids_in_order(self) -> None:
        rows = [
            _ledger_row("call-1", "v2.runtime.understand", "0.000705", 384, 107),
            _ledger_row("call-2", "v2.runtime.plan", "0.000886", 499, 129),
            _ledger_row("call-3", "v2.runtime.plan", "0.000686", 572, 38),
        ]
        agg = rerun.aggregate_ledger_rows(rows)
        assert agg["calls"] == 3
        assert agg["input_tokens"] == 384 + 499 + 572
        assert agg["output_tokens"] == 107 + 129 + 38
        assert agg["cost_yuan"] == round(0.000705 + 0.000886 + 0.000686, 6)
        assert agg["call_ids"] == ["call-1", "call-2", "call-3"]

    def test_by_caller_breakdown_and_fallback_count(self) -> None:
        rows = [
            _ledger_row("call-1", "v2.runtime.understand", "0.000705", 384, 107),
            _ledger_row("call-2", "v2.runtime.plan", "0.000886", 499, 129),
            _ledger_row("call-3", "v2.runtime.plan", "0.000686", 572, 38,
                        fallback=True),
        ]
        agg = rerun.aggregate_ledger_rows(rows)
        assert agg["fallback_calls"] == 1
        assert agg["by_caller"]["v2.runtime.understand"] == {
            "calls": 1, "input_tokens": 384, "output_tokens": 107,
            "cost_yuan": 0.000705,
        }
        assert agg["by_caller"]["v2.runtime.plan"] == {
            "calls": 2, "input_tokens": 499 + 572, "output_tokens": 129 + 38,
            "cost_yuan": round(0.000886 + 0.000686, 6),
        }

    def test_non_null_run_ids_archived_in_order(self) -> None:
        """账本 run_id 列现值留档（服务侧盖章后此处即逐笔对账锚）。"""
        rows = [
            _ledger_row("call-1", "v2.runtime.understand", "0.000705", 1, 1),
            _ledger_row("call-2", "v2.runtime.plan", "0.000886", 1, 1,
                        run_id="run-x"),
        ]
        agg = rerun.aggregate_ledger_rows(rows)
        assert agg["ledger_run_ids"] == ["run-x"]

    def test_empty_rows_zero_shape(self) -> None:
        agg = rerun.aggregate_ledger_rows([])
        assert agg == {
            "calls": 0, "fallback_calls": 0, "input_tokens": 0,
            "output_tokens": 0, "cost_yuan": 0.0, "by_caller": {},
            "call_ids": [], "ledger_run_ids": [],
        }


# ---------- PG 连接参数装配（pg_connect_kwargs） ----------


class TestPgConnectKwargs:
    def test_defaults_match_database_yaml_dev(self) -> None:
        """缺省＝config/database.yaml 开发默认（localhost:5433/petro/petro/petro）。"""
        kw = rerun.pg_connect_kwargs(environ={}, dotenv={})
        assert kw == {
            "host": "localhost", "port": 5433, "database": "petro",
            "user": "petro", "password": "petro",
        }

    def test_dotenv_overrides_default(self) -> None:
        kw = rerun.pg_connect_kwargs(
            environ={}, dotenv={"PG_PORT": "6789", "PG_PASSWORD": "s3cret"})
        assert kw["port"] == 6789
        assert kw["password"] == "s3cret"
        assert kw["host"] == "localhost"

    def test_environ_overrides_dotenv(self) -> None:
        kw = rerun.pg_connect_kwargs(
            environ={"PG_USER": "envuser"},
            dotenv={"PG_USER": "fileuser", "PG_DB": "filedb"},
        )
        assert kw["user"] == "envuser"
        assert kw["database"] == "filedb"


# ---------- .env 解析（load_pg_env） ----------


class TestLoadPgEnv:
    def test_parses_key_value_skips_comments_and_blank(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# 注释行\n"
            "\n"
            "PG_HOST=db.internal\n"
            "PG_PORT=5433\n"
            "  PG_DB = spaced \n"
            "NOT_A_PG_KEY=ignore\n",
            encoding="utf-8",
        )
        env = rerun.load_pg_env(env_file)
        assert env == {"PG_HOST": "db.internal", "PG_PORT": "5433",
                       "PG_DB": "spaced"}

    def test_missing_file_empty(self, tmp_path: Path) -> None:
        assert rerun.load_pg_env(tmp_path / "absent.env") == {}


# ---------- 时间窗助手（now_ts/fmt_ts/parse_ts/expand_window） ----------


class TestWindowHelpers:
    def test_fmt_parse_round_trip_microseconds(self) -> None:
        at = datetime(2026, 10, 9, 10, 30, 15, 123456)
        assert rerun.parse_ts(rerun.fmt_ts(at)) == at

    def test_expand_window_margin_both_sides(self) -> None:
        t0 = datetime(2026, 10, 9, 10, 0, 0)
        t1 = datetime(2026, 10, 9, 10, 0, 12)
        start, end = rerun.expand_window(t0, t1, margin_s=2.5)
        assert start == datetime(2026, 10, 9, 9, 59, 57, 500000)
        assert end == datetime(2026, 10, 9, 10, 0, 14, 500000)

    def test_expand_window_zero_margin_is_identity(self) -> None:
        t0 = datetime(2026, 10, 9, 10, 0, 0)
        t1 = datetime(2026, 10, 9, 10, 0, 12)
        assert rerun.expand_window(t0, t1, margin_s=0.0) == (t0, t1)


# ---------- 批次计费摘要（spend_summary） ----------


class TestSpendSummary:
    def test_totals_over_ok_rows_and_errors_counted(self) -> None:
        rows = [
            {"qid": "数-明1", "group": "DATA", "run_id": "run-a",
             "spend": {"calls": 3, "fallback_calls": 0, "input_tokens": 100,
                       "output_tokens": 50, "cost_yuan": 0.002112,
                       "by_caller": {}, "call_ids": ["call-1", "call-2", "call-3"],
                       "ledger_run_ids": []}},
            {"qid": "数-降1", "group": "DATA", "run_id": "run-b",
             "spend": {"calls": 2, "fallback_calls": 1, "input_tokens": 80,
                       "output_tokens": 40, "cost_yuan": 0.001,
                       "by_caller": {}, "call_ids": ["call-4", "call-5"],
                       "ledger_run_ids": []}},
            {"qid": "数-闸1", "group": "DATA", "error": "ConnectError: x",
             "spend": {"error": "ConnectError: x"}},
        ]
        s = rerun.spend_summary(
            tag="P025DRY", base="http://localhost:8001/api/v2",
            caller_prefix="v2.runtime.", rows=rows,
            generated_at="2026-10-09T10:00:00",
        )
        assert s["tag"] == "P025DRY"
        assert s["caller_prefix"] == "v2.runtime."
        assert s["questions"] == 3
        assert s["spend_ok"] == 2
        assert s["spend_errors"] == 1
        assert s["totals"] == {
            "calls": 5, "fallback_calls": 1, "input_tokens": 180,
            "output_tokens": 90, "cost_yuan": round(0.002112 + 0.001, 6),
        }
        assert [i["qid"] for i in s["items"]] == ["数-明1", "数-降1"]
        assert s["items"][0]["run_id"] == "run-a"
        assert s["items"][0]["call_ids"] == ["call-1", "call-2", "call-3"]
        assert s["errors"] == [{"qid": "数-闸1", "error": "ConnectError: x"}]

    def test_empty_rows_zero_shape(self) -> None:
        s = rerun.spend_summary(
            tag="T", base="b", caller_prefix="", rows=[], generated_at="g")
        assert s["questions"] == 0
        assert s["spend_ok"] == 0
        assert s["spend_errors"] == 0
        assert s["totals"]["calls"] == 0
        assert s["items"] == [] and s["errors"] == []


# ---------- 冻结时钟字段（frozen_date_field——V2-39 jsonl 溯源） ----------


class TestFrozenDateField:
    def test_frozen_date_iso_string(self) -> None:
        """冻结态：jsonl 行 frozen_date＝ISO 日期串（本批评分对应的「今天」）。"""
        from datetime import date

        assert rerun.frozen_date_field(date(2026, 8, 31)) == "2026-08-31"

    def test_real_mode_none(self) -> None:
        """real 对照态：frozen_date＝null（真实时钟——墙钟字段已在场）。"""
        assert rerun.frozen_date_field(None) is None


# ---------- 归集查询计划（ledger_query_plan——V2-33 run_id 直查主路） ----------


class TestLedgerQueryPlan:
    def test_run_id_present_direct_query(self) -> None:
        """jsonl 行带 run_id＝run_id 直查计划（服务侧盖章后的主路——票面 V2-33）。"""
        plan = rerun.ledger_query_plan(
            {"qid": "数-明1", "run_id": "run-abc123",
             "ask_started_at": "2026-10-09T10:00:00.000000",
             "ask_ended_at": "2026-10-09T10:00:12.000000"},
            margin_s=0.0,
        )
        assert plan == {"method": "run_id", "run_id": "run-abc123"}

    def test_run_id_blank_string_treated_as_absent(self) -> None:
        """空串/纯空白 run_id 同缺省——不拿空键直查。"""
        plan = rerun.ledger_query_plan(
            {"qid": "数-明1", "run_id": "  ",
             "ask_started_at": "2026-10-09T10:00:00.000000",
             "ask_ended_at": "2026-10-09T10:00:12.000000"},
            margin_s=0.0,
        )
        assert plan["method"] == "time_window"

    def test_run_id_absent_time_window_fallback(self) -> None:
        """无 run_id（V1 base/帧解析失败）＝时间窗兜底计划（margin 两侧外扩）。"""
        plan = rerun.ledger_query_plan(
            {"qid": "A-正6",
             "ask_started_at": "2026-10-09T10:00:00.000000",
             "ask_ended_at": "2026-10-09T10:00:12.000000"},
            margin_s=2.5,
        )
        assert plan["method"] == "time_window"
        assert plan["start"] == datetime(2026, 10, 9, 9, 59, 57, 500000)
        assert plan["end"] == datetime(2026, 10, 9, 10, 0, 14, 500000)


# ---------- 归集查询派发（collect_spend——run_id 直查＋窗兜底注记） ----------


class _FakeConn:
    """asyncpg 连接桩：按 SQL 分流返回预设行集，逐次调用留痕（sql＋args）。"""

    def __init__(self, by_run: list[dict], by_window: list[dict]) -> None:
        self._by_run = by_run
        self._by_window = by_window
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, sql: str, *args: Any) -> list[dict]:
        self.calls.append((sql, args))
        if sql is rerun.SPEND_SQL_BY_RUN or sql == rerun.SPEND_SQL_BY_RUN:
            return list(self._by_run)
        return list(self._by_window)

    async def close(self) -> None:
        return None


_ROW_RUN_X = {
    "id": "call-1", "time": datetime(2026, 10, 9, 10, 0, 1),
    "caller": "v2.runtime.understand", "alias": "MiniMax-M3", "model_key": "main",
    "input_tokens": 384, "output_tokens": 107, "cost_yuan": Decimal("0.000705"),
    "fallback": False, "run_id": "run-x",
}
_ROW_RUN_X_B = {
    "id": "call-2", "time": datetime(2026, 10, 9, 10, 0, 2),
    "caller": "v2.runtime.decision", "alias": "MiniMax-M3", "model_key": "main",
    "input_tokens": 499, "output_tokens": 129, "cost_yuan": Decimal("0.000886"),
    "fallback": False, "run_id": "run-x",
}


def _ask_row(**extra: Any) -> dict:
    row = {
        "qid": "数-明1", "group": "DATA",
        "ask_started_at": "2026-10-09T10:00:00.000000",
        "ask_ended_at": "2026-10-09T10:00:12.000000",
    }
    row.update(extra)
    return row


class TestCollectSpendDispatch:
    async def _collect(self, monkeypatch: Any, conn: _FakeConn,
                       rows: list[dict]) -> None:
        async def _fake_connect(**_kw: Any) -> _FakeConn:
            return conn

        monkeypatch.setattr(rerun.asyncpg, "connect", _fake_connect)
        await rerun.collect_spend(
            rows, dsn=None, connect_kwargs={}, caller_prefix="v2.runtime.", margin_s=0.0,
        )

    async def test_direct_hit_uses_run_id_sql_and_notes_method(
        self, monkeypatch: Any
    ) -> None:
        conn = _FakeConn(by_run=[_ROW_RUN_X, _ROW_RUN_X_B], by_window=[])
        rows = [_ask_row(run_id="run-x")]
        await self._collect(monkeypatch, conn, rows)
        assert len(conn.calls) == 1
        sql, args = conn.calls[0]
        assert sql == rerun.SPEND_SQL_BY_RUN
        assert args == ("run-x",)
        spend = rows[0]["spend"]
        assert spend["method"] == "run_id"
        assert "fallback" not in spend  # 直查命中零兜底注记
        assert spend["calls"] == 2
        assert spend["ledger_run_ids"] == ["run-x", "run-x"]

    async def test_direct_miss_falls_back_to_window_with_note(
        self, monkeypatch: Any
    ) -> None:
        """直查零行（账本未盖章的旧窗行）→退时间窗，spend.fallback 注记原因。"""
        conn = _FakeConn(by_run=[], by_window=[_ROW_RUN_X])
        rows = [_ask_row(run_id="run-old")]
        await self._collect(monkeypatch, conn, rows)
        assert [sql for sql, _ in conn.calls] == [rerun.SPEND_SQL_BY_RUN, rerun.SPEND_SQL]
        spend = rows[0]["spend"]
        assert spend["method"] == "time_window"
        assert "run_id 直查零行" in spend["fallback"]
        assert spend["calls"] == 1

    async def test_missing_run_id_goes_window_only(self, monkeypatch: Any) -> None:
        """jsonl 行无 run_id＝只走窗 SQL，fallback 注记缺因。"""
        conn = _FakeConn(by_run=[], by_window=[_ROW_RUN_X])
        rows = [_ask_row()]
        await self._collect(monkeypatch, conn, rows)
        assert [sql for sql, _ in conn.calls] == [rerun.SPEND_SQL]
        _, args = conn.calls[0]
        assert args[0] == datetime(2026, 10, 9, 10, 0, 0)
        assert args[1] == datetime(2026, 10, 9, 10, 0, 12)
        assert args[2] == "v2.runtime.%"
        spend = rows[0]["spend"]
        assert spend["method"] == "time_window"
        assert "无 run_id" in spend["fallback"]

    async def test_summary_items_carry_method(self, monkeypatch: Any) -> None:
        """摘要件 items 增 method 列（归集主路/兜底占比可审计）。"""
        conn = _FakeConn(by_run=[_ROW_RUN_X], by_window=[])
        rows = [_ask_row(run_id="run-x")]
        await self._collect(monkeypatch, conn, rows)
        s = rerun.spend_summary(
            tag="P030DRY", base="http://localhost:8011/api/v2",
            caller_prefix="v2.runtime.", rows=rows, generated_at="g",
        )
        assert s["items"][0]["method"] == "run_id"

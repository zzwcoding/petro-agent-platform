"""L-04 意图比对纯函数测试（红先绿后——票面验收第 2 条）。

被测件＝eval/results/tools/plan_rerun.py 内纯函数（跑批脚本本体照 rerun.py
惯例不进 tests/，但比对纯函数必须进 tests/——票面规定）。三路测试在案：
逐字段等值／字段缺失／期望缺件；另覆盖 golden 文件本体闸（24 题五族矩阵）
与少样本构建替身 messages 形状（票面交付物③——L-02 未合入走替身验证）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "eval" / "results" / "tools" / "plan_rerun.py"
GOLDEN = REPO / "eval" / "results" / "golden" / "plan-golden-v1.json"

_spec = importlib.util.spec_from_file_location("plan_rerun", TOOL)
assert _spec is not None and _spec.loader is not None
pr = importlib.util.module_from_spec(_spec)
sys.modules["plan_rerun"] = pr  # slots dataclass 构造要查 sys.modules[module].__dict__
_spec.loader.exec_module(pr)


# ---------- 帧构造助手（wire 形照 tests/api/test_chat_sse.py——node/node_line/verdict） ----------

def _node(key: str, note: str, state: str = "finish") -> dict[str, Any]:
    return {"id": 1, "event": "node", "data": {"key": key, "state": state, "note": note}}


def _line(key: str, text: str) -> dict[str, Any]:
    return {"id": 2, "event": "node_line", "data": {"key": key, "text": text}}


def _verdict(chain: str, slots: str) -> dict[str, Any]:
    return {"id": 3, "event": "verdict", "data": {"chain": chain, "slots": slots}}


RANK_SQL = (
    "模板装配 SQL：\nSELECT w.well_id AS 井号, w.block_name AS 区块, "
    "SUM(m.oil_output) AS 日产油量合计（吨）\nFROM agg.fct_daily_metering m\n"
    "  JOIN agg.dim_well w ON w.well_id = m.well_id\n"
    "  JOIN agg.dim_date d ON d.date = m.prod_date\n"
    "WHERE m.prod_date >= '2025-01-01' AND m.prod_date < '2026-01-01'\n"
    "GROUP BY w.well_id, w.block_name\nORDER BY SUM(m.oil_output) DESC\nLIMIT 50"
)
DETAIL_SQL = RANK_SQL.replace(
    "SUM(m.oil_output) AS 日产油量合计（吨）", "m.oil_output AS 日产油量（吨）"
).replace(
    "GROUP BY w.well_id, w.block_name\nORDER BY SUM(m.oil_output) DESC\nLIMIT 50",
    "ORDER BY m.prod_date, m.well_id\nLIMIT 50",
)


def _fast_frames(*, sql: str = RANK_SQL,
                 verdict_slots: str = "指标＝日产油量 · 报告＝《R》") -> list:
    return [
        _verdict("状态机六站链", verdict_slots),
        _node("N7.1", "三要素齐：指标＝日产油量（台账「日产油量（吨）」）· 时间＝去年 · "
                      "条数＝50——确定性校验通过，未额外调用模型"),
        _line("N7.3", sql),
    ]


# ---------- 提取：extract_plan_slots ----------


class TestExtract:
    def test_ranking_full(self) -> None:
        s = pr.extract_plan_slots(_fast_frames())
        assert s.ok is True
        assert s.metric_slot == "日产油量"
        assert s.window_start == "2025-01-01"
        assert s.window_end == "2026-01-01"
        assert s.limit_effective == 50
        assert s.ranking is True
        assert s.direction == "desc"
        assert s.verdict_metric == "日产油量"

    def test_detail_no_direction_literal(self) -> None:
        """明细模板 ORDER BY 无方向字面——direction 不可提取＝None（期望侧对明细题不钉）。"""
        s = pr.extract_plan_slots(_fast_frames(sql=DETAIL_SQL))
        assert s.ok is True
        assert s.ranking is False
        assert s.direction is None
        assert s.limit_effective == 50

    def test_default_window_note_kept(self) -> None:
        note = ("三要素齐：指标＝日产油量（台账「日产油量（吨）」）· 时间＝最近 30 天（默认） · "
                "条数＝50（默认窗——问句无显式时间）——确定性校验通过，未额外调用模型")
        s = pr.extract_plan_slots([_node("N7.1", note), _line("N7.3", RANK_SQL)])
        assert s.ok is True
        assert s.n71_note.find("默认窗") >= 0

    def test_degrade(self) -> None:
        frames = [_node("N7.1", "指标槽位未命中可出数的注册声明（模板只认绑定 agg 计量列的指标）"
                                "——降级解释链：不自由生成 SQL（不冒充审定口径）")]
        s = pr.extract_plan_slots(frames)
        assert s.ok is False
        assert s.reason.find("降级") >= 0

    def test_askback(self) -> None:
        frames = [_node("N7.1", "时间窗缺参：「最近/近期」为模糊时间词，无法确定时间窗"
                                "（近 3 天/近 30 天/本月的数完全不同——不猜数）——澄清反问挂起")]
        s = pr.extract_plan_slots(frames)
        assert s.ok is False
        assert s.reason.find("缺参反问") >= 0

    def test_not_in_chain(self) -> None:
        s = pr.extract_plan_slots([_verdict("检索问答链", "")])
        assert s.ok is False
        assert s.reason.find("未产计划") >= 0 or s.reason.find("未入") >= 0
        assert s.chain == "检索问答链"

    def test_extable_line_seen(self) -> None:
        frames = [*_fast_frames(),
                  _line("N7.2", "外表 erp_well_register 不在本轮选表命中集"
                                "——交下一站执行前表引用比对（F14）")]
        s = pr.extract_plan_slots(frames)
        assert s.extable_named == ("erp_well_register",)


# ---------- 判定：judge_intent（三路——逐字段等值／字段缺失／期望缺件）----------

EXPECTED_RANK = {
    "metric_slot": "日产油量",
    "window": {"rule": "去年", "start": "2025-01-01", "end": "2026-01-01",
               "label": "去年", "is_default": False},
    "limit_requested": None,
    "limit_effective": 50,
    "ranking": True,
    "direction": "desc",
}


class TestJudgeThreePaths:
    def test_all_fields_equal_green(self) -> None:
        """路 1：逐字段等值 → 绿。"""
        j = pr.judge_intent(EXPECTED_RANK, pr.extract_plan_slots(_fast_frames()))
        assert j.status == pr.JUDGE_GREEN
        assert j.divergent_fields == ()

    def test_value_mismatch_red(self) -> None:
        """路 1 反例：任一字段值不等 → 红并列明字段。"""
        j = pr.judge_intent(EXPECTED_RANK, pr.extract_plan_slots(_fast_frames(sql=(
            "模板装配 SQL：\nSELECT w.well_id AS 井号, SUM(m.oil_output) AS t\n"
            "FROM agg.fct_daily_metering m JOIN agg.dim_well w ON w.well_id = m.well_id\n"
            "WHERE m.prod_date >= '2025-01-01' AND m.prod_date < '2026-01-01'\n"
            "GROUP BY w.well_id\nORDER BY SUM(m.oil_output) DESC\nLIMIT 200"))))
        assert j.status == pr.JUDGE_RED
        assert "limit_effective" in j.divergent_fields

    def test_actual_field_missing_red(self) -> None:
        """路 2：字段缺失——期望已钉而实际侧提取不到 → 红并列明字段（不静默）。"""
        frames = [_verdict("状态机六站链", "指标＝日产油量"),
                  _node("N7.1", "三要素齐：指标＝日产油量（台账「日产油量（吨）」）· 时间＝去年 · "
                                "条数＝50——确定性校验通过，未额外调用模型")]
        # N7.3 SQL 行缺席 → window/limit/ranking/direction 全缺
        j = pr.judge_intent(EXPECTED_RANK, pr.extract_plan_slots(frames))
        assert j.status == pr.JUDGE_RED
        assert "window.start" in j.divergent_fields
        assert "ranking" in j.divergent_fields

    def test_expected_null_human(self) -> None:
        """路 3：期望缺件（expected_intent=null——慢路题本批不钉）→ 人审。"""
        j = pr.judge_intent(None, pr.extract_plan_slots(_fast_frames()))
        assert j.status == pr.JUDGE_HUMAN

    def test_expected_field_null_skipped(self) -> None:
        """路 3（字段级）：期望侧 None 字段不判——明细题 direction 不钉，实际 None 不红。"""
        expected = {**EXPECTED_RANK, "ranking": False, "direction": None}
        j = pr.judge_intent(expected, pr.extract_plan_slots(_fast_frames(sql=DETAIL_SQL)))
        assert j.status == pr.JUDGE_GREEN

    def test_extract_failed_human(self) -> None:
        """解析失败 → 人审列不进机器判绿红（票面口径）。"""
        j = pr.judge_intent(EXPECTED_RANK, pr.extract_plan_slots([_verdict("检索问答链", "")]))
        assert j.status == pr.JUDGE_HUMAN

    def test_verdict_contradiction_red(self) -> None:
        """verdict slots 佐证与 N7.1 指标矛盾 → 红（佐证非摆设）。"""
        frames = _fast_frames(verdict_slots="指标＝日产液量 · 报告＝《R》")
        j = pr.judge_intent(EXPECTED_RANK, pr.extract_plan_slots(frames))
        assert j.status == pr.JUDGE_RED

    def test_boundary_notrigger_held_green(self) -> None:
        """触发边界：期望不触发而实际未产计划 → 绿（边界守住——机器判在退出码内）。"""
        j = pr.judge_intent(None, pr.extract_plan_slots([_verdict("检索问答链", "")]),
                            expected_path="不触发")
        assert j.status == pr.JUDGE_GREEN

    def test_boundary_notrigger_broken_red(self) -> None:
        """触发边界：期望不触发却产了计划 → 红（不该快路直进却直进）。"""
        j = pr.judge_intent(None, pr.extract_plan_slots(_fast_frames()),
                            expected_path="不触发")
        assert j.status == pr.JUDGE_RED
        assert j.notes and j.notes[0].find("不触发") >= 0

    def test_slowpath_solved_note(self) -> None:
        """慢路预期题被快路解出（过宽桶）——不挡绿红，注记留痕归 L-03 分桶。"""
        j = pr.judge_intent(EXPECTED_RANK, pr.extract_plan_slots(_fast_frames()),
                            expected_path="慢路触发")
        assert j.status == pr.JUDGE_GREEN
        assert any("过宽" in n for n in j.notes)


# ---------- 窗口锚新鲜度：window_pin_stale ----------


class TestWindowPin:
    A = date(2026, 10, 7)  # anchor

    def test_lastyear_same_year_fresh(self) -> None:
        q = {"expected_intent": EXPECTED_RANK}
        assert pr.window_pin_stale(q, today=date(2026, 10, 7), anchor_date=self.A) is False
        assert pr.window_pin_stale(q, today=date(2026, 12, 31), anchor_date=self.A) is False

    def test_lastyear_next_year_stale(self) -> None:
        q = {"expected_intent": EXPECTED_RANK}
        assert pr.window_pin_stale(q, today=date(2027, 1, 1), anchor_date=self.A) is True

    def test_day_scope_same_day_only(self) -> None:
        q = {"expected_intent": {**EXPECTED_RANK,
                                 "window": {**EXPECTED_RANK["window"], "rule": "今年"}}}
        assert pr.window_pin_stale(q, today=date(2026, 10, 7), anchor_date=self.A) is False
        assert pr.window_pin_stale(q, today=date(2026, 10, 8), anchor_date=self.A) is True

    def test_no_intent_never_stale(self) -> None:
        assert pr.window_pin_stale({"expected_intent": None},
                                   today=date(2027, 1, 1), anchor_date=self.A) is False


# ---------- golden 文件本体闸＋少样本替身 ----------


class TestGoldenFile:
    def test_load_and_matrix(self) -> None:
        """24 题、五族分配 6/6/2/4/6、qid 唯一、必填字段齐（golden 本体进测试闸）。"""
        golden = pr.load_golden(GOLDEN)
        qs = golden["questions"]
        assert len(qs) == 24
        counts: dict[str, int] = {}
        for q in qs:
            counts[q["family"]] = counts.get(q["family"], 0) + 1
        assert counts == {"三指标×快路": 6, "慢路触发": 6, "默认窗": 2, "触发边界": 4, "红例族": 6}
        qids = [q["qid"] for q in qs]
        assert len(set(qids)) == 24
        for q in qs:
            assert q["question"].strip()
            assert q["expected_path"] in ("快路", "慢路触发", "不触发")
            assert q["answer_essentials"].strip()
            assert isinstance(q["tags"], list) and q["tags"]
            assert q["anchor_scope"] in ("day", "year")
            intent = q["expected_intent"]
            if intent is not None:
                assert intent["metric_slot"] in ("日产油量", "日产液量", "油压")
                assert set(intent) <= {"metric_slot", "window", "limit_requested",
                                       "limit_effective", "ranking", "direction"}

    def test_signoff_slot_blank(self) -> None:
        """Owner 签认位留空（拍板 5——未签认 golden 不算数）。"""
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        assert golden["owner_signoff"]["approved"] is False
        assert golden["owner_signoff"]["signed_by"] == ""

    def test_every_family_has_required_labels(self) -> None:
        """覆盖标签五族语义在案（快路可解/词面缺件/降级链/触发边界）。"""
        golden = pr.load_golden(GOLDEN)
        tags = {t for q in golden["questions"] for t in q["tags"]}
        assert {"快路可解", "词面缺件", "解析缺件", "默认窗", "触发边界", "降级链"} <= tags

    def test_fastpath_questions_have_pinned_intent(self) -> None:
        """快路题必须钉全六字段（window 端点/limit_effective 含内）；慢路题期望缺件。"""
        golden = pr.load_golden(GOLDEN)
        for q in golden["questions"]:
            intent = q["expected_intent"]
            if q["expected_path"] == "快路":
                assert intent is not None, q["qid"]
                assert intent["window"]["start"] and intent["window"]["end"]
                assert isinstance(intent["limit_effective"], int)
                assert isinstance(intent["ranking"], bool)
            # 不触发题可以钉意图（如缺参反问题不钉）也可以不钉——只约束慢路题
            if q["expected_path"] == "慢路触发":
                assert intent is None, q["qid"]


class TestFewshotStub:
    def test_messages_shape_k3(self) -> None:
        """票面交付物③替身：golden 前 3 条 → 合法 messages（system＋3 组交替）。"""
        golden = pr.load_golden(GOLDEN)
        msgs = pr.build_fewshot_messages(golden["questions"][:3])
        assert [m["role"] for m in msgs] == ["system", "user", "assistant",
                                             "user", "assistant", "user", "assistant"]
        assert msgs[0]["content"].strip()

    def test_assistant_payload_whitelist(self) -> None:
        """assistant 载荷＝五源槽位白名单（与 DRAFT_ALLOWED_KEYS 闭世界同形——禁区键不出现）。"""
        golden = pr.load_golden(GOLDEN)
        msgs = pr.build_fewshot_messages(golden["questions"][:3])
        allowed = {"metric_slot", "window", "limit_requested", "ranking", "direction"}
        forbidden = {"actor", "metric_name", "measure_column", "unit",
                     "limit_effective", "external_tables"}
        for m in msgs:
            if m["role"] != "assistant":
                continue
            payload = json.loads(m["content"])
            assert set(payload) <= allowed
            assert not (set(payload) & forbidden)
            assert payload["metric_slot"] in ("日产油量", "日产液量", "油压")
            assert set(payload["window"]) <= {"start", "end"}

    def test_k_respects_null_intent(self) -> None:
        """K 窗内遇期望缺件题（慢路）——替身跳过不产 assistant=null 载荷，取满 K 条有意图样例。"""
        golden = pr.load_golden(GOLDEN)
        # L04-07 起连着六道慢路题（expected_intent=null）——从切片取，证跳过而非产 null
        msgs = pr.build_fewshot_messages(golden["questions"][6:], k=3)
        assistants = [m for m in msgs if m["role"] == "assistant"]
        assert len(assistants) == 3
        for m in assistants:
            assert json.loads(m["content"]) is not None
        users = [m["content"] for m in msgs if m["role"] == "user"]
        # L04-13/14（默认窗）后接 L04-15/16/17（不触发·缺件）——第三条取到 L04-18
        assert users == ["各井日产油量排名", "各井日产油量是多少？", "去年日产油量明细前 200 行"]

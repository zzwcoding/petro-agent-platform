"""G-06 检索质量第一刀单测——报告池多样性（同报告至多 2 支、轮询补齐、保序）
＋A9 文档置信度配额（llm 档：席位按来源置信度轮转发放）。"""

from app.domains.chat import chains
from app.domains.chat.domain import Evidence


def _ev(i: int, report_id: str, score: float = 0.9) -> Evidence:
    return Evidence(ref="", kind="报告引用", label=f"r{i}", locator={},
                    snippet=f"s{i}", score=score, source="报告引用",
                    report_id=report_id)


def test_diversify_two_reports_interleave() -> None:
    report = [_ev(1, "rpt-A"), _ev(2, "rpt-A"), _ev(3, "rpt-B"), _ev(4, "rpt-B")]
    out = chains._report_diversify(report, 4)
    assert [e.report_id for e in out] == ["rpt-A", "rpt-A", "rpt-B", "rpt-B"]


def test_diversify_three_reports_no_single_occupation() -> None:
    """同报告不占满窗：三报告各一支即满窗（cap=4 时第四席给余量首支）。"""
    report = [_ev(i, rid) for i, rid in enumerate(
        ["rpt-A", "rpt-A", "rpt-A", "rpt-B", "rpt-C"], start=1)]
    out = chains._report_diversify(report, 4)
    reps = [e.report_id for e in out]
    assert reps.count("rpt-A") == 2  # 同报告至多 2
    assert {"rpt-B", "rpt-C"} <= set(reps)  # 其余报告不被挤光


def test_diversify_single_report_degrades_to_original() -> None:
    """单报告语料：退化为主序前 cap 支（与旧分池一致）。"""
    report = [_ev(i, "rpt-A") for i in range(6)]
    out = chains._report_diversify(report, 4)
    assert out == report[:4]


def test_diversify_small_pool_passthrough() -> None:
    report = [_ev(1, "rpt-A"), _ev(2, "rpt-B")]
    assert chains._report_diversify(report, 4) == report


# —— A9 文档置信度配额（llm 档专用，窗口 S4 就地成型） ——


def test_conf_quota_target_report_takes_majority() -> None:
    """高置信目标来源多占席：9 分来源 3 席、5 分来源 1 席、2 分无关线下来 0 席。"""
    report = [
        _ev(1, "rpt-A"), _ev(2, "rpt-A"), _ev(3, "rpt-A"),
        _ev(4, "rpt-B"), _ev(5, "rpt-B"),
        _ev(6, "rpt-C"),
    ]
    kept, note = chains._confidence_quota(
        report, {"rpt-A": 9.0, "rpt-B": 5.0, "rpt-C": 2.0}, 4)
    reps = [e.report_id for e in kept]
    assert reps == ["rpt-A", "rpt-A", "rpt-A", "rpt-B"]  # 全局序保持、只丢不重排
    assert "rpt-C" not in reps  # 无关线（<3 分）不占席
    assert "9分→3席" in note and "5分→1席" in note


def test_conf_quota_two_sources_split_seats() -> None:
    """两来源都过无关线：置信度高的先占、轮转发放至 cap 满即停。"""
    report = [
        _ev(1, "rpt-A"), _ev(2, "rpt-A"),
        _ev(3, "rpt-B"), _ev(4, "rpt-B"), _ev(5, "rpt-B"),
    ]
    kept, _note = chains._confidence_quota(report, {"rpt-A": 7.0, "rpt-B": 6.0}, 4)
    reps = [e.report_id for e in kept]
    assert reps.count("rpt-A") == 2 and reps.count("rpt-B") == 2  # 3+1 后 cap 满


def test_conf_quota_all_below_floor_falls_back_to_diversify() -> None:
    """全部来源低于无关线＝打分不可信——回退固定配额（同报告至多 2 支）。"""
    report = [_ev(i, rid) for i, rid in enumerate(
        ["rpt-A", "rpt-A", "rpt-A", "rpt-B", "rpt-C"], start=1)]
    kept, note = chains._confidence_quota(report, {"rpt-A": 1.0, "rpt-B": 2.0, "rpt-C": 0.0}, 4)
    reps = [e.report_id for e in kept]
    assert reps.count("rpt-A") == 2
    assert "回退固定配额" in note


def test_conf_quota_missing_score_treated_as_floor_below() -> None:
    """配额函数对缺失分的来源按 0 分（无关线下）处理——不占席、不炸；
    上游 _doc_confidence 已保证缺分的整份打分先回退，此为兜底语义。"""
    report = [_ev(1, "rpt-A"), _ev(2, "rpt-A"), _ev(3, "rpt-B")]
    kept, _note = chains._confidence_quota(report, {"rpt-A": 8.0}, 4)
    assert [e.report_id for e in kept] == ["rpt-A", "rpt-A"]


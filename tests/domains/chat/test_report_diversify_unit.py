"""G-06 检索质量第一刀单测——报告池多样性（同报告至多 2 支、轮询补齐、保序）。"""

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

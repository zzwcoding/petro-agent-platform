"""V2-59 澄清相位（轮2）装配治理——三删一补测试（票面附 D T1–T3）。"""

from __future__ import annotations

from datetime import date

from appv2.api.ontology_guide import OntologyGuideProvider
from appv2.runtime.guide import CLARIFY_CONTRACT


def _section_a() -> str:
    return OntologyGuideProvider(
        today=date(2026, 10, 8), include_decision_contract=False
    ).guide()


def test_section_a_three_deletions_and_keeps() -> None:  # T1
    section = _section_a()
    # 三删：块级绝迹（含连带修正的悬空指针与非法动作词残留）
    assert "◆ **发射判据**" not in section
    assert "◆ **指标名册**" not in section
    assert "收口硬规则" not in section
    assert "下方指标名册" not in section
    assert "本轮即 execute" not in section
    # 保留段完好
    for keep in ("三链路由", "窗词锚定", "台账 no_hit 处置", "limit 纪律", "发现预算"):
        assert keep in section, f"保留段缺失：{keep}"


def test_contract_no_example_p039_gate() -> None:  # T2（修订）——合同零业务名词
    assert "填写样例" not in CLARIFY_CONTRACT


def test_render_decompose_example_dynamic() -> None:  # T2 一补（运行时动态装配形）
    from appv2.runtime.orientation import render_decompose_example

    unbound_first = render_decompose_example(
        [{"slot": "检泵周期", "binding_state": "unbound", "value": "x"},
         {"slot": "日产油量", "binding_state": "bound", "value": "x"}],
        today=date(2026, 8, 31),
    )
    assert "检泵周期是多少？" in unbound_first  # 未绑定优先——演示 knowledge 链路由
    assert "检泵周期｜未绑定｜2026-08-01~2026-08-31" in unbound_first
    assert '"chain": "knowledge", "tool": "doc_retrieve"' in unbound_first
    assert unbound_first.rstrip().endswith("}]}}")
    bound_only = render_decompose_example(
        [{"slot": "日产油量", "binding_state": "bound", "value": "x"}],
        today=date(2026, 8, 31),
    )
    assert '"chain": "data", "tool": "data_query"' in bound_only
    assert "日产油量｜在册可出数" in bound_only
    assert render_decompose_example([], today=date(2026, 8, 31)) == ""


def test_existing_pins_no_regression() -> None:  # T3 既有钉不回退
    assert "faq_lookup：FAQ 现成问答库" in CLARIFY_CONTRACT  # V2-52 附 A 工具目录
    assert "零探查观察发射 finalize＝非法发射" in CLARIFY_CONTRACT  # V2-53 finalize 定义
    assert "无时间词的数据链" in CLARIFY_CONTRACT  # P-039b F2c 两分支校准

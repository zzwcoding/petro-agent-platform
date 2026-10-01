"""faq 域语义单测——归一化/去重键/标识族/提示模板（合同常量层）。"""

from app.domains.faq import domain as d
from app.domains.faq.service import _hook_from_onto_hit


def test_normalize_ignores_case_width_punct_whitespace() -> None:
    """归一化规则（合同常量）：去首尾空白、忽略大小写、全半角标点差异。"""
    assert d.normalize_text("  完成率公式是什么？ ") == "完成率公式是什么"
    assert d.normalize_text("完成率公式是什么?") == d.normalize_text("完成率公式是什么？")
    assert d.normalize_text("ＦＡＱ 10") == d.normalize_text("faq10")
    assert d.normalize_text("N-02 井") == d.normalize_text("N02井")


def test_norm_hash_stable_for_equivalent_questions() -> None:
    """导入去重 R24＝归一化 SHA256（票 49）——结果等价即同键。"""
    assert d.norm_hash("产量完成率怎么算？") == d.norm_hash("产量完成率怎么算")
    assert d.norm_hash("FAQ-1") != d.norm_hash("faq-2")


def test_id_generators_follow_contract_shapes() -> None:
    """标识族照合同演示形：faq-<n> / sq-<n> / c<n> / scan-<MMDD>。"""
    assert d.new_entry_id(["faq-1", "faq-9"]) == "faq-10"
    assert d.new_entry_id([]) == "faq-1"
    assert d.new_sim_id(["sq-101"]) == "sq-102"
    assert d.new_sim_id([]) == "sq-101"
    assert d.new_candidate_id(["c1", "c4"]) == "c5"
    from datetime import datetime

    assert d.new_scan_task_id(datetime(2026, 9, 29, 10, 0)) == "scan-0929"


def test_scan_done_hint_lists_clusters() -> None:
    """扫库完成提示模板（合同常量——多簇逐个列举/空态说明）。"""
    hint = d.scan_done_hint([d.NewCluster(id="c4", question="N-02 的完井方式是啥", freq=15)])
    assert hint == "扫描完成：本次新增 1 个候选簇——「N-02 的完井方式是啥」（15 次 / 近30天）。"
    empty = d.scan_done_hint([])
    assert "0 个候选簇" in empty and "A1" in empty  # 料源空态说明（A1 未上线）


def test_hook_from_onto_hit_value_domain() -> None:
    """本体命中展示串 → 挂接建议（指标卡/术语可挂；井对象无 hook 语义）。"""
    assert _hook_from_onto_hit("指标卡 · 自然递减率") == d.Hook(kind="metric", name="自然递减率")
    assert _hook_from_onto_hit("术语 · 时率") == d.Hook(kind="term", name="时率")
    assert _hook_from_onto_hit("井对象 · N-02") is None
    assert _hook_from_onto_hit(None) is None

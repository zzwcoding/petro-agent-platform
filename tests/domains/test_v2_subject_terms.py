"""V2-82a 主体/术语程序预识别钉测（票②a-1——`appv2/tools/subject_terms.py`）。

票面验收三钉（tickets/v2/V2-82a-主体术语识别与结构化通道.md「测试」节）：
- `subject_candidates`：油田名带空格「渤中 34-5 油田」→归一形；井号变体形 `W11`→`W-11`
  （RULE-PETRO-005 归一单点判形）；题面无主体→空；空 dump 不崩；
- `term_candidates`：别名「日产液」→命中台账规范名「日产液量」；未命中→空；术语正名
  直读 dump（`roster.metric_roster` 不含术语正名——名录源必须直读投影）；
- 纯程序零模型：同题两跑逐字相等、dump 缺位＝空集（additive 零漂移）。
"""

from __future__ import annotations

from appv2.tools import subject_candidates, term_candidates
from tests.domains.test_v2_four_phase import LEDGER_DUMP

# ---------- ①主体候选（油田/平台名归一形＋井号归一形） ----------


def test_subject_field_name_with_spaces_normalized() -> None:
    # 别名形（台账登记的空格形）命中 → 出规范名（紧凑形）。
    assert "渤中34-5油田" in subject_candidates("渤中 34-5 油田三季度注采比是多少？", LEDGER_DUMP)


def test_subject_well_variant_form_normalized() -> None:
    # 井号变体形（去连字符/大小写混写）→ RULE-PETRO-005 归一形（归一单点在 well_ids）。
    assert subject_candidates("W11 井的日产油量是多少？", LEDGER_DUMP) == ("W-11",)
    assert subject_candidates("w-11 井的日产油量是多少？", LEDGER_DUMP) == ("W-11",)
    assert subject_candidates("W_11 井的日产油量是多少？", LEDGER_DUMP) == ("W-11",)
    # 规范形本身幂等（同册井两种写法归一到同一主体）。
    assert subject_candidates("W-11 井的日产油量是多少？", LEDGER_DUMP) == ("W-11",)


def test_subject_platform_alias_form() -> None:
    # 平台名别名形（GLS-PETRO-012 修饰形）命中 → 出规范名。
    assert subject_candidates("CEP-C 生产平台有几口井？", LEDGER_DUMP) == ("CEP-C平台",)


def test_subject_multi_subject_keeps_order_and_dedup() -> None:
    # 保序去重：井号在前（扫描序）、实体名续后；重复提及只出一次。
    subjects = subject_candidates("W-22 井与 Y-41 井，哪个属于渤中 34-5 油田？", LEDGER_DUMP)
    assert subjects == ("W-22", "Y-41", "渤中34-5油田")


def test_subject_no_subject_empty() -> None:
    # 题面无主体（无井号、无闭世界实体名）→ 空集（只从题面提取，绝不推测）。
    assert subject_candidates("近 7 天各井日产液量是多少？", LEDGER_DUMP) == ()


def test_subject_empty_question_and_empty_dump() -> None:
    # 空题面＝空集；空 dump（未接线 run 同形）不崩且井号面照常（别名面回退 glossary 单点）。
    assert subject_candidates("", LEDGER_DUMP) == ()
    assert subject_candidates("   ", LEDGER_DUMP) == ()
    assert subject_candidates("W11 井的日产油量是多少？", {}) == ("W-11",)


def test_subject_deterministic_two_runs() -> None:
    # 纯程序零模型：同题两跑逐字相等。
    question = "渤中 34-5 油田的 W22 井日产油量是多少？"
    assert subject_candidates(question, LEDGER_DUMP) == subject_candidates(question, LEDGER_DUMP)


# ---------- ②术语候选（台账指标/术语名及其别名——直读 dump） ----------


def test_term_alias_question_hits_canonical_slot() -> None:
    # 题面问别名「日产液」→命中台账规范名（指标槽位「日产液量」）。
    assert "日产液量" in term_candidates("Y-41 井今天的日产液是多少？", LEDGER_DUMP)


def test_term_canonical_question_hits_self() -> None:
    # 题面问正名「检泵周期」→含自身。
    assert "检泵周期" in term_candidates("W-22 井的检泵周期是多少天？", LEDGER_DUMP)


def test_term_reads_ledger_terms_not_only_metric_roster() -> None:
    # 术语正名直读 dump（`roster.metric_roster` 不含术语正名——必须直读投影）。
    assert term_candidates("R1 井躺井了吗？", {"terms": [{"term": "躺井"}]}) == ("躺井",)


def test_term_ledger_miss_empty() -> None:
    # 未命中台账指标/术语名 → 空集。
    assert term_candidates("W-11 井生产套管的尺寸与下深是多少？", LEDGER_DUMP) == ()


def test_term_empty_dump_and_question_empty() -> None:
    # 空 dump／空题面 → 空集（additive 零漂移的两个半边）。
    assert term_candidates("Y-41 井今天的日产液是多少？", {}) == ()
    assert term_candidates("", LEDGER_DUMP) == ()


def test_term_normalization_both_sides() -> None:
    # 双侧同规归一（NFKC 全半角折叠＋casefold＋去空白）：全角题面＋空格别名形照样命中。
    found = term_candidates("问 Ｗ－１１ 井的 日 产 油 量 与 日产液 是多少？", LEDGER_DUMP)
    assert "日产油量" in found and "日产液量" in found


def test_term_deterministic_two_runs_and_order() -> None:
    # 保序（台账投影序——指标面在前、术语面续后）＋两跑逐字相等。
    question = "W-22 井的抽油机时率与躺井情况？"
    first = term_candidates(question, LEDGER_DUMP)
    assert first == term_candidates(question, LEDGER_DUMP)
    assert first.index("抽油机时率") < first.index("躺井")

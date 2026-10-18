"""V2-125 第 10 项｜V2-115 两处未迁的收口看守（回炉请求文本入 `prompts/`＋归因桶 `CALLER_REPAIR`）。

真源＝`tickets/v2/V2-115-核验失败动作回炉修复.md` 收票回写「待办：`prompts/` 迁移与归因桶
`CALLER_REPAIR`（现复用 `answer`）另立小票」；本票即那半张。

两半判据：
1. **文本迁移**（六件逐字照抄迁入）：无槽合同三件落 `prompts/constants.py` 族 `repair_request`；
   携槽模板三件＋两装配函数落 `prompts/repair_round.py`；`orchestration/repair.py` 只引不复制
   （零第二份字面）——装配输出与迁出前 `_repair_prompt`／`_gap_prompt` 逐字同形。
2. **归因桶**：`bookkeeping` 归因桶闭世界加第四桶 `repair`（`CALLER_REPAIR`），步型 `verify`；
   `orchestration/repair.py` 的 `MODEL_CALLER` 与闭世界同值（零漂移）。
"""

from __future__ import annotations

from pathlib import Path

from appv2.runtimev2.bookkeeping.constants import (
    CALLER_REPAIR,
    CALLER_STEP_KINDS,
    CALLERS,
)
from appv2.runtimev2.orchestration import repair as repair_module
from appv2.runtimev2.prompts import (
    ASSEMBLY_FUNCTIONS,
    CONTRACT_CONSTANT_FAMILIES,
    REPAIR_MATERIALS_HEAD,
    REPAIR_OUTPUT_CONTRACT,
    REPAIR_SYSTEM_CONTRACT,
    assemble_repair_gap_prompt,
    assemble_repair_prompt,
)
from appv2.runtimev2.prompts import repair_round as repair_round_module
from appv2.runtimev2.state import STEP_VERIFY

REPO_ROOT = Path(__file__).resolve().parents[2]

# 迁出前逐字（`orchestration/repair.py` V2-115 收票面字面——照抄，零改写）。
_VERBATIM_SYSTEM = (
    "你是答案校对修复器：只按给定窗内材料改写被标红的行，不新增材料里没有的数值，"
    "不改动未标红的行，不做任何跳转或动作发射。"
)
_VERBATIM_REQUEST_HEAD = (
    "【回炉修复】以下 {count} 行在核验中标红（无据／引标不可解析／归属对不上）——"
    "只重写这些行，其余行一字不动。"
)
_VERBATIM_LINE_TEMPLATE = "[{index}] {line}"
_VERBATIM_MATERIALS_HEAD = "本轮窗内正确材料（命中支）："
_VERBATIM_OUTPUT_CONTRACT = (
    '只输出一个 JSON 对象：{"lines":[{"index":1,"action":"rewrite","text":"改写后的整行"},'
    '{"index":2,"action":"drop"}]}——改引标（指向窗内正确支）／改写成「本轮材料未覆盖」／'
    "删除该行（action=drop）；不得新增窗内无据的数值。"
)
_VERBATIM_GAP_HEAD = (
    "【缺位说明】以下行经 {rounds} 轮回炉仍无材料支撑——只输出一段**缺位说明**"
    "（已试什么、仍缺什么），不得复述任何未在材料里出现的数值。"
)


# ---------- 1 文本迁移：逐字＋族＋装配函数 ----------


def test_repair_contract_constants_verbatim_in_family() -> None:
    """无槽合同三件逐字在场且入族 `repair_request`（V2-125 同批登记闭世界）。"""
    assert REPAIR_SYSTEM_CONTRACT == _VERBATIM_SYSTEM
    assert REPAIR_MATERIALS_HEAD == _VERBATIM_MATERIALS_HEAD
    assert REPAIR_OUTPUT_CONTRACT == _VERBATIM_OUTPUT_CONTRACT
    assert CONTRACT_CONSTANT_FAMILIES["repair_request"] == (
        "REPAIR_SYSTEM_CONTRACT",
        "REPAIR_MATERIALS_HEAD",
        "REPAIR_OUTPUT_CONTRACT",
    )


def test_repair_templates_verbatim_in_assembly_module() -> None:
    """携槽模板三件逐字在场（落装配模块——pin-24 合同常量无槽，先例 `RECOMMENDATION_TEMPLATE`）。"""
    assert repair_round_module.REPAIR_REQUEST_HEAD == _VERBATIM_REQUEST_HEAD
    assert repair_round_module.REPAIR_LINE_TEMPLATE == _VERBATIM_LINE_TEMPLATE
    assert repair_round_module.REPAIR_GAP_HEAD == _VERBATIM_GAP_HEAD


def test_repair_assemblers_in_closed_world() -> None:
    """两装配函数入 `ASSEMBLY_FUNCTIONS` 闭世界（族名单同批改规格清单）。"""
    assert "assemble_repair_prompt" in ASSEMBLY_FUNCTIONS
    assert "assemble_repair_gap_prompt" in ASSEMBLY_FUNCTIONS


def test_repair_prompt_assembly_verbatim_output() -> None:
    """装配输出逐字同形（迁出前 `_repair_prompt` 的 `\\n` 拼接形——字节级零漂移）。"""
    expected = "\n".join(
        [
            _VERBATIM_REQUEST_HEAD.format(count=2),
            _VERBATIM_LINE_TEMPLATE.format(index=1, line="行一"),
            _VERBATIM_LINE_TEMPLATE.format(index=2, line="行二"),
            _VERBATIM_MATERIALS_HEAD,
            "材料段",
            _VERBATIM_OUTPUT_CONTRACT,
        ]
    )
    assert (
        assemble_repair_prompt(["行一", "行二"], materials_text="材料段") == expected
    )

    expected_gap = "\n".join(
        [
            _VERBATIM_GAP_HEAD.format(rounds=2),
            _VERBATIM_LINE_TEMPLATE.format(index=1, line="行一"),
            _VERBATIM_MATERIALS_HEAD,
            "材料段",
        ]
    )
    assert (
        assemble_repair_gap_prompt(2, ["行一"], materials_text="材料段") == expected_gap
    )


def test_repair_text_single_source_no_duplicate() -> None:
    """单源：回炉请求文本只在本族／装配模块在场——编排块零字面副本（消费方只引不复制）。"""
    source = (REPO_ROOT / "appv2" / "runtimev2" / "orchestration" / "repair.py").read_text(
        encoding="utf-8"
    )
    for literal in (
        _VERBATIM_SYSTEM,
        _VERBATIM_MATERIALS_HEAD,
        _VERBATIM_OUTPUT_CONTRACT,
        _VERBATIM_REQUEST_HEAD,
        _VERBATIM_GAP_HEAD,
    ):
        assert literal not in source, f"编排块残留副本：{literal[:16]}…"
    # 迁入面＝包根引用（装配函数＋规章段），零本地文本常量
    assert repair_module.REPAIR_SYSTEM_CONTRACT is REPAIR_SYSTEM_CONTRACT


# ---------- 2 归因桶：第四桶 `repair` ----------


def test_caller_repair_bucket_registered() -> None:
    """归因桶闭世界四值＋桶→步型分派（`repair`→`verify`）；编排块 `MODEL_CALLER` 与闭世界同值。"""
    assert CALLER_REPAIR == "repair"
    assert CALLERS == {"understand", "decision", "answer", "repair"}
    assert CALLER_STEP_KINDS["repair"] == STEP_VERIFY
    assert repair_module.MODEL_CALLER == CALLER_REPAIR


def test_caller_repair_not_answer() -> None:
    """回炉调用**不再**复用 `answer` 桶（V2-115 待办原状＝复用 `answer`）。"""
    assert repair_module.MODEL_CALLER != "answer"

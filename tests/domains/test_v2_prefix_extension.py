"""V2-134 验收钉①：同一 run 内相邻调用的**完整请求**互为前缀延伸（追加形）。

**判据同源**＝`scripts/ladder_run.py:421` `_prefix_report`（该工具自称「KV 纪律验收线」）——
本文件**不自立第二判据**：比对面＝completer 记录的**完整请求 messages**（含链首背景块），
比对法＝逐条 dict 相等的前缀延伸。

**Owner 2026-10-19 裁定**：本判据＝**结构性追加形**（设计是否符合 KV 缓存原则），
与「供应商是否支持缓存／命中多少」无关——故本文件零 `cached_tokens` 类断言。

病灶面（本钉要看守的回归）：H 批（2026-10-17）把四相位规章段改走「每请求前置 system」，
跨相位首调用前缀在**第 0 条**即分叉 ⇒ 真机 `run-a7f03490` 9 对中 5 对断裂
（`run-918b94c4` 3 对 3 断）。V2-134 把规章段并回 user 首入包后，本钉应全绿。
"""

from __future__ import annotations

from typing import Any

from tests.domains.test_v2_four_phase import (
    V2_UNDERSTAND,
    V2LedgerPort,
    V2QueueEngine,
    V2RunStore,
    _rows_outcome,
    freeze,
    v2_data_match,
    v2_decision_turn,
    v2_decompose,
    v2_ledger_dump,
    v2_ledger_note,
    v2_matches,
    v2_registry,
    v2_run,
    v2_runtime,
    wire_ledger_projection,
)


def _breaks(calls: list[tuple[str, list[dict[str, str]]]]) -> list[str]:
    """相邻调用前缀延伸判定（判据同源 `ladder_run._prefix_report`）——返回断裂描述列（空＝全绿）。"""
    breaks: list[str] = []
    for index in range(1, len(calls)):
        prev_caller, prev = calls[index - 1]
        cur_caller, cur = calls[index]
        if not (len(prev) <= len(cur) and cur[: len(prev)] == prev):
            breaks.append(f"#{index} {prev_caller}→{cur_caller}")
    return breaks


async def _run_standard(*, guide_text: str = "") -> tuple[Any, Any, list[Any]]:
    """标准四相位真跑（零 DB／零真实端口；剧本 completer 记录完整请求）。"""
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script={
                "understand": [V2_UNDERSTAND],
                "decision": v2_decision_turn(
                    clarify=v2_decompose(
                        subtask_id="s1",
                        question="2025-09-01 到 09-03 各井日产油量",
                        ledger_notes=note,
                        chain="data",
                    ),
                    toolmatch=v2_matches(
                        v2_data_match(
                            subtask_id="s1",
                            slot="日产油量",
                            start="2025-09-01",
                            end="2025-09-03",
                        )
                    ),
                ),
                "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
            },
            registry=v2_registry(engine=V2QueueEngine([_rows_outcome()])),
            guide_text=guide_text,
        )
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    return runtime, completer, events


async def test_request_prefix_extension_across_all_calls() -> None:
    """① 全调用前缀延伸：一次标准 run 的**每**相邻调用对皆前缀延伸（零断裂）。

    覆盖面：understand → clarify → toolmatch → answer 四相位**跨相位**对全在内——
    即 H 批的病灶面（跨相位首调用第 0 条分叉）在本钉下直接可检。
    """
    _runtime, completer, events = await _run_standard(guide_text="§A 指南（测试注入）")
    assert events[-1].data["status"] == "completed"

    calls = [(str(caller), [dict(m) for m in messages]) for caller, messages in completer.calls]
    assert len(calls) >= 4, [caller for caller, _ in calls]  # 四相位都真跑到

    breaks = _breaks(calls)
    assert breaks == [], f"请求前缀延伸断裂（KV 失效）：{breaks}"


async def test_request_prefix_extension_cross_phase_pair_is_the_watched_regression() -> None:
    """② 病灶对专检：**跨相位**相邻对（澄清→匹配）亦前缀延伸。

    单独立此钉＝把 H 批回归的那一对显式写进验收面（避免将来「全绿」被无关调用的同相位对
    平均掉）：澄清轮与匹配轮是相邻两次 decision 调用，规章段不同相位——正是旧判据「按链段
    比对」放过、而真机 KV 失效的那一对。
    """
    _runtime, completer, events = await _run_standard()
    assert events[-1].data["status"] == "completed"

    decisions = [
        [dict(m) for m in messages] for caller, messages in completer.calls if caller == "decision"
    ]
    assert len(decisions) >= 2, "澄清／匹配两轮 decision 未都发生"
    first, second = decisions[0], decisions[1]
    # 跨相位对：整请求前缀延伸（第 0 条＝链首背景块，两轮逐字相同）
    assert second[: len(first)] == first
    assert first[0] == second[0]
    assert first[0]["role"] == "system"


async def test_request_prefix_extension_chain_is_append_only() -> None:
    """③ 追加形本体：终态链＝各调用请求的**后缀延伸**，且链上 `system` 恰一条＝链首背景块。

    与 ① 互为两面：① 看「请求之间」；③ 看「请求＝链的前缀」（即请求未携带链外内容——
    H 批的每请求前置 system 正是「链外内容」，本钉把它挡在门外）。
    """
    _runtime, completer, events = await _run_standard()
    assert events[-1].data["status"] == "completed"

    state = V2RunStore().load(events[-1].data["run_id"])
    chain = [dict(m) for m in state.messages]
    for caller, messages in completer.calls:
        request = [dict(m) for m in messages]
        assert request == chain[: len(request)], caller  # 请求＝链前缀（零链外内容）
    roles = [str(m["role"]) for m in chain]
    assert roles.count("system") == 1, roles
    assert chain[0]["role"] == "system"

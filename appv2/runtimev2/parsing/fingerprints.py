"""指纹器材四件（同参重投闸的**指纹面**——`specs/parsing.md` 行为 13／接口定义节 ④）。

真源 `appv2/runtime/graph.py` L537-L571 逐字迁移（V1 私有 `_payload_fingerprint` 等去下划线
公开化——差异点⑦）；`is_same_param_replay` 形参由 V1 `emission` 拆解为 `fingerprints`
（随 legacy 退场，判定语义逐点不变）。

- `payload_fingerprint`：载荷规范指纹＝键序归一（`sort_keys`）＋紧凑分隔符＋不转义非 ASCII
  （R-A1-24）；
- `discover_fingerprint`：发现调用指纹＝`{"tool": 名, "args": 参}` 键序归一 JSON（R-A1-25；
  与载荷指纹的归一规范不同——两规范各自保留、不跨面比较，V1 事实面 D-A1-13）；
- `emission_fingerprints`：按支拆算（单支单形，`plan` 支在前；两皆空 → 空元组——R-A1-26）；
- `is_same_param_replay`：同参判定（空元组 → 放行；全部支都在实录 → 拦；任一支为新参 → 放行
  ——R-A1-27／R-A1-28）。

**触发、拦截与回喂归消费方**（`execution`——`specs/execution.md` 行为 14；流水 30②）：本块只产
纯函数器材、零触发面。`discover_fingerprint` 的**行为面**（空手探查记指纹＋同参空手重发发射级拒）
挂 `specs/execution.md` 行为 13（空手闸）——**两「同参」闸勿混**，本块只供该器材。
"""

import json
from collections.abc import Collection
from typing import Any


def payload_fingerprint(payload: Any) -> str:
    """载荷规范指纹：键序归一＋紧凑分隔符＋不转义非 ASCII（R-A1-24）。"""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def discover_fingerprint(tool_name: str, args: Any) -> str:
    """发现调用指纹：`{"tool": 名, "args": 参}` 键序归一 JSON（R-A1-25；默认分隔符）。

    参数改了＝新尝试（门开着）；本件与 `payload_fingerprint` 属不同命名空间，不可跨面比较。
    """
    return json.dumps({"tool": tool_name, "args": args}, sort_keys=True, ensure_ascii=False)


def emission_fingerprints(
    plan: dict[str, Any] | None, retrieval_need: dict[str, Any] | None
) -> tuple[str, ...]:
    """发射指纹按支拆算：单支单形（`plan` 支在前）；两皆空 → 空元组（R-A1-26）。

    不算整发射混合形——整形与 execute 侧逐支实录永不匹配，闸会空转。
    """
    fingerprints: list[str] = []
    if plan is not None:
        fingerprints.append(payload_fingerprint({"plan": plan, "retrieval_need": None}))
    if retrieval_need is not None:
        fingerprints.append(
            payload_fingerprint({"plan": None, "retrieval_need": retrieval_need})
        )
    return tuple(fingerprints)


def is_same_param_replay(fingerprints: tuple[str, ...], executed: Collection[str]) -> bool:
    """同参二次发射判定（R-A1-27／R-A1-28）：零支 → 放行；全支已在实录 → 拦；任一支新参 → 放行。

    `executed`＝调用方传入口（真源 `RunState.executed_payloads`）——本件只读、不改。
    """
    if not fingerprints:
        return False
    return all(fingerprint in executed for fingerprint in fingerprints)

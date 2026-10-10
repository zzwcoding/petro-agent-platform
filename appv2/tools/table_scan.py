"""tools.table_scan —— 越集后置确定性扫描件（V2-44——Owner 签发 2026-10-10）。

高危安检失效双实证（P-039b/P-040 回报）的根治件：现行越集审批闸依赖模型在
plan 里申报 external_tables——模型漏报则闸空转（数-察2 形：toolmatch 漏带
external_tables→审批未触发→Z-16 1335.52 直出数）。本件＝**后置确定性扫描**
：闸不看出申报，看实际执行请求——引擎执行面（前置条件机→批量执行）在 SQL
定稿后、执行发生前，对执行请求的表名集做白名单比对：

1. **执行前表集提取**（票面任务 1——agg/raw/lake/schema 全解析）：
   - 模板基座面＝agg 三表（STAR_TABLES——引擎模板构造面的固定表集：SQL 定稿
     蓝图无论计划字段如何只触这三表，基座恒白名单）；
   - 问句词面外表引用＝别名面（detect_external_tables——EXTERNAL_TABLE_ALIASES
     单源复用，零第二份别名册）＋schema 限定面（词面 agg/raw/lake/schema 前缀
     的 schema.table 引用逐个捕获——前缀剥除裸名归一比对）。
2. **白名单比对**（票面任务 2）：表集 vs 审定开放集（放行名单＝ToolContext
   审批态 approved_tables——sem_join_whitelist 审批语义的 V2 落点（A2 裁决）
   ＋agg 三表基座）——出现未审定表＝拦截在执行前（前置条件机 blocked_ask
   external_table_approval 同形挂起——复用现有审批帧与 resume 通道，零新
   交互面）。
3. **申报/实扫双闸并存**（票面任务 3）：申报面（引擎 N7.4c＋前置条件机申报
   比对现语义）零改动——实扫是兜底不是替代；计划未申报而实扫命中＝漏报捕获
   （miss_declared 面——机读留痕不静默）。

零 I/O、零 LLM（纯函数——R1 红线：判定面代码无模型通道）；依赖只许
appv2.query 公开接口（别名册/基座常量/词面检测单源）。消费点＝
precondition.judge 闸 2（前置条件机——执行前最后一道固定代码闸）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from appv2.query import STAR_TABLES, detect_external_tables

# schema 限定引用面（票面任务 1「agg/raw/lake/schema 全解析」——问句词面的
# schema.table 引用逐个捕获；白名单 schema 层闭世界四值，前缀剥除裸名归一）。
_SCHEMA_TABLE_RE = re.compile(
    r"\b(agg|raw|lake|schema)\.([a-z_][a-z0-9_]*)\b", re.IGNORECASE
)

# agg 三表基座（裸名投影——STAR_TABLES 单源派生：agg.fct_daily_metering →
# fct_daily_metering；模板构造面的固定表集恒白名单，词面基座引用零误拦）。
TEMPLATE_BASE_TABLES: frozenset[str] = frozenset(
    name.rsplit(".", 1)[-1] for name in STAR_TABLES
)


@dataclass(frozen=True, slots=True)
class TableScanFindings:
    """实扫结论（申报/实扫双面并载——漏报捕获面判定与留痕的唯一判据源）。

    - declared_tables：计划申报集（原样保序——申报面现语义比对消费形）；
    - detected_tables：实扫提取集（问句词面——不看申报）；
    - unapproved：未审定表（申报∪实扫对开放集——拦截判据，保序去重）；
    - miss_declared：实扫命中而计划未申报（漏报捕获面——机读留痕判据）。
    """

    declared_tables: tuple[str, ...]
    detected_tables: tuple[str, ...]
    unapproved: tuple[str, ...]
    miss_declared: tuple[str, ...]


def _bare(table: str) -> str:
    """schema 前缀剥除（裸名归一——agg/raw/lake/schema 全解析的比对形）。"""
    return table.rsplit(".", 1)[-1].strip()


def extract_external_table_refs(question: str) -> tuple[str, ...]:
    """问句词面外表引用提取（确定性零 LLM——实扫面，不看申报）。

    两面单源：别名面＝detect_external_tables（EXTERNAL_TABLE_ALIASES——F14
    越集比对触发源，appv2.query 单源复用）；schema 限定面＝词面 schema.table
    引用捕获（前缀剥除裸名归一——agg 基座命中同样归裸名，比对面恒白名单）。
    去重保序（首现序）。
    """
    seen: list[str] = []

    def _add(raw: str) -> None:
        name = _bare(raw)
        if name and name not in seen:
            seen.append(name)

    for table in detect_external_tables(question):
        _add(table)
    for match in _SCHEMA_TABLE_RE.finditer(question):
        _add(match.group(2))
    return tuple(seen)


def scan_unapproved_tables(
    question: str,
    plan: Mapping[str, Any],
    *,
    approved_tables: tuple[str, ...],
) -> TableScanFindings:
    """执行前白名单比对（纯函数——零 LLM 零 I/O；前置条件机闸 2 消费单点）。

    - 申报面现语义逐字保留：declared 对放行名单 identity 比对（原值原序——
      拦停措辞/帧形零漂移）；
    - 实扫兜底面：detected 对开放集（放行名单＋agg 三表基座）比对——漏报也拦；
    - miss_declared＝detected − declared（漏报捕获面——申报在案即非漏报）。
    """
    declared = tuple(
        dict.fromkeys(
            str(t).strip()
            for t in (plan.get("external_tables") or ())
            if str(t).strip()
        )
    )
    detected = extract_external_table_refs(question)
    open_set = set(approved_tables) | TEMPLATE_BASE_TABLES
    unapproved: list[str] = []
    for table in declared:  # 申报面现语义（identity 比对——不动）
        if table not in approved_tables and table not in unapproved:
            unapproved.append(table)
    for table in detected:  # 实扫兜底面（基座恒开放——漏报也拦）
        if table not in open_set and table not in unapproved:
            unapproved.append(table)
    return TableScanFindings(
        declared_tables=declared,
        detected_tables=detected,
        unapproved=tuple(unapproved),
        miss_declared=tuple(t for t in detected if t not in declared),
    )

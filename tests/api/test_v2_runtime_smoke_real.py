"""R14 红线②终实证冒烟（RUNTIME_SMOKE=1 门控）——生产组合真网关一轮 ask。

跑法（V2-19 票面任务 5；P-008 票面 R14 条目）：
    RUNTIME_SMOKE=1 uv run pytest tests/api/test_v2_runtime_smoke_real.py -q -s

真装配含义（V2-19 起为**生产组合根**——create_app registry 缺省＝真引擎）：
create_app 真起（真实 primary PG@5433 演示库——config/database.yaml）＋真
gateway.complete（B6 唯一出口——GatewayService＋LlmClient，petro-main＝
MiniMax-M3 真调用真计费）＋三引擎生产读面真链路——PgKnowledgeStore（sem_*
台账直读）／PgQueryExecutor（agg 星型真 SQL＋dim_well 区块列＋batch_id 回
血缘④）＋生产水位读缝（water_line 汇总层直读＋T-1 判定，DE-16 翻板从
config 进组合根——config 缺省 true＝闸在位）／PgFragmentLibrary（kb_* 直读
＋RemoteEmbedder——问数题不触检索，装配在位即如实）。

流程（每题一轮 ask 走通六步 loop）：
① POST /api/v2/chat/asks（真实 MiniMax 出理解/计划/草稿）→ SSE 流保留帧 done
   收场，终局 verdict subtype=final；
② 六步合同次序钉死：understand→plan→tool→observe→verify→answer 全在流且
   恰此序（V2-09 验收①——真模型格式校准后不再 understand 拒答中途收口），
   全流零 refused notice；
③ GET run 状态＝completed（run 状态机收口）；
④ V2-19 验收③：血缘④「数据截至批次」带真批次号——observation 流中血缘卡
   支含「批次 b-*」（b-a1a61db9f458 单源族＝演示库 agg 单一批次，逐字断言）；
⑤ R14 核心：caller 归因落 spend 记录——`v2.runtime.*` caller 桶本轮在场
   且 cost>0（GatewayChatModel→gateway.complete 的 B6 归因链真账本实证）；
⑥ V2-23 内容级断言（防「六步走完了但答案是拒答」式假绿）：数-明1 答案须含
   明细表首行 N-01 21.16（LIMIT 50 截断形态下仍如实出表——verify 表格/血缘卡
   豁免后不再整表吞成「未找到」，P-015 实测 rewritten=34 根因）；数-排1 答案
   须含排名首行 Z-16 5839.6（去年窗合计 5839.63 的前缀形）；全部问数题答案须
   含截断收口注记（血缘⑤ LIMIT 收口确定性随答案）。

重跑幂等：每轮新增真流水（演示库量级，GATEWAY_SMOKE/CHAT_SMOKE 同款处置）；
断言只看「本轮桶在场」不看全库计数。证据打印（-s 采集）：每题的理解/计划/
核验步/答案/血缘④与 spend 行——回报 P-013 冒烟输出原文（血缘批次号证据）的来源。
"""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

import pytest
from sqlalchemy import select

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("RUNTIME_SMOKE") != "1",
        reason="R14 真装配冒烟需 RUNTIME_SMOKE=1（真实 PG/LLM 计费——不进常规门禁）",
    )
]

# 数-明1 类标准题三形：显式窗（P-008 偏差 5 原题——「不再 understand 拒答」回归钉）
# ＋数-明1 原句（few-shot 样张同题——「去年」相对窗经样张落 ISO 端点）
# ＋数-排1（V2-23 内容级断言面）。值组＝答案内容级必含子串（V2-23 票面③——
# 防「六步走完了但答案是拒答」式假绿；空组＝只作结构断言）。
SMOKE_QUESTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("2025 年 9 月 1 日到 3 日的日产油量", ()),
    ("去年各井每天的日产油量是多少？", ("N-01", "21.16")),  # 明细表首行（截断形态仍出表）
    ("去年日产油量最高的井是哪口？", ("Z-16", "5839.6")),  # 排名首行（合计 5839.63 前缀形）
)
REACT_STEP_HEAD = ["decision", "decision", "execute", "observe", "decision"]
# ReAct 周期钉序（V2-31）：understand(decision)→decision(execute)→execute→
# observe→decision(finalize)→answer(起草)→verify→answer(收口)。
REACT_STEP_TAIL = ["answer", "verify", "answer"]
TODAY = date(2026, 10, 8)
DEMO_BATCH_ID = "b-a1a61db9f458"  # 演示库 agg 单一批次（V2-11 seed 单源——单源族）
ACTOR = {"X-Dev-User": "aqiang"}


def _parse_frames(text: str) -> list[tuple[str, dict[str, Any]]]:
    frames: list[tuple[str, dict[str, Any]]] = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        assert event is not None and data is not None
        frames.append((event, data))
    return frames


def test_runtime_production_smoke_real_gateway() -> None:
    from fastapi.testclient import TestClient

    from appv2.api import create_app
    from appv2.infra.clock import now
    from appv2.infra.config import load_database_specs
    from appv2.infra.db import ConnectionManager
    from appv2.infra.gateway import GatewayService, SpendFilter
    from appv2.infra.gateway.store import SpendRecord, SpendStore
    from appv2.infra.llm_client import LlmClient
    from appv2.runtime import RunStore

    db = ConnectionManager(load_database_specs())  # 真实 primary PG（演示库）
    gateway = GatewayService(db, LlmClient())  # B6 唯一出口真件（MiniMax 真引擎）
    # 生产组合根（V2-19 任务 4）：registry 缺省＝三引擎生产读面真装配
    # ＋DE-16 翻板从 config 进组合根（config 缺省 true＝水位闸在位）。
    app = create_app(db=db, completer=gateway, today=lambda: TODAY)
    store = RunStore(db)
    started_at = now()
    batch_run_ids: list[str] = []  # 本批 session 帧 run_id（V2-33 全等对账锚）

    with TestClient(app) as client:
        for question, content_expect in SMOKE_QUESTIONS:
            # —— ① 一轮 ask：真实 MiniMax 走六步 loop，SSE 保留帧收场 ——
            resp = client.post("/api/v2/chat/asks", json={"question": question}, headers=ACTOR)
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            frames = _parse_frames(resp.text)
            run_id = frames[0][1]["run_id"]
            batch_run_ids.append(run_id)  # V2-33：账本 run_id 全等对账锚
            assert frames[0][0] == "session" and frames[0][1]["resume"] is False
            assert frames[-1][0] == "done" and frames[-1][1]["run_id"] == run_id
            # —— ② ReAct 周期走完至 answer（真模型自主选 data_query 出数） ——
            step_kinds = [d["step"] for n, d in frames if n == "step"]
            assert step_kinds == REACT_STEP_HEAD + REACT_STEP_TAIL, (
                f"ReAct 周期未走完：{step_kinds}"
            )
            refused = [
                d for n, d in frames if n == "notice" and d.get("type") == "refused"
            ]
            assert not refused, f"理解/决策拒答链被触发：{refused}"
            finals = [d for n, d in frames if n == "verdict" and d.get("subtype") == "final"]
            assert finals and finals[-1]["run_id"] == run_id  # R10 终局判定（wire 定型形）
            # —— ③ run 状态机收口 ——
            status = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR).json()
            assert status["status"] == "completed"
            assert status["manifest_digest"] == finals[-1]["manifest_digest"]
            # —— ④ V2-19 验收③：血缘④真批次号（agg 星型真 SQL 随行——单源族） ——
            lineage_obs = [
                d
                for n, d in frames
                if n == "observation" and "④ 数据截至批次" in str(d.get("content", ""))
            ]
            assert lineage_obs, "血缘卡④（数据截至批次）未随结果必出"
            watermark_line = str(lineage_obs[-1]["content"])
            assert f"批次 {DEMO_BATCH_ID}" in watermark_line, (
                f"血缘④未带真批次号（期望 {DEMO_BATCH_ID}）：{watermark_line}"
            )
            # —— ⑥ V2-23 内容级断言：答案是内容不是拒答 ——
            # （流尾末条 text 帧＝答案收口——与 run.answer 同源，无需先查 run 行。）
            answer_text = next(
                (d.get("content", "") for n, d in reversed(frames) if n == "text"), ""
            )
            for needle in content_expect:
                assert needle in answer_text, (
                    f"答案缺内容级断言值 {needle!r}（问句：{question}）：{answer_text[:400]}"
                )
            assert "收口注记" in answer_text and "LIMIT" in answer_text, (
                f"答案缺截断收口注记（问句：{question}）：{answer_text[:400]}"
            )
            # —— 证据打印（-s 采集——回报 P-013 冒烟输出原文来源） ——
            async def _evidence(run_id: str = run_id) -> tuple[Any, Any]:
                return await store.get_run(run_id), await store.list_steps(run_id)

            run_row, steps = client.portal.call(_evidence)
            understanding = next(
                (d.get("content", "") for n, d in frames if n == "text"), ""
            )
            plan_payload = next(
                (
                    (s.payload or {}).get("emission", {}).get("plan")
                    for s in steps
                    if s.step_type == "decision"
                    and (s.payload or {}).get("emission", {}).get("plan")
                ),
                None,
            )
            verify_title = next(
                (s.title for s in steps if s.step_type == "verify"), ""
            )
            print(f"\nSMOKE 问句：{question}")
            print(f"SMOKE 理解（真模型两行/降级产）：{understanding}")
            print(f"SMOKE 计划（真模型 JSON 产）：{json.dumps(plan_payload, ensure_ascii=False)}")
            print(f"SMOKE 核验（verify 步标题）：{verify_title}")
            print(f"SMOKE 答案首 200 字：{(run_row.answer or '')[:200]}")
            print(f"SMOKE 血缘④（数据截至批次）：{watermark_line}")

        # —— ⑤ R14 核心：caller 归因落 spend 记录（红线②真账本实证） ——
        # V2-33 run_id 盖章：本轮新行 run_id 逐笔非空且与本批 session 帧 run_id
        # 全等（账本归属链真实证——存储行直读，SpendView 合同投影不扩列）。
        spend_store = SpendStore(db)
        batch_run_ids = set(batch_run_ids)

        async def _mine_rows() -> Any:
            async with db.readonly() as session:
                rows = (
                    (
                        await session.execute(
                            select(SpendRecord).where(
                                SpendRecord.time >= started_at,
                                SpendRecord.caller.like("v2.runtime.%"),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            return list(rows)

        async def _spend_page() -> Any:
            return await spend_store.page(SpendFilter(), page_size=200)

        page = client.portal.call(_spend_page)  # portal＝应用事件循环
        mine = [
            row
            for row in page.items
            if str(row.caller or "").startswith("v2.runtime.") and row.time >= started_at
        ]
        assert mine, "本轮 runtime 调用未落 spend 账本——红线②归因链断裂"
        assert {row.caller for row in mine} >= {
            "v2.runtime.understand", "v2.runtime.decision",
        }
        assert all(row.cost_yuan > 0 for row in mine)  # 真调用真计费（非估算零值）
        ledger_rows = client.portal.call(_mine_rows)
        assert ledger_rows, "存储行直读零行——账本读形断"
        assert all(row.run_id for row in ledger_rows), (
            f"账本新行 run_id 存在空值——盖章链路断裂："
            f"{[r.id for r in ledger_rows if not r.run_id]}"
        )
        assert {str(row.run_id) for row in ledger_rows} <= batch_run_ids, (
            f"账本 run_id 越批（与本批 session 帧不全等）："
            f"{sorted({str(r.run_id) for r in ledger_rows} - batch_run_ids)}"
        )
        for row in ledger_rows:
            print(
                f"spend: caller={row.caller} alias={row.alias} fallback={row.fallback} "
                f"cost={row.cost_yuan} in={row.input_tokens} out={row.output_tokens} "
                f"run_id={row.run_id}"
            )

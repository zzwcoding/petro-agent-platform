"""真装配冒烟（GATEWAY_SMOKE=1 门控）——P1-10 端点 8 聚合真数＋caller 归因落账。

跑法（tickets/phase1/README.md P1-10 验收）：
    GATEWAY_SMOKE=1 uv run pytest tests/test_gateway_smoke_real.py -q

真装配含义：main.py lifespan 真起（真实 primary PG16@5433 演示库）＋真
gateway.complete（B6 唯一出口——petro-main 真调用真计费两笔）。真调用经
TestClient portal 在应用事件循环内执行（complete 无 HTTP 端点——B6 是域
间唯一出口，账本与聚合读面走真 HTTP）。

流程（真 complete 两笔→聚合三维度真数）：
① 真 complete 两笔：caller 各不相同（smoke.<tag>.a/.b）；
② 端点 8 聚合三维度真数：caller 维度本轮两桶在场＋存量 unattributed 桶、
   花费降序；model 维度 main 桶 alias=petro-main 且 calls≥2；day 维度时序
   升序且末桶＝今日；sums＝窗口全量合计不随分页截断（pageSize=1 对照）；
③ 端点 4 keyword（pg_trgm SQL 检索）按调用号命中本轮流水＋caller 归因回显。

重跑幂等：每轮新增两笔真流水（演示库量级，KB_SMOKE/CHAT_SMOKE 同款处置）；
caller 带 tag 每轮唯一，断言只看「本轮桶在场」不看全库计数。
"""

import os
import uuid

import pytest

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("GATEWAY_SMOKE") != "1",
        reason="真装配冒烟需 GATEWAY_SMOKE=1（真实 PG/LLM 计费——不进常规门禁）",
    )
]


def test_gateway_spend_stats_real_smoke() -> None:
    from fastapi.testclient import TestClient

    from app.infra.clock import now
    from app.main import app

    tag = uuid.uuid4().hex[:6]
    caller_a = f"smoke.{tag}.a"
    caller_b = f"smoke.{tag}.b"
    with TestClient(app) as client:  # lifespan 真起（真 PG＋真 LLM 注册表）
        assert client.get("/health").json() == {"status": "ok"}
        gateway = app.state.gateway

        # —— ① 真 complete 两笔（真 LLM、真记账、caller 归因落列；portal＝应用事件循环） ——
        async def _two_calls() -> tuple[object, object]:
            first = await gateway.complete(
                "petro-main",
                [{"role": "user", "content": f"冒烟心跳{tag}——请只回答两个字：正常"}],
                caller=caller_a,
                max_tokens=32,
            )
            second = await gateway.complete(
                "petro-main",
                [{"role": "user", "content": f"冒烟心跳{tag}——请只回答两个字：正常"}],
                caller=caller_b,
                max_tokens=32,
            )
            return first, second

        first, second = client.portal.call(_two_calls)
        assert first.fallback is False and second.fallback is False
        assert len({first.call_id, second.call_id}) == 2  # 两笔独立调用号

        # —— ② 端点 8 三维度真数 ——
        caller_stats = client.get("/api/gateway/spend-stats?group_by=caller&range=all").json()
        caller_buckets = {i["caller"] for i in caller_stats["items"]}
        assert {caller_a, caller_b, "unattributed"} <= caller_buckets  # 本轮归因桶＋存量桶
        mine = [
            i for i in caller_stats["items"] if i["caller"] in (caller_a, caller_b)
        ]
        assert all(m["calls"] == 1 and m["cost_yuan"] > 0 for m in mine)
        costs = [i["cost_yuan"] for i in caller_stats["items"]]
        assert costs == sorted(costs, reverse=True)  # 花费降序——谁花得多排前面

        model_stats = client.get("/api/gateway/spend-stats?group_by=model&range=all").json()
        main_row = next(i for i in model_stats["items"] if i["model_key"] == "main")
        assert main_row["alias"] == "petro-main" and main_row["calls"] >= 2  # 本轮两笔走主用

        day_stats = client.get("/api/gateway/spend-stats?group_by=day&range=all").json()
        days = [i["day"] for i in day_stats["items"]]
        assert days == sorted(days)  # 时序升序
        assert days[-1] == now().strftime("%Y-%m-%d")  # 末桶＝今日（本轮两笔当日落账）
        assert day_stats["items"][-1]["calls"] >= 2

        # sums＝窗口全量（pageSize=1 截断 items、不截断 sums——合同）
        paged = client.get("/api/gateway/spend-stats?group_by=caller&range=all&pageSize=1").json()
        assert len(paged["items"]) == 1
        assert paged["sums"]["calls"] == caller_stats["sums"]["calls"]

        # —— ③ 端点 4 keyword（trgm SQL 检索）＋caller 归因回显 ——
        logs = client.get(f"/api/gateway/spend-logs?keyword={first.call_id}").json()
        assert logs["total"] == 1
        assert logs["items"][0]["caller"] == caller_a

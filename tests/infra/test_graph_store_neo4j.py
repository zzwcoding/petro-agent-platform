"""infra.graph_store Neo4j 集成测试——compose neo4j 真连（建边/拦边/整图读）。

约定同 PG 组：无 Neo4j 底座即 skip（懒连探活失败——GraphStoreUnavailableError
即视作底座不可用，与 adapter「显式错不静默降级」语义一致）。
"""

from collections.abc import AsyncIterator

import pytest

from app.infra.graph_store import GraphStoreUnavailableError, Neo4jGraphStore

LIB = "lib-graph-test"
LIB2 = "lib-graph-test-other"


@pytest.fixture
async def neo4j_store() -> AsyncIterator[Neo4jGraphStore]:
    store = Neo4jGraphStore()
    try:
        await store._ensure_driver()
    except GraphStoreUnavailableError:
        pytest.skip("compose neo4j 不可达——Neo4j 集成测试跳过（约定同 PG 组）")
    driver = await store._ensure_driver()

    async def _clean() -> None:
        async with driver.session(database="neo4j") as session:
            await session.run(
                "MATCH (n) WHERE n.lib_id IN [$a, $b] DETACH DELETE n",
                a=LIB, b=LIB2,
            )
            await session.run(
                "MATCH (b:BlockedEdge) WHERE b.lib_id IN [$a, $b] DELETE b",
                a=LIB, b=LIB2,
            )

    await _clean()  # 前置清理（残留防串）
    yield store
    await _clean()
    await store.close()


async def test_upsert_and_read_net(neo4j_store: Neo4jGraphStore) -> None:
    s = neo4j_store
    await s.upsert_node(LIB, node_id="N-02", label="N-02", node_type="井",
                        short="N-02", sub="井")
    await s.upsert_node(LIB, node_id="渤南", label="渤南", node_type="区块",
                        short="渤南", sub="区块")
    await s.upsert_node(LIB, node_id="N-06", label="N-06", node_type="井",
                        short="N-06", sub="井")
    await s.upsert_node(LIB2, node_id="他库", label="他库", node_type="井",
                        short="他库", sub="井")  # namespace 隔离对照组
    edge = {
        "key": "N-02|隶属|渤南", "from_id": "N-02", "rel": "隶属", "to_id": "渤南",
        "note": None, "evidence": "N-02 井隶属渤南区块。",
        "chunk_id": "f1", "report_id": "rpt-1",
    }
    await s.upsert_edge(LIB, **edge)
    await s.upsert_edge(LIB, **edge)  # 边唯一键 MERGE——重复写不翻倍
    net = await s.read_net(LIB)
    ids = {n["id"] for n in net["nodes"]}
    assert ids == {"N-02", "渤南", "N-06"}  # 他库节点不串库
    assert len(net["edges"]) == 1, "边唯一键（from|rel|to）防重"
    e = net["edges"][0]
    assert e["rel"] == "隶属" and e["evidence"].startswith("N-02")
    assert e["chunk_id"] == "f1" and e["report_id"] == "rpt-1"


async def test_blocked_edges_roundtrip(neo4j_store: Neo4jGraphStore) -> None:
    s = neo4j_store
    await s.record_blocked(
        LIB, key="化验样 H-01|取样自|N-02", from_id="化验样 H-01",
        from_type="化验样", rel="取样自", to_id="N-02", to_type="井",
        reason_code="type_mismatch",
        reason="关系标签「取样自」不在该库抽取配置 relation_tags 清单内（类型闸拦下）",
        report_id="rpt-1", report_title="N-02 井完井报告", chunk_id="chk-0173",
        blocked_at="2026-10-01 10:12",
    )
    await s.record_blocked(
        LIB, key="N-06|受效|N-02", from_id="N-06", from_type="井", rel="受效",
        to_id="N-02", to_type="井", reason_code="uncertain",
        reason="抽取模型自报拿不准（弃权跳过——拿不准宁可跳过，不胡编）",
        report_id="rpt-1", report_title="N-02 井完井报告", chunk_id=None,
        blocked_at="2026-10-01 10:13",
    )
    rows = await s.list_blocked(LIB)
    assert {r["reason_code"] for r in rows} == {"type_mismatch", "uncertain"}
    assert rows[0]["report_title"] == "N-02 井完井报告"
    assert rows[1].get("chunk_id") is None  # chunk_id 可 null（合同注记——Cypher SET null 即删属性）
    assert await s.list_blocked(LIB2) == []  # namespace 隔离

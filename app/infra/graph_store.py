"""infra.graph_store —— 图存储统一接缝（98 §4 adapter；ADR-0003 裁决 2 拍 Neo4j）。

选型理由（票面要求说明）：
- 99 §2.7 图两表迁移注记：graph_node/graph_edge 不落 PG、迁 Neo4j（98
  `infra.graph_store` adapter）——B5 整图读/N 跳遍历与 A1 图谱问答链取数改
  Cypher；抽取设置（kb_extract_config）与活动流（kb_activity）仍留 PG。
- compose 中间件五件已含 neo4j:5（bolt 7687 / neo4j·petro12345）、pyproject
  已有 neo4j>=5.24 依赖——**落真 Neo4j adapter** 而非占位：占位无法兑现
  「整图一次给」Cypher 读面与「被拦边留痕可查」两条合同行为，冒烟验收
  （真报告入库→真抽边→图可查→拦边清单有记录）也无从谈起。
- 图模型（99 §2.7 关键列平移为图模型约束，namespace=库）：
  - 节点 `(:GraphNode {lib_id, id, label, type, short, sub})`——id＝实体名
    （同名不消歧 F40 原判，库内唯一）；type 值域＝该库 ExtractConfig 投影。
  - 边 `(:GraphNode)-[:REL {lib_id, key, rel, note, evidence, chunk_id,
    report_id}]->(:GraphNode)`——key=`from|rel|to`（B5 冻结边唯一键，MERGE
    承载唯一约束）；evidence＝原文依据句（依据闸凭据）；chunk_id/report_id
    ＝出处 chunk＋报告（「只含过闸边」——写口仅抽取管线过闸后调用）。
  - 被拦边 `(:BlockedEdge {lib_id, key, from, from_type, rel, to, to_type,
    reason_code, reason, report_id, report_title, chunk_id, blocked_at})`
    ——拦下的边不进图，只进对账镜像（B5 端点 4 只读消费面）。
- neo4j SDK 自带 asyncio 驱动——直接 async，无需 to_thread 卸载。
- 探活失败显式错不静默降级：首次使用懒建连＋verify_connectivity；失败抛
  GraphStoreUnavailableError（500 域错误——图存储不可用不是空图，禁假装）。

边界：B16（infra 不 import domains/api）、B1（不咬框架）、B3（图存储是
B3 出口之外的图专用接触面——98 §4 adapter 清单单列行）。
凭证经 infra.config InfraSettings 注入（.env / 环境变量，不进 git）。
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from app.infra.config import get_settings

# Neo4j 目标库（compose 缺省 database 名；session 级显式指定防 env 漂移）。
NEO4J_DATABASE = "neo4j"


class GraphStoreUnavailableError(Exception):
    """图存储不可用（懒连探活失败——显式错不静默降级，禁假装空图）。"""


class GraphStore(Protocol):
    """图存储 seam（测试注入假实现；生产装配 Neo4jGraphStore）。"""

    async def upsert_node(
        self, lib_id: str, *, node_id: str, label: str, node_type: str,
        short: str, sub: str,
    ) -> None: ...

    async def upsert_edge(
        self, lib_id: str, *, key: str, from_id: str, rel: str, to_id: str,
        note: str | None, evidence: str, chunk_id: str, report_id: str,
    ) -> None: ...

    async def record_blocked(
        self, lib_id: str, *, key: str, from_id: str, from_type: str,
        rel: str, to_id: str, to_type: str, reason_code: str, reason: str,
        report_id: str, report_title: str, chunk_id: str | None,
        blocked_at: str,
    ) -> None: ...

    async def read_net(self, lib_id: str) -> dict[str, Any]: ...

    async def list_blocked(self, lib_id: str) -> list[dict[str, Any]]: ...


class Neo4jGraphStore:
    """Neo4j adapter（compose 中间件；凭证经 InfraSettings）。

    首次使用懒建连＋verify_connectivity（探活失败显式抛
    GraphStoreUnavailableError——不静默降级为空图）。
    """

    def __init__(self) -> None:
        self._driver: Any = None
        self._ready = False
        self._lock = asyncio.Lock()
        settings = get_settings()
        self._uri = settings.neo4j_uri
        self._user = settings.neo4j_user
        self._password = settings.neo4j_password

    async def _ensure_driver(self) -> Any:
        if self._ready:
            return self._driver
        async with self._lock:
            if self._ready:
                return self._driver
            from neo4j import AsyncGraphDatabase  # 局部 import——SDK 接触面收敛单模块

            driver = AsyncGraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
            try:
                await driver.verify_connectivity()  # 探活——失败显式错不静默降级
            except Exception as exc:
                await driver.close()
                raise GraphStoreUnavailableError(
                    f"图存储（Neo4j {self._uri}）不可用：{exc}"
                ) from exc
            self._driver = driver
            self._ready = True
            return driver

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            self._ready = False

    # ---------- 写口（只许抽取管线过闸后调用——99 §3 derivatives 写权注记） ----------

    async def upsert_node(
        self, lib_id: str, *, node_id: str, label: str, node_type: str,
        short: str, sub: str,
    ) -> None:
        driver = await self._ensure_driver()

        async def _tx(tx: Any) -> None:
            await tx.run(
                """
                MERGE (n:GraphNode {lib_id: $lib, id: $id})
                SET n.label = $label, n.type = $type, n.short = $short, n.sub = $sub
                """,
                lib=lib_id, id=node_id, label=label, type=node_type,
                short=short, sub=sub,
            )

        async with driver.session(database=NEO4J_DATABASE) as session:
            await session.execute_write(_tx)

    async def upsert_edge(
        self, lib_id: str, *, key: str, from_id: str, rel: str, to_id: str,
        note: str | None, evidence: str, chunk_id: str, report_id: str,
    ) -> None:
        driver = await self._ensure_driver()

        async def _tx(tx: Any) -> None:
            await tx.run(
                """
                MERGE (a:GraphNode {lib_id: $lib, id: $from})
                MERGE (b:GraphNode {lib_id: $lib, id: $to})
                MERGE (a)-[r:REL {lib_id: $lib, key: $key}]->(b)
                SET r.rel = $rel, r.note = $note, r.evidence = $evidence,
                    r.chunk_id = $chunk, r.report_id = $report
                """,
                lib=lib_id, key=key, **{"from": from_id}, to=to_id, rel=rel,
                note=note, evidence=evidence, chunk=chunk_id, report=report_id,
            )

        async with driver.session(database=NEO4J_DATABASE) as session:
            await session.execute_write(_tx)

    async def record_blocked(
        self, lib_id: str, *, key: str, from_id: str, from_type: str,
        rel: str, to_id: str, to_type: str, reason_code: str, reason: str,
        report_id: str, report_title: str, chunk_id: str | None,
        blocked_at: str,
    ) -> None:
        driver = await self._ensure_driver()

        async def _tx(tx: Any) -> None:
            await tx.run(
                """
                MERGE (b:BlockedEdge {lib_id: $lib, key: $key, report_id: $report})
                SET b.from = $from, b.from_type = $from_type, b.rel = $rel,
                    b.to = $to, b.to_type = $to_type, b.reason_code = $reason_code,
                    b.reason = $reason, b.chunk_id = $chunk, b.blocked_at = $at,
                    b.report_title = $report_title
                """,
                lib=lib_id, key=key, **{"from": from_id}, from_type=from_type,
                rel=rel, to=to_id, to_type=to_type, reason_code=reason_code,
                reason=reason, report=report_id, chunk=chunk_id, at=blocked_at,
                report_title=report_title,
            )

        async with driver.session(database=NEO4J_DATABASE) as session:
            await session.execute_write(_tx)

    # ---------- 读口（B5 端点 1/4；A1 图谱问答链 N 跳遍历随 P1-08b 扩展） ----------

    async def read_net(self, lib_id: str) -> dict[str, Any]:
        """整图一次给：nodes/edges 原始行（legend/stats 由域层聚合——计数与
        nodes 必然一致，聚合单点在域不在 adapter）。"""
        driver = await self._ensure_driver()

        async def _tx(tx: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            node_res = await tx.run(
                "MATCH (n:GraphNode {lib_id: $lib}) RETURN n ORDER BY n.id",
                lib=lib_id,
            )
            nodes = [dict(record["n"]) async for record in node_res]
            edge_res = await tx.run(
                "MATCH (a:GraphNode {lib_id: $lib})-[r:REL {lib_id: $lib}]->"
                "(b:GraphNode {lib_id: $lib}) "
                "RETURN r, a, b ORDER BY r.key",
                lib=lib_id,
            )
            edges = [
                {
                    "key": record["r"]["key"],
                    "from": record["a"]["id"],
                    "rel": record["r"]["rel"],
                    "to": record["b"]["id"],
                    "note": record["r"].get("note"),
                    "evidence": record["r"].get("evidence", ""),
                    "chunk_id": record["r"].get("chunk_id", ""),
                    "report_id": record["r"].get("report_id", ""),
                }
                async for record in edge_res
            ]
            return nodes, edges

        async with driver.session(database=NEO4J_DATABASE) as session:
            nodes, edges = await session.execute_read(_tx)
        return {"nodes": nodes, "edges": edges}

    async def list_blocked(self, lib_id: str) -> list[dict[str, Any]]:
        driver = await self._ensure_driver()

        async def _tx(tx: Any) -> list[dict[str, Any]]:
            result = await tx.run(
                "MATCH (b:BlockedEdge {lib_id: $lib}) "
                "RETURN b ORDER BY b.blocked_at, b.key",
                lib=lib_id,
            )
            return [dict(record["b"]) async for record in result]

        async with driver.session(database=NEO4J_DATABASE) as session:
            rows: list[dict[str, Any]] = await session.execute_read(_tx)
        return rows

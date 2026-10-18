"""retrieval.source —— 片段库/图谱源 seam 与内存适配器（V2-04，specs/modules.md
retrieval 卡「Seam: RetrievalEngine / embedder；Adapter: fixture 片段库」）。

Seam 裁决：检索引擎对 kb_* 台账/图存储的接触面收敛为两个只读 callable 形
（V1 B9「运行期只见 callable」同款）——生产装配=PG kb_* 只读读面/Neo4j 邻域
适配器（后续票接线），测试注入 InMemoryFragmentLibrary（fixture 片段库——
specs/modules.md retrieval 卡测试计划点名的 adapter）。

行形状（FragmentRecord/GraphEdgeRecord）与纯语义在 domain.py——本模块只立
seam 与内存适配器，全程只读（INV-2：返回容器一律副本、注入后不改）。

V2-97（D7）：生产装配无 `GraphSource` 实现、`RetrievalEngine` 构造无 `graph=`——
图谱腿整条**保留未接线** DEBT(V2-97)：本文件（GraphSource 协议／空集回退）不删，
接线另立决策票。
"""

from __future__ import annotations

import abc

from appv2.retrieval.domain import FragmentRecord, GraphEdgeRecord


class FragmentLibrary(abc.ABC):
    """片段库读面 seam（kb_* 台账只读投影——检索双路召回的语料源）。"""

    @abc.abstractmethod
    async def fragments(self) -> list[FragmentRecord]:
        """子块片段全集（向量列随行；调用方零写——只读快照语义）。"""


class GraphSource(abc.ABC):
    """图谱源 seam（图存储只读投影——图谱面邻域遍历的边源）。"""

    @abc.abstractmethod
    async def graph_edges(self) -> list[GraphEdgeRecord]:
        """关系边全集（带出处 chunk_id/report_id；邻域过滤归 engine）。"""


class InMemoryFragmentLibrary(FragmentLibrary, GraphSource):
    """快照驱动的内存片段库（fixture 注入；零 I/O、零写路径）。

    同时实现两 seam——单测一个对象供双面（片段语料＋图谱边）；生产装配拆
    两个适配器（PG 读面/Neo4j 读面）不受影响：engine 只认抽象基类。
    """

    def __init__(
        self,
        fragments: list[FragmentRecord],
        *,
        edges: list[GraphEdgeRecord] | None = None,
    ) -> None:
        self._fragments = list(fragments)
        self._edges = list(edges or [])

    async def fragments(self) -> list[FragmentRecord]:
        return list(self._fragments)

    async def graph_edges(self) -> list[GraphEdgeRecord]:
        return list(self._edges)

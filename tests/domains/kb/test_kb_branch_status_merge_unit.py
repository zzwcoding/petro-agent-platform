"""branch_status 键级合并（DE-15——挂账清单 §E2）服务单测（sqlite 底座）。

缺陷面红钉三枚＋语义钉两枚：

- 交错写丢键：wiki 支路写 done 与 graph 支路逐 chunk 进度写并发交错时，
  「会话内读旧载荷→整载荷回写」两写者互盖——后提交者基于旧载荷整块覆盖，
  先到键被抹。用语句序编排夹具（_InterleaveSessionProxy）把交错确定化：
  读改写式实现两读先行、后写整载荷覆盖＝必丢一键（红）；单语句服务端合并
  实现无独立读点、后写者的合并语句阻塞在前者的行锁上，超时兜底放行后仍
  读到前者已提交值＝两键均存（绿）。
- 整行 save 抹键：TaskStore.save/finish_with_activity 为分离行 session.merge
  整行合并——管线装载时的旧 branch_status 随每步 save 回写 DB，盖掉并发支路
  写（DE-06 曾以两段写＋本地镜像绕行；本票改列归属规则后镜像退役——审查
  R1-15①随本票消化）。此缺陷与并发时序无关、单线程即可复现（确定性红）。
- 语义钉：键级合并＝顶层支路键**整值替换**（不深合并、旧子键不残留）；
  DE-06 chunk_check 与 G-02 wiki/graph 三键共存，载荷形状（state/detail/
  extra）零变化。

消费方零破坏由全量既有测试守（TestChunkCheckAlert 走全管线——chunk_check
在 embed/index/enrich 多次整行 save 后仍须存活，即镜像退役的回归钉）。
"""

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any

from app.domains.kb import KbService
from app.domains.kb.store import IngestTaskRow, LibraryRow, ReportRow, TaskStore
from app.infra.clock import now
from tests.domains.kb.conftest import FakeObjectStorage, StubCompleter

TASK_ID = "task-de15"


async def _seed_task(manager: Any) -> str:
    """最小任务行（lib→report→task 外键链；branches 初始空载荷）。"""
    async with manager.session() as session:
        session.add(LibraryRow(id="lib-de15", name="DE15 合并库", biz_template="completion"))
        await session.flush()  # 父行先落（无 relationship 不保证 UOW 插序——store 惯例）
        session.add(
            ReportRow(
                id="rpt-de15", lib_id="lib-de15", doc="DE15 报告", object_key="de15/doc.txt"
            )
        )
        await session.flush()
        session.add(
            IngestTaskRow(
                id=TASK_ID,
                report_id="rpt-de15",
                lib_id="lib-de15",
                state="running",
                source="上传入库",
                current_step=0,
                nodes=[],
                config_snapshot={},
                started_at=now(),
            )
        )
    return TASK_ID


def _service(manager: Any) -> KbService:
    return KbService(manager, StubCompleter(), FakeObjectStorage())


class _HookedSession:
    """语句挂点会话代理：首条语句（读点/合并写点）前后回调编排器。"""

    def __init__(
        self, real: Any, harness: "_InterleaveSessionProxy", writer: int, rnd: int
    ) -> None:
        self._real = real
        self._harness = harness
        self._writer = writer
        self._rnd = rnd
        self._first = True

    async def get(self, *args: Any, **kwargs: Any) -> Any:
        return await self._call("read", self._real.get, *args, **kwargs)

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return await self._call("write", self._real.execute, *args, **kwargs)

    async def _call(self, kind: str, method: Any, *args: Any, **kwargs: Any) -> Any:
        first, self._first = self._first, False
        if first:
            await self._harness.before_statement(self._writer, self._rnd)
        try:
            return await method(*args, **kwargs)
        finally:
            if first:
                await self._harness.after_statement(self._writer, self._rnd, kind)

    async def __aenter__(self) -> "_HookedSession":
        await self._real.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> Any:
        return await self._real.__aexit__(*exc)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class _InterleaveSessionProxy:
    """两写者逐轮语句/提交序编排（交错红钉确定性化）。

    每个协程＝一个写者（wiki/graph 各一）；每轮＝一次 set_branch_status（一次
    会话）。逐轮栅栏：B 的第 k 轮首语句等 A 第 k 轮首语句完成（两读同基线）；
    A 的首语句若是**独立读语句**（get——读改写形态），其提交再压到 B 读点之后
    ——每轮收尾状态确定：两读先行、后提交者携旧基线整载荷覆盖，先到键被抹
    （读改写实现的必现交错，末轮终态必缺一键＝红）。sqlite 读语句不持写锁
    （pysqlite 仅 DML 前隐式 BEGIN），挂起点零锁无死锁；放行靠事件不靠超时，
    超时（1s）只是安全阀。

    单语句服务端合并实现（键级 UPDATE，首语句经 execute、无独立读点）不触发
    挂起：语句自带原子读改写，交错本就无损——A 落库后 B 的合并语句被 A 的行
    键锁自然串行化、仍读到 A 已提交值＝两键均存（绿，零超时开销）。
    """

    def __init__(self, manager: Any) -> None:
        self._manager = manager
        self._writer_of_task: dict[int, int] = {}
        self._round_of_writer: dict[int, int] = {}
        self.a_read_done: dict[int, asyncio.Event] = defaultdict(asyncio.Event)
        self.b_read_done: dict[int, asyncio.Event] = defaultdict(asyncio.Event)
        self.writer1_first_is_read: dict[int, bool] = {}

    @asynccontextmanager
    async def session(self, *args: Any, **kwargs: Any) -> Any:
        task = id(asyncio.current_task())
        writer = self._writer_of_task.setdefault(task, len(self._writer_of_task) + 1)
        self._round_of_writer[writer] = self._round_of_writer.get(writer, 0) + 1
        rnd = self._round_of_writer[writer]
        cm = self._manager.session(*args, **kwargs)
        real = await cm.__aenter__()
        exited = False
        try:
            yield _HookedSession(real, self, writer, rnd)
            # 读改写形态：写者 A 携旧基线的写压到 B 本轮读点之后（两读先行）
            if writer == 1 and self.writer1_first_is_read.get(rnd, False):
                await asyncio.wait_for(self.b_read_done[rnd].wait(), 1.0)  # 安全阀
            await cm.__aexit__(None, None, None)
            exited = True
        except BaseException as exc:
            if not exited:
                await cm.__aexit__(type(exc), exc, exc.__traceback__)
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._manager, name)

    async def before_statement(self, writer: int, rnd: int) -> None:
        if writer == 2:  # B 的读点/写点压到 A 本轮语句完成之后——两读同基线
            await asyncio.wait_for(self.a_read_done[rnd].wait(), 5.0)

    async def after_statement(self, writer: int, rnd: int, kind: str) -> None:
        if writer == 1:
            self.writer1_first_is_read[rnd] = kind == "read"
            self.a_read_done[rnd].set()
        else:
            self.b_read_done[rnd].set()


class TestInterleavedBranchWrites:
    """交付物 2：交错红转绿——wiki done ∥ graph 进度并发写，终态两键均保留。"""

    async def test_wiki_done_and_graph_progress_survive_interleaving(
        self, kb_db: Any
    ) -> None:
        interleave = _InterleaveSessionProxy(kb_db)
        service = _service(interleave)  # 写面会话经编排代理——交错确定化
        task_id = await _seed_task(kb_db)

        async def wiki_writer() -> None:
            for i in range(10):
                await service.set_branch_status(task_id, "wiki", "running", detail=f"生成中 {i}")
            await service.set_branch_status(task_id, "wiki", "done")

        async def graph_writer() -> None:
            for i in range(1, 11):
                await service.set_branch_status(
                    task_id,
                    "graph",
                    "running",
                    extra={"chunks_done": i, "chunks_total": 10, "edges": i * 2, "blocked": 1},
                )
            await service.set_branch_status(
                task_id,
                "graph",
                "done",
                extra={"chunks_done": 10, "chunks_total": 10, "edges": 20, "blocked": 1},
            )

        await asyncio.gather(wiki_writer(), graph_writer())

        branches = (await service.ingest_task(task_id)).branches
        assert branches["wiki"] == {"state": "done"}, f"wiki 键被并发写抹掉：{branches}"
        graph = branches["graph"]
        assert graph["state"] == "done", f"graph 键被并发写抹掉：{branches}"
        assert graph["chunks_done"] == 10
        assert graph["chunks_total"] == 10
        assert graph["edges"] == 20
        assert graph["blocked"] == 1


class TestFullRowSaveKeepsBranchKeys:
    """整行 save 抹键红钉（确定性、零并发依赖）：branch_status 列归属键级写口。"""

    async def test_save_keeps_concurrent_branch_key(self, kb_db: Any) -> None:
        service = _service(kb_db)
        store = TaskStore(kb_db)
        task_id = await _seed_task(kb_db)

        row = await store.get(task_id)  # 管线装载——此刻 branches 尚空
        assert row is not None
        await service.set_branch_status(  # 支路并发写（wiki/graph/chunk_check 同通道）
            task_id,
            "graph",
            "running",
            extra={"chunks_done": 1, "chunks_total": 3, "edges": 0, "blocked": 0},
        )
        row.state = "running"
        row.current_step = 2
        await store.save(row)  # 分离行整行 save（管线每步一次）

        branches = (await service.ingest_task(task_id)).branches
        assert branches.get("graph", {}).get("chunks_done") == 1, (
            f"整行 save 抹掉并发支路键：{branches}"
        )

    async def test_finish_with_activity_keeps_concurrent_branch_key(self, kb_db: Any) -> None:
        service = _service(kb_db)
        store = TaskStore(kb_db)
        task_id = await _seed_task(kb_db)

        row = await store.get(task_id)
        assert row is not None
        await service.set_branch_status(task_id, "wiki", "done")
        row.state = "done"
        row.finished_at = now()
        await store.finish_with_activity(row, activity=("系统 · 知识管线", "入库完成", "目标"))

        branches = (await service.ingest_task(task_id)).branches
        assert branches.get("wiki") == {"state": "done"}, (
            f"finish_with_activity 抹掉并发支路键：{branches}"
        )


class TestKeyLevelMergeSemantics:
    """键级合并语义钉：顶层支路键整值替换＋三键共存。"""

    async def test_entry_replaced_wholesale_not_deep_merged(self, kb_db: Any) -> None:
        """新写不带 detail → 旧 detail 不残留（整值替换，非字段级深合并）。"""
        service = _service(kb_db)
        task_id = await _seed_task(kb_db)

        await service.set_branch_status(task_id, "wiki", "running", detail="生成中")
        await service.set_branch_status(task_id, "wiki", "done")

        branches = (await service.ingest_task(task_id)).branches
        assert branches["wiki"] == {"state": "done"}

    async def test_chunk_check_coexists_with_wiki_graph(self, kb_db: Any) -> None:
        """DE-06 chunk_check 与 G-02 wiki/graph 三键共存，各键值互不干扰。"""
        service = _service(kb_db)
        task_id = await _seed_task(kb_db)

        await service.set_branch_status(
            task_id,
            "chunk_check",
            "warn",
            detail="切块自检 2 条违规",
            extra={"violations": 2, "evidence": "/tmp/chunk_validate_task-de15.md"},
        )
        await service.set_branch_status(task_id, "wiki", "done")
        await service.set_branch_status(
            task_id, "graph", "done", extra={"chunks_total": 3, "chunks_done": 3}
        )

        branches = (await service.ingest_task(task_id)).branches
        assert branches["chunk_check"] == {
            "state": "warn",
            "detail": "切块自检 2 条违规",
            "violations": 2,
            "evidence": "/tmp/chunk_validate_task-de15.md",
        }
        assert branches["wiki"] == {"state": "done"}
        assert branches["graph"] == {"state": "done", "chunks_total": 3, "chunks_done": 3}

    async def test_missing_task_is_silent_noop(self, kb_db: Any) -> None:
        """任务行不存在＝静默跳过（原行为保持——回写失败不阻塞支路）。"""
        service = _service(kb_db)
        await service.set_branch_status("task-none", "wiki", "done")

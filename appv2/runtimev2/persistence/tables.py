"""簿记表的框架无关行级存储端口与内存件（Seam：存储入口——换载体不改调用面）。

真源＝`specs/persistence.md` 卡级澄清②（**业务数据面只读**，簿记表 `agent_v2_*` 是本块唯一写面）
＋「不做什么」INV-2 行（业务数据零写入）。本模块是**唯一**的行级写入口：所有写都经 `Tables.write`
一次性批量提交（**原子**——同一批次要么全落要么全不落，行为 14 无半写），且按表校验操作闭世界
——**只追加表**（黑匣子／引用载体）只许 `append`，**既成行无改写／删除路径**（行为 2 的行为证）。

框架与依赖红线：本模块零框架类型（`langgraph`／`langchain` 零出现，R5b）、零引擎直引（R6）、
零模型出口（R7）；时间列由 `store` 经 `infra.clock` 盖（B14），本层不取时间。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from appv2.runtimev2.persistence.errors import TableWriteError

# ── 簿记表清单（前缀隔离＝INV-2 的机器面：簿记表前缀 agent_v2_* 是唯一写面）────────
BOOKKEEPING_TABLE_PREFIX = "agent_v2_"

TABLE_RUN = "agent_v2_run"
TABLE_STEP = "agent_v2_step"
TABLE_BLACKBOX = "agent_v2_blackbox"
TABLE_BLOB = "agent_v2_blob"  # 大结果原文的引用载体（载体实现阶段 5 定；簿记表件为其一）
TABLE_CHECKPOINT = "agent_v2_checkpoint"
TABLE_CHECKPOINT_BLOB = "agent_v2_checkpoint_blob"
TABLE_CHECKPOINT_WRITE = "agent_v2_checkpoint_write"

TABLES: tuple[str, ...] = (
    TABLE_RUN,
    TABLE_STEP,
    TABLE_BLACKBOX,
    TABLE_BLOB,
    TABLE_CHECKPOINT,
    TABLE_CHECKPOINT_BLOB,
    TABLE_CHECKPOINT_WRITE,
)
CHECKPOINT_TABLES: frozenset[str] = frozenset(
    {TABLE_CHECKPOINT, TABLE_CHECKPOINT_BLOB, TABLE_CHECKPOINT_WRITE}
)

RowOpName = Literal["put", "append", "delete"]

# ── 每表允许的行级操作（闭世界）：只追加表只许 append——无覆盖、无删除路径 ──────────
TABLE_OPS: Mapping[str, frozenset[str]] = {
    TABLE_RUN: frozenset({"put"}),
    TABLE_STEP: frozenset({"put"}),
    TABLE_BLACKBOX: frozenset({"append"}),
    TABLE_BLOB: frozenset({"append"}),
    TABLE_CHECKPOINT: frozenset({"put", "delete"}),
    TABLE_CHECKPOINT_BLOB: frozenset({"put", "delete"}),
    TABLE_CHECKPOINT_WRITE: frozenset({"put", "delete"}),
}
APPEND_ONLY_TABLES: frozenset[str] = frozenset(
    {table for table, ops in TABLE_OPS.items() if ops == frozenset({"append"})}
)


@dataclass(frozen=True, slots=True)
class RowOp:
    """一次行级操作（表／主键／行体／操作名）——`delete` 无行体（恒空映射）。"""

    table: str
    key: tuple[str, ...]
    row: Mapping[str, Any]
    op: RowOpName


class Tables(Protocol):
    """簿记表行级端口（Seam：换载体不改调用面；真件由装配点注入，缺省＝内存件）。"""

    def ensure(self) -> None:
        """幂等建表（与迁移脚本同形；缺省件＝建表清单在场）。"""
        ...

    def write(self, ops: Sequence[RowOp]) -> None:
        """原子批量落行：全部落或全不落；只会计表拒收（INV-2）与非法操作（行为 14）。"""
        ...

    def get(self, table: str, key: tuple[str, ...]) -> dict[str, Any] | None:
        """按主键取行（副本——改返回值不改库内行）。"""
        ...

    def scan(self, table: str, column: str, value: str) -> list[dict[str, Any]]:
        """按列等值扫描（插入序；副本）。"""
        ...

    def scan_recent(self, limit: int) -> list[dict[str, Any]]:
        """`agent_v2_run` 按 `created_at` 降序取前 `limit` 行（副本）——列表读口的 limit 下推口。

        **逐字稿**（V2-141 任务 1）：`def scan_recent(self, limit: int) -> list[RunRow]: ...`，
        语义＝「created_at DESC，取前 limit」；本端口行形为 `dict[str, Any]`（与 `get`／`scan`
        同款——仓内无 `RunRow` 类型，逐字稿的 `RunRow` 按端口既有行形落）。真件 SQL 落实现块内
        （`SELECT ... FROM agent_v2_run ORDER BY created_at DESC LIMIT $1`，api 侧不自造 SQL）；
        PG 真件口随 V2-135 同批补（`PgTables.scan_recent`——`pg_tables.py` 未落）。
        """
        ...


class MemoryTables:
    """内存簿记表件（测试替身／阶段 5 缺省件）——只落 `agent_v2_*` 表。

    非簿记表名一律拒收（`TableWriteError`）＝业务数据零写入（INV-2）在端口层的把守：
    任何对业务表的写入尝试判失败。`writes` ＝行写下账（表／主键／操作），读口不留下账
    ——「`load` 两次无副作用」的落盘计数面（行为 3）。
    """

    def __init__(self) -> None:
        self._rows: dict[str, dict[tuple[str, ...], dict[str, Any]]] = {}
        self.writes: list[tuple[str, tuple[str, ...], RowOpName]] = []

    def ensure(self) -> None:
        for table in TABLES:
            self._rows.setdefault(table, {})

    def write(self, ops: Sequence[RowOp]) -> None:
        prepared: list[tuple[str, tuple[str, ...], dict[str, Any]]] = []
        removed: list[tuple[str, tuple[str, ...]]] = []
        for op in ops:
            stored = self._check(op)
            if op.op == "delete":
                removed.append((op.table, op.key))
            elif op.op == "append":
                if stored is not None:
                    raise TableWriteError(
                        f"表 {op.table} 只追加：主键 {op.key} 已在场，既成行不覆盖、不删除"
                    )
                prepared.append((op.table, op.key, deepcopy(dict(op.row))))
            else:
                prepared.append((op.table, op.key, deepcopy(dict(op.row))))
        # 全行备齐后才落（原子批量：任一行非法 → 一行不落，行为 14）
        for table, key, row in prepared:
            self._rows[table][key] = row
        for table, key in removed:
            self._rows[table].pop(key, None)
        self.writes.extend((op.table, op.key, op.op) for op in ops)

    def get(self, table: str, key: tuple[str, ...]) -> dict[str, Any] | None:
        row = self._rows_for(table).get(key)
        return None if row is None else deepcopy(row)

    def scan(self, table: str, column: str, value: str) -> list[dict[str, Any]]:
        return [
            deepcopy(row)
            for row in self._rows_for(table).values()
            if row.get(column) == value
        ]

    def scan_recent(self, limit: int) -> list[dict[str, Any]]:
        """按 `created_at` 降序取前 `limit` 行（副本）——内存件侧 limit 下推。"""
        rows = sorted(
            self._rows_for(TABLE_RUN).values(),
            key=lambda row: row["created_at"],
            reverse=True,
        )
        return [deepcopy(row) for row in rows[:limit]]

    def _check(self, op: RowOp) -> dict[str, Any] | None:
        allowed = TABLE_OPS.get(op.table)
        if allowed is None:
            raise TableWriteError(
                f"非簿记表拒写：{op.table!r}"
                f"（唯一写面＝前缀 {BOOKKEEPING_TABLE_PREFIX}* 簿记表——INV-2）"
            )
        if op.op not in allowed:
            ops = "／".join(sorted(allowed))
            raise TableWriteError(f"表 {op.table} 不允许操作 {op.op!r}（闭世界 {ops}）")
        return self._rows_for(op.table).get(op.key)

    def _rows_for(self, table: str) -> dict[tuple[str, ...], dict[str, Any]]:
        if table not in TABLE_OPS:
            raise TableWriteError(
                f"非簿记表不可读：{table!r}"
                f"（唯一面＝前缀 {BOOKKEEPING_TABLE_PREFIX}* 簿记表——INV-2）"
            )
        return self._rows.setdefault(table, {})


# ── 缺省件与装配点（换载体不改调用面：真件由装配点 configure_tables 注入）──────────
_DEFAULT_TABLES: Tables = MemoryTables()


def configure_tables(tables: Tables) -> Tables:
    """装配点注入表件（返回旧件——测试还原便利）。**唯一替换缝**，调用面不变。"""
    global _DEFAULT_TABLES
    previous = _DEFAULT_TABLES
    _DEFAULT_TABLES = tables
    return previous


def current_tables() -> Tables:
    """当前装配的表件（未注入＝内存件）。"""
    return _DEFAULT_TABLES

"""domains.semantics.service —— 薄服务面：本体仓同步器（sync_from_ontology_repo）。

98 §3.7 卡签名：sync_from_ontology_repo(ref, actor, schema_version="1.1.0") -> SyncReport
——消费 MR 合入事件；幂等重放安全；台账行禁手工改（B4 投影纪律）；
schema_version＝钉版契约（低于钉版拒同步，跨 1.x 兼容读）。

投影实现（tickets/phase1/README.md P1-01）：
- 真源＝ontology/petro/ 七模型 YAML（平台仓普通目录，只读文件读入——不跑
  ontology/ 写操作，守 ontology/AGENTS.md）；ref 为 MR 合入事件标识（随审计与
  SyncReport 留痕；当前实现消费工作区 petro/ 目录）。
- 行内容：本体承载字段从 YAML 读出（指标 mark/grain/unit/modifiers/ambiguous
  口径字段组、m2 头注 Action 承载校验、M1/M6/M3/GLS 元素锚校验），台账展示串
  照抄 C1 合同现值（种子常量见 domain.py，锚校验不过＝OntologyDriftError 不静默）。
- 幂等：行内容逐列比对——未变行零写（计数 rows_unchanged）；新行 INSERT＋
  revision v1；已变行 UPDATE＋revision v+1（首跑零手养、重放安全）。
- B12：同步动作经 security.audit 落横切审计（动作槽 semantics.ontology_synced，
  who＝调用 actor；内容槽带 ref/schema/行计数）。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Protocol

import yaml
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.domains.security.domain import Actor, AuditRow
from app.domains.semantics import domain as sem_domain
from app.domains.semantics.domain import (
    SEMANTIC_CURRENT_SEED,
    OntologyDriftError,
    SeedRow,
    SyncReport,
    assert_schema_version,
    enrich_metric_seeds,
    metric_slot_name,
    validate_against_ontology,
)
from app.domains.semantics.store import (
    SemAction,
    SemJoinWhitelist,
    SemLedgerRevision,
    SemMetric,
    SemObject,
    SemRelation,
    SemTerm,
    SemVersion,
    SemWorkflow,
    latest_row_version,
)
from app.infra.clock import now
from app.infra.db import ConnectionManager

LOGGER = logging.getLogger("domains.semantics")

# 本体真源目录（平台仓普通目录——只读；真源裁决 ADR-0004）。
ONTOLOGY_PETRO_DIR = Path(__file__).resolve().parents[3] / "ontology" / "petro"

_MODEL_FILES: dict[str, str] = {
    "glossary": "glossary-model.yaml",
    "m1": "m1-object-model.yaml",
    "m2": "m2-behavior-model.yaml",
    "m3": "m3-rule-model.yaml",
    "m6": "m6-flow-model.yaml",
}

_BASELINE_COLUMNS = frozenset({"created_at", "updated_at"})


@dataclass(frozen=True, slots=True)
class LedgerPage:
    """台账读面分页信封（C1 端点 2/3/5/6 列形＋00 §4.1 回显；total 筛选后/grand_total 全量）。"""

    items: list[Any] = field(default_factory=list)
    total: int = 0
    grand_total: int = 0
    page: int = 1
    page_size: int = 20


class AuditSink(Protocol):
    """B12 审计写口缝（装配根注入 SecurityService——semantics 不反向构造）。"""

    async def audit(self, row: AuditRow, *, session: AsyncSession | None = None) -> None: ...


@dataclass(frozen=True, slots=True)
class OntologyModels:
    """petro/ 模型解析结果（同步与导出共用一份读取面）。"""

    models: dict[str, dict[str, Any]]  # 模型键 → YAML 解析结果
    raw_text: dict[str, str]           # 模型键 → 文件原文（m2 头注等字面承载校验域）
    manifest_version: str              # manifest.schemaVersion（钉版契约轴）


def load_ontology_models(petro_dir: Path = ONTOLOGY_PETRO_DIR) -> OntologyModels:
    """读入 petro/ 五模型 YAML＋manifest（只读——不跑 ontology/ 写操作）。"""
    models: dict[str, dict[str, Any]] = {}
    raw_text: dict[str, str] = {}
    for key, filename in _MODEL_FILES.items():
        path = petro_dir / filename
        if not path.is_file():
            raise OntologyDriftError(f"本体真源缺文件：{path}")
        raw = path.read_text(encoding="utf-8")
        raw_text[key] = raw
        models[key] = yaml.safe_load(raw) or {}
    manifest_path = petro_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return OntologyModels(
        models=models, raw_text=raw_text, manifest_version=str(manifest["schemaVersion"])
    )


class SemanticsService:
    """semantics 域服务（薄）——本体仓同步口＋C1 台账读面（P1-01b 三件套）。"""

    def __init__(self, db: ConnectionManager, audit: AuditSink) -> None:
        self._db = db
        self._audit = audit  # B12 唯一写口（security.audit）注入

    async def sync_from_ontology_repo(
        self, ref: str, actor: Actor, schema_version: str = sem_domain.SCHEMA_VERSION_PIN
    ) -> SyncReport:
        """本体仓同步投影（98 §3.7 同步口）——幂等可重跑；动作落 B12 审计。"""
        if not ref or not ref.strip():
            raise ValueError("ref 必填——MR 合入事件标识（留痕于审计与 SyncReport）")
        ontology = load_ontology_models()
        assert_schema_version(ontology.manifest_version, schema_version)
        warnings = validate_against_ontology(ontology.models, ontology.raw_text)
        enriched_seeds, enrich_warnings = self._enriched_seeds(ontology.models)
        warnings.extend(w for w in enrich_warnings if w not in warnings)
        seeds = [*enriched_seeds, *self._plain_seeds()]

        counts: dict[str, int] = {}
        revisions = 0
        unchanged = 0
        async with self._db.transaction() as session:
            for seed in seeds:
                inserted, changed = await self._upsert(session, seed, actor)
                counts[seed.domain] = counts.get(seed.domain, 0) + 1
                revisions += inserted + changed
                if inserted == 0 and changed == 0:
                    unchanged += 1
            await self._upsert_sem_version(session)
        for warning in warnings:
            LOGGER.warning("semantics 同步锚告警：%s", warning)
        report = SyncReport(
            ref=ref,
            schema_version=schema_version,
            counts=counts,
            revisions_appended=revisions,
            rows_unchanged=unchanged,
            warnings=list(warnings),
        )
        await self._audit.audit(
            AuditRow(
                who=actor.who,
                action="semantics.ontology_synced",
                content=(
                    f"本体仓同步 ref={ref} schema={schema_version}——七账投影 "
                    f"{sum(report.counts.values())} 行（新行/变更行 {revisions}、"
                    f"未变 {unchanged}）、全量版本种子 {SEMANTIC_CURRENT_SEED}"
                ),
                meta={
                    "ref": ref,
                    "schema_version": schema_version,
                    "counts": report.counts,
                    "warnings": report.warnings,
                },
            )
        )
        return report

    # ---------- 台账读面（C1 三件套：术语/指标/对象与关系——B5 下游合法入口，票 93） ----------

    async def list_terms(
        self, *, keyword: str | None = None, status: list[str] | None = None,
        owner: str | None = None, page: int = 1, page_size: int = 20,
    ) -> LedgerPage:
        """术语账读面（C1 端点 2＋P1-01b 补分页/keyword/status——00 §4.5 命名）。

        keyword 命中面＝术语名＋类型展示串＋定义——类型串「别名 → X」「缩写 → X」
        「黑话 → X」族即 GLS 别名的台账载体，故检索别名名亦命中别名行；status 对
        status_key 精确等值（C1 筛选语义，多值 IN）；台账序＝id 升序（合同常量）。
        """
        return await self._paged(
            SemTerm, _term_conditions(keyword, status, owner), page, page_size
        )

    async def list_metrics(
        self, *, keyword: str | None = None, status: list[str] | None = None,
        owner: str | None = None, page: int = 1, page_size: int = 20,
    ) -> LedgerPage:
        """指标账读面（C1 端点 3＋P1-01b 补面；grain_display 读侧拼装不落列——裁决 e）。

        status 为 jsonb 数组列（#10 双徽标），包含谓词跨方言（PG jsonb/sqlite
        JSON）无统一写法；台账量级 15 行（C1「量级 3–15 条」）——SQL 只筛
        keyword/owner，status 数组命中与分页读侧完成（total＝筛选后计数）。
        """
        conditions: list[ColumnElement[bool]] = []
        if keyword:
            pattern = f"%{keyword}%"
            conditions.append(
                or_(
                    SemMetric.name.ilike(pattern),
                    SemMetric.slot_name.ilike(pattern),
                    SemMetric.def_.ilike(pattern),
                )
            )
        if owner:
            conditions.append(SemMetric.owner == owner)
        async with self._db.readonly() as session:
            grand_total = int(
                await session.scalar(select(func.count()).select_from(SemMetric)) or 0
            )
            stmt = select(SemMetric).order_by(SemMetric.id)
            if conditions:
                stmt = stmt.where(*conditions)
            rows: list[SemMetric] = list((await session.execute(stmt)).scalars())
        if status:
            rows = [row for row in rows if any(value in row.status for value in status)]
        start = (page - 1) * page_size
        return LedgerPage(
            items=rows[start : start + page_size], total=len(rows),
            grand_total=grand_total, page=page, page_size=page_size,
        )
    async def list_objects(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 20,
    ) -> LedgerPage:
        """对象账读面（C1 端点 5——草案态整体呈现；keyword 命中对象名/属性列）。"""
        return await self._paged(
            SemObject,
            _keyword_conditions(keyword, SemObject.obj, SemObject.attr),
            page, page_size,
        )

    async def list_relations(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 20,
    ) -> LedgerPage:
        """关系账读面（C1 端点 6——对象读面的关系账引用行；keyword 命中关系串/读法）。"""
        return await self._paged(
            SemRelation,
            _keyword_conditions(keyword, SemRelation.rel, SemRelation.read),
            page, page_size,
        )

    async def _paged(
        self, model: type[Any], conditions: list[ColumnElement[bool]],
        page: int, page_size: int,
    ) -> LedgerPage:
        """SQL 筛选＋计数＋分页信封（00 §4.1 回显；§4.2 total 筛选后/grand_total 全量）。"""
        async with self._db.readonly() as session:
            count_stmt = select(func.count()).select_from(model)
            if conditions:
                count_stmt = count_stmt.where(*conditions)
            total = int(await session.scalar(count_stmt) or 0)
            grand_total = int(
                await session.scalar(select(func.count()).select_from(model)) or 0
            )
            stmt = select(model).order_by(model.id)
            if conditions:
                stmt = stmt.where(*conditions)
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            rows: list[Any] = list((await session.execute(stmt)).scalars())
        return LedgerPage(
            items=rows, total=total, grand_total=grand_total, page=page, page_size=page_size
        )

    # ---------- 种子装配 ----------

    def _enriched_seeds(
        self, models: dict[str, dict[str, Any]]
    ) -> tuple[list[SeedRow], list[str]]:
        """指标种子 × M3 口径字段组（grain/unit/modifiers/ambiguous 从 YAML 投影）。"""
        m3_rules = {
            str(rule["id"]): rule for rule in (models["m3"].get("rules") or [])
        }
        return enrich_metric_seeds(m3_rules)

    def _plain_seeds(self) -> list[SeedRow]:
        """非指标账种子（术语/对象/关系/白名单/工作流/Action——C1 现值照抄）。"""
        return [
            *sem_domain.TERM_SEEDS,
            *sem_domain.OBJECT_SEEDS,
            *sem_domain.RELATION_SEEDS,
            *sem_domain.WHITELIST_SEEDS,
            *sem_domain.WORKFLOW_SEEDS,
            *sem_domain.ACTION_SEEDS,
        ]

    # ---------- 单行投影（幂等核心） ----------

    async def _upsert(
        self, session: AsyncSession, seed: SeedRow, actor: Actor
    ) -> tuple[int, int]:
        """新行 INSERT（revision v1）/ 行变 UPDATE（revision v+1）/ 未变零写。

        比对口径＝行投影字典（基线列除外）：材质化一枚新行，与现行行逐列同值
        即幂等重放零写。返回 (inserted, changed)。
        """
        model, fresh = _materialize(seed)
        current = await session.get(model, _pk_of(seed))
        fresh_values = _row_dict(model, fresh)
        if current is not None and _row_dict(model, current) == fresh_values:
            return 0, 0
        version = await latest_row_version(session, seed.domain, seed.row_id)
        if current is None:
            session.add(fresh)
        else:
            for key, value in fresh_values.items():
                setattr(current, _attr_of(key), value)
            current.updated_at = now()
        session.add(
            SemLedgerRevision(
                domain=seed.domain,
                row_id=seed.row_id,
                version=version + 1,
                payload=_json_safe(fresh_values),  # 该版全行快照（99 §2.8）
                changed_by=actor.who,
                source_proposal_id=None,  # 同步器投影非提案汇入——可溯锚＝ref（审计 meta）
                changed_at=now(),
            )
        )
        await session.flush()
        action = "insert" if current is None else "update"
        LOGGER.info(
            "semantics %s %s#%s（revision v%d）", action, seed.domain, seed.row_id, version + 1
        )
        return (1, 0) if action == "insert" else (0, 1)

    async def _upsert_sem_version(self, session: AsyncSession) -> None:
        """全量版本单例行种子（v37——C1/C3 演示值同源）；同步器不推全量版本。

        全量版本轴与行版本轴显式分离（C2 对账 8）：本行不在 sem_ledger_revision
        内留痕；版本推进归治理链发布事务（C3），发布批接管本种子行后移除回填。
        """
        row = await session.get(SemVersion, "current")
        if row is None:
            session.add(
                SemVersion(
                    id="current", current=SEMANTIC_CURRENT_SEED, created_at=now(), updated_at=now()
                )
            )
        elif row.current != SEMANTIC_CURRENT_SEED:
            row.current = SEMANTIC_CURRENT_SEED  # 种子值幂等回填（发布批接管前）
            row.updated_at = now()


# ---------- 载荷 ↔ ORM 落位（列名照 99 §2.8；键＝投影 payload 口径） ----------


def _keyword_conditions(
    keyword: str | None, *columns: Any
) -> list[ColumnElement[bool]]:
    """keyword 全文筛（00 §4.5）——子串匹配（台账中文量级，大小写无关由 ilike 承担）。"""
    if not keyword:
        return []
    pattern = f"%{keyword}%"
    return [or_(*(column.ilike(pattern) for column in columns))]


def _term_conditions(
    keyword: str | None, status: list[str] | None, owner: str | None
) -> list[ColumnElement[bool]]:
    conditions = _keyword_conditions(keyword, SemTerm.term, SemTerm.type, SemTerm.def_)
    if status:
        conditions.append(SemTerm.status_key.in_(status))
    if owner:
        conditions.append(SemTerm.owner == owner)
    return conditions


def _pk_of(seed: SeedRow) -> Any:
    """各账主键：int 注册序族（C1 四账 id）直用 int；wf 前缀与 Action 用注册名。"""
    int_domains = ("term", "metric", "object", "relation", "whitelist")
    return int(seed.row_id) if seed.domain in int_domains else seed.row_id


def _materialize(seed: SeedRow) -> tuple[type[Any], Any]:
    """SeedRow → (ORM 模型类, 新行实例)；payload 键按 99 §2.8 列投影。"""
    p = seed.payload
    at = now()
    if seed.domain == "term":
        return SemTerm, SemTerm(
            id=int(seed.row_id), term=p["term"], type=p["type"], def_=p["def"],
            status=p["status"], status_key=p["status_key"], owner=p["owner"],
            source=p["source"], version=int(p["version"]),
            expires_at=p.get("expires_at"), created_at=at, updated_at=at,
        )
    if seed.domain == "metric":
        name = str(p["name"])
        mark = p.get("mark")
        if mark is None:
            mark = name[0] if name[:1] in ("★", "☆") else None
        slot = str(p.get("slot_name") or metric_slot_name(name))
        return SemMetric, SemMetric(
            id=int(seed.row_id), name=name, mark=mark,
            slot_name=slot, def_=p["def"],
            grain=str(p["grain"]), unit=str(p["unit"]),
            status=list(p["status"]), owner=p["owner"], source=p["source"],
            dispute=p.get("dispute"), modifiers=p.get("modifiers"),
            ambiguous=bool(p.get("ambiguous", False)),
            calibers=list(p.get("calibers") or []), default_caliber=p.get("default_caliber"),
            version=int(p["version"]), created_at=at, updated_at=at,
        )
    if seed.domain == "object":
        return SemObject, SemObject(
            id=int(seed.row_id), obj=p["obj"], attr=p.get("attr"), status=p["status"],
            owner=p.get("owner"), source=p["source"], version=p.get("version"),
            created_at=at, updated_at=at,
        )
    if seed.domain == "relation":
        return SemRelation, SemRelation(
            id=int(seed.row_id), rel=p["rel"], read=p["read"], source=p["source"],
            created_at=at, updated_at=at,
        )
    if seed.domain == "whitelist":
        return SemJoinWhitelist, SemJoinWhitelist(
            id=int(seed.row_id), left_table=p["left_table"], right_table=p["right_table"],
            verdict=p["verdict"], tables=p["tables"], how=p["how"],
            version=int(p["version"]), created_at=at, updated_at=at,
        )
    if seed.domain == "workflow":
        return SemWorkflow, SemWorkflow(
            id=seed.row_id, name=p["name"], status=p["status"], account=p.get("account"),
            source=p.get("source"), card=dict(p["card"]), version=p.get("version"),
            created_at=at, updated_at=at,
        )
    if seed.domain == "action":
        return SemAction, SemAction(
            id=seed.row_id, register_name=p["register_name"],
            business_name=p["business_name"], created_at=at, updated_at=at,
        )
    raise OntologyDriftError(f"未登记的种子域：{seed.domain}")


def _row_dict(model: type[Any], row: Any) -> dict[str, Any]:
    """现行行 → 投影口径字典（基线列除外；def 列名 ↔ def_ 属性名对齐）。"""
    values: dict[str, Any] = {}
    for column in model.__table__.columns:
        if column.name in _BASELINE_COLUMNS:
            continue
        attr = "def_" if column.name == "def" else column.name
        values[column.name] = getattr(row, attr)
    return values


def _attr_of(key: str) -> str:
    return "def_" if key == "def" else key


def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
    """revision.payload jsonb 落位：date→ISO（json 不识 date）；其余原样。"""

    def convert(value: Any) -> Any:
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [convert(v) for v in value]
        return value

    return {str(k): convert(v) for k, v in payload.items()}

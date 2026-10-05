"""infra.config —— 配置装载（真源分载：config.yaml 文件 + .env 凭证注入）。

- 真源裁决（99 §2.13）：D1 params/model_list 的真源＝config/models.yaml
  （写回＋热加载——D1 端点 3 合同原文）；D5 预算/开关落 DB（gateway 域），
  两真源禁令——本模块只装文件侧，不碰 DB 侧。
- 凭证不进 git：yaml 里 ${VAR} / ${VAR:-默认} 占位符经环境变量或 .env 解析
  （os.environ 优先，.env 文件兜底；空值视同未设置）。
- 数据库连接规格：config/database.yaml → infra.db.DatabaseSpec（99 §4.2
  DatabaseSpec「config.yaml 装载，infra.config 供给」）。
- 本模块只依赖 stdlib/pydantic(-settings)/yaml/infra.db——不咬上层（B16/B1）。
"""

from __future__ import annotations

import logging
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infra.db import DatabaseSpec

LOGGER = logging.getLogger("infra.config")

_REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_YAML = _REPO_ROOT / "config" / "models.yaml"
DATABASE_YAML = _REPO_ROOT / "config" / "database.yaml"
ENTITY_TYPES_JSON = _REPO_ROOT / "config" / "entity_types.json"
DOTENV = _REPO_ROOT / ".env"

# ${VAR} / ${VAR:-default}（默认值可为空串）
_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class InfraSettings(BaseSettings):
    """infra 层环境参数（.env / 环境变量注入；生产值由部署环境覆盖）。

    sm4_key：SM4 字段加密密钥（hex 32 位＝16 字节，infra.crypto 消费）——
    缺省为开发默认值，仅开发态可用；生产必须经环境变量注入覆盖。
    minio_*：对象存储（infra.object_storage 消费）——缺省对齐 compose 演示
    拓扑（宿主 9000 / petro / petro12345，见 compose.yaml minio 服务段）；
    生产凭证经环境变量注入覆盖。
    """

    model_config = SettingsConfigDict(
        env_file=DOTENV, env_file_encoding="utf-8", extra="ignore"
    )

    sm4_key: str = "00112233445566778899aabbccddeeff"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "petro"
    minio_secret_key: str = "petro12345"
    minio_secure: bool = False
    # neo4j_*：图存储（infra.graph_store 消费）——缺省对齐 compose 演示拓扑
    # （bolt 7687 / neo4j·petro12345，见 compose.yaml neo4j 服务段）；生产凭证
    # 经环境变量注入覆盖。
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "petro12345"


@lru_cache(maxsize=1)
def get_settings() -> InfraSettings:
    return InfraSettings()


def _dotenv_vars() -> dict[str, str]:
    """解析 .env 的简单 KEY=VALUE 行（不导出 os.environ——只作解析兜底源）。"""
    values: dict[str, str] = {}
    if DOTENV.is_file():
        for line in DOTENV.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, raw = stripped.partition("=")
            value = raw.strip().strip('"').strip("'")
            if value:  # 空值视同未设置（模板注释形态 PG_PASSWORD= 不覆盖默认）
                values[key.strip()] = value
    return values


def resolve_placeholders(value: Any) -> Any:
    """递归解析结构中的 ${VAR} / ${VAR:-default}——os.environ 优先，.env 兜底。"""

    def substitute(match: re.Match[str]) -> str:
        var, default = match.group(1), match.group(2)
        for source in (os.environ.get(var), _dotenv_vars().get(var), default):
            if source is not None and source != "":
                return source
        LOGGER.warning("配置占位符 ${%s} 无环境值亦无默认，落空串", var)
        return ""

    if isinstance(value, str):
        return _PLACEHOLDER.sub(substitute, value)
    if isinstance(value, dict):
        return {k: resolve_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_placeholders(item) for item in value]
    return value


# ---------- 模型注册表（D1 真源——gateway 消费） ----------


class ModelEntry(BaseModel):
    """models.yaml 的单条模型注册（B6：业务代码只认别名）。"""

    alias: str
    provider: str
    model: str
    base_url: str = ""
    api_key: str = ""
    context_window: int = 0
    group: str = "standard"
    # D1 model_list 展示三件（缺省回退＝model 名/空注记——gateway 投影消费）
    name: str = ""
    access: str = ""
    note: str = ""


class RoutingConfig(BaseModel):
    default: str = ""
    fallback_order: list[str] = Field(default_factory=list)


class PricesConfig(BaseModel):
    input_per_mtok: float = 0.0
    output_per_mtok: float = 0.0


class GatewayParamsSpec(BaseModel):
    """models.yaml `gateway:` 段——D1 配置面四参数（数值边界校验归 gateway 域，本类只承形状）。

    真源纪律（00 §13 档①直改即生效）：D1 端点 3 保存＝写回本段四行＋热加载；
    "表单里每个数字对应文件里的一行"。缺省值＝D1 合同示例值。
    """

    allowed_fails: int = 2
    cooldown_seconds: int = 60
    num_retries: int = 3
    request_timeout: int = 30


class StreamConfig(BaseModel):
    """出站流式消费参数（G-01——独立顶层段：D1 配置面按固定四键整块重写 gateway
    段，新键放那里会被下次保存抹掉；本段带默认值，旧 yaml 无此段照常校验）。"""

    idle_timeout: float = 30.0  # 流空闲超时秒——连续无新帧判上游假死（网关可切备）
    max_seconds: float = 600.0  # 单次流总时长护栏秒——防持续出帧但失控的 runaway
    llm_max_concurrency: int = 2  # 全局 LLM 并发上限（G-06 信号量——超限排队等而非挂死）


class ModelsConfig(BaseModel):
    models: list[ModelEntry] = Field(default_factory=list)
    routing: RoutingConfig = RoutingConfig()
    prices: dict[str, PricesConfig] = Field(default_factory=dict)
    gateway: GatewayParamsSpec = Field(default_factory=GatewayParamsSpec)
    stream: StreamConfig = Field(default_factory=StreamConfig)


_models_cache: ModelsConfig | None = None


def load_models_config(path: Path | None = None) -> ModelsConfig:
    """装载并解析 models.yaml（占位符解析后 pydantic 校验）；每次即热加载。"""
    global _models_cache
    target = path or MODELS_YAML
    raw = resolve_placeholders(yaml.safe_load(target.read_text(encoding="utf-8")))
    config = ModelsConfig.model_validate(raw)
    _models_cache = config
    return config


def get_models_config() -> ModelsConfig:
    """带缓存的读取面（首次懒装载）——gateway 例行取数走这里。"""
    if _models_cache is None:
        return load_models_config()
    return _models_cache


def reload_models_config() -> ModelsConfig:
    """热加载缝：D1 端点 3「写回 config.yaml 并热加载」的读侧落点。"""
    return load_models_config()


# ---------- D1 配置面写回（gateway 段四参数；写边界归 gateway 域，文件 IO 归本模块） ----------

# gateway 段块头（块体＝四行 key: value，至下一个顶层键或 EOF）；顶格无缩进。
# 行内注释保留权在写回方：块头/块体都带注解，写回后文件仍自释（"表单里每个
# 数字对应文件里的一行"）。
_GATEWAY_BLOCK_HEAD = "gateway:"
_GATEWAY_BLOCK_BODY = (
    "  allowed_fails: {allowed_fails}           # 连续失败判故障阈值，1–10",
    "  cooldown_seconds: {cooldown_seconds}       # 故障冷却秒数，10–600",
    "  num_retries: {num_retries}             # 网关层重试次数，0–5（业务侧永不重试）",
    "  request_timeout: {request_timeout}        # 单次调用超时秒，5–120",
)


def _top_level_key(line: str) -> str:
    """顶格键名（剥行内注释与空白）——空串＝非顶层键行。"""
    bare = line.split("#", 1)[0].rstrip()
    if not bare or bare[0] in (" ", "\t", "-"):
        return ""
    return bare.split(":", 1)[0].strip()


def read_models_yaml_text(path: Path | None = None) -> str:
    """models.yaml 全文原样读出（D1 端点 2 `yaml` 字段＝「config.yaml 全文」）。"""
    return (path or MODELS_YAML).read_text(encoding="utf-8")


def upsert_gateway_params(
    params: Mapping[str, int], path: Path | None = None
) -> ModelsConfig:
    """写回 gateway 段四行并热加载（D1 端点 3；其余段零改动）。

    块替换策略：定位顶格 `gateway:` 段（行内注释不碍匹配），吞掉其后缩进行/
    空行至下一个顶格键或 EOF，原位重写注解块——文件里其余字节（头注释/
    占位符）逐字保留，密钥占位符 ${VAR} 永不落明文。无块则文件尾追加。

    原子替换（P0-05 审查收口）：写前先对渲染文本做内存解析＋模型校验
    （渲染坏不落盘——真源不被写坏）；落盘走「同目录临时文件＋os.replace」
    ——并发读者只见旧全文或新全文、无半截 yaml，写一半崩则旧文件原封不动。
    热加载（load_models_config）失败由调用方收口（service→ConfigWriteError）。
    """
    target = path or MODELS_YAML
    text = target.read_text(encoding="utf-8")
    order = ("allowed_fails", "cooldown_seconds", "num_retries", "request_timeout")
    missing = [key for key in order if key not in params]
    if missing:
        raise ValueError(f"gateway 参数缺项: {missing}")
    values = {key: int(params[key]) for key in order}
    head_note = "                     # D1 配置面四参数（端点 3 保存＝写回本段并热加载）"
    block = [_GATEWAY_BLOCK_HEAD + head_note]
    block += [line.format(**values) for line in _GATEWAY_BLOCK_BODY]
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if _top_level_key(ln) == "gateway"), None)
    if start is None:
        rendered = text.rstrip("\n") + "\n\n" + "\n".join(block) + "\n"
    else:
        end = start + 1
        while end < len(lines) and (lines[end].startswith((" ", "\t")) or not lines[end].strip()):
            end += 1
        rendered = "\n".join([*lines[:start], *block, *lines[end:]]) + "\n"
    # 写前校验：渲染文本可解析可校验才允许落盘（fail-fast——真源禁被写坏）
    ModelsConfig.model_validate(resolve_placeholders(yaml.safe_load(rendered)))
    _atomic_write_text(target, rendered)
    return load_models_config(target)  # 热加载同一目标文件（缓存随之指向新配置）


def _atomic_write_text(target: Path, text: str) -> None:
    """同目录临时文件＋os.replace 原子替换（write_text 先截断后写的非原子替换）。

    POSIX rename 原子：读侧要么见旧全文要么见新全文；任一步失败清理临时
    文件并抛出，旧文件原封不动（写一半崩＝真源无损）。权限位随原文件。
    """
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(text)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.chmod(tmp_name, stat.S_IMODE(target.stat().st_mode))
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


# ---------- 数据库连接规格（→ infra.db.DatabaseSpec） ----------

_ROLES: tuple[str, ...] = ("primary", "replica", "midplatform")


def load_database_specs(path: Path | None = None) -> list[DatabaseSpec]:
    """装载 config/database.yaml → DatabaseSpec 列表（角色＝primary/replica/midplatform）。

    凭证经 ${VAR:-默认} 注入——文件只进 git 结构与开发默认，真实凭证走环境。
    """
    target = path or DATABASE_YAML
    raw = resolve_placeholders(yaml.safe_load(target.read_text(encoding="utf-8")))
    specs: list[DatabaseSpec] = []
    for role_key, body in (raw.get("database") or {}).items():
        if role_key not in _ROLES:
            raise ValueError(f"未登记的数据库角色: {role_key!r}（99 §4.1 三角色）")
        entry = dict(body)
        specs.append(
            DatabaseSpec(
                name=entry.pop("name", role_key),
                role=role_key,  # 键已按 _ROLES 校验
                driver=entry.pop("driver"),
                host=entry.pop("host"),
                port=int(entry.pop("port")),
                database=entry.pop("database"),
                user=entry.pop("user"),
                password=entry.pop("password"),
                pool_size=int(entry.pop("pool_size", 10)),
                max_overflow=int(entry.pop("max_overflow", 5)),
                pool_recycle_seconds=int(entry.pop("pool_recycle_seconds", 1800)),
                slow_query_ms=int(entry.pop("slow_query_ms", 800)),
                readonly=bool(entry.pop("readonly", role_key != "primary")),
            )
        )
        if entry:
            raise ValueError(f"database.yaml 角色 {role_key!r} 存在未消费字段: {sorted(entry)}")
    return specs


# ---------- 本体派生词表（P1-01 导出物——kb 入库路由话题分析辅助消费） ----------


def load_entity_type_names(path: Path | None = None) -> list[str]:
    """读 config/entity_types.json 的实体类型名册（P1-01 派生物，进 git）。

    消费面（B1 v0.3「入库路由（阶段 1 实施项）」专节）：入库路由话题分析用
    全局默认能力（gateway.complete petro-main）＋本词表辅助——不依赖目标库
    配置（库未定时防「鸡生蛋」）。文件缺失/损坏显式报错（导出物是仓库内
    提交物，缺文件即部署错误，禁静默吞掉）。
    """
    return [
        str(item["name"])
        for item in load_ontology_export("entity_types", path)
    ]


def load_ontology_export(
    kind: str, path: Path | None = None
) -> list[dict[str, Any]]:
    """读 config/{kind}.json 的本体导出物行（P1-01 派生物，进 git）。

    kind ∈ entity_types | relation_types——B5 抽取设置对号强校（端点 3）
    与 A2 映射卡/白名单的合同消费面。文件缺失/损坏显式报错（导出物是仓库
    内提交物，缺文件即部署错误，禁静默吞掉——对号强校的「接线就绪」判据
    由此派生：可装载＝接线后强校；不可装载＝部署错误，同样不静默放行）。
    """
    import json

    target = path or (_REPO_ROOT / "config" / f"{kind}.json")
    raw = json.loads(target.read_text(encoding="utf-8"))
    return list(raw.get(kind, []))

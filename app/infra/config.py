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
DOTENV = _REPO_ROOT / ".env"

# ${VAR} / ${VAR:-default}（默认值可为空串）
_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class InfraSettings(BaseSettings):
    """infra 层环境参数（.env / 环境变量注入；生产值由部署环境覆盖）。

    sm4_key：SM4 字段加密密钥（hex 32 位＝16 字节，infra.crypto 消费）——
    缺省为开发默认值，仅开发态可用；生产必须经环境变量注入覆盖。
    """

    model_config = SettingsConfigDict(
        env_file=DOTENV, env_file_encoding="utf-8", extra="ignore"
    )

    sm4_key: str = "00112233445566778899aabbccddeeff"


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


class RoutingConfig(BaseModel):
    default: str = ""
    fallback_order: list[str] = Field(default_factory=list)


class PricesConfig(BaseModel):
    input_per_mtok: float = 0.0
    output_per_mtok: float = 0.0


class ModelsConfig(BaseModel):
    models: list[ModelEntry] = Field(default_factory=list)
    routing: RoutingConfig = RoutingConfig()
    prices: dict[str, PricesConfig] = Field(default_factory=dict)


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

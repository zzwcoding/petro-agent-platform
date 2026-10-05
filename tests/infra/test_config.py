"""infra.config 单测——占位符解析 / models.yaml / database.yaml 装载（不依赖外部服务）。"""

import os
import stat
from pathlib import Path

import pytest
import yaml

from app.infra import config
from app.infra.config import (
    get_settings,
    load_database_specs,
    load_models_config,
    resolve_placeholders,
    upsert_gateway_params,
)


@pytest.fixture(autouse=True)
def _reset_models_cache() -> None:
    """用例结束复位进程级注册表缓存（infra.config 全局态——测试隔离）。

    P1-08b：hot_reload 用例的 m1/m2 残留缓存会让同进程后续的真 LLM 消费
    （chat 冒烟——config 默认装载）判 NoAvailableRoute——任意测试装载过
    非默认 yaml 都必须复位（gateway/llm_client 测试同款纪律）。
    """
    yield
    config._models_cache = None


def test_placeholder_env_over_dotenv_over_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        'A_FROM_FILE=file-value\nB_EMPTY=""\nC_QUOTED=\'quoted\'\n', encoding="utf-8"
    )
    monkeypatch.setattr(config, "DOTENV", dotenv)
    monkeypatch.setenv("A_OVERRIDE", "env-wins")
    monkeypatch.setenv("B_EMPTY", "")  # 空串环境值视同未设置（模板注释形态）

    resolved = resolve_placeholders(
        {
            "env_wins": "${A_OVERRIDE:-fallback}",
            "from_file": "${A_FROM_FILE:-fallback}",
            "default_only": "${A_MISSING:-fell-back}",
            "no_default": "${A_MISSING}",
            "empty_falls_to_default": "${B_EMPTY:-def}",
            "quoted_unwrapped": "${C_QUOTED}",
        }
    )
    assert resolved == {
        "env_wins": "env-wins",
        "from_file": "file-value",
        "default_only": "fell-back",
        "no_default": "",
        "empty_falls_to_default": "def",
        "quoted_unwrapped": "quoted",
    }
    assert os.environ["B_EMPTY"] == ""


def test_placeholder_recursive_structures() -> None:
    raw: dict[str, object] = {
        "list": ["${P1:-a}", {"nested": "${P2:-b}"}],
        "num": 3,
        "plain": "x",
    }
    assert resolve_placeholders(raw) == {
        "list": ["a", {"nested": "b"}],
        "num": 3,
        "plain": "x",
    }


def test_load_models_yaml_from_repo() -> None:
    config.load_models_config()  # 装载即进缓存
    models = config.get_models_config()
    aliases = {m.alias for m in models.models}
    assert {"petro-main", "petro-lite"} <= aliases
    main = next(m for m in models.models if m.alias == "petro-main")
    assert main.provider == "anthropic"
    assert main.model == "MiniMax-M3"
    assert models.routing.default == "petro-main"
    assert models.routing.fallback_order == ["petro-main", "petro-lite"]
    assert models.prices["default"].input_per_mtok == 1.0
    assert models.prices["default"].output_per_mtok == 3.0


def _write_models(path: Path, alias: str, model: str) -> Path:
    path.write_text(
        f"models:\n  - alias: {alias}\n    provider: anthropic\n    model: {model}\n"
        f"routing:\n  default: {alias}\n  fallback_order: [{alias}]\nprices: {{}}\n",
        encoding="utf-8",
    )
    return path


def test_load_models_config_hot_reload(tmp_path: Path) -> None:
    loaded = load_models_config(_write_models(tmp_path / "m1.yaml", "m1", "M1"))
    assert loaded.models[0].alias == "m1"
    assert config.get_models_config().models[0].alias == "m1"  # 缓存随最近一次装载

    reloaded = load_models_config(_write_models(tmp_path / "m2.yaml", "m2", "M2"))
    assert reloaded.models[0].alias == "m2"  # 热加载：写回后重读（D1 端点 3）
    assert config.get_models_config().models[0].alias == "m2"


def test_load_database_specs_from_repo() -> None:
    specs = load_database_specs()
    primary = next(s for s in specs if s.role == "primary")
    assert primary.driver == "postgresql"
    assert primary.readonly is False
    url = primary.url()
    assert url.drivername == "postgresql+asyncpg"  # 本仓驱动定型（99 雏形 psycopg→asyncpg）
    assert url.host is not None  # 占位符已解析（默认或环境值）


def test_load_database_specs_repo_midplatform_readonly() -> None:
    """M-01：repo database.yaml 自带 midplatform 只读段——独立 URL/只读账号。

    跨库指向中台库（DP-03 湖真身：dev 期与平台库同实例不同 schema，生产独立
    实例走环境量）；强制只读（99 §4.1），凭证占位符经 ${VAR:-默认} 解析。
    """
    specs = {s.role: s for s in load_database_specs()}
    mid = specs["midplatform"]
    primary = specs["primary"]
    assert mid.readonly is True  # 强制只读（99 §4.1——连接层与账号级双保险）
    assert mid.driver == "postgresql"
    assert mid.user  # 只读账号在位
    assert mid.user != primary.user  # 独立于 primary 账号
    assert mid.url() != primary.url()  # 独立 URL（跨库指向中台库）


def test_load_database_specs_placeholder_and_roles(tmp_path: Path) -> None:
    conf = tmp_path / "database.yaml"
    conf.write_text(
        yaml.safe_dump(
            {
                "database": {
                    "primary": {
                        "driver": "postgresql",
                        "host": "${IT_DB_HOST:-db-host}",
                        "port": "${IT_DB_PORT:-6543}",
                        "database": "itdb",
                        "user": "itu",
                        "password": "${IT_DB_PW:-itpw}",
                    },
                    "midplatform": {
                        "driver": "postgresql",
                        "host": "mid",
                        "port": 5432,
                        "database": "mid",
                        "user": "mu",
                        "password": "mp",
                        "readonly": True,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    specs = {s.role: s for s in load_database_specs(conf)}
    assert specs["primary"].host == "db-host"
    assert specs["primary"].port == 6543
    assert specs["primary"].password == "itpw"
    assert specs["midplatform"].readonly is True


def test_load_database_specs_rejects_unknown_role(tmp_path: Path) -> None:
    conf = tmp_path / "database.yaml"
    conf.write_text(
        yaml.safe_dump(
            {
                "database": {
                    "staging": {
                        "driver": "postgresql",
                        "host": "h",
                        "port": 5432,
                        "database": "d",
                        "user": "u",
                        "password": "p",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="未登记的数据库角色"):
        load_database_specs(conf)


def test_load_database_specs_env_injection_overrides_repo_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DEP-01 件③：config/database.yaml 的 ${VAR:-默认} 生产口令注入机制——两半边机判。

    环境量在位时覆盖 yaml 开发默认（生产口令经密管/环境注入的唯一通道——
    平台 primary 的 PG_* 与中台只读路由的 MIDPLATFORM_PG_* 同机制）；缺省
    回落 yaml 默认（「生产禁默认口令上生产」的机制基础——runbook
    docs/deploy/db-accounts-runbook.md 口令纪律节）。.env 兜底源在本测隔离
    （DOTENV 指向不存在路径），只验 os.environ 与 yaml 默认两端。
    """
    monkeypatch.setattr(config, "DOTENV", tmp_path / "no-dotenv-here")
    monkeypatch.setenv("PG_HOST", "prod-db.internal")
    monkeypatch.setenv("PG_PASSWORD", "from-secret-manager")
    monkeypatch.setenv("MIDPLATFORM_PG_HOST", "mid.internal")
    specs = {s.role: s for s in load_database_specs()}
    assert specs["primary"].host == "prod-db.internal"
    assert specs["primary"].password == "from-secret-manager"
    assert specs["midplatform"].host == "mid.internal"

    monkeypatch.delenv("PG_HOST")
    monkeypatch.delenv("PG_PASSWORD")
    monkeypatch.delenv("MIDPLATFORM_PG_HOST")
    fallback = {s.role: s for s in load_database_specs()}
    assert fallback["primary"].host == "localhost"  # config/database.yaml 开发默认
    assert fallback["primary"].password == "petro"  # 开发默认口令——生产禁用（runbook 口令纪律）
    assert fallback["midplatform"].host == "localhost"


def test_settings_sm4_key_shape() -> None:
    settings = get_settings()
    assert len(settings.sm4_key) == 32  # hex 32 位＝16 字节
    bytes.fromhex(settings.sm4_key)  # 可解码


# ---------- gateway 段写回：原子替换（P0-05 审查收口——写一半崩真源无损） ----------

_FULL_PARAMS = {
    "allowed_fails": 4,
    "cooldown_seconds": 90,
    "num_retries": 1,
    "request_timeout": 20,
}


def _models_yaml_with_gateway(path: Path) -> Path:
    path.write_text(
        "models:\n"
        "  - alias: m1\n"
        "    provider: anthropic\n"
        "    model: M1\n"
        "routing:\n"
        "  default: m1\n"
        "  fallback_order: [m1]\n"
        "prices: {}\n"
        "gateway:\n"
        "  allowed_fails: 2\n"
        "  cooldown_seconds: 60\n"
        "  num_retries: 3\n"
        "  request_timeout: 30\n",
        encoding="utf-8",
    )
    return path


def test_upsert_gateway_params_atomic_no_temp_leftover(tmp_path: Path) -> None:
    """原子替换落盘：内容生效、原权限位保住、目录无临时文件残留。"""
    path = _models_yaml_with_gateway(tmp_path / "models.yaml")
    path.chmod(0o644)
    loaded = upsert_gateway_params(_FULL_PARAMS, path)
    assert loaded.gateway.allowed_fails == 4  # 热加载随写回生效
    text = path.read_text(encoding="utf-8")
    assert "allowed_fails: 4" in text and "cooldown_seconds: 90" in text
    assert stat.S_IMODE(path.stat().st_mode) == 0o644  # 临时文件权限随原文件
    assert [p.name for p in tmp_path.iterdir()] == ["models.yaml"]  # 无 .models-*.tmp 残留


def test_upsert_gateway_params_write_failure_keeps_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """替换中途失败＝旧文件原封不动＋临时文件清理（写一半崩真源无损可回滚）。"""
    path = _models_yaml_with_gateway(tmp_path / "models.yaml")
    before = path.read_text(encoding="utf-8")

    def broken_replace(src: object, dst: object) -> None:
        raise OSError("disk on fire")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError, match="disk on fire"):
        upsert_gateway_params(_FULL_PARAMS, path)
    assert path.read_text(encoding="utf-8") == before  # 旧全文未被动过（无半截态）
    assert [p.name for p in tmp_path.iterdir()] == ["models.yaml"]  # 临时文件已清理

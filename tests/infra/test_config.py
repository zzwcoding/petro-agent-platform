"""infra.config 单测——占位符解析 / models.yaml / database.yaml 装载（不依赖外部服务）。"""

import os
from pathlib import Path

import pytest
import yaml

from app.infra import config
from app.infra.config import (
    get_settings,
    load_database_specs,
    load_models_config,
    resolve_placeholders,
)


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


def test_settings_sm4_key_shape() -> None:
    settings = get_settings()
    assert len(settings.sm4_key) == 32  # hex 32 位＝16 字节
    bytes.fromhex(settings.sm4_key)  # 可解码

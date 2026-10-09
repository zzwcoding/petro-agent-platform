"""appv2.infra.config 启动装配健壮单测——V2-26「启动时配置缺失不裸崩两形」钉测面。

两形＝①配置文件缺失（裸 FileNotFoundError）②文件在但空/段缺/角色段缺必需键
（裸 AttributeError／裸 KeyError('driver')／缺 database 段静默回空清单）。
钉法：异常须为 ValueError 族（显式报错类 ConfigLoadError——既有 except
ValueError 收口面兼容）且文案自释（路径/角色/缺什么/拒绝启动——fail-fast
拒绝启动语义不变（M-01 禁静默回落），只是报错可读可行动）。

消费面＝appv2.api.app 生产组合根（compose_production_registry 启动时装载
load_database_specs＋load_chat_settings——appv2/api/app.py:85-86）；V1 侧
app/infra/config.py 是独立复制件非本票边界，V1 行为零触碰。
"""

from pathlib import Path

import pytest

from appv2.infra.config import (
    load_chat_settings,
    load_database_specs,
    load_models_config,
)

# ---------- 形一：配置文件缺失 ----------


def test_load_database_specs_missing_file_explicit_error(tmp_path: Path) -> None:
    """形一：database.yaml 不在——显式报错（路径＋角色＋拒绝启动），非裸
    FileNotFoundError 文案（启动装配面 create_app 生产组合消费此装载器）。"""
    with pytest.raises(ValueError, match="拒绝启动") as exc_info:
        load_database_specs(tmp_path / "absent-database.yaml")
    message = str(exc_info.value)
    assert "absent-database.yaml" in message  # 报错自带路径
    assert "database.yaml" in message  # 报错自带装载物角色


def test_load_chat_settings_missing_file_explicit_error(tmp_path: Path) -> None:
    """形一（chat 开关同文件同装载器）：database.yaml 缺失——显式报错，
    非裸 FileNotFoundError。段缺省（文件在、无 chat 段）仍＝全默认缺省——
    登记过的旧部署形态语义不在本钉域。"""
    with pytest.raises(ValueError, match="拒绝启动"):
        load_chat_settings(tmp_path / "absent-database.yaml")


def test_load_models_config_missing_file_explicit_error(tmp_path: Path) -> None:
    """形一（models.yaml 同收口单点）：文件缺失——显式报错非裸 FileNotFoundError。"""
    with pytest.raises(ValueError, match=r"models\.yaml"):
        load_models_config(tmp_path / "absent-models.yaml")


# ---------- 形二：文件在但空/段缺/必需键缺 ----------


def test_load_database_specs_empty_file_explicit_error(tmp_path: Path) -> None:
    """形二之一：文件在但为空——显式报错点名空文件，非裸 AttributeError
    （现状 NoneType.get 裸崩形态）。"""
    conf = tmp_path / "database.yaml"
    conf.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="为空"):
        load_database_specs(conf)


def test_load_database_specs_missing_section_explicit_error(tmp_path: Path) -> None:
    """形二之二：database 段整段缺——显式报错（禁静默回落：现状缺段静默回
    空清单＝零库继续装配的静默形，一并收口）。"""
    conf = tmp_path / "database.yaml"
    conf.write_text("chat:\n  freshness_gate_enabled: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="database 段"):
        load_database_specs(conf)


def test_load_database_specs_missing_required_keys_named(tmp_path: Path) -> None:
    """形二之三：角色段缺必需键——逐键点名（哪个角色段缺什么），非裸
    KeyError('driver')。"""
    conf = tmp_path / "database.yaml"
    conf.write_text(
        "database:\n  primary:\n    name: 主库\n    host: localhost\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="driver") as exc_info:
        load_database_specs(conf)
    assert "primary" in str(exc_info.value)  # 报错自带角色段


def test_load_models_config_empty_file_explicit_error(tmp_path: Path) -> None:
    """形二（models.yaml）：空文件——显式报错（现状＝pydantic ValidationError
    英文裸文案，一并收口）。"""
    empty = tmp_path / "models.yaml"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="为空"):
        load_models_config(empty)


# ---------- 非收口域（语义零漂移守护钉） ----------


def test_load_chat_settings_missing_section_still_defaults(tmp_path: Path) -> None:
    """段缺省（文件在、无 chat 段）＝全默认 true——旧部署形态登记语义零变化
    （V2-26 只收「裸崩/静默回空」两形，不动合法缺省面）。"""
    conf = tmp_path / "database.yaml"
    conf.write_text("database:\n  primary:\n    driver: postgresql\n", encoding="utf-8")
    from appv2.infra.config import ChatSettings

    assert load_chat_settings(conf) == ChatSettings(freshness_gate_enabled=True)


def test_load_database_specs_repo_true_source_still_loads() -> None:
    """仓内真源 database.yaml 照常装载（收口只换报错形态，不改合法装载行为）。
    replica 段仓内预留未配置（读回落 primary——99 §4.1），在册角色＝primary＋
    midplatform。"""
    specs = {s.role: s for s in load_database_specs()}
    assert {"primary", "midplatform"} <= set(specs)

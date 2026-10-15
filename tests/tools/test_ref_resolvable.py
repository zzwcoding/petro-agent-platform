"""真源引用可解析闸看守测试（治「指向不存在的真源」复发形态）。

对应病例：规格把红线挂到真源里不存在的边界规则编号（幻影闸 `R7`）；把阈值挂到
不存在该条目的真源节。本测试保证闸真跑且当前为绿。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

TOOL = Path(__file__).resolve().parents[2] / "tools" / "ref_resolvable.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("ref_resolvable", TOOL)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_green_on_current_repo() -> None:
    """闸绿实判：当前全部规格的真源引用与边界规则编号均可解析。"""
    assert _load().check() == []


def test_rule_ids_cover_modules_and_linter() -> None:
    """编号真源＝modules.md 边界规则标签 ∪ importlinter 契约名前缀（含只在后者的 R5b）。"""
    ids = _load().rule_ids()
    assert {"R1", "R2", "R8"} <= ids
    assert "R5b" in ids  # 只在 importlinter 契约名里出现


def test_resolves_shorthand_and_reports_missing() -> None:
    """解析器：简写引用可解析（walk/08、synth/S3）；不存在的路径返回 None。"""
    rr = _load()
    assert rr.resolve_ref("walk/08") is not None
    assert rr.resolve_ref("synth/S3") is not None
    assert rr.resolve_ref("walk/99-不存在.md") is None

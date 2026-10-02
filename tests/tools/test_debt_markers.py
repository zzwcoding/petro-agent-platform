"""债务标记闸看守测试（P1-13——AGENTS.md 硬纪律 8 的 pytest 面）。

CLI（tools/debt_markers.py check/report）与 CI 步骤同源调用。三面：
规则红绿注入（裸短语/可解析标签/不可解析标签/测试豁免）、去向解析单测、
当前仓实判（闸绿）。
"""

import importlib.util
from pathlib import Path
from typing import Any

TOOL = Path(__file__).resolve().parents[2] / "tools" / "debt_markers.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("debt_markers", TOOL)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_repo(tmp_path: Path, rel: str, content: str) -> Path:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return tmp_path


def test_bare_phrase_is_violation(tmp_path: Path) -> None:
    """裸债务短语（无 DEBT 标签）＝红。"""
    cc = _load()
    repo = _make_repo(tmp_path, "web/src/landing/X.jsx", "// 这里挂后续批再说\n")
    violations, _ = cc.scan(repo, tickets_text="")
    assert len(violations) == 1 and "裸债务短语" in violations[0]


def test_tagged_resolvable_is_clean(tmp_path: Path) -> None:
    """携 DEBT 标签且票号在票面真实存在＝绿；上方 2 行内的标签也算数。"""
    cc = _load()
    repo = _make_repo(
        tmp_path, "web/src/landing/X.jsx",
        "// DEBT(P1-99)：占位\nconst a = 1 // 随其票落\n",
    )
    violations, _ = cc.scan(repo, tickets_text="## P1-99 某票\n")
    assert violations == []


def test_unresolvable_target_is_violation(tmp_path: Path) -> None:
    """标签去向不可解析（票号不存在/自由文本）＝红——陈旧标记与假登记同判。"""
    cc = _load()
    repo = _make_repo(
        tmp_path, "web/src/landing/X.jsx",
        "// 随其票落 DEBT(以后再说)\n",
    )
    violations, _ = cc.scan(repo, tickets_text="## P1-99 某票\n")
    assert len(violations) == 1 and "不可解析" in violations[0]


def test_phase_and_owner_targets_resolve(tmp_path: Path) -> None:
    """阶段\\d 与 Owner 是合法去向；票号校验走票面文本。"""
    cc = _load()
    assert cc.resolve_target("阶段2-B4页", "")
    assert cc.resolve_target("Owner", "")
    assert cc.resolve_target("P1-12", "票面含 P1-12")
    assert not cc.resolve_target("P1-12", "票面没有")
    assert not cc.resolve_target("随便写", "票面含 P1-12")


def test_test_files_exempt_from_strict(tmp_path: Path) -> None:
    """测试文件豁免 strict（断言合法引用 UI 文案原文）——不进违规面。"""
    cc = _load()
    repo = _make_repo(tmp_path, "web/src/landing/X.test.jsx", "// 未接线的断言原文\n")
    violations, _ = cc.scan(repo, tickets_text="")
    assert violations == []


def test_inventory_collects_app_without_violation(tmp_path: Path) -> None:
    """app/ 裸短语进盘点不进违规（inventory 面）。"""
    cc = _load()
    repo = _make_repo(tmp_path, "app/domains/x.py", "# 场景注册表随其票落\n")
    violations, inventory = cc.scan(repo, tickets_text="")
    assert violations == []
    assert len(inventory) == 1 and "随其票落" in inventory[0]


def test_gate_green_on_current_repo() -> None:
    """闸绿实判：当前仓 web 源码债务短语全部携可解析标签（P1-13 治理后）。"""
    assert _load().check() == []

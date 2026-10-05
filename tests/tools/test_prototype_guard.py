"""原型树保护闸看守测试（DEP-01 件④——原型树纪律的 pytest 面）。

CLI（tools/prototype_guard.py check/update）与 CI 前端 job 步骤同源调用。
三面：清单形状看守（schema/键集与脚本 _TRACKED 对账）、当前仓实判（闸绿——
原型树与 W-LAND 同步点还原态一致）、规则红绿注入（漂移/缺失/复原——规则
本身的红绿双向，全程在临时根内，零触碰真实原型树）。
"""

import importlib.util
import json
from pathlib import Path
from typing import Any

TOOL = Path(__file__).resolve().parents[2] / "tools" / "prototype_guard.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("prototype_guard", TOOL)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pg = _load()


def test_manifest_shape_matches_tracked() -> None:
    """清单形状：manifest 文件在位、schema 对、键集与脚本 _TRACKED 逐键对账。"""
    manifest = json.loads(pg.MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema"] == pg.SCHEMA
    assert set(manifest["files"]) == set(pg._TRACKED)
    assert manifest["sync_points"] == pg._TRACKED
    assert all(len(d) == 64 for d in manifest["files"].values())  # sha256 hex


def test_guard_green_on_current_repo() -> None:
    """当前仓实判：真实原型树与清单一致（W-LAND 同步点 3c2d63a/04f9606 还原态）。"""
    assert pg.check() == 0


def _tmp_repo(tmp_path: Path, initial: str, final: str | None = None) -> Any:
    """临时根：按 initial 内容建 manifest，再覆写 final（缺省同 initial＝绿基线）；
    _TRACKED 收窄到注入文件（update 遍历 _TRACKED 建清单，临时根只备此一件）。
    红绿注入全程在临时根内，零触碰真实原型树。"""
    rel = "web/src/pages/E2.jsx"
    (tmp_path / "web" / "src" / "pages").mkdir(parents=True)
    target = tmp_path / rel
    target.write_text(initial, encoding="utf-8")
    manifest = {"schema": pg.SCHEMA, "note": "t", "sync_points": {rel: "x"},
                "files": {rel: pg._sha256(target)}}
    (tmp_path / "web" / "prototype-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8")
    if final is not None:
        target.write_text(final, encoding="utf-8")
    saved = (pg.REPO_ROOT, pg.MANIFEST_PATH, pg._TRACKED)
    pg.REPO_ROOT = tmp_path
    pg.MANIFEST_PATH = tmp_path / "web" / "prototype-manifest.json"
    pg._TRACKED = {rel: "x"}
    return saved


def test_guard_red_on_drift_and_missing(tmp_path: Path) -> None:
    """红绿注入：篡改→RED（退出 1＋点名漂移文件）；删除→RED（缺失）。"""
    saved = _tmp_repo(tmp_path, "original")
    try:
        assert pg.check() == 0  # 注入基线绿
        target = tmp_path / "web" / "src" / "pages" / "E2.jsx"
        target.write_text("tampered", encoding="utf-8")
        assert pg.check() == 1  # 内容漂移＝红
        target.unlink()
        assert pg.check() == 1  # 文件缺失＝红
    finally:
        pg.REPO_ROOT, pg.MANIFEST_PATH, pg._TRACKED = saved


def test_update_regen_restores_green(tmp_path: Path, capsys) -> None:
    """合法原型同步批路径：update 重生成清单后 check 复绿（写盘与打印留痕）。"""
    saved = _tmp_repo(tmp_path, "new-prototype-state", final="even-newer")
    try:
        assert pg.check() == 1  # 旧清单对新内容＝红（合法同步批的预期起点）
        assert pg.update() == 0
        assert "已重生成" in capsys.readouterr().out
        assert pg.check() == 0  # 新清单＝绿
    finally:
        pg.REPO_ROOT, pg.MANIFEST_PATH, pg._TRACKED = saved

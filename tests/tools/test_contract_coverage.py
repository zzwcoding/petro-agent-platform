"""合同覆盖率闸看守测试（P1-12——AGENTS.md 硬纪律 8 的 pytest 面）。

CLI（tools/contract_coverage.py check）与 CI 步骤同源调用；本测试使闸在
pytest 门禁内同样生效（纯静态对账零底座依赖——无 PG 也可跑）。三面：
清单形状看守（归一/字段齐全）、闸绿实判（当前仓状态）、违规判定注入
（无主缺口/实现多出——规则本身的红绿双向）。
"""

import importlib.util
import re
from pathlib import Path
from typing import Any

TOOL = Path(__file__).resolve().parents[2] / "tools" / "contract_coverage.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("contract_coverage", TOOL)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_shape() -> None:
    """清单形状看守：21 册全量在场、字段齐全、路径参数已归一（无具名参数）。"""
    cc = _load()
    endpoints = cc.load_manifest()["endpoints"]
    assert len(endpoints) >= 150  # 当前 173 条——合同册扩册只会更多
    books = {str(row["book"]) for row in endpoints}
    assert {"A1", "B1", "B2", "B3", "B4", "B5", "C1", "D1", "D2"} <= books
    for row in endpoints:
        assert str(row["method"]) in {"GET", "POST", "PUT", "DELETE", "PATCH"}
        assert str(row["path"]).startswith("/api/")
        for param in re.findall(r"\{[^}]*\}", str(row["path"])):
            assert param == "{}"  # 路径参数归一——具名差异不进对账


def test_gate_green_on_current_repo() -> None:
    """闸绿实判：实现有/清单无＝0；清单有/实现无每条带 owner（硬纪律 8）。"""
    assert _load().check() == []


def test_reconcile_flags_unowned_and_undeclared() -> None:
    """违规判定注入（红绿双向）：无主缺口红、已归属绿、实现多出红。"""
    cc = _load()
    endpoints = [
        {"book": "X1", "no": "1", "method": "GET", "path": "/api/x/owned", "owner": "阶段 2"},
        {"book": "X1", "no": "2", "method": "GET", "path": "/api/x/unowned", "owner": ""},
    ]
    implemented = {("GET", "/api/x/owned"), ("GET", "/api/x/extra")}
    problems = cc.reconcile(endpoints, implemented)
    assert len(problems) == 2
    assert any("无主缺口" in p and "/api/x/unowned" in p for p in problems)
    assert any("实现有/清单无" in p and "/api/x/extra" in p for p in problems)
    # 已归属未实现＋实现面全对上 → 绿
    assert cc.reconcile(endpoints[:1], {("GET", "/api/x/owned")}) == []


def test_v2_manifest_shape_and_match() -> None:
    """V2 面看守（Owner 2026-10-15 裁定「建」）：冻结基线形状合法且与 appv2/api 路由完全对上。"""
    cc = _load()
    endpoints = cc.load_manifest(cc.V2_MANIFEST_PATH)["endpoints"]
    assert len(endpoints) >= 4  # 现 4 条（E1–E4）；端点增删须同步清单
    for row in endpoints:
        assert str(row["book"]) == "V2"
        assert str(row["path"]).startswith("/api/v2/")
        assert str(row["owner"]).strip()  # 冻结基线每条带归属注记
        for param in re.findall(r"\{[^}]*\}", str(row["path"])):
            assert param == "{}"  # 路径参数归一
    assert cc.reconcile(endpoints, cc.parse_implemented(cc.V2_API_DIR)) == []

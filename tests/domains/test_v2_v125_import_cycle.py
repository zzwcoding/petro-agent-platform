"""V2-125 第 8 项｜`appv2.query ↔ appv2.tools` 循环 import 看守（单文件收集不再 ERROR）。

病灶（HEAD 既有；V2-104／V2-105／V2-107／V2-124 四票实证）：`appv2.query.domain`
包导入期 `from appv2.tools.anchors import well_tokens`，而 `appv2.tools.__init__`
反向 `from appv2.query import (ASKBACK_TIME_CHOICES, …)`——**先导入 `appv2.query`**
时 `appv2.query` 尚在初始化中，`tools` 包根取四常量即 ImportError。全量套件因
导入序（有模块先引 `appv2.tools`）侥幸通过；**单文件收集**
（`pytest tests/domains/test_v2_context.py`／`tests/domains/test_v2_agent_verify.py`）
直接 ERROR。

修法（V2-125，落 `appv2/query/domain.py`）：`well_tokens` 改**惰性局部导入**
（调用点唯一＝`build_query_plan`），单点件本体零搬动（V2-112 单点语义不变）。

本看守以**子进程**复现「哪个包先被导入」——同进程内已缓存的 `sys.modules`
会让环失效（这正是全量套件侥幸通过的机理），故必须隔离子进程。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, cwd=REPO_ROOT)


def test_query_first_import_no_cycle() -> None:
    """先导 `appv2.query`（tools 未预载）——修前 ImportError，修后 ok。"""
    proc = _run([sys.executable, "-c", "import appv2.query; import appv2.tools; print('ok')"])
    assert proc.returncode == 0, f"先导 query 仍成环：\n{proc.stdout}\n{proc.stderr}"


def test_tools_first_import_no_cycle() -> None:
    """先导 `appv2.tools`（反向序）——两侧序皆通才算环解。"""
    proc = _run([sys.executable, "-c", "import appv2.tools; import appv2.query; print('ok')"])
    assert proc.returncode == 0, f"先导 tools 仍成环：\n{proc.stdout}\n{proc.stderr}"


def test_lazy_single_point_still_reachable() -> None:
    """惰性局部导入不破单点：包导入后调用点仍取得同一 `well_tokens` 单点件。"""
    code = (
        "from appv2.query.domain import build_query_plan\n"
        "from appv2.tools.anchors import well_tokens\n"
        "from datetime import date\n"
        "plan = build_query_plan(metric_slot='日产油', question='W-22 井昨天日产油',"
        " today=date(2026, 10, 19))\n"
        "assert plan.well_slot == well_tokens('W-22 井昨天日产油') == ('W-22',), plan.well_slot\n"
        "print('ok')\n"
    )
    proc = _run([sys.executable, "-c", code])
    assert proc.returncode == 0, f"惰性导入后单点调用异常：\n{proc.stdout}\n{proc.stderr}"


def test_single_file_collection_green() -> None:
    """票面验收面：两文件**单文件收集**零 ERROR（修前两文件皆 ERROR）。"""
    proc = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/domains/test_v2_context.py",
            "tests/domains/test_v2_agent_verify.py",
        ]
    )
    assert proc.returncode == 0, f"单文件收集仍 ERROR：\n{proc.stdout}\n{proc.stderr}"
    assert "ERROR" not in proc.stdout, proc.stdout

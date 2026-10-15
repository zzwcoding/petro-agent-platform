"""spec 闸看守测试：规格闸必须真跑且当前为绿。

对应 AGENTS.md 硬纪律 8（两道机器闸绿是交付闸）与 sdd-flow 核心原则 7
（文档里写着却没有闸的禁令等于不存在）——本测试保证 `tools/check_specs.py`
接进 CI 且不会被静默改红。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_spec_gate_green() -> None:
    """跑一遍规格闸：退出码非 0 即红（FAIL 明细在 stdout）。"""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "check_specs.py"), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, f"spec gate 未绿：\n{proc.stdout}\n{proc.stderr}"

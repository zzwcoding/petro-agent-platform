"""tests 根 conftest —— V2-92 检索留痕测试隔离（取证面去污染）＋ V2-116 核验档位 env-pin。

`appv2.tools.retrieval_calllog` 的留痕目录缺省是生产路径
`logs/retrieval_calls/`：任何调 `doc_retrieve` 的测试（`test_v2_guide_ac_anchors.py`
等）都会把夹具行写进生产留痕件，污染 EB9 类取证（`20261018.jsonl` 实测 468 行里
451 行是 pytest 行、裸 grep 假阳性）。本 autouse 夹具把留痕面整体钉在测试语境：

- `_LOG_DIR` → 本测 `tmp_path/retrieval_calls`（生产 `logs/` 零写）；
- `_ORIGIN` → `test`（记录 `origin` 键的值源——与运行语境 `runtime` 区分）。

夹具是**全测试树**兜底（tests/ 根级 conftest），子目录 conftest 无需重复；
个别测试仍可自行 `monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", ...)` 覆盖
（如 `test_v2_retrieval_calllog.py`——monkeypatch 逆序恢复，互不干扰）。

**V2-116 核验档位 env-pin（2026-10-18，Kimi 评审修正 2：新建机制）**：核验动作档位
（`VERIFY_ACTION ∈ {off, observe, repair, delete}`，单点＝`appv2.runtimev2.verification.constants`）
缺省档为 `delete`（保既有行为）。本夹具把全测试树的 env **钉为 `delete`**——既有 ~34 例删句
断言（`test_v2_verification.py` 33 ＋ 真删行断言 1）零回退；`observe`／`off`／`repair` 档用例在
**本例内** `monkeypatch.setenv` 显式覆盖（同一 monkeypatch 实例逆序恢复，互不干扰）。夹具末尾带
pin 生效断言（机制证据，非静默设置）。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_retrieval_calllog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """留痕目录钉 tmp_path＋origin 注入 test（任何测试不写生产 `logs/retrieval_calls/`）。"""
    from appv2.tools import retrieval_calllog

    monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", tmp_path / "retrieval_calls")
    monkeypatch.setattr(retrieval_calllog, "_ORIGIN", "test")


@pytest.fixture(autouse=True)
def _pin_verify_action(monkeypatch: pytest.MonkeyPatch) -> None:
    """核验动作档位 env-pin（V2-116；Kimi 评审修正 2——新建机制，非「加一行」）。

    全测试树把 `VERIFY_ACTION` 钉为 `delete`（＝缺省档，保既有删句断言零回退）；
    档位用例在本例内 `monkeypatch.setenv` 显式覆盖。末尾 pin 生效断言＝机制在场证据。
    """
    from appv2.runtimev2.verification import VERIFY_ACTION_ENV, VERIFY_MODE_DELETE

    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_DELETE)
    assert os.environ[VERIFY_ACTION_ENV] == VERIFY_MODE_DELETE

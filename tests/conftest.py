"""tests 根 conftest —— V2-92 检索留痕测试隔离（取证面去污染）。

`appv2.tools.retrieval_calllog` 的留痕目录缺省是生产路径
`logs/retrieval_calls/`：任何调 `doc_retrieve` 的测试（`test_v2_guide_ac_anchors.py`
等）都会把夹具行写进生产留痕件，污染 EB9 类取证（`20261018.jsonl` 实测 468 行里
451 行是 pytest 行、裸 grep 假阳性）。本 autouse 夹具把留痕面整体钉在测试语境：

- `_LOG_DIR` → 本测 `tmp_path/retrieval_calls`（生产 `logs/` 零写）；
- `_ORIGIN` → `test`（记录 `origin` 键的值源——与运行语境 `runtime` 区分）。

夹具是**全测试树**兜底（tests/ 根级 conftest），子目录 conftest 无需重复；
个别测试仍可自行 `monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", ...)` 覆盖
（如 `test_v2_retrieval_calllog.py`——monkeypatch 逆序恢复，互不干扰）。
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_retrieval_calllog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """留痕目录钉 tmp_path＋origin 注入 test（任何测试不写生产 `logs/retrieval_calls/`）。"""
    from appv2.tools import retrieval_calllog

    monkeypatch.setattr(retrieval_calllog, "_LOG_DIR", tmp_path / "retrieval_calls")
    monkeypatch.setattr(retrieval_calllog, "_ORIGIN", "test")

"""V2-98 文档漂移看守（债务闸票号扩面的同批文档面）。

背景：V2-97 把 `graph_query` 从工具注册面摘除（名单 5→4，代码保留＋`DEBT(V2-97)`），
但承诺面文档仍写「五工具」——承诺与实现二选一，本票取实现面同步。三条判据：

1. `specs/modules.md`／`docs/architecture-v2.md` 文本内「五工具」零残留；
2. 两文件内 `graph_query` 的每一处出现都带「摘除」或「V2-97」语境（摘除注记在场）；
3. 承诺面改成四工具（不是把登记删掉了事）。
另加第 4 条：`appv2/tools/__init__.py` 包 docstring 同批同步（任务 2 第三项）。
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = ("specs/modules.md", "docs/architecture-v2.md")


def _text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_doc_no_five_tools_residue() -> None:
    """「五工具」零残留；`graph_query` 出现处均带摘除/V2-97 语境（或零出现）。"""
    for rel in DOCS:
        text = _text(rel)
        assert "五工具" not in text, f"{rel} 仍残留「五工具」——实现面已是四工具"
        for num, line in enumerate(text.splitlines(), start=1):
            if "graph_query" in line:
                assert "摘除" in line or "V2-97" in line, (
                    f"{rel}:{num} 提到 graph_query 却无摘除/V2-97 语境：{line.strip()}"
                )


def test_doc_keeps_registered_tool_face() -> None:
    """承诺面跟随注册面（不是删登记）：两文件写明在册名单＝六工具（V2-96 后）。"""
    for rel in DOCS:
        text = _text(rel)
        assert "六工具" in text, f"{rel} 未写明六工具在册名单"
        assert "fetch_section" in text and "fetch_report" in text, f"{rel} 未登记两新读面"


def test_tools_package_docstring_synced() -> None:
    """`appv2/tools/__init__.py` 包 docstring：摘除注记在场，graph_query 语境带 V2-97。"""
    src = (REPO / "appv2" / "tools" / "__init__.py").read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(src)) or ""
    assert "摘除" in doc and "V2-97" in doc, "包 docstring 未同步摘除注记（V2-97）"
    for num, line in enumerate(doc.splitlines(), start=1):
        if "graph_query" in line:
            assert "摘除" in line or "V2-97" in line, (
                f"包 docstring 第 {num} 行提到 graph_query 却无摘除/V2-97 语境：{line.strip()}"
            )

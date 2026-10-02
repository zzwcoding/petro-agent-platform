"""合同覆盖率闸（P1-12——端点 3 事故的固化，AGENTS.md 硬纪律 8）。

事故背景（2026-10-02 复盘）：A1 册端点 3（会话消息回放）在阶段 1 静默无主——
拆票范围节手写枚举漏条、挂账自然语言丢词、缺口标记只活在代码注释里；四门禁
全是「实现内部质量」闸，没有「实现 vs 合同」覆盖率闸，收官验收全绿也照不亮。
本闸把「合同 → 票 → 实现」的映射从人脑枚举换成机器对账：

- ``export``：解析 teach 合同册（specs/api/*.md 端点表）→ 导出
  ``config/contract_endpoints.json`` 清单（生成物进 git，entity_types.json
  先例）。**合同册变更后须重跑 export 并提交**（Owner 操作——真源在仓外，
  CI 无法再生）；已有 owner 归属注记按 (book, no) 键保留不丢。
- ``check``：清单 × app/api 路由双向对账（pytest 看守测试同源调用）——
  ①「实现有/清单无」必须为 0（新增路由先登记合同册或随差异登记重导出）；
  ②「清单有/实现无」每条必须带非空 ``owner`` 归属（票号/挂账行/阶段标注），
  空 owner＝无主缺口，闸红。

路径参数归一：合同册 ``{id}``/``{pageId}`` 与实现 ``{session_id}``/``{page_id}``
同归一为 ``{}`` 后比对（只对端点缺失/多出敏感，DTO 形状漂移归测试面看守）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "contract_endpoints.json"
TEACH_DEFAULT = REPO_ROOT.parent / "teach-petro-agent"

# 合同册端点表行：| 3 | `GET /api/chat/sessions/{id}/messages` | ... |
_ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*`?(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s`|]+)")
_SKIP_BOOKS = {"README", "98", "99"}
_METHODS = ("get", "post", "put", "delete", "patch")
_PARAM = re.compile(r"\{[^}]+\}")


def normalize(path: str) -> str:
    """路径参数统一归一为 {}（合同册与实现的参数命名不强行一致）。"""
    return _PARAM.sub("{}", path)


def parse_contract(teach: Path) -> list[dict[str, object]]:
    """解析 specs/api/*.md 端点表 → [{book,no,method,path}]（去重保序）。"""
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for md in sorted((teach / "specs" / "api").glob("*.md")):
        book = md.name.split("-")[0]
        if book in _SKIP_BOOKS:
            continue
        for line in md.read_text(encoding="utf-8").splitlines():
            m = _ROW.match(line.strip())
            if m:
                key = (book, m.group(2), normalize(m.group(3)))
                if key not in seen:
                    seen.add(key)
                    rows.append(
                        {"book": book, "no": m.group(1),
                         "method": m.group(2), "path": normalize(m.group(3))}
                    )
    return rows


def parse_implemented(api_dir: Path | None = None) -> set[tuple[str, str]]:
    """实现路由面：APIRouter(prefix=..) ＋ @router.<method>("..")（源码静态扫）。"""
    api_dir = api_dir or (REPO_ROOT / "app" / "api")
    routes: set[tuple[str, str]] = set()
    prefix_re = re.compile(r'APIRouter\([^)]*prefix="([^"]+)"')
    route_re = re.compile(r'@router\.(\w+)\("([^"]+)"')
    for py in sorted(api_dir.glob("*.py")):
        prefix = ""
        for line in py.read_text(encoding="utf-8").splitlines():
            pm = prefix_re.search(line)
            if pm:
                prefix = pm.group(1)
            rm = route_re.match(line.strip())
            if rm and rm.group(1).lower() in _METHODS:
                routes.add((rm.group(1).upper(), normalize(prefix + rm.group(2))))
    return routes


def load_manifest() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("endpoints"), list):
        raise SystemExit(f"清单形状非法（endpoints 缺失）：{MANIFEST_PATH}")
    return manifest


def reconcile(
    endpoints: list[dict[str, object]], implemented: set[tuple[str, str]]
) -> list[str]:
    """双向对账（纯函数——看守测试注入面）→ 违规清单（空＝绿）。"""
    contract: dict[tuple[str, str], dict[str, object]] = {
        (str(row["method"]), str(row["path"])): row for row in endpoints
    }
    problems: list[str] = []
    for method, path in sorted(implemented - set(contract)):
        problems.append(f"实现有/清单无：{method} {path}（先登记合同册或差异登记，再重跑 export）")
    for (method, path), row in sorted(contract.items()):
        if (method, path) not in implemented and not str(row.get("owner") or "").strip():
            problems.append(
                f"无主缺口：[{row['book']}] 端点{row['no']} {method} {path}"
                "（合同有/实现无且无 owner 归属——补票/挂账/阶段标注后重跑 export）"
            )
    return problems


def check() -> list[str]:
    """清单 × app/api 路由双向对账 → 违规清单（空＝绿）。看守测试与 CLI 同源调用。"""
    manifest = load_manifest()
    return reconcile(manifest["endpoints"], parse_implemented())  # type: ignore[arg-type]


def export(teach: Path) -> None:
    """解析合同册 → 写清单（保留既有 owner 注记——按 (book,no) 键合并）。"""
    old: dict[tuple[str, str], str] = {}
    if MANIFEST_PATH.exists():
        for row in load_manifest()["endpoints"]:  # type: ignore[union-attr]
            old[(str(row["book"]), str(row["no"]))] = str(row.get("owner") or "")
    rows = parse_contract(teach)
    for row in rows:
        row["owner"] = old.get((str(row["book"]), str(row["no"])), "")
    payload = {
        "source": f"{teach}/specs/api（设计真源，只读引用——本文件是导出物，"
                  "合同册变更后重跑 export 并提交；owner=归属注记：票号/挂账行/阶段标注）",
        "exported_at": "2026-10-02",
        "gate": "tools/contract_coverage.py check（硬纪律 8——实现有/清单无必须为 0；"
                "清单有/实现无必须带 owner）",
        "endpoints": rows,
    }
    MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"导出 {len(rows)} 条 → {MANIFEST_PATH.relative_to(REPO_ROOT)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="合同覆盖率闸（AGENTS.md 硬纪律 8）")
    sub = parser.add_subparsers(dest="command", required=True)
    p_export = sub.add_parser("export", help="解析 teach 合同册 → config/contract_endpoints.json")
    p_export.add_argument("--teach", type=Path, default=TEACH_DEFAULT, help="teach 仓根路径")
    sub.add_parser("check", help="清单 × app/api 路由双向对账（违规 exit 1）")
    args = parser.parse_args(argv)
    if args.command == "export":
        if not args.teach.exists():
            raise SystemExit(f"teach 仓不存在：{args.teach}（--teach 指定）")
        export(args.teach)
        return 0
    problems = check()
    if problems:
        print("合同覆盖率闸红：")
        for p in problems:
            print(f"  - {p}")
        return 1
    manifest = load_manifest()
    total = len(manifest["endpoints"])  # type: ignore[union-attr]
    print(f"合同覆盖率闸绿：{total} 条合同端点双向对账通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

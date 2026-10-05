#!/usr/bin/env python3
"""原型树保护闸（DEP-01 件④）——web 原型树同步页 hash 与清单比对。

背景（W-LAND 教训固化）：原型树（web/src/pages|data 的 mock 态）是 teach 仓
原型真源的快照（同步点 3c2d63a/04f9606），平时禁改——页面讨论与改版只动
teach 原型真源，阶段开始时一次性同步定稿（AGENTS.md 硬纪律 0）。本闸对原型
树关键文件计算 SHA-256，与 ``web/prototype-manifest.json`` 清单逐文件比对：
不一致（内容漂移）或缺失（文件被删/改名）即退出码 1 并逐条打印漂移文件。

用法（仓根执行；路径按脚本位置解析，与当前目录无关）：
    python3 tools/prototype_guard.py check    # 比对（缺省动作）
    python3 tools/prototype_guard.py update   # 重生成清单（合法原型同步批专用）

误报面（T1 审查点）：闸只盯清单内文件——落地树接线/页面迭代（landing/、
api/ 真客户端、flows/ 等）零触碰清单内路径，不会误红；**合法的原型树同步批**
（阶段开工一次性定稿）属预期漂移，随批跑 ``update`` 重生成清单并同票提交
（manifest 与页面同 commit，闸在 CI 前端 job 看守后续提交）。

纯标准库（hashlib/json/argparse/pathlib）——CI ubuntu-latest python3 零依赖可跑。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "web" / "prototype-manifest.json"

# 原型树关键文件（首版清单＝W-LAND 双树归位 a63808a 还原态，已与同步点
# blob hash 逐字等证：E2/B4/api/e2 ← 3c2d63a、A2 ← 04f9606）。后续原型同步
# 批增删条目直接改 _TRACKED 并 update。
_TRACKED: dict[str, str] = {
    "web/src/pages/E2.jsx": "3c2d63a",
    "web/src/pages/A2.jsx": "04f9606",
    "web/src/pages/B4.jsx": "3c2d63a",
    "web/src/api/e2.js": "3c2d63a",
}

SCHEMA = "petro.prototype-manifest/1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict:
    """按 _TRACKED 现算 hash 组装清单（update 模式与首版生成共用）。"""
    return {
        "schema": SCHEMA,
        "note": (
            "原型树关键文件 SHA-256 清单（DEP-01 件④原型树保护闸）。比对器＝"
            "tools/prototype_guard.py check（CI 前端 job 看守）。清单内文件＝teach "
            "原型真源的同步快照，平时禁改；合法原型同步批（阶段开工一次性定稿）"
            "随批 `python3 tools/prototype_guard.py update` 重生成本清单并同票提交。"
        ),
        "sync_points": dict(_TRACKED),
        "files": {rel: _sha256(REPO_ROOT / rel) for rel in sorted(_TRACKED)},
    }


def check() -> int:
    """清单比对：漂移/缺失逐条打印，有漂移退出 1（CI 红即不过）。"""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        print(f"原型闸 RED：manifest schema 不识别——{manifest.get('schema')!r}")
        return 1
    drifted: list[str] = []
    missing: list[str] = []
    for rel, expected in manifest.get("files", {}).items():
        path = REPO_ROOT / rel
        if not path.is_file():
            missing.append(rel)
            continue
        actual = _sha256(path)
        if actual != expected:
            drifted.append(rel)
    if not drifted and not missing:
        print(f"原型闸 GREEN：原型树 {len(manifest['files'])} 个关键文件与清单一致"
              f"（同步点 {_TRACKED and sorted(set(_TRACKED.values()))}）。")
        return 0
    for rel in missing:
        print(f"原型闸 RED：文件缺失——{rel}")
    for rel in drifted:
        print(f"原型闸 RED：内容漂移——{rel}")
    print("处置：原型树禁改（AGENTS.md 硬纪律 0）——还原改动；如属合法原型同步批，"
          "随批 `python3 tools/prototype_guard.py update` 重生成清单并同票提交。")
    return 1


def update() -> int:
    """重生成清单（合法原型同步批专用）——写盘并打印新 hash 面。"""
    manifest = build_manifest()
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"原型闸 manifest 已重生成：{MANIFEST_PATH.relative_to(REPO_ROOT)}")
    for rel, digest in manifest["files"].items():
        print(f"  {digest[:16]}…  {rel}  ← 同步点 {manifest['sync_points'][rel]}")
    print("随票提交本清单与原型页改动（同 commit）。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="原型树保护闸（hash × 清单比对）")
    parser.add_argument("mode", nargs="?", default="check",
                        choices=("check", "update"), help="check＝比对（缺省）；update＝重生成清单")
    args = parser.parse_args(argv)
    return check() if args.mode == "check" else update()


if __name__ == "__main__":
    sys.exit(main())

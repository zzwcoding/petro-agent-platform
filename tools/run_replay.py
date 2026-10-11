"""tools/run_replay.py —— run 全过程只读回放（V2-54 黑匣子第②层）。

从 agent_v2_checkpoint 快照表按 run_id 解码每步通道值（官方读面
PgCheckpointer.alist 复用——零手写反序列化），渲染交 runtime.blackbox
统一语义面（人读转写／机器 JSON）。

用法（仓根执行——-m 模块形，v2_enrich_batch 同惯例）：
  uv run python -m tools.run_replay run-1df15b96           # 人读转写
  uv run python -m tools.run_replay run-1df15b96 --json    # 机器全量
  uv run python -m tools.run_replay run-1df15b96 --list    # 快照清单

只读纪律：会话走 ConnectionManager（B3 唯一 DB 出口——与 PgCheckpointer 内部
实现同源）；零写入零删除。tools 脚本 import appv2 先例＝tools/v2_enrich_batch.py。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any


async def _collect(run_id: str) -> list[dict[str, Any]]:
    """快照解码（时序正排）——每快照 {checkpoint_id, channels(曲面白名单内)}。"""
    from appv2.infra.config import load_database_specs
    from appv2.infra.db import ConnectionManager
    from appv2.runtime.blackbox import CURATED_CHANNELS
    from appv2.runtime.checkpointer import PgCheckpointer

    manager = ConnectionManager(load_database_specs())
    saver = PgCheckpointer(manager)
    config: dict[str, Any] = {"configurable": {"thread_id": run_id}}
    snapshots: list[dict[str, Any]] = []
    async for tpl in saver.alist(config):
        values = (tpl.checkpoint or {}).get("channel_values") or {}
        snapshots.append(
            {
                "checkpoint_id": str(
                    tpl.config["configurable"].get("checkpoint_id", "")
                ),
                "channels": {
                    key: value
                    for key, value in values.items()
                    if key in CURATED_CHANNELS
                },
            }
        )
    snapshots.reverse()  # alist 倒序（最新在前）——转写按时序正排
    return snapshots


def main() -> int:
    parser = argparse.ArgumentParser(description="run 全过程只读回放（黑匣子第②层）")
    parser.add_argument("run_id", help="run 号（run-XXXXXXXX）")
    parser.add_argument("--json", action="store_true", help="机器全量 JSON")
    parser.add_argument("--list", action="store_true", help="仅快照清单")
    parser.add_argument(
        "--distill", action="store_true", help="仅黑匣子蒸馏行（agent_v2_blackbox）"
    )
    args = parser.parse_args()

    from appv2.infra.config import load_database_specs
    from appv2.infra.db import ConnectionManager
    from appv2.runtime.store import RunStore

    if args.distill:
        store = RunStore(ConnectionManager(load_database_specs()))
        payload = await store.get_blackbox(args.run_id)
        if payload is None:
            print(f"无黑匣子行：{args.run_id}", file=sys.stderr)
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    from appv2.runtime.blackbox import render_snapshots

    snapshots = asyncio.run(_collect(args.run_id))
    if not snapshots:
        print(f"无快照：{args.run_id}（run 不存在或快照表空）", file=sys.stderr)
        return 1
    if args.list:
        for snap in snapshots:
            channels = sorted((snap.get("channels") or {}).keys())
            print(f"{snap['checkpoint_id']}  通道{len(channels)}: {', '.join(channels)}")
        return 0
    print(render_snapshots(snapshots, as_json=args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

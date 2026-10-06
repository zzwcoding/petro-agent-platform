"""DE-05 同文同切——跨进程双跑子进程（pytest 子进程独立建库入库一次）。

用法：`python _same_text_child.py <scenario> <db_path>`，stdout 输出单行 JSON：
原文块切片序列（section＋text，落卷序）＋sha256 指纹＋片数＋均长。

场景（敌意两翼——若结构路径仍查 LLM，两场景必分歧；DE-05 后 chunk 步不查
LLM，两场景必须同指纹，且等于纯规则基线）：
- llm_subset —— stub LLM 应答「合法但不完整」结构图（只报前半 2 标题）；
- llm_down   —— stub LLM 对结构提取抛异常（模拟 LLM 不可用→旧回退路径）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.domains.gateway import Completion  # noqa: E402
from app.domains.kb import KbService  # noqa: E402
from app.domains.kb.store import UploadStore, ensure_kb_tables  # noqa: E402
from app.infra.db import ConnectionManager, DatabaseSpec  # noqa: E402
from app.infra.eventbus import InMemoryEventBus  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "report_C_heading双样式裁剪.txt"
TEXT = FIXTURE.read_text(encoding="utf-8")
LINES = TEXT.splitlines()
ACTOR = "阿强 · 平台运维"

# fixture 标题行（1 基行号 5/8/13/16——提示词口径）与层级（DE-05 后无人消费，
# 仅作敌意 stub 应答素材：两场景若进入任何 LLM 消费面即互相分歧）。
_FULL = [
    {"line_no": 5, "title": LINES[4], "level": 1},
    {"line_no": 8, "title": LINES[7], "level": 2},
    {"line_no": 13, "title": LINES[12], "level": 1},
    {"line_no": 16, "title": LINES[15], "level": 2},
]


class _FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes) -> None:
        self.objects[key] = data

    async def presign_put(self, key: str, *, ttl_seconds: int = 1800) -> str:
        return f"https://minio.test/put/{key}"

    async def presign_get(self, key: str, *, ttl_seconds: int = 3600) -> str:
        return f"https://minio.test/get/{key}"

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def get_bytes(self, key: str) -> bytes:
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]


class _HostileCompleter:
    """敌意桩 LLM：结构提取应答按场景给「合法子集图」或直接抛异常。"""

    def __init__(self, answers: dict[str, str | Exception]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, str]] = []

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Completion:
        content = messages[-1]["content"]
        self.calls.append((caller, content))
        answer: str | Exception = self.answers.get(caller, "应答")
        if isinstance(answer, Exception):
            raise answer
        return Completion(
            content=answer,
            prompt_tokens=10,
            completion_tokens=5,
            usage_estimated=False,
            call_id="call-stub",
            cost_yuan=0.0001,
            fallback=False,
            served_alias=alias,
        )


async def _main(scenario: str, db_path: str) -> None:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=db_path, user="", password="", pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_kb_tables(manager.engine())
    if scenario == "llm_down":
        answers: dict[str, str | Exception] = {
            "kb.ingest.structure": RuntimeError("LLM 不可用（模拟断网）"),
        }
    elif scenario == "llm_subset":
        answers = {
            "kb.ingest.structure": json.dumps(
                {"headings": _FULL[:2]}, ensure_ascii=False
            ),
        }
    else:
        raise SystemExit(f"未知场景 {scenario}")
    answers.setdefault("kb.ingest.summary", "摘要")
    answers.setdefault("kb.ingest.questions", "问题？")
    service = KbService(
        manager, _HostileCompleter(answers), _FakeStorage(),
        eventbus=InMemoryEventBus(),
    )
    receipt = await service.create_library("完井报告库", "completion", ACTOR)
    up = await service.upload_init("C报告.txt", 2048, receipt.lib_id, ACTOR)
    row = await UploadStore(manager).get(up.upload_id)
    assert row is not None
    storage = service._storage
    await storage.put(row.object_key, TEXT.encode("utf-8"))
    confirm = await service.upload_confirm(up.upload_id, ACTOR)
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        task = await service.ingest_task(confirm.task_id)
        if task.state in ("done", "failed"):
            assert task.state == "done", f"入库失败：{task.state} {task.reason}"
            break
        await asyncio.sleep(0.02)
    else:
        raise SystemExit("入库等待超时")
    task_row = await service._tasks.get(confirm.task_id)
    assert task_row is not None
    frags = await service._fragments.for_report(task_row.report_id)
    seq_rows: list[tuple[int, str, str]] = []
    for f in frags:
        if f.type != "原文块":
            continue
        m = re.search(r"(\d+)$", f.id)
        seq_rows.append((int(m.group(1)) if m else 0, f.section or "", f.hit_text or ""))
    seq_rows.sort()
    pieces = [(section, text) for _, section, text in seq_rows]
    print(
        json.dumps(
            {
                "scenario": scenario,
                "n_pieces": len(pieces),
                "avg_len": round(
                    sum(len(t) for _, t in pieces) / max(len(pieces), 1), 1
                ),
                "sha256": hashlib.sha256(
                    json.dumps(pieces, ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
            },
            ensure_ascii=False,
        )
    )
    await manager.dispose()


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1], sys.argv[2]))

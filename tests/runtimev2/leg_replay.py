"""tests.runtimev2.leg_replay —— leg 格式帧流回放 harness（测试网 L3 钉的断言面）。

读 leg 格式 JSONL（真机 SSE 帧全量存档——`eval/results/V2-80-员工模拟批跑2/runs/
*.jsonl` 17 件为格式真源；`eval/results/frames/*.json` 是另一载体——单对象 frames
数组、int id，不在本 harness 辖域）：

    首行   {"leg": "open", "http": 200, "body": {"question": ...}}
    帧行   {"leg": "frame", "id": "0", "t": 0.04, "event": "step", "data": {...}}
    末行   {"summary": {...}}   # 可缺省；在场必须收尾且唯一

断言辅助（eng/04-测试网设计.md §五步骤 1 第二件地基）：
- 帧序列指纹比对：fingerprint()／assert_fingerprint()——event 序、"|" 连接，
  字符串形与序列形同参
- 指定 event 在场/缺席：assert_has(event, nth=)（返回第 n 帧，nth 从 1 计）／
  assert_absent(event)
- data 字段子集断言：assert_data(event, subset, nth=)——dict 递归子集、
  list/tuple 全等（序敏感）、标量相等

解析违例（空文件／首行非 open／缺 body.question/http／帧行缺 event/data/id/t／
summary 后仍出现帧行／summary 重复／open 不在首行／无法识别的行／非法 JSON）
一律 ValueError fail-fast——结构违例不静默吞。

构造入口有二：LegRecording.load(路径) 读真机存档；LegRecording(...) 直接构
（LegFrame 列表）供脚本化多轮合成流。冻结时钟处理在 tests.runtimev2.frozen_clock。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LEG_OPEN = "open"
LEG_FRAME = "frame"

RUNS_DIR = (
    Path(__file__).resolve().parents[2]
    / "eval" / "results" / "V2-80-员工模拟批跑2" / "runs"
)


def sample_leg(name: str) -> Path:
    """批跑样本路径（name 形如 "Q15"）——L3 golden 回放钉的原料入口。"""
    return RUNS_DIR / f"{name}.jsonl"


@dataclass(frozen=True)
class LegFrame:
    """单帧（leg=frame 行）——line 为 1 基源行号，断言失败定位用。"""

    id: str
    t: float
    event: str
    data: Mapping[str, Any]
    line: int


class LegRecording:
    """一份 leg 格式 JSONL 的解析结果＋按 event 序的断言辅助。"""

    def __init__(
        self,
        *,
        question: str,
        http: int,
        frames: Sequence[LegFrame],
        summary: Mapping[str, Any] | None,
        path: str | None = None,
    ) -> None:
        self._question = question
        self._http = http
        self._frames = tuple(frames)
        self._summary = summary
        self._path = path

    # ---------- 解析 ----------

    @classmethod
    def load(cls, path: str | Path) -> LegRecording:
        p = Path(path)
        rows: list[tuple[int, Any]] = []
        for lineno, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                rows.append((lineno, json.loads(raw)))
            except json.JSONDecodeError as e:
                raise ValueError(f"{p}:{lineno}: 非法 JSON——{e.msg}") from e
        if not rows:
            raise ValueError(f"{p}: 空文件——无 open 行")

        head_lineno, head = rows[0]
        if head.get("leg") != LEG_OPEN:
            raise ValueError(f"{p}:{head_lineno}: 首行 leg≠open（实为 {head.get('leg')!r}）")
        body = head.get("body")
        if not isinstance(body, Mapping) or "question" not in body:
            raise ValueError(f"{p}:{head_lineno}: open 行缺 body.question")
        http = head.get("http")
        if not isinstance(http, int) or isinstance(http, bool):
            raise ValueError(f"{p}:{head_lineno}: open 行缺 http（int）")

        frames: list[LegFrame] = []
        summary: Mapping[str, Any] | None = None
        for lineno, row in rows[1:]:
            leg = row.get("leg")
            if leg == LEG_OPEN:
                raise ValueError(f"{p}:{lineno}: open 行只许首行")
            if leg == LEG_FRAME:
                if summary is not None:
                    raise ValueError(f"{p}:{lineno}: summary 后仍出现帧行（summary 必须收尾）")
                event = row.get("event")
                if not isinstance(event, str) or not event:
                    raise ValueError(f"{p}:{lineno}: 帧行缺 event")
                data = row.get("data")
                if not isinstance(data, Mapping):
                    raise ValueError(f"{p}:{lineno}: 帧行缺 data（mapping）")
                fid = row.get("id")
                if not isinstance(fid, str):
                    raise ValueError(f"{p}:{lineno}: 帧行缺 id（str）")
                t = row.get("t")
                if not isinstance(t, (int, float)) or isinstance(t, bool):
                    raise ValueError(f"{p}:{lineno}: 帧行缺 t（数值）")
                frames.append(
                    LegFrame(id=fid, t=float(t), event=event, data=dict(data), line=lineno)
                )
            elif "summary" in row:
                if summary is not None:
                    raise ValueError(f"{p}:{lineno}: summary 行重复")
                if not isinstance(row["summary"], Mapping):
                    raise ValueError(f"{p}:{lineno}: summary 行非 mapping")
                summary = dict(row["summary"])
            else:
                raise ValueError(f"{p}:{lineno}: 无法识别的行（缺 leg=frame 形或 summary 形）")

        return cls(
            question=str(body["question"]),
            http=http,
            frames=frames,
            summary=summary,
            path=str(p),
        )

    # ---------- 观测面 ----------

    @property
    def question(self) -> str:
        return self._question

    @property
    def http(self) -> int:
        return self._http

    @property
    def frames(self) -> tuple[LegFrame, ...]:
        return self._frames

    @property
    def summary(self) -> Mapping[str, Any] | None:
        return self._summary

    def events(self) -> tuple[str, ...]:
        """帧 event 序（open/summary 不在其列——只数帧）。"""
        return tuple(f.event for f in self._frames)

    def frames_of(self, event: str) -> tuple[LegFrame, ...]:
        return tuple(f for f in self._frames if f.event == event)

    def count(self, event: str) -> int:
        return len(self.frames_of(event))

    def fingerprint(self) -> str:
        """帧序列指纹——event 序用 "|" 连接（跨 run 比对/落钉用稳定形）。"""
        return "|".join(self.events())

    # ---------- 断言面 ----------

    def assert_fingerprint(self, expected: str | Sequence[str]) -> None:
        want = expected if isinstance(expected, str) else "|".join(expected)
        got = self.fingerprint()
        if got != want:
            raise AssertionError(
                f"帧序列指纹失配（{self._where()}，{len(self._frames)} 帧）\n"
                f"  期望: {want}\n  实际: {got}"
            )

    def assert_has(self, event: str, *, nth: int = 1) -> LegFrame:
        """event 第 n 帧在场（nth 从 1 计）；返回该帧供链式断言。"""
        if nth < 1:
            raise ValueError(f"nth 从 1 计（实为 {nth}）")
        hits = self.frames_of(event)
        if len(hits) < nth:
            raise AssertionError(
                f"event={event!r} 第 {nth} 帧缺席（在场 {len(hits)} 帧——{self._where()}）"
            )
        return hits[nth - 1]

    def assert_absent(self, event: str) -> None:
        hits = self.frames_of(event)
        if hits:
            raise AssertionError(
                f"event={event!r} 应缺席却在场 {len(hits)} 帧"
                f"（帧行 {[f.line for f in hits]}——{self._where()}）"
            )

    def assert_data(self, event: str, subset: Mapping[str, Any], *, nth: int = 1) -> LegFrame:
        """event 第 n 帧 data ⊇ subset（递归子集/list 全等/标量相等）；返回该帧。"""
        frame = self.assert_has(event, nth=nth)
        miss = _subset_mismatch(frame.data, subset, "data")
        if miss:
            raise AssertionError(
                f"event={event!r} 第 {nth} 帧（行 {frame.line}）data 子集断言失配：{miss}\n"
                f"  期望子集: {dict(subset)!r}\n  实际 data: {dict(frame.data)!r}"
            )
        return frame

    def _where(self) -> str:
        return f"来源 {self._path}" if self._path else "合成流"


def _subset_mismatch(actual: Any, expected: Any, path: str) -> str | None:
    """子集比对：dict 递归子集；list/tuple 全等（序敏感）；标量相等。失配返描述，过返 None。"""
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            return f"{path}: 期望 mapping，实为 {type(actual).__name__}"
        for key, want in expected.items():
            if key not in actual:
                return f"{path}.{key}: 子集键缺失"
            miss = _subset_mismatch(actual[key], want, f"{path}.{key}")
            if miss:
                return miss
        return None
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or list(actual) != list(expected):
            return f"{path}: 期望序列全等 {expected!r}，实为 {actual!r}"
        return None
    if actual != expected:
        return f"{path}: 期望 {expected!r}，实为 {actual!r}"
    return None

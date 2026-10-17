"""understanding 的错误族：解析不合格的错误形状（`UnderstandingParseError`）＋片段截断单点。

真源＝`specs/understanding.md` 接口定义「错误契约」行＋行为 7／13：应答不是合法 JSON／缺必填
字段／字段类型不符／`route` 越界 → 先**回喂拒因重试恰一次**；仍不合 ⇒ **收敛拒答**（2026-10-17
EB3 D4.4 改判：`direct_answer` 落拒答正文，run 收口、**不判 `failed`、不零交付**——旧形「抛
`UnderstandingParseError` → 编排收 `failed`」退役，真机证据 `eval/results/frames/EB2-NQ-D2.json`）。

**本类型自 2026-10-17 EB3 D4.4 起退出本块出口**（保留作错误族形状与消费面兼容——`excerpt` 片段面
仍由「如实上报」两件套消费，两处同源）。**合法降级路径＝无**：本块无「抽第一个 `{...}`」「冒号
回退」「两行式」一类降级提取（旧形随 `specs/parsing.md` 行为 1 退场）；收敛拒答＝确定性拒答正文，
不是降级提取、不猜不补默认（`specs/understanding.md` 行为 13 尾）。
"""

from __future__ import annotations

from appv2.runtimev2.understanding.constants import RAW_EXCERPT_LIMIT, TRUNCATION_MARK


def excerpt(raw: str) -> str:
    """原始应答片段（≤ 上限；超长截断**可见**——截断标记计入上限，不静默硬切）。

    单点：`UnderstandingParseError` 的片段面与「如实上报」notice／step payload 的片段面**同源**
    （两处不各自截一份）。
    """
    if len(raw) <= RAW_EXCERPT_LIMIT:
        return raw
    return raw[: RAW_EXCERPT_LIMIT - len(TRUNCATION_MARK)] + TRUNCATION_MARK


class UnderstandingParseError(ValueError):
    """读题应答不合 schema（缺必填字段／类型不符／`route` 越界／非合法 JSON）——fail-closed。

    携带三面供留痕：`reason`（不合项一句如实描述）、`excerpt`（原始应答片段，超长截断可见）、
    `raw`（原始应答全量——「原始应答片段供留痕」的完整面，片段面是 `excerpt`）。
    """

    def __init__(self, reason: str, *, raw: str) -> None:
        snippet = excerpt(raw)
        super().__init__(f"{reason}（原始应答片段：{snippet}）")
        self.reason = reason
        self.excerpt = snippet
        self.raw = raw


__all__ = ["UnderstandingParseError", "excerpt"]

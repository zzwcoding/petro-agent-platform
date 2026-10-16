"""understanding 的错误族：解析不合格的唯一转译出口（`UnderstandingParseError`）。

真源＝`specs/understanding.md` 接口定义「错误契约」行＋行为 7（解析严格）：「应答不是合法
JSON／缺必填字段／字段类型不符 → 抛 `UnderstandingParseError`（携带原始应答片段供留痕）。
**不返回半成品**」；`route` 越界（闭世界仅 `full`｜`direct`）同判失败（不猜、不取默认）。
parsing 解析不合格（`parse_understanding` 返 `None`）在场时由本块**转译**抛同类错——唯一转译
出口（真源 `specs/parsing.md` 行为 1／接口⑤：本块不抛业务异常、不合格走三态返回）。

**合法降级路径＝无**：本块无「抽第一个 `{...}`」「冒号回退」「两行式」一类降级提取（旧形随
`specs/parsing.md` 行为 1 退场）——不合格恒以本异常收口，不静默、不半成品。
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

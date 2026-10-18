"""appv2.text_tokens —— 题眼 token 边界/全等判据单点真源（V2-100 D-a）。

**依赖自由模块**：零 `appv2` 依赖、零 I/O、零状态、纯字符扫描（禁 `re`）——L1
（`appv2.retrieval`）与 L3（`appv2.runtimev2.context`）**双方直引本模块**，消除第二份
边界/全等判定（V2-90 钉死的 `W-11≠W-111`／`22≠2200` 语义单点化；`appv2/tools/__init__`
→`handlers`→`retrieval` 成环，故判据不许落 `appv2.tools.*`）。新增 import-linter 契约
（`tools/importlinter_v2.toml`「V2-100 D-a」）**禁本模块反向 import** `appv2` 任何块
——防其长成第二个 tools。

只下沉两个**纯判据**（判据本体下沉自 `appv2/runtimev2/context/materials.py:227`／`:248`，
同源同文）；分层锚分（`_anchor_score`／`_anchor_hit_count`）**留 L3**，不属本模块。

签名序＝`tickets/v2/V2-100-题眼表节行集确定性占席.md` §施工基准逐字稿（`text` 在前、
判据串在后）。形态处理豁免面＝`specs/context.md` 行为 13（字符串包含／边界／全等，零语义）。
"""

from __future__ import annotations

# 数字 token 全等的边界字符集（前后紧邻任一字符即非全等——V2-90 锚分边界化）。
_ASCII_DIGITS = "0123456789"
_ASCII_LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_NUMERIC_BOUNDARY_CHARS = _ASCII_DIGITS + ".,"
# 井号／油田等强锚的边界字符集（前后紧邻字母／数字／连字符即非边界——`W-11` 与 `W-111` 可辨）。
_SUBJECT_BOUNDARY_CHARS = _ASCII_LETTERS + _ASCII_DIGITS + "-"


def num_token_hit(text: str, token: str) -> bool:
    """数字 token **全等**命中（V2-90——`22` 不得命中 `2200`／`202608`；`12.5` 命中 `12.5`）。

    纯字符扫描（禁 `re`）：token 在 text 中的每次出现，前后字符都不得是数字或 `.`／`,`；任一
    出现满足全等即命中。故 `12.5` 命中 `12.5 MPa`、不命中 `112.5`／`12.55`（落在更长数字串内）。
    """
    if not token or not text:
        return False
    start = 0
    while True:
        found = text.find(token, start)
        if found < 0:
            return False
        end = found + len(token)
        before_ok = found == 0 or text[found - 1] not in _NUMERIC_BOUNDARY_CHARS
        after_ok = end == len(text) or text[end] not in _NUMERIC_BOUNDARY_CHARS
        if before_ok and after_ok:
            return True
        start = found + 1


def boundary_hit(text: str, needle: str) -> bool:
    """强锚（井号／油田／区块／平台名）**边界**命中（V2-90——`W-11` 不得命中 `W-111`）。

    纯字符扫描（禁 `re`）：needle 在 text 中的每次出现，前后字符都不得是字母／数字／连字符；
    任一出现满足边界即命中。中文等非 ASCII 字母数字字符不作边界字符（`W-11井位于` 仍命中）。
    """
    if not needle or not text:
        return False
    start = 0
    while True:
        found = text.find(needle, start)
        if found < 0:
            return False
        end = found + len(needle)
        before_ok = found == 0 or text[found - 1] not in _SUBJECT_BOUNDARY_CHARS
        after_ok = end == len(text) or text[end] not in _SUBJECT_BOUNDARY_CHARS
        if before_ok and after_ok:
            return True
        start = found + 1

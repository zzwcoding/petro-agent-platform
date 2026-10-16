"""发射通道确定性剥离（`strip_emission_fences`）——钉 `pin-04`（P0）的行为单点。

真源＝`specs/answering.md` 行为 11（模型应答在进答案面——`AnswerDraft` 片段与其 `text` 帧增量
——之前经**发射围栏／JSON 形确定性剥离**，发射 JSON 不得进答案面，泄漏=0）＋迁移逐字稿
`docs/runtime-refactor/recon/A2-核验规则与归属审.md`（R-A2-03…R-A2-07 五条规则、
`appv2/runtime/graph.py` L697-L736 的承载位形）＋旧码真源 `docs/runtime-refactor/recon/
L2b-作答装配与回声.md`（:58 `strip_emission_fences`／:101 剥离后草稿才进答案装配）。

剥离四条（逐字迁移、语义零漂移）：

1. **围栏块**：三反引号围栏体的 `strip()` 整体可解为 JSON 对象／数组（或前缀噪声形——首个 `{`
   到末个 `}` 的中段可解）→ **整块剥除**（发射形与否都剥：答案面零裸 JSON 段，R-A2-03）；
   纯散文围栏零误伤原样保留；
2. **裸发射行**：行内含裸发射 JSON 令牌（`{"action": "<值>"…}` 且值 ∈ 发射动作闭世界）→
   **整行剥除**（回声行余文＝提示原文，同属泄漏承载——一并离场，R-A2-04）；
3. **裸 JSON 行**：`strip()` 后以 `{`／`[` 开头且整行可解为 JSON 对象／数组 → **剥除**（R-A2-05）；
4. **域外 JSON 零误伤**：动作值在闭世界外、且整行非纯 JSON 的行**原样保留**（R-A2-06）。

返回（剥离后文本, 是否检出 JSON 通道残留）——**纯格式隔离零语义判定**：不计数、不进改写统计
（协议残片非断言）。本函数是 runtimev2 面内的**唯一定义点**（消费方零第二套副本——
`specs/parsing.md` :24 的答案面归属注）。

**实现面差异声明（不引 `re`）**：判据以纯字符串扫描实现（等价于 V1 的三条正则字面
`_FENCE_RE`／`_EMISSION_TOKEN_RE`／`_parses_as_json`），以守本块的「程序侧无词表／正则语义判断」
红线（形处理面零正则）；**差异仅两处边角**：① 围栏起始行后无换行的退化形（单行围栏）不作围栏
剥除——该行若真携发射令牌仍由规则 2／3 咬住（登记见票面回报）；② V1 的 `re.splitlines` 行分割
与 `"\n"` 重连的换行归一（recon/A2 D-A2-04）随实现面逐字保留。
"""

from __future__ import annotations

import json

from appv2.runtimev2.answering.constants import EMISSION_ACTIONS

_FENCE = "```"
_ACTION_KEY = '"action"'


def _parses_as_json(text: str) -> bool:
    """文本是否可解析为 JSON 对象／数组（JSON 标量不作数——R-A2-01）。"""
    try:
        payload = json.loads(text)
    except ValueError:
        return False
    return isinstance(payload, (dict, list))


def _fence_is_json(body: str) -> bool:
    """围栏体是否 JSON 段（整段可解／前缀噪声形首个 `{` 到末个 `}` 可解——R-A2-02）。"""
    candidate = body.strip()
    if _parses_as_json(candidate):
        return True
    start = candidate.find("{")
    end = candidate.rfind("}")
    return start != -1 and end > start and _parses_as_json(candidate[start : end + 1])


def _line_has_emission_token(line: str) -> bool:
    """行内是否含裸发射 JSON 令牌（`{"action": "<值>"…}`，值 ∈ 发射动作闭世界——R-A2-04）。

    判据逐字对齐 V1 `_EMISSION_TOKEN_RE`：`{` 与 `"action"` 之间只许空白、`:` 两侧只许空白、
    值以双引号闭合、值后到最近 `}` 之间**禁花括号**（嵌套花括号形不咬——V1 同款窄口径，
    recon/A2 D-A2-05 如实登记）。
    """
    cursor = 0
    while True:
        found = line.find(_ACTION_KEY, cursor)
        if found < 0:
            return False
        cursor = found + len(_ACTION_KEY)
        brace = line.rfind("{", 0, found)
        if brace < 0 or line[brace + 1 : found].strip():
            continue
        colon = line.find(":", cursor)
        if colon < 0 or line[cursor:colon].strip():
            continue
        open_quote = line.find('"', colon + 1)
        if open_quote < 0 or line[colon + 1 : open_quote].strip():
            continue
        close_quote = line.find('"', open_quote + 1)
        if close_quote < 0:
            continue
        if line[open_quote + 1 : close_quote] not in EMISSION_ACTIONS:
            continue
        tail = line[close_quote + 1 :]
        end = tail.find("}")
        if end < 0 or "{" in tail[:end]:
            continue
        return True


def _line_is_bare_json(line: str) -> bool:
    """整行是否即 JSON 对象／数组（无围栏裸 JSON 行——R-A2-05）。"""
    stripped = line.strip()
    if not stripped.startswith(("{", "[")):
        return False
    return _parses_as_json(stripped)


def _strip_json_fences(text: str) -> tuple[str, bool]:
    """围栏块剥除（规则 1）：JSON 段整块剥、纯散文围栏原样保留（非贪心、逐块推进）。"""
    out: list[str] = []
    leaked = False
    cursor = 0
    while True:
        start = text.find(_FENCE, cursor)
        if start < 0:
            out.append(text[cursor:])
            return "".join(out), leaked
        line_end = text.find("\n", start + len(_FENCE))
        close = text.find(_FENCE, start + len(_FENCE))
        if line_end < 0:
            line_end = len(text)
        if close < line_end:  # 起始行内即闭合（单行围栏退化形）——不剥、交行级规则咬
            out.append(text[cursor : close + len(_FENCE)])
            cursor = close + len(_FENCE)
            continue
        if close < 0:  # 无闭合围栏——整段原样离场
            out.append(text[cursor:])
            return "".join(out), leaked
        body = text[line_end + 1 : close]
        if _fence_is_json(body):
            leaked = True
            out.append(text[cursor:start])
        else:
            out.append(text[cursor : close + len(_FENCE)])
        cursor = close + len(_FENCE)


def strip_emission_fences(text: str) -> tuple[str, bool]:
    """确定性剥离答案文本中的 JSON 通道残留，返回（剥后文本, 是否检出）——见模块注四条。"""
    stripped, leaked = _strip_json_fences(text)
    kept: list[str] = []
    for line in stripped.splitlines():
        if _line_has_emission_token(line) or _line_is_bare_json(line):
            leaked = True
            continue
        kept.append(line)
    return "\n".join(kept), leaked

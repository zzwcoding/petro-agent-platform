"""共用件族四件（两发射面共用单点——真源 `specs/parsing.md` 接口定义节 ②）。

- `extract_plan_json`：首个花括号平衡块提取单点（真源 `appv2/runtime/subtask.py` L61-L79
  逐字迁移）；
- `json_syntax_feedback`：拒因带定位拼装（真源同文件 L82-L110 逐字迁移，V2-57）；
- `repair_inner_quotes`：确定性引号自修（真源同文件 L381-L428 逐字迁移，V2-60 ③层）；
- `parse_with_quote_repair`：受理编排单点（解析拒→自修一次→重解析→首拒因保留＋受理标志；
  形随 V1 `appv2/runtime/graph.py` L392-L408 迁移，arch/P4b A-P4b-39「单函数三调用不复制三份」）。

单点纪律（`specs/parsing.md` 框架与依赖红线「禁手写替代」）：提取件／拒因带定位件／引号自修件／
受理编排件在 runtimev2 面内**各恰一处定义**，相位块内出现同形字面副本＝判失败。

**消费面两处（2026-10-17 EB5a 改）**：澄清面（`clarification._dispatch`）与理解面
（`understanding._read_and_parse`）各经 `parse_with_quote_repair` 受理引号自修；匹配面
（`parse_tool_match`）经提取件走拒因回喂。`parse_understanding` 本体仍走统一 JSON 严格解析、
不合格直落 `None`（**本件不改解析面语义**——自修受理编排归消费方相位，V1 理解节点
`_parse_with_quote_repair` 同款；真源 `specs/parsing.md` 行为 10／
`specs/understanding.md` 行为 13）。
受理 notice（`emission_quote_repair`）由调用方发、归其事件面——本块零事件。
"""

import json
from collections.abc import Callable
from typing import Any


def extract_plan_json(content: str) -> dict[str, Any] | None:
    """JSON 子串提取单点（首个平衡 ``{...}`` 块）：两发射面共用——围栏产／散文包裹产同路。

    只读首块、首块坏即 ``None``（不续扫后续块，V1 事实面 D-L1a-01）；无左花括号／括号未平衡／
    顶层非对象 → ``None``（真源 recon/L1a R-L1a-01…R-L1a-05）。
    """
    start = content.find("{")
    if start < 0:
        return None
    depth = 0
    for position in range(start, len(content)):
        if content[position] == "{":
            depth += 1
        elif content[position] == "}":
            depth -= 1
            if depth == 0:
                try:
                    loaded = json.loads(content[start : position + 1])
                except json.JSONDecodeError:
                    return None
                return loaded if isinstance(loaded, dict) else None
    return None


def json_syntax_feedback(content: str, fallback: str) -> str:
    """V2-57 拒因带定位（错误原样回喂）：重放同款平衡块扫描取 json 异常定位＋坏点前后窗，
    拼进打回理由。零模型调用、零新依赖——信息本来就在异常里。

    三形（真源 recon/L1a R-L1a-06…R-L1a-08）：无左花括号 → 追加「漏了 JSON 外壳」提示；平衡块
    内语法坏 → 追加异常消息＋绝对坏点字符序＋坏点 ±40 字符原文＋修复指令；**括号始终不平衡
    （截断形）→ 退裸 `fallback`（零定位）**——V1 事实面，本块不自行裁量。
    """
    start = content.find("{")
    if start < 0:
        return (
            fallback
            + "——输出中没有任何以左花括号起始的 JSON 对象"
            "（检查是否漏了 JSON 外壳、只输出了围栏或解释文字）"
        )
    depth = 0
    for position in range(start, len(content)):
        ch = content[position]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                segment = content[start : position + 1]
                try:
                    json.loads(segment)
                except json.JSONDecodeError as exc:
                    bad = start + exc.pos  # 绝对位置（exc.pos 相对片段）
                    snippet = content[max(0, bad - 40) : bad + 40]
                    return (
                        f"{fallback}——JSON 语法错误：{exc.msg}（约第 {bad} 字符）。"
                        "常见原因：少写右括号或方括号、尾逗号、引号未闭合。"
                        f"你上次输出坏点附近原文：「{snippet}」"
                        "——只修正语法错误，结构与其余内容照旧，重新输出一个 JSON。"
                    )
    return fallback  # 重放意外成功（防御性——理论不可达）→ 原笼统话兜底


def repair_inner_quotes(text: str) -> str | None:
    """值内裸引号确定性修复（V2-60 ③层——族D 真病因：题干英文引号短语照抄进字符串值
    不转义，json.loads 断裂）。逐字符扫描跟踪在串／不在串态：串内遇 ``"`` 且其后（跳空白）
    非结构字符 ``,`` ``}`` ``]`` ``:`` ＝值内裸引号→换中文引号（开「闭」交替）；转义序列原样
    带过。修后 `json.loads` 成功才返回修复文本；扫描无值内引号（无病不修）或修后仍失败
    （结构伤——引号修不了括号）＝``None``，调用方走既有 V2-57 定位回喂。纯字符格式处理，
    零语义零模型（真源 recon/L1b R-L1b-22…R-L1b-28）。
    """
    out: list[str] = []
    in_string = False
    inner_open = False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if not in_string:
            if ch == '"':
                in_string = True
                inner_open = False
            out.append(ch)
            i += 1
            continue
        if ch == "\\":  # 转义序列原样带过（防误伤合法 \"）
            out.append(text[i : i + 2])
            i += 2
            continue
        if ch != '"':
            out.append(ch)
            i += 1
            continue
        j = i + 1
        while j < n and text[j] in " \t\r\n":
            j += 1
        nxt = text[j] if j < n else ""
        if nxt in ",}]:":  # 结构引号——串在此结束
            in_string = False
            inner_open = False
            out.append(ch)
        else:  # 值内裸引号——换中文引号（开「闭」交替）
            out.append("」" if inner_open else "「")
            inner_open = not inner_open
        i += 1
    repaired = "".join(out)
    if repaired == text:
        return None
    try:
        json.loads(repaired)
    except json.JSONDecodeError:
        return None
    return repaired


def parse_with_quote_repair(parse: Callable[[str], Any], content: str) -> tuple[Any, bool]:
    """V2-60 引号自修兜底受理编排（③层——零模型零语义，设计宪法「程序管格式合规」）：
    解析拒→确定性引号修复一次→重解析；修好＝(结果, True)（调用方发 `emission_quote_repair`
    notice——不占轮不回喂）；修不好＝(原拒因, False)（既有 V2-57 定位回喂零改动）。只重试一次、
    只做引号层修复（真源 recon/A1 R-A1-12／R-A1-13）。
    """
    result = parse(content)
    if not isinstance(result, str):
        return result, False
    repaired = repair_inner_quotes(content)
    if repaired is None:
        return result, False
    second = parse(repaired)
    if isinstance(second, str):
        return result, False
    return second, True


def whole_json_object(text: str) -> dict[str, Any] | None:
    """整枚 JSON 对象判定（V2-96——作答第二出口的「整应答恰一枚 JSON」判据）。

    与 `extract_plan_json` 的**子串**提取不同：本件只认**整应答**（可去整围栏壳、去两侧空白）
    恰为一个 JSON 对象——散文包裹／JSON 标量／数组一律不作数。纯字符扫描＋`json.loads`，
    零语义零模型零 IO（同族先例＝`answering.emission.extract_finalize_answer` 的三条件判定；
    本件归 parsing 侧自修族，因 R3 禁 parsing 引业务相位）。
    """
    stripped = _fence_shell_stripped(text)
    try:
        payload = json.loads(stripped)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _fence_shell_stripped(text: str) -> str:
    """整围栏壳解壳（```` ```json\\n…\\n``` ````）——非包裹形原样（两侧 `strip`）。

    只解**整体包裹**（首尾皆三反引号）：首行语言标记行离场；解壳不成即原样返回。
    """
    fence = "```"
    stripped = text.strip()
    if len(stripped) < 2 * len(fence):
        return stripped
    # 纯字符扫描（禁 `startswith`／`endswith`——parsing 面词面判方法零使用红线）。
    if stripped[: len(fence)] != fence or stripped[-len(fence) :] != fence:
        return stripped
    body = stripped[len(fence) : -len(fence)]
    line_end = body.find("\n")
    if line_end >= 0:
        body = body[line_end + 1 :]
    return body.strip()

#!/usr/bin/env python3
"""设计令牌闸 —— web/design-tokens.json × web/src/theme.js 一致性看守。

背景（refactoring-ui Workflow A 落地）：设计令牌的唯一真源是
``web/src/theme.js`` 的 ``palette``；``web/design-tokens.json`` 是它的机读副本，
供人/机查阅。两份一旦漂移，DESIGN.md 里写的对比度数字就失去意义——
本闸把漂移变成退出码 1。

三条检查：
  ① **JSON ↔ theme.js 同步**：JSON 的 primitive 层每个值必须等于 theme.js 里的同名值；
  ② **对比度达标**：JSON ``contrast.pairs`` 里每对前景/背景必须过 WCAG §5.6
     （正文 4.5:1、大字 3:1）。实测值与记录值偏差 >0.05 视为过期。
  ③ **暗色令牌落地**：theme.js 的 ``cssVars`` 必须覆盖三档文字色 + 三层表面。

用法（仓根执行；路径按脚本位置解析，与当前目录无关）：
    python3 tools/check_design_tokens.py check    # 比对（缺省动作）
    python3 tools/check_design_tokens.py update   # 由 theme.js 重生 JSON 的 primitive 层

纯标准库——CI 零依赖可跑。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKENS_PATH = REPO_ROOT / "web" / "design-tokens.json"
THEME_PATH = REPO_ROOT / "web" / "src" / "theme.js"

AA_NORMAL = 4.5
AA_LARGE = 3.0
# rgba 白字在暗底上的实际合成色（用于对比度计算）
_RGBA_BG = {
    "rgba(255, 255, 255, 0.85)": "#dcdcdc",
    "rgba(255, 255, 255, 0.65)": "#adadad",
    "rgba(255, 255, 255, 0.25)": "#4f4f4f",
}


def _hex_to_rgb(s: str) -> tuple[int, int, int]:
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"not a hex color: {s}")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(v: int) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    fg = _RGBA_BG.get(fg, fg)
    bg = _RGBA_BG.get(bg, bg)
    l1 = _relative_luminance(_hex_to_rgb(fg))
    l2 = _relative_luminance(_hex_to_rgb(bg))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def parse_theme_palette() -> dict:
    """从 theme.js 抽出 palette 的字面量值（不执行 JS——纯正则，避免引 JS 运行时）。"""
    src = THEME_PATH.read_text(encoding="utf-8")
    m = re.search(r"export const palette = \{(.*?)\n\}", src, re.S)
    if not m:
        raise SystemExit("theme.js：找不到 export const palette = {...}")
    body = m.group(1)
    out: dict[str, str] = {}
    # 逐层：surface / text / brand / sider
    for section in ("surface", "text", "brand", "sider"):
        sm = re.search(rf"{section}:\s*\{{(.*?)\n  \}}", body, re.S)
        if not sm:
            continue
        for key, val in re.findall(r"(\w+):\s*'([^']+)'", sm.group(1)):
            out[f"{section}.{key}"] = val
    # viz（数据可视化分类色）——嵌套两层：viz.typeHex.{类型} 与 viz.palette 数组。
    # 必须一并抽出来，否则这块令牌就是「闸看不见的盲区」——闸绿了却没人守。
    vm = re.search(r"\n  viz:\s*\{(.*?)\n  \},", body, re.S)
    if vm:
        vbody = vm.group(1)
        for key, val in re.findall(r"(\w+):\s*'([^']+)'", vbody):
            out[f"viz.{key}"] = val
        tm = re.search(r"typeHex:\s*\{(.*?)\}", vbody, re.S)
        if tm:
            for key, val in re.findall(r"([^:\s,{}]+):\s*'([^']+)'", tm.group(1)):
                out[f"viz.typeHex.{key}"] = val
        pm = re.search(r"palette:\s*\[(.*?)\]", vbody, re.S)
        if pm:
            for i, val in enumerate(re.findall(r"'([^']+)'", pm.group(1))):
                out[f"viz.palette.{i}"] = val
    return out


def check() -> int:
    if not TOKENS_PATH.exists():
        print("令牌闸 RED：web/design-tokens.json 不存在")
        return 1
    if not THEME_PATH.exists():
        print("令牌闸 RED：web/src/theme.js 不存在")
        return 1

    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    palette = parse_theme_palette()
    problems: list[str] = []

    # ① JSON primitive ↔ theme.js palette
    prim = tokens.get("primitive", {})
    for section, values in prim.items():
        for key, val in values.items():
            theme_val = palette.get(f"{section}.{key}")
            if theme_val is None:
                problems.append(f"theme.js 无 palette.{section}.{key}（JSON 有 {val}）")
            elif theme_val.lower() != val.lower():
                problems.append(
                    f"漂移 palette.{section}.{key}: theme.js={theme_val} / json={val}"
                )
    for key, val in palette.items():
        sec, _, name = key.partition(".")
        if sec not in prim or name not in prim.get(sec, {}):
            problems.append(f"theme.js 有 palette.{key}={val}，JSON primitive 缺")

    # ② 对比度矩阵
    for pair in tokens.get("contrast", {}).get("pairs", []):
        fg, bg = pair["fg"], pair["bg"]
        minimum = pair.get("min", AA_NORMAL)
        try:
            ratio = contrast_ratio(fg, bg)
        except ValueError as e:
            problems.append(f"对比度对无法解析: {fg} on {bg}（{e}）")
            continue
        if ratio < minimum:
            problems.append(
                f"对比度不足 {fg} on {bg}: {ratio:.2f}:1 < {minimum}:1"
            )
        recorded = pair.get("measured")
        if recorded is not None and abs(ratio - recorded) > 0.05:
            problems.append(
                f"对比度记录过期 {fg} on {bg}: 记 {recorded} / 实 {ratio:.2f}"
            )

    # ③ cssVars 覆盖三档文字色 + 三层表面
    theme_src = THEME_PATH.read_text(encoding="utf-8")
    required_vars = [
        "--pa-text-primary",
        "--pa-text-secondary",
        "--pa-text-tertiary",
        "--pa-surface-page",
        "--pa-surface-card",
        "--pa-surface-raised",
    ]
    for var in required_vars:
        if var not in theme_src:
            problems.append(f"theme.js 的 cssVars 缺 {var}")

    # ④ G6/canvas 图形属性里不得出现 CSS 变量。
    #    G6 v5 默认 canvas 渲染器：fill/stroke/labelFill/background 走 canvas 2D
    #    上下文或 SVG 属性，**CSS 变量在那里不解析**。实测踩坑：把画布底与节点
    #    文字改成 var(--pa-*) 后，画布变纯黑、节点主文字整段消失、边标签不显
    #    （页面看起来「图没了」，但代码 review 看不出问题）。
    #    故进 G6 配置的颜色一律取 theme.js palette.viz 的字面 hex。
    #
    #    判据按**槽位名**而非按行——G6 的 tooltip 插件那套 style 是 DOM
    #    （内联样式，var() 能解析），不能误报。
    for jsx in sorted((REPO_ROOT / "web" / "src" / "landing").rglob("*.jsx")):
        text = jsx.read_text(encoding="utf-8")
        idx = text.find("new Graph(")
        if idx < 0:
            continue
        end = text.find("\n    })", idx)
        block = text[idx : end if end > 0 else idx + 4000]
        for line in block.splitlines():
            stripped = line.strip()
            if "var(--pa-" not in stripped:
                continue
            m = re.match(r"(\w+):", stripped)
            if not m:
                continue  # 模板字符串里的 HTML style 属性（DOM，var() 可用）→ 不判
            key = m.group(1)
            indent = len(line) - len(line.lstrip())
            # 图形属性槽位：*Fill / stroke / haloStroke，以及 Graph 根层的 background
            is_graphic = (
                key.endswith("Fill")
                or key in ("stroke", "haloStroke")
                or (key == "background" and indent == 6)
            )
            if is_graphic:
                problems.append(
                    f"G6 图形属性里出现 CSS 变量（canvas/SVG 属性不解析 var()）："
                    f"{jsx.relative_to(REPO_ROOT)}  {stripped[:60]}"
                )

    if problems:
        print(f"令牌闸 RED：{len(problems)} 条问题")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(
        f"令牌闸 GREEN：{len(prim)} 组 primitive 与 theme.js 同步，"
        f"{len(tokens.get('contrast', {}).get('pairs', []))} 对对比度全达标，"
        f"G6 配置无 CSS 变量"
    )
    return 0


def update() -> int:
    """由 theme.js 重生 JSON 的 primitive 层（语义层/刻度/对比度矩阵人工维护）。"""
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    palette = parse_theme_palette()
    # 整层重生而非只刷新既有键——theme.js 新增的键（如 sider.groupTitle）
    # 必须能进 JSON，否则「JSON 与 theme.js 同步」这条检查会永远红。
    order = ["surface", "text", "brand", "sider"]
    grouped: dict[str, dict[str, str]] = {k: {} for k in order}
    for key, val in palette.items():
        sec, _, name = key.partition(".")
        grouped.setdefault(sec, {})[name] = val
    tokens["primitive"] = {k: v for k, v in grouped.items() if v}
    tokens["note"] = (
        "前端设计令牌（refactoring-ui Workflow A 产出）。真源＝web/src/theme.js 的 palette；"
        "本文件是机读副本，供 tools/check_design_tokens.py 闸比对，勿手改——"
        "改 theme.js 后跑 `python3 tools/check_design_tokens.py --update` 重生。"
    )
    TOKENS_PATH.write_text(
        json.dumps(tokens, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已重生 {TOKENS_PATH.relative_to(REPO_ROOT)} 的 primitive 层")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="设计令牌一致性闸")
    ap.add_argument("action", nargs="?", default="check", choices=["check", "update"])
    args = ap.parse_args()
    return check() if args.action == "check" else update()


if __name__ == "__main__":
    sys.exit(main())

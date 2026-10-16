"""超窗 compaction＝模型视图压缩（行为 9——`pin-30` 的 compaction 半面／`pin-22` 视图面）。

真源：`specs/context.md` 接口定义节 `compact_messages` 签名＋行为 9；摘要形逐字稿载体＝
`tickets/v2/V2-79d-compaction摘要化.md` §1.1／§1.2（摘要头＋「问：／答：」行、截数 120——
真源 `docs/runtime-refactor/arch/P5b3-票堆V2-79c至79d.md` A-P5b3-13／A-P5b3-15／A-P5b3-17）。

**触发参数注入制、无裸值**：`dialogue_view_tokens` 承载位＝`RunState` 独立字段
（流水 46①／49②），数值单点＝`DEFAULT_DIALOGUE_VIEW_TOKENS`（已裁 8k 档——流水 43④，
真源 `docs/runtime-refactor/arch/P6a-票堆V2-80系列前半.md` A-P6a-11）。

**识别面（结构化、非内容子串）**：`messages` 条目的标记键＝`origin`（流水 49③——与
`dialogue` 条目同词表）——`origin` 落在来源闭世界 `DIALOGUE_ORIGINS` 内者＝可压缩的对话轮；
其余条目（合同／相位包／角色红线／指令等，标记随条目字段携带）**永不摘除**，原地保留
（fail-safe：未标记者一律不摘）。**参形（链位贡献表随调用传入那一支）随风险 4 落点裁定后
入签名——登记**；本块不采内容子串识别。

**只作用于模型视图**：`state.messages` 零覆盖（只压不删、原史全量在 checkpoint 可查，
`pin-22`）；压缩唯一调用点＝调用方（编排面）——本块只产视图与披露账目串，账目由调用方
在合成最终 `Manifest` 时**追加于材料面 `selected_reason` 之后（分隔「；」）**。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from appv2.runtimev2.state import DIALOGUE_ORIGINS

# 对话层视窗 token 预算单点（流水 43④ 已裁 8k 档——注入制、无裸值；披露文案随注入值走）。
DEFAULT_DIALOGUE_VIEW_TOKENS = 8192

# 摘要行单行上限（问原文／答首行截数——真源 A-P5b3-13）。
_SUMMARY_HEAD_CAP = 120
# 摘要头逐字（真源 A-P5b3-15——迁移照抄）。
_SUMMARY_HEAD = "（前情摘要——旧轮原文已压缩，完整原史在会话档案可查）"


def _estimate_tokens(text: str) -> int:
    """视窗 token 估算（chars/4——与网关记账兜底同口径，确定性无模型）。"""
    return len(text) // 4


def _head_line(text: str, cap: int = _SUMMARY_HEAD_CAP) -> str:
    """摘要行取材（首行＋单行上限截断——规则抽取的确定性取材单点）。"""
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    return first_line[:cap]


def _is_dialogue_turn(entry: Mapping[str, str]) -> bool:
    """对话轮判定（`origin` ∈ 来源闭世界——结构化、零内容子串）。"""
    return str(entry.get("origin", "")) in DIALOGUE_ORIGINS


def compact_messages(
    messages: Sequence[Mapping[str, str]], *,
    dialogue_view_tokens: int
) -> tuple[list[dict[str, str]], str]:
    """整链 messages→（模型视图，压缩披露账目串）——行为 9。

    总量（全链 chars/4 估值）入预算 ⇒ 原样返回、披露为空（零漂移）；超窗 ⇒ 自尾向前累积
    保留窗（**保留窗三条保证**：自尾向前累积、**至少 1 轮——最新轮恒在场，哪怕单轮超预算**、
    **单轮独占预算＝原样放行零压缩**）；窗前最旧对话轮逐轮摘要化（`user`→「问：{原文截 120}」／
    其余→「答：{首行截 120}」），摘要＝`system` 消息置于角色红线 `system` 之后、近期轮之前；
    合同／相位包等非对话条目全数原地保留。返回账目串由调用方以「；」追加于材料面
    `selected_reason` 之后（本块不写 `selected_reason`、不改原史）。
    形态越界（`dialogue_view_tokens` 非正整数）→ 抛参数错误，不吞错（规格「错误契约」）。
    """
    if isinstance(dialogue_view_tokens, bool) or not isinstance(dialogue_view_tokens, int):
        raise ValueError(
            f"形态越界：dialogue_view_tokens 须为正整数（实为 {dialogue_view_tokens!r}）"
        )
    if dialogue_view_tokens < 1:
        raise ValueError(
            f"形态越界：dialogue_view_tokens 须为正整数（实为 {dialogue_view_tokens}）"
        )
    view = [dict(entry) for entry in messages]
    total_tokens = sum(_estimate_tokens(str(entry.get("content", ""))) for entry in view)
    if total_tokens <= dialogue_view_tokens:
        return view, ""
    # 保留窗：自尾向前累积（非对话条目不入窗、也不摘除）。
    kept: list[int] = []
    total = 0
    for index in range(len(view) - 1, -1, -1):
        if not _is_dialogue_turn(view[index]):
            continue
        cost = _estimate_tokens(str(view[index].get("content", "")))
        if kept and total + cost > dialogue_view_tokens:
            break
        kept.append(index)
        total += cost
    window = set(kept)
    compressed = [
        index for index, entry in enumerate(view)
        if _is_dialogue_turn(entry) and index not in window
    ]
    turns = sum(1 for entry in view if _is_dialogue_turn(entry))
    if not compressed:  # 单巨轮独占预算／无旧轮可压——原样放行（零压缩零漂移，不静默丢锚）
        return view, ""
    summary = "\n".join(
        [_SUMMARY_HEAD]
        + [
            (
                f"问：{_head_line(str(view[index].get('content', '')))}"
                if str(view[index].get("role", "user")) == "user"
                else f"答：{_head_line(str(view[index].get('content', '')))}"
            )
            for index in compressed
        ]
    )
    dropped = set(compressed)
    reduced = [entry for index, entry in enumerate(view) if index not in dropped]
    # 摘要置位：角色红线 system 之后、近期轮之前（链首为 system 条目时插于其后）。
    insert_at = 1 if reduced and reduced[0].get("role") == "system" else 0
    reduced.insert(insert_at, {"role": "system", "content": summary})
    account = (
        f"对话层 compaction：{turns} 轮→保留 {len(kept)} 轮＋前情摘要"
        f"（预算 {dialogue_view_tokens}，原史在会话档案全量可查）"
    )
    return reduced, account

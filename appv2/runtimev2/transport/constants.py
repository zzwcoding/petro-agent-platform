"""transport 的五个闭世界常量族（取值真源逐族标注——见各族注记）。

真源＝`specs/transport.md` 接口定义节「闭世界常量族」段（签名以 `specs/modules.md`
`## transport` 卡为准）。本模块只落取值、不落行为：同一族在别处再建第二份＝缺陷
（「闭世界只有一个常量族」——`specs/transport.md` 风险 2 的对策；文案随集合生成，不写死条数）。
"""

# ── runtime 九类事件名（取值真源 `synth/S6-事件与帧目录.md` §一；九类口径真源
# `synth/S3-口径裁决清单.md` C-05——「八类」为 `EVENT_BLACKBOX` 入列前的陈旧注记）──
# `blackbox` **必须与其他八类同列导出面**（现状 `appv2/runtime/__init__.py` 缺该符号＝
# S3 C-10／D-P9a1-09；本块收正）。
EVENT_KINDS: frozenset[str] = frozenset(
    {"step", "text", "tool", "observation", "ask", "verdict", "citation", "notice", "blackbox"}
)

# ── wire 三帧（取值真源 `synth/S6-事件与帧目录.md` §二；发射时机与载荷归 `api` 开流段，
# 本块只保帧名在闭世界内与信封形状）────────────────────────────────────────────
WIRE_FRAMES: frozenset[str] = frozenset({"session", "done", "error"})

# ── 事件名的十二值全集（＝`EVENT_KINDS ∪ WIRE_FRAMES`，行为 1 的构造期判据面）──────
_FRAME_EVENTS: frozenset[str] = EVENT_KINDS | WIRE_FRAMES

# ── 通知类型二十九值（取值真源＝本规格自立·实测全集——`specs/transport.md` 接口定义节
# 逐字列全；2026-10-16 补全（流水 53-C）：B5 golden 回放 54444 帧实测越界 7 值入列）──────
# 行为 7：`notice` 载荷恰三键 `{type, gates, content}`；取值越界即拒；**取消隐式兜底**
# （旧码 `locator.notice_type` 缺省填 `"notice"`）——**缺 `type` 即拒**，不猜不填；
# **新增类型必须同批入列**（禁「白名单外偷偷发」）。
NOTICE_TYPES: frozenset[str] = frozenset(
    {
        "refused",
        "run_failed",
        "ban_exempt",
        "budget_converged",
        "clarify_capped",
        "emission_strip",
        "emission_quote_repair",
        "material_truncated",
        "unsupported_claim",
        "contradiction_split",
        "attribution_split",
        "decision_note",
        "decision_rejected",
        "chain_switch_reentry",
        "window_miss_reentry",
        "approval_gate_pending",
        "approval_recorded",
        "tool_unavailable",
        "subtask_failed",
        "subtask_refused",
        "audit_write_failed",
        "blackbox_write_failed",
        # 2026-10-16 补全（流水 53-C）：B5 回放实测越界 7 值（来源＝V1 tools/query/gate 通道）
        "window_note",
        "no_hit",
        "unbound_degrade",
        "freshness_block",
        "same_param_replay",
        "rebind",
        "schema_not_allowed",
    }
)

# ── verdict 两形（行为 6：载荷含 `status` 键 → `final`，否则 → `verify`；二值闭世界）──
_VERDICT_VERIFY = "verify"
_VERDICT_FINAL = "final"

VERDICT_SUBTYPES: frozenset[str] = frozenset({_VERDICT_VERIFY, _VERDICT_FINAL})

# ── ask 帧 kind 二值（行为 8；`AskReason.kind` → 本闭世界的映射表在
# `specs/preconditions.md` 接口定义）─────────────────────────────────────────
ASK_FRAME_KINDS: frozenset[str] = frozenset({"clarify", "external_table_approval"})

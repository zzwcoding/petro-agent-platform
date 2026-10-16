"""gate 的闭世界常量族（三族词表＋三条话术＋步标题映射——逐字迁移）。

迁移源＝`appv2/runtime/graph.py` L1360-L1387（词表与话术）／L1452／L1458／L1466（步标题三形）；
逐字稿载体＝`tickets/v2/V2-66-注入拦截闸.md`／`tickets/v2/V2-67-外发写意图闸.md`——
**承载位换、文本不变**（`specs/gate.md` 行为 6／行为 8，差异点表外零偏离）。

- 三族清单＋三条话术为闭世界常量（行为 10）：**只扩不删**（扩容随红队用例回流、须同批改规格）；
  runtimev2 面内各恰一处定义、消费方零副本（禁手写替代——V1 病灶＝注入词表双份并存、可各自演化
  且无防漂移断言，`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` D-B2-11）。
- 匹配方式三族不齐＝V1 事实面（行为 5，仅作证据）：注入折叠（casefold）、外发／写意图纯子串不折叠；
  统一折叠＝规格变更。
"""

# ── 注入族五条模式（真源 graph.py L1360-L1362；V1 自 app/domains/chat/domain.py
#    INJECTION_PATTERNS 逐字移植——promptfoo 红队用例同源）／匹配按 casefold 折叠 ──────
INJECTION_PATTERNS: tuple[str, ...] = (
    "忽略之前", "忽略你之前的", "无视之前", "ignore previous", "ignore all previous",
)
INJECTION_ANSWER_TEMPLATE = (
    "我注意到这句话包含「{feature}」——这类要求不会被执行，"
    "平台规则不可能被对话内容覆盖。"
)                                        # {feature}＝命中模式词原文（槽）
# 外发族（真源 graph.py L1369-L1378）——动词＋通道同句共现才命中（降误伤：单一词面会拦
# 「邮箱格式是什么」这类无辜问句）：
OUTBOUND_VERBS: tuple[str, ...] = (
    "发到", "发送到", "发送给", "发给", "推送到", "传到", "外传",
)
OUTBOUND_CHANNELS: tuple[str, ...] = (
    "邮箱", "邮件", "微信", "短信", "手机", "钉钉", "飞书", "外部系统",
)
OUTBOUND_ANSWER = (
    "本系统只读——未配置外发通道，数据不能发往邮箱、微信等外部渠道；"
    "可在本对话内查看，明细类结果可按行导出文本。"
)                                        # 固定话术（无槽）
# 写意图族（真源 graph.py L1380-L1387）——写动词＋写对象同句共现才命中：
WRITE_VERBS: tuple[str, ...] = (
    "下调", "上调", "调到", "调成", "改成", "改为", "写入", "删除", "停用", "启用",
)
WRITE_TARGETS: tuple[str, ...] = ("配注", "配产", "计划产量", "指标", "台账", "数据")
WRITE_ANSWER_TEMPLATE = (
    "本系统只读——不做任何写入或调整，「{target}」等生产参数不在本平台变更；"
    "如需变更请走线下变更流程。"
)                                        # {target}＝命中写对象词原文（槽）

# ── STEP_TITLES：family→标题映射闭世界（迁移照抄，与话术同批锁定；真源 graph.py
#    L1452／L1458／L1466）——「N0」为迁移字面，编号体系本身不入 V2；改名＝规格变更 ────
STEP_TITLES: dict[str, str] = {
    "injection": "N0 注入拦截硬终止",
    "outbound": "N0 外发拦截硬终止",
    "write": "N0 写意图拦截硬终止",
}

# 三族闭世界（`Refusal.family` 取值域；`specs/gate.md` 行为 1／行为 11）——从 `STEP_TITLES`
# 键集派生（三族名各恰一处定义，防两处清单漂移）；私有：族名单闭世界，公开面只列规程成员。
_FAMILIES: frozenset[str] = frozenset(STEP_TITLES)

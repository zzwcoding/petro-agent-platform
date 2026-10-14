"""V2-58 理解步信息面治理——装配器、渲染器与本体摘要缝测试（票面附 D T1–T7）。

设计宪法（Owner 拍板）：语义归模型，程序管装配与格式合规——本文件只测装配的
结构合规（段落序/词面/枚举在场），不测「复述是否正确」（那是语义面，无闸）。
"""

from __future__ import annotations

from datetime import date

from appv2.api.ontology_guide import load_object_digests
from appv2.runtime.orientation import (
    assemble_understand_turn,
    build_understand_instruction,
    iso_day,
    render_metric_lines,
    render_relation_lines,
    render_term_lines,
    thin_object_lines,
)


def _metric(slot: str, unit: str, bound: bool) -> dict:
    binding = "bound" if bound else "unbound"
    return {
        "slot": slot,
        "binding_state": binding,
        "value": f"{slot}：定义｜粒度 日 · 单位 {unit}｜状态 生效中（绑定态：{binding}）",
    }


# ---------- T2 指标渲染（Owner 定稿措辞） ----------


def test_metric_lines_wording() -> None:
    lines = render_metric_lines([
        _metric("日产油量", "吨", True),
        _metric("检泵周期", "天", False),
    ])
    assert lines[0] == "日产油量｜吨｜可出数"
    assert lines[1] == "检泵周期｜天｜未绑定（台账无数值——数值走报告检索）"


# ---------- T3 术语渲染三形（禁用词／映射／纯定义） ----------


def test_term_lines_three_forms() -> None:
    lines = render_term_lines([
        {"term": "老完成率", "banned": True,
         "value": "老完成率（禁用词 · 禁用（替代：产量完成率））：v1 口径，2024 年废弃"
                  "（时效：—（已禁用））"},
        {"term": "躺井", "banned": False,
         "value": "躺井（黑话 → 停产待检泵 · 有效（限作业区语境））：作业区口语"
                  "（时效：2026-12-31）"},
        {"term": "存水率", "banned": False,
         "value": "存水率（术语 · 有效）：注入水留存地层比例（物质平衡用）（时效：长期）"},
    ])
    assert lines[0] == "老完成率＝禁用词！正确名「产量完成率」（v1 口径，2024 年废弃）"
    assert lines[1] == "躺井＝停产待检泵"
    assert lines[2] == "存水率＝注入水留存地层比例（物质平衡用）"


# ---------- T4 对象摘要（真 m1 本体文件——枚举在场＋生命周期去重） ----------


def test_object_digests_real_m1() -> None:
    lines = load_object_digests()
    assert lines, "本体对象摘要不得为空（m1-object-model.yaml 装载面）"
    well = next(line for line in lines if line.startswith("井："))
    assert "井别（EW／IW）" in well
    # 生命周期值集与「当前状态」属性枚举相同——不重复渲染「状态机（…）」段。
    assert "状态机（生产中" not in well
    daily = next(line for line in lines if line.startswith("日产计量："))
    assert "报表班次（A／B／C）" in daily


def test_thin_object_lines_fallback() -> None:  # T7 回退形
    lines = thin_object_lines([
        {"obj": "井", "value": "井（草案）：井号 / 井别 / 投产日 / 状态机"},
        {"obj": "区块", "value": "区块（草案）：§5 未列属性"},
    ])
    assert lines == ["井：井号 / 井别 / 投产日 / 状态机", "区块"]


# ---------- T5 关系渲染（链路＋人话注解） ----------


def test_relation_lines_chain_and_gloss() -> None:
    lines = render_relation_lines([
        {"rel": "井—隶属→油田", "value": "井 —隶属→ 油田——井属于哪个油田"},
    ])
    assert lines == ["井—隶属→油田（井属于哪个油田）"]


# ---------- V2-80a 路由原则化钉（能力块＋清单降级句） ----------


def test_v2_80a_capability_block_and_list_demotion() -> None:
    """【本系统】能力块在环境块首条（相关性判断的成文依据），且明文把名录/术语/
    本体清单降级为取数依据——防清单变成相关性门槛（判断面收窄的回归钉）。"""
    text = assemble_understand_turn(
        question="数据库里都有什么油田？",
        families=["monthly"],
        watermark="2026-08-31",
        metric_lines=render_metric_lines([_metric("日产油量", "吨", True)]),
        term_lines=[],
        object_lines=["井：井号·井别（EW／IW）"],
        relation_lines=[],
    )
    assert "【本系统】（事实描述——业务相关性的判断依据）" in text
    assert "本系统是油田生产与管理数据的问答系统" in text
    # 清单降级句在册（名录/术语/本体＝取数依据，相关性只看领域沾边）。
    assert "它们是后续环节取数的依据" in text
    assert "你判断相关性只看领域是否沾边" in text
    # 能力块在环境块首条（资料库族行之前）。
    assert text.index("【本系统】") < text.index("资料库族")
    # 数据止于水位日的边界陈述在场。
    assert "数据止于下方水位日" in text


# ---------- T1 装配序与尾部（题干紧邻生成点） ----------


def test_assemble_order_and_tail() -> None:
    text = assemble_understand_turn(
        question="上月躺井的那几口井，日产油和时率怎么样？",
        families=["completion", "monthly"],
        watermark="2026-08-31",
        metric_lines=render_metric_lines([_metric("日产油量", "吨", True)]),
        term_lines=render_term_lines([
            {"term": "躺井", "banned": False,
             "value": "躺井（黑话 → 停产待检泵 · 有效）：作业区口语"},
        ]),
        object_lines=["井：井号·井别（EW／IW）"],
        relation_lines=render_relation_lines([
            {"rel": "", "value": "井 —隶属→ 油田——井属于油田"},
        ]),
    )
    assert text.startswith("【场景】")
    assert (
        text.index("【你的输出与它的消费方式】")
        < text.index("【样例】")
        < text.index("【环境】")
        < text.index("【红线】")
        < text.index("【待解构的题干】")
    )
    assert "日产油量｜吨｜可出数" in text
    assert "躺井＝停产待检泵" in text
    assert "数据水位：2026-08-31" in text
    assert "上月躺井的那几口井" in text
    assert text.rstrip().endswith(
        "（先判与业务的相关性：可能有关＝两行式；确定无关的寒暄闲聊＝直答。现在输出。）"
    )
    # V2-80a 路由原则化条款在任务书内（可能有关＝两行式／确定无关＝直答——零禁令零例子）。
    assert "唯一例外（纯寒暄直答）" in text
    assert "你的判断只有一个" in text and "可能" in text
    assert "确定与业务毫无关系" in text
    assert "以油田数据问答助手的身份" in text
    # 原禁令式措辞退役（V2-80a——禁止式白名单拆除）。
    assert "一律不用" not in text
    assert "不含任何查询" not in text


# ---------- T6 节点侧装配入口（缝缺省就地兜底——dump 空/None 两形） ----------


def test_build_understand_instruction_full_dump() -> None:
    dump = {
        "metrics": [_metric("日产油量", "吨", True)],
        "terms": [{"term": "躺井", "banned": False,
                   "value": "躺井（黑话 → 停产待检泵 · 有效）：作业区口语"}],
        "objects": [{"obj": "井", "value": "井（草案）：井号 / 井别"}],
        "relations": [{"rel": "", "value": "井 —隶属→ 油田——井属于油田"}],
        "families_map": {"隶属": ["completion", "monthly"], "受效": ["monthly"]},
    }
    text = build_understand_instruction(
        question="问昨日日产油。",
        dump=dump,
        object_lines=None,  # 组合根未注入本体摘要——回退 dump.objects 薄形
        watermark_date=date(2026, 8, 31),
        today=date(2026, 9, 1),
    )
    assert text.startswith("【场景】")
    assert "日产油量｜吨｜可出数" in text
    assert "躺井＝停产待检泵" in text
    assert "井：井号 / 井别" in text  # 薄形回退在场
    assert "数据水位：2026-08-31" in text  # 水位缝优先
    assert "completion（完井工程报告）" in text
    assert text.rstrip().endswith(
        "（先判与业务的相关性：可能有关＝两行式；确定无关的寒暄闲聊＝直答。现在输出。）"
    )
    # V2-80a 路由原则化条款在任务书内（可能有关＝两行式／确定无关＝直答——零禁令零例子）。
    assert "唯一例外（纯寒暄直答）" in text
    assert "你的判断只有一个" in text and "可能" in text
    assert "确定与业务毫无关系" in text
    assert "以油田数据问答助手的身份" in text
    # 原禁令式措辞退役（V2-80a——禁止式白名单拆除）。
    assert "一律不用" not in text
    assert "不含任何查询" not in text


def test_build_understand_instruction_empty_dump_uses_today() -> None:
    text = build_understand_instruction(
        question="问昨日日产油。",
        dump=None,
        object_lines=None,
        watermark_date=None,  # 水位缝缺——回退 today
        today=date(2026, 9, 1),
    )
    assert "数据水位：2026-09-01" in text
    assert "台账指标名录（0 条" in text
    assert "问昨日日产油。" in text


# ---------- iso_day 形状 ----------


def test_iso_day_shapes() -> None:
    assert iso_day(date(2026, 8, 31)) == "2026-08-31"
    assert iso_day(lambda: date(2026, 8, 31)) == "2026-08-31"
    assert iso_day(None) == ""


# ---------- V2-80d 钉（查询性质声明＋作用域句＋拒因翻译） ----------


def test_v2_80d_system_prompt_query_identity_and_scope() -> None:
    """SYSTEM_PROMPT：查询性质声明（执行类诉求不在系统内）＋红线 2 作用域句
    （找到才逐源详答／没找到简短说明＋主体未命中请确认）。"""
    from appv2.runtime.context import SYSTEM_PROMPT

    assert "查询与解读系统" in SYSTEM_PROMPT
    assert "执行类诉求" in SYSTEM_PROMPT and "引导线下流程" in SYSTEM_PROMPT
    assert "逐源作答只用于材料确实覆盖了所问内容的情形" in SYSTEM_PROMPT
    assert "只说明未找到并请用户确认" in SYSTEM_PROMPT


def test_v2_80d_answer_instruction_scope_clause() -> None:
    """作答指令：未找到比例半句在册（追加不删改——V2-61 锁定段零触碰）。"""
    from appv2.runtime.graph import _ANSWER_INSTRUCTION

    assert "（材料未覆盖所问时：只简短说明未找到与所缺，不逐源铺陈无关材料）" in _ANSWER_INSTRUCTION


def test_v2_80d_humanize_refusal_translations() -> None:
    """拒因翻译单点：已知形（指标不在台账全量）→人话；未知形→兜底保留原文。"""
    from appv2.runtime.graph import _humanize_refusal

    known = _humanize_refusal(
        "指标 '油田' 不在台账全量——确定性校验拒（不在目录不代答；台账闭世界校验）"
    )
    assert "「'油田'」不在可查询的指标名录里" in known
    assert "确定性校验拒" not in known  # 机读措辞不达用户面
    unknown = _humanize_refusal("某种全新拒因形态")
    assert "系统没法直接给这条的数" in unknown and "某种全新拒因形态" in unknown

"""任务书装配（数据区→题干段）＋读题环节规章段（指令区＋输出契约区）——确定性拼接、零判断。

段序真源＝`specs/understanding.md` 行为 1（三区序）＋`specs/prompts.md` 行为 3（题干段置末）；
数据区真源＝`recon/L2a-装配前半.md`（V1 `assemble_understand_turn` 的环境段迁移）。本模块
零判断：不判相关性、不判要不要问、不筛内容——只拼字（判断在模型，装配在程序）。

**2026-10-17 H 批（角色分家·system 承载位）**：原一条 user 包（指令区→数据区→输出契约区→
题干段）**拆两路**——**规章段**（指令区＋输出契约区）＝`understand_system_contract()`，经
`bookkeeping.call_model(system=…)` **随本次请求走**（前置一条 system 条，不入链）；**动态段**
（数据区＋题干段）＝`assemble_task_book()`，仍作 user 条入链。文本零改、段内相对序零改，
**只换承载位**（真源 `specs/prompts.md` 2026-10-17 H 批注：「规章走 system、动态段留 user」）。

入参纪律（`specs/prompts.md` 接口定义节）：只读 `state` 投影字段（`ledger_dump`）；
**水位＝时间量，只经入参注入**（`watermark`），本块不读时钟（B14 在装配面的形态）。

指令区四常量与题干段原＝**V1 逐字迁移**（`arch/P6b` A-P6b-24/34「文本常量零变化、只换承载位」，
逐字真源＝`appv2/runtime/orientation.py` L20-78＋题干段 L275-276）；**2026-10-18 V2-87 已统一为
单 JSON**——V1 的「两行式／直答」措辞与三则样例两行输出退役（逐字稿＝V2-87 票面四段＋主窗裁决
的题干收束句），输出契约模板补 `subjects`／`terms` 两键（消费面已读、契约必须列）；原「登记张力」
（`specs/understanding.md` 行为 3 定「输出契约＝单个 JSON 对象；不使用两行式」而本块字面仍两行式）
随之销案。

**2026-10-17 V2-82a（程序预识别推荐行）**：数据区块尾接一行「程序预识别」（逐字稿＝票面②，
字面落点＝`RECOMMENDATION_TEMPLATE`）——主体／术语候选的顿号串由**装配方**（`understanding.
assembly`，经 `tools` 包根调 `subject_terms`）拼好随 `recommendation` 注入，本块只渲字；
空串＝不加行（既有调用逐字不变）。位置＝区块尾、题干段之前（题干段仍置末）。

**2026-10-17 V2-82（环境块去重瘦身）**：段头＝一行功能段头（逐字稿见票面①）——原「【环境】」
表头＋「【本系统】」四句介绍（与链首背景块 `SYSTEM_BACKGROUND` 语义全覆盖重复）随删；指标
名录／术语表两节改名字级（下文①②）；追加链原则＝任何信息只在被需要的最早环节注入一次——
环境块只服务理解环节三件事（相关性判断／指标提名／主体识别），绑定态与定义由后续「台账全量
常驻块」（`prompts/decision_round.render_ledger_resident_block`）全量承担。

与 V1 数据区的差异（显式声明——逐字稿 V1 环境段 L251-268 的迁移面）：
①指标名录行＝名字级顿号串（V1 `名字｜单位｜状态` 行形退场：单位段随结构化投影退场，本块
  禁正则 `specs/prompts.md` 行为 15；绑定态注解由常驻块承接）；
②术语行＝`口语／别名→正名`映射对（名字取 `term` 字段、正名取投影值串的箭头／替代名——
  零正则；类型／时效／定义注记不渲染）；对象／关系行＝台账投影值串逐字转抄（V1 的「未列
  属性」探测为正则或子串判定，V2 不迁移）——逐字转抄不改写、不摘要（同常驻块纪律）。
其余静态文案（段头／清单指引／空块占位文案／缩进）＝V1 照抄（含占位文案逐字：
「（暂无族标注）」「（空）」「关系：（空）」「（水位未取得）」）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from appv2.runtimev2.prompts.constants import (
    TASK_BOOK_EXAMPLES,
    TASK_BOOK_OUTPUT_CONTRACT,
    TASK_BOOK_REDLINE,
    TASK_BOOK_SCENE,
    TASK_BOOK_TASK,
)
from appv2.runtimev2.state import RunState

# 段间连接形（真源 recon/L2a R-L2a-17：段间「\n\n」连接）。
_PARA_SEP = "\n\n"
# 空块占位文案（逐字——真源 recon/L2a R-L2a-19；指标／术语／对象「（空）」、关系「关系：（空）」）。
_EMPTY = "（空）"
_EMPTY_RELATION = "关系：（空）"
_NO_FAMILY = "（暂无族标注）"
_NO_WATERMARK = "（水位未取得）"

# 库族机器名→中文名（迁移照抄 V1 `FAMILY_GLOSS`；缺键落「?」——真源 R-L2a-20）。
FAMILY_GLOSS: Mapping[str, str] = {
    "completion": "完井工程报告",
    "monthly": "月报",
    "dynamic": "生产动态",
}

# 程序预识别推荐行（**2026-10-17 V2-82a 逐字稿**——票面②）：接在数据区块尾、题干段之前；
# `{subjects}`／`{terms}`＝程序抽出的主体／术语候选顿号串（空＝调用方填「无」——拼装归
# `understanding.assembly`，本块只落字面）。一行一件、非空才渲染（`recommendation` 空串＝不加行，
# 直接调 `assemble_task_book` 的既有调用逐字不变）。
RECOMMENDATION_TEMPLATE = (
    " - 程序预识别（仅供参考——可能不准，以你的判断为准）：主体候选：{subjects}；术语候选：{terms}"
)

# 题干段（迁移照抄 V1 `assemble_understand_turn` 末段——真源 R-L2a-22；
# 题干非三区之一、置末紧邻生成点）。
# **2026-10-18 V2-87**：收束句随输出形统一改 **JSON 两出口**（逐字稿＝V2-87 主窗裁决）——
# 原「可能有关＝两行式；确定无关的寒暄闲聊＝直答」是模型可见的最后一处两行式残留，本批退役。
_QUESTION_SEGMENT = (
    "【待解构的题干】\n{question}\n"
    "（先判与业务的相关性：可能有关＝输出 route=\"full\" 的 JSON；"
    "确定无关的寒暄闲聊＝输出 route=\"direct\" 的 JSON。现在输出。）"
)


def _rows(value: Any) -> list[Mapping[str, Any]]:
    """投影块取值（非列表／非映射项一律不取——不抛错、不编造，形态过滤零语义）。"""
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _projection(state: RunState) -> Mapping[str, Any]:
    dump = state.ledger_dump
    return dump if isinstance(dump, Mapping) else {}


def _family_line(dump: Mapping[str, Any]) -> str:
    """资料库族行（真源 R-L2a-20：机器名（中文释义），缺键「?」；空集走占位文案）。"""
    families_map = dump.get("families_map")
    if not isinstance(families_map, Mapping):
        return _NO_FAMILY
    tags: set[str] = set()
    for values in families_map.values():
        if isinstance(values, (list, tuple, set, frozenset)):
            tags.update(tag for tag in values if isinstance(tag, str))
    line = "、".join(f"{tag}（{FAMILY_GLOSS.get(tag, '?')}）" for tag in sorted(tags))
    return line or _NO_FAMILY


def _metric_line(metric: Mapping[str, Any]) -> str:
    """指标名录条目（名字级——绑定态与定义由后续台账全量常驻块承接）。"""
    return str(metric.get("slot", ""))


def _term_line(term: Mapping[str, Any]) -> str:
    """术语表条目（口语／别名→正名映射对；非映射词条＝裸名——不带类型／时效／定义注记）。

    正名取投影值串里的箭头目标（`黑话 → X`／`别名 → X`；到「 · 」或「）」为止）；无箭头
    时取禁用词替代名（`（替代：X）`——V1 称之为「正确名」）；两者皆无＝纯定义型词条，只报名。
    """
    value = str(term.get("value") or "")
    target = value.partition("→")[2].split(" ·", 1)[0].split("）", 1)[0].strip()
    if not target:
        target = value.partition("替代：")[2].split("）", 1)[0].strip()
    name = str(term.get("term") or "")
    return f"{name}→{target}" if target else name


def _object_line(obj: Mapping[str, Any]) -> str:
    return str(obj.get("value") or obj.get("obj") or "")


def _relation_line(relation: Mapping[str, Any]) -> str:
    return str(relation.get("value") or relation.get("rel") or "")


def render_data_zone(
    state: RunState, *, watermark: str = "", recommendation: str = ""
) -> str:
    """数据区渲染（活体投影现取；标来源；空块走占位文案两形——零降级）。

    段头＝一行功能段头（V2-82 逐字稿）；指标名录／术语表＝名字级单行（绑定态与定义由后续
    台账全量常驻块承接）；对象／关系节照旧。

    `recommendation`＝「程序预识别」推荐行全文（V2-82a：装配方按 `RECOMMENDATION_TEMPLATE`
    填好传入）——**非空才渲染**，接在区块尾、题干段之前；空串＝既有调用逐字不变。
    """
    dump = _projection(state)
    metrics = _rows(dump.get("metrics"))
    terms = _rows(dump.get("terms"))
    objects = _rows(dump.get("objects"))
    relations = _rows(dump.get("relations"))
    metric_block = "、".join(_metric_line(m) for m in metrics) or "\n  " + _EMPTY
    term_block = "、".join(_term_line(t) for t in terms) or "\n  " + _EMPTY
    object_block = "\n".join("  " + _object_line(o) for o in objects) or "  " + _EMPTY
    relation_block = (
        "\n".join("  关系：" + _relation_line(r) for r in relations) or "  " + _EMPTY_RELATION
    )
    zone = (
        "【环境数据】（以下由系统按当前数据现状动态装配——业务相关性只看领域是否沾边；"
        "数据止于下方水位日）\n"
        f"- 资料库族：{_family_line(dump)}——报告事实（完井参数／月报统计／生产动态／治理事件）"
        "都在这里。\n"
        f"- 数据水位：{watermark or _NO_WATERMARK}——题干中「本月／去年」等时间词以该日为锚。\n"
        f" - 台账指标名录（{len(metrics)} 条——名字级清单；绑定态与定义见后续台账全量块）："
        f"{metric_block}\n"
        f" - 术语表（{len(terms)} 条——口语/别名→正名；定义见后续台账全量块）：{term_block}\n"
        " - 本体速览（解构用户问题的依据——用户说的名词对到对象，动作对到关系，取数对到指标）：\n"
        f"  对象：\n{object_block}\n{relation_block}"
    )
    if recommendation:
        zone = zone + "\n" + recommendation
    return zone


def instruction_zone() -> str:
    """指令区＝场景→任务→样例→红线四常量（相对序真源 `specs/prompts.md` 行为 3）。"""
    return _PARA_SEP.join([TASK_BOOK_SCENE, TASK_BOOK_TASK, TASK_BOOK_EXAMPLES, TASK_BOOK_REDLINE])


def understand_system_contract() -> str:
    """读题环节**规章段**（system 承载位——2026-10-17 H 批）：指令区＋输出契约区。

    文本零新写（指令区四常量＋输出契约区逐字，均为既有常量）；与动态段的分工＝
    **规章＝system、材料与题面＝user**：数据区（活体投影现取）与题干段留 `assemble_task_book`。
    纯文本进出、确定性（同入参两跑逐字相等）；`state` 零写入。
    """
    return _PARA_SEP.join([instruction_zone(), TASK_BOOK_OUTPUT_CONTRACT])


def question_segment(question: str) -> str:
    """题干段（置末、紧邻生成点——题干非三区之一）。"""
    return _QUESTION_SEGMENT.format(question=question)


def assemble_task_book(
    state: RunState, *, watermark: str = "", recommendation: str = ""
) -> str:
    """任务书**动态段**（数据区→题干段；段间「\\n\\n」连接）——user 承载位（2026-10-17 H 批）。

    规章段（指令区＋输出契约区）经 `understand_system_contract` 走调用级 system 注入参、不入链
    （真源 `specs/prompts.md` 2026-10-17 H 批注：「规章走 system、动态段留 user」）。本函数只出
    动态段：数据区＝活体投影现取、题干段置末紧邻生成点（行为 2／3 的段内相对序不变）。

    `recommendation`＝「程序预识别」推荐行（V2-82a）——随注入文本进数据区尾（空串＝不加行）；
    本块不产该文本（拼装归 `understanding.assembly`，字面单点＝`RECOMMENDATION_TEMPLATE`）。

    纯函数：只读 `state` 投影与注入的文本（水位／推荐行），零 IO／零时钟／零随机（行为 14）；
    输出恒为 `str`（不抛业务错、不返回 `None`）。
    """
    return _PARA_SEP.join(
        [
            render_data_zone(state, watermark=watermark, recommendation=recommendation),
            question_segment(state.question),
        ]
    )

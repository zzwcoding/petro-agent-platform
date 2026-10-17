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

指令区四常量与题干段＝**V1 逐字迁移**（`arch/P6b` A-P6b-24/34「文本常量零变化、只换承载位」，
逐字真源＝`appv2/runtime/orientation.py` L20-78＋题干段 L275-276）：**登记张力**——其字面仍为
V1 的「两行式／直答」措辞，而 `specs/understanding.md` 行为 3 定「输出契约＝单个 JSON 对象；
不使用两行式」；本块不自行改写 Owner 审定文案（无逐字稿），登记待主窗裁决。

与 V1 数据区的差异（显式声明——逐字稿 V1 环境段 L251-268 的迁移面）：
①指标名录行形＝`名字｜状态`（V1 `名字｜单位｜状态`）——V1 的单位段靠正则从 `value` 提取，
  本块禁正则（`specs/prompts.md` 行为 15），单位段随结构化投影退场，块头同步改述；
②术语／对象／关系行＝台账投影值串逐字转抄（V1 的箭头映射／定义截取／「未列属性」探测
  同为正则或子串判定，V2 不迁移）——逐字转抄不改写、不摘要（同常驻块纪律）。
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

# 指标绑定态两形文案（迁移照抄 V1 `render_metric_lines`——真源 R-L2a-02）。
_BOUND = "可出数"
_UNBOUND = "未绑定（台账无数值——数值走报告检索）"

# 题干段（迁移照抄 V1 `assemble_understand_turn` 末段＋收束句——真源 R-L2a-22；
# 题干非三区之一、置末紧邻生成点）。
_QUESTION_SEGMENT = (
    "【待解构的题干】\n{question}\n（先判与业务的相关性：可能有关＝两行式；"
    "确定无关的寒暄闲聊＝直答。现在输出。）"
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
    binding = _BOUND if metric.get("binding_state") == "bound" else _UNBOUND
    return f"{metric.get('slot', '')}｜{binding}"


def _term_line(term: Mapping[str, Any]) -> str:
    head = "禁用词！" if term.get("banned") else ""
    return head + str(term.get("value") or term.get("term") or "")


def _object_line(obj: Mapping[str, Any]) -> str:
    return str(obj.get("value") or obj.get("obj") or "")


def _relation_line(relation: Mapping[str, Any]) -> str:
    return str(relation.get("value") or relation.get("rel") or "")


def render_data_zone(state: RunState, *, watermark: str = "") -> str:
    """数据区渲染（活体投影现取；标来源；空块走占位文案两形——零降级）。"""
    dump = _projection(state)
    metrics = _rows(dump.get("metrics"))
    terms = _rows(dump.get("terms"))
    objects = _rows(dump.get("objects"))
    relations = _rows(dump.get("relations"))
    metric_block = "\n".join("  " + _metric_line(m) for m in metrics) or "  " + _EMPTY
    term_block = "\n".join("  " + _term_line(t) for t in terms) or "  " + _EMPTY
    object_block = "\n".join("  " + _object_line(o) for o in objects) or "  " + _EMPTY
    relation_block = (
        "\n".join("  关系：" + _relation_line(r) for r in relations) or "  " + _EMPTY_RELATION
    )
    return (
        "【环境】（以下由系统按当前数据现状动态装配）\n"
        "【本系统】（事实描述——业务相关性的判断依据）\n"
        "本系统是油田生产与管理数据的问答系统：围绕油田、井、区块的生产与管理数据，"
        "以及完井工程、生产动态、月报等报告中的事实，做查询、检索与解读。\n"
        "台账指标、术语与本体对象的具体清单见下方——它们是后续环节取数的依据；"
        "你判断相关性只看领域是否沾边。\n"
        "数据止于下方水位日。\n"
        f"- 资料库族：{_family_line(dump)}——报告事实（完井参数／月报统计／生产动态／治理事件）"
        "都在这里。\n"
        f"- 数据水位：{watermark or _NO_WATERMARK}——题干中「本月／去年」等时间词以该日为锚。\n"
        f" - 台账指标名录（{len(metrics)} 条——名字｜状态，可出数＝数值在台账；"
        "未绑定＝有名字暂无数值）：\n"
        f"{metric_block}\n"
        f" - 术语表（{len(terms)} 条——口语／别名 → 正名；纯定义型给一句式定义）：\n"
        f"{term_block}\n"
        " - 本体速览（解构用户问题的依据——用户说的名词对到对象，动作对到关系，取数对到指标）：\n"
        f"  对象：\n{object_block}\n{relation_block}"
    )


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


def assemble_task_book(state: RunState, *, watermark: str = "") -> str:
    """任务书**动态段**（数据区→题干段；段间「\\n\\n」连接）——user 承载位（2026-10-17 H 批）。

    规章段（指令区＋输出契约区）经 `understand_system_contract` 走调用级 system 注入参、不入链
    （真源 `specs/prompts.md` 2026-10-17 H 批注：「规章走 system、动态段留 user」）。本函数只出
    动态段：数据区＝活体投影现取、题干段置末紧邻生成点（行为 2／3 的段内相对序不变）。

    纯函数：只读 `state` 投影与注入的水位文本，零 IO／零时钟／零随机（行为 14）；
    输出恒为 `str`（不抛业务错、不返回 `None`）。
    """
    return _PARA_SEP.join(
        [
            render_data_zone(state, watermark=watermark),
            question_segment(state.question),
        ]
    )

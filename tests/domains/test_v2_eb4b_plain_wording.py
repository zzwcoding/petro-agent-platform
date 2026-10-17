"""EB4b 程序写死文案白话化批的契约测试（2026-10-17）。

依据＝`docs/runtime-refactor/research/最佳实践-3a-白话化与受众适配.md` 第三节 3.2（「用户可见面
文案白话化＋术语映射单源＋裸术语机检护栏」）；票面＝EB4b（程序写死文案白话化批）。

**两刀纪律的机检栅（本件三条）**：

1. **用户可见面文案不得含未注解行话词**（行话词表＝共享白话单源
   `prompts.JARGON_PLAIN_GLOSSARY` 的键集——「注解形」＝该词后紧跟「（」，逐条对上屏常量断言）。
   上屏口径（票面逐字）＝**正文（text 帧）／supplement 帧／notice 帧／ask 帧**四路径。
2. **术语白话映射单源（禁止第二份字面）**：共享表右侧的白话注解字面在四个相位块源码零命中
   ——相位块内出现第二份白话注解即判失败（要注解除非引共享单源，否则读写各说各话）。
3. **回喂机面零改动栅**（A-P6b-05）：机器拒因原文／拒因回喂行／机读缺口面**逐字冻结**——
   本件逐常量钉死字面（对账面），任何一处改动即红，逼改动者显式回设计仓裁决。

**扫描面与豁免面（如实登记）**：上屏清单＝EB4b 核实后的确认集＋V2-82e 引擎注记常量四条
（见 `_USER_FACE_TEXTS`）；**未入本件**的用户面文本分两类——①非上屏面（步帧标题／过程档案
digest／机读 payload：`TITLE_*`／`STEP_TITLE_*`／`NOTE_DIGEST_*`／`CAPPED_NOTE_DIGEST`，
按票面上屏口径不属用户可见面）；②本人行话词表外、已是白话的样板（`NO_MATERIAL_SHELL`／
`CITATION_BLOCK_HEAD`／`CONTRADICTION_SECTION_HEAD`）——已逐条核实、零改（记录见各
`constants.py` 的「两刀分类」注）。
"""

from __future__ import annotations

from pathlib import Path

from appv2.retrieval import domain as retrieval_domain
from appv2.runtimev2.answering import constants as answering_constants
from appv2.runtimev2.clarification import constants as clarification_constants
from appv2.runtimev2.execution import constants as execution_constants
from appv2.runtimev2.preconditions import constants as preconditions_constants
from appv2.runtimev2.prompts import JARGON_PLAIN_GLOSSARY

_REPO_ROOT = Path(__file__).resolve().parents[2]

# ── ① 行话词表（＝共享白话单源的键集——本件只声明、并在 `test_jargon_table_single_source` 里
#       与共享表的键逐一对账；表长胖或改名 → 本件红，逼重跑白话化核实）────────────────────
_JARGON_TERMS: tuple[str, ...] = ("口径", "台账", "水位", "窗", "绑定", "召回", "送窗")

# 注解形判据：注解记号＝紧随其后的全角左括号（口径（这个数是按什么规则算的））。
_ANNOTATION_MARK = "（"

# ── ② 上屏面文案清单（EB4b 确认集：逐条＝已核实上屏路径 + 已核实行话词零残留）──────────
_USER_FACE_TEXTS: dict[str, str] = {
    # answering：notice 帧内容（web `NoticeRow` 渲染 content）
    "answering.MATERIAL_TRUNCATED_CONTENT": answering_constants.MATERIAL_TRUNCATED_CONTENT,
    "answering.EMISSION_STRIP_CONTENT": answering_constants.EMISSION_STRIP_CONTENT,
    "answering.EMISSION_STRIP_EMPTY_CONTENT": (
        answering_constants.EMISSION_STRIP_EMPTY_CONTENT
    ),
    # answering：增补面（supplement 帧 text／run 行 supplements——交付面，
    # 评分面＝正文＋增补面合并判）
    "answering.CONTRADICTION_SECTION_HEAD": answering_constants.CONTRADICTION_SECTION_HEAD,
    "answering.SOURCE_SECTION_HEAD": answering_constants.SOURCE_SECTION_HEAD,
    "answering.CITATION_BLOCK_HEAD": answering_constants.CITATION_BLOCK_HEAD,
    # preconditions：ask 帧 prompt（web 反问卡正文）
    "preconditions.WINDOW_ASK_PROMPT_TEMPLATE": preconditions_constants.WINDOW_ASK_PROMPT_TEMPLATE,
    # preconditions：notice 帧内容四壳（机读槽位保留，见各常量注）
    "preconditions.NOTICE_REFUSED_TEMPLATE": preconditions_constants.NOTICE_REFUSED_TEMPLATE,
    "preconditions.NOTICE_ASK_TEMPLATE": preconditions_constants.NOTICE_ASK_TEMPLATE,
    "preconditions.NOTICE_NOTE_TEMPLATE": preconditions_constants.NOTICE_NOTE_TEMPLATE,
    "preconditions.NOTICE_CHAIN_SWITCH_TEMPLATE": (
        preconditions_constants.NOTICE_CHAIN_SWITCH_TEMPLATE
    ),
    # preconditions：两条 NOTE 经 notice `{digest}` 上屏
    "preconditions.NOTE_MENTION_ONLY": preconditions_constants.NOTE_MENTION_ONLY,
    "preconditions.NOTE_CHAIN_SWITCH_REENTRY": preconditions_constants.NOTE_CHAIN_SWITCH_REENTRY,
    # clarification：正文首行（text 帧）＋ notice 内容
    "clarification.CAPPED_ANSWER_HEADER": clarification_constants.CAPPED_ANSWER_HEADER,
    "clarification.CAPPED_NOTICE_TEMPLATE": clarification_constants.CAPPED_NOTICE_TEMPLATE,
    "clarification.QUOTE_REPAIR_NOTICE_CONTENT": (
        clarification_constants.QUOTE_REPAIR_NOTICE_CONTENT
    ),
    "clarification.NO_MATERIAL_SHELL": clarification_constants.NO_MATERIAL_SHELL,
    # execution：notice 帧内容（`{reason}` 槽＝拒因原文，壳白文化）
    "execution.CONTENT_REPLAY_NOTICE_PREFIX": execution_constants.CONTENT_REPLAY_NOTICE_PREFIX,
    "execution.CONTENT_EMPTY_PROBE_NOTICE_PREFIX": (
        execution_constants.CONTENT_EMPTY_PROBE_NOTICE_PREFIX
    ),
    "execution.CONTENT_REF_DISCLOSURE_TEMPLATE": (
        execution_constants.CONTENT_REF_DISCLOSURE_TEMPLATE
    ),
    "execution.CONTENT_SUBTASK_REFUSED_TEMPLATE": (
        execution_constants.CONTENT_SUBTASK_REFUSED_TEMPLATE
    ),
    "execution.CONTENT_SUBTASK_FAILED_TEMPLATE": (
        execution_constants.CONTENT_SUBTASK_FAILED_TEMPLATE
    ),
    "execution.CONTENT_TOOL_UNAVAILABLE_TEMPLATE": (
        execution_constants.CONTENT_TOOL_UNAVAILABLE_TEMPLATE
    ),
    "execution.CONTENT_DECISION_REJECTED_TEMPLATE": (
        execution_constants.CONTENT_DECISION_REJECTED_TEMPLATE
    ),
    "execution.CONTENT_PLAN_FACE_NOTICE_PREFIX": (
        execution_constants.CONTENT_PLAN_FACE_NOTICE_PREFIX
    ),
    # retrieval：window_note 各段逐字常量（V2-82e 引擎注记白话批——notice 帧正文＋
    # 模型面材料段；handlers 以 window_note 原文落 notice 观察）。L0 2026-10-17 裁决
    # 改稿后四条同等待遇入册（逐字稿载体＝本件 ⑤ 同源断言）。
    "retrieval.NOTE_RECALLED_SENT": retrieval_domain.NOTE_RECALLED_SENT,
    "retrieval.NOTE_RECALL_GAP": retrieval_domain.NOTE_RECALL_GAP,
    "retrieval.NOTE_CONFLICT_SOURCES": retrieval_domain.NOTE_CONFLICT_SOURCES,
    "retrieval.NOTE_MISSING_SOURCES": retrieval_domain.NOTE_MISSING_SOURCES,
}

# ── ③ 回喂机面冻结点（A-P6b-05——拒因原文／拒因回喂行／机读缺口面；字面逐字＝本批改动前的仓内
#       现状，来源见各块 constants 注；改动任一处＝红，须回设计仓裁决）────────────────────
_FROZEN_MACHINE_FACE: dict[tuple[str, str], str] = {
    ("answering", "ENGINE_NOTES_HEAD"): (
        "\n引擎注记（引擎降级／拦停／未绑定注记——如实转述，不得静默丢弃）：\n"
    ),
    ("answering", "ZERO_MATERIAL_REASON"): (
        "零实质材料（观察面无非 notice 条目）——本轮回答无材料可核，未及核验"
    ),
    ("answering", "EMPTY_DRAFT_REASON"): (
        "模型未产出草稿（剥离后空稿）——不推空答案，按结构化缺口如实收口"
    ),
    ("answering", "MISSING_DRAFT_REASON"): "起草未产出可交付答案——按结构化缺口如实收口",
    ("answering", "SUBTASK_MISSING_REASON"): "执行未取得材料（失败／重试耗尽）",
    ("preconditions", "GATE_UNAVAILABLE_TEXT"): (
        "前置条件机闸件不可用（判定器抛错）——按 fail-closed 如实拒答，不静默放行"
    ),
    ("preconditions", "CHAIN_SWITCH_TERMINAL_TEXT_TEMPLATE"): (
        "换链回炉已用尽（一次为界）：坚持 data 链同参（指纹 {fingerprint}…在簿）——{tail}"
    ),
    ("preconditions", "CHAIN_SWITCH_TERMINAL_TAIL_UNBOUND"): "未绑定口径如实拒答，不代答",
    ("preconditions", "CHAIN_SWITCH_TERMINAL_TAIL_DOMAIN"): (
        "题眼井不在数据链井闭世界——域错如实拒答，不代答"
    ),
    ("clarification", "GUIDANCE_PRECONDITION"): (
        "数据链已被前置判定拒（在册未绑定/台账外）——该指标材料走报告检索："
        "分解时 chain=knowledge、tool=doc_retrieve"
    ),
    ("clarification", "GUIDANCE_EMPTY_PROBES"): "已空手探查：{tools}——禁再试同名同参",
    ("clarification", "GUIDANCE_FALLBACK"): (
        "先 discover 取得条目（精确名单词），或 decompose 分解走 doc_retrieve 检索执行。"
    ),
    ("clarification", "TEXT_ZERO_OBSERVATION"): "零实质观察禁定稿",
    ("clarification", "TEXT_NO_REDISCOVER"): "台账命中且时间窗已定——禁再 discover（直发分解）",
    ("clarification", "TEXT_SLOT_MISMATCH_HEAD"): (
        "上次发射被拒：ledger_notes 槽位对账未过：{ids}"
    ),
    ("clarification", "TEXT_SLOT_MISMATCH_TITLE"): "ledger_notes 槽位对账未过：{ids}",
    ("clarification", "TEXT_SLOT_MISMATCH_BLOCK"): (
        "【拒因】{id} 的「{segment}」段「{value}」{cause}\n"
        "【期望形】〈台账行首名｜或「无台账命中」〉｜已绑定|未绑定"
        "｜〈锚定窗形：2026-09-16~2026-10-16｜检索式无窗：窗未定或 null~null〉\n"
        "【台账相关行】{row}"
    ),
    ("clarification", "TEXT_SLOT_MISMATCH_TAIL"): "——修正后重新输出 JSON。",
    ("clarification", "CAUSE_SLOT_NOT_IN_LEDGER"): "不在台账名录",
    ("clarification", "CAUSE_BINDING_OUT_OF_WORLD"): "绑定态越界",
    ("clarification", "CAUSE_WINDOW_ILLEGAL"): "窗形不合法",
    ("clarification", "CAUSE_SEGMENT_COUNT"): "段数非三（形＝槽位｜绑定态｜窗，位次固定）",
    ("clarification", "NO_LEDGER_ROW_SHELL"): (
        "（名录无此名——只许用台账注入块内出现的指标/对象/关系/术语名；"
        "自造名≠「无台账命中」——无台账行时才写它）"
    ),
    ("clarification", "NO_LEDGER_HIT_ROW_SHELL"): "（无命中形——本子问题不锚台账行）",
    ("execution", "PLAN_FACE_REASON_UNGROUNDED_TEMPLATE"): (
        "计划面闸拒（问句指标在册无绑定／未注册）：计划指标「{slot}」无问句注册面支撑——"
        "禁止回落相近列出数（不给差不多）；改链（检索问答链如实说明）或如实拒答"
    ),
    ("execution", "PLAN_FACE_REASON_MISMATCH_TEMPLATE"): (
        "计划面闸拒（回落相近列）：问句注册面＝{slots}，计划指标「{slot}」不在其列——"
        "禁止把问句问及的指标换成相近代用品出数（不给差不多）；改链或如实拒答"
    ),
    ("execution", "EMPTY_PROBE_FEEDBACK_TEMPLATE"): (
        "{tool} 同参已空手（探查未命中）——禁原样重发；"
        "改用其他探查（换参视为新尝试），或 decompose 分解走 doc_retrieve。"
    ),
    ("execution", "SAME_PARAM_REPLAY_REASON"): (
        "同参已执行（同参重执行零新信息）——带结果直答或改参"
        "（finalize 按观察材料作答，或换参数后再发射），不要重复发射同一计划"
    ),
    ("execution", "MISSING_SOURCE_REASON"): (
        "观察缺出处（source 为空）：观察必带出处（台账行／片段→报告→库／表名）——"
        "缺出处＝判失败（INV-1 的输入），不猜、不补、不静默收下"
    ),
}

_PHASE_BLOCK_DIRS = (
    "answering",
    "preconditions",
    "clarification",
    "execution",
    "transport",
    "orchestration",
)


def _block_constants(name: str):
    """块 → 其 `constants` 模块（冻结点含未进包根公开面的常量，故直达常量模块）。"""
    return {
        "answering": answering_constants,
        "preconditions": preconditions_constants,
        "clarification": clarification_constants,
        "execution": execution_constants,
    }[name]


def _unannotated(text: str, terms: tuple[str, ...] = _JARGON_TERMS) -> list[tuple[str, int]]:
    """未注解行话词位点（词出现且其后不是注解记号「（」）——本件核心判据的纯函数形。

    重叠形按**最长词**归一（「送窗」命中即不再另记其内的「窗」——同一处不重复计数）。
    """
    covered: list[tuple[int, int]] = []
    hits: list[tuple[str, int]] = []
    for term in sorted(terms, key=len, reverse=True):
        start = 0
        while True:
            index = text.find(term, start)
            if index < 0:
                break
            end = index + len(term)
            if not any(index >= low and end <= high for low, high in covered):
                covered.append((index, end))
                after = text[end : end + 1]
                if after != _ANNOTATION_MARK:
                    hits.append((term, index))
            start = end
    return sorted(hits, key=lambda item: item[1])


def _glossary_pairs(glossary: str = JARGON_PLAIN_GLOSSARY) -> dict[str, str]:
    """共享白话单源（`【术语白话表】T＝P；…。`）→ `{术语: 白话}`（纯形态切分，零语义）。"""
    body = glossary.strip()
    head = "【术语白话表】"
    if body.startswith(head):
        body = body[len(head) :]
    if body.endswith("。"):
        body = body[:-1]
    pairs: dict[str, str] = {}
    for item in body.split("；"):
        term, separator, plain = item.partition("＝")
        assert separator and term and plain, f"共享白话单源条目形异常：{item!r}"
        pairs[term] = plain
    return pairs


# ---------- ① 上屏文案不得含未注解行话词（裸术语闸——EB4b 行 1） ----------


def test_user_face_texts_free_of_bare_jargon() -> None:
    """上屏面逐条：行话词出现处必带注解形（词后紧跟「（」）。"""
    assert len(_USER_FACE_TEXTS) >= 20, "上屏清单可疑（条数过少＝扫描面失效）"
    for name, text in _USER_FACE_TEXTS.items():
        assert text.strip(), f"{name} 文案为空"
        assert _unannotated(text) == [], f"{name} 含未注解行话词：{_unannotated(text)}"

    # 探测器非空转（病句必被咬、注解形必放行）
    assert _unannotated("召回 51 支／送窗 12 支") == [("召回", 0), ("送窗", 8)]
    assert _unannotated("召回（检索到的材料）51 条") == []
    # 仓内真机病句形（EB3 终判第 27 行病灶）必被咬
    assert _unannotated("已召回未送窗 39 支") != []


# ---------- ② 术语白话映射单源（禁第二份字面——EB4b 行 2） ----------


def test_jargon_plain_single_source() -> None:
    """共享白话单源为唯一注解真源：相位块内零副本（第二份字面＝判失败）。"""
    pairs = _glossary_pairs()
    # 词表与共享单源键集对账（表长胖／改名 → 本件红，逼重跑白话化核实）
    assert set(pairs) == set(_JARGON_TERMS), f"词表与共享单源不一致：{sorted(pairs)}"
    for term, plain in pairs.items():
        assert plain, f"共享单源 {term} 白话为空"

    # 白话注解字面在六个改造面块源码零命中（注释与文案同扫——「每处各说各话」的机检代理）
    offenders: dict[str, list[str]] = {}
    for block in _PHASE_BLOCK_DIRS:
        for path in sorted((_REPO_ROOT / "appv2" / "runtimev2" / block).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for term, plain in pairs.items():
                if plain in text:
                    offenders.setdefault(f"{block}/{path.name}", []).append(term)
    assert not offenders, f"出现第二份白话注解字面（应引共享单源）：{offenders}"

    # 探测器非空转：把共享白话正文投进伪造源即被咬
    forged = "台账（平台里登记指标和术语的名册）"
    assert pairs["台账"] in forged


# ---------- ③ 回喂机面零改动栅（A-P6b-05——EB4b 行 3） ----------


def test_machine_face_frozen_verbatim() -> None:
    """回喂机面（拒因原文／拒因回喂行／机读缺口面）逐字冻结——改动即红。"""
    assert len(_FROZEN_MACHINE_FACE) >= 25, "冻结点清单可疑（条数过少＝对账面失效）"
    for (block, name), literal in _FROZEN_MACHINE_FACE.items():
        assert getattr(_block_constants(block), name) == literal, (
            f"{block}.{name} 回喂机面字面被改动"
        )


# ---------- ④ 非上屏面登记（票面上屏口径的显式排除面，防「漏改」误判） ----------


def test_non_user_face_registry() -> None:
    """非上屏面＝步帧标题／过程档案 digest／机读 payload——本批零改（如实登记）。"""
    assert preconditions_constants.TITLE_TEMPLATE == "前置条件机：{subtask}={decision}"
    assert preconditions_constants.TITLE_RULE_TEMPLATE == (
        "前置条件机：{subtask}={decision}（{rule}）"
    )
    assert clarification_constants.CAPPED_NOTE_DIGEST == "连续澄清达上限（≥{cap}）——带材料直答"
    assert execution_constants.TITLE_ADMISSION_REJECTED_TEMPLATE == (
        "子问题 {subtask} 前置闸拒（终局不回炉）"
    )


# ---------- ⑤ V2-82e 引擎注记白话常量（window_note 各段逐字稿——L0 裁决改稿后转正） ----------


def test_note_texts_free_of_bare_jargon_words() -> None:
    """注记四条常量零「支/召回/送窗/口径」裸词（L0 裁决改稿逐字——grep 断言）。"""
    for text in (
        retrieval_domain.NOTE_RECALLED_SENT,
        retrieval_domain.NOTE_RECALL_GAP,
        retrieval_domain.NOTE_CONFLICT_SOURCES,
        retrieval_domain.NOTE_MISSING_SOURCES,
    ):
        for term in ("支", "召回", "送窗", "口径"):
            assert term not in text, f"{term} 裸词回退：{text!r}"
        assert _unannotated(text) == []  # 既有裸行话闸同判（全词表面）
    # 探测面非空转：老措辞字面必被咬（本条即「新文本不得回退到旧行话」的机检）。
    assert _unannotated("召回 21 支/送窗 4 支") != []

"""降级与引用簇（`RT-W4-06b`）——行为 6／12／13／14／15／16／17／19 的**确定性形态层**单点。

真源＝`specs/answering.md` 行为约定节（行为 6 多来源矛盾分开列／行为 12 行集题交付与落引用界线／
行为 13 占位符不进答案面／行为 14 起草回声＝0／行为 15 台账 no_hit 降级三段形／行为 16 排名型子问题
强制消费排名观察支／行为 17 跨油田题分源列明油田归属／行为 19 残尾护栏——定稿前悬空结构检测与
诚实收口，2026-10-17 F1 件三）。形态逐字迁移面＝`docs/runtime-refactor/
recon/A2-核验规则与归属审.md`（R-A2-29／R-A2-30 矛盾池分组形态、R-A2-23 分源列明、R-A2-27 归属块
行形）＋`recon/L2b-作答装配与回声.md`（草稿分段与假阳面）。

**本层零语义判断**（规格验收行 19 的豁免面：形态处理／集合成员判定）：

- 方括号记号扫描（引标记号 / 占位符记号）、全角「：」切分、字符集成员判定、字符串相等比较、
  计数与拼接、原文照抄——**全部形态处理**；
- 回声签名（行为 14）的两条判据字面是规格逐字给定的**形态签名**（`arch/P4b-票堆V2-56至65.md`
  A-P4b-61：「首行以『理解：』开头或前 100 字含『指标候选』」）——**观测字段只记不拦**：本层只
  产签名真值，零拦截、零改写、不进任何交付分支；
- 「答没答上原问题」不判（交模型与 `verification`）；本层不产任何一次语义裁决。

**分工登记（防两处漂移，呈主窗对账）**：

- 行为 12 的**执行侧**落点＝`specs/execution.md` 行为 4（`RT-W4-05a-execution.md` 行 4——
  `::big_result_ref_only`）；本层落**交付侧**：`engine_rows`／`delivered_rows` 两机读字段
  （答案面实际交付行数＝引擎返回行数 ⇒ 丢行=0 可机检），与 `specs/verification.md` 行为 11 的
  行集对账（`obs_rows`／`delivered_rows`）**同口径**——本块只记账与披露，**不拦截**（拦截与
  补如实注记归 `verification` 行为 11／钉 `pin-12`）；
- 行为 15／17 的**业务面枚举**（哪个油田的邻近可得量、逐井点名、「指路」措辞）属模型面义务
  （`prompts` 合同：答案要求③多来源逐源作答、④引擎降级注记如实转述）；本层只保证**不静默**：
  引擎注记原文送入窗口 ＋ 机读 `engine_notes` 字段；**零业务事实发明**（AGENTS.md 7）。
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.answering.constants import (
    ASCII_DIGITS,
    ASCII_LETTERS,
    BOLD_MARK,
    CONTRADICTION_EXEMPT_KINDS,
    CONTRADICTION_LINE,
    CONTRADICTION_SECTION_HEAD,
    ECHO_CANDIDATE_MARK,
    ECHO_HEAD,
    ECHO_WINDOW,
    ENGINE_NOTES_HEAD,
    FULLWIDTH_COLON,
    KIND_NOTICE,
    PAYLOAD_DELIVERED_ROWS_KEY,
    PAYLOAD_ENGINE_ROWS_KEY,
    ROWSET_OBSERVATION_KINDS,
    SENTENCE_END_EXCLAMATION,
    SENTENCE_END_FULLSTOP,
    SENTENCE_END_QUESTION,
    SENTENCE_END_SEMICOLON,
    SOURCE_LINE,
    SOURCE_SECTION_HEAD,
    TABLE_COLUMN_MARK,
    TAIL_CLOSE_BARE_HEADING,
    TAIL_CLOSE_LEAD_IN,
    TAIL_CLOSE_TABLE_HEADER,
    TAIL_HEADING_MAX_CHARS,
    TAIL_MIN_BODY_LINES,
    TAIL_TABLE_MAX_HEADER_LINES,
)
from appv2.runtimev2.transport import (
    SUPPLEMENT_BLOCK_ATTRIBUTION,
    SUPPLEMENT_BLOCK_SPLIT,
    same_family_head_in,
)

_OPEN = "["
_CLOSE = "]"
# 句读收尾字符集（残尾护栏的短行判据面——不以句读收尾者才可能是裸标题）。
_SENTENCE_ENDINGS = (
    SENTENCE_END_FULLSTOP,
    SENTENCE_END_QUESTION,
    SENTENCE_END_EXCLAMATION,
    SENTENCE_END_SEMICOLON,
    FULLWIDTH_COLON,
)


def bracket_tokens(text: str) -> list[tuple[int, int, str]]:
    """方括号记号列（`(起点, 终点, 体)`——终点＝「]」之后一位）——形态扫描单点（零正则、零语义）。

    「[」无「]」闭合的尾段不成记号（原样留在文本内）；体可为空串（`[]`）。嵌套方括号形按
    首个「]」切分（体含「[」＝非数字／非字母体，两判据自然不咬——与 -A 的引标扫描同口径）。
    """
    tokens: list[tuple[int, int, str]] = []
    cursor = 0
    while True:
        start = text.find(_OPEN, cursor)
        if start < 0:
            return tokens
        end = text.find(_CLOSE, start + 1)
        if end < 0:
            return tokens
        tokens.append((start, end + 1, text[start + 1 : end]))
        cursor = end + 1


def citation_seqs(text: str) -> list[int]:
    """文本内引标序号列（`[n]` 形——体全 ASCII 数字；出现序、含重复）——形态扫描，零语义。"""
    seqs: list[int] = []
    for _start, _end, body in bracket_tokens(text):
        if body and all(char in ASCII_DIGITS for char in body):
            seqs.append(int(body))
    return seqs


def strip_placeholders(text: str) -> str:
    """剥除字面占位符记号（行为 13）：体为 ASCII 字母的方括号记号（`[n]` 形）整枚离场。

    引标号（体全数字）与其它方括号文本原样保留；剥后成空的行由分段面（空段跳过）自然丢弃——
    「答案面不得出现字面占位引标 `[n]`」与「含 `[n]` 字面的行不得以占位符形式交付」两半同落。
    """
    out: list[str] = []
    cursor = 0
    for start, end, body in bracket_tokens(text):
        if not body or not all(char in ASCII_LETTERS for char in body):
            continue
        out.append(text[cursor:start])
        cursor = end
    if not out:
        return text
    out.append(text[cursor:])
    return "".join(out)


def strip_dangling_citations(
    text: str, known: frozenset[int] | set[int] | tuple[int, ...] | list[int]
) -> tuple[str, tuple[int, ...]]:
    """剥除**观察序列外**的引标记号（坏引标——行为 13 剥除族的第二形，2026-10-17 EB5b）。

    体全 ASCII 数字且序号不在 `known`（在界引标号集）内的方括号记号**整枚离场**——不猜、不补、
    不改写正文其余字面；返回（剥后文本，被剥序号列——出现序去重）。**判据纯形态**（同上方的
    占位符剥除：同一方括号扫描面，禁第二份）。剥后该行失去引标＝由核验面按「无据断言」既有处置
    收口（删句／结构行原样）——本层不做核验判定。
    """
    in_scope = set(known)
    out: list[str] = []
    removed: list[int] = []
    cursor = 0
    for start, end, body in bracket_tokens(text):
        if not body or not all(char in ASCII_DIGITS for char in body):
            continue
        seq = int(body)
        if seq in in_scope:
            continue
        out.append(text[cursor:start])
        cursor = end
        if seq not in removed:
            removed.append(seq)
    if not removed:
        return text, ()
    out.append(text[cursor:])
    return "".join(out), tuple(removed)


def echo_flag(text: str) -> bool:
    """起草回声签名（行为 14；判据字面＝A-P4b-61 逐字）——**观测字段只记不拦**。

    判据：草稿首行以「理解：」开头 **或** 草稿前 100 字含「指标候选」。调用方只许把本真值写进
    机读 payload；**不得据本签名拦截、改写或丢弃交付**（行为 14 末注「只记不拦」）。
    """
    first_line = text.split("\n", 1)[0]
    if first_line[: len(ECHO_HEAD)] == ECHO_HEAD:
        return True
    return text[:ECHO_WINDOW].find(ECHO_CANDIDATE_MARK) >= 0


def dangling_tail_closing(text: str) -> str:
    """残尾护栏（2026-10-17 F1 件三）：定稿前检测**悬空结构**——命中即返回诚实收口短句
    （未命中＝空串）。

    触发三形（判据全为**形态面**，零语义、零词表，见常量族注）：

    ① 末行以全角「：」收尾（悬空引导句）；② 末段连续表格行（含表格列记号）≤ 表头行上限（有表头
    无数据行）；③ 末段为**裸标题**——整行加粗，或独立短行（短、无引标、无 ASCII 数字、无句读收尾）。

    返回的短句由调用方（收口段）追加为末段：**只补一句诚实收口**，正文其余字面零改、零改写（不改
    数值断言、不重试、不拦截）；重入幂等判据＝该短句已在场（调用方把守）。真机证据＝run-c6fd52c7
    （删句误伤后交付答案断在裸标题「**两口井教训的差异**」，`eval/results/frames/EB4-D-诱12.json`）。
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    tail = lines[-1].strip()
    if tail[-len(FULLWIDTH_COLON) :] == FULLWIDTH_COLON:
        return TAIL_CLOSE_LEAD_IN
    if _table_header_tail(lines):
        return TAIL_CLOSE_TABLE_HEADER
    if _bare_heading_tail(lines, tail):
        return TAIL_CLOSE_BARE_HEADING
    return ""


def _table_header_tail(lines: Sequence[str]) -> bool:
    """末段表格行数判据（连续含表格列记号的行——只表头／表头＋分隔行＝有表头无数据行）。"""
    count = 0
    for line in reversed(list(lines)):
        if TABLE_COLUMN_MARK not in line:
            break
        count += 1
    return 0 < count <= TAIL_TABLE_MAX_HEADER_LINES


def _bare_heading_tail(lines: Sequence[str], tail: str) -> bool:
    """裸标题判据（整行加粗 或 独立短行——形态面；短行须无引标、无 ASCII 数字、无句读收尾）。"""
    if len(lines) < TAIL_MIN_BODY_LINES:
        return False
    if tail[: len(BOLD_MARK)] == BOLD_MARK and tail[-len(BOLD_MARK) :] == BOLD_MARK:
        return True
    if len(tail) > TAIL_HEADING_MAX_CHARS or citation_seqs(tail):
        return False
    if any(char in ASCII_DIGITS for char in tail):
        return False
    return tail[-1:] not in _SENTENCE_ENDINGS


def observation_kind(observation: Mapping[str, Any]) -> str:
    """观察 `locator.kind` 取值（形态读取：缺 `locator`／缺 `kind` 取空串——零语义）。"""
    locator = observation.get("locator")
    if not isinstance(locator, Mapping):
        return ""
    return str(locator.get("kind") or "")


def source_of(observation: Mapping[str, Any]) -> str:
    """观察出处名（`source` 原样；非串取空串）——引用块与分源块的出处面。"""
    source = observation.get("source")
    return source if isinstance(source, str) else ""


def source_id_of(observation: Mapping[str, Any]) -> str:
    """观察出处标识（`source_id` 原样；非串取空串）——与出处名同族的可机读定位面。"""
    source_id = observation.get("source_id")
    return source_id if isinstance(source_id, str) else ""


def content_of(observation: Mapping[str, Any]) -> str:
    """观察正文（`content` 原样；非串取空串）——分源列明**原文照抄**的取值面（零二次创作）。"""
    content = observation.get("content")
    return content if isinstance(content, str) else ""


def subject_of(content: str) -> str:
    """矛盾池 subject（首个全角「：」前段；无「：」或以「：」起首＝空串）——形态切分，零语义。"""
    index = content.find(FULLWIDTH_COLON)
    return content[:index] if index > 0 else ""


def value_of(content: str) -> str:
    """矛盾池值段（首个全角「：」后原文；无「：」或用「：」起首＝空串）——形态切分，零语义。"""
    index = content.find(FULLWIDTH_COLON)
    return content[index + 1 :] if index > 0 else ""


def contradiction_groups(
    cited: Sequence[int], by_index: Mapping[int, Mapping[str, Any]]
) -> list[list[int]]:
    """矛盾池分组（行为 6；形态逐字迁移 recon/A2 R-A2-29／R-A2-30）。

    辖域＝**被引**观察 ∩ `locator.kind` ∉ {`agg_row`, `lineage`, `notice`}（行级时序事实与元信息
    不入池）∩ content 含全角「：」且 subject 非空；同 subject 组内支数 ≥2 且值集合去重后 >1 →
    全组入池（按观察序号升序）。零调和、零取值：分组只做字符串相等判定（不判「哪个值对」）。
    """
    pools: dict[str, list[int]] = {}
    for seq in cited:
        row = by_index.get(seq)
        if row is None or observation_kind(row) in CONTRADICTION_EXEMPT_KINDS:
            continue
        subject = subject_of(content_of(row))
        if not subject:
            continue
        pools.setdefault(subject, []).append(seq)
    groups: list[list[int]] = []
    for seqs in pools.values():
        if len(seqs) < 2:
            continue
        values = {value_of(content_of(by_index[seq])) for seq in seqs}
        if len(values) > 1:
            groups.append(sorted(seqs))
    return sorted(groups, key=lambda seqs: seqs[0])


def contradiction_section(
    groups: Sequence[Sequence[int]], by_index: Mapping[int, Mapping[str, Any]], text: str
) -> str:
    """「互不一致」分源列明块（行为 6：分源列明、不强调和——逐支原文照抄，零二次创作）。

    收口重入面幂等：`text` 已携**同族块头行**＝零追加（不重复落块）——判据面＝块头模式族
    （2026-10-17 EB5c：由「固定字面在场」改为「同族块头在场」，加粗变体同族；单点＝
    `transport.same_family_head_in`）。
    """
    if not groups or same_family_head_in(text, SUPPLEMENT_BLOCK_SPLIT):
        return ""
    lines = [CONTRADICTION_SECTION_HEAD]
    for seqs in groups:
        for seq in seqs:
            row = by_index[seq]
            lines.append(
                CONTRADICTION_LINE.format(
                    seq=seq,
                    source=source_of(row),
                    source_id=source_id_of(row),
                    content=content_of(row),
                )
            )
    return "\n".join(lines)


def source_names(
    cited: Sequence[int], by_index: Mapping[int, Mapping[str, Any]]
) -> list[str]:
    """被引支的出处名序列（去重、按引标序）——分源块的触发判据面（形态处理，零语义）。"""
    names: list[str] = []
    for seq in cited:
        row = by_index.get(seq)
        if row is None:
            continue
        label = source_of(row)
        if label and label not in names:
            names.append(label)
    return names


def source_section(
    cited: Sequence[int], by_index: Mapping[int, Mapping[str, Any]], text: str
) -> str:
    """分源列明归属块（行为 17：逐源归属配对——来源名↔数值／结论配对，逐支原文照抄）。

    触发＝被引集跨 ≥2 个不同出处（`source` 字符串不等判定——**跨油田／跨区块／跨报告题的形态
    判据代理**：归属名承载在出处名里）。单出处＝零追加（保留集：普通答案的分源行为不变）。
    含糊归属形（「某区块／小范围结算序列」等不认列来源的框架）不由本块产出，无据归属不进
    答案面（本块只照抄窗口材料自带出处，零发明）。收口重入面幂等。
    """
    if len(source_names(cited, by_index)) < 2 or same_family_head_in(
        text, SUPPLEMENT_BLOCK_ATTRIBUTION
    ):
        return ""
    lines = [SOURCE_SECTION_HEAD]
    for seq in cited:
        row = by_index.get(seq)
        if row is None:
            continue
        lines.append(
            SOURCE_LINE.format(seq=seq, source=source_of(row), content=content_of(row))
        )
    return "\n".join(lines)


def engine_notes(observations: Sequence[Any]) -> list[str]:
    """引擎注记原文列（行为 15 的「不静默」面）：`locator.kind == notice` 的观察正文，按序、去空。

    引擎降级／拦停／未绑定注记（台账 no_hit 同族）在 `context.render_materials` 里整体排除
    （`specs/context.md` 行为 2），故本块另以其**原文**送入窗口（`prompts` 合同④「引擎的降级／
    未绑定／拦停注记必须如实转述」的材料侧承接）并落机读 payload——不得静默丢弃。零二次创作。
    """
    notes: list[str] = []
    for observation in observations:
        if not isinstance(observation, Mapping):
            continue
        if observation_kind(observation) != KIND_NOTICE:
            continue
        content = content_of(observation)
        if content:
            notes.append(content)
    return notes


def engine_notes_block(notes: Sequence[str]) -> str:
    """引擎注记段（窗口尾段——材料段之后）：无注记＝空串（零残留）。"""
    if not notes:
        return ""
    return ENGINE_NOTES_HEAD + "\n".join(notes)


def rowset_seqs(by_index: Mapping[int, Mapping[str, Any]]) -> list[int]:
    """行集族观察序号列（`locator.kind` ∈ 行集族 —— 引擎返回的**数据行**，按序号升序）。

    行集题全量交付的形态判据面（行为 12）：一观察即一行（`recon/H` 权威表行观察逐行一条）——
    交付行数＝引擎返回行数即「丢行=0」的机检形。
    """
    return [
        seq
        for seq in sorted(by_index)
        if observation_kind(by_index[seq]) in ROWSET_OBSERVATION_KINDS
    ]


def ranking_order_ok(text: str, branch_seqs: Sequence[int]) -> bool:
    """排名支序一致判定（行为 16 的**序信息**面）：被交付的排名支行首现位次随支序严格递增。

    排名观察支＝窗口行集族行（引擎按计划序返回——`specs/execution.md` 行为 4 行集承载）；
    交付的排名序对以 `[n]` 引标锚定，行首现位次乱序＝「排名序对与排名支序信息不一致」
    （数-排2 形：弃排名支、以他支拼排名）。未在答案面出现的支行不参与（无位次）；零语义判定
    ——只做引标位次比较。**只记不判罚**：本判定落机读字段，回炉／改写归 `verification`／
    `orchestration`（本块不产半成品改写，见 `core` 模块注）。
    """
    positions = [
        position
        for position in (text.find(f"[{seq}]") for seq in branch_seqs)
        if position >= 0
    ]
    return all(
        earlier < later
        for earlier, later in itertools.pairwise(positions)  # 相邻位次严格递增
    )


def delivery_accounting(
    by_index: Mapping[int, Mapping[str, Any]], delivered_seqs: Sequence[int]
) -> dict[str, int]:
    """行集交付对账（行为 12 **交付侧**）：`engine_rows`＝引擎返回行数、`delivered_rows`＝交付行数。

    两数同出**一次形态扫描**（同一个行集族判据），差额＝丢行面——如实落机读 payload（不静默）；
    拦截与补如实注记归 `verification` 行为 11（同一界线、同一口径：`delivered_rows`／`obs_rows`）。
    """
    branch = rowset_seqs(by_index)
    return {
        PAYLOAD_ENGINE_ROWS_KEY: len(branch),
        PAYLOAD_DELIVERED_ROWS_KEY: len([seq for seq in branch if seq in set(delivered_seqs)]),
    }

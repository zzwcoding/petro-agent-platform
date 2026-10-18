"""V2-107 相对窗（降级版）：答案日期标注＝实际取数窗（单点真源 `query.domain.TimeWindow.label`）。

票面＝`tickets/v2/V2-107-相对窗标注即实际窗.md`（依据 `design/统筹方案-供给窗口.md` §二 V2-107）。
**只落一条不变量**：答案里出现的日期标注必须＝**实际取数窗**（单点真源
`appv2/query/domain.py::TimeWindow.label`），**不许沿用用户原词**——「昨天（2026-08-30）」式
（把改绑日标成用户词）＝违规形。**不做**冻结日/水位机制（已裁略过）；**不改**时间解析算法
（`parse_time_window` 逐字不动——用例 9 钉行为）。

**红→绿面**：`answering.degradation.annotate_window_label`（本票新件）与血缘载荷
`LINEAGE_WINDOW_LABEL_KEY`（本票 additive 键）在实现前不存在 ⇒ 用例 1／2／3／8 红；
实现后 Q10／Q14 形正文零「用户词（日期）」形、改为 `实际取数窗：{TimeWindow.label}`。

**单点真源断言**（验收 2）：日期标注只来自 `TimeWindow.label`——①读回与生产同文件同源
（`lineage_filter_window_label(lineage_filter_line(window)) == window.label` 往返）；
②标注模板在 runtimev2 面内恰一处定义、恰一处消费；③载荷键在 appv2 生产面恰一处写入。
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

import appv2.runtimev2.answering as answering
from appv2.query import (
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_FILTER,
    LINEAGE_KEY_WATERMARK,
    RECENT_TIME_WORDS,
    RELATIVE_TIME_WORDS,
    LineageLine,
    QueryOutcome,
    QueryPlan,
    TimeWindow,
    lineage_filter_window_label,
    parse_time_window,
)
from appv2.query.domain import fill_window_label, lineage_filter_line
from appv2.runtimev2.answering import (
    MODEL_CALLER,
    AnswerDraft,
    annotate_window_label,
    answer,
    relative_time_word,
)
from appv2.runtimev2.answering import constants as answering_constants
from appv2.runtimev2.context import DEFAULT_MAX_OBSERVATIONS
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EventBus
from appv2.tools import RECENT_TIME_WORDS as TOOLS_RECENT_TIME_WORDS
from appv2.tools import RELATIVE_TIME_WORDS as TOOLS_RELATIVE_TIME_WORDS
from appv2.tools import handlers
from appv2.tools.schema import LINEAGE_WINDOW_LABEL_KEY, LOCATOR_PAYLOAD_KEY

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
_ANSWERING_DIR = _V2_DIR / "answering"

# Q10 形（EB11-C-Q10 帧）：问句「昨天」、草案「N-01 井昨天（2026-08-30）…」、
# 实际取数窗＝`fill_window_label` 按半开区间补标的日期区间（真机血缘③同形）。
_Q10_QUESTION = "帮我整三个数：N-01昨天产油多少、Z-16含水多少、咱区块这月完成率多少。"
_Q10_DRAFT = "**① N-01 昨天产油**\nN-01 井昨天（2026-08-30）日产油量 18.71 吨 [1]。"
_Q10_WINDOW = fill_window_label(
    TimeWindow(start=date(2026, 8, 30), end=date(2026, 8, 31), label="")
)
# Q14 形（EB11-C-Q14 帧）：问句「最近」、澄清后窗＝[2026-08-29, 2026-08-31)、
# 草案把窗尾写成含端「2026-08-31」并用「近 3 天窗」沿用用户词。
_Q14_QUESTION = "N-01 井最近的生产产量情况。"
_Q14_DRAFT = "- 近 3 天窗（2026-08-29～2026-08-31）内仅 08-29 一天有 N-01 数据。"
_Q14_WINDOW = fill_window_label(
    TimeWindow(start=date(2026, 8, 29), end=date(2026, 8, 31), label="")
)


# ── fixture：观察面（血缘卡＋行集——经生产装配单点 `handlers._rows_observations`）──


def _lineage_obs(
    index: int, *, label_window: TimeWindow, rows: tuple[dict[str, Any], ...] = ()
) -> list[dict[str, Any]]:
    """血缘卡＋行集观察（生产装配单点产出——载荷键与内容逐字同真机形）。"""
    outcome = QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=rows,
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_FILTER, value=lineage_filter_line(label_window)),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )
    plan = QueryPlan(
        metric_slot="日产油量（吨）",
        window_start=label_window.start,
        window_end=label_window.end,
        limit=None,
        ranking=False,
        actor="laowang",
    )
    observations = handlers._rows_observations(outcome, plan=plan)
    return [
        {
            "index": index + position,
            "locator": dict(obs.locator),
            "content": obs.content,
            "source": obs.source,
            "source_id": obs.source_id,
            "version": obs.version,
            "freshness": obs.freshness,
            "scope": obs.scope,
            "well": obs.well,
        }
        for position, obs in enumerate(observations)
    ]


def _state(**overrides: Any) -> RunState:
    values: dict[str, Any] = {
        "run_id": "run-v107-01",
        "question": _Q10_QUESTION,
        "actor": "laowang",
    }
    values.update(overrides)
    return RunState(**values)


def _agg_row_obs(index: int) -> dict[str, Any]:
    """行集观察（N-01 08-30 日产油量 18.71——Q10 帧 obs[1] 同形）。"""
    return {
        "index": index,
        "locator": {"kind": "agg_row", "well_id": "N-01", "prod_date": "2026-08-30"},
        "content": "井号=N-01；日期=2026-08-30；日产油量（吨）=18.71",
        "source": "agg.fct_daily_metering",
        "well": "N-01",
        "source_id": "N-01@2026-08-30",
        "version": None,
        "freshness": "",
    }


@contextmanager
def _phase(*replies: str) -> Any:
    """剧本化 completer（同面替身，离线零触网）＋ per-run 总线。"""
    completer = ScriptedCompleter({MODEL_CALLER: list(replies)})
    previous = set_completer(completer)
    try:
        yield EventBus()
    finally:
        set_completer(previous)


# ── 验收 2：单点真源（`TimeWindow.label` 唯一来源）──────────────────────────────


def test_lineage_filter_label_round_trip() -> None:
    """血缘③行只读反解＝`TimeWindow.label` 原文（生产／读回同文件同源——单点真源面）。"""
    windows = (
        _Q10_WINDOW,
        _Q14_WINDOW,
        TimeWindow(start=date(2026, 8, 1), end=date(2026, 8, 31), label="本月至今"),
        TimeWindow(
            start=date(2026, 7, 26), end=date(2026, 8, 25), label="最近 30 天（默认）",
            is_default=True,
        ),
    )
    for window in windows:
        assert lineage_filter_window_label(lineage_filter_line(window)) == window.label
    # 形不符＝空串（不猜、不回落正文）
    assert lineage_filter_window_label("") == ""
    assert lineage_filter_window_label("时间＝昨天（没有区间标记）") == ""


def test_window_label_payload_key_additive_single_write() -> None:
    """血缘载荷 additive `window_label` 键＝实际窗标签（值只来自血缘③行的 label 位）。"""
    observations = _lineage_obs(51, label_window=_Q10_WINDOW)
    lineage = [obs for obs in observations if obs["locator"]["kind"] == "lineage"]
    assert len(lineage) == 1
    payload = lineage[0]["locator"][LOCATOR_PAYLOAD_KEY]
    assert payload[LINEAGE_WINDOW_LABEL_KEY] == _Q10_WINDOW.label
    # 五要素子键面零漂移（additive 兄弟键——不并进 lineage 子映射）
    assert LINEAGE_KEY_FILTER in payload["lineage"]
    assert LINEAGE_WINDOW_LABEL_KEY not in payload["lineage"]


# ── 验收 1：Q10／Q14 形离线复现（不出现「用户词（日期）」；改为实际窗标注）────────


def test_q10_shape_no_user_word_date_form() -> None:
    """Q10 形：正文零「昨天（2026-08-30）」；改为 `实际取数窗：{实际窗标签}`＋原问法对照。"""
    out = annotate_window_label(_Q10_DRAFT, label=_Q10_WINDOW.label, question=_Q10_QUESTION)
    assert "昨天（2026-08-30）" not in out
    assert f"实际取数窗：{_Q10_WINDOW.label}" in out
    assert "你问的「昨天」" in out
    # 数值与其余字面零改（只动标注位）
    assert "18.71 吨 [1]" in out
    assert out.startswith("**① N-01 昨天产油**\n")  # 无日期括注的行不入面


def test_q14_shape_window_tail_is_exclusive_end() -> None:
    """Q14 形：`近 3 天窗（2026-08-29～2026-08-31）` → 实际窗标签（含端口径如实）。"""
    out = annotate_window_label(_Q14_DRAFT, label=_Q14_WINDOW.label, question=_Q14_QUESTION)
    assert "（2026-08-29～2026-08-31）" not in out
    assert f"实际取数窗：{_Q14_WINDOW.label}" in out
    assert "你问的「最近」" in out
    assert out.startswith("- ")
    assert out.endswith("内仅 08-29 一天有 N-01 数据。")


def test_relative_time_word_from_question() -> None:
    """用户原词识别（只识别不解析——解析单点仍在 `parse_time_window`）。"""
    assert relative_time_word(_Q10_QUESTION) == "昨天"
    assert relative_time_word(_Q14_QUESTION) == "最近"
    assert relative_time_word("N-01 近 3 天产量") == "近 3 天"
    assert relative_time_word("N-01 井日产油量是多少") == ""


# ── 零改面（不误伤：不是日期标注／不是同族词／无实际窗／多窗不可归属）────────────


def test_no_rewrite_when_label_equals_user_word() -> None:
    """标注词＝实际窗标签 ⇒ 零改（本就用实际窗——不重复标注）。"""
    text = "N-01 井近 3 天（2026-10-15～2026-10-17）日产油量 18.71 吨。"
    out = annotate_window_label(text, label="近 3 天", question="N-01 近 3 天产量")
    assert out == text


def test_no_rewrite_without_user_time_word_or_label() -> None:
    """无用户时间词／无实际窗 ⇒ 零改（不猜、不标注）。"""
    text = "N-01 井昨天（2026-08-30）日产油量 18.71 吨。"
    assert annotate_window_label(text, label=_Q10_WINDOW.label, question="N-01 产量") == text
    assert annotate_window_label(text, label="", question=_Q10_QUESTION) == text


def test_no_rewrite_for_other_window_words() -> None:
    """异族时间词标注零改（问「昨天」不得把「上月」标注也改绑成本窗）。"""
    text = "对比参考：上月（2026-09-01～2026-09-30）全区日产油量。"
    out = annotate_window_label(text, label=_Q10_WINDOW.label, question=_Q10_QUESTION)
    assert out == text


def test_no_rewrite_when_paren_is_not_a_window() -> None:
    """括注非纯日期表达式（含量值/说明）＝不是日期标注 ⇒ 零改。"""
    text = "N-01 井昨天（2026-08-30 日产油量 18.71 吨）的数据。"
    out = annotate_window_label(text, label=_Q10_WINDOW.label, question=_Q10_QUESTION)
    assert out == text
    # 半角括号同判据
    half = "N-01 井昨天(2026-08-30)日产油量 18.71 吨。"
    out = annotate_window_label(half, label=_Q10_WINDOW.label, question=_Q10_QUESTION)
    assert "昨天(2026-08-30)" not in out
    assert f"实际取数窗：{_Q10_WINDOW.label}" in out


# ── 接线面：答案相位起草即改（交付面正文——非仅材料面）────────────────────────


async def test_draft_face_rewritten_end_to_end() -> None:
    """端到端：`answer` 起草面即改写（state.draft 与 text 帧同源——交付面零旧形）。"""
    observations = _lineage_obs(
        51,
        label_window=_Q10_WINDOW,
        rows=({"well_id": "N-01", "日产油量（吨）": "18.71"},),
    )
    observations.insert(
        0,
        {
            "index": 1,
            "locator": {"kind": "agg_row", "well_id": "N-01", "prod_date": "2026-08-30"},
            "content": "井号=N-01；日期=2026-08-30；日产油量（吨）=18.71",
            "source": "agg.fct_daily_metering",
            "well": "N-01",
            "source_id": "N-01@2026-08-30",
            "version": None,
            "freshness": "",
        },
    )
    state = _state(observations=observations)
    with _phase(_Q10_DRAFT) as bus:
        draft = answer(
            state, bus=bus, max_observations=DEFAULT_MAX_OBSERVATIONS, supplements=[]
        )
    assert isinstance(draft, AnswerDraft)
    assert "昨天（2026-08-30）" not in state.draft
    assert f"实际取数窗：{_Q10_WINDOW.label}" in state.draft
    face = "\n".join(segment.text for segment in draft.segments)
    assert "昨天（2026-08-30）" not in face
    assert f"实际取数窗：{_Q10_WINDOW.label}" in face


async def test_multiple_distinct_labels_not_attributed() -> None:
    """多窗不可归属（两个不同实际窗标签）⇒ 不改写（不猜哪个窗是这一句的）。"""
    observations = _lineage_obs(51, label_window=_Q10_WINDOW)
    observations += _lineage_obs(60, label_window=_Q14_WINDOW)
    state = _state(observations=observations)
    with _phase(_Q10_DRAFT) as bus:
        answer(state, bus=bus, max_observations=DEFAULT_MAX_OBSERVATIONS, supplements=[])
    assert "昨天（2026-08-30）" in state.draft


async def test_rewritten_annotation_survives_verification() -> None:
    """改写后的标注行过核验**不删**（交付面实际可达——非「改了又被核验删」）。"""
    from appv2.runtimev2.verification import verify

    observations = [_agg_row_obs(1), *_lineage_obs(51, label_window=_Q10_WINDOW)]
    draft = annotate_window_label(
        _Q10_DRAFT, label=_Q10_WINDOW.label, question=_Q10_QUESTION
    )
    state = _state(observations=observations, draft=draft)
    verdict = verify(state, bus=EventBus())
    assert verdict.ok is True
    assert f"实际取数窗：{_Q10_WINDOW.label}" in state.draft
    assert "18.71" in state.draft
    assert "昨天（2026-08-30）" not in state.draft


# ── 单点面（AST 扫描：模板恰一处定义／恰一处消费；解析算法零改）──────────────


def _v2_sources() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_V2_DIR.rglob("*.py"))
    ]


def _assign_sites(sources: list[tuple[Path, ast.Module]], name: str) -> list[str]:
    sites: list[str] = []
    for path, tree in sources:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                continue
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                sites.append(path.name)
    return sites


def _def_sites(sources: list[tuple[Path, ast.Module]], name: str) -> list[str]:
    return [
        path.name
        for path, tree in sources
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]


def _name_uses(path: Path, name: str) -> int:
    """文件内名字位点（定义／读取皆计——载荷键面收口判据）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(
        1 for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == name
    )


def test_window_annotation_single_point() -> None:
    """标注模板 runtimev2 面内恰一处定义、恰一处消费；标注函数恰一处定义。"""
    sources = _v2_sources()
    assert sources, "扫描面为空——看守失效"
    assert _assign_sites(sources, "ANSWER_WINDOW_ANNOTATION_TEMPLATE") == ["constants.py"]
    assert _def_sites(sources, "annotate_window_label") == ["degradation.py"]
    template_uses = [
        path.name
        for path, _tree in sources
        if path.name != "constants.py" and _name_uses(path, "ANSWER_WINDOW_ANNOTATION_TEMPLATE")
    ]
    assert template_uses == ["degradation.py"]
    # 载荷键面收口：`tools/schema.py` 定义、`tools/handlers.py` 装配恰一处、
    # `answering/core.py` 只读恰一处——全仓 appv2 无第三处引用（禁第二份字面/第二读面）。
    key = "LINEAGE_WINDOW_LABEL_KEY"
    appv2_sources = sorted((_REPO_ROOT / "appv2").rglob("*.py"))
    users = {
        str(path.relative_to(_REPO_ROOT)): _name_uses(path, key)
        for path in appv2_sources
        if _name_uses(path, key)
    }
    assert users == {
        "appv2/tools/schema.py": 1,  # 定义
        "appv2/tools/handlers.py": 1,  # 装配（唯一写入位点）
        "appv2/runtimev2/answering/core.py": 1,  # 只读（唯一读取位点）
    }, users
    # R6 桥接面：`appv2/tools/__init__.py` 以 import 别名＋`__all__` 字面各转出一处
    bridge = (_REPO_ROOT / "appv2" / "tools" / "__init__.py").read_text(encoding="utf-8")
    assert bridge.count(key) == 2, bridge.count(key)
    # 相对时间词闭世界字面**不在** answering 代码面（本块行 19 禁语义词表——只经 tools 包根
    # 转出）；answering 面 AST 扫描闸＝`test_v2_answering.py`
    # `::test_no_lexicon_or_regex_in_answering`。


def test_relative_words_mirror_parser() -> None:
    """标注面相对词闭世界＝解析面识别词集的只读镜像（解析单点仍在 `parse_time_window`）。

    词表真源＝`appv2.query.domain`「相对时间词闭世界」节，经 `appv2.tools` 包根只读转出
    （R6 桥接）——`answering` 侧零第二份字面（AST 扫描面见 `test_window_annotation_single_point`）。
    """
    today = date(2026, 10, 18)
    assert TOOLS_RELATIVE_TIME_WORDS == RELATIVE_TIME_WORDS
    assert TOOLS_RECENT_TIME_WORDS == RECENT_TIME_WORDS
    assert set(RECENT_TIME_WORDS) <= set(RELATIVE_TIME_WORDS)
    for word in RELATIVE_TIME_WORDS:
        status, _window = parse_time_window(f"N-01 {word}产量", today=today)
        assert status != "missing", word
    for word in ("昨天", "前天", "今天", "本月", "这个月", "上个月", "上月", "今年", "去年"):
        assert word in RELATIVE_TIME_WORDS, word
    for word in ("最近", "近期", "近日"):
        assert word in RELATIVE_TIME_WORDS, word
        assert parse_time_window(f"N-01 {word}产量", today=today)[0] == "vague"


def test_parse_time_window_algorithm_unchanged() -> None:
    """验收 3：时间解析算法零改（本票只读引用 label，不改解析）。"""
    today = date(2026, 10, 18)
    assert parse_time_window("N-01 昨天产量", today=today)[1].label == "昨天"
    assert parse_time_window("N-01 近 3 天产量", today=today)[1].label == "近 3 天"
    assert parse_time_window("N-01 最近产量", today=today) == ("vague", None)
    assert parse_time_window("N-01 产量", today=today) == ("missing", None)
    window = parse_time_window("N-01 昨天产量", today=today)[1]
    assert (window.start, window.end) == (date(2026, 10, 17), date(2026, 10, 18))


def test_annotate_window_label_exported_on_public_face() -> None:
    """本件经包根公开（消费方只经 `appv2.runtimev2.answering` 消费——R2）。"""
    assert answering.annotate_window_label is annotate_window_label
    assert answering_constants.RECENT_TIME_GROUP == "recent"

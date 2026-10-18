"""context 块验收（RT-W3-02a：骨架＋六函数功能行为簇＋4 条 pin 行；RT-W3-02b：元面与边界簇）。

票面对象＝`specs/context.md`「验收测试」表全 21 行（逐字，测试标识同规格列——
`test_` 前缀为本仓 pytest 收集口径，其余逐字一致；`#` 保留规格表行序、不重编）：
第 1–12、19 行＝`RT-W3-02a-context.md`（骨架＋六函数功能行为簇＋4 条 pin 行）；
第 13–18、20、21 行＝`RT-W3-02b-context.md`（元面与边界簇——渲染器族纯函数确定性／
import 白名单与写面唯一·零帧／无词表正则／帽预算常量单点／渲染单点／零合同字面／
【边界集】／【保留集】）。两票同包顺序施工：-02b 只加固 -02a 落地的形状，
六函数签名与常量族以 -02a 为唯一真源（改形状＝回 -02a 或回设计仓）。
测试网钉＝pin-09（渲染面三落点：行 5／6／19）／pin-08（渲染帽分形面，行 4）／
pin-22（视图不改原史，行 9）／pin-30（compaction 半面，行 9）——四钉全在本票。
「钉落点对读」两行（pin-24／pin-26 不落本块）＝核实在案（本块零合同、零标记、零追加时点；
`dialogue` 写口不在本块——见 `test_ledger_load_via_tools_take_once` 尾注与测试网钉注）。

真源指针：行为 1–6／8–11＝`specs/context.md` 行为约定；渲染色字逐字稿＝
`appv2/runtime/context.py`（材料段）／`appv2/runtime/graph.py:1278-1302`（过程档案）／
`tickets/v2/V2-79d-compaction摘要化.md` §1.1／§1.2（compaction 摘要头与截数 120）；
`selected_reason` 逐字稿＝`tickets/v2/V2-61-材料承载分形渲染.md` 附 A；三来源行真源＝
`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` R-B2-05；字段形状＝`specs/state.md`。

**装载入口形＝前置核定项（未获核定）**：规格风险 5——loader 的 tools 公开面调用形未落定、
tools 装载入口形＝「阶段 5 context 施工票前置核定」（流水 43⑥）。故本件按票面「装载面只出端口＋
注入缝」施工：行 11／12 的装载语义（取一次／写回／副本／失败 fail-fast／合法空不触发失败腿）经
**注入端口**全量落绿，「经 tools 公开面」的真实现形不在本件发明（按票面停报 L0）。
"""

from __future__ import annotations

import ast
import inspect
import re
from collections.abc import Callable, Iterator, Mapping
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

from appv2.query import LINEAGE_KEY_CALIBER, LINEAGE_KEY_SOURCE
from appv2.runtimev2.answering.core import _numeric_anchor_tokens
from appv2.runtimev2.context import (
    DEFAULT_DIALOGUE_VIEW_TOKENS,
    DEFAULT_MAX_OBSERVATIONS,
    PROCESS_NOTES_BUDGET,
    RESIDENT_SOURCE_ROWS,
    TRUST_AGG,
    TRUST_LEDGER,
    TRUST_REPORT,
    LedgerLoadError,
    compact_messages,
    compile_manifest,
    load_ledger_dump,
    render_materials,
    render_process_notes,
    trust_of,
    wire_ledger_projection,
)
from appv2.runtimev2.context.materials import _KIND_TRUST, MAX_REPORT_SEATS_PER_SOURCE
from appv2.runtimev2.state import DIALOGUE_ORIGINS, RunState
from appv2.tools import (
    LINEAGE_LIMIT_HIT_KEY,
    LINEAGE_LIMIT_KEY,
    LINEAGE_LIMIT_ROWS_KEY,
    LINEAGE_PAYLOAD_KEY,
    LOCATOR_PAYLOAD_KEY,
)
from appv2.tools.schema import SEND_BUDGET_CAP

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTEXT_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "context"

# 材料段披露行逐字（`appv2/runtime/context.py` 承载位形——迁移照抄、零改写）。
_DISCLOSURE_HEAD = "（材料披露："
# 过程档案披露行逐字（`appv2/runtime/graph.py` `_render_process_notes` 承载位形）。
_PROCESS_NOTES_DISCLOSURE = "-（过程档案摘要有界截断——已渲染 {n}/{total} 条）"
# compaction 摘要头逐字（V2-79d §1.1／§1.2——截数 120 真源 A-P5b3-13）。
_SUMMARY_HEAD = "（前情摘要——旧轮原文已压缩，完整原史在会话档案可查）"
# 装载失败稳定提示（fail-fast——行为 11；用户面帧面归发射方）。
_FAILURE_HINT = "台账投影装载失败——本轮无法取得台账材料，run 已失败收场（未带缺台账的投影续跑）"

# 合同／相位包条目标记（非对话来源——结构化标记键 `origin`，永不摘除）。
_PHASE_CONTRACT_ORIGIN = "phase_contract"


def _obs(
    index: int,
    kind: str,
    *,
    content: str = "正文",
    source: str = "",
    well: str = "",
    source_id: str = "",
    version: str | None = None,
) -> dict[str, Any]:
    """观察 fixture（材料面字段形——`index`／`locator.kind`／`source`／`well`／`content`）。"""
    return {
        "index": index,
        "locator": {"kind": kind},
        "content": content,
        "source": source,
        "well": well,
        "source_id": source_id,
        "version": version,
    }


def _indices(text: str) -> list[int]:
    """渲染文本中的 `[n]` 引标序号列（块形 `[{index}]（` 抽取）。"""
    return [int(m) for m in re.findall(r"\[(\d+)\]（", text)]


def _machine_fields(meta: Mapping[str, Any]) -> dict[str, Any]:
    """三机检字段面（V2-93 起 `render_materials` 元数据另携 additive `window_materials` 键——
    三字段口径与逐字值零改，本取法只把断言面收窄到那三键）。"""
    return {
        key: meta[key]
        for key in ("material_truncated", "material_rendered", "material_total")
    }


def _fragments(count: int, *, start: int = 1, source_count: int = 5) -> list[dict[str, Any]]:
    """检索片段 fixture（按 `source_count` 轮转分源——V2-86 起单来源有席位上限
    `MAX_REPORT_SEATS_PER_SOURCE`，故帽面 fixture 不得落在单一来源，否则「检索族帽」与
    「单来源席位上限」两个数值在本 fixture 上不可分辨；分源后 `source_id` 仍逐支唯一）。"""
    return [
        _obs(
            start + i,
            "fragment",
            content=f"检索片段{i}",
            source=f"kb-{i % source_count}",
            source_id=f"kb-{i}",
        )
        for i in range(count)
    ]


def _lineage_obs(
    index: int,
    *,
    caliber: str = "日产油量（单位：吨）——指标台账注册声明：日产油量（吨），口径随答案标注",
    source_table: str = "agg.fct_daily_metering（agg 星型读模型 ⋈ 井维度 ⋈ 日期维度）",
    limit_hit: bool = False,
    limit_rows: int = 0,
) -> dict[str, Any]:
    """血缘卡观察 fixture（2026-10-17 EB2 D1：`locator.payload` 结构化载荷＋五要素正文）。"""
    return {
        "index": index,
        "locator": {
            "kind": "lineage",
            "table": "agg.fct_daily_metering",
            LOCATOR_PAYLOAD_KEY: {
                LINEAGE_PAYLOAD_KEY: {
                    "① 口径": caliber,
                    "② 来源表": source_table,
                    "③ 过滤条件": "时间＝近 30 天 [2026-08-01, 2026-09-01)（默认窗）",
                    "　└（权限注入）": "数据域＝全量",
                    "④ 数据截至批次": "批次 B20260831-T3 · 汇总层水位 2026-08-31（承诺 T-1）",
                    "⑤ 收口注记": "LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200",
                },
                LINEAGE_LIMIT_KEY: {
                    LINEAGE_LIMIT_HIT_KEY: limit_hit,
                    LINEAGE_LIMIT_ROWS_KEY: limit_rows,
                },
            },
        },
        "content": (
            "① 口径 日产油量（单位：吨）——指标台账注册声明\n"
            "② 来源表 agg.fct_daily_metering\n③ 过滤条件 时间＝近 30 天\n"
            "④ 数据截至批次 批次 B20260831-T3\n⑤ 收口注记 LIMIT 50"
        ),
        "source": "agg.fct_daily_metering",
        "well": "",
        "source_id": "lineage",
        "version": None,
    }


def _context_sources() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_CONTEXT_DIR.rglob("*.py"))
    ]


class _Port:
    """装载端口替身（注入缝的测试面——真实现形待核定，见文件头注）。"""

    def __init__(self, result: Mapping[str, Any] | None) -> None:
        self.result = result
        self.calls = 0

    async def fetch(self) -> Mapping[str, Any] | None:
        self.calls += 1
        return self.result


@pytest.fixture(autouse=True)
def _reset_projection_port() -> Iterator[None]:
    wire_ledger_projection(None)
    yield
    wire_ledger_projection(None)


# ---------- 1 材料段渲染形逐字迁移（行为 1——pin-09 渲染面底座） ----------


def test_material_segment_verbatim_render() -> None:
    """行 1 材料段渲染形逐字迁移：段头／块形／空段跳过／空材料「（无）」（行为 1）。"""
    text, meta = render_materials(
        [
            _obs(7, "metric", content="日产油量（吨）：21.16", source="台账·指标", well="K12-3"),
        ],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    # 段头逐字＋块形：index＝观察自带全局序号（非渲染位次）、label＝信任级｜来源｜井
    assert text == "\n观察材料：\n[7]（ledger｜台账·指标｜K12-3）日产油量（吨）：21.16"
    assert text.startswith("\n观察材料：\n")
    assert _machine_fields(meta) == {
        "material_truncated": False, "material_rendered": 1, "material_total": 1,
    }

    # 空段跳过（来源/井空白串经 `.strip()` 归一后跳过——只剩信任级段）
    blank, _ = render_materials(
        [_obs(1, "graph", content="图谱无锚边", source="  ", well="")],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert "观察材料：\n[1]（report）图谱无锚边" in blank

    # `content` 缺失＝空串（现状缺省——真源 R-K-20）
    missing, _ = render_materials(
        [{"index": 2, "locator": {"kind": "term"}}], max_observations=DEFAULT_MAX_OBSERVATIONS
    )
    assert missing == "\n观察材料：\n[2]（ledger）"

    # 空材料集正文＝逐字「（无）」
    empty, empty_meta = render_materials([], max_observations=DEFAULT_MAX_OBSERVATIONS)
    assert empty == "\n观察材料：\n（无）"
    assert _machine_fields(empty_meta) == {
        "material_truncated": False, "material_rendered": 0, "material_total": 0,
    }

    # 三段全空＝空括号（）：迁移照抄保留该写法，公开面无可达入口（信任级段恒非空——
    # 闭世界查表恒返三档之一）＝死分支，现状固有、迁移不修（规格行为 1 原注）。
    for kind in ("agg_row", "metric", "fragment"):
        assert trust_of({"locator": {"kind": kind}}) != ""

    # 错误契约：`index` 缺失／非整数形（观察面形态违约）→ 抛参数错误（V1 裸 KeyError 收口）
    with pytest.raises(ValueError):
        render_materials([{"locator": {"kind": "term"}}], max_observations=24)
    with pytest.raises(ValueError):
        render_materials(
            [{"index": "缺形", "locator": {"kind": "term"}}], max_observations=24
        )


# ---------- 1b 血缘卡＝口径行（2026-10-17 EB2 D1——材料面瘦身） ----------


def test_lineage_lineage_renders_caliber_line_only() -> None:
    """血缘卡不进五要素全文，原位渲染一行口径行（EB2 D1；原料＝结构化载荷）。

    判据三条：①口径行逐字（①口径原文｜来源：②来源表原文）；②五要素全文零进窗
    （材料面瘦身即此面）；③血缘 observation 帧仍全量下发（前端核验面不受损——
    帧面判据落 `test_v2_execution`）。
    """
    text, meta = render_materials(
        [_lineage_obs(2)], max_observations=DEFAULT_MAX_OBSERVATIONS
    )
    assert text == (
        "\n观察材料：\n"
        "[2]（authoritative｜agg.fct_daily_metering）"
        "【口径】日产油量（单位：吨）——指标台账注册声明：日产油量（吨），口径随答案标注"
        "｜来源：agg.fct_daily_metering（agg 星型读模型 ⋈ 井维度 ⋈ 日期维度）"
    )
    # 五要素全文与工程腔行标零进窗（③过滤／④批次／⑤收口＋权限注入行皆不在）
    for owed in ("③ 过滤条件", "④ 数据截至批次", "⑤ 收口注记", "└（权限注入）", "LIMIT 50"):
        assert owed not in text, owed
    assert meta["material_rendered"] == 1 and meta["material_truncated"] is False


def test_lineage_limit_hit_appends_cap_suffix() -> None:
    """LIMIT 触顶（结构化载荷 `limit.hit`）→ 口径行尾缀「本次封顶前 N 行」（EB2 D1）。"""
    hit, _ = render_materials(
        [_lineage_obs(2, limit_hit=True, limit_rows=50)],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert hit.endswith("｜本次封顶前 50 行")
    # 未触顶＝零尾缀（不报无关数）
    miss, _ = render_materials(
        [_lineage_obs(2, limit_hit=False, limit_rows=50)],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert "本次封顶前" not in miss


def test_lineage_without_payload_renders_empty_not_fulltext() -> None:
    """载荷缺位（旧形／形态违约）＝空串——不回落五要素全文、不解析正文文本串（EB2 D1）。"""
    text, _ = render_materials(
        [
            _obs(
                2,
                "lineage",
                content="① 口径 日产油量（单位：吨）\n② 来源表 agg.fct_daily_metering",
                source="agg.fct_daily_metering",
            )
        ],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert text == "\n观察材料：\n[2]（authoritative｜agg.fct_daily_metering）"
    assert "① 口径" not in text and "来源表" not in text
    # 五要素合同键＝口径行取值指针真源（本块 R1 不能引 query，故以字面落此并在此钉同值）
    obs = _lineage_obs(2)
    lineage = obs["locator"][LOCATOR_PAYLOAD_KEY][LINEAGE_PAYLOAD_KEY]
    assert LINEAGE_KEY_CALIBER in lineage and LINEAGE_KEY_SOURCE in lineage


# ---------- 2 信任级映射闭世界＋notice 排除（行为 2） ----------


def test_trust_mapping_closed_world() -> None:
    """行 2 十 kind 三族、异常输入落 `report`、notice 排除（行为 2）。"""
    closed = {
        "agg_row": TRUST_AGG,
        "lineage": TRUST_AGG,
        "metric": TRUST_LEDGER,
        "term": TRUST_LEDGER,
        "object": TRUST_LEDGER,
        "relation": TRUST_LEDGER,
        "family": TRUST_LEDGER,
        "fragment": TRUST_REPORT,
        "graph": TRUST_REPORT,
    }
    for kind, trust in closed.items():
        assert trust_of({"locator": {"kind": kind}}) == trust, kind
    # V2-105（D-d′）｜台账族五键＝**生产实点 `locator.kind`**（真源
    # `appv2/knowledge/domain.py:28-32` `KIND_ALL`）——旧键 `family_annotation` 与生产 `family`
    # 永不匹配（族标注卡信任级落默认＝活缺陷），本票改键。
    assert {"metric", "term", "object", "relation", "family"} <= set(_KIND_TRUST)
    assert "family_annotation" not in _KIND_TRUST
    assert _KIND_TRUST["family"] == TRUST_LEDGER
    # notice 名义入表（material 段整体排除）
    assert trust_of({"locator": {"kind": "notice"}}) == "notice"
    # 三种异常输入统一落 report（不抛错）
    assert trust_of({}) == TRUST_REPORT
    assert trust_of({"locator": {}}) == TRUST_REPORT
    assert trust_of({"locator": {"kind": "未登记"}}) == TRUST_REPORT

    # notice 排除：不进渲染文本、不计任何计数
    text, meta = render_materials(
        [
            _obs(1, "agg_row", content="合计 100"),
            _obs(2, "notice", content="窗口缺参反问（元信息）"),
        ],
        max_observations=DEFAULT_MAX_OBSERVATIONS,
    )
    assert "[2]" not in text and "元信息" not in text
    assert _machine_fields(meta) == {
        "material_truncated": False, "material_rendered": 1, "material_total": 1,
    }


# ---------- 3 排序＝信任级稳定序（行为 3） ----------


def test_trust_order_stable() -> None:
    """行 3 同 rank 保持入栈序、两跑同序（行为 3）。"""
    observations = [
        _obs(1, "fragment"),
        _obs(2, "metric"),
        _obs(3, "graph"),
        _obs(4, "agg_row"),
        _obs(5, "term"),
        _obs(6, "lineage"),
    ]
    text, _ = render_materials(observations, max_observations=DEFAULT_MAX_OBSERVATIONS)
    # 权威（4、6）→ 台账（2、5）→ 检索（1、3）；组内保持入栈序
    assert _indices(text) == [4, 6, 2, 5, 1, 3]
    assert render_materials(observations, max_observations=DEFAULT_MAX_OBSERVATIONS)[0] == text


# ---------- 4 分承载体预算：权威/台账全量无帽、检索族超帽才截断（行为 4——pin-08） ----------


def test_carrier_fractal_budget() -> None:
    """行 4 pin-08 渲染帽分形面（行为 4）。"""
    # 权威/台账族超帽 → 全量渲染、零披露、material_truncated=False
    authority = [
        _obs(i + 1, "agg_row", content=f"行 {i + 1}", source="agg.fct_daily_metering")
        for i in range(40)
    ]
    text, meta = render_materials(authority, max_observations=24)
    assert len(_indices(text)) == 40
    assert _DISCLOSURE_HEAD not in text
    assert _machine_fields(meta) == {
        "material_truncated": False, "material_rendered": 40, "material_total": 40,
    }

    # 检索族超帽 → 只渲染帽内支、披露在场（帽只作用检索族）
    text, meta = render_materials(_fragments(30), max_observations=24)
    assert len(_indices(text)) == 24
    assert _DISCLOSURE_HEAD in text
    assert _machine_fields(meta) == {
        "material_truncated": True, "material_rendered": 24, "material_total": 30,
    }


# ---------- 4b 检索族席位选择：来源轮转＋锚席位＋单来源上限（行为 4——V2-86） ----------


def _source_obs(index: int, source: str, *, content: str = "") -> dict[str, Any]:
    """检索片段 fixture（来源段可辨——席位选择按 `source` 分源）。"""
    return _obs(
        index,
        "fragment",
        content=content or f"{source} 片段 {index}",
        source=source,
        source_id=f"{source}-{index}",
    )


def test_reports_every_source_gets_a_seat() -> None:
    """行 4b-1 来源保底席＋来源轮转：每来源至少一席、总席不越帽（行为 4——V2-86）。

    朴素前缀截断下 B／C 两来源零席（A×8 吃满 6 席）——本判据正是 EB7「已检索到但被帽裁掉」的
    供给窗口选择面。
    """
    reports = [
        *[_source_obs(1 + i, "A") for i in range(8)],
        *[_source_obs(21 + i, "B") for i in range(2)],
        *[_source_obs(31 + i, "C") for i in range(2)],
    ]
    text, meta = render_materials(reports, max_observations=6)
    seats = _indices(text)
    # 总帽不变：席位不越帽（三字段口径亦不变——检索族超帽＝截断）
    assert len(seats) == 6
    assert meta["material_rendered"] == 6
    assert meta["material_total"] == 12
    assert meta["material_truncated"] is True
    # 三来源各至少一席（判据面＝块标签的来源段）
    for source in ("A", "B", "C"):
        assert f"（report｜{source}）" in text, f"来源 {source} 零席"


def test_reports_anchor_seat_wins_over_source_order() -> None:
    """行 4b-2 锚席位优先于朴素轮转：锚点只在 C 来源第 7 支 → 该支入选（行为 4——V2-86）。

    cap=6 且 A／B／C 三来源各至少一席 → 轮转补席只走到 A2／B2；锚席位先占，故 C 的第 7 支
    （唯含题面数值「16.5」者）进窗；无锚点同 fixture 该支不进窗（对照面）。
    """
    reports = [
        *[_source_obs(1 + i, "A") for i in range(3)],
        *[_source_obs(11 + i, "B") for i in range(3)],
        *[_source_obs(21 + i, "C") for i in range(6)],
        _source_obs(99, "C", content="酸化后日产 16.5 吨"),
    ]
    text, meta = render_materials(
        reports, max_observations=6, anchors=(("number", "16.5"),)
    )
    seats = _indices(text)
    assert 99 in seats  # 锚席位保底：题眼片段进窗
    assert len(seats) == 6 and meta["material_rendered"] == 6
    # 对照面：同 fixture 无锚点 → 该支被席位轮转挤掉（选择确实变了「选谁」）
    naive, _ = render_materials(reports, max_observations=6)
    assert 99 not in _indices(naive)
    # 空锚点＝零变化（additive 参：缺省行为与本批前一致）
    assert naive == render_materials(reports, max_observations=6, anchors=())[0]


def test_anchor_cooccurrence_prefers_multi_anchor_fragment() -> None:
    """行 4b-5 锚共现保底（V2-90 改判）：逐锚各保一席，同分按片段长度升序→index。

    V2-90 前判据＝「不同锚串命中个数」为总分、按 `(-分, index)` 取前 `ANCHOR_SEATS` 条；V2-90
    起改判据＝**逐锚各保一席**（强锚→弱锚→数字锚）——本用例保留的意图是「多锚共现者胜单锚
    者」：cap=1 下强锚（`W-33`）先占席，只沾弱锚（`16.5`）的单锚片段让位（旧「首个命中」判据
    下先入栈的单锚者会吃掉唯一席位）。同分平手面＝片段长度升序（更短＝更具体）→ `index` 升序。
    """
    one_anchor = _source_obs(5, "报告C", content="酸化后日产 16.5 吨")
    two_anchors = _source_obs(9, "报告C", content="W-33 井酸化后日产 16.5 吨")
    text, _ = render_materials(
        [one_anchor, two_anchors],
        max_observations=1,
        anchors=(("subject", "W-33"), ("number", "16.5")),
    )
    assert _indices(text) == [9]  # 强锚独在者胜出（单锚者零强锚命中）
    # 同分平手面：等长片段按原 index 升序（确定性）
    tie_a = _source_obs(7, "报告D", content="W-33 井 16.5 吨")
    tie_b = _source_obs(3, "报告D", content="W-33 井 16.5 吨")
    tie_text, _ = render_materials(
        [tie_a, tie_b],
        max_observations=1,
        anchors=(("subject", "W-33"), ("number", "16.5")),
    )
    assert _indices(tie_text) == [3]
    # 空锚串不计、重复锚串只计一次（同一 (kind, text) 锚不虚增分数、不重复占席）
    dup_text, _ = render_materials(
        [one_anchor, two_anchors],
        max_observations=1,
        anchors=(("number", ""), ("number", "16.5"), ("number", "16.5")),
    )
    assert _indices(dup_text) == [5]  # 两片段同分（各 1）→ 同分按片段长度升序取短者


def test_reports_per_source_cap() -> None:
    """行 4b-3 单来源席位上界：单一来源 10 支、cap=24 → 至多 `MAX_REPORT_SEATS_PER_SOURCE` 席。"""
    text, meta = render_materials(
        [_source_obs(1 + i, "A") for i in range(10)], max_observations=24
    )
    seats = _indices(text)
    assert len(seats) == MAX_REPORT_SEATS_PER_SOURCE
    assert len(seats) <= MAX_REPORT_SEATS_PER_SOURCE
    assert MAX_REPORT_SEATS_PER_SOURCE < 24  # 两个数值各一点：席位上限 ≠ 检索片段帽
    assert meta["material_rendered"] == MAX_REPORT_SEATS_PER_SOURCE
    assert meta["material_total"] == 10


def test_numeric_anchor_tokens_shape_only() -> None:
    """行 4b-4 题面数字串锚点：纯字符扫描（禁 `re`）取连续数字串、去重保序、至多 12 个
    （V2-93 D8：上界 8→12——NQ-C6 题面 10 个数值须全成锚）。

    小数／千分位**保形**取原文（`12.5`／`1,000`）；百分号作形态分隔符（不并入数字串——锚点取
    数字字面，写法差异不丢召回）；汉字数字不取（无阿拉伯数字位即零 token）。
    """
    assert _numeric_anchor_tokens("12.5/16.5 MPa、1,000 吨") == ("12.5", "16.5", "1,000")
    assert _numeric_anchor_tokens("十二点五吨") == ()
    assert _numeric_anchor_tokens("2026 年 2026 月 34-8 井") == ("2026", "34", "8")
    assert _numeric_anchor_tokens("、。；：") == ()
    assert _numeric_anchor_tokens("产量 12.5%，1,000 吨") == ("12.5", "1,000")
    # 去重保序＋至多 12 个（上限＝形态面常量，不随题面数字个数膨胀）
    assert len(_numeric_anchor_tokens(" ".join(str(number) for number in range(1, 20)))) == 12
    assert _numeric_anchor_tokens("2026 与 2026 与 2026") == ("2026",)


def test_anchor_token_limit_12() -> None:
    """V2-93 D8：题面数字锚上界 8→12——题面 10 个数值全成锚（NQ-C6 形后两值不再被截）。"""
    numbers = ("11", "22", "33", "44", "55", "66", "77", "88", "99", "110")
    assert _numeric_anchor_tokens(" ".join(numbers)) == numbers
    # 上界恰为 12：13 个数值截到前 12 个（去重保序）
    many = tuple(str(number) for number in range(1, 14))
    assert _numeric_anchor_tokens(" ".join(many)) == many[:12]


# ---------- 4c 锚分边界化与逐锚席位（V2-90——行为 4） ----------


def test_numeric_anchor_no_substring() -> None:
    """行 4c-1 数字锚只做**数字 token 全等**（V2-90）：`22` 不得命中 `2200`／`4.2`／`202608`；
    `12.5` 命中 `12.5 MPa` 但不得命中 `112.5`／`12.55`（更长的数字串内）。

    判据面＝锚席位取谁：cap=1 下若子串命中生效，四支假命中者同分（各 1）→ 同分按片段长度升序
    → 最短的假命中者（`4.2`／`112.5`）先占席；token 全等下只有真命中者进锚席。
    """
    false_hits = [
        _source_obs(1, "A", content="泵挂 2200 米"),
        _source_obs(2, "B", content="冲次 4.2 次/分"),
        _source_obs(3, "C", content="月报 202608"),
    ]
    true_hit = _source_obs(9, "D", content="22 井")
    text, _ = render_materials(
        [*false_hits, true_hit], max_observations=1, anchors=(("number", "22"),)
    )
    assert _indices(text) == [9]  # 2200／4.2／202608 皆非 22 的全等 token

    # 小数锚保形：`12.5` 命中 `12.5 MPa`，不命中更长数字串（前后紧邻数字即非全等）
    decimal = [
        _source_obs(1, "A", content="含水 112.5%"),
        _source_obs(2, "B", content="密度 12.55"),
        _source_obs(9, "C", content="套压 12.5 MPa"),
    ]
    decimal_text, _ = render_materials(
        decimal, max_observations=1, anchors=(("number", "12.5"),)
    )
    assert _indices(decimal_text) == [9]


def test_well_anchor_boundary() -> None:
    """行 4c-2 井号锚边界匹配（V2-90）：`W-11` 不得命中 `W-111`；命中 `W-11 井`。

    判据面＝锚席位取谁：cap=1 下子串匹配会令 `W-111`（更短、index 更小）与 `W-11 井` 同分
    （各 3）→ 同分按片段长度升序取 `W-111`；边界匹配下只有 `W-11 井` 进锚席。
    """
    text, _ = render_materials(
        [_source_obs(1, "A", content="W-111"), _source_obs(9, "B", content="W-11 井")],
        max_observations=1,
        anchors=(("subject", "W-11"),),
    )
    assert _indices(text) == [9]  # `W-11` 后紧邻数字 `1` → 非边界，不算命中


def test_per_anchor_one_seat() -> None:
    """行 4c-3 逐锚各保一席（V2-90）：3 个锚（强/弱/数字）、帽 6 → 每锚各取一条最佳片段占席，
    不被「同源高分泛片段」按 index 挤掉（不再按 index 取前 6）。

    fixture 的判别力：数字锚 `24` 独在 index 90 一支；旧判据（不同锚串命中个数为总分、同分按
    index 取前 `ANCHOR_SEATS`）下 index 1–6 的泛片段（同含 `W-22`＋`杆断`，分 2）先吃满 6 席、
    index 90（分 1）出局；逐锚席位下 `W-22`／`杆断`／`24` 各占一席，index 90 必进窗。
    """
    cluster = [
        _source_obs(1 + i, "A", content="W-22 井杆断，泵挂 2200 米") for i in range(6)
    ]
    number_only = _source_obs(90, "B", content="24 小时内完成检泵")
    text, meta = render_materials(
        [*cluster, number_only],
        max_observations=6,
        anchors=(("subject", "W-22"), ("term", "杆断"), ("number", "24")),
    )
    seats = _indices(text)
    assert len(seats) == 6 and meta["material_rendered"] == 6
    assert 90 in seats  # 数字锚独苗占一席（旧规则被 6 支高分泛片段按 index 挤掉）
    assert 6 not in seats  # 泛片段群只取到补席所需条数，不再「按 index 取前 6」
    assert 1 in seats and 2 in seats  # 强锚／弱锚各占一席


def test_anchor_seat_ignores_per_source_cap() -> None:
    """行 4c-4 锚席不占单源上限（V2-90）：单源 8 条、锚在第 8 条、`MAX_REPORT_SEATS_PER_SOURCE=6`
    → 锚席仍先落，且该来源另有满额 6 席常规席位（锚席不计数）。

    对照面：同 fixture 无锚点 → 该来源常规席位只到第 6 条，锚片段（第 8 条）不进窗。
    """
    reports = [_source_obs(1 + i, "A") for i in range(7)] + [
        _source_obs(8, "A", content="W-22 井杆断")
    ]
    text, _ = render_materials(
        reports, max_observations=24, anchors=(("subject", "W-22"),)
    )
    seats = _indices(text)
    assert 8 in seats  # 锚席先落（不被单源上限挡）
    assert len([index for index in seats if index != 8]) == MAX_REPORT_SEATS_PER_SOURCE
    # 对照面：无锚点 → 第 8 条被单源上限挤出窗
    naive, _ = render_materials(reports, max_observations=24)
    assert 8 not in _indices(naive)
    assert _indices(naive) == [1, 2, 3, 4, 5, 6]


def test_d_you12_shape_keeps_41() -> None:
    """行 4c-5 复刻 D-诱12 形（V2-90）：锚 `W-22`／`W-24`／`杆断`／`22`／`24`；船日表片段数字
    子串误配下总分虚高、`4.1 W-22` 正文只中强锚＋弱锚 → `4.1` 正文必进窗。

    fixture 的判别力：船日表 6 支（同源 `B2608`、index 40–45）在旧判据下各得 5 分（`W-22`／
    `W-24`／`杆断`／`2200` 中的 `22`／`24 天` 子串），先吃满 6 个锚席并顶满单源上限，`4.1`
    （index 8）出局；V2-90 下逐锚席位先落、`4.1` 再经高锚分补席进窗。对照面：无锚点同 fixture
    → 单源轮转只到 index 45，`4.1` 不进窗。
    """
    ship_day = [
        _source_obs(
            40 + i, "B2608", content="九、作业队伍与船日 W-22 W-24 杆断 2200 米 24 天"
        )
        for i in range(6)
    ]
    four_one = _source_obs(
        8,
        "B2608",
        content="4.1 W-22 井抽油杆断（典型案例）W-22 井基本参数：泵挂 2200 米",
    )
    fillers = [
        _source_obs(50, "S2"),
        _source_obs(51, "S2"),
        _source_obs(60, "S3"),
        _source_obs(61, "S3"),
    ]
    anchors = (
        ("subject", "W-22"),
        ("subject", "W-24"),
        ("term", "杆断"),
        ("number", "22"),
        ("number", "24"),
    )
    reports = [*ship_day, four_one, *fillers]
    text, _ = render_materials(reports, max_observations=10, anchors=anchors)
    assert 8 in _indices(text)  # 4.1 正文进窗（旧规则下被船日表锚席＋单源上限挤出）
    # 对照面：无锚点 → 同源单源轮转只到 index 45，4.1 不进窗
    naive, _ = render_materials(reports, max_observations=10)
    assert 8 not in _indices(naive)


# ---------- 4d 题眼表/节＋原文/表格保底席（V2-93——D1/D2/D4/D8） ----------


def _seat_obs(
    index: int,
    source: str,
    *,
    content: str = "",
    node_kind: str | None = None,
    table: bool = False,
    declaration: bool = False,
) -> dict[str, Any]:
    """席位 fixture（`locator` 可携 `node_kind`／`table_bearing`／`declaration` 机读位——
    V2-93：`table_bearing` 由引擎侧打、`declaration` 由工具声明支构造点打，L3 只读标记）。"""
    row = _source_obs(index, source, content=content)
    if node_kind is not None:
        row["locator"]["node_kind"] = node_kind
    if table:
        row["locator"]["table_bearing"] = True
    if declaration:
        row["locator"]["declaration"] = True
    return row


def test_topic_table_seat_keeps_detail_row() -> None:
    """V2-93 D8／B-正2 形：题眼锚命中的**表格承载原文切片**优先占题眼表保底席——同源摘要
    （更短、`index` 更小）不得顶替（cap=1 下判别力面＝锚席取谁：旧序按片段长度升序）。"""
    decoy = _seat_obs(
        5, "《B-月报-202608》", content="443 摘要", node_kind="section_summary"
    )
    detail = _seat_obs(
        90,
        "《B-月报-202608》",
        content="检泵作业明细表\n  443 井 2026-08-01 检泵",
        table=True,
    )
    text, _meta = render_materials(
        [decoy, detail], max_observations=1, anchors=(("number", "443"),)
    )
    assert _indices(text) == [90]  # 表格承载者胜（旧序下摘要先占锚席）


def test_topic_section_seat_keeps_original() -> None:
    """V2-93 D8／NQ-C9 形：题眼节所在**原文切片**必进窗——同源节摘要挤占（帽内轮转只到
    摘要）下原文不得缺席（132 立方米／8.2 所在原文节入选）。"""
    summaries = [
        _seat_obs(
            3 + i,
            "《NQ-C9 检泵月报》",
            content="检泵作业（节摘要）",
            node_kind="section_summary",
        )
        for i in range(8)
    ]
    original = _seat_obs(
        77,
        "《NQ-C9 检泵月报》",
        content="三、作业明细：日产液 132 立方米，含水 8.2%",
        node_kind="slice",
    )
    text, _meta = render_materials(
        [*summaries, original], max_observations=4, anchors=(("term", "检泵"),)
    )
    assert 77 in _indices(text)  # 同源原文保底席（摘要不得顶替）


def test_original_over_summary_per_source() -> None:
    """V2-93 D8：同源「节摘要＋原文切片」并存 → 原文占保底席；同源常规摘要席让位。"""
    summary_hit = _seat_obs(1, "报告A", content="检泵 摘要", node_kind="section_summary")
    summary_fill = _seat_obs(2, "报告A", content="另一节摘要", node_kind="section_summary")
    original = _seat_obs(
        99, "报告A", content="原文正文：日产液 132 立方米，含水 8.2%", node_kind="slice"
    )
    text, _meta = render_materials(
        [summary_hit, summary_fill, original],
        max_observations=2,
        anchors=(("term", "检泵"),),
    )
    seats = _indices(text)
    assert 99 in seats  # 原文保底席先于同源常规席
    assert 1 in seats  # 题眼席（摘要命中锚——席位不因保底而丢）
    assert 2 not in seats  # 常规摘要席被保底挤掉（摘要不得顶替原文）


def test_declaration_not_in_report_seats() -> None:
    """V2-93 D4：身份声明支不进检索族候选、不占席、不改其余支 `[n]`（对照面＝无声明支同序）。"""
    rows = [
        _seat_obs(1, "报告A", content="正文一"),
        _seat_obs(
            2,
            "检索供给窗声明（截断显式）",
            content="共检索到 2 条材料，1 条用进了答案",
            declaration=True,
        ),
        _seat_obs(3, "报告A", content="正文二"),
    ]
    text, _meta = render_materials(rows, max_observations=24)
    assert _indices(text) == [1, 3]  # 声明支零席、其余支 [n] 与序零改
    assert "共检索到" not in text  # 声明正文不进材料段（走 note／引擎注记通道）
    without, _ = render_materials([rows[0], rows[2]], max_observations=24)
    assert _indices(without) == [1, 3]  # 对照面：声明支在场不改任何 [n]
    # notice 形声明支（工具构造点真形）照旧被整体排除（材料段＋计数面零改）
    notice_decl = _seat_obs(
        4, "检索供给窗声明（截断显式）", content="声明", declaration=True
    )
    notice_decl["locator"]["kind"] = "notice"
    notice_decl["locator"]["notice_type"] = "window_note"
    notice_text, notice_meta = render_materials([rows[0], notice_decl], max_observations=24)
    assert _indices(notice_text) == [1] and notice_meta["material_total"] == 1


# ---------- 5 截断披露行逐字在场、未截断零残留（行为 5——pin-09 之一） ----------


def test_truncation_disclosure_line_verbatim() -> None:
    """行 5 披露行逐字＋两个计数正确；未截断零残留（行为 5）。"""
    text, meta = render_materials(_fragments(30), max_observations=10)
    assert (
        "\n（材料披露：检索片段共 30 支，本轮渲染前 10 支——未渲染片段不在"
        "本轮视野，不得对其断言；权威行集与台账卡已全量渲染。）" in text
    )
    assert meta["material_truncated"] is True and meta["material_rendered"] == 10
    # 计数与元数据一致：检索支数＝总、实渲支数＝帽
    assert meta["material_total"] == 30

    clean, clean_meta = render_materials(_fragments(3), max_observations=10)
    assert _DISCLOSURE_HEAD not in clean and "截断" not in clean
    assert clean_meta["material_truncated"] is False


# ---------- 6 Manifest 三机检字段（四态）＋selected_reason 逐字（行为 6——pin-09 之二） ----------


def test_manifest_material_fields_and_reason() -> None:
    """行 6 四态三字段逐条对＋`selected_reason` 逐字（行为 6；无 compaction 态逐字）。"""
    # 零材料步（仅生于理解步——文案恒为「理解步」）
    zero = compile_manifest([], step="understand", max_observations=24)
    assert (zero.material_total, zero.material_rendered, zero.material_truncated) == (0, 0, False)
    assert zero.selected_reason == "步骤 understand：理解步零材料渲染"

    # 全量态
    full = compile_manifest(
        [*[_obs(1, "agg_row"), _obs(2, "lineage")], *_fragments(3, start=3)],
        step="answer",
        max_observations=24,
    )
    assert (full.material_total, full.material_rendered, full.material_truncated) == (5, 5, False)
    assert full.selected_reason == (
        "步骤 answer：信任级降序稳定排序；权威 2 支全量；检索片段 3 支全量（合计入选 5/5）"
    )

    # 检索截断态
    cut = compile_manifest(_fragments(5), step="answer", max_observations=2)
    assert (cut.material_total, cut.material_rendered, cut.material_truncated) == (5, 2, True)
    assert cut.selected_reason == (
        "步骤 answer：信任级降序稳定排序；权威 0 支全量；检索片段帽 2 支截断（2/5）"
        "（合计入选 2/5）"
    )

    # 权威超帽态（帽不作用权威族）
    over = compile_manifest(
        [
            _obs(i + 1, "agg_row", content=f"行 {i + 1}")
            for i in range(30)
        ],
        step="answer",
        max_observations=24,
    )
    assert (over.material_total, over.material_rendered, over.material_truncated) == (
        30,
        30,
        False,
    )
    assert over.selected_reason == (
        "步骤 answer：信任级降序稳定排序；权威 30 支全量；检索片段 0 支全量（合计入选 30/30）"
    )


# ---------- 7 每次调用 Manifest 在场且材料标来源（行为 7） ----------


def test_manifest_present_source_rows() -> None:
    """行 7 四列表同长、来源逐条对应、常驻来源行按呼叫分型、零材料亦在场（行为 7）。"""
    observations = [
        _obs(4, "agg_row", content="合计", source_id="agg.fct_daily_metering", version="v1"),
        _obs(5, "metric", content="台账卡", source_id="metric-1"),
        _obs(6, "fragment", content="片段", source_id="kb-1"),
    ]
    answer = compile_manifest(observations, step="answer", max_observations=24)
    assert answer.source_type == ["agg_row", "metric", "fragment"]
    assert answer.source_id == ["agg.fct_daily_metering", "metric-1", "kb-1"]
    assert answer.version == ["v1", None, None]
    assert answer.trust_level == [TRUST_AGG, TRUST_LEDGER, TRUST_REPORT]
    # 空串如实（图谱无锚边形——V1 事实面）
    assert answer.source_id == [
        str(obs.get("source_id", "")) for obs in observations
    ]

    # 常驻来源行按呼叫分型：decision／clarify／toolmatch 首入且投影非空 → 恰 3 行
    dump: dict[str, Any] = {"metrics": [{"slot": "日产油量"}], "cards": ["agg"]}
    for step in ("decision", "clarify", "toolmatch"):
        first = compile_manifest(observations, step=step, max_observations=24, ledger_dump=dump)
        assert len(first.source_type) == len(first.source_id) == len(first.version) == 3 + 3
        assert list(RESIDENT_SOURCE_ROWS.items()) == [
            ("ledger_dump", "ledger_full_dump"),
            ("alias_dump", "ledger_aliases"),
            ("schema_card", "schema_cards"),
        ]
        assert first.source_type[-3:] == list(RESIDENT_SOURCE_ROWS)
        assert first.source_id[-3:] == list(RESIDENT_SOURCE_ROWS.values())
        assert first.version[-3:] == [None, None, None]
        assert first.trust_level[-3:] == [TRUST_LEDGER] * 3
    # answer 轮零常驻行（ledger_dump=None）
    assert len(answer.source_type) == 3

    # 台账空投影 → 零台账来源行且材料字段不受影响
    empty_dump = compile_manifest(
        observations, step="decision", max_observations=24, ledger_dump={}
    )
    assert len(empty_dump.source_type) == 3
    assert (empty_dump.material_total, empty_dump.material_rendered) == (3, 3)

    # 零材料步 → 0/0/False 且四列表空（Manifest 仍在场）
    zero = compile_manifest([], step="understand", max_observations=24)
    assert zero.source_type == zero.source_id == zero.version == zero.trust_level == []

    # 截断态 → 来源行只含实渲支
    cut = compile_manifest(_fragments(5), step="answer", max_observations=2)
    assert len(cut.source_id) == 2 and cut.material_total == 5

    # as_dict 全键恒出（十键）
    assert set(answer.as_dict()) == {
        "source_type",
        "source_id",
        "version",
        "trust_level",
        "selected_reason",
        "token_count",
        "transform",
        "material_total",
        "material_rendered",
        "material_truncated",
    }


# ---------- 7b Manifest 来源行＝席位实投逐支（V2-86 补丁——行为 7） ----------


def test_manifest_sources_match_rendered_seats() -> None:
    """行 7b 多来源超帽 fixture → Manifest 来源四列＝`_select_reports` 实投席位的逐支序。

    判据：`manifest.source_id` 与材料段 `[n]` 序逐支对应（同源同序）；且**不等于**朴素前缀
    截断的取支序（否则本判据不可区分）；三字段与 `selected_reason` 文本零改（帽账仍按支数）。
    """
    reports = [
        *[_source_obs(1 + i, "A") for i in range(8)],
        *[_source_obs(21 + i, "B") for i in range(2)],
        *[_source_obs(31 + i, "C") for i in range(2)],
    ]
    anchors = (("term", "C 片段 32"),)
    text, meta = render_materials(reports, max_observations=6, anchors=anchors)
    manifest = compile_manifest(
        reports, step="answer", max_observations=6, anchors=anchors
    )
    by_index = {int(obs["index"]): str(obs["source_id"]) for obs in reports}
    # 逐支同源同序（Manifest 来源列＝实投席位的逐支账）
    assert manifest.source_id == [by_index[index] for index in _indices(text)]
    assert manifest.source_type == ["fragment"] * 6
    assert len(manifest.source_id) == len(manifest.source_type) == 6
    assert manifest.material_rendered == meta["material_rendered"] == 6
    assert manifest.material_truncated is meta["material_truncated"] is True
    # 非朴素前缀截断（选择确实换了「选谁」——该判据才可区分两实现）
    assert manifest.source_id != [str(obs["source_id"]) for obs in reports[:6]]
    # 三字段与 `selected_reason` 文本零改（帽账仍按「支数 > 帽」）
    assert manifest.selected_reason == (
        "步骤 answer：信任级降序稳定排序；权威 0 支全量；"
        "检索片段帽 6 支截断（6/12）（合计入选 6/12）"
    )
    # 权威/台账族恒全量在前（与 render 同形）
    with_authority = [
        _obs(90, "agg_row", content="合计", source_id="agg.fct_daily_metering"),
        *reports,
    ]
    mixed_text, _ = render_materials(with_authority, max_observations=6, anchors=anchors)
    mixed_manifest = compile_manifest(
        with_authority, step="answer", max_observations=6, anchors=anchors
    )
    mixed_by_index = {int(obs["index"]): str(obs["source_id"]) for obs in with_authority}
    assert mixed_manifest.source_id == [
        mixed_by_index[index] for index in _indices(mixed_text)
    ]
    assert mixed_manifest.source_id[0] == "agg.fct_daily_metering"


# ---------- 8 过程档案摘要段有界（行为 8） ----------


def _notes_state(count: int, *, phase: str = "decision") -> RunState:
    return RunState(
        process_notes=[
            {"phase": phase, "title": f"第 {i} 步", "digest": f"结果 {i}" * 4} for i in range(count)
        ]
    )


def test_process_notes_bounded_summary() -> None:
    """行 8 零档案零段／有界／披露行逐字／全入预算无披露（行为 8）。"""
    # 零档案＝零段（调用方跳过——首轮零噪声）
    assert render_process_notes(RunState(), budget=PROCESS_NOTES_BUDGET) == ""

    # 全入预算 → 全行、零披露行（头注逐字在场）
    full = render_process_notes(_notes_state(3), budget=PROCESS_NOTES_BUDGET)
    assert full.startswith("【本 run 已做（过程档案摘要——防重参考，不是作答材料）】\n")
    assert full.count("\n- [") == 3
    assert "有界截断" not in full

    # 超预算 → 披露行逐字＋`n` 与已渲行数一致
    bounded = render_process_notes(_notes_state(20), budget=120)
    rendered = bounded.count("\n- [")
    assert _PROCESS_NOTES_DISCLOSURE.format(n=rendered, total=20) in bounded
    assert rendered < 20

    # 两跑逐字相等（确定性）
    assert render_process_notes(_notes_state(20), budget=120) == bounded

    # phase 缺失＝`?`（现状缺省回落——迁移照抄）
    missing = render_process_notes(
        RunState(process_notes=[{"title": "无相位", "digest": "d"}]), budget=PROCESS_NOTES_BUDGET
    )
    assert "\n- [?] 无相位｜d" in missing


# ---------- 9 compaction：超窗视图（行为 9——pin-22／pin-30） ----------


def _long(tag: str, length: int) -> str:
    return tag + "字" * (length - len(tag))


def _chain() -> list[dict[str, str]]:
    """超窗链 fixture：角色红线＋相位合同包＋两轮对话＋当前轮（预算 120 下压缩第 1 轮对）。"""
    return [
        {"role": "system", "content": "角色红线", "origin": "system_redline"},
        {"role": "user", "content": "相位合同包", "origin": _PHASE_CONTRACT_ORIGIN},
        {"role": "user", "content": _long("第一轮问", 200), "origin": "user_verbatim"},
        {"role": "assistant", "content": _long("第一轮答", 200), "origin": "assistant_final"},
        {"role": "user", "content": _long("第二轮问", 200), "origin": "user_verbatim"},
        {"role": "assistant", "content": _long("第二轮答", 200), "origin": "assistant_final"},
        {"role": "user", "content": _long("本轮问", 40), "origin": "user_verbatim"},
    ]


def test_compaction_overwindow_model_view() -> None:
    """行 9 超窗视图：摘要置位／最新轮恒在场／单巨轮零压缩／合同不摘／原史零覆盖／
    披露账目（行为 9——pin-22 视图面／pin-30 compaction 半面）。
    """
    chain = _chain()
    before = deepcopy(chain)
    view, account = compact_messages(chain, dialogue_view_tokens=120)
    # 摘要＝system 消息、置于角色红线 system 之后、近期轮之前
    assert view[0] == chain[0]
    assert view[1]["role"] == "system" and view[1]["content"].startswith(_SUMMARY_HEAD)
    # 最旧对话轮对（第一轮 user＋assistant）摘要化：问原文／答首行（单行上限 120 截数）
    assert f"\n问：{_long('第一轮问', 200)[:120]}" in "\n" + view[1]["content"]
    assert f"\n答：{_long('第一轮答', 200)[:120]}" in "\n" + view[1]["content"]
    # 保留近轮逐字（第二轮对＋当前轮全量在场）
    assert view[-3:] == chain[-3:]
    # 最新轮恒在场（保留窗至少 1 轮）；合同／相位包条全数保留（原地）
    assert view[-1] == chain[-1]
    assert {"role": "user", "content": "相位合同包", "origin": _PHASE_CONTRACT_ORIGIN} in view
    # 原史零覆盖（只作用于模型视图）
    assert chain == before
    # 披露账目在场（合成位：材料面 selected_reason 之后以「；」追加）
    reason = compile_manifest([], step="answer", max_observations=24).selected_reason
    assert account == (
        "对话层 compaction：5 轮→保留 3 轮＋前情摘要（预算 120，原史在会话档案全量可查）"
    )
    assert f"{reason}；{account}".endswith(account)
    # 截数 120：摘要行单行上限（问原文截 120／答取首行截 120）
    long_chain = [
        {"role": "system", "content": "角色红线"},
        {"role": "user", "content": _long("旧问", 600), "origin": "user_verbatim"},
        {"role": "assistant", "content": _long("旧答", 600), "origin": "assistant_final"},
        {"role": "user", "content": _long("本轮问", 40), "origin": "user_verbatim"},
    ]
    capped, _ = compact_messages(long_chain, dialogue_view_tokens=20)
    summary_lines = [line for line in capped[1]["content"].split("\n") if line.startswith("问：")]
    assert len(summary_lines) == 1 and len(summary_lines[0]) == len("问：") + 120
    # 答首行取值（多行内容取首行）
    multi = [
        {"role": "system", "content": "角色红线"},
        {"role": "user", "content": _long("旧问", 200), "origin": "user_verbatim"},
        {
            "role": "assistant",
            "content": "首行答案" + "填" * 100 + "\n第二行不入摘要",
            "origin": "assistant_final",
        },
        {"role": "user", "content": _long("本轮问", 40), "origin": "user_verbatim"},
    ]
    first_line_view, _ = compact_messages(multi, dialogue_view_tokens=15)
    assert "答：首行答案" in first_line_view[1]["content"]
    assert "第二行不入摘要" not in first_line_view[1]["content"]

    # 最新轮单轮超预算仍恒在场（含单巨轮＝原样放行零压缩）
    giant = [
        {"role": "system", "content": "角色红线"},
        {"role": "user", "content": _long("巨轮", 5000), "origin": "user_verbatim"},
    ]
    giant_view, giant_account = compact_messages(
        giant, dialogue_view_tokens=DEFAULT_DIALOGUE_VIEW_TOKENS
    )
    assert giant_view == giant and giant_account == ""


# ---------- 10 compaction：预算内原样返回、披露为空（行为 10 前置——零漂移） ----------


def test_compaction_within_budget_no_drift() -> None:
    """行 10 预算内原样返回、披露为空（零漂移）；形态越界抛参数错误（行为 9／错误契约）。"""
    chain = [
        {"role": "system", "content": "角色红线"},
        {"role": "user", "content": "问", "origin": "user_verbatim"},
        {"role": "assistant", "content": "答", "origin": "assistant_final"},
    ]
    before = deepcopy(chain)
    view, account = compact_messages(chain, dialogue_view_tokens=DEFAULT_DIALOGUE_VIEW_TOKENS)
    assert view == chain and account == ""
    # 视图为副本（改视图不改入参——零写入）
    view[0]["content"] = "改"
    assert chain == before

    # 形态越界（非正整数）→ 抛参数错误，不吞错
    for illegal in (0, -1, True, "8192"):
        with pytest.raises(ValueError):
            compact_messages(chain, dialogue_view_tokens=illegal)  # type: ignore[arg-type]

    # 识别面词表＝`dialogue` 条目来源闭世界（结构化标记键 `origin`——流水 49③；零内容子串识别）
    assert DIALOGUE_ORIGINS == {"user_verbatim", "assistant_final", "clarify_approval_replay"}


# ---------- 11 投影取得：取一次、返回值副本（行为 10） ----------


async def test_ledger_load_via_tools_take_once() -> None:
    """行 11 已有投影（含空投影）零工具调用、空→恰一次取得＋写回、返回值副本（行为 10）。

    取得路径唯一＝注入端口（装载入口形待核定——见文件头注；未接线时不静默兜底，见下断言）。
    """
    dump: dict[str, Any] = {"metrics": [{"slot": "日产油量"}], "aliases": {"日产": "日产油量"}}
    port = _Port(dump)
    wire_ledger_projection(port)

    # 已有投影 → 零工具调用、原样返回
    state = RunState(ledger_dump=deepcopy(dump))
    loaded = await load_ledger_dump(state)
    assert port.calls == 0 and loaded == dump
    # 返回值副本语义（改返回值不改 state）
    loaded["metrics"] = []
    loaded["新增"] = 1
    assert state.ledger_dump == dump

    # 空投影 {}＝已取之空态（不再取）
    empty_state = RunState(ledger_dump={})
    assert await load_ledger_dump(empty_state) == {} and port.calls == 0

    # 空 state → 恰一次取得＋写回 state
    fresh = RunState()
    got = await load_ledger_dump(fresh)
    assert port.calls == 1 and fresh.ledger_dump == dump and got == dump
    got["metrics"] = []  # 副本语义（写回值与返回值互不串改）
    assert fresh.ledger_dump == dump
    # 再取一次 → 复用（仍零新调用）
    assert await load_ledger_dump(fresh) == dump and port.calls == 1

    # 取得路径唯一：未接线（注入缝空）→ 不静默兜底、不冒充已取得（fail-fast）
    wire_ledger_projection(None)
    with pytest.raises(LedgerLoadError):
        await load_ledger_dump(RunState())


# ---------- 12 取得失败＝fail-fast（行为 11） ----------


async def test_ledger_load_failure_run_failed_honest() -> None:
    """行 12 失败＝fail-fast 终局＋稳定错误提示在场＋留痕可查；合法空不触发失败腿（行为 11）。"""
    # 判据面一：工具面返回 failed 态（端口返 None）
    wire_ledger_projection(_Port(None))
    failed_state = RunState(run_id="run-fail")
    with pytest.raises(LedgerLoadError) as none_exc:
        await load_ledger_dump(failed_state)
    assert str(none_exc.value) == _FAILURE_HINT  # 稳定错误提示（机读可查的留痕载体）
    assert failed_state.ledger_dump is None  # 不写空投影、不冒充已取得（无静默兜底）

    # 判据面二：调用异常捕获面（原始异常文本只经异常链留痕，不进稳定提示）
    class _Boom:
        async def fetch(self) -> Mapping[str, Any] | None:
            raise RuntimeError("引擎 500：连接被拒")

    wire_ledger_projection(_Boom())
    with pytest.raises(LedgerLoadError) as boom_exc:
        await load_ledger_dump(RunState())
    assert str(boom_exc.value) == _FAILURE_HINT  # 两路同一稳定提示
    assert "引擎 500" not in str(boom_exc.value)
    assert boom_exc.value.__cause__ is not None and "引擎 500" in str(boom_exc.value.__cause__)

    # 合法空结果 fixture：与失败不同路（工具成功返回空 ≠ 失败——原样取得＋写回）
    port = _Port({})
    wire_ledger_projection(port)
    legal = RunState()
    assert await load_ledger_dump(legal) == {}
    assert port.calls == 1 and legal.ledger_dump == {}


# ---------- 19 截断机读信号两面在场、本块零 emit（行为 5／6／不降级节——pin-09 之三） ----------


def test_truncation_signal_no_emit() -> None:
    """行 19 披露行＋字段两面在同一次调用内同场；本块源码零 emit（行为 5／6／不降级节）。"""
    observations = _fragments(30)
    text, meta = render_materials(observations, max_observations=10)
    manifest = compile_manifest(observations, step="answer", max_observations=10)
    assert _DISCLOSURE_HEAD in text  # 模型面（a）
    assert meta["material_truncated"] is True  # 机读字段（b）
    assert manifest.material_truncated is True and "帽 10 支截断" in manifest.selected_reason

    # 本块零 emit（帧面归发射方——AST 扫描）
    sources = _context_sources()
    assert sources, "扫描面为空——看守失效"
    emit_sites = [
        (path.name, node.lineno)
        for path, tree in sources
        for node in ast.walk(tree)
        if (isinstance(node, ast.Attribute) and node.attr == "emit")
        or (isinstance(node, ast.Name) and node.id == "emit")
    ]
    assert emit_sites == [], f"本块出现 emit 位点：{emit_sites}"

    # 探测器非空转（`emit` 位点必须被抓）
    forged = ast.parse("bus.emit('notice', {})\n")
    assert [
        node.lineno
        for node in ast.walk(forged)
        if isinstance(node, ast.Attribute) and node.attr == "emit"
    ] == [1]


# ══════════════════════════════════════════════════════════════════════════════
# RT-W3-02b：元面与边界簇（规格表第 13–18、20、21 行）
#   本票只加固 -02a 落地的形状（六函数签名＋常量族）——不改值、不改形；
#   改形状＝回 -02a 或回设计仓。
# ══════════════════════════════════════════════════════════════════════════════

_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"

# 渲染器族五件（纯函数面）——**唯一 IO 面＝`load_ledger_dump` 的 tools 调用**不在其内（行为 12）。
_RENDERERS = (render_materials, render_process_notes, compile_manifest, compact_messages, trust_of)
# 渲染器族载件（扫描面钉死——`ledger.py` 是唯一 IO 面、不在纯函数扫描面内）
_RENDERER_FILES = ("compaction.py", "manifest.py", "materials.py", "process_notes.py")

# 依赖白名单＝`state`＋`tools` 两块＋**依赖自由判据单点模块 `text_tokens`**
# （V2-100 D-a：题眼 token 边界／数字全等本体单点——非 runtimev2 块、非 infra、非旧码；
# 禁引其余 runtimev2 块——红线④⑤）。
_ALLOWED_DEPENDENCY_BLOCKS = ("state", "tools", "text_tokens")
# 共享写面零写（写口归 `bookkeeping`；全块唯一状态写入＝`ledger_dump` 取一次装载——红线⑥）。
_SHARED_WRITE_FIELDS = (
    "messages",
    "steps",
    "notices",
    "process_notes",
    "dialogue",
    "next_intent",
)
_MUTATING_METHODS = (
    "append",
    "extend",
    "insert",
    "pop",
    "remove",
    "clear",
    "update",
    "setdefault",
    "add",
    "sort",
    "reverse",
)

# 行 13 判据面：零 IO／模型／时钟／随机／emit（AST）。
_FORBIDDEN_PURE_MODULES = (
    "os",
    "io",
    "sys",
    "pathlib",
    "time",
    "datetime",
    "random",
    "secrets",
    "uuid",
    "socket",
    "subprocess",
    "shutil",
    "tempfile",
    "logging",
    "asyncio",
    "threading",
    "pickle",
    "sqlite3",
    "requests",
    "httpx",
    "urllib",
)
_FORBIDDEN_BARE_CALLS = ("open", "input", "eval", "exec", "__import__", "print")
_FORBIDDEN_ATTR_CALLS = (
    "now",
    "utcnow",
    "today",
    "monotonic",
    "perf_counter",
    "time",
    "sleep",
    "choice",
    "randint",
    "shuffle",
    "uuid4",
    "emit",
)
_MODEL_CALL_NAMES = ("acomplete", "chat", "complete", "embed", "embedding", "embeddings")

# 行 15 判据面：正则族＋词表名面＋非标识符形字符串集合（语义词表的机检代理）。
_REGEX_MODULES = ("re", "regex")
_LEXICON_NAME_MARKS = ("lexicon", "wordlist", "keyword_table", "词表")
_IDENTIFIER_SHAPE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# 行 15 判定清单（逐条可指真源条目——真源 `docs/runtime-refactor/walk/判断归责表.md`；
# 全部落「闭世界查表／排序／计数／截断／字符串归一／字符截取」＝形态处理，零语义判断）。
_JUDGEMENT_INVENTORY = (
    ("materials.py", "_KIND_TRUST.get", "闭世界查表（真源 recon/K R-K-15…R-K-17）"),
    ("materials.py", "_TRUST_RANK.get", "信任级排序键闭世界（真源 R-K-05）"),
    ("materials.py", "sorted(", "稳定排序（同 rank 保持入栈序）"),
    ("materials.py", "len(reports) > max_observations", "计数＋截断（帽只作用检索族）"),
    ("materials.py", ".strip()", "字符串归一（空段判定——形态处理豁免面）"),
    ("manifest.py", "RESIDENT_SOURCE_ROWS.items()", "三来源行闭世界映射"),
    ("compaction.py", "in DIALOGUE_ORIGINS", "集合成员判定（形态处理豁免面）"),
    ("compaction.py", "[:cap]", "字符截取（摘要行单行上限——形态处理豁免面）"),
    ("process_notes.py", "total + len(line) + 1 > budget", "计数＋预算截断"),
)

# 行 17 渲染单点（runtimev2 面内各恰一处定义；`kind` ∈ `def`／`assign`）。
_RENDERER_SINGLE_POINT = (
    ("render_materials", "def", "materials.py", "材料段渲染"),
    ("render_process_notes", "def", "process_notes.py", "过程档案渲染"),
    ("trust_of", "def", "materials.py", "信任映射"),
    ("_KIND_TRUST", "assign", "materials.py", "信任级闭世界映射表"),
    ("_TRUST_RANK", "assign", "materials.py", "信任级排序映射"),
    ("_carrier_split", "def", "materials.py", "分形帽分组单点"),
    ("DEFAULT_MAX_OBSERVATIONS", "assign", "materials.py", "帽常量"),
    ("RESIDENT_SOURCE_ROWS", "assign", "manifest.py", "三来源行映射"),
    ("_PROCESS_NOTES_HEADER", "assign", "process_notes.py", "过程档案头注"),
)

# 模型面渲染文案锚（跨面唯一——消费方私存副本＝判失败。用户/审计面披露文案归发射方
# `specs/answering.md`，不在本锚列——本扫描只钉模型面渲染产物）。
_RENDER_TEXT_ANCHORS = ("观察材料：", "【本 run 已做（过程档案摘要——防重参考，不是作答材料）】")


def _v2_sources() -> list[tuple[Path, ast.Module]]:
    """V2 全块源码树（单点断言的扫描面——「runtimev2 面内恰一处定义」）。"""
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_V2_DIR.rglob("*.py"))
    ]


def _renderer_sources() -> list[tuple[Path, ast.Module]]:
    """渲染器族载件（扫描面由函数对象反查，清单漂移即红）。"""
    files = set()
    for func in _RENDERERS:
        source = inspect.getsourcefile(func)
        assert source is not None, f"{func.__name__} 源文件不可得"
        files.add(Path(source))
    assert sorted(path.name for path in files) == list(_RENDERER_FILES), sorted(files)
    return [(path, ast.parse(path.read_text(encoding="utf-8"))) for path in sorted(files)]


def _context_texts() -> dict[str, str]:
    """本块源码文本（文本级扫描面——字面命中判定用）。"""
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(_CONTEXT_DIR.rglob("*.py"))
    }


def _imported_modules(tree: ast.Module) -> list[tuple[int, str]]:
    """文件内 import 位点（`(行, 模块名)`；相对引以点号前缀记名）。"""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append((node.lineno, "." * node.level + (node.module or "")))
    return found


def _call_sites(tree: ast.Module) -> list[tuple[int, str, str]]:
    """调用位点（`(行, 形, 被调名)`；形 ∈ `bare`／`attr`）。"""
    found: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            found.append((node.lineno, "bare", node.func.id))
        elif isinstance(node.func, ast.Attribute):
            found.append((node.lineno, "attr", node.func.attr))
    return found


def _dependency_block(module: str) -> str:
    """`appv2.runtimev2.X[.…]` → `X`；其余 `appv2.…` 形 → 第二段（`infra`／`runtime` 等）。"""
    parts = module.split(".")
    if parts[:2] == ["appv2", "runtimev2"] and len(parts) >= 3:
        return parts[2]
    return parts[1] if len(parts) > 1 else module


def _is_whitelisted_import(module: str) -> bool:
    """`state`＋`tools`＋`text_tokens`（V2-100 D-a 依赖自由判据单点）＋本包自身为白名单；
    其余 `appv2.*` 一律越界。"""
    if not module.startswith("appv2"):
        return True
    block = _dependency_block(module)
    return block == "context" or block in _ALLOWED_DEPENDENCY_BLOCKS


def _emit_sites(tree: ast.Module) -> list[int]:
    """帧发射位点（`emit` 名或属性——本块零帧，帧面归发射方）。"""
    return [
        node.lineno
        for node in ast.walk(tree)
        if (isinstance(node, ast.Attribute) and node.attr == "emit")
        or (isinstance(node, ast.Name) and node.id == "emit")
    ]


def _purity_findings(sources: list[tuple[Path, ast.Module]]) -> list[str]:
    """行 13 AST 判据面：零 IO／模型／时钟／随机／emit＋零越界引块。"""
    findings: list[str] = []
    for path, tree in sources:
        for lineno, module in _imported_modules(tree):
            root = module.split(".")[0]
            if root in _FORBIDDEN_PURE_MODULES:
                findings.append(f"{path.name}:{lineno} 禁引模块 {module}")
            elif root == "appv2" and not _is_whitelisted_import(module):
                findings.append(f"{path.name}:{lineno} 越界引块 {module}")
        for lineno, kind, callee in _call_sites(tree):
            if kind == "bare" and callee in _FORBIDDEN_BARE_CALLS:
                findings.append(f"{path.name}:{lineno} 禁止调用 {callee}")
            if kind == "attr" and callee in _FORBIDDEN_ATTR_CALLS:
                findings.append(f"{path.name}:{lineno} IO／时钟／随机／帧面调用 .{callee}")
            if callee in _MODEL_CALL_NAMES:
                findings.append(f"{path.name}:{lineno} 模型调用 {callee}")
        findings.extend(f"{path.name}:{lineno} 帧面 emit" for lineno in _emit_sites(tree))
    return findings


def _import_findings(sources: list[tuple[Path, ast.Module]]) -> list[str]:
    """行 14 AST 判据面：import 白名单（只 `state`＋`tools`＋自身）。"""
    return [
        f"{path.name}:{lineno} 越界引块 {module}"
        for path, tree in sources
        for lineno, module in _imported_modules(tree)
        if not _is_whitelisted_import(module)
    ]


def _state_field(node: ast.expr) -> str | None:
    """`state.<字段>` 形（含其下标取值根）→ 字段名；其余 → None。"""
    while isinstance(node, ast.Subscript):
        node = node.value
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "state"
    ):
        return node.attr
    return None


def _state_field_write_sites(sources: list[tuple[Path, ast.Module]]) -> list[tuple[str, int, str]]:
    """`state.<字段>` 写入位点（赋值／增广／下标存／`setattr`／原地变更方法＝写面扫描面）。"""
    sites: list[tuple[str, int, str]] = []
    for path, tree in sources:
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                field = _state_field(target)
                if field is not None:
                    sites.append((path.name, node.lineno, field))
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "setattr" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Name) and first.id == "state":
                    sites.append((path.name, node.lineno, "setattr(state, …)"))
            elif isinstance(func, ast.Attribute) and func.attr in _MUTATING_METHODS:
                field = _state_field(func.value)
                if field is not None:
                    sites.append((path.name, node.lineno, f"{field}.{func.attr}()"))
    return sites


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _module_str_collections(tree: ast.Module) -> list[tuple[int, str, tuple[str, ...]]]:
    """模块级字符串集合常量（元组／列表／集合字面量与 `set|frozenset(...)`，映射取键集）。

    元素非标识符形即「自建语义词表」的机检代理（闭世界枚举取值与 `__all__` 名单都是标识符形）。
    """
    sites: list[tuple[int, str, tuple[str, ...]]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            target = node.target
        else:
            continue
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        values: tuple[str, ...] = ()
        if isinstance(value, (ast.Tuple, ast.List, ast.Set)):
            values = tuple(
                element.value
                for element in value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
        elif (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in ("set", "frozenset")
            and value.args
            and isinstance(value.args[0], (ast.Tuple, ast.List, ast.Set))
        ):
            values = tuple(
                element.value
                for element in value.args[0].elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
        elif isinstance(value, ast.Dict) and all(
            isinstance(key, ast.Constant) and isinstance(key.value, str) for key in value.keys
        ):
            values = tuple(key.value for key in value.keys)
        if values:
            sites.append((node.lineno, target.id, values))
    return sites


def _lexicon_findings(sources: list[tuple[Path, ast.Module]]) -> list[str]:
    """行 15 AST 判据面：正则语义判定＋自建语义词表＋词表名面＋汉字串集合／成员判据。

    豁免面＝形态处理（集合成员判定／字符串归一／字符截取）：闭世界枚举取值恒标识符形、
    不算语义词表；逐字披露文案只作拼接、不作判据（只在集合元素与 `in` 操作数两面被咬）。
    """
    findings: list[str] = []
    for path, tree in sources:
        for lineno, module in _imported_modules(tree):
            if module.split(".")[0] in _REGEX_MODULES:
                findings.append(f"{path.name}:{lineno} 禁引正则模块 {module}")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in _REGEX_MODULES
            ):
                findings.append(
                    f"{path.name}:{node.lineno} 正则语义判定 {node.value.id}.{node.attr}"
                )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if any(mark in node.name.lower() for mark in _LEXICON_NAME_MARKS):
                    findings.append(f"{path.name}:{node.lineno} 词表名面 {node.name}")
            elif isinstance(node, ast.Name):
                if any(mark in node.id.lower() for mark in _LEXICON_NAME_MARKS):
                    findings.append(f"{path.name}:{node.lineno} 词表名面 {node.id}")
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                for element in node.elts:
                    if (
                        isinstance(element, ast.Constant)
                        and isinstance(element.value, str)
                        and _has_cjk(element.value)
                    ):
                        findings.append(f"{path.name}:{node.lineno} 字面集合含汉字串（词表形）")
            if isinstance(node, ast.Compare) and any(
                isinstance(op, (ast.In, ast.NotIn)) for op in node.ops
            ):
                for operand in (node.left, *node.comparators):
                    if (
                        isinstance(operand, ast.Constant)
                        and isinstance(operand.value, str)
                        and _has_cjk(operand.value)
                    ):
                        findings.append(f"{path.name}:{node.lineno} 汉字串成员判据")
        for lineno, target, values in _module_str_collections(tree):
            for value in values:
                if not _IDENTIFIER_SHAPE.fullmatch(value):
                    findings.append(f"{path.name}:{lineno} 疑似语义词表项 {target} 含 {value!r}")
    return findings


def _constant_defs(
    sources: list[tuple[Path, ast.Module]], name: str
) -> list[tuple[str, int, Any]]:
    """模块级常量定义位点（`(文件名, 行, 字面值)`；非字面值记 `None`）。"""
    sites: list[tuple[str, int, Any]] = []
    for path, tree in sources:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                target = node.targets[0] if len(node.targets) == 1 else None
            elif isinstance(node, ast.AnnAssign):
                target = node.target
            else:
                continue
            if isinstance(target, ast.Name) and target.id == name:
                literal = node.value.value if isinstance(node.value, ast.Constant) else None
                sites.append((path.name, node.lineno, literal))
    return sites


def _alias_targets(
    sources: list[tuple[Path, ast.Module]], name: str
) -> list[tuple[str, str]]:
    """模块级**别名**定义位点（`名 = 另一名` 形——`(文件名, 右值名)`；V2-93 帽派生面）。"""
    sites: list[tuple[str, str]] = []
    for path, tree in sources:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                target = node.targets[0] if len(node.targets) == 1 else None
            elif isinstance(node, ast.AnnAssign):
                target = node.target
            else:
                continue
            if (
                isinstance(target, ast.Name)
                and target.id == name
                and isinstance(node.value, ast.Name)
            ):
                sites.append((path.name, node.value.id))
    return sites


def _bare_literal_sites(
    sources: list[tuple[Path, ast.Module]], values: tuple[int, ...]
) -> list[tuple[str, int, int]]:
    """源码内裸数值字面量位点（判「无缺省裸字面」残留）。"""
    return [
        (path.name, node.lineno, node.value)
        for path, tree in sources
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value in values
        and not isinstance(node.value, bool)
    ]


def _definition_sites(
    sources: list[tuple[Path, ast.Module]], name: str, kind: str
) -> list[tuple[str, int]]:
    """定义位点（`kind` ∈ `def`／`assign`）。"""
    sites: list[tuple[str, int]] = []
    for path, tree in sources:
        for node in ast.walk(tree):
            if kind == "def" and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == name:
                    sites.append((path.name, node.lineno))
            elif kind == "assign" and isinstance(node, ast.Assign):
                if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                    sites.append((path.name, node.lineno))
            elif kind == "assign" and isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == name:
                    sites.append((path.name, node.lineno))
    return sites


def _signature_shape(func: Any) -> tuple[tuple[str, str, bool], ...]:
    """签名形状（参数名／参形／「无缺省」标志——形状单点的观测面）。"""
    return tuple(
        (name, parameter.kind.name, parameter.default is inspect.Parameter.empty)
        for name, parameter in inspect.signature(func).parameters.items()
    )


# ---------- 13 渲染器族纯函数确定性（两跑相等／入参深比较不变／AST 零 IO·模型·时钟·随机·emit）-----


def test_renderers_pure_deterministic() -> None:
    """行 13 渲染器族纯函数确定性（行为 12——唯一 IO 面＝`load_ledger_dump` 的 tools 调用）。"""
    observations = [
        _obs(3, "fragment", content="检索片段", source="kb", source_id="kb-3"),
        _obs(1, "agg_row", content="合计 100", source_id="agg.fct_daily_metering"),
        _obs(2, "metric", content="台账卡", source_id="metric-1"),
    ]
    dump: dict[str, Any] = {"metrics": [{"slot": "日产油量"}]}
    state = _notes_state(6)
    chain = _chain()
    inputs = {
        "observations": deepcopy(observations),
        "state": deepcopy(state),
        "chain": deepcopy(chain),
        "observation": deepcopy(observations[0]),
        "dump": deepcopy(dump),
    }
    calls: list[tuple[str, Callable[[], Any]]] = [
        ("render_materials", lambda: render_materials(observations, max_observations=24)),
        (
            "render_process_notes",
            lambda: render_process_notes(state, budget=PROCESS_NOTES_BUDGET),
        ),
        (
            "compile_manifest",
            lambda: compile_manifest(
                observations, step="answer", max_observations=24, ledger_dump=dump
            ),
        ),
        ("compact_messages", lambda: compact_messages(chain, dialogue_view_tokens=120)),
        ("trust_of", lambda: trust_of(observations[2])),
    ]
    for label, call in calls:
        first, second = call(), call()
        assert first == second, f"{label} 两跑不相等（确定性被破）"
        assert repr(first) == repr(second), f"{label} 两跑不逐字相等"
    # 调用前后入参深比较相等（零写入）
    assert observations == inputs["observations"]
    assert state == inputs["state"]
    assert chain == inputs["chain"]
    assert observations[0] == inputs["observation"]
    assert dump == inputs["dump"]
    # 同输入异实例同结果（结果只由入参决定——无隐藏状态）
    assert render_materials(deepcopy(observations), max_observations=24) == render_materials(
        observations, max_observations=24
    )

    sources = _renderer_sources()
    assert sources, "扫描面为空——看守失效"
    assert _purity_findings(sources) == [], "渲染器族出现 IO／模型／时钟／随机／emit 位点"

    # 探测器非空转（IO／时钟／随机／模型／帧面五面各命中）
    probes: dict[str, str] = {
        "IO": "import os\nopen('痕迹')\n",
        "时钟": "from datetime import datetime\nnow = datetime.now()\n",
        "随机": "import random\npick = random.choice([1])\n",
        "模型": "async def go(egress):\n    await egress.complete([])\n",
        "帧面": "bus.emit('notice', {})\n",
    }
    for label, source in probes.items():
        assert _purity_findings([(Path("forged.py"), ast.parse(source))]), f"{label} 面探测器空转"


# ---------- 14 import 白名单（只 state＋tools）＋写面唯一（ledger_dump）＋零帧（AST）----------


def test_imports_and_write_ports_scan() -> None:
    """行 14 import 白名单＋写面唯一＋零帧（AST 扫描——红线④⑤⑥⑦）。"""
    sources = _context_sources()
    assert sources, "扫描面为空——看守失效"

    # ① import 白名单＝`state`＋`tools`＋`text_tokens`（V2-100 D-a 依赖自由判据单点）
    # ＋本包自身（禁引其余 runtimev2 块／infra／旧码）
    assert _import_findings(sources) == [], "本块 import 面越出「state＋tools＋text_tokens」白名单"
    blocks = {
        _dependency_block(module)
        for _name, tree in sources
        for _lineno, module in _imported_modules(tree)
        if module.startswith("appv2")
    }
    assert blocks <= {"context", "state", "tools", "text_tokens"}, (
        f"依赖白名单外块：{sorted(blocks)}"
    )
    # 零模型调用（连 `gateway_adapter` 都不 import——规格 :102 诚实声明面）
    assert not any(
        module.startswith(("appv2.runtimev2.gateway_adapter", "appv2.infra.llm_client"))
        for _name, tree in sources
        for _lineno, module in _imported_modules(tree)
    )

    # ② 写面唯一＝`ledger_dump` 取一次装载（恰一处，且不在共享写面）
    writes = _state_field_write_sites(sources)
    assert [(name, field) for name, _lineno, field in writes] == [("ledger.py", "ledger_dump")]
    for field in _SHARED_WRITE_FIELDS:
        assert not any(attr.startswith(field) for _n, _l, attr in writes), field

    # ③ 零帧（本块零 emit——帧面归发射方）
    assert [lineno for _path, tree in sources for lineno in _emit_sites(tree)] == []

    # 探测器非空转：其余 15 块／infra／旧码／引擎逐一被咬；伪造写面与帧面被咬
    for block in (
        "understanding",
        "clarification",
        "tool_matching",
        "preconditions",
        "execution",
        "answering",
        "verification",
        "orchestration",
        "bookkeeping",
        "prompts",
        "parsing",
        "transport",
        "persistence",
        "gateway_adapter",
        "gate",
    ):
        forged = [(Path("forged.py"), ast.parse(f"from appv2.runtimev2.{block} import x\n"))]
        assert _import_findings(forged), f"越界引块 {block} 未被咬"
    for module in ("appv2.infra.llm_client", "appv2.runtime.context", "appv2.knowledge.kb"):
        forged = [(Path("forged.py"), ast.parse(f"from {module} import x\n"))]
        assert _import_findings(forged), f"越界引块 {module} 未被咬"
    for forged_source in (
        "def f(state):\n    state.messages = []\n",
        "def f(state):\n    state.process_notes.append({})\n",
        "def f(state):\n    state.notices[0] = {}\n",
        "def f(state):\n    setattr(state, 'dialogue', [])\n",
    ):
        assert _state_field_write_sites([(Path("forged.py"), ast.parse(forged_source))])
    assert _emit_sites(ast.parse("bus.emit('notice', {})\n")) == [1]


# ---------- 15 程序侧无词表／正则语义判断（AST；豁免面＝形态处理） ----------


def test_no_lexicon_or_regex_in_context() -> None:
    """行 15 程序侧无词表／正则语义判断（AST；豁免面＝形态处理——行为 13）。"""
    sources = _context_sources()
    assert sources, "扫描面为空——看守失效"
    assert _lexicon_findings(sources) == [], "本块出现正则／语义词表位点"

    # 判定清单逐条可指真源条目（全部落形态处理——零语义判断）
    texts = _context_texts()
    for filename, marker, source in _JUDGEMENT_INVENTORY:
        assert marker in texts[filename], f"判定清单条目缺失：{filename} 的 {marker}（{source}）"

    # 探测器非空转（正则／词表名面／自建词表／汉字串集合／汉字串成员判据五类各命中）
    probes: dict[str, str] = {
        "正则": "import re\nhit = re.search('错', text)\n",
        "词表名面": "LEXICON = {'没答上': 'no'}\n",
        "自建词表": "WORDS: tuple[str, ...] = ('有用', '没用')\n",
        "汉字串集合": "PAIRS = ['提及', '执行']\n",
        "汉字串成员判据": "ok = word in '提及执行'\n",
    }
    for label, source in probes.items():
        assert _lexicon_findings([(Path("forged.py"), ast.parse(source))]), f"{label} 面探测器空转"
    # 豁免不是漏网：闭世界枚举取值与逐字披露文案不被咬（形态处理豁免面）
    legit = (
        "KINDS = {'agg_row': 1, 'fragment': 2}\n"
        "HINT = '台账投影装载失败——本轮无法取得台账材料'\n"
        "def use(kind):\n"
        "    return kind in KINDS\n"
    )
    assert _lexicon_findings([(Path("forged.py"), ast.parse(legit))]) == []


# ---------- 16 帽/预算常量单点（各一处、注入制无缺省裸字面） ----------


def test_cap_constant_single_point() -> None:
    """行 16 帽／预算常量各一处、注入制无缺省裸字面（行为 4／8——数值不落规格）。

    V2-93 D2 改判：帽 `DEFAULT_MAX_OBSERVATIONS` 不再是本块裸字面，而是由
    `tools/schema.py::SEND_BUDGET_CAP` 派生的**导入别名**（右值＝Name）；本块源码内 24 零残留
    （裸字面单点只剩 `PROCESS_NOTES_BUDGET=400`）。
    """
    sources = _v2_sources()
    assert sources, "扫描面为空——看守失效"
    definitions: dict[str, tuple[int, str]] = {
        "PROCESS_NOTES_BUDGET": (400, "process_notes.py"),
    }
    for name, (value, filename) in definitions.items():
        sites = _constant_defs(sources, name)
        assert [(site[0], site[2]) for site in sites] == [(filename, value)], (
            f"常量 {name} 在 runtimev2 面内非恰一处定义：{sites}"
        )
    # 帽单点＝导入别名（恰一处定义、右值非字面——真源 appv2/tools/schema.py::SEND_BUDGET_CAP）
    cap_sites = _constant_defs(sources, "DEFAULT_MAX_OBSERVATIONS")
    assert [(site[0], site[2]) for site in cap_sites] == [("materials.py", None)]
    # 视窗数值单点（同款纪律——行为 9：触发参数注入制、无裸值）
    window = _constant_defs(sources, "DEFAULT_DIALOGUE_VIEW_TOKENS")
    assert [(site[0], site[2]) for site in window] == [("compaction.py", 8192)]

    # 注入制、无缺省裸字面（帽／预算／视窗三参皆 kw-only 且无缺省）
    for func, parameter in (
        (render_materials, "max_observations"),
        (compile_manifest, "max_observations"),
        (render_process_notes, "budget"),
        (compact_messages, "dialogue_view_tokens"),
    ):
        param = inspect.signature(func).parameters[parameter]
        assert param.kind is inspect.Parameter.KEYWORD_ONLY, f"{func.__name__}.{parameter} 非注入制"
        assert param.default is inspect.Parameter.empty, f"{func.__name__}.{parameter} 带缺省裸字面"

    # 裸字面零残留：400 只出现在常量定义行、24 在本块源码内零命中（帽已派生）
    context_sources = _context_sources()
    allowed = {
        (path, lineno)
        for name in definitions
        for path, lineno, _value in _constant_defs(context_sources, name)
    }
    bare = _bare_literal_sites(context_sources, (24, 400))
    assert {(site[0], site[1]) for site in bare} == allowed, f"帽／预算裸字面残留：{bare}"

    # 探测器非空转
    forged_const = [(Path("forged.py"), ast.parse("DEFAULT_MAX_OBSERVATIONS = 24\n"))]
    assert _constant_defs(forged_const, "DEFAULT_MAX_OBSERVATIONS")
    forged_default = [(Path("forged.py"), ast.parse("def f(*, cap=24):\n    return cap\n"))]
    assert _bare_literal_sites(forged_default, (24,)) == [("forged.py", 1, 24)]


def test_cap_single_source() -> None:
    """V2-93 D2 帽单一真源：`context.DEFAULT_MAX_OBSERVATIONS` 由
    `appv2/tools/schema.py::SEND_BUDGET_CAP` 派生（导入别名）——两值相等性断言＋单点定义断言。"""
    assert DEFAULT_MAX_OBSERVATIONS == SEND_BUDGET_CAP == 24
    # 数值单点＝tools/schema.py 恰一处裸字面定义
    schema_path = _REPO_ROOT / "appv2" / "tools" / "schema.py"
    schema_sources = [(schema_path, ast.parse(schema_path.read_text(encoding="utf-8")))]
    assert [
        (site[0], site[2]) for site in _constant_defs(schema_sources, "SEND_BUDGET_CAP")
    ] == [("schema.py", 24)]
    # 派生面＝materials.py 恰一处别名赋值（右值＝Name，非第二份裸字面）
    assert _alias_targets(_context_sources(), "DEFAULT_MAX_OBSERVATIONS") == [
        ("materials.py", "SEND_BUDGET_CAP")
    ]


# ---------- 16b 判据本体单点（V2-100 D-a——L1/L3 共享 `appv2.text_tokens`） ----------


def test_judgement_single_source_text_tokens() -> None:
    """V2-100 D-a 单点真源：本块边界／全等判据**直引** `appv2.text_tokens`（零第二份实现）。

    `_anchor_score` 的分层加权留本块（不下沉）；判据本体＝`appv2.text_tokens.boundary_hit`／
    `num_token_hit`——L1（`appv2.retrieval`）与 L3 消费**同一对象**（对象同一性断言），
    全仓该两判据各**恰一处**定义（AST 扫 `appv2/`——名字含/不含前导下划线都算同一判据）。
    """
    from appv2 import text_tokens
    from appv2.retrieval import domain as retrieval_domain
    from appv2.runtimev2.context import materials as context_materials

    # 双方直引同一对象（L3 侧消费面＝本模块对象——非第二份副本）
    assert context_materials.boundary_hit is text_tokens.boundary_hit
    assert context_materials.num_token_hit is text_tokens.num_token_hit
    assert retrieval_domain.boundary_hit is text_tokens.boundary_hit
    assert retrieval_domain.num_token_hit is text_tokens.num_token_hit

    # 判据本体全仓恰一处定义（禁第二份）
    definitions: dict[str, list[str]] = {"boundary_hit": [], "num_token_hit": []}
    for path in sorted((_REPO_ROOT / "appv2").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.lstrip("_") in definitions:
                definitions[node.name.lstrip("_")].append(path.name)
    assert definitions == {
        "boundary_hit": ["text_tokens.py"],
        "num_token_hit": ["text_tokens.py"],
    }, f"判据本体非单点：{definitions}"

    # 判据语义（V2-90 钉死面——L1/L3 共享同一实现）
    assert text_tokens.boundary_hit("W-111", "W-11") is False
    assert text_tokens.boundary_hit("W-11 井", "W-11") is True
    assert text_tokens.num_token_hit("泵挂 2200 米", "22") is False
    assert text_tokens.num_token_hit("冲次 4.2 次/分", "22") is False
    assert text_tokens.num_token_hit("22 井", "22") is True


# ---------- 17 渲染单点（材料/过程档/信任映射/帽/三来源行映射各恰一处定义） ----------


def test_renderers_single_source() -> None:
    """行 17 五组渲染件在 runtimev2 面内各恰一处定义、消费方零副本（红线「禁手写替代」）。"""
    sources = _v2_sources()
    assert sources, "扫描面为空——看守失效"
    for name, kind, filename, label in _RENDERER_SINGLE_POINT:
        sites = _definition_sites(sources, name, kind)
        assert [site[0] for site in sites] == [filename], (
            f"{label}（{name}）在 runtimev2 面内非恰一处定义：{sites}"
        )

    # 渲染文案跨面唯一（消费方私存副本＝判失败）
    for anchor in _RENDER_TEXT_ANCHORS:
        holders = sorted(
            path.name for path, _tree in sources if anchor in path.read_text(encoding="utf-8")
        )
        assert len(holders) == 1, f"渲染文案「{anchor}」在 runtimev2 面内出现于多处：{holders}"
        assert holders[0] in _RENDERER_FILES

    # 消费面单点：包根 re-export 与定义处同一对象（消费方只经包根引用——R2）
    root = import_module("appv2.runtimev2.context")
    for func in _RENDERERS:
        assert getattr(root, func.__name__) is func

    # 探测器非空转：伪造第二定义点即被咬
    forged = [
        (Path("materials.py"), ast.parse("def trust_of(observation):\n    return 'report'\n")),
        (Path("answering.py"), ast.parse("def trust_of(observation):\n    return 'report'\n")),
    ]
    assert len(_definition_sites(forged, "trust_of", "def")) == 2


# ---------- 18 本块零合同字面（六族特征子串零命中） ----------


def _contract_features() -> list[tuple[str, str, str]]:
    """合同六族首句特征子串（定义点＝`prompts`——扫描范围对偶于 `specs/prompts.md` 行为 1）。

    **2026-10-18 V2-120 改判**：`ANSWER_THREE_STEP_CONTRACT` 以 7 字段头行「【作答前三步】」起头，
    特征子串改取**首个 ≥12 字内容句**（段头形短行不具副本看守力；其余成员首行即内容句、行为零改）。
    """
    constants = import_module("appv2.runtimev2.prompts.constants")
    features: list[tuple[str, str, str]] = []
    for family, members in constants.CONTRACT_CONSTANT_FAMILIES.items():
        for name in members:
            value = getattr(constants, name)
            feature = next(
                (line for line in value.split("\n") if len(line) >= 12), value
            )[:24]
            assert len(feature) >= 12 and feature in value, f"{family}.{name} 特征子串失效"
            features.append((family, name, feature))
    return features


def test_no_contract_literals_in_context() -> None:
    """行 18 合同六族特征子串在本块源码零命中（行为 14——本块零合同、零指令）。"""
    features = _contract_features()
    assert len(features) >= 6, "六族特征子串面为空——看守失效"
    texts = _context_texts()
    for family, name, feature in features:
        hits = sorted(filename for filename, text in texts.items() if feature in text)
        assert hits == [], f"{family}.{name} 合同字面副本残留：{hits}"

    # 探测器非空转：伪造本块源码，六族首句之一在场即被咬
    forged = {"forged.py": f'CONTRACT = "{features[0][2]}"'}
    hits = sorted(filename for filename, text in forged.items() if features[0][2] in text)
    assert hits == ["forged.py"]


# ---------- 20 【边界集】（空材料／全 notice／权威超帽／检索超帽／超长档案／超窗链） ----------


def test_boundary_empty_overcap_overwindow() -> None:
    """行 20【边界集】六形各落空段、全量、披露、摘要各分支（行为 1／4／5／8／9）。"""
    cap = DEFAULT_MAX_OBSERVATIONS
    zero = {"material_truncated": False, "material_rendered": 0, "material_total": 0}

    # ① 空材料 → 空段「（无）」＋(0, 0, False)；零档案 → 零段（调用方跳过）
    text, meta = render_materials([], max_observations=cap)
    assert text == "\n观察材料：\n（无）"
    assert _machine_fields(meta) == zero
    empty_manifest = compile_manifest([], step="understand", max_observations=cap)
    assert (
        empty_manifest.material_total,
        empty_manifest.material_rendered,
        empty_manifest.material_truncated,
    ) == (0, 0, False)
    assert empty_manifest.source_type == empty_manifest.source_id == []
    assert empty_manifest.version == empty_manifest.trust_level == []
    assert render_process_notes(RunState(), budget=PROCESS_NOTES_BUDGET) == ""

    # ② 全 notice → 材料段空段、零计数、零来源行（notice 不进模型面、不计任何计数）
    notices = [_obs(index, "notice", content=f"窗口缺参反问 {index}") for index in range(1, 5)]
    notice_text, notice_meta = render_materials(notices, max_observations=cap)
    assert notice_text == "\n观察材料：\n（无）" and _machine_fields(notice_meta) == zero
    assert "反问" not in notice_text
    notice_manifest = compile_manifest(notices, step="answer", max_observations=cap)
    assert notice_manifest.material_truncated is False
    assert notice_manifest.source_type == [] and notice_manifest.source_id == []

    # ③ 权威超帽 → 全量渲染、零披露、False（帽不作用权威族——pin-08 渲染分形面）
    authority = [_obs(index + 1, "agg_row", content=f"行 {index + 1}") for index in range(40)]
    authority_text, authority_meta = render_materials(authority, max_observations=cap)
    assert len(_indices(authority_text)) == 40
    assert _DISCLOSURE_HEAD not in authority_text
    assert _machine_fields(authority_meta) == {"material_truncated": False,
                                               "material_rendered": 40, "material_total": 40}

    # ④ 检索超帽 → 只渲帽内支＋披露行＋True（模型面披露行与机读字段同场）
    cut_text, cut_meta = render_materials(_fragments(30), max_observations=cap)
    assert len(_indices(cut_text)) == cap and _DISCLOSURE_HEAD in cut_text
    assert _machine_fields(cut_meta) == {"material_truncated": True,
                                         "material_rendered": cap, "material_total": 30}
    cut_manifest = compile_manifest(_fragments(30), step="answer", max_observations=cap)
    assert cut_manifest.material_truncated is True
    assert f"帽 {cap} 支截断（{cap}/30）" in cut_manifest.selected_reason

    # ⑤ 超长档案 → 披露行逐字＋有界停止（n 与已渲行数一致）
    long_notes = render_process_notes(_notes_state(30), budget=120)
    rendered = long_notes.count("\n- [")
    assert rendered < 30
    assert _PROCESS_NOTES_DISCLOSURE.format(n=rendered, total=30) in long_notes

    # ⑥ 超窗链 → 摘要置位＋披露账目在场＋原史零覆盖（`state.messages` 深比较不变）
    chain = _chain()
    before = deepcopy(chain)
    view, account = compact_messages(chain, dialogue_view_tokens=120)
    assert view[1]["role"] == "system" and view[1]["content"].startswith(_SUMMARY_HEAD)
    assert view != chain and account != "" and chain == before
    # 合成位：材料面 `selected_reason` 之后以「；」追加（本块只返账目串）
    reason = compile_manifest([], step="answer", max_observations=cap).selected_reason
    assert f"{reason}；{account}".endswith(account)


# ---------- 21 【保留集】（常规渲染与常规档案逐字不变；[n] 序号与排序行为不回归） ----------


def test_retention_normal_render_unchanged() -> None:
    """行 21【保留集】常规材料渲染与常规档案（无截断、预算内）输出逐字不变；
    既有 `[n]` 序号与排序行为不因本批改形回归（形状单点＝-02a 落地件，本票只加断言）。"""
    observations = [
        _obs(11, "metric", content="日产油量（吨）：21.16", source="台账·指标", well="K12-3"),
        _obs(12, "agg_row", content="合计 100", source="agg.fct_daily_metering"),
        _obs(13, "fragment", content="检索片段正文", source="kb"),
        _obs(14, "fragment", content="第二片段", source="kb"),
    ]
    text, meta = render_materials(observations, max_observations=DEFAULT_MAX_OBSERVATIONS)
    assert text == (
        "\n观察材料：\n"
        "[12]（authoritative｜agg.fct_daily_metering）合计 100\n"
        "[11]（ledger｜台账·指标｜K12-3）日产油量（吨）：21.16\n"
        "[13]（report｜kb）检索片段正文\n"
        "[14]（report｜kb）第二片段"
    )
    # 序号＝观察自带全局序号（非渲染位次）；排序＝信任级稳定序（authoritative＜ledger＜report）
    assert _indices(text) == [12, 11, 13, 14]
    assert _machine_fields(meta) == {
        "material_truncated": False, "material_rendered": 4, "material_total": 4,
    }
    assert _DISCLOSURE_HEAD not in text and "（无）" not in text
    # 同 rank 保持入栈序（稳定排序不抖动）：检索族两条换位 → 输出组内序随动
    swapped = [observations[0], observations[1], observations[3], observations[2]]
    assert _indices(render_materials(swapped, max_observations=DEFAULT_MAX_OBSERVATIONS)[0]) == [
        12,
        11,
        14,
        13,
    ]

    # 常规档案（预算内）逐字：头注＋条目行形；零披露行
    notes = RunState(process_notes=[{"phase": "decision", "title": "第 0 步", "digest": "结果"}])
    assert render_process_notes(notes, budget=PROCESS_NOTES_BUDGET) == (
        "【本 run 已做（过程档案摘要——防重参考，不是作答材料）】\n- [decision] 第 0 步｜结果"
    )

    # 形状单点：六函数签名与常量族仍以 -02a 落地的为唯一真源（V2-122 追加 `source_columns`
    # 一枚 additive 可选参＝列名改判；其余五函数签名与常量族零改）
    expected_shapes: dict[Any, tuple[tuple[str, str, bool], ...]] = {
        render_materials: (
            ("observations", "POSITIONAL_OR_KEYWORD", True),
            ("max_observations", "KEYWORD_ONLY", True),
            ("anchors", "KEYWORD_ONLY", False),  # V2-86 additive 可选参（缺省空元组）
            # V2-123 additive 可选参（执行日注入——缺省空串＝本批前逐字零漂移）
            ("execution_date", "KEYWORD_ONLY", False),
            # V2-122 追加（签名 4→5 参，列名改判）：分源分栏开关（缺省 True＝多来源分栏；
            # False＝逐字回分栏前形——零改证明面；单来源/零检索族恒零块头）。
            ("source_columns", "KEYWORD_ONLY", False),
        ),
        render_process_notes: (
            ("state", "POSITIONAL_OR_KEYWORD", True),
            ("budget", "KEYWORD_ONLY", True),
        ),
        compile_manifest: (
            ("observations", "POSITIONAL_OR_KEYWORD", True),
            ("step", "KEYWORD_ONLY", True),
            ("max_observations", "KEYWORD_ONLY", True),
            ("anchors", "KEYWORD_ONLY", False),  # V2-86 补丁 additive 可选参（与 render 同一组）
            ("ledger_dump", "KEYWORD_ONLY", False),
            ("token_count", "KEYWORD_ONLY", False),
        ),
        compact_messages: (
            ("messages", "POSITIONAL_OR_KEYWORD", True),
            ("dialogue_view_tokens", "KEYWORD_ONLY", True),
        ),
        trust_of: (("observation", "POSITIONAL_OR_KEYWORD", True),),
        load_ledger_dump: (("state", "POSITIONAL_OR_KEYWORD", True),),
    }
    for func, expected in expected_shapes.items():
        assert _signature_shape(func) == expected, f"{func.__name__} 签名形状漂移"
    assert inspect.iscoroutinefunction(load_ledger_dump)

    # 常量族（六枚＋视窗单点）值面不改
    assert (DEFAULT_MAX_OBSERVATIONS, PROCESS_NOTES_BUDGET) == (24, 400)
    assert (TRUST_AGG, TRUST_LEDGER, TRUST_REPORT) == ("authoritative", "ledger", "report")
    assert list(RESIDENT_SOURCE_ROWS.items()) == [
        ("ledger_dump", "ledger_full_dump"),
        ("alias_dump", "ledger_aliases"),
        ("schema_card", "schema_cards"),
    ]


# ---------- 附：消费面指针（登记件——本票不实现） ----------

# ①`specs/prompts.md` 行为 16⑤：已做段由调用方传入 `render_process_notes` 产物文本原样在场
#   （渲染归本块、拼接归调用方——本块不追加、不改写）；
# ②`specs/answering.md` 行为 4：材料面 Manifest 由本块编译、随步落地（缺位＝判失败）；
#   材料截断 notice 帧与用户面披露文本＝发射方义务（本块零帧）；
# ③`specs/bookkeeping.md` 行为 7／8：`messages` 物理追加与合同标记写入＝其唯一写口
#   （pin-24／pin-26 不落本块：本块零合同、零标记、零追加时点——`dialogue` 写口不在本块）。

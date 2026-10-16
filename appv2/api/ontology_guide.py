"""api.ontology_guide —— ontology 指南资产装载件（V2-34 任务 10）。

GUIDE-PETRO-001（ontology/petro/skill-guides/——业务语义资产，与台账同治理）
的装载点：manifest.loadingSeam 合同的落码面——「ontology 导出（本目录文件）→
runtime Context Builder 装载点」。

guide() 输出＝instructions.md §A 装载切面原文（{today}/{month_start}/{start30}/
{max_rounds}/{max_discovers}/{max_executes} 占位符按执行日与预算合同填充）。

**旧码决策合同的落点（RT-W5-02 G9 登记，本层不再引旧码）**：§A 装载时曾拼接
`DECISION_CONTRACT`（决策发射合同正文——真源＝旧编排件 `appv2/runtime/guide.py`，
与 `graph.parse_decision` schema 校验同源单点）。RT-W5-02 起本层（V2 api）**不再
引旧码**（旧运行时包进口零命中——`appv2/api/*.py` 对旧包的 import 面清零）：该合同的
服务对象＝**旧 runtime 装配面**（ReAct
单相位决策面），随 eng/03 §三 废弃节奏与旧码一并退场；本层服务的四相位装配由相位
合同（`appv2.runtimev2.prompts` 的澄清/匹配合同，相位侧前置）承载，从不请求该合同。
`include_decision_contract` 形参保留＝**旧装配面构造兼容**（取值不再影响本层输出——
合同正文不复制进本层、不设第二真源；受影响的旧面断言归 eng/04 §五 织网②改写面）。

边界注记：本件在 api 装配面（modules.md「api 只依赖 orchestration＋transport/
persistence/infra」的组合根例外延伸——与 compose_production_registry 同款局部性质：
只读 repo 内 ontology 资产文件，零引擎接触）。
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from appv2.infra import clock

# ontology 指南资产缺省路径（repo 相对——本文件 parents[2]＝仓根）。
DEFAULT_GUIDE_PATH = (
    Path(__file__).resolve().parents[2] / "ontology" / "petro" / "skill-guides" / "instructions.md"
)

# 本体对象模型缺省路径（V2-58 理解步任务书注入面——对象摘要提取源）。
DEFAULT_M1_PATH = (
    Path(__file__).resolve().parents[2] / "ontology" / "petro" / "m1-object-model.yaml"
)

_SECTION_A_HEAD = "## §A"
_SECTION_END_MARK = "\n---"


def load_object_digests(path: Path | None = None) -> list[str]:
    """本体对象摘要（V2-58 理解步任务书注入面——m1 对象模型程序化提取）。

    每聚合一行「name：label（枚举1／枚举2）·label…」；lifecycle 值集若与某属性
    枚举重复（井：当前状态＝状态机）则不重复渲染。api 层读本体资产＝
    OntologyGuideProvider 同款组合根例外（只读 repo 内本体文件，零引擎接触）。
    """
    import yaml

    m1_path = path if path is not None else DEFAULT_M1_PATH
    with m1_path.open(encoding="utf-8") as fh:
        m1 = yaml.safe_load(fh)
    lines: list[str] = []
    for agg in m1.get("aggregates", []):
        labels: list[str] = []
        enums_by_attr: list[set[str]] = []
        for attr in agg.get("attributes", []):
            label = str(attr.get("label", attr.get("name", "")))
            ev = list(attr.get("enumValues") or [])
            enums_by_attr.append(set(ev))
            labels.append(f"{label}（{'／'.join(ev)}）" if ev else label)
        lifecycle = list(agg.get("lifecycle") or [])
        if lifecycle and not any(set(lifecycle) == enums for enums in enums_by_attr):
            labels.append(f"状态机（{'／'.join(lifecycle)}）")
        body = "·".join(labels)
        name = str(agg.get("name", ""))
        lines.append(f"{name}：{body}" if body else name)
    return lines


def _extract_section_a(text: str) -> str:
    """§A 装载切面提取（manifest.runtimeSurface.section 合同——到下一个分隔线）。"""
    start = text.find(_SECTION_A_HEAD)
    if start < 0:
        raise ValueError(f"指南资产缺 §A 装载切面：{_SECTION_A_HEAD!r} 未找到")
    end = text.find(_SECTION_END_MARK, start)
    section = text[start:end] if end > start else text[start:]
    return section.strip()


class OntologyGuideProvider:
    """ontology 资产件装载器（§A 装载切面——旧 runtime `LoopDeps.guide` 注入面同形）。"""

    def __init__(
        self,
        *,
        path: Path | None = None,
        today: date | None = None,
        max_rounds: int = 3,
        max_discovers: int = 2,
        max_executes: int = 2,
        include_decision_contract: bool = True,
    ) -> None:
        self._path = path if path is not None else DEFAULT_GUIDE_PATH
        # 时钟唯一出口（B14）——执行日缺省取 infra.clock；测试注入固定值。
        self._today = today if today is not None else clock.now().date()
        self._max_rounds = max_rounds
        self._max_discovers = max_discovers
        self._max_executes = max_executes
        # 旧码决策合同的拼接已随旧 runtime 装配面退场（G9 落点登记，见模块 docstring）：
        # 形参保留＝旧装配面构造兼容；取值不再影响本层输出——合同正文的真源在旧编排件
        # （`appv2/runtime/guide.py` ↔ `graph.parse_decision`），本层不引旧码、不复制正文。
        self._include_decision_contract = include_decision_contract

    def guide(self) -> str:
        text = self._path.read_text(encoding="utf-8")
        section = _extract_section_a(text)
        today = self._today
        start30 = (today - timedelta(days=30)).isoformat()
        month_start = today.replace(day=1).isoformat()
        return (
            section.replace("{today}", today.isoformat())
            .replace("{month_start}", month_start)
            .replace("{start30}", start30)
            .replace("{max_rounds}", str(self._max_rounds))
            .replace("{max_discovers}", str(self._max_discovers))
            .replace("{max_executes}", str(self._max_executes))
        )

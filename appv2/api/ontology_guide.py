"""api.ontology_guide —— ontology 指南资产装载件（V2-34 任务 10——create_app 真指南接线）。

GUIDE-PETRO-001（ontology/petro/skill-guides/——业务语义资产，与台账同治理）
的 runtime 常驻装载点：manifest.loadingSeam 合同的落码面——
「ontology 导出（本目录文件）→ runtime Context Builder 装载点＝GraphRunExecutor
(guide=…) 构造参数（create_app 组合根传递）」。

guide() 输出＝instructions.md §A 装载切面原文（{today}/{month_start}/{start30}/
{max_rounds}/{max_discovers}/{max_executes} 占位符按执行日与预算合同填充）＋
runtime 发射合同文本 DECISION_CONTRACT（appv2.runtime.guide——与
graph.parse_decision schema 校验同源单点，本件不复制不设双真源）。

占位退役（V2-34）：runtime 侧 DefaultGuideProvider 五段内置文案由 §A 对应条款
接管——生产唯一指南源＝本装载件（create_app 缺省构造）。

边界注记：本件在 api 装配面（modules.md「api 只依赖 runtime＋infra」的组合根
例外延伸——与 compose_production_registry 同款局部性质：只读 repo 内 ontology
资产文件，零引擎接触）。
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from appv2.infra import clock
from appv2.runtime.guide import DECISION_CONTRACT

# ontology 指南资产缺省路径（repo 相对——本文件 parents[2]＝仓根）。
DEFAULT_GUIDE_PATH = (
    Path(__file__).resolve().parents[2] / "ontology" / "petro" / "skill-guides" / "instructions.md"
)

_SECTION_A_HEAD = "## §A"
_SECTION_END_MARK = "\n---"


def _extract_section_a(text: str) -> str:
    """§A 装载切面提取（manifest.runtimeSurface.section 合同——到下一个分隔线）。"""
    start = text.find(_SECTION_A_HEAD)
    if start < 0:
        raise ValueError(f"指南资产缺 §A 装载切面：{_SECTION_A_HEAD!r} 未找到")
    end = text.find(_SECTION_END_MARK, start)
    section = text[start:end] if end > start else text[start:]
    return section.strip()


class OntologyGuideProvider:
    """ontology 资产件装载器（GuideProvider 同形协议——LoopDeps.guide 注入面）。"""

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
        # 四相位装配（V2-34）置 False：legacy 决策发射合同不拼进指南面——相位
        # 发射合同（CLARIFY/TOOLMATCH_CONTRACT）由 runtime 在消费缝前置。双合同
        # 并存时真模型跟随 legacy 四动作（P033SK1 实证：MiniMax 逐字照抄
        # execute/finalize——澄清相位三轮被拒收敛），故四相位只挂一份合同。
        self._include_decision_contract = include_decision_contract

    def guide(self) -> str:
        text = self._path.read_text(encoding="utf-8")
        section = _extract_section_a(text)
        today = self._today
        start30 = (today - timedelta(days=30)).isoformat()
        month_start = today.replace(day=1).isoformat()
        section = (
            section.replace("{today}", today.isoformat())
            .replace("{month_start}", month_start)
            .replace("{start30}", start30)
            .replace("{max_rounds}", str(self._max_rounds))
            .replace("{max_discovers}", str(self._max_discovers))
            .replace("{max_executes}", str(self._max_executes))
        )
        if not self._include_decision_contract:
            return section
        return f"{section}\n\n{DECISION_CONTRACT}"

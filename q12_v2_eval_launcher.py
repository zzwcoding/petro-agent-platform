"""评测组合根启动器（:8001 —— V2 问答服务；冻结时钟走 gateway_adapter 显式注入缝）。

与 q12_v2_launcher（生产组合根——真实时钟零冻结）装配完全同形，唯一差异＝
`today=frozen_date` 注入（规格 `specs/gateway_adapter.md` 行为 9 的显式注入缝；
生产桥不读环境变量，冻结取值封在本件内：未设/空串＝缺省冻结日 2026-08-31，
`real`＝真实当日，ISO＝该日，非法值 fail-fast）。

启动（评测/跑批用——与历届批次同口径，水位日冻结）：
    .venv/bin/uvicorn q12_v2_eval_launcher:app --host 127.0.0.1 --port 8001
"""

from appv2.api.app import create_app
from appv2.infra.config import load_database_specs
from appv2.infra.db import ConnectionManager
from appv2.infra.gateway.service import GatewayService
from appv2.infra.llm_client import LlmClient
from appv2.runtimev2.gateway_adapter import GatewayBridge, frozen_date

_manager = ConnectionManager(load_database_specs())
# 同面缝真源＝gateway_adapter：评测态同样注入 GatewayBridge
#（429 可重试/fail-closed/记账回执），egress＝GatewayService（B6 唯一出口）。
_completer = GatewayBridge(egress=GatewayService(_manager, LlmClient()))
app = create_app(db=_manager, completer=_completer, today=frozen_date)

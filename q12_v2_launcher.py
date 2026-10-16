"""生产组合根启动器（:8001 —— V2 问答服务；真实时钟，零冻结零侦探）。

装配＝create_app 生产组合（registry 缺省真装配三引擎＋faq_lookup 读缝）；
启动：.venv/bin/uvicorn q12_v2_launcher:app --host 127.0.0.1 --port 8001
"""

from appv2.api.app import create_app
from appv2.infra.config import load_database_specs
from appv2.infra.db import ConnectionManager
from appv2.infra.gateway.service import GatewayService
from appv2.infra.llm_client import LlmClient
from appv2.runtimev2.gateway_adapter import GatewayBridge

_manager = ConnectionManager(load_database_specs())
# 同面缝真源＝gateway_adapter：生产注入 GatewayBridge（429 可重试/fail-closed/记账回执），
# egress＝GatewayService（B6 唯一出口——别名路由/fallback/熔断在 infra 侧）。
_completer = GatewayBridge(egress=GatewayService(_manager, LlmClient()))
app = create_app(db=_manager, completer=_completer)

"""生产组合根启动器（:8001 —— V2 问答服务；真实时钟，零冻结零侦探）。

装配＝create_app 生产组合（registry 缺省真装配三引擎＋faq_lookup 读缝）；
启动：.venv/bin/uvicorn q12_v2_launcher:app --host 127.0.0.1 --port 8001
"""

from appv2.api.app import create_app
from appv2.infra.config import load_database_specs
from appv2.infra.db import ConnectionManager
from appv2.infra.gateway.service import GatewayService
from appv2.infra.llm_client import LlmClient

_manager = ConnectionManager(load_database_specs())
_completer = GatewayService(_manager, LlmClient())
app = create_app(db=_manager, completer=_completer)

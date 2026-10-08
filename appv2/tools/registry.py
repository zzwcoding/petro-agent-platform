"""tools.registry —— ToolRegistry（agent 与世界的唯一接触面；specs/tools.md 接口定义节）。

三段统一调出口（行为约定 2/3 单点）：
1. 寻工具——未知工具名→failed(bad_args)；
2. schema 校验——argscheck 子集校验器：不合→failed(bad_args)，引擎零调用；
3. 执行——handler（引擎包装），ArgsError（装配层参数拒）转 bad_args，其余
   异常统一三分类封套（classify_exception：超时→retryable；上游 4xx 类→
   bad_args；网关 UpstreamRejected→bad_args／UpstreamUnavailable→retryable；
   越权→refused；ValueError→bad_args；其余上游抖动→retryable）。

INV-2 工具层落点：register 拒绝 readonly!=True 的工具与重名；registry 公开面
只有 register/descriptors/call 三个方法——零数据写出口（测试钉死）。渐进披露
发现面＝descriptors()（只透 ToolDescriptor 四字段）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from appv2.infra.llm_client import UpstreamRejected, UpstreamUnavailable
from appv2.knowledge import KnowledgeStore
from appv2.tools.argscheck import ArgsError, validate_args
from appv2.tools.handlers import (
    QueryFace,
    RetrievalFace,
    build_tools,
)
from appv2.tools.schema import (
    CATEGORY_BAD_ARGS,
    CATEGORY_REFUSED,
    CATEGORY_RETRYABLE,
    Tool,
    ToolContext,
    ToolDescriptor,
    ToolResult,
)


def classify_exception(exc: Exception) -> tuple[str, str, str | None]:
    """引擎异常→（category, message, hint）三分类（specs/tools.md 行为约定 3）。

    4xx 判定双面：duck 型认异常的 status_code 属性（400–499——与 HTTP 异常形状
    对齐，不绑具体异常类型，真实 HTTP 异常与测试桩 FakeUpstreamRejection 同判）；
    类型面认网关异常族（UpstreamRejected/UpstreamUnavailable——B6 出口不带
    status_code 属性，按网关切换判据投影：4xx/429 业务性拒绝→bad_args，
    网络错/超时/5xx→retryable，防接线变化后三分类失真）。asyncio.TimeoutError
    在 3.12 即内建 TimeoutError，异步超时同判。
    """
    if isinstance(exc, TimeoutError):
        return (
            CATEGORY_RETRYABLE,
            f"上游超时：{exc}",
            "可重试——同参重调一次，再败即转人工/收口",
        )
    if isinstance(exc, PermissionError):
        return CATEGORY_REFUSED, f"越权拒绝：{exc}", "权限闸拒——不重试"
    if isinstance(exc, UpstreamUnavailable):
        return (
            CATEGORY_RETRYABLE,
            f"上游暂不可用：{exc}",
            "可重试——同参重调一次，再败即转人工/收口",
        )
    if isinstance(exc, UpstreamRejected):
        return (
            CATEGORY_BAD_ARGS,
            f"上游拒绝（4xx/限流族）：{exc}",
            "上游业务性拒绝——修参后重试；再败即转人工/收口",
        )
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and 400 <= status < 500:
        return (
            CATEGORY_BAD_ARGS,
            f"上游参数拒绝（HTTP {status}）：{exc}",
            "4xx 为请求侧错误——修参后重试",
        )
    if isinstance(exc, ValueError):
        return CATEGORY_BAD_ARGS, f"计划或参数错误：{exc}", "修 plan/参数后重试"
    return (
        CATEGORY_RETRYABLE,
        f"上游抖动：{exc}",
        "可重试——同参重调一次，再败即转人工/收口",
    )


class ToolRegistry:
    """只读工具注册表与统一调出口（specs/tools.md 接口定义节原形）。"""

    def __init__(
        self,
        *,
        knowledge: KnowledgeStore,
        query: QueryFace,
        retrieval: RetrievalFace,
    ) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in build_tools(knowledge=knowledge, query=query, retrieval=retrieval):
            self.register(tool)

    def register(self, tool: Tool) -> None:
        """注册工具（INV-2：readonly!=True 拒绝入册；重名拒绝——注册表确定性）。"""
        if tool.descriptor.readonly is not True:
            raise ValueError(
                f"工具 {tool.descriptor.name!r} readonly!=True——"
                "工具层只收只读工具（INV-2，specs/tools.md 行为约定 1）"
            )
        if tool.descriptor.name in self._tools:
            raise ValueError(f"工具重名：{tool.descriptor.name!r}")
        self._tools[tool.descriptor.name] = tool

    def descriptors(self) -> list[ToolDescriptor]:
        """渐进披露发现面（注册序；只暴露名称/描述/参数 schema/只读声明）。"""
        return [tool.descriptor for tool in self._tools.values()]

    async def call(
        self, name: str, args: Mapping[str, Any], ctx: ToolContext
    ) -> ToolResult:
        """统一调出口（寻工具→schema 校验→执行；异常统一三分类封套）。"""
        tool = self._tools.get(name)
        if tool is None:
            known = ", ".join(self._tools) or "（空）"
            return ToolResult.failed(
                CATEGORY_BAD_ARGS,
                f"未知工具：{name}（可用：{known}）",
                hint="按 descriptors() 列表选择工具名",
            )
        try:
            validated = validate_args(tool.descriptor.args_schema, args)
        except ArgsError as exc:
            return ToolResult.failed(
                CATEGORY_BAD_ARGS,
                str(exc),
                hint="按 args_schema 修参后重试（schema 拒＝引擎零调用）",
            )
        try:
            return await tool.handler(validated, ctx)
        except ArgsError as exc:
            return ToolResult.failed(
                CATEGORY_BAD_ARGS, str(exc), hint="按拒因修参后重试"
            )
        except Exception as exc:  # 引擎异常统一三分类（行为约定 3）
            category, message, hint = classify_exception(exc)
            return ToolResult.failed(category, message, hint=hint)

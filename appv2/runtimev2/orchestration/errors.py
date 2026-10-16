"""orchestration 的错误族（异常上抛面——api 层据此映射 404／409；映射表不在本块）。

两条形（照旧码 `appv2.runtime.executor` 的同名异常，语义零改动——api 的 `errors.py` 消费面
逐字同形）：

- `RunNotFoundError`：run 不存在（api 404 的运行时侧异常源）；
- `RunNotSuspendedError`：run 非挂起态不可 resume／前轮未收口不可追问（api 409 的异常源）。

本模块**不吞错、不返回哨兵值**：图执行器不可用时按 fail-closed 收束为 `failed`（规格「不降级与
静默禁令」节：合法降级路径＝无），受理参数类错误一律上抛。
"""


class OrchestrationError(RuntimeError):
    """orchestration 错误族基类（便于 api 侧一次捕获转码）。"""


class RunNotFoundError(OrchestrationError):
    """run 不存在（受理侧与追问播种侧共用——404 的异常源）。"""


class RunNotSuspendedError(OrchestrationError):
    """run 非挂起态不可 resume（409）；前轮未收口不可追问（409）——同一异常族两语义。"""

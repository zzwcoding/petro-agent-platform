"""infra.object_storage —— 对象存储统一接缝（98 §4 adapter；B1/F5 预签名直传的落点）。

选型理由（票面要求说明）：
- 99 册 m5 对象存储＋PRD F5「预签名直传直下载」裁定对象存储为本票 kb 域的
  硬依赖（直传两拍 ①受理发预签名 PUT ②服务端 HEAD 核实落桶）；compose 中间件
  五件已含 MinIO、pyproject 已有 minio>=7.2 依赖——**落真 MinIO adapter**
  而非凭证句柄占位：占位无法兑现「服务端核实对象已落桶」（confirm 409 判据源）
  与「下载直链小时级有效」两条合同行为，冒烟验收（真传→五步）也无从谈起。
- 物理桶名＝F5 桶规划 `reports`（合同「桶：报告原文」为显示名照抄——B1 出入
  对账 8：显示名不入物理命名）；对象不设过期（99 册对象存储生命周期注记）。
- minio SDK 是同步客户端——全部调用经 asyncio.to_thread 包装（线程池卸载，
  不阻塞事件循环）；presign 是纯本地签名，但走同一线路保持 seam 一致。

边界：B1（不 import fastapi/starlette）、B16（infra 不咬上层）；
凭证经 infra.config InfraSettings 注入（.env / 环境变量，不进 git）。
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING, Protocol

from app.infra.config import get_settings

if TYPE_CHECKING:
    from minio import Minio

# 桶规划（PRD F5）——报告原件桶（「一个字不动」的物理落点）。
REPORTS_BUCKET = "reports"

# TTL 口径（00 §7）：GET 直链小时级有效、上限 7 天（票 85）；PUT 直传凭证
# 合同未冻结期限（B1 端点 5 示例约 25–30 分钟量级）——落 30 分钟常量，挂疑点清单。
PUT_TTL_SECONDS = 30 * 60
GET_TTL_SECONDS = 60 * 60


class ObjectStorage(Protocol):
    """对象存储 seam（测试注入假实现；生产装配 MinioObjectStorage）。"""

    async def presign_put(self, key: str, *, ttl_seconds: int = PUT_TTL_SECONDS) -> str: ...

    async def presign_get(self, key: str, *, ttl_seconds: int = GET_TTL_SECONDS) -> str: ...

    async def exists(self, key: str) -> bool: ...

    async def get_bytes(self, key: str) -> bytes: ...


class MinioObjectStorage:
    """MinIO adapter（compose 中间件；凭证经 InfraSettings）。

    首次使用懒建连＋确保桶存在（make_bucket if not exists——幂等）。
    """

    def __init__(self) -> None:
        self._client: Minio | None = None
        self._ready = False
        settings = get_settings()
        self._endpoint = settings.minio_endpoint
        self._access_key = settings.minio_access_key
        self._secret_key = settings.minio_secret_key
        self._secure = settings.minio_secure

    def _ensure_client(self) -> Minio:
        if self._client is None:
            from minio import Minio  # 局部 import——B6 同款纪律：SDK 接触面收敛单模块

            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
        return self._client

    def _ensure_bucket(self) -> None:
        client = self._ensure_client()
        if not client.bucket_exists(REPORTS_BUCKET):
            client.make_bucket(REPORTS_BUCKET)
        self._ready = True

    async def _ensure_ready(self) -> None:
        if not self._ready:
            await asyncio.to_thread(self._ensure_bucket)

    async def presign_put(self, key: str, *, ttl_seconds: int = PUT_TTL_SECONDS) -> str:
        await self._ensure_ready()

        def _presign() -> str:
            return str(
                self._ensure_client().presigned_put_object(
                    REPORTS_BUCKET, key, timedelta(seconds=ttl_seconds)
                )
            )

        return await asyncio.to_thread(_presign)

    async def presign_get(self, key: str, *, ttl_seconds: int = GET_TTL_SECONDS) -> str:
        await self._ensure_ready()

        def _presign() -> str:
            return str(
                self._ensure_client().presigned_get_object(
                    REPORTS_BUCKET, key, timedelta(seconds=ttl_seconds)
                )
            )

        return await asyncio.to_thread(_presign)

    async def exists(self, key: str) -> bool:
        await self._ensure_ready()

        def _stat() -> bool:
            from minio.error import S3Error

            try:
                self._ensure_client().stat_object(REPORTS_BUCKET, key)
                return True
            except S3Error as exc:
                if exc.code in ("NoSuchKey", "NoSuchObject"):
                    return False
                raise

        return await asyncio.to_thread(_stat)

    async def get_bytes(self, key: str) -> bytes:
        await self._ensure_ready()

        def _get() -> bytes:
            resp = self._ensure_client().get_object(REPORTS_BUCKET, key)
            try:
                return bytes(resp.read())
            finally:
                resp.close()
                resp.release_conn()

        return await asyncio.to_thread(_get)

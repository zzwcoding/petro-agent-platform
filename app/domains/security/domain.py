"""domains.security.domain —— 身份与审计的领域语义（厚：合同语义在此闭环）。

合同锚（真源在 teach-petro-agent/specs/api/，只引路径不复制正文）：
- 00-系统级API.md §2.3/2.4：401＝身份解析失败；开发期身份桩＝读请求头
  X-Dev-User（缺省落默认角色）；接 OAuth2.0 只换 resolve_actor 实现，
  签名与 401/403/404 判例零改动（ADR-0003 裁决 5）。
- 00 §8：审计语义四槽（时间/操作者/动作/内容）、只读追加不可关闭、
  拦截也是审计事件、digest＝SM3 摘要指纹永不落正文。
- 00 §9.1：五角色与 who 格式（label 全名「小李 · 地质/质检」，照抄 roles.js）。
- 98-模块划分与分层.md §3.13：公开接口 authenticate≡resolve_actor（同位同义）、
  authorize（页面组闸）、audit（B12 唯一写口）、audit_logs（D3 读面）。
- docs/prd.md 拍板回执：默认角色＝阿强。

B1：本模块禁 import fastapi/starlette——身份解析入参是请求头取值字符串，
请求解包归接口层（app/api/deps.py）。B12：写存储归 service/store；
本文件只持语义（角色注册表/四槽/digest），不触 DB。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from app.infra.clock import ISO_FMT, now
from app.infra.crypto import sm3_digest

# ---------- 五角色（冻结值照抄 prototype roles.js——00 §9.1） ----------


@dataclass(frozen=True, slots=True)
class RoleProfile:
    """单角色档案：key＝X-Dev-User 取值（sys_user.id 同源，99 §2.1）；display＝who 展示格式。"""

    key: str
    display: str


ROLE_REGISTRY: dict[str, RoleProfile] = {
    "laowang": RoleProfile(key="laowang", display="老王 · 油藏工程师"),
    "xiaoli": RoleProfile(key="xiaoli", display="小李 · 地质/质检"),
    "zhuren": RoleProfile(key="zhuren", display="主任 · 汇报人"),
    "aqiang": RoleProfile(key="aqiang", display="阿强 · 平台运维"),
    "shixi": RoleProfile(key="shixi", display="实习生 · 作业区"),
}

# 缺省角色（00 §2.4「缺省落默认角色」——docs/prd.md 拍板：默认角色＝阿强）。
DEFAULT_ROLE_KEY = "aqiang"


@dataclass(frozen=True, slots=True)
class Actor:
    """当前操作者值对象（who 字段服务端解析的唯一来源——00 §2.2）。"""

    user_id: str  # 角色键（laowang…）
    display: str  # label 全名——who 的展示格式（00 §9.1）

    @property
    def who(self) -> str:
        """留痕 who 槽取值＝label 全名（B1 活动流口径，00 §9.1）。"""
        return self.display


class UnauthenticatedError(Exception):
    """身份解析失败（00 §2.3 401 语义）——接口层统一映射错误包 401。"""


def resolve_actor(actor_id: str | None) -> Actor:
    """身份解析 seam（98 §3.13 authenticate；ADR 拍板稿名 resolve_actor，同位同义）。

    开发期实现（ADR-0003 裁决 5）＝解析 X-Dev-User 请求头取值：
    - None/空白 → 缺省落默认角色（00 §2.4；默认＝aqiang，PRD 拍板）——**不 401**；
    - 非五角色键 → UnauthenticatedError（401＝身份解析失败，00 §2.3）；
    - 五角色键精确匹配（roles.js 冻结值，不做人名大小写归一）。

    OAuth2.0 替换缝（00 §2.4「接 OAuth 只换一处」）：生产接入只替换本函数
    实现，本签名与 401 语义、各册合同/DTO 零改动。
    """
    key = (actor_id or "").strip()
    if not key:
        key = DEFAULT_ROLE_KEY
    profile = ROLE_REGISTRY.get(key)
    if profile is None:
        raise UnauthenticatedError(
            f"身份解析失败——X-Dev-User={actor_id!r} 未登记"
            f"（五角色键：{'、'.join(ROLE_REGISTRY)}）"
        )
    return Actor(user_id=profile.key, display=profile.display)


# ---------- 页面组闸（authorize 的 PageGroup 分支——00 §2.3/§9.2） ----------

PageGroup = Literal["工作台", "报告库", "指标与术语", "设置中心", "考核与质量", "平台"]

# 组级可见规则照抄 prototype roles.js MENU（组级 roles 字段缺省＝全员可见，
# 00 §9.2「运行时以 roles.js 为准」）；页级细分（A3/C2/C3/F1 等）随各页票落。
# 注：平台组 roles 缺省＝全员，F1 页级 aqiang 归 F1 票。
PAGE_GROUP_ROLES: dict[PageGroup, frozenset[str]] = {
    "工作台": frozenset(ROLE_REGISTRY),
    "报告库": frozenset(ROLE_REGISTRY),
    "指标与术语": frozenset(ROLE_REGISTRY),
    "设置中心": frozenset({"aqiang"}),
    "考核与质量": frozenset({"xiaoli", "aqiang", "zhuren"}),
    "平台": frozenset(ROLE_REGISTRY),
}


class ForbiddenError(Exception):
    """已认证但越权（00 §2.3 403 语义）——接口层统一映射错误包 403。"""


def authorize(actor: Actor, target: PageGroup) -> None:
    """页面组闸（98 §3.13 authorize 的 PageGroup 分支）。

    98 卡签名还有 Capability（五层能力闸）分支——随 D3 权限矩阵批扩展，
    本票只有组闸（越界自查：不越 D3 整页票的工）。判例（00 §2.3）：403 留给
    直调越权；列表/面板路径走过滤不报 403。
    """
    if actor.user_id not in PAGE_GROUP_ROLES[target]:
        raise ForbiddenError(
            f"「{target}」组仅 {'、'.join(sorted(PAGE_GROUP_ROLES[target]))} 角色可见"
            f"——{actor.display} 直调越权"
        )


# ---------- 审计语义（00 §8 四槽——B12 唯一写口的入参与读面投影） ----------


@dataclass(frozen=True, slots=True)
class AuditRow:
    """审计语义四槽（00 §8.1：时间/操作者/动作/内容）＋存储预留位。

    security.audit 唯一写口（B12）的入参；各模块的横切留痕都经此入参表达，
    列形投影（when/who/agent/what、time/who/action/target…四族）不收编
    （00 §14-R10）——各面投影在各自读口组装。
    """

    who: str  # 操作者槽：label 全名（Actor.display）；低风险自动执行＝「系统」（00 §2.2）
    action: str  # 动作槽：域内语义串（拦截也是审计事件——00 §8.2）
    content: str  # 内容槽：人话内容；D3 面不落正文只落 digest（99 §2.1）
    at: datetime | None = None  # 时间槽：None → infra.clock.now()（B14）
    meta: Mapping[str, Any] | None = None  # jsonb 预留位：trace_id/主体等（99 §2.1）

    def resolved_at(self) -> datetime:
        """时间槽落定：显式传参优先（回放/测试），否则统一时钟（B14）。"""
        return self.at if self.at is not None else now()


def audit_digest(row: AuditRow) -> str:
    """digest＝SM3 摘要指纹（D3 audit-logs——永不落正文；00 §8.1/§11）。

    哈希输入口径为合同悬置处的本仓拍板（99 §1.7.3：应用层计算、不依赖 DB
    函数）：ISO 时间|who|action|content 的 UTF-8 字节——篡改可见，正文不进
    digest 读面。口径变更即换指纹空间，只动本函数。
    """
    canonical = (
        f"{row.resolved_at().strftime(ISO_FMT)}|{row.who}|{row.action}|{row.content}"
    )
    return sm3_digest(canonical)


@dataclass(frozen=True, slots=True)
class AuditFilter:
    """audit_logs 读面筛选（D3 端点 14 骨架；合同未冻结筛选参数——who/action 预留槽）。"""

    who: str | None = None
    action: str | None = None


@dataclass(frozen=True, slots=True)
class AuditLogView:
    """D3 面投影（time/who/action/digest 四列形——D3 端点 14 合同值）。

    刻意无 content 字段：正文不出门，只出 SM3 指纹（00 §8.1「永不落正文」）。
    time 保持 datetime——ISO 串化是接口层表示职责（00 §1.4 机器时间戳）。
    """

    time: datetime
    who: str
    action: str
    digest: str

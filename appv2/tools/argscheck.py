"""tools.argscheck —— args_schema 校验器（JSON Schema 常用子集，确定性零依赖）。

specs/tools.md 行为约定 2：「参数先经 args_schema 校验：不合→failed(bad_args)
不触引擎」。本模块是那道闸的单点实现——只收本仓工具实际声明的子集（type/
properties/required/additionalProperties/items/enum/minLength/minimum），
不引第三方 jsonschema 库（依赖面零新增）；布尔不冒充整数（isinstance(bool, int)
陷阱显式封堵——RetrievalNeed 同款纪律）。

校验失败＝ArgsError（ValueError 子类）——registry.call 捕获转 failed(bad_args)，
引擎零调用；校验只判形不改值（原样 dict 返回，零隐式类型强转）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ArgsError(ValueError):
    """参数校验/装配失败（bad_args 的工具层来源——registry 捕获转 failed）。"""


def validate_args(
    schema: Mapping[str, Any], args: Mapping[str, Any]
) -> dict[str, Any]:
    """按 args_schema 校验参数（子集语义；通过＝原样返回 dict 副本）。"""
    if not isinstance(args, dict):
        raise ArgsError(
            f"参数须为对象（jsonschema type=object），得到 {type(args).__name__}"
        )
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        unknown = sorted(str(key) for key in args if key not in properties)
        if unknown:
            raise ArgsError(
                f"未知参数键：{unknown}（args_schema additionalProperties=false）"
            )
    for key in schema.get("required", []):
        if key not in args:
            raise ArgsError(f"缺少必填参数：{key}")
    for key, value in args.items():
        prop_schema = properties.get(key)
        if prop_schema is not None:
            _validate_value(str(key), value, prop_schema)
    return dict(args)


def _validate_value(key: str, value: Any, prop_schema: Mapping[str, Any]) -> None:
    """单键递归校验（type/enum/minLength/minimum/items——声明了才查）。"""
    type_spec = prop_schema.get("type")
    if type_spec is not None:
        type_names: tuple[Any, ...] = (
            (type_spec,) if isinstance(type_spec, str) else tuple(type_spec)
        )
        if not any(_matches_type(value, str(name)) for name in type_names):
            raise ArgsError(
                f"参数 {key} 类型须为 {list(type_names)}，得到 {type(value).__name__}"
            )
    if "enum" in prop_schema and value not in prop_schema["enum"]:
        raise ArgsError(f"参数 {key} 越界（允许 {prop_schema['enum']}）：{value!r}")
    min_length = prop_schema.get("minLength")
    if isinstance(value, str) and min_length is not None and len(value) < min_length:
        raise ArgsError(f"参数 {key} 长度须 ≥{min_length}：{value!r}")
    minimum = prop_schema.get("minimum")
    if _is_number(value) and minimum is not None and value < minimum:
        raise ArgsError(f"参数 {key} 须 ≥{minimum}：{value!r}")
    items_schema = prop_schema.get("items")
    if isinstance(value, list) and items_schema is not None:
        for index, item in enumerate(value):
            _validate_value(f"{key}[{index}]", item, items_schema)


def _matches_type(value: Any, type_name: str) -> bool:
    """JSON Schema 类型判定（boolean/integer 分立——bool 不冒充 int）。"""
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return _is_number(value)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "null":
        return value is None
    return True  # 未声明子集内的类型名不拦（schema 由本仓工具定义，无外来输入面）


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

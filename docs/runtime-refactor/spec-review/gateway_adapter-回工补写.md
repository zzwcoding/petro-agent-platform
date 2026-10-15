- 日期：2026-10-15 ｜ 状态：**回工补写**（复审⑦ F1/F3/F4/F5 修法；本件为首建——此前本规格无回工补写记录）
- 本次只改 `specs/gateway_adapter.md`（156→157 行）＋本记录，其它文件未动（`appv2/runtimev2/gateway_adapter/fake.py`／`appv2/runtime/llm.py` 未动——只作现状锚引用）；未 git commit（主窗统一提交）。

## 修法记录（复审⑦：F1 重试配置现状锚 ＋ F3 同形签名口径 ＋ F4 `calls` 观测面 ＋ F5 锚错位）——2026-10-15

### 1.（F1）行为 6「按配置的重试次数与退避」补现状锚——已补

- 行为 6（`specs/gateway_adapter.md:85`）括注补：缺省值以现状 env 面 `appv2/runtime/llm.py`（:47-49）的 `GATEWAY_429_RETRIES`／`GATEWAY_429_BACKOFF` 为**现状锚**（env 可覆写）；**正式数值阶段 5 随真机定**，本规格不复制字面值。行号引用按本仓体例置于反引号外；被锚文件实读核对：`:47-49` 恰为 `GATEWAY_429_RETRIES_DEFAULT = 3`／`GATEWAY_429_BACKOFF_DEFAULT = (5.0, 20.0, 60.0)`／`GATEWAY_429_JITTER = 0.1`。

### 2.（F3）替身 `run_id` 缺省 `""` vs 规格「同一签名」口径调和——已补

- 行为 11（:90）由「替身 `complete` 与生产桥**同一签名**与同一回执形状」改为「**同形签名（替身 `run_id` 可缺省＝测试便利，生产面必填）与同一回执形状**」。口径事实：生产面 `complete(messages, *, caller, run_id)` 必填（行为 2 入参面固定三件），替身 `fake.py` 的 `complete(..., run_id: str = "")` 缺省空串；接口定义块（:59）本就按替身实面写 `run_id: str = ""`，本批只调和行为 11 措辞，接口块与替身代码均未动。

### 3.（F4）替身 `calls` 公开留痕属性纳入规格观测面——已补（两处＋一注）

- **接口定义块**（:60）：`ScriptedCompleter` 下新增 `calls: list[tuple[str, list[dict[str, str]]]]` 一行（注释：「公开留痕属性（测试断言专用）：逐调用 (caller, messages 拷贝) 快照」），与 `counts()`／`messages_of()` 并列；形状与 `fake.py:57` 的 `self.calls` 实面逐字同形。
- **行为 5 断言**（:84）：「替身 `counts()`／`messages_of()` 与 calllog 行同口径」补 `calls` 并注「测试断言专用」。
- **行为 11**（:90）：观测面枚举同步补 `calls`（只读留痕、不改注入剧本的既有约束覆盖它）。

### 4.（F5）「不做什么」自由参数透传行锚错位——已改

- 「不做什么」表该行锚点（:21）由「本规格行为 3」改为「**本规格行为 2**」——自由参数面（无自由 `params`、未知键报错）的行为落点是行为 2「入参面固定三件」，行为 3 是回执面恒全键，原锚指错行。

### 契约与闸核对

- 本批四项均为规格文本层修正，不触及 importlinter 契约（R5b／R6／R7／R8／V2 B6 语义不变）；未改 toml。

### 验证

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                  # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：20 份规格的真源引用与边界规则编号均可解析。   # exit 0
```

（本批改后实跑均 exit 0；替身看守件 `tests/runtimev2/test_gateway_adapter_fake.py` 本批未动、未重跑——规格措辞调和不涉代码面。）

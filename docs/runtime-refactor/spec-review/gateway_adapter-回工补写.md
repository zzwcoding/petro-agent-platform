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

## W3 前规格微修正批：:86 重试口径回改（2026-10-16，流水 53-D）

- 依据：`docs/runtime-refactor/00-决议与方法.md` 流水 53「**裁定 D＝重试口径以行为 6 为准**」——原 `specs/gateway_adapter.md:86`（行为 7）「前两类可重试、后两类不可重试」与行为 6／接口注／B7b 前提（网络错可重试）三处相抵。
- 范围：只改 `specs/gateway_adapter.md:86`（一句）＋本记录；**行为 6 与接口注未动**；未 git commit。

### 改动

| 落点 | 改前 → 改后 |
|---|---|
| `specs/gateway_adapter.md:86`（行为 7） | 「…；**前两类可重试、后两类不可重试**。」→「…；**可重试＝限流／超时／网络错／5xx（三类：`rate_limited`／`timeout`／`upstream_unavailable`）；不可重试＝`rejected` 等客户端拒绝（4xx 业务性拒绝）**——2026-10-16 回改（流水 53-D）：原「前两类可重试、后两类不可重试」与行为 6／接口注／B7b 前提（网络错可重试）相抵，按行为 6 落，本批只回改此句（行为 6／接口注未动）。」 |

- 同行后段（「分层辨明」／现状锚／跨块待办／断言）逐字未动。**断言句未对齐**（「`rejected` 类一次即抛、`rate_limited`／`timeout` 类重试到上限」）——该句是示例枚举、与改后口径不冲突（可重试完整集以上文三类为准）。
- 实现面**只读核对、未改**：`appv2/runtimev2/gateway_adapter/bridge.py:15-17／59-60` 已按「可重试＝前三类（`rate_limited`／`timeout`／`upstream_unavailable`）／`rejected` 一次即抛」落——本批把规格的**陈述**与实现对齐，无代码改动。

### 闸与验证（本批实跑）

```
$ uv run python tools/check_specs.py          → spec gate: PASS（0 警告）            exit 0
$ uv run python tools/ref_resolvable.py check → 真源引用可解析闸绿：22 份规格可解析   exit 0
$ uv run python -m pytest -q（全量，排除 3 个 real smoke 文件）
                                              1910 passed, 105 skipped in 77.78s   exit 0
$ uv run lint-imports ／ uv run lint-imports --config tools/importlinter_v2.toml
                                              6 kept,0 broken ／ 18 kept,0 broken  exit 0
```

### 上报项（非本批擅改，报主窗）

1. **接口注（`:65`）的「前两类」标签**：该行括注已写「（429／超时／网络错／5xx）」（＝行为 6 同口径），但标签词「重试**只对前两类**」仍沿用旧「两类」计数（四类枚举里数不出两类）。本批按范围（不改接口注）原样保留；若要收净该标签，属下一批一字改，宜与派生视图同步同批。
2. **派生视图待同步（讲释层，Owner 亲产面）**：`docs/runtime-refactor/explain/gateway_adapter-讲释.md:52` 逐字引用了被回改的旧句（「前两类可重试、后两类不可重试」＋「四类失败只有前两类够格重试」）——该层自声明「规格改，本文即废」，随派生视图节奏同步（本批未动讲释层）。
3. **已收票历史引文**：`tickets/v2-refactor/RT-W2-03a-gateway_adapter.md:67`（W2 已收票）施工基准行照抄旧句；已收票面属历史记录，本批未回改（如需追溯更正由主窗裁）。

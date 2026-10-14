# V2-80f · LLM 调用全量留痕（发送 messages＋返回全文——B6 单点接线）

状态: **随票实施** ｜ 来源: Owner 2026-10-14「我要看 llm 发送的 和 发回的 内容 完整记录」——现状调用即焚（库里只有状态快照与计费行），无原始收发记录

## 0. 本票一句话

在 B6 唯一出口（GatewayService.complete）加**调用级全量留痕**：每次 LLM 调用的发送 messages 全文、返回全文、token、耗时、路由别名、run_id/caller 归属——逐行 JSONL 落 `logs/llm_calls/YYYYMMDD.jsonl`（按日分文件）。成功与失败（429/超时/切换）都留痕。开关 `LLM_CALL_LOG`（缺省 on，off 关闭），留痕故障绝不影响调用（try/except 降级）。

## 1. 施工伪代码

```python
# appv2/infra/gateway/calllog.py（新文件——纯函数＋文件写，零依赖）
def record_call(*, alias, caller, run_id, messages, content=None,
                prompt_tokens=0, completion_tokens=0, duration_ms=0,
                error=None, requested=None) -> None:
    if os.environ.get("LLM_CALL_LOG", "on").strip().lower() == "off": return
    rec = {"ts": now_iso, "run_id": run_id or "", "caller": caller,
           "requested": requested, "alias": alias,
           "messages": messages,                       # 发送全文（逐条 role/content）
           "response": {"content": content, "prompt_tokens": …,
                        "completion_tokens": …, "duration_ms": …},  # 返回全文
           "error": error}                             # 失败留痕（成功为 None）
    try: logs/llm_calls/YYYYMMDD.jsonl 追加一行（utf-8）
    except Exception: LOGGER.warning（留痕故障不影响调用）

# gateway/service.py complete()：
for candidate …:
    for _attempt …:
        try:
            answer = await self._backend.complete(...)
            record_call(alias=candidate, caller=caller, run_id=params.get("run_id"),
                        messages=messages, content=answer.content, …tokens, duration)
            break
        except UpstreamUnavailable as exc:
            record_call(…, error=f"{exc.reason}", …)   # 失败尝试也留痕
# 4xx/429 直抛路径：complete() 外层 try/except Exception 记 error 行后 re-raise
```

## 2. 理由

- B6 单点落位——所有调用（V1/V2/桌面）一次接线全量覆盖，无第二处；
- JSONL 按日分文件＝观测面最简（无需迁移；DB 表随 80b 观测层再议）；
- 失败留痕治「429 循环黑箱」——上次额度耗尽只能靠服务日志拼，留痕后每次尝试可查。

## 3. 测试与验收

- 单测：record_call 写行结构（messages 全文/response/error 三形）；off 开关零写；写失败不影响调用；
- 接线钉：gateway complete 后 JSONL 增行；
- 真机：重跑「上回杆断躺的那口…」一问——JSONL 里能看到 understand 发送全文＋原始回文（两行式）、clarify 发送全文＋决策 JSON 原文（含澄清循环的每一轮收发）。

## 4. 边界红线

留痕故障不冒泡（LOGGER.warning 降级）；不改 messages 组装与回文语义（纯旁路观测）；密钥/系统提示词本就随调用走——JSONL 含完整 messages，logs/ 已在 .gitignore（不入仓）；零新依赖。

## 5. 完工记录（2026-10-14）

- calllog.py 上岗＋gateway.complete 内层接线（成功/失败尝试全量记录，LLM_CALL_LOG=off 可关，
  留痕故障降级不冒泡）；三枚钉测；全量 1749 过（基线 1746＋3）＋六闸绿；
- 真机演示：重跑「上回杆断躺的那口…」——logs/llm_calls/20261014.jsonl 落下该 run 全部
  收发原文（发送 messages 全文＋返回 content 全文＋token/耗时）。

# WEK1 存档：默认 2048 输出预算的跑批（2026-10-17 15:4x）

第一批跑批走 `weknora chat` 默认链路，单次输出预算 2048 token
（types/agent.go DefaultMaxCompletionTokens quick-answer 缺省值）。
MiniMax-M3 思考段较长，22/81 题在思考中途耗尽预算，正文为空。

处理：创建自定义 agent（quick-answer + max_completion_tokens=32768），
全量 81 题改用 `session ask --agent` 统一重跑（WEK2）。
本目录保留原始记录供台账追溯。

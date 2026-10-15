"""替身地基自证（eng/04 §五步骤 1 第一件）：剧本应答分流＋逐轮 messages 回看＋默认兜底。

被测件＝appv2.runtimev2.gateway_adapter.ScriptedCompleter（modules.md gateway_adapter
卡 Seam 点名的测试替身——存量离线测试改接线的地基）。全部离线：替身本旨就是
runtimev2 测试零触网。卡面公开接口钉（`async complete(messages, *, caller, run_id)
-> ModelReply`——2026-10-15 随阶段 3 规格回写）在本件看守。
"""

from __future__ import annotations

import inspect

import pytest

from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter


def _messages(*texts: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": t} for t in texts]


# ---------- 剧本应答分流 ----------


class TestScriptedRouting:
    async def test_caller_split(self) -> None:
        fake = ScriptedCompleter({"decision": ["甲"], "answer": ["乙"]})
        assert (await fake.complete(_messages("问"), caller="decision")).content == "甲"
        assert (await fake.complete(_messages("答"), caller="answer")).content == "乙"

    async def test_queue_multiturn_replay_last_sticky(self) -> None:
        """多轮 replay：第二调用取第二条，末条驻留（同旧件语义）。"""
        fake = ScriptedCompleter({"m": ["一", "二", "三"]})
        assert (await fake.complete(_messages("r1"), caller="m")).content == "一"
        assert (await fake.complete(_messages("r2"), caller="m")).content == "二"
        assert (await fake.complete(_messages("r3"), caller="m")).content == "三"
        assert (await fake.complete(_messages("r4"), caller="m")).content == "三"


# ---------- 观测面：留痕／计数／messages 回看 ----------


class TestObservationFaces:
    async def test_calls_log_captures_caller_and_messages_in_order(self) -> None:
        fake = ScriptedCompleter({"a": ["x"], "b": ["y"]})
        await fake.complete(_messages("q1"), caller="a")
        await fake.complete(_messages("q2", "q3"), caller="b")
        assert fake.calls == [
            ("a", [{"role": "user", "content": "q1"}]),
            ("b", [{"role": "user", "content": "q2"}, {"role": "user", "content": "q3"}]),
        ]

    async def test_counts(self) -> None:
        fake = ScriptedCompleter({"a": ["x"], "b": ["y"]})
        await fake.complete([], caller="a")
        await fake.complete([], caller="a")
        await fake.complete([], caller="b")
        assert fake.counts() == {"a": 2, "b": 1}

    async def test_messages_of_per_round(self) -> None:
        fake = ScriptedCompleter({"a": ["x"], "b": ["y"]})
        await fake.complete(_messages("q1"), caller="a")
        await fake.complete(_messages("q2"), caller="b")
        await fake.complete(_messages("q3"), caller="a")
        assert fake.messages_of("a") == [
            [{"role": "user", "content": "q1"}],
            [{"role": "user", "content": "q3"}],
        ]
        assert fake.messages_of("ghost") == []

    async def test_messages_snapshot_isolated_from_caller_mutation(self) -> None:
        """留痕是调用时刻快照——调用方事后篡改不回写（断言面不串场）。"""
        fake = ScriptedCompleter({"m": ["答"]})
        msgs = [{"role": "user", "content": "问"}]
        await fake.complete(msgs, caller="m")
        msgs[0]["content"] = "篡改"
        assert fake.messages_of("m")[0][0]["content"] == "问"

    async def test_script_injection_readonly(self) -> None:
        """INV-2 同款：注入剧本不被替身改写（构造即拷贝）。"""
        script = {"m": ["一", "二"]}
        fake = ScriptedCompleter(script)
        await fake.complete([], caller="m")
        await fake.complete([], caller="m")
        assert script["m"] == ["一", "二"]


# ---------- 默认兜底 ----------


class TestDefaultFallback:
    async def test_unscripted_caller_gets_default_and_is_recorded(self) -> None:
        fake = ScriptedCompleter({"m": ["甲"]}, default="兜底")
        assert (await fake.complete(_messages("q"), caller="m")).content == "甲"
        assert (await fake.complete(_messages("q"), caller="ghost")).content == "兜底"
        assert fake.counts() == {"m": 1, "ghost": 1}
        assert fake.messages_of("ghost") == [[{"role": "user", "content": "q"}]]

    async def test_unscripted_without_default_fails_fast(self) -> None:
        """无 default＝当场暴露（旧件「剧本耗尽」纪律——不静默）。"""
        fake = ScriptedCompleter({"m": ["甲"]})
        with pytest.raises(AssertionError, match="ghost"):
            await fake.complete([], caller="ghost")

    async def test_empty_script_entry_is_unscripted(self) -> None:
        fake = ScriptedCompleter({"m": []})
        with pytest.raises(AssertionError):
            await fake.complete([], caller="m")

    async def test_empty_script_entry_uses_default(self) -> None:
        fake = ScriptedCompleter({"m": []}, default="兜底")
        assert (await fake.complete([], caller="m")).content == "兜底"

    async def test_scripted_caller_never_falls_to_default(self) -> None:
        fake = ScriptedCompleter({"m": ["甲"]}, default="兜底")
        assert (await fake.complete([], caller="m")).content == "甲"
        assert (await fake.complete([], caller="m")).content == "甲"


# ---------- 公开接口卡面形 ----------


class TestCardFace:
    async def test_complete_signature_matches_card(self) -> None:
        """卡公开接口：async complete(messages, *, caller, run_id) -> ModelReply。"""
        sig = inspect.signature(ScriptedCompleter.complete)
        assert list(sig.parameters) == ["self", "messages", "caller", "run_id"]
        assert sig.parameters["caller"].kind is inspect.Parameter.KEYWORD_ONLY
        assert sig.parameters["run_id"].kind is inspect.Parameter.KEYWORD_ONLY
        assert inspect.iscoroutinefunction(ScriptedCompleter.complete)

    async def test_complete_returns_model_reply(self) -> None:
        fake = ScriptedCompleter({"m": ["答"]})
        reply = await fake.complete(_messages("q"), caller="m", run_id="run-1")
        assert isinstance(reply, ModelReply)
        assert reply.content == "答"
        assert (reply.caller, reply.run_id) == ("m", "run-1")
        assert reply.cached_tokens == 0  # 上游未上报＝0（钉 pin-25 同口径）
        assert reply.usage_estimated is True

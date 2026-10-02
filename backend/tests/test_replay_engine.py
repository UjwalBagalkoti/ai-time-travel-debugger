from app.replay_engine import ReplayEngine

def test_tool_cache_key_is_order_independent():
    engine = ReplayEngine()
    a = engine.tool_cache_key("lookup_order", {"order_id": 7, "user": "u"})
    b = engine.tool_cache_key("lookup_order", {"user": "u", "order_id": 7})
    assert a == b

def test_cached_tool_result_requires_exact_arguments():
    engine = ReplayEngine()
    history = [
        {
            "input": {"tool_name": "lookup_order", "arguments": {"order_id": 7}},
            "output": {"result": {"status": "shipped"}},
        }
    ]
    result, hit = engine.cached_tool_result(history, "lookup_order", {"order_id": 7})
    assert hit is True
    assert result == {"status": "shipped"}

    result, hit = engine.cached_tool_result(history, "lookup_order", {"order_id": 8})
    assert hit is False
    assert result is None

def test_cached_tool_result_handles_non_result_output():
    engine = ReplayEngine()
    history = [
        {
            "input": {"tool_name": "refund", "arguments": {"amount": 25}},
            "output": {"status": "accepted"},
        }
    ]
    result, hit = engine.cached_tool_result(history, "refund", {"amount": 25})
    assert hit is True
    assert result == {"status": "accepted"}

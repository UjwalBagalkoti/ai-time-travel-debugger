import pytest

from app.agent_tools import calculate, execute_builtin_tool


def test_calculator_handles_basic_math():
    assert calculate("(18 + 6) / 3") == 8
    assert calculate("2 ** 5") == 32


def test_calculator_rejects_code_and_names():
    with pytest.raises(ValueError):
        calculate("__import__('os').getcwd()")


def test_calculator_bounds_exponents_and_expression_size():
    with pytest.raises(ValueError):
        calculate("2 ** 9")
    with pytest.raises(ValueError):
        calculate("1" * 201)


def test_builtin_tool_allowlist_and_utc_clock():
    assert execute_builtin_tool("calculator", {"expression": "10 * 4"}) == 40
    assert execute_builtin_tool("current_time", {}).endswith("+00:00")
    with pytest.raises(ValueError):
        execute_builtin_tool("shell", {})

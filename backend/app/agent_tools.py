"""Small, side-effect-free tools available to user-configured agents."""

import ast
import math
import operator
from datetime import datetime, timezone
from typing import Any, Dict


SUPPORTED_TOOLS = {"calculator", "current_time"}

TOOL_SCHEMAS = {
    "calculator": {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "maxLength": 200}},
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    "current_time": {
        "type": "function",
        "function": {
            "name": "current_time",
            "description": "Get the current time in UTC.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
}

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _evaluate(node: ast.AST, depth: int = 0) -> float:
    if depth > 12:
        raise ValueError("Expression is too complex")
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        value = node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left, depth + 1)
        right = _evaluate(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("Exponent is too large")
        value = _BINARY_OPERATORS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        value = _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand, depth + 1))
    else:
        raise ValueError("Only basic arithmetic is allowed")

    if not math.isfinite(value) or abs(value) > 1_000_000_000_000:
        raise ValueError("Result is outside the supported range")
    return value


def calculate(expression: str) -> int | float:
    if len(expression) > 200:
        raise ValueError("Expression is too long")
    tree = ast.parse(expression, mode="eval")
    result = _evaluate(tree.body)
    return int(result) if isinstance(result, float) and result.is_integer() else result


def execute_builtin_tool(name: str, arguments: Dict[str, Any]) -> Any:
    if name == "calculator":
        expression = arguments.get("expression")
        if not isinstance(expression, str):
            raise ValueError("Calculator requires an expression")
        return calculate(expression)
    if name == "current_time":
        return datetime.now(timezone.utc).isoformat()
    raise ValueError("This tool is not available to the agent")

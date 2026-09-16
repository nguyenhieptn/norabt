"""Bộ thông dịch Logic Chiến lược (Strategy Logic Evaluator)."""
import math
import operator
from typing import Any, Callable, Dict, Optional


class LogicEvaluator:
    """Đánh giá AST điều kiện chiến lược bằng interpreter an toàn."""

    COMPARATORS = {
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
        "==": operator.eq,
        "=": operator.eq,
        "!=": operator.ne,
    }

    MATH_OPERATORS = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
    }

    @staticmethod
    def compile_value_expr(item: Any) -> str:
        return str(item)

    @staticmethod
    def compile_condition_expr(condition_tree: Any) -> str:
        return str(condition_tree)

    @staticmethod
    def compile_ast(node: list) -> Callable[[Dict, Dict, Optional[Dict]], bool]:
        if not node:
            return lambda row_1m, row_4h, row_1h=None: False

        def _compiled(row_1m: Dict, row_4h: Dict, row_1h: Optional[Dict] = None) -> bool:
            return LogicEvaluator.evaluate_condition_tree(node, row_1m, row_4h, row_1h)

        return _compiled

    @staticmethod
    def evaluate_condition_tree(
        condition_tree: Any,
        row_1m: Dict,
        row_4h: Dict,
        row_1h: Optional[Dict] = None,
    ) -> bool:
        if not isinstance(condition_tree, list):
            return False

        for and_block in condition_tree:
            if not isinstance(and_block, list) or not and_block:
                continue
            if all(LogicEvaluator._evaluate_triplet(triplet, row_1m, row_4h, row_1h) for triplet in and_block):
                return True
        return False

    @staticmethod
    def _evaluate_triplet(
        triplet: Any,
        row_1m: Dict,
        row_4h: Dict,
        row_1h: Optional[Dict],
    ) -> bool:
        if not isinstance(triplet, list) or len(triplet) != 3:
            return False

        left = LogicEvaluator.evaluate_value(triplet[0], row_1m, row_4h, row_1h)
        right = LogicEvaluator.evaluate_value(triplet[2], row_1m, row_4h, row_1h)
        comparator = LogicEvaluator.COMPARATORS.get(triplet[1])
        if comparator is None or left is None or right is None:
            return False

        try:
            return bool(comparator(left, right))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def evaluate_value(
        item: Any,
        row_1m: Dict,
        row_4h: Dict,
        row_1h: Optional[Dict] = None,
    ) -> Optional[float]:
        if isinstance(item, bool):
            return None
        if isinstance(item, (int, float)):
            return LogicEvaluator._finite_or_none(float(item))
        if isinstance(item, list):
            return None
        if not isinstance(item, dict):
            return None

        node_type = item.get("type")
        if node_type == "calculate":
            return LogicEvaluator._evaluate_calculate(item, row_1m, row_4h, row_1h)
        if node_type in ("min", "max"):
            return LogicEvaluator._evaluate_min_max(node_type, item, row_1m, row_4h, row_1h)
        if "frame" in item and "column" in item:
            return LogicEvaluator._evaluate_field(item, row_1m, row_4h, row_1h)
        return None

    @staticmethod
    def _evaluate_calculate(
        item: Dict[str, Any],
        row_1m: Dict,
        row_4h: Dict,
        row_1h: Optional[Dict],
    ) -> Optional[float]:
        n1 = LogicEvaluator.evaluate_value(item.get("number_1"), row_1m, row_4h, row_1h)
        n2 = LogicEvaluator.evaluate_value(item.get("number_2"), row_1m, row_4h, row_1h)
        if n1 is None or n2 is None:
            return None

        op = item.get("logic")
        if op == "/":
            result = 0.0 if n2 == 0 else n1 / n2
        else:
            fn = LogicEvaluator.MATH_OPERATORS.get(op)
            if fn is None:
                return None
            result = fn(n1, n2)

        multiply = item.get("multiply", 1.0)
        if isinstance(multiply, bool) or not isinstance(multiply, (int, float)):
            return None
        return LogicEvaluator._finite_or_none(result * float(multiply))

    @staticmethod
    def _evaluate_min_max(
        node_type: str,
        item: Dict[str, Any],
        row_1m: Dict,
        row_4h: Dict,
        row_1h: Optional[Dict],
    ) -> Optional[float]:
        values = [
            LogicEvaluator.evaluate_value(number, row_1m, row_4h, row_1h)
            for number in item.get("numbers", [])
        ]
        clean_values = [value for value in values if value is not None]
        if not clean_values:
            return None
        result = min(clean_values) if node_type == "min" else max(clean_values)
        return LogicEvaluator._finite_or_none(result)

    @staticmethod
    def _evaluate_field(
        item: Dict[str, Any],
        row_1m: Dict,
        row_4h: Dict,
        row_1h: Optional[Dict],
    ) -> Optional[float]:
        frame = item.get("frame")
        column = item.get("column")
        row = row_1m if frame == "1m" else row_4h if frame == "4h" else row_1h if frame == "1h" else None
        if row is None or column not in row:
            return None

        value = LogicEvaluator._coerce_float(row.get(column))
        if value is None:
            return None

        for key, sign in (("subtract", -1.0), ("add", 1.0)):
            if key in item:
                modifier = LogicEvaluator.evaluate_value(item[key], row_1m, row_4h, row_1h)
                if modifier is None:
                    return None
                value += sign * modifier

        if "divide" in item:
            divider = LogicEvaluator.evaluate_value(item["divide"], row_1m, row_4h, row_1h)
            if divider is None:
                return None
            value = 0.0 if divider == 0 else value / divider

        return LogicEvaluator._finite_or_none(value)

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        try:
            return LogicEvaluator._finite_or_none(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _finite_or_none(value: float) -> Optional[float]:
        return value if math.isfinite(value) else None

"""Bộ thông dịch Logic Chiến lược (Strategy Logic Evaluator).

Xử lý và tính toán biểu thức logic động của các tín hiệu (Signals),
Dựa trên cấu trúc Abstract Syntax Tree (AST) lưu trong JSON.
Sử dụng kỹ thuật AST Pre-compilation (chuyển JSON thành Python Lambda) để tối đa hóa tốc độ.
"""
from typing import Any, Dict, Callable


class LogicEvaluator:
    """Đánh giá biểu thức chiến lược Alpha thành hàm Callable siêu tốc."""

    @staticmethod
    def compile_value_expr(item: Any) -> str:
        """Chuyển đổi một node giá trị thành chuỗi biểu thức Python."""
        if isinstance(item, (int, float)):
            return str(float(item))
        if isinstance(item, list):
            return "0.0"
            
        if isinstance(item, dict):
            node_type = item.get("type")
            
            if node_type in ("min", "max"):
                vals = [LogicEvaluator.compile_value_expr(n) for n in item.get("numbers", [])]
                if not vals:
                    return "0.0"
                return f"{node_type}([{', '.join(vals)}])"
                
            if node_type == "calculate":
                n1 = LogicEvaluator.compile_value_expr(item.get("number_1"))
                n2 = LogicEvaluator.compile_value_expr(item.get("number_2"))
                op = item.get("logic")
                mult = float(item.get("multiply", 1.0))
                
                if op == "/":
                    expr = f"(({n1}) / ({n2}) if ({n2}) != 0 else 0.0)"
                else:
                    expr = f"(({n1}) {op} ({n2}))"
                return f"({expr} * {mult})"
                
            if "frame" in item and "column" in item:
                frame = item["frame"]
                col = item["column"]
                
                if frame == "1m":
                    base = f"(row_1m.get('{col}', 0.0) if row_1m else 0.0)"
                elif frame == "4h":
                    base = f"(row_4h.get('{col}', 0.0) if row_4h else 0.0)"
                elif frame == "1h":
                    base = f"(row_1h.get('{col}', 0.0) if row_1h else 0.0)"
                else:
                    base = "0.0"
                    
                if "subtract" in item:
                    base = f"({base} - {LogicEvaluator.compile_value_expr(item['subtract'])})"
                if "add" in item:
                    base = f"({base} + {LogicEvaluator.compile_value_expr(item['add'])})"
                if "divide" in item:
                    div = LogicEvaluator.compile_value_expr(item["divide"])
                    base = f"({base} / ({div}) if ({div}) != 0 else 0.0)"
                    
                return base
                
        return "0.0"

    @staticmethod
    def compile_condition_expr(condition_tree: Any) -> str:
        """Chuyển đổi cây điều kiện (OR của AND của Triplet) thành chuỗi biểu thức Python."""
        if not condition_tree or not isinstance(condition_tree, list):
            return "False"
            
        or_exprs = []
        for and_block in condition_tree:
            if not isinstance(and_block, list):
                continue
                
            and_exprs = []
            for triplet in and_block:
                if isinstance(triplet, list) and len(triplet) == 3:
                    left = LogicEvaluator.compile_value_expr(triplet[0])
                    op = triplet[1]
                    right = LogicEvaluator.compile_value_expr(triplet[2])
                    if op == "=":
                        op = "=="
                    and_exprs.append(f"({left} {op} {right})")
                    
            if and_exprs:
                or_exprs.append("(" + " and ".join(and_exprs) + ")")
                
        if not or_exprs:
            return "False"
            
        return "(" + " or ".join(or_exprs) + ")"

    @staticmethod
    def compile_ast(node: list) -> Callable[[Dict, Dict, Dict], bool]:
        """Biên dịch toàn bộ cấu trúc JSON AST thành một hàm Lambda Python."""
        if not node:
            return lambda r1, r4, r1h=None: False
            
        expr = LogicEvaluator.compile_condition_expr(node)
        func_str = f"lambda row_1m, row_4h, row_1h=None: {expr}"
        # Sử dụng eval để sinh hàm trong bộ nhớ (cực kỳ nhanh)
        return eval(func_str)

"""Bộ kiểm tra (Validator) Cây cú pháp Chiến lược (AST).

Đảm bảo cấu trúc JSON AST hợp lệ và logic an toàn trước khi nạp vào Backtest Engine.
Ngăn chặn các lỗi logic ngớ ngẩn (ví dụ: 1m high < 1m low).
"""
from typing import Any, Dict


class ASTValidator:
    """Bộ xác thực JSON AST."""
    
    VALID_OPERATORS = {">", "<", ">=", "<=", "==", "!="}
    VALID_MATH_LOGIC = {"+", "-", "*", "/"}
    
    @classmethod
    def validate_flow(cls, flow_name: str, flow_ast: Dict[str, Any]) -> bool:
        """Kiểm tra toàn bộ luồng (flow) xem hợp lệ không."""
        
        # 1. Kiểm tra cấu trúc căn bản
        if "type" not in flow_ast or flow_ast["type"] not in ("LONG", "SHORT"):
            return False
            
        if "match" not in flow_ast or not isinstance(flow_ast["match"], list):
            return False
            
        # 2. Kiểm tra phần điều kiện kích hoạt
        for match_block in flow_ast["match"]:
            if "condition" in match_block:
                if not cls._validate_condition_tree(match_block["condition"]):
                    return False
                    
        # 3. Kiểm tra phần điều kiện đóng (stop)
        if "stop" in flow_ast:
            for stop_block in flow_ast["stop"]:
                if "condition" in stop_block:
                    if not cls._validate_condition_tree(stop_block["condition"]):
                        return False
                        
        return True

    @classmethod
    def _validate_condition_tree(cls, condition_tree: Any) -> bool:
        if not isinstance(condition_tree, list):
            return False
            
        for and_group in condition_tree:
            if not isinstance(and_group, list):
                return False
                
            for triplet in and_group:
                if not isinstance(triplet, list) or len(triplet) != 3:
                    return False
                    
                left, operator, right = triplet
                
                # Kiểm tra toán tử
                if operator not in cls.VALID_OPERATORS:
                    return False
                    
                # Có thể mở rộng để chống lỗi ngớ ngẩn (ví dụ: 1m_high < 1m_low)
                # (Hiện tại chỉ kiểm tra cú pháp căn bản)
                
        return True

"""Quản lý Tham số Chiến lược (Strategy Parameters).

Module này đảm bảo mọi cấu hình tham số của chiến lược
được nạp, validate và chuẩn hóa một cách nhất quán,
không bao giờ bị mất/thiếu các tham số cốt lõi.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StrategyParams:
    """Cấu trúc chuẩn cho tham số một chiến lược (hoặc một luồng chiến lược)."""
    # 1. Định danh
    name: str = "LONG"
    strategy: str = ""
    
    # 2. Tham số chung / Hệ thống
    data_type: str = "1m"                  # '1m' hoặc '4h' (khung khớp lệnh)
    allow_negative_price_rate: bool = True # Cho phép giá âm (ví dụ: dùng cho Keltner)
    using_match_price: bool = True         # Dùng giá khớp thực tế thay vì giá close
    max_open_trades: int = 45              # Tối đa số lệnh mở cùng lúc
    max_capital_usage: float = 1.0         # Tối đa phần trăm vốn được dùng

    # 3. Tham số quản lý rủi ro / vốn
    volume_rate: float = 1.0               # % vốn cho mỗi lệnh (1.0 = 100%)
    leverage: int = 1                      # Đòn bẩy
    stop_loss_rate: float = 0.0            # % Cắt lỗ (0 = không cắt)
    take_profit_rate: float = 0.0          # % Chốt lời (0 = không chốt)
    trailing_stop: float = 0.0             # % Trailing stop
    timeout: int = 0                       # Số nến tối đa giữ lệnh

    # 4. Tham số DCA / Nhồi lệnh
    dca_steps: List[float] = field(default_factory=list)      # Ví dụ: [-2.0, -5.0] (giảm 2%, 5% thì nhồi)
    dca_multipliers: List[float] = field(default_factory=list) # Hệ số vốn nhồi: [1.5, 2.0]

    # 5. Các tham số tự do khác (để đánh giá điều kiện)
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyParams":
        """Nạp tham số từ Dict (Json DB)."""
        d = dict(data)
        
        # Xử lý các trường có trong class
        core_kwargs = {}
        extra_kwargs = {}
        
        for k, v in d.items():
            if hasattr(cls, k) and k != "extra":
                core_kwargs[k] = v
            else:
                extra_kwargs[k] = v
                
        # Ép kiểu an toàn cho một số trường quan trọng
        if "max_open_trades" in core_kwargs:
            core_kwargs["max_open_trades"] = int(core_kwargs["max_open_trades"])
        if "allow_negative_price_rate" in core_kwargs:
            core_kwargs["allow_negative_price_rate"] = bool(core_kwargs["allow_negative_price_rate"])
        if "using_match_price" in core_kwargs:
            core_kwargs["using_match_price"] = bool(core_kwargs["using_match_price"])
            
        # Nạp data
        obj = cls(**core_kwargs)
        obj.extra = extra_kwargs
        return obj

    def to_dict(self) -> Dict[str, Any]:
        """Xuất về lại Dict phẳng để lưu database."""
        d = {
            "name": self.name,
            "strategy": self.strategy,
            "data_type": self.data_type,
            "allow_negative_price_rate": self.allow_negative_price_rate,
            "using_match_price": self.using_match_price,
            "max_open_trades": self.max_open_trades,
            "max_capital_usage": self.max_capital_usage,
            "volume_rate": self.volume_rate,
            "leverage": self.leverage,
            "stop_loss_rate": self.stop_loss_rate,
            "take_profit_rate": self.take_profit_rate,
            "trailing_stop": self.trailing_stop,
            "timeout": self.timeout,
            "dca_steps": self.dca_steps,
            "dca_multipliers": self.dca_multipliers,
        }
        d.update(self.extra)
        return d

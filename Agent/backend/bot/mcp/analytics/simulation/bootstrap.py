from __future__ import annotations

from typing import Optional

import numpy as np


class BootstrapSampler:
    """Bộ lấy mẫu IID và moving-block, tất định được theo seed.

    KHÔNG PHẢI bộ lấy mẫu mà engine đang dùng. Không một đường chạy sản xuất
    nào gọi tới lớp này (chỉ `__init__.py` của package và một test tham
    chiếu). Ghi rõ ở đây vì nó dễ gây hiểu nhầm nghiêm trọng: `block_resample`
    dưới đây là MOVING-BLOCK bootstrap (Künsch, 1989) -- độ dài khối CỐ ĐỊNH,
    lấy từ các cửa sổ chồng lấn, KHÔNG vòng lại đầu chuỗi, nên chuỗi tái chọn
    KHÔNG dừng.

    Thứ mà báo cáo trích dẫn và engine thật sự chạy là STATIONARY bootstrap
    (Politis và Romano, 1994), cài trong
    `Agent/backend/mcp/analytics/simulation/monte_carlo.py::_simulate_horizon`:
    ở đó mỗi bước khởi động lại với xác suất 1/L nên độ dài khối là biến ngẫu
    nhiên HÌNH HỌC kỳ vọng L, chỉ số lấy modulo độ dài sổ lệnh nên chuỗi VÒNG
    TRÒN, và L = n^(1/3) theo tốc độ chuẩn. Ba điểm đó chính là cái phân biệt
    stationary bootstrap với moving-block.

    Đừng dùng lớp này cho phần mô phỏng rủi ro nếu không muốn đổi phương pháp
    thống kê mà báo cáo đang công bố.
    """

    @staticmethod
    def iid_resample(
        returns: np.ndarray,
        n_samples: int,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        if n_samples < 0:
            raise ValueError("n_samples must be non-negative")
        if len(returns) == 0:
            return np.zeros(n_samples, dtype=np.float64)
        generator = rng or np.random.default_rng(seed)
        indices = generator.integers(0, len(returns), size=n_samples)
        return returns[indices]

    @staticmethod
    def block_resample(
        returns: np.ndarray,
        n_samples: int,
        block_size: int = 4,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        if n_samples < 0:
            raise ValueError("n_samples must be non-negative")
        if block_size <= 0:
            raise ValueError("block_size must be positive")
        generator = rng or np.random.default_rng(seed)
        count = len(returns)
        if count <= block_size:
            return BootstrapSampler.iid_resample(returns, n_samples, rng=generator)
        block_count = int(np.ceil(n_samples / block_size))
        starts = generator.integers(0, count - block_size + 1, size=block_count)
        indices = (starts[:, None] + np.arange(block_size)).reshape(-1)[:n_samples]
        return returns[indices]

"""Bộ phân tích và Xếp hạng kết quả Tối ưu hoá (Metrics Ranker).

Phân tích kết quả trả về từ Runner, lọc bỏ các bộ thông số không khả thi (VD: Drawdown cao)
Và xếp hạng (Rank) để tìm ra bộ thông số vàng (Golden Params).
"""
from typing import Dict, List, Any


class ResultsRanker:
    """Xếp hạng các tổ hợp cấu hình dựa trên tiêu chí lợi nhuận và rủi ro."""

    @staticmethod
    def rank_results(
        results: List[Dict[str, Any]],
        sort_by: str = "pnl",
        min_trades: int = 5,
        max_drawdown: float = 30.0,
        min_winrate: float = 40.0
    ) -> List[Dict[str, Any]]:
        """Lọc và sắp xếp danh sách kết quả.
        
        Args:
            results: Danh sách kết quả từ OptimizeRunner.
            sort_by: Tiêu chí sắp xếp ("pnl", "winrate", "sharpe").
            min_trades: Bỏ qua các chiến lược có quá ít lệnh.
            max_drawdown: Cắt bỏ các chiến lược có độ sụt giảm % cao hơn mức này.
            min_winrate: Cắt bỏ các chiến lược có tỷ lệ thắng thấp.
        """
        valid_results = []
        
        for res in results:
            if res["status"] != "success" or not res["metrics"]:
                continue
                
            metrics = res["metrics"]
            trades = res["trades"]
            
            pnl_pct = metrics.get("total_pnl_pct", 0.0)
            winrate = metrics.get("winrate", 0.0)
            drawdown = metrics.get("max_drawdown_pct", 0.0)
            
            # Áp dụng các bộ lọc (Filters)
            if trades < min_trades:
                continue
            if drawdown > max_drawdown:
                continue
            if winrate < min_winrate:
                continue
                
            valid_results.append(res)
            
        # Sắp xếp (Sort)
        if sort_by == "pnl":
            valid_results.sort(key=lambda x: x["metrics"]["total_pnl_pct"], reverse=True)
        elif sort_by == "winrate":
            valid_results.sort(key=lambda x: x["metrics"]["winrate"], reverse=True)
        # Thêm các tiêu chí khác (Sharpe) nếu cần
        else:
            valid_results.sort(key=lambda x: x["metrics"]["total_pnl_pct"], reverse=True)
            
        return valid_results

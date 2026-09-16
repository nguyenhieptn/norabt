from __future__ import annotations

import numpy as np
from typing import Any, Dict, List
from Agent.backend.market.schemas.market_result import (
    StructureState,
    TrendState,
    VolatilityState,
)


class StructureFeatureExtractor:
    """Tính toán cấu trúc kỹ thuật: EMA20/50/200, ATR14, Keltner Channel, Width Z-Score, Volatility."""

    @staticmethod
    def extract(candles_1h: List[Dict[str, Any]], last_price: float) -> StructureState:
        if not candles_1h:
            return StructureState(
                ema_20=last_price,
                ema_50=last_price,
                ema_200=last_price,
                atr_14=last_price * 0.01,
                keltner_middle=last_price,
                keltner_upper=last_price * 1.02,
                keltner_lower=last_price * 0.98,
                keltner_width=0.04,
                keltner_width_zscore=0.0,
                realized_volatility=0.02,
                volatility_percentile=50.0,
                trend_state=TrendState.SIDEWAYS,
                volatility_state=VolatilityState.NORMAL,
                range_high=last_price * 1.02,
                range_low=last_price * 0.98,
                range_position_pct=50.0,
            )

        # Lấy tối đa 300 nến gần nhất để tính toán tức thời (đủ cho EMA200 và ATR14)
        active_candles = candles_1h[-300:] if len(candles_1h) > 300 else candles_1h
        closes = np.array([float(c.get("close", last_price)) for c in active_candles])
        highs = np.array([float(c.get("high", last_price)) for c in active_candles])
        lows = np.array([float(c.get("low", last_price)) for c in active_candles])

        # EMA tính toán
        def calc_ema(arr: np.ndarray, period: int) -> float:
            if len(arr) < period:
                return float(arr[-1])
            alpha = 2.0 / (period + 1)
            val = float(arr[0])
            for x in arr[1:]:
                val = alpha * float(x) + (1 - alpha) * val
            return val

        ema_20 = calc_ema(closes, 20)
        ema_50 = calc_ema(closes, 50) if len(closes) >= 50 else None
        ema_200 = calc_ema(closes, 200) if len(closes) >= 200 else None

        # ATR 14
        tr_list = []
        for i in range(1, len(closes)):
            h_l = highs[i] - lows[i]
            h_pc = abs(highs[i] - closes[i - 1])
            l_pc = abs(lows[i] - closes[i - 1])
            tr_list.append(max(h_l, h_pc, l_pc))
        atr_14 = (
            float(np.mean(tr_list[-14:]))
            if len(tr_list) >= 14
            else float(last_price * 0.01)
        )

        # Keltner Channel (Middle = EMA20, Upper = EMA20 + 2*ATR, Lower = EMA20 - 2*ATR)
        keltner_middle = ema_20
        keltner_upper = ema_20 + 2.0 * atr_14
        keltner_lower = ema_20 - 2.0 * atr_14
        keltner_width = (
            (keltner_upper - keltner_lower) / keltner_middle
            if keltner_middle > 0
            else 0.04
        )

        # Rolling Keltner Width Z-Score qua 50 chu kỳ
        widths = []
        for i in range(max(14, len(closes) - 50), len(closes)):
            sub_tr = tr_list[max(0, i - 14) : i]
            sub_atr = float(np.mean(sub_tr)) if sub_tr else atr_14
            sub_ema = float(closes[i])
            w = (4.0 * sub_atr) / sub_ema if sub_ema > 0 else 0.04
            widths.append(w)

        w_mean = float(np.mean(widths)) if widths else keltner_width
        w_std = float(np.std(widths)) if len(widths) > 1 else 0.001
        w_zscore = (keltner_width - w_mean) / w_std if w_std > 1e-6 else 0.0

        # Realized Volatility
        returns = np.diff(closes) / closes[:-1] if len(closes) > 1 else np.array([0.0])
        realized_vol = float(np.std(returns[-24:])) if len(returns) >= 24 else 0.02
        vol_pct = min(100.0, max(0.0, (realized_vol / 0.05) * 100.0))

        # Phân loại Trend State
        if last_price > keltner_upper:
            trend_state = TrendState.BREAKOUT_BULL
        elif last_price < keltner_lower:
            trend_state = TrendState.BREAKOUT_BEAR
        elif last_price > ema_20:
            trend_state = TrendState.BULLISH
        elif last_price < ema_20:
            trend_state = TrendState.BEARISH
        else:
            trend_state = TrendState.SIDEWAYS

        # Phân loại Volatility State
        if w_zscore < -1.5:
            vol_state = VolatilityState.COMPRESSED
        elif w_zscore > 2.0:
            vol_state = VolatilityState.EXTREME
        elif w_zscore > 1.0:
            vol_state = VolatilityState.EXPANDING
        else:
            vol_state = VolatilityState.NORMAL

        # Range position qua 50 nến gần nhất
        r_high = float(np.max(highs[-50:]))
        r_low = float(np.min(lows[-50:]))
        r_span = max(1e-6, r_high - r_low)
        r_pos = ((last_price - r_low) / r_span) * 100.0

        return StructureState(
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
            atr_14=atr_14,
            keltner_middle=keltner_middle,
            keltner_upper=keltner_upper,
            keltner_lower=keltner_lower,
            keltner_width=keltner_width,
            keltner_width_zscore=w_zscore,
            realized_volatility=realized_vol,
            volatility_percentile=vol_pct,
            trend_state=trend_state,
            volatility_state=vol_state,
            range_high=r_high,
            range_low=r_low,
            range_position_pct=min(100.0, max(0.0, r_pos)),
        )

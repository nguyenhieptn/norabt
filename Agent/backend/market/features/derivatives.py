from __future__ import annotations

import math
from typing import Any, Dict, Optional

from Agent.backend.market.schemas.market_result import DerivativesState


class DerivativesFeatureExtractor:
    """Normalize OI/funding evidence; absent fields remain unknown."""

    @staticmethod
    def extract(
        delta_oi_data: Optional[Dict[str, Any]] = None,
        sentiment_data: Optional[Dict[str, Any]] = None,
    ) -> DerivativesState:
        oi_data = (delta_oi_data or {}).get("data", delta_oi_data or {})
        sentiment = (sentiment_data or {}).get("sentiment", sentiment_data or {})

        oi_raw = oi_data.get(
            "current_oi_usd", oi_data.get("oi", oi_data.get("open_interest"))
        )
        previous_raw = oi_data.get("prev_oi_usd")
        delta_raw = oi_data.get("delta_oi_usd", oi_data.get("delta_oi"))
        if delta_raw is None and oi_raw is not None and previous_raw is not None:
            delta_raw = float(oi_raw) - float(previous_raw)

        oi = float(oi_raw) if oi_raw is not None else None
        delta = float(delta_raw) if delta_raw is not None else None
        delta_pct_raw = oi_data.get("delta_oi_pct")
        delta_pct = (
            float(delta_pct_raw)
            if delta_pct_raw is not None
            else (
                (delta / max(abs(oi - delta), 1e-12)) * 100.0
                if oi is not None and delta is not None
                else None
            )
        )
        z_raw = oi_data.get("zscore", oi_data.get("delta_oi_zscore"))
        sigma_raw = oi_data.get("sigma_oi")
        oi_zscore = (
            float(z_raw)
            if z_raw is not None
            else (
                delta / max(float(sigma_raw), 1e-12)
                if delta is not None and sigma_raw is not None
                else None
            )
        )

        funding_raw = oi_data.get("funding_rate", sentiment.get("funding_rate"))
        funding_rate = None
        if funding_raw is not None:
            text = str(funding_raw).split("%")[0].replace("+", "").strip()
            funding_rate = (
                float(text) / 100.0 if "%" in str(funding_raw) else float(text)
            )
        funding_zscore = (
            (funding_rate - 0.0001) / 0.0002 if funding_rate is not None else None
        )

        ls_raw = sentiment.get("ls_ratio", oi_data.get("long_short_ratio"))
        long_short_ratio = float(ls_raw) if ls_raw not in (None, "") else None

        lsi = None
        if oi_zscore is not None or funding_zscore is not None:
            raw = abs(oi_zscore or 0.0) * 0.4 + abs(funding_zscore or 0.0) * 0.6
            lsi = min(1.0, max(0.0, 1.0 / (1.0 + math.exp(-raw + 2.0))))

        return DerivativesState(
            open_interest=oi,
            delta_oi=delta,
            delta_oi_pct=delta_pct,
            oi_zscore=oi_zscore,
            funding_rate=funding_rate,
            funding_zscore=funding_zscore,
            long_short_ratio=long_short_ratio,
            liquidation_squeeze_index=lsi,
        )

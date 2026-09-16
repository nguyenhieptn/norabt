from __future__ import annotations

import argparse
import json

from Agent.backend.pipeline import RiskSupervisionPipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one READ_ONLY AI Risk Supervisor assessment"
    )
    parser.add_argument("asset", help="Universe asset, for example BTC")
    parser.add_argument(
        "--bot", default="bot_top_performer", help="Local bot snapshot folder"
    )
    parser.add_argument("--venue", choices=("CEX", "DEX"), default="CEX")
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--horizon", type=int, default=500)
    parser.add_argument(
        "--as-of-ms",
        type=int,
        default=None,
        help="Evaluation clock for deterministic replay",
    )
    args = parser.parse_args()
    result = RiskSupervisionPipeline().run(
        args.asset,
        args.bot,
        venue_type=args.venue,
        simulation_iterations=args.iterations,
        simulation_horizon=args.horizon,
        as_of_ms=args.as_of_ms,
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

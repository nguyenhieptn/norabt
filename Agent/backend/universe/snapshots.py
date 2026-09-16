from __future__ import annotations

import json
import time
from pathlib import Path

from Agent.backend.infra.config import config
from Agent.backend.universe.registry import UniverseRegistry


class UniverseSnapshotManager:
    SNAPSHOT_PATH = Path(config.DATA_DIR) / "universe_snapshot.json"

    @classmethod
    def save_snapshot(cls) -> str:
        registry = UniverseRegistry.get_instance()
        payload = {
            "schema_version": "universe_snapshot.v1",
            "saved_at": int(time.time() * 1000),
            "target_limits": {"cex": 30, "dex": 20},
            "candidate_count": len(registry.list_candidates()),
            "eligible_count": len(registry.list_all()),
            "cex_eligible_count": len(registry.list_cex()),
            "dex_eligible_count": len(registry.list_dex()),
            "rejections": registry.list_rejections(),
            "assets": [asset.model_dump(mode="json") for asset in registry.list_all()],
        }
        cls.SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        cls.SNAPSHOT_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return str(cls.SNAPSHOT_PATH)

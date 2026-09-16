import time
from typing import Dict, Any
import redis.asyncio as aioredis
from Agent.backend.infra.config import config


async def check_system_health() -> Dict[str, Any]:
    health = {"timestamp": int(time.time() * 1000), "status": "HEALTHY", "checks": {}}
    # Check Redis
    try:
        r = aioredis.from_url(config.REDIS_URL)
        ping = await r.ping()
        await r.aclose()
        health["checks"]["redis"] = "OK" if ping else "FAILED"
    except Exception as e:
        health["checks"]["redis"] = f"ERROR: {e}"
        health["status"] = "DEGRADED"

    return health

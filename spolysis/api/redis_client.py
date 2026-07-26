from __future__ import annotations
from upstash_redis import Redis
from api.config import settings
import json

redis = Redis(url=settings.upstash_redis_rest_url, token=settings.upstash_redis_rest_token)


def cache_job_status(job_id: str, status_data: dict, ttl: int = 5) -> None:
    redis.setex(f"job:status:{job_id}", ttl, json.dumps(status_data))


def get_cached_job_status(job_id: str) -> dict | None:
    raw = redis.get(f"job:status:{job_id}")
    if raw:
        return json.loads(raw)
    return None


def invalidate_job_cache(job_id: str) -> None:
    redis.delete(f"job:status:{job_id}")

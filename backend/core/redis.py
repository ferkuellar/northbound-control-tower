from redis import Redis

from core.config import settings


redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def check_redis() -> bool:
    return bool(redis_client.ping())

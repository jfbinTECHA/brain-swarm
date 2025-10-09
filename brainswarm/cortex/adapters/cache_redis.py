import json
import time
from typing import Optional
from redis import Redis

class CacheRedis:
    def __init__(self, url: str):
        self.client = Redis.from_url(url, decode_responses=True)

    def set(self, key: str, value: dict, ttl: int = 600):
        payload = json.dumps(value)
        self.client.set(key, payload, ex=ttl)

    def get(self, key: str) -> Optional[dict]:
        data = self.client.get(key)
        return json.loads(data) if data else None

    def remember(self, key: str, compute_fn, ttl: int = 600):
        cached = self.get(key)
        if cached:
            return cached
        value = compute_fn()
        self.set(key, value, ttl)
        return value
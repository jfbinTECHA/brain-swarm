"""
Cache Memory Layer
------------------
Short-term Redis cache for recent incidents and working memory.
"""

import redis, os, json

r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

class RedisCache:
    """Redis-based cache for the cortex"""

    def __init__(self):
        self.redis = r

    def store(self, key: str, value: dict, ttl: int = None):
        """Store a value in cache"""
        data = json.dumps(value)
        if ttl:
            self.redis.setex(key, ttl, data)
        else:
            self.redis.set(key, data)

    def get(self, key: str):
        """Get a value from cache"""
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    def delete(self, key: str):
        """Delete a key from cache"""
        return self.redis.delete(key)

def store_recent_incident(incident_id: str, payload: dict):
    r.hset("recent_incidents", incident_id, json.dumps(payload))

def get_recent_incidents(limit=10):
    incidents = list(r.hvals("recent_incidents"))
    return [json.loads(x) for x in incidents[-limit:]]
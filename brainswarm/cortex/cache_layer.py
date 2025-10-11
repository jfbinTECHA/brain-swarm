"""
Cache Memory Layer
------------------
Short-term Redis cache for recent incidents and working memory.
"""

import redis, os, json

r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

def store_recent_incident(incident_id: str, payload: dict):
    r.hset("recent_incidents", incident_id, json.dumps(payload))

def get_recent_incidents(limit=10):
    incidents = list(r.hvals("recent_incidents"))
    return [json.loads(x) for x in incidents[-limit:]]
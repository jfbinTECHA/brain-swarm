import json
import time
from typing import Dict, Any, Iterable
import duckdb

try:
    import boto3
    from botocore.client import Config as BotoConfig
except Exception:
    boto3 = None

class ArchiveStore:
    def __init__(self, duckdb_path: str, bucket: str, endpoint_url: str | None, region: str | None, access_key: str | None, secret_key: str | None, secure: bool = True):
        self.db = duckdb.connect(duckdb_path)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS archive (
                id TEXT,
                ts DOUBLE,
                s3_key TEXT,
                metadata JSON
            );
        """)
        self.bucket = bucket
        self.s3_enabled = access_key and secret_key
        if self.s3_enabled:
            if boto3 is None:
                raise RuntimeError("boto3 is not installed")
            session = boto3.session.Session()
            self.s3 = session.client(
                "s3",
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=BotoConfig(signature_version="s3v4", s3={"addressing_style":"auto"}, retries={"max_attempts":3}),
                use_ssl=secure,
            )
            # Ensure bucket exists (idempotent best-effort)
            try:
                self.s3.head_bucket(Bucket=bucket)
            except Exception:
                self.s3.create_bucket(Bucket=bucket)
        else:
            self.s3 = None

    def write_jsonl(self, record_id: str, payload: Dict[str, Any]):
        ts = time.time()
        key = f"jsonl/{int(ts)}/{record_id}.jsonl"
        if self.s3_enabled:
            body = (json.dumps(payload) + "\n").encode("utf-8")
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=body)
        self.db.execute("INSERT INTO archive (id, ts, s3_key, metadata) VALUES (?,?,?,?)",
                         [record_id, ts, key, payload.get("metadata", {})])
        return key

    def list(self) -> Iterable[Dict[str, Any]]:
        return self.db.execute("SELECT * FROM archive").fetchall()
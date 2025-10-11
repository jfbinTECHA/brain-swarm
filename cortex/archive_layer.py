"""
Archive Memory Layer
--------------------
Stores long-term incidents and embeddings into S3 + DuckDB.
"""

import boto3, duckdb, os, json

s3 = boto3.client("s3")
bucket = os.getenv("S3_BUCKET", "brainswarm-archive")
db_path = os.getenv("ARCHIVE_DB_PATH", "data/archive.duckdb")
con = duckdb.connect(db_path)

def archive_incident(incident_id: str, data: dict):
    con.execute("CREATE TABLE IF NOT EXISTS incidents (id TEXT, data JSON)")
    con.execute("INSERT INTO incidents VALUES (?, ?)", [incident_id, json.dumps(data)])
    s3.put_object(Bucket=bucket, Key=f"incidents/{incident_id}.json", Body=json.dumps(data))
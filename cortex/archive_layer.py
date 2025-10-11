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

class ArchiveStore:
    """Archive store for long-term storage"""

    def __init__(self):
        self.s3 = s3
        self.bucket = bucket
        self.db = con

    def store(self, key: str, data: dict):
        """Store data in archive"""
        self.db.execute("CREATE TABLE IF NOT EXISTS archive (key TEXT, data JSON)")
        self.db.execute("INSERT INTO archive VALUES (?, ?)", [key, json.dumps(data)])
        self.s3.put_object(Bucket=self.bucket, Key=f"archive/{key}.json", Body=json.dumps(data))

    def retrieve(self, key: str):
        """Retrieve data from archive"""
        result = self.db.execute("SELECT data FROM archive WHERE key = ?", [key]).fetchone()
        if result:
            return json.loads(result[0])
        return None

def archive_incident(incident_id: str, data: dict):
    con.execute("CREATE TABLE IF NOT EXISTS incidents (id TEXT, data JSON)")
    con.execute("INSERT INTO incidents VALUES (?, ?)", [incident_id, json.dumps(data)])
    s3.put_object(Bucket=bucket, Key=f"incidents/{incident_id}.json", Body=json.dumps(data))
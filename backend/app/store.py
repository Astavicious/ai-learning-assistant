import hashlib
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from fastapi import HTTPException


def uid():
    return secrets.token_hex(16)


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / "sessions.sqlite", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created REAL, touched REAL);
            CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, owner TEXT, hash TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS pages (document_id TEXT, page INTEGER, text TEXT, PRIMARY KEY(document_id,page));
            CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, document_id TEXT, page INTEGER, text TEXT, vector BLOB);
            CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(id UNINDEXED, document_id UNINDEXED, text);
            CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, owner TEXT, payload TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS usage (owner TEXT, day TEXT, tokens INTEGER, requests INTEGER, PRIMARY KEY(owner,day));
            CREATE TABLE IF NOT EXISTS cache (owner TEXT, key TEXT, payload TEXT, PRIMARY KEY(owner,key));
        """)
        # Jobs interrupted by process loss cannot be safely resumed.
        for row in self.db.execute("SELECT id,payload FROM jobs").fetchall():
            job = json.loads(row["payload"])
            if job["status"] in ("queued", "running"):
                job.update(
                    status="failed",
                    error={"code": "interrupted", "message": "Processing was interrupted. Please retry."},
                )
                self.db.execute("UPDATE jobs SET payload=? WHERE id=?", (json.dumps(job), row["id"]))
        for row in self.db.execute("SELECT id,payload FROM documents").fetchall():
            doc = json.loads(row["payload"])
            if doc["status"] not in ("ready", "failed"):
                doc.update(
                    status="failed",
                    error={
                        "code": "interrupted",
                        "message": "Indexing was interrupted. Remove and upload again.",
                    },
                )
                self.db.execute("UPDATE documents SET payload=? WHERE id=?", (json.dumps(doc), row["id"]))
        self.db.commit()

    def execute(self, sql, args=()):
        with self.lock:
            cursor = self.db.execute(sql, args)
            rows = cursor.fetchall()
            self.db.commit()
            return rows

    def create_session(self):
        token = secrets.token_urlsafe(32)
        owner = hashlib.sha256(token.encode()).hexdigest()
        now = time.time()
        self.execute("INSERT INTO sessions VALUES (?,?,?)", (owner, now, now))
        return {"access_token": token, "expires_at": now + 7200, "maximum_expires_at": now + 86400}

    def authorize(self, authorization, touch=True):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Create a temporary session to continue.")
        owner = hashlib.sha256(authorization[7:].encode()).hexdigest()
        rows = self.execute("SELECT * FROM sessions WHERE id=?", (owner,))
        now = time.time()
        if not rows or now - rows[0]["touched"] >= 7200 or now - rows[0]["created"] >= 86400:
            if rows:
                self.delete_session(owner)
            raise HTTPException(
                401,
                "Your temporary session ended. Start a new session; private uploads may have been deleted.",
            )
        if touch:
            self.execute("UPDATE sessions SET touched=? WHERE id=?", (now, owner))
        return owner

    def documents(self, owner):
        return [
            json.loads(row["payload"])
            for row in self.execute("SELECT payload FROM documents WHERE owner IN (?, 'sample')", (owner,))
        ]

    def document(self, owner, doc_id):
        rows = self.execute(
            "SELECT payload FROM documents WHERE id=? AND owner IN (?, 'sample')", (doc_id, owner)
        )
        if not rows:
            raise HTTPException(404, "Document not found.")
        return json.loads(rows[0]["payload"])

    def update_document(self, doc):
        self.execute("UPDATE documents SET payload=? WHERE id=?", (json.dumps(doc), doc["id"]))

    def job(self, owner, job_id):
        rows = self.execute("SELECT payload FROM jobs WHERE id=? AND owner=?", (job_id, owner))
        if not rows:
            raise HTTPException(404, "Job not found.")
        return json.loads(rows[0]["payload"])

    def update_job(self, job):
        self.execute("UPDATE jobs SET payload=? WHERE id=?", (json.dumps(job), job["id"]))

    def new_job(self, owner, doc_id=None):
        active = [json.loads(r["payload"]) for r in self.execute("SELECT payload FROM jobs")]
        if sum(j["status"] in ("queued", "running") for j in active) >= 8:
            raise HTTPException(429, "The processing queue is full. Try again shortly.")
        owned = self.execute("SELECT payload FROM jobs WHERE owner=?", (owner,))
        if sum(json.loads(r["payload"])["status"] in ("queued", "running") for r in owned) >= 2:
            raise HTTPException(429, "Wait for your current jobs to finish before starting another.")
        job = {
            "id": uid(),
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "document_id": doc_id,
            "result": None,
            "error": None,
        }
        self.execute("INSERT INTO jobs VALUES (?,?,?,?)", (job["id"], owner, json.dumps(job), time.time()))
        return job

    def delete_document(self, owner, doc_id):
        doc = self.document(owner, doc_id)
        if doc["sample"]:
            raise HTTPException(403, "Sample documents are immutable.")
        with self.lock:
            for table in ("pages", "chunks", "search"):
                self.execute(f"DELETE FROM {table} WHERE document_id=?", (doc_id,))
            self.execute("DELETE FROM documents WHERE id=? AND owner=?", (doc_id, owner))
            # All derived artifacts are invalidated, including completed chat citations.
            self.execute("DELETE FROM jobs WHERE owner=?", (owner,))
            self.execute("DELETE FROM cache WHERE owner=?", (owner,))
            (self.root / f"{doc_id}.pdf").unlink(missing_ok=True)

    def delete_session(self, owner):
        with self.lock:
            ids = self.execute("SELECT id FROM documents WHERE owner=?", (owner,))
            for row in ids:
                self.delete_document(owner, row["id"])
            for table in ("jobs", "cache"):
                self.execute(f"DELETE FROM {table} WHERE owner=?", (owner,))
            self.execute("DELETE FROM sessions WHERE id=?", (owner,))

    def cleanup(self):
        now = time.time()
        for row in self.execute(
            "SELECT id FROM sessions WHERE touched<? OR created<?", (now - 7200, now - 86400)
        ):
            self.delete_session(row["id"])
        self.execute("DELETE FROM usage WHERE day < date('now','-2 days')")

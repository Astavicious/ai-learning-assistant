"""Measure original-sample indexing and sampled process-tree memory on this machine."""

import hashlib
import json
import os
import platform
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil
from app.service import Service
from app.store import Store

os.environ["MODEL_CACHE"] = str(Path("data/models").resolve())
process = psutil.Process()
peak = [0]
stopped = threading.Event()


def sample_memory():
    while not stopped.wait(0.02):
        try:
            usage = process.memory_info().rss
            for child in process.children(recursive=True):
                try:
                    usage += child.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            peak[0] = max(peak[0], usage)
        except psutil.NoSuchProcess:
            pass


monitor = threading.Thread(target=sample_memory, daemon=True)
monitor.start()
measurements = []
started = time.monotonic()
with tempfile.TemporaryDirectory(prefix="study-index-benchmark-") as temp:
    store = Store(temp)
    service = Service(store)
    for index, path in enumerate(sorted(Path("backend/samples").glob("*.pdf"))):
        content = path.read_bytes()
        doc_id = f"benchmark-{index}"
        (store.root / f"{doc_id}.pdf").write_bytes(content)
        doc = {
            "id": doc_id,
            "filename": path.name,
            "status": "queued",
            "pages": 0,
            "bytes": len(content),
            "sample": True,
            "unreadable_pages": [],
            "error": None,
        }
        store.execute(
            "INSERT INTO documents VALUES (?,?,?,?)",
            (doc_id, "sample", hashlib.sha256(content).hexdigest(), json.dumps(doc)),
        )
        job = store.new_job("sample", doc_id)
        begin = time.monotonic()
        service.index("sample", job, doc)
        assert store.job("sample", job["id"])["status"] == "completed", store.job("sample", job["id"])
        measurements.append(
            {"filename": path.name, "pages": doc["pages"], "seconds": round(time.monotonic() - begin, 3)}
        )
    store.db.close()
stopped.set()
monitor.join()
result = {
    "date_utc": datetime.now(UTC).isoformat(),
    "platform": os.name,
    "python": platform.python_version(),
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "threads": 1,
    "embedding_batch": 8,
    "condition": "Cold process, embedding files cached on disk; five samples indexed sequentially; process-tree RSS sampled every 20ms. Not a Render maximum-load measurement.",
    "total_seconds": round(time.monotonic() - started, 3),
    "sampled_peak_process_tree_rss_mib": round(peak[0] / 1048576, 2),
    "documents": measurements,
}
Path("evaluation/results/indexing-v1.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))

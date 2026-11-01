"""Evaluate fixed sample retrieval; optionally record model answers for manual review."""

import argparse
import hashlib
import json
import os
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil
from app.models import AnswerDraft
from app.service import Service
from app.store import Store

parser = argparse.ArgumentParser()
parser.add_argument("--answers", action="store_true")
parser.add_argument("--secret-file")
parser.add_argument("--resume", action="store_true")
parser.add_argument("--interval", type=float, default=22)
args = parser.parse_args()
if args.secret_file:
    os.environ["GROQ_API_KEY"] = Path(args.secret_file).read_text().strip()
dataset_path = Path("evaluation/acceptance-v1.json")
dataset = json.loads(dataset_path.read_text())
store = Store(os.getenv("DATA_DIR", "data"))
service = Service(store)
ids = [d["id"] for d in store.documents("evaluation") if d["sample"] and d["status"] == "ready"]
assert len(ids) == 5, "Start the backend and wait for sample indexing before evaluating."
service.embedder()
records, times = [], []
previous = {}
if args.resume:
    saved_path = Path("evaluation/results/answers-v1.json")
    saved = json.loads(saved_path.read_text())
    assert saved["dataset_sha256"] == hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    archive = Path("evaluation/results/answers-initial-attempt-v1.json")
    if not archive.exists():
        archive.write_text(saved_path.read_text(), encoding="utf-8")
    previous = {r["id"]: r for r in saved["records"]}
    # The first evaluator retained reservations for rejected 429s. These are
    # known rejected requests, not unknown provider usage; refund once using its recorded error.
    marker = Path("data/evaluation-rejected-reservations-refunded")
    if not marker.exists():
        for record in previous.values():
            if record.get("error", "").startswith("provider_quota|"):
                store.execute("UPDATE usage SET tokens=0 WHERE owner=?", ("evaluation-" + record["id"],))
        marker.touch()
for question in dataset["questions"]:
    if args.resume and "answer" in previous[question["id"]]:
        records.append(previous[question["id"]])
        times.append(previous[question["id"]]["retrieval_seconds"])
        continue
    start = time.monotonic()
    sources = service.retrieve("evaluation", ids, question["question"])
    elapsed = time.monotonic() - start
    times.append(elapsed)
    record = {
        "id": question["id"],
        "retrieval_seconds": round(elapsed, 4),
        "retrieved": [{"document": s["filename"], "page": s["page"]} for s in sources],
    }
    if "document" in question:
        record["page_hit"] = any(
            s["filename"] == question["document"] and s["page"] == question["page"] for s in sources
        )
    if args.answers:
        # Separate evaluation identities keep ordinary demo sessions out of the benchmark.
        owner = "evaluation-" + question["id"]
        started = time.monotonic()
        try:
            answer = service.generate(owner, AnswerDraft, question["question"], sources)
            if answer["status"] != "insufficient_evidence":
                service.resolve(answer, sources)
            record["answer"] = answer
            record["manual_correct"] = None
        except ValueError as exc:
            record["error"] = str(exc)
        record["response_seconds"] = round(time.monotonic() - started, 3)
    records.append(record)
    print(question["id"], record.get("page_hit", "unsupported"), record.get("error", ""), flush=True)
    if args.answers:
        time.sleep(args.interval)
result = {
    "dataset_version": dataset["version"],
    "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
    "date_utc": datetime.now(UTC).isoformat(),
    "model": os.getenv("GENERATION_MODEL", "openai/gpt-oss-20b"),
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "retrieval_hits": sum(r.get("page_hit", False) for r in records),
    "answerable_total": 30,
    "retrieval_median_seconds": statistics.median(times),
    "process_peak_rss_mib": psutil.Process().memory_info().peak_wset / 1048576 if os.name == "nt" else None,
    "answer_evaluation": "pending manual rubric review" if args.answers else "not run",
    "records": records,
}
Path("evaluation/results").mkdir(exist_ok=True)
output = Path(
    "evaluation/results/answers-v1.json" if args.answers else "evaluation/results/retrieval-v1.json"
)
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(f"Supporting page in top six: {result['retrieval_hits']}/30")

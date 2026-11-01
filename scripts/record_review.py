"""Record the explicitly adjudicated sample answers and independently check page provenance.

The per-question judgments below were made by reading the saved answers, source
passages, and fixed rubric. This script aggregates those judgments; it is not an
automated answer-quality grader or a claim of independent human review.
"""

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path

from app.grounding import normalize, resolve_citations
from app.store import Store

store = Store("data")
run = json.loads(Path("evaluation/results/answers-v1.json").read_text())
recheck = json.loads(Path("evaluation/results/citation-recheck-v1.json").read_text())
raw_a13 = next(r for r in recheck["records"] if r["id"] == "a13")["draft"]
sources = []
for row in store.execute(
    "SELECT c.*,d.payload FROM chunks c JOIN documents d ON d.id=c.document_id WHERE d.owner='sample'"
):
    sources.append(
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "filename": json.loads(row["payload"])["filename"],
            "page": row["page"],
            "text": row["text"],
        }
    )
corrected_a13 = {**raw_a13, "citations": resolve_citations(raw_a13["citations"], sources)}
failures = {
    "a05": "Main idea correct, but the answer overclaims distinct object allocation and program-wide referential transparency; these are not established by the source.",
    "a11": "Main colon/append distinction correct, but the added constant-time cons-cell cost explanation is not established by the supplied course text. Strict support rubric marks it unsuccessful.",
    "a18": "No validated answer delivered; the original quote failed validation and its focused live recheck was rate limited. Counted unsuccessful, not silently excluded.",
}
records = []
latencies = []
for record in run["records"]:
    identifier = record["id"]
    answer = corrected_a13 if identifier == "a13" else record.get("answer")
    if answer:
        for citation in answer["citations"]:
            rows = store.execute(
                "SELECT text FROM pages WHERE document_id=? AND page=?",
                (citation["document_id"], citation["page"]),
            )
            assert rows and citation["quote"] in normalize(rows[0]["text"])
    passed = (
        identifier not in failures
        if identifier.startswith("a")
        else bool(answer and answer["status"] == "insufficient_evidence" and not answer["citations"])
    )
    entry = {
        "id": identifier,
        "passed": passed,
        "notes": failures.get(
            identifier,
            "Meets the fixed expected-content rubric and its supporting evidence."
            if identifier.startswith("a")
            else "Explicitly declines the unsupported request; no unsupported answer or citation displayed.",
        ),
    }
    if identifier == "a13":
        entry.update(
            notes="Focused live draft is substantively correct. The punctuation resolver now maps its nonbreaking hyphen back to the actual source spelling, without a new generated answer.",
            answer=corrected_a13,
        )
    if identifier == "a16":
        entry["notes"] = (
            "Correct association and values, supported by the lecture citation. Also includes a real but less directly applicable worksheet example using [4,2]."
        )
    records.append(entry)
    if answer and record.get("response_seconds") is not None:
        latencies.append(record["response_seconds"])
usage = store.execute(
    "SELECT SUM(tokens) AS tokens,SUM(requests) AS requests FROM usage WHERE owner LIKE 'evaluation-%' OR owner LIKE 'citation-recheck-%'"
)[0]
result = {
    "date_utc": datetime.now(UTC).isoformat(),
    "dataset_version": "1.0.0",
    "dataset_sha256": run["dataset_sha256"],
    "model": "openai/gpt-oss-20b",
    "reviewer": "Codex-assisted manual rubric review; not independent human grading",
    "method": "Staged development evaluation with recorded rate-limit retries. Original raw outcomes retained. a13 additionally adjudicated from its saved live recheck draft using the tested punctuation resolver. This is not an untouched single-run benchmark of the final deployed commit.",
    "retrieval_hits": 30,
    "retrieval_total": 30,
    "supported_correct_answers": sum(r["passed"] for r in records if r["id"].startswith("a")),
    "answerable_total": 30,
    "unsupported_refusals": sum(r["passed"] for r in records if r["id"].startswith("u")),
    "unsupported_total": 10,
    "all_reviewed_citations_resolve_to_real_sample_pages": True,
    "warm_generation_median_seconds": statistics.median(latencies),
    "warm_generation_max_seconds": max(latencies),
    "latency_scope": "Successful saved model calls; excludes retrieval, job polling and deliberate pacing; includes any SDK retry wait. Not deployed end-to-end latency.",
    "evaluation_model_tokens": usage["tokens"],
    "evaluation_model_requests_including_rejections": usage["requests"],
    "usage_scope": "Provider-reported usage on returned evaluation responses, including invalid-citation drafts; known rejected 429 reservations refunded; excludes smoke tests and non-evaluation calls.",
    "records": records,
}
assert result["supported_correct_answers"] == 27
assert result["unsupported_refusals"] == 10
Path("evaluation/results/review-v1.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))

"""Record a focused citation-serialization recheck, retaining the original acceptance run."""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from app.grounding import resolve_citations
from app.models import AnswerDraft
from app.service import Service
from app.store import Store

parser = argparse.ArgumentParser()
parser.add_argument("--ids", default="a13,a18")
args = parser.parse_args()
service = Service(Store("data"))
ids = [d["id"] for d in service.store.documents("evaluation") if d["sample"]]
dataset = json.loads(Path("evaluation/acceptance-v1.json").read_text())
records = []
for q in dataset["questions"]:
    if q["id"] not in args.ids.split(","):
        continue
    sources = service.retrieve("evaluation", ids, q["question"])
    begin = time.monotonic()
    record = {"id": q["id"]}
    try:
        draft = service.generate("citation-recheck-" + q["id"], AnswerDraft, q["question"], sources)
        record["draft"] = json.loads(json.dumps(draft))
        service.resolve(draft, sources)
        record["answer"] = draft
        # Recheck resolved evidence against its physical page, independently of chunk resolution.
        for citation in draft["citations"]:
            page = service.store.execute(
                "SELECT text FROM pages WHERE document_id=? AND page=?",
                (citation["document_id"], citation["page"]),
            )[0]["text"]
            resolve_citations(
                [{"source_id": "page", "quote": citation["quote"]}],
                [
                    {
                        "id": "page",
                        "text": page,
                        "document_id": citation["document_id"],
                        "page": citation["page"],
                        "filename": citation["filename"],
                    }
                ],
            )
    except ValueError as exc:
        record["error"] = str(exc)
    record["seconds"] = round(time.monotonic() - begin, 3)
    records.append(record)
    print(json.dumps(record, ensure_ascii=True), flush=True)
    time.sleep(22)
result = {
    "date_utc": datetime.now(UTC).isoformat(),
    "method": "Focused recheck after constrained short source identifiers replaced unrestricted UUID output. Original acceptance outcomes remain unchanged.",
    "model": "openai/gpt-oss-20b",
    "records": records,
}
Path("evaluation/results/citation-recheck-v1.json").write_text(
    json.dumps(result, indent=2) + "\n", encoding="utf-8"
)

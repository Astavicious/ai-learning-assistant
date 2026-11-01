"""Live API workflow against original samples. Never prints session credentials."""

import argparse
import time

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--base", default="http://127.0.0.1:8000")
args = parser.parse_args()
with httpx.Client(base_url=args.base, timeout=120) as client:
    session = client.post("/api/sessions").json()
    client.headers["Authorization"] = "Bearer " + session["access_token"]
    docs = client.get("/api/documents").json()
    ids = [d["id"] for d in docs if d["status"] == "ready"]
    assert len(ids) == 5, docs
    tasks = [
        ("/api/chat", {"question": "Why is map a higher-order function?", "document_ids": ids}),
        ("/api/study-materials", {"kind": "quiz", "document_ids": ids}),
        ("/api/study-materials", {"kind": "flashcards", "document_ids": ids}),
        ("/api/study-materials", {"kind": "summary", "document_ids": ids[:1]}),
    ]
    try:
        for endpoint, body in tasks:
            started = time.monotonic()
            response = client.post(endpoint, json=body)
            response.raise_for_status()
            job = response.json()
            while job["status"] in ("running", "queued"):
                time.sleep(1)
                job = client.get("/api/jobs/" + job["id"]).json()
            print(
                body.get("kind", "chat"),
                f"{time.monotonic() - started:.2f}s",
                job["status"],
                job.get("error"),
            )
            if job["status"] != "completed":
                continue
            result = job["result"]
            if "answer" in result:
                print(result["answer"])
                for citation in result["citations"]:
                    page = client.get(f"/api/documents/{citation['document_id']}/pages/{citation['page']}")
                    assert page.status_code == 200
                print("citations", len(result["citations"]))
            else:
                print("items", len(result.get("questions", result.get("cards", result.get("sections", [])))))
    finally:
        client.delete("/api/session")

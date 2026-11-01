"""Live API workflow against original samples. Never prints session credentials."""

import argparse
import json
import time
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--base", default="http://127.0.0.1:8000")
parser.add_argument("--interval", type=float, default=22)
parser.add_argument("--only", choices=["chat", "quiz", "flashcards", "summary"])
args = parser.parse_args()
with httpx.Client(base_url=args.base, timeout=120) as client:
    for attempt in range(60):
        try:
            if client.get("/api/health").json().get("samples_ready"):
                break
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(2)
    else:
        raise SystemExit("The backend did not finish sample startup within two minutes.")
    session = client.post("/api/sessions").json()
    client.headers["Authorization"] = "Bearer " + session["access_token"]
    docs = client.get("/api/documents").json()
    ids = [d["id"] for d in docs if d["status"] == "ready"]
    assert len(ids) == 5, docs
    private_pdf = Path("backend/samples/Lecture-1-Pure-Functions.pdf").read_bytes()
    upload = client.post(
        "/api/documents", files={"file": ("Private lecture.pdf", private_pdf, "application/pdf")}
    )
    upload.raise_for_status()
    upload_job = upload.json()
    while upload_job["status"] in ("queued", "running"):
        time.sleep(1)
        upload_job = client.get("/api/jobs/" + upload_job["id"]).json()
    assert upload_job["status"] == "completed", upload_job
    private_id = upload_job["document_id"]
    assert client.get(f"/api/documents/{private_id}/pages/1").status_code == 200
    assert client.get(f"/api/documents/{private_id}/pdf").status_code == 200
    assert (
        client.post(
            "/api/documents", files={"file": ("Copy.pdf", private_pdf, "application/pdf")}
        ).status_code
        == 409
    )
    stranger = client.post("/api/sessions").json()
    outsider = {"Authorization": "Bearer " + stranger["access_token"]}
    assert client.get(f"/api/documents/{private_id}/pages/1", headers=outsider).status_code == 404
    assert client.delete(f"/api/documents/{private_id}", headers=outsider).status_code == 404
    client.delete("/api/session", headers=outsider)
    assert client.delete(f"/api/documents/{private_id}").status_code == 204
    print("private upload, preview, duplicates, isolation and deletion passed", flush=True)
    tasks = [
        ("/api/chat", {"question": "Why is map a higher-order function?", "document_ids": ids}),
        ("/api/study-materials", {"kind": "quiz", "document_ids": ids}),
        ("/api/study-materials", {"kind": "flashcards", "document_ids": ids}),
        ("/api/study-materials", {"kind": "summary", "document_ids": ids[:1]}),
    ]
    failures = []
    try:
        for endpoint, body in tasks:
            if args.only and body.get("kind", "chat") != args.only:
                continue
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
                failures.append(body.get("kind", "chat"))
                time.sleep(args.interval)
                continue
            result = job["result"]
            if "answer" in result:
                print(json.dumps(result["answer"], ensure_ascii=True), flush=True)
                for citation in result["citations"]:
                    page = client.get(f"/api/documents/{citation['document_id']}/pages/{citation['page']}")
                    assert page.status_code == 200
                print("citations", len(result["citations"]))
            else:
                print("items", len(result.get("questions", result.get("cards", result.get("sections", [])))))
            time.sleep(args.interval)
    finally:
        client.delete("/api/session")
    if failures:
        raise SystemExit("Failed live tasks: " + ", ".join(failures))

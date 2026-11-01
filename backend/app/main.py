import hashlib
import json
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .models import ChatRequest, Document, FlashcardSet, Job, Quiz, Session, StudyRequest, Summary
from .service import Service
from .store import Store, uid


def create_app(data_dir=None, load_embeddings=True):
    store = Store(data_dir or os.getenv("DATA_DIR", "data"))
    service = Service(store, load_embeddings)
    limits = defaultdict(deque)
    limit_lock = threading.Lock()
    stopped = threading.Event()

    def maintenance():
        while not stopped.wait(60):
            store.cleanup()

    def samples():
        try:
            root = Path(__file__).resolve().parents[1] / "samples"
            if len(list(root.glob("*.pdf"))) != 5:
                raise RuntimeError("Expected five bundled sample PDFs")
            for path in sorted(root.glob("*.pdf")):
                doc_id = "sample-" + path.stem
                existing = store.execute("SELECT payload FROM documents WHERE id=?", (doc_id,))
                if existing and json.loads(existing[0]["payload"])["status"] == "ready":
                    continue
                if existing:
                    store.execute("DELETE FROM documents WHERE id=?", (doc_id,))
                content = path.read_bytes()
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
                service.index("sample", job, doc)
                if store.document("sample", doc_id)["status"] != "ready":
                    raise RuntimeError("Sample indexing failed")
            service.samples_ready = True
        except Exception:
            service.startup_error = "Sample course startup failed. The operator must inspect the model cache and service resources."

    @asynccontextmanager
    async def lifespan(app):
        store.cleanup()
        threading.Thread(target=maintenance, daemon=True).start()
        if load_embeddings:
            threading.Thread(target=samples, daemon=True).start()
        yield
        stopped.set()

    app = FastAPI(title="AI Learning Assistant", version="0.1.0", lifespan=lifespan)
    app.state.store, app.state.service = store, service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        from fastapi.responses import JSONResponse

        # Do not trust arbitrary X-Forwarded-For values. Uvicorn's trusted proxy setting resolves client IP.
        ip = request.client.host if request.client else "unknown"
        key = (
            hashlib.sha256(ip.encode()).hexdigest(),
            "sessions" if request.url.path == "/api/sessions" else "api",
        )
        now = time.monotonic()
        with limit_lock:
            bucket = limits[key]
            while bucket and now - bucket[0] > 60:
                bucket.popleft()
            maximum = 10 if key[1] == "sessions" else 180
            if len(bucket) >= maximum:
                return JSONResponse(
                    {"detail": "Too many requests. Wait a minute and retry."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            bucket.append(now)
            if len(limits) > 10000:
                for old in list(limits):
                    if not limits[old] or now - limits[old][-1] > 60:
                        del limits[old]
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/api/health")
    def health():
        return {
            "status": "degraded"
            if service.startup_error
            else "ready"
            if service.samples_ready
            else "starting",
            "samples_ready": service.samples_ready,
            "generation_configured": bool(os.getenv("GROQ_API_KEY")),
            "error": service.startup_error,
        }

    @app.post("/api/sessions", status_code=201, response_model=Session)
    def new_session():
        with store.lock:
            store.cleanup()
            if store.execute("SELECT COUNT(*) AS n FROM sessions")[0]["n"] >= 500:
                raise HTTPException(503, "The demo is at capacity. Try again later.")
            return store.create_session()

    @app.delete("/api/session", status_code=204)
    def clear_session(authorization: str | None = Header(default=None)):
        store.delete_session(store.authorize(authorization))

    @app.get("/api/documents", response_model=list[Document])
    def list_documents(authorization: str | None = Header(default=None)):
        return store.documents(store.authorize(authorization, touch=False))

    @app.get("/api/study-materials", response_model=list[Summary | Quiz | FlashcardSet])
    def saved_materials(authorization: str | None = Header(default=None)):
        owner = store.authorize(authorization, touch=False)
        jobs = [
            json.loads(row["payload"])
            for row in store.execute("SELECT payload FROM jobs WHERE owner=? ORDER BY created", (owner,))
        ]
        return [
            job["result"]
            for job in jobs
            if job["status"] == "completed" and job.get("result") and "kind" in job["result"]
        ]

    @app.post("/api/documents", status_code=202, response_model=Job)
    async def upload(
        file: UploadFile, background: BackgroundTasks, authorization: str | None = Header(default=None)
    ):
        owner = store.authorize(authorization)
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(422, "Choose a text-based PDF file.")
        content = await file.read(10 * 1024 * 1024 + 1)
        await file.close()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Each PDF must be 10 MB or smaller.")
        if not content.startswith(b"%PDF-"):
            raise HTTPException(422, "This file is not a valid PDF.")
        fingerprint = hashlib.sha256(content).hexdigest()
        with store.lock:
            docs = [d for d in store.documents(owner) if not d["sample"]]
            if store.execute("SELECT id FROM documents WHERE owner=? AND hash=?", (owner, fingerprint)):
                raise HTTPException(409, "This PDF is already in your session.")
            if (
                len(docs) >= int(os.getenv("MAX_DOCUMENTS", "5"))
                or sum(d["bytes"] for d in docs) + len(content) > 25 * 1024 * 1024
            ):
                raise HTTPException(
                    413, "Your session supports 5 PDFs and 25 MB total. Remove a document and retry."
                )
            if (
                sum(p.stat().st_size for p in store.root.iterdir() if p.is_file()) + len(content)
                > 250 * 1024 * 1024
            ):
                raise HTTPException(503, "Temporary demo storage is full. Try again later.")
            doc_id = uid()
            doc = {
                "id": doc_id,
                "filename": Path(file.filename.replace("\\", "/")).name[:180],
                "status": "queued",
                "pages": 0,
                "bytes": len(content),
                "sample": False,
                "unreadable_pages": [],
                "error": None,
            }
            job = store.new_job(owner, doc_id)
            (store.root / f"{doc_id}.pdf").write_bytes(content)
            store.execute(
                "INSERT INTO documents VALUES (?,?,?,?)", (doc_id, owner, fingerprint, json.dumps(doc))
            )
        background.add_task(service.index, owner, job, doc)
        return job

    @app.get("/api/documents/{doc_id}", response_model=Document)
    def document(doc_id: str, authorization: str | None = Header(default=None)):
        return store.document(store.authorize(authorization), doc_id)

    @app.delete("/api/documents/{doc_id}", status_code=204)
    def delete_document(doc_id: str, authorization: str | None = Header(default=None)):
        store.delete_document(store.authorize(authorization), doc_id)

    @app.get("/api/documents/{doc_id}/pages/{page}")
    def page(doc_id: str, page: int, authorization: str | None = Header(default=None)):
        owner = store.authorize(authorization)
        doc = store.document(owner, doc_id)
        if not 1 <= page <= doc["pages"]:
            raise HTTPException(404, "Physical PDF page not found.")
        rows = store.execute("SELECT text FROM pages WHERE document_id=? AND page=?", (doc_id, page))
        return {
            "document_id": doc_id,
            "filename": doc["filename"],
            "page": page,
            "text": rows[0]["text"] if rows else "",
            "readable": bool(rows and rows[0]["text"].strip()),
        }

    @app.get("/api/documents/{doc_id}/pdf")
    def pdf(doc_id: str, authorization: str | None = Header(default=None)):
        store.document(store.authorize(authorization), doc_id)
        path = store.root / f"{doc_id}.pdf"
        if not path.is_file():
            raise HTTPException(404, "The PDF is no longer available.")
        return FileResponse(path, media_type="application/pdf")

    @app.post("/api/chat", status_code=202, response_model=Job)
    def chat(
        request: ChatRequest, background: BackgroundTasks, authorization: str | None = Header(default=None)
    ):
        owner = store.authorize(authorization)
        service.sources(owner, request.document_ids)
        with store.lock:
            job = store.new_job(owner)
        background.add_task(service.study, owner, job, request, True)
        return job

    @app.post("/api/study-materials", status_code=202, response_model=Job)
    def study(
        request: StudyRequest, background: BackgroundTasks, authorization: str | None = Header(default=None)
    ):
        owner = store.authorize(authorization)
        service.sources(owner, request.document_ids)
        if request.kind == "summary" and len(request.document_ids) != 1:
            raise HTTPException(422, "Select exactly one document for a summary.")
        with store.lock:
            job = store.new_job(owner)
        background.add_task(service.study, owner, job, request)
        return job

    @app.get("/api/jobs/{job_id}", response_model=Job)
    def job(job_id: str, authorization: str | None = Header(default=None)):
        return store.job(store.authorize(authorization, touch=False), job_id)

    return app


app = create_app()

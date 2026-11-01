import time
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas
from test_api import pdf, session


def test_encrypted_pdf_is_rejected(client):
    headers = session(client)
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(pdf())))
    writer.encrypt("password")
    output = BytesIO()
    writer.write(output)
    response = client.post(
        "/api/documents",
        headers=headers,
        files={"file": ("secret.pdf", output.getvalue(), "application/pdf")},
    )
    job = client.get("/api/jobs/" + response.json()["id"], headers=headers).json()
    assert job["error"]["code"] == "encrypted_pdf"


def test_image_only_and_partially_readable_pages(client):
    headers = session(client)
    output = BytesIO()
    canvas = Canvas(output)
    canvas.showPage()
    canvas.save()
    response = client.post(
        "/api/documents", headers=headers, files={"file": ("scan.pdf", output.getvalue(), "application/pdf")}
    )
    job = client.get("/api/jobs/" + response.json()["id"], headers=headers).json()
    assert job["error"]["code"] == "image_only_pdf"
    output = BytesIO()
    canvas = Canvas(output)
    canvas.drawString(50, 700, "Readable text on page one.")
    canvas.showPage()
    canvas.showPage()
    canvas.save()
    response = client.post(
        "/api/documents",
        headers=headers,
        files={"file": ("partial.pdf", output.getvalue(), "application/pdf")},
    )
    job = client.get("/api/jobs/" + response.json()["id"], headers=headers).json()
    document = client.get("/api/documents/" + job["document_id"], headers=headers).json()
    assert document["status"] == "ready"
    assert document["unreadable_pages"] == [2]


def test_expiry_removes_private_data(client):
    headers = session(client)
    store = client.app.state.store
    owner = store.authorize(headers["Authorization"])
    store.execute("UPDATE sessions SET touched=? WHERE id=?", (time.time() - 7201, owner))
    assert client.get("/api/documents", headers=headers).status_code == 401
    assert not store.execute("SELECT id FROM sessions WHERE id=?", (owner,))


def test_selected_documents_are_enforced_before_retrieval(client):
    headers = session(client)
    ids = []
    for name, text in [
        ("pure.pdf", "Pure functions return values without side effects."),
        ("fold.pdf", "foldr associates operations to the right."),
    ]:
        response = client.post(
            "/api/documents", headers=headers, files={"file": (name, pdf(text), "application/pdf")}
        )
        ids.append(client.get("/api/jobs/" + response.json()["id"], headers=headers).json()["document_id"])
    owner = client.app.state.store.authorize(headers["Authorization"])
    passages = client.app.state.service.retrieve(owner, [ids[0]], "functions effects")
    assert passages and all(p["document_id"] == ids[0] for p in passages)
    stranger = session(client)
    assert (
        client.post(
            "/api/chat", headers=stranger, json={"question": "What is pure?", "document_ids": ids}
        ).status_code
        == 404
    )


def test_oversized_upload_does_not_create_document(client):
    headers = session(client)
    response = client.post(
        "/api/documents",
        headers=headers,
        files={"file": ("huge.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024), "application/pdf")},
    )
    assert response.status_code == 413
    assert client.get("/api/documents", headers=headers).json() == []


def test_tokenizer_chunking_does_not_truncate_long_pages():
    from app.grounding import chunk_page
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace

    tokenizer = Tokenizer(WordLevel({"[UNK]": 0}, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.enable_truncation(512)
    text = " ".join(f"word{i}" for i in range(1200))
    chunks = chunk_page(text, tokenizer=tokenizer)
    assert chunks[-1].endswith("word1199")


def test_absolute_expiry_is_enforced_even_after_recent_activity(client):
    headers = session(client)
    store = client.app.state.store
    owner = store.authorize(headers["Authorization"])
    store.execute(
        "UPDATE sessions SET created=?,touched=? WHERE id=?", (time.time() - 86401, time.time(), owner)
    )
    assert client.get("/api/documents", headers=headers).status_code == 401


def test_restart_marks_interrupted_jobs_failed_without_restarting_them(tmp_path):
    from app.store import Store

    store = Store(tmp_path)
    credentials = store.create_session()
    owner = store.authorize("Bearer " + credentials["access_token"])
    job = store.new_job(owner)
    restarted = Store(tmp_path)
    recovered = restarted.job(owner, job["id"])
    assert recovered["status"] == "failed"
    assert recovered["error"]["code"] == "interrupted"
    restarted.db.close()
    store.db.close()


def test_private_session_deletion_removes_files_and_source_text(client):
    headers = session(client)
    response = client.post(
        "/api/documents", headers=headers, files={"file": ("private.pdf", pdf(), "application/pdf")}
    )
    doc_id = client.get("/api/jobs/" + response.json()["id"], headers=headers).json()["document_id"]
    store = client.app.state.store
    assert (store.root / f"{doc_id}.pdf").exists()
    assert client.delete("/api/session", headers=headers).status_code == 204
    assert not (store.root / f"{doc_id}.pdf").exists()
    assert not store.execute("SELECT text FROM pages WHERE document_id=?", (doc_id,))
    assert not store.execute("SELECT text FROM chunks WHERE document_id=?", (doc_id,))

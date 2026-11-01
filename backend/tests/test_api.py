from io import BytesIO

import pytest
from reportlab.pdfgen.canvas import Canvas


def pdf(text="A pure function returns the same output for the same input and has no side effects."):
    out = BytesIO()
    canvas = Canvas(out, invariant=1)
    canvas.drawString(50, 750, text)
    canvas.save()
    return out.getvalue()


def session(client):
    response = client.post("/api/sessions")
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_session_required(client):
    assert client.get("/api/documents").status_code == 401


def test_upload_pages_duplicate_and_private_isolation(client):
    owner, stranger = session(client), session(client)
    response = client.post(
        "/api/documents", headers=owner, files={"file": ("lecture.pdf", pdf(), "application/pdf")}
    )
    assert response.status_code == 202, response.text
    job = client.get("/api/jobs/" + response.json()["id"], headers=owner).json()
    assert job["status"] == "completed", job
    doc_id = job["document_id"]
    assert (
        client.get(f"/api/documents/{doc_id}/pages/1", headers=owner)
        .json()["text"]
        .startswith("A pure function")
    )
    assert client.get(f"/api/documents/{doc_id}", headers=stranger).status_code == 404
    assert client.get(f"/api/documents/{doc_id}/pdf", headers=stranger).status_code == 404
    assert client.get("/api/jobs/" + job["id"], headers=stranger).status_code == 404
    assert client.delete(f"/api/documents/{doc_id}", headers=stranger).status_code == 404
    assert (
        client.post(
            "/api/documents", headers=owner, files={"file": ("copy.pdf", pdf(), "application/pdf")}
        ).status_code
        == 409
    )
    assert client.delete(f"/api/documents/{doc_id}", headers=owner).status_code == 204
    assert client.get(f"/api/documents/{doc_id}/pages/1", headers=owner).status_code == 404


@pytest.mark.parametrize("content", [b"not a pdf", b"%PDF-1.4 broken"])
def test_corrupt_pdf_has_specific_failure(client, content):
    headers = session(client)
    response = client.post(
        "/api/documents", headers=headers, files={"file": ("bad.pdf", content, "application/pdf")}
    )
    if response.status_code == 202:
        job = client.get("/api/jobs/" + response.json()["id"], headers=headers).json()
        assert job["status"] == "failed"
        assert job["error"]["code"] == "corrupt_pdf"
    else:
        assert response.status_code == 422


def test_session_deletion_revokes_access(client):
    headers = session(client)
    assert client.delete("/api/session", headers=headers).status_code == 204
    assert client.get("/api/documents", headers=headers).status_code == 401

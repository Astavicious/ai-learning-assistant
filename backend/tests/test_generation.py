import pytest
from test_api import pdf, session


def upload(client, headers):
    response = client.post(
        "/api/documents", headers=headers, files={"file": ("lecture.pdf", pdf(), "application/pdf")}
    )
    return client.get("/api/jobs/" + response.json()["id"], headers=headers).json()["document_id"]


def test_invalid_citation_never_reaches_client(client, monkeypatch):
    headers = session(client)
    doc_id = upload(client, headers)
    monkeypatch.setattr(
        client.app.state.service,
        "generate",
        lambda *args: {
            "status": "answered",
            "answer": "Unsupported claim",
            "citations": [{"source_id": "invented", "quote": "Fake passage"}],
        },
    )
    response = client.post(
        "/api/chat", headers=headers, json={"question": "What is pure?", "document_ids": [doc_id]}
    )
    job = client.get("/api/jobs/" + response.json()["id"], headers=headers).json()
    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["error"]["code"] == "invalid_citation"


def test_invalid_quiz_options_are_rejected(client, monkeypatch):
    headers = session(client)
    doc_id = upload(client, headers)
    monkeypatch.setattr(
        client.app.state.service,
        "generate",
        lambda *args: {
            "questions": [
                {
                    "question": "Test",
                    "options": ["one", "one", "three", "four"],
                    "correct_index": 0,
                    "explanation": "test",
                    "citations": [],
                }
            ]
            * 5
        },
    )
    response = client.post(
        "/api/study-materials", headers=headers, json={"kind": "quiz", "document_ids": [doc_id]}
    )
    job = client.get("/api/jobs/" + response.json()["id"], headers=headers).json()
    assert job["status"] == "failed"
    assert job["error"]["code"] == "invalid_quiz"


def test_global_budget_rejects_before_exceeding_allowance(client, monkeypatch):
    monkeypatch.setenv("GLOBAL_DAILY_TOKENS", "7000")
    service = client.app.state.service
    service.reserve("first")
    with pytest.raises(ValueError, match="quota_exhausted"):
        service.reserve("second")


def test_job_polling_does_not_extend_session(client):
    headers = session(client)
    store = client.app.state.store
    owner = store.authorize(headers["Authorization"])
    job = store.new_job(owner)
    before = store.execute("SELECT touched FROM sessions WHERE id=?", (owner,))[0]["touched"]
    assert client.get("/api/jobs/" + job["id"], headers=headers).status_code == 200
    assert store.execute("SELECT touched FROM sessions WHERE id=?", (owner,))[0]["touched"] == before


def test_materials_are_restorable_only_by_their_session(client):
    headers, stranger = session(client), session(client)
    store = client.app.state.store
    owner = store.authorize(headers["Authorization"])
    job = store.new_job(owner)
    job.update(status="completed", result={"kind": "flashcards", "cards": []})
    store.update_job(job)
    assert client.get("/api/study-materials", headers=headers).json() == [{"kind": "flashcards", "cards": []}]
    assert client.get("/api/study-materials", headers=stranger).json() == []


def test_rejected_provider_requests_release_unused_token_reservation(client, monkeypatch):
    from types import SimpleNamespace

    import httpx
    from app import service as module
    from app.models import AnswerDraft
    from groq import APIStatusError

    def rejected(**kwargs):
        raise APIStatusError(
            "rate limited",
            response=httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com")),
            body={},
        )

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        module,
        "Groq",
        lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=rejected))),
    )
    with pytest.raises(ValueError, match="provider_quota"):
        client.app.state.service.generate("quota-test", AnswerDraft, "Question", [])
    assert (
        client.app.state.store.execute("SELECT tokens FROM usage WHERE owner='quota-test'")[0]["tokens"] == 0
    )

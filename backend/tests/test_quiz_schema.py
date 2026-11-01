from test_api import pdf, session


def test_fixed_quiz_slots_become_five_questions_with_four_ordered_options(client, monkeypatch):
    headers = session(client)
    uploaded = client.post(
        "/api/documents", headers=headers, files={"file": ("lecture.pdf", pdf(), "application/pdf")}
    ).json()
    doc_id = client.get("/api/jobs/" + uploaded["id"], headers=headers).json()["document_id"]
    service = client.app.state.service
    owner = client.app.state.store.authorize(headers["Authorization"])
    source = service.sources(owner, [doc_id])[0]
    question = {
        "question": "Which choice?",
        "options": {"a": "A", "b": "B", "c": "C", "d": "D"},
        "correct_index": 2,
        "explanation": "The supplied passage supports this choice.",
        "citations": [{"source_id": source["id"], "quote": "A pure function"}],
    }
    monkeypatch.setattr(
        service,
        "generate",
        lambda *args: {
            f"question_{i}": {**question, "citations": [dict(question["citations"][0])]} for i in range(1, 6)
        },
    )
    response = client.post(
        "/api/study-materials", headers=headers, json={"kind": "quiz", "document_ids": [doc_id]}
    ).json()
    job = client.get("/api/jobs/" + response["id"], headers=headers).json()
    assert job["status"] == "completed", job
    assert len(job["result"]["questions"]) == 5
    assert job["result"]["questions"][0]["options"] == ["A", "B", "C", "D"]
    assert job["result"]["questions"][0]["correct_index"] == 2

def test_oversized_request_is_rejected_before_parsing(client):
    response = client.post(
        "/api/chat",
        content=b'{"question":"' + b"x" * 70000 + b'"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_chunked_request_is_bounded_without_content_length(client):
    def chunks():
        yield b'{"question":"'
        for _ in range(10):
            yield b"x" * 10000
        yield b'"}'

    response = client.post("/api/chat", content=chunks(), headers={"Content-Type": "application/json"})
    assert response.status_code == 413

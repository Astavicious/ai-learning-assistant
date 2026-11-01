from types import SimpleNamespace

import httpx
from app import service as module
from app.models import AnswerDraft
from groq import APIStatusError


def test_transient_structured_generation_error_is_retried_once(client, monkeypatch):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise APIStatusError(
                "JSON generation failed",
                response=httpx.Response(400, request=httpx.Request("POST", "https://api.groq.com")),
                body={"error": {"code": "json_validate_failed"}},
            )
        return SimpleNamespace(
            usage=SimpleNamespace(total_tokens=40),
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"status":"answered","answer":"Pure function","citations":[{"source_id":"S1","quote":"Pure function"}]}'
                    )
                )
            ],
        )

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        module,
        "Groq",
        lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=generate))),
    )
    result = client.app.state.service.generate(
        "structured-retry", AnswerDraft, "Question", [{"id": "actual-chunk", "text": "Pure function"}]
    )
    assert result["citations"][0]["source_id"] == "actual-chunk"
    assert len(calls) == 2

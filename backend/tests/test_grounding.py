import pytest


def test_citations_reject_unknown_and_invented_quotes():
    from app.grounding import resolve_citations

    sources = [
        {
            "id": "c1",
            "document_id": "d1",
            "filename": "Lecture.pdf",
            "page": 2,
            "text": "A pure function has no side effects.",
        }
    ]
    result = resolve_citations([{"source_id": "c1", "quote": "no side effects"}], sources)
    assert result[0]["page"] == 2
    assert result[0]["document_id"] == "d1"
    for citation in [
        {"source_id": "c2", "quote": "no side effects"},
        {"source_id": "c1", "quote": "always changes state"},
        {"source_id": "c1", "quote": ""},
    ]:
        with pytest.raises(ValueError):
            resolve_citations([citation], sources)


def test_reciprocal_rank_fusion_rewards_agreement():
    from app.grounding import fuse_ranks

    assert fuse_ranks([["a", "b", "c"], ["b", "d", "a"]])[0] == "b"


def test_chunks_overlap_without_crossing_pages():
    from app.grounding import chunk_page

    text = " ".join(f"word{i}" for i in range(900))
    chunks = chunk_page(text, size=350, overlap=50)
    assert len(chunks) == 3
    assert chunks[0].endswith("word349")
    assert chunks[1].startswith("word300 ")
    assert chunks[-1].endswith("word899")

import re
from collections import defaultdict


def chunk_page(text, size=350, overlap=50, tokenizer=None):
    if tokenizer is None:
        # Whitespace fallback is used only by unit tests, never by semantic indexing.
        words = text.split()
        return [" ".join(words[i : i + size]) for i in range(0, len(words), size - overlap)]
    # The embedding tokenizer truncates at 512 tokens. Clone it so chunking covers
    # the entire physical page without changing the shared inference tokenizer.
    from tokenizers import Tokenizer

    full_page_tokenizer = Tokenizer.from_str(tokenizer.to_str())
    full_page_tokenizer.no_truncation()
    encoded = full_page_tokenizer.encode(text, add_special_tokens=False)
    offsets = encoded.offsets
    return [
        text[offsets[i][0] : offsets[min(i + size, len(offsets)) - 1][1]]
        for i in range(0, len(offsets), size - overlap)
    ]


def fuse_ranks(rankings):
    scores = defaultdict(float)
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            scores[item] += 1 / (60 + rank)
    return sorted(scores, key=lambda item: (-scores[item], item))


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def resolve_citations(citations, sources):
    typography = str.maketrans(
        {"\u2010": "-", "\u2011": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}
    )
    lookup = {source["id"]: source for source in sources}
    resolved = []
    for citation in citations:
        source = lookup.get(citation["source_id"])
        quote = normalize(citation["quote"])
        text = normalize(source["text"]) if source else ""
        offset = text.translate(typography).find(quote.translate(typography))
        if source is None or len(quote) < 3 or offset < 0:
            raise ValueError("The model returned an invalid supporting passage. Please retry.")
        # Translation is one character to one character. Return the actual source
        # spelling, never the model's altered punctuation or a fuzzy word match.
        quote = text[offset : offset + len(quote)]
        resolved.append(
            {
                "source_id": source["id"],
                "document_id": source["document_id"],
                "filename": source["filename"],
                "page": source["page"],
                "quote": quote,
            }
        )
    return resolved

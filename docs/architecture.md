# Architecture

```mermaid
flowchart LR
    Student[Student browser] --> UI[React study workspace]
    UI -->|Anonymous bearer token| API[FastAPI ownership and quota checks]
    API --> Upload[Bounded PDF upload]
    Upload --> Parser[Isolated pypdf extraction process]
    Parser --> Pages[Physical pages and extraction status]
    Pages --> Chunks[350-token page chunks / 50 overlap]
    Chunks --> Embed[FastEmbed / BGE small]
    Chunks --> FTS[SQLite FTS5]
    Embed --> Vectors[NumPy vectors / SQLite metadata]
    API --> Search[Authorized selected-document scope]
    Search --> FTS
    Search --> Vectors
    FTS --> Fusion[Reciprocal rank fusion / top six]
    Vectors --> Fusion
    Fusion --> Groq[Groq structured generation]
    Pages --> Batches[Full-scope summary batches]
    Batches --> Groq
    Groq --> Validate[Schema and source quote validation]
    Validate --> Jobs[Session-owned jobs and materials]
    Jobs --> UI
    UI --> Evidence[Authorized text and PDF.js preview]
    UI --> Export[Markdown / UTF-8 TSV]
    API --> Cleanup[Expiry / deletion / restart recovery]
```

One web worker and one indexing lock avoid duplicating the embedding model. A generation lock bounds model concurrency. The index uses one SQLite connection protected by a reentrant lock. Private files use random server identifiers; original filenames are metadata, never filesystem paths. Sample PDFs are build artifacts and reindex automatically into a new temporary store.

No database or uploaded data lives in the frontend. The model key exists exclusively in backend environment variables. No question or document contents are written to logs. Timing/usage logs contain only numeric measurements and error categories.

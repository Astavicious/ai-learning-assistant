from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    source_id: str
    quote: str


class Citation(Evidence):
    document_id: str
    filename: str
    page: int


class AnswerDraft(StrictModel):
    status: Literal["answered", "insufficient_evidence", "conflicting_evidence"]
    answer: str
    citations: list[Evidence]


class ChatAnswer(StrictModel):
    status: Literal["answered", "insufficient_evidence", "conflicting_evidence"]
    answer: str
    citations: list[Citation]


class SummaryDraft(StrictModel):
    overview: str
    key_concepts: list[str]
    definitions: list[str]
    revision_points: list[str]
    citations: list[Evidence] = Field(min_length=1)


class SummarySection(StrictModel):
    overview: str
    key_concepts: list[str]
    definitions: list[str]
    revision_points: list[str]
    citations: list[Citation]


class Summary(StrictModel):
    kind: Literal["summary"] = "summary"
    sections: list[SummarySection]
    covered_pages: list[str]
    failed_pages: list[str]
    incomplete: bool


class QuestionDraft(StrictModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: Literal[0, 1, 2, 3]
    explanation: str
    citations: list[Evidence] = Field(min_length=1)


class QuizDraft(StrictModel):
    questions: list[QuestionDraft] = Field(min_length=5, max_length=5)


class Question(StrictModel):
    question: str
    options: list[str]
    correct_index: int
    explanation: str
    citations: list[Citation]


class Quiz(StrictModel):
    kind: Literal["quiz"] = "quiz"
    questions: list[Question]


class CardDraft(StrictModel):
    question: str
    answer: str
    citations: list[Evidence] = Field(min_length=1)


class CardsDraft(StrictModel):
    cards: list[CardDraft] = Field(min_length=10, max_length=10)


class Flashcard(StrictModel):
    question: str
    answer: str
    citations: list[Citation]


class FlashcardSet(StrictModel):
    kind: Literal["flashcards"] = "flashcards"
    cards: list[Flashcard]


class ChatRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[str] = Field(min_length=1, max_length=25)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=6)


class StudyRequest(StrictModel):
    kind: Literal["summary", "quiz", "flashcards"]
    document_ids: list[str] = Field(min_length=1, max_length=25)
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)


class Document(StrictModel):
    id: str
    filename: str
    status: Literal["queued", "extracting", "indexing", "ready", "failed"]
    pages: int
    bytes: int
    sample: bool
    unreadable_pages: list[int]
    error: dict | None


class Job(StrictModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    stage: str
    progress: int
    document_id: str | None
    result: ChatAnswer | Summary | Quiz | FlashcardSet | None
    error: dict | None


class Session(StrictModel):
    access_token: str
    expires_at: float
    maximum_expires_at: float

import React, { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import {
  BookOpen,
  Upload,
  ArrowUp,
  FileText,
  ChevronRight,
  PanelLeft,
  PanelRight,
  X,
  Download,
  Trash2,
  Check,
  RotateCcw,
  Layers,
  MessageSquare,
  ListChecks,
  NotebookPen,
} from "lucide-react";
import "@fontsource/source-sans-3/latin-400.css";
import "@fontsource/source-sans-3/latin-500.css";
import "@fontsource/source-sans-3/latin-600.css";
import "@fontsource/source-sans-3/latin-700.css";
import {
  api,
  createSession,
  SessionEnded,
  type Document,
  type Job,
  type Citation,
  type ChatAnswer,
  type Material,
  type Quiz,
  type FlashcardSet,
} from "./api";
import { scoreQuiz, ankiTSV, download } from "./study";
const PdfPreview = lazy(() => import("./PdfPreview").then(module => ({default: module.PdfPreview})));
import "./style.css";

type Tab = "Ask" | "Summary" | "Quiz" | "Flashcards";
class ActivityCancelled extends Error {}
const suggestions = [
  "What makes a function pure?",
  "How does recursion work on a list?",
  "When should I use foldr instead of foldl?",
];
const icons = [MessageSquare, NotebookPen, ListChecks, Layers];
function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown skipHtml rehypePlugins={[rehypeSanitize]}>
      {children}
    </ReactMarkdown>
  );
}
function References({
  items,
  onOpen,
}: {
  items: Citation[];
  onOpen: (c: Citation) => void;
}) {
  return (
    <div className="references">
      {items.map((citation, index) => (
        <button
          key={`${citation.source_id}-${index}`}
          onClick={() => onOpen(citation)}
          className="reference"
        >
          <FileText size={13} />
          {citation.filename.replace(/\.pdf$/i, "")}{" "}
          <span>p. {citation.page}</span>
          <ChevronRight size={12} />
        </button>
      ))}
    </div>
  );
}
function Drawer({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog ref={ref} onCancel={close} className="drawer">
      <header>
        <h2>{title}</h2>
        <button aria-label={`Close ${title}`} onClick={close}>
          <X size={20} />
        </button>
      </header>
      {children}
    </dialog>
  );
}
function QuizView({
  quiz,
  onOpen,
}: {
  quiz: Quiz;
  onOpen: (c: Citation) => void;
}) {
  const [answers, setAnswers] = useState<(number | undefined)[]>([]);
  const [submitted, setSubmitted] = useState(false);
  const score = scoreQuiz(
    answers,
    quiz.questions.map((q) => q.correct_index),
  );
  return (
    <div className="study-result">
      <div className="result-heading">
        <h2>Check your understanding</h2>
        {submitted && (
          <strong>
            {score.correct} / {score.total}
          </strong>
        )}
      </div>
      {quiz.questions.map((q, index) => (
        <fieldset key={index} className="quiz-question">
          <legend>
            {index + 1}. {q.question}
          </legend>
          {q.options.map((option, i) => (
            <label
              key={i}
              className={
                submitted && i === q.correct_index ? "option correct" : "option"
              }
            >
              <input
                type="radio"
                name={`question-${index}`}
                checked={answers[index] === i}
                disabled={submitted}
                onChange={() =>
                  setAnswers((old) => {
                    const next = [...old];
                    next[index] = i;
                    return next;
                  })
                }
              />
              <span>{option}</span>
              {submitted && i === q.correct_index && <Check size={16} />}
            </label>
          ))}
          {submitted && (
            <div className="review">
              <Markdown>{q.explanation}</Markdown>
              <References items={q.citations} onOpen={onOpen} />
            </div>
          )}
        </fieldset>
      ))}
      <button className="primary" onClick={() => setSubmitted(!submitted)}>
        {submitted ? "Try again" : "Submit quiz"}
      </button>
      {submitted && (
        <button
          className="quiet"
          onClick={() =>
            download(
              "quiz-review.md",
              quiz.questions
                .map(
                  (q, i) =>
                    `## ${i + 1}. ${q.question}\n\n${q.options.map((o, n) => `${n === q.correct_index ? "✓" : "-"} ${o}`).join("\n")}\n\n${q.explanation}\n\n${q.citations.map((c) => `${c.filename}, p. ${c.page}: ${c.quote}`).join("\n")}`,
                )
                .join("\n\n"),
            )
          }
        >
          <Download size={16} />
          Export review
        </button>
      )}
    </div>
  );
}
function CardsView({
  set,
  onOpen,
}: {
  set: FlashcardSet;
  onOpen: (c: Citation) => void;
}) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const card = set.cards[index];
  return (
    <div className="study-result">
      <div className="result-heading">
        <h2>One idea at a time</h2>
        <span>
          {index + 1} / {set.cards.length}
        </span>
      </div>
      <button
        className={"flashcard " + (flipped ? "flipped" : "")}
        onClick={() => setFlipped(!flipped)}
        aria-label={flipped ? "Show question" : "Show answer"}
      >
        <span className="muted">{flipped ? "Answer" : "Question"}</span>
        <span>{flipped ? card.answer : card.question}</span>
        <small>Click or press Enter to flip</small>
      </button>
      {flipped && <References items={card.citations} onOpen={onOpen} />}
      <div className="card-controls">
        <button
          onClick={() => {
            setIndex((index + set.cards.length - 1) % set.cards.length);
            setFlipped(false);
          }}
        >
          Previous
        </button>
        <button
          onClick={() => {
            setIndex((index + 1) % set.cards.length);
            setFlipped(false);
          }}
        >
          Next card <ChevronRight size={16} />
        </button>
      </div>
      <button
        className="quiet"
        onClick={() =>
          download(
            "flashcards.tsv",
            ankiTSV(
              set.cards.map((c) => ({
                question: c.question,
                answer: c.answer,
                source: c.citations
                  .map((r) => `${r.filename}, p. ${r.page}`)
                  .join("; "),
              })),
            ),
            "text/tab-separated-values;charset=utf-8",
          )
        }
      >
        <Download size={16} />
        Export for Anki
      </button>
      <p className="muted small">
        Import as tab-separated text with three fields. Keep HTML disabled.
      </p>
    </div>
  );
}
function App() {
  const [started, setStarted] = useState(
    Boolean(sessionStorage.getItem("study-token")),
  );
  const [docs, setDocs] = useState<Document[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [tab, setTab] = useState<Tab>("Ask");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<
    { question: string; answer: ChatAnswer }[]
  >([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [activeMaterial, setActiveMaterial] = useState<Material>();
  const [source, setSource] = useState<Citation>();
  const [sourceText, setSourceText] = useState("");
  const [drawer, setDrawer] = useState<"library" | "sources">();
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<Job>();
  const [error, setError] = useState("");
  const [health, setHealth] = useState("Connecting to the study service…");
  const [range, setRange] = useState({ start: "", end: "" });
  const [drag, setDrag] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const known = useRef(new Set<string>());
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const handleError = useCallback((err: unknown) => {
    if (err instanceof ActivityCancelled) return;
    setError(
      err instanceof Error
        ? err.message
        : "The service is unavailable. Please retry.",
    );
    if (err instanceof SessionEnded) {
      sessionStorage.removeItem("study-token");
      setStarted(false);
      setDocs([]);
      setSelected([]);
      setMessages([]);
      setMaterials([]);
      setActiveMaterial(undefined);
      setSource(undefined);
      known.current.clear();
    }
  }, []);
  const refresh = useCallback(async () => {
    const documents = await api<Document[]>("/api/documents");
    setDocs(documents);
    setSelected((old) => {
      const ready = documents.filter((d) => d.status === "ready");
      const added = ready
        .filter((d) => !known.current.has(d.id))
        .map((d) => d.id);
      ready.forEach((d) => known.current.add(d.id));
      return [...old.filter((id) => ready.some((d) => d.id === id)), ...added];
    });
  }, []);
  useEffect(() => {
    if (!started) return;
    let cancelled = false;
    void api<Material[]>("/api/study-materials").then(saved => {
      if (!cancelled) { setMaterials(saved); setActiveMaterial(saved.at(-1)); }
    }).catch(handleError);
    return () => { cancelled = true; };
  }, [started, handleError]);
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const h = await api<{
          status: string;
          samples_ready: boolean;
          generation_configured: boolean;
          error: string | null;
        }>("/api/health");
        if (cancelled) return;
        setHealth(
          h.error ||
            (!h.samples_ready
              ? "Preparing the sample course…"
              : !h.generation_configured
                ? "Sample course ready · AI generation needs an API key"
                : "Ready to study"),
        );
        if (started) await refresh();
      } catch (err) {
        if (!cancelled) {
          setHealth("The free service may be waking up. Retrying…");
          if (err instanceof SessionEnded) handleError(err);
        }
      }
    };
    void tick();
    const timer = setInterval(() => void tick(), 5000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [started, refresh, handleError]);
  const start = async (upload = false) => {
    setError("");
    setBusy(true);
    try {
      if (!sessionStorage.getItem("study-token")) await createSession();
      setStarted(true);
      await refresh();
      if (upload) fileInput.current?.click();
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  };
  const awaitJob = async (initial: Job) => {
    const activityToken = sessionStorage.getItem("study-token");
    let current = initial;
    setJob(current);
    while (current.status === "queued" || current.status === "running") {
      await new Promise((resolve) => setTimeout(resolve, 1200));
      if (activityToken !== sessionStorage.getItem("study-token")) throw new ActivityCancelled();
      if (!mounted.current) throw new Error("Workspace closed.");
      current = await api<Job>(`/api/jobs/${current.id}`);
      setJob(current);
    }
    if (current.status === "failed")
      throw new Error(
        (current.error?.message as string) ||
          "Processing failed. Please retry.",
      );
    return current;
  };
  const upload = async (files: FileList | File[]) => {
    setError("");
    setBusy(true);
    try {
      if (!sessionStorage.getItem("study-token")) {
        await createSession();
        setStarted(true);
      }
      for (const file of Array.from(files)) {
        const data = new FormData();
        data.append("file", file);
        const initial = await api<Job>("/api/documents", {
          method: "POST",
          body: data,
        });
        await refresh();
        await awaitJob(initial);
        await refresh();
      }
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
      setJob(undefined);
      if (fileInput.current) fileInput.current.value = "";
    }
  };
  const ask = async (text = question) => {
    if (!text.trim() || !selected.length) return;
    setBusy(true);
    setError("");
    try {
      const history = messages.slice(-2).flatMap((m) => [
        { role: "user", content: m.question },
        { role: "assistant", content: m.answer.answer },
      ]);
      const result = await awaitJob(
        await api<Job>("/api/chat", {
          method: "POST",
          body: JSON.stringify({
            question: text,
            document_ids: selected,
            history,
          }),
        }),
      );
      if (result.result && "answer" in result.result) {
        setMessages((old) => [
          ...old,
          { question: text, answer: result.result as ChatAnswer },
        ]);
        setQuestion("");
      }
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
      setJob(undefined);
    }
  };
  const generate = async () => {
    setBusy(true);
    setError("");
    try {
      const body = {
        kind: tab.toLowerCase(),
        document_ids: selected,
        start_page: tab === "Summary" && range.start ? Number(range.start) : null,
        end_page: tab === "Summary" && range.end ? Number(range.end) : null,
      };
      const result = await awaitJob(
        await api<Job>("/api/study-materials", {
          method: "POST",
          body: JSON.stringify(body),
        }),
      );
      if (result.result && "kind" in result.result) {
        const material = result.result;
        setMaterials((old) => [...old, material]);
        setActiveMaterial(material);
      }
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
      setJob(undefined);
    }
  };
  const openSource = async (citation: Citation) => {
    setSource(citation);
    if (window.matchMedia("(max-width: 1170px)").matches) setDrawer("sources");
    setSourceText("Loading source text…");
    try {
      const page = await api<{ text: string }>(
        `/api/documents/${citation.document_id}/pages/${citation.page}`,
      );
      setSourceText(page.text);
    } catch (err) {
      handleError(err);
      setSourceText("Source unavailable.");
    }
  };
  const clear = async () => {
    setBusy(true);
    try {
      await api("/api/session", { method: "DELETE" });
      sessionStorage.removeItem("study-token");
      setStarted(false);
      setDocs([]);
      setSelected([]);
      setMessages([]);
      setMaterials([]);
      setActiveMaterial(undefined);
      setSource(undefined);
      setDrawer(undefined);
      known.current.clear();
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  };
  const remove = async (id: string) => {
    try {
      await api(`/api/documents/${id}`, { method: "DELETE" });
      setMessages([]);
      setMaterials([]);
      setActiveMaterial(undefined);
      setSource(undefined);
      await refresh();
    } catch (err) {
      handleError(err);
    }
  };
  const library = (
    <>
      <div className="library-heading">
        <span className="section-title">Your library</span>
        <span className="count">{docs.length}</span>
      </div>
      <p className="muted small">Choose the documents to study.</p>
      <div className="course-label">
        <BookOpen size={15} />
        <span>Functional Programming</span>
      </div>
      <div className="document-list">
        {docs.map((doc) => (
          <div className="document" key={doc.id}>
            <label>
              <input
                type="checkbox"
                checked={selected.includes(doc.id)}
                disabled={doc.status !== "ready" || busy}
                onChange={() =>
                  setSelected((old) =>
                    old.includes(doc.id)
                      ? old.filter((id) => id !== doc.id)
                      : [...old, doc.id],
                  )
                }
              />
              <FileText size={18} />
              <span>
                <strong>
                  {doc.filename.replace(/\.pdf$/i, "").replaceAll("-", " ")}
                </strong>
                <small>
                  {doc.status === "ready"
                    ? `${doc.pages} pages${doc.sample ? " · Sample" : ""}`
                    : doc.status}
                  {doc.unreadable_pages.length > 0
                    ? ` · ${doc.unreadable_pages.length} unreadable`
                    : ""}
                </small>
                {doc.error && (
                  <small className="error-text">
                    {String(doc.error.message)}
                  </small>
                )}
              </span>
            </label>
            {!doc.sample && (
              <button
                className="icon-button"
                aria-label={`Remove ${doc.filename}`}
                disabled={busy}
                onClick={() => void remove(doc.id)}
              >
                <X size={14} />
              </button>
            )}
          </div>
        ))}
      </div>
      <button
        className="upload-button"
        disabled={busy}
        onClick={() => fileInput.current?.click()}
      >
        <Upload size={16} />
        Upload PDFs
      </button>
      <p className="muted small">
        5 PDFs · 10 MB each
        <br />
        25 MB and 150 pages per session
      </p>
      <div className="library-bottom">
        <div>
          <span className="status-dot" />
          {health}
        </div>
        <button className="quiet" onClick={() => void clear()}>
          <Trash2 size={14} />
          Delete session
        </button>
      </div>
    </>
  );
  const sourcePanel = (
    <>
      {source ? (
        <>
          <div className="source-title">
            <FileText size={17} />
            <span>{source.filename}</span>
          </div>
          <p className="muted small">Physical PDF page {source.page}</p>
          <blockquote>{source.quote}</blockquote>
          <details>
            <summary>Read extracted page text</summary>
            <pre className="source-text">{sourceText}</pre>
          </details>
          <Suspense fallback={<p className="muted small">Loading PDF preview…</p>}><PdfPreview documentId={source.document_id} page={source.page} /></Suspense>
        </>
      ) : (
        <div className="source-empty">
          <div className="source-symbol">
            <FileText size={28} />
          </div>
          <h3>Follow the evidence</h3>
          <p>
            Open a citation to read the supporting passage and inspect its PDF
            page.
          </p>
          <div className="example-reference">
            <FileText size={14} />
            Lecture 1 <span>p. 2</span>
          </div>
        </div>
      )}
    </>
  );
  const active =
    activeMaterial?.kind === tab.toLowerCase() ? activeMaterial : undefined;
  return (
    <div
      className="app"
      onDragOver={(event) => {
        event.preventDefault();
        setDrag(true);
      }}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node))
          setDrag(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDrag(false);
        if (!busy && event.dataTransfer.files.length)
          void upload(event.dataTransfer.files);
      }}
    >
      <input
        type="file"
        accept="application/pdf,.pdf"
        multiple
        ref={fileInput}
        className="sr-only"
        aria-label="Choose PDF files"
        onChange={(event) => {
          if (event.target.files) void upload(event.target.files);
        }}
      />
      <header className="topbar">
        <a href="/" className="brand">
          <span className="brand-icon">
            <BookOpen size={22} />
          </span>
          <span>
            AI Learning Assistant<small>Your course, understood.</small>
          </span>
        </a>
        <div className="topbar-right">
          <span className="temporary">
            <span className="status-dot" />
            Temporary study session
          </span>
          <a
            href="https://github.com/Astavicious/ai-learning-assistant"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </div>
      </header>
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss error">
            <X size={16} />
          </button>
        </div>
      )}
      {!started ? (
        <main className="welcome">
          <div className="welcome-copy">
            <div className="welcome-book">
              <BookOpen size={36} />
            </div>
            <h1>
              Less searching.
              <br />
              More understanding.
            </h1>
            <p>
              Turn your course PDFs into answers you can trace, ideas you can
              revise, and questions that help them stick.
            </p>
            <div className="welcome-actions">
              <button
                className="primary"
                disabled={busy}
                onClick={() => void start()}
              >
                <BookOpen size={18} />
                Try the sample course
              </button>
              <button disabled={busy} onClick={() => void start(true)}>
                <Upload size={18} />
                Upload your PDFs
              </button>
            </div>
            <p className="muted small">
              No account needed. Start with five original Functional Programming
              documents.
            </p>
            <div className="privacy">
              <h2>A temporary place to study</h2>
              <p>
                Uploads and study materials expire after two hours of
                inactivity, within 24 hours at most. Free-service restarts can
                end a session sooner. You can delete application data at any
                time.
              </p>
              <p>
                Relevant extracted text is sent to Groq for generation.
                Application deletion does not control provider retention.{" "}
                <a
                  href="https://console.groq.com/docs/your-data"
                  target="_blank"
                  rel="noreferrer"
                >
                  Read Groq’s data policy
                </a>
                .
              </p>
            </div>
            <p className="service-state" role="status">
              {health}
            </p>
          </div>
          <div className="welcome-note">
            <span className="note-tab">From your course</span>
            <h2>
              Why is <code>map</code>
              <br />a higher-order function?
            </h2>
            <p>
              A higher-order function takes a function as an argument or returns
              one. <code>map</code> takes a function and applies it to every
              element of a list.
            </p>
            <pre>{"map (* 2) [1, 2, 3]\n-- [2, 4, 6]"}</pre>
            <span className="note-citation">
              <FileText size={14} />
              Illustrative study question
            </span>
            <div className="note-bottom">
              <Check size={16} />
              Understand it. Find it. Remember it.
            </div>
          </div>
        </main>
      ) : (
        <>
          <div className="mobile-toolbar">
            <button onClick={() => setDrawer("library")}>
              <PanelLeft size={17} />
              Library ({selected.length})
            </button>
            <button onClick={() => setDrawer("sources")}>
              Sources
              <PanelRight size={17} />
            </button>
          </div>
          <div className="workspace">
            <aside className="library">{library}</aside>
            <main className="study-area">
              <div className="workspace-heading">
                <div>
                  <p className="muted small">Your study workspace</p>
                  <h1>Make sense of your course.</h1>
                </div>
                <span className="selected-pill">
                  {selected.length} selected
                </span>
              </div>
              <div className="tabs" role="tablist" aria-label="Study tools">
                {(["Ask", "Summary", "Quiz", "Flashcards"] as Tab[]).map(
                  (name, i) => {
                    const Icon = icons[i];
                    return (
                      <button
                        key={name}
                        role="tab"
                        id={`tab-${name}`}
                        aria-controls="study-panel"
                        aria-selected={tab === name}
                        tabIndex={tab === name ? 0 : -1}
                        onKeyDown={(event) => {
                          if (
                            ["ArrowLeft", "ArrowRight", "Home", "End"].includes(
                              event.key,
                            )
                          ) {
                            event.preventDefault();
                            const names: Tab[] = [
                              "Ask",
                              "Summary",
                              "Quiz",
                              "Flashcards",
                            ];
                            const next =
                              event.key === "Home"
                                ? 0
                                : event.key === "End"
                                  ? 3
                                  : (i + (event.key === "ArrowRight" ? 1 : 3)) %
                                    4;
                            setTab(names[next]);
                            document
                              .getElementById(`tab-${names[next]}`)
                              ?.focus();
                          }
                        }}
                        onClick={() => setTab(name)}
                      >
                        <Icon size={17} />
                        {name}
                      </button>
                    );
                  },
                )}
              </div>
              <section
                className="study-panel"
                id="study-panel"
                role="tabpanel"
                aria-labelledby={`tab-${tab}`}
              >
                <div className="activity">
                  {tab === "Ask" ? (
                    <>
                      {messages.length === 0 ? (
                        <div className="ask-empty">
                          <span className="activity-icon">
                            <MessageSquare size={25} />
                          </span>
                          <h2>Start with a good question.</h2>
                          <p>
                            Ask about a concept, work through an example,
                            <br />
                            or connect ideas across your documents.
                          </p>
                          <div className="suggestions">
                            {suggestions.map((text) => (
                              <button
                                disabled={busy || !selected.length}
                                key={text}
                                onClick={() => void ask(text)}
                              >
                                {text}
                                <ChevronRight size={16} />
                              </button>
                            ))}
                          </div>
                          <p className="evidence-note">
                            <FileText size={14} />
                            Every answer starts with your sources.
                          </p>
                        </div>
                      ) : (
                        <div className="conversation">
                          {messages.map((message, index) => (
                            <article key={index}>
                              <div className="question-bubble">
                                {message.question}
                              </div>
                              <div className="answer">
                                <div className="answer-label">
                                  <BookOpen size={17} />
                                  From your documents
                                </div>
                                {message.answer.status !== "answered" && (
                                  <span className="answer-status">
                                    {message.answer.status.replaceAll("_", " ")}
                                  </span>
                                )}
                                <Markdown>{message.answer.answer}</Markdown>
                                <References
                                  items={message.answer.citations}
                                  onOpen={(c) => void openSource(c)}
                                />
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      {active?.kind === "summary" ? (
                        <div className="study-result">
                          <div className="result-heading">
                            <h2>Your revision notes</h2>
                            <button
                              onClick={() =>
                                download(
                                  "summary.md",
                                  active.sections
                                    .map(
                                      (s) =>
                                        `# Overview\n\n${s.overview}\n\n## Key concepts\n${s.key_concepts.map((x) => "- " + x).join("\n")}\n\n## Definitions\n${s.definitions.map((x) => "- " + x).join("\n")}\n\n## Revision points\n${s.revision_points.map((x) => "- " + x).join("\n")}\n\n${s.citations.map((c) => `${c.filename}, p. ${c.page}: ${c.quote}`).join("\n")}`,
                                    )
                                    .join("\n\n") +
                                    (active.incomplete
                                      ? "\n\nINCOMPLETE COVERAGE: " +
                                        active.failed_pages.join(", ")
                                      : ""),
                                )
                              }
                            >
                              <Download size={16} />
                              Export
                            </button>
                          </div>
                          {active.incomplete && (
                            <p role="alert" className="coverage-warning">
                              Incomplete coverage. Unprocessed pages:{" "}
                              {active.failed_pages.join(", ")}
                            </p>
                          )}
                          {active.sections.map((section, i) => (
                            <section key={i}>
                              <Markdown>{section.overview}</Markdown>
                              {(
                                [
                                  "key_concepts",
                                  "definitions",
                                  "revision_points",
                                ] as const
                              ).map((key) => (
                                <div key={key}>
                                  <h3>{key.replaceAll("_", " ")}</h3>
                                  <ul>
                                    {section[key].map((text, n) => (
                                      <li key={n}>
                                        <Markdown>{text}</Markdown>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              ))}
                              <References
                                items={section.citations}
                                onOpen={(c) => void openSource(c)}
                              />
                            </section>
                          ))}
                        </div>
                      ) : active?.kind === "quiz" ? (
                        <QuizView
                          key={materials.indexOf(active)}
                          quiz={active}
                          onOpen={(c) => void openSource(c)}
                        />
                      ) : active?.kind === "flashcards" ? (
                        <CardsView
                          key={materials.indexOf(active)}
                          set={active}
                          onOpen={(c) => void openSource(c)}
                        />
                      ) : (
                        <div className="tool-empty">
                          <span className="activity-icon">
                            {tab === "Summary" ? (
                              <NotebookPen size={26} />
                            ) : tab === "Quiz" ? (
                              <ListChecks size={26} />
                            ) : (
                              <Layers size={26} />
                            )}
                          </span>
                          <h2>
                            {tab === "Summary"
                              ? "Find the ideas that matter."
                              : tab === "Quiz"
                                ? "Put your understanding to work."
                                : "Make your next revision easier."}
                          </h2>
                          <p>
                            {tab === "Summary"
                              ? "Overview, concepts, definitions, and revision points across the full selected scope."
                              : tab === "Quiz"
                                ? "Five questions. Four options each. Explanations and evidence after you submit."
                                : "Ten focused cards, grounded in your course. Flip to learn; export to Anki."}
                          </p>
                        </div>
                      )}
                      {tab === "Summary" && (
                        <div className="range-fields">
                          <label>
                            From page
                            <input
                              type="number"
                              min="1"
                              placeholder="First"
                              value={range.start}
                              onChange={(e) =>
                                setRange({ ...range, start: e.target.value })
                              }
                            />
                          </label>
                          <label>
                            To page
                            <input
                              type="number"
                              min="1"
                              placeholder="Last"
                              value={range.end}
                              onChange={(e) =>
                                setRange({ ...range, end: e.target.value })
                              }
                            />
                          </label>
                          <small>
                            Select one document. Leave blank for all pages.
                          </small>
                        </div>
                      )}
                      <div className="generate-row">
                        <button
                          className="primary"
                          disabled={
                            busy ||
                            !selected.length ||
                            (tab === "Summary" && selected.length !== 1)
                          }
                          onClick={() => void generate()}
                        >
                          {active ? <RotateCcw size={16} /> : null}
                          {active
                            ? "Generate again"
                            : `Create ${tab.toLowerCase()}`}
                        </button>
                        {materials.filter((m) => m.kind === tab.toLowerCase())
                          .length > 0 && (
                          <select
                            aria-label="Saved study materials"
                            value={
                              activeMaterial
                                ? materials.indexOf(activeMaterial)
                                : -1
                            }
                            onChange={(e) =>
                              setActiveMaterial(
                                materials[Number(e.target.value)],
                              )
                            }
                          >
                            <option value={-1}>Previous materials</option>
                            {materials.map((m, i) =>
                              m.kind === tab.toLowerCase() ? (
                                <option key={i} value={i}>
                                  {tab} {i + 1}
                                </option>
                              ) : null,
                            )}
                          </select>
                        )}
                      </div>
                    </>
                  )}
                </div>
                {busy && (
                  <div className="processing" role="status">
                    <span className="spinner" />
                    {job ? job.stage : "Working…"}
                    {job && (
                      <progress
                        value={job.progress}
                        max="100"
                        aria-label="Processing progress"
                      />
                    )}
                  </div>
                )}
                {tab === "Ask" && (
                  <form
                    className="composer"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void ask();
                    }}
                  >
                    <label className="sr-only" htmlFor="question">
                      Ask about your documents
                    </label>
                    <textarea
                      id="question"
                      placeholder="Ask about your documents…"
                      rows={2}
                      maxLength={2000}
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          if (!busy) void ask();
                        }
                      }}
                    />
                    <div>
                      <span>
                        {selected.length
                          ? `Using ${selected.length} selected documents`
                          : "Select a ready document to begin"}
                      </span>
                      <button
                        className="send"
                        aria-label="Send question"
                        disabled={busy || !question.trim() || !selected.length}
                      >
                        <ArrowUp size={19} />
                      </button>
                    </div>
                  </form>
                )}
                <p className="study-footer">
                  Check the cited evidence. AI can make mistakes.
                </p>
              </section>
            </main>
            <aside className="source-panel">
              <div className="source-heading">
                <span className="section-title">Source evidence</span>
                <PanelRight size={16} />
              </div>
              {sourcePanel}
            </aside>
          </div>
          {drawer && (
            <Drawer
              title={drawer === "library" ? "Your library" : "Source evidence"}
              close={() => setDrawer(undefined)}
            >
              {drawer === "library" ? library : sourcePanel}
            </Drawer>
          )}
        </>
      )}
      {drag && (
        <div className="drop-overlay">
          <Upload size={42} />
          <h2>Drop your PDFs here</h2>
          <p>Text-based PDFs · up to 10 MB each</p>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);

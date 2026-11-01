import { useEffect, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import worker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { base } from "./api";
GlobalWorkerOptions.workerSrc = worker;

export function PdfPreview({
  documentId,
  page,
}: {
  documentId: string;
  page: number;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    const task = getDocument({
      url: `${base}/api/documents/${documentId}/pdf`,
      httpHeaders: {
        Authorization: `Bearer ${sessionStorage.getItem("study-token")}`,
      },
      enableXfa: false,
    });
    setError("");
    void (async () => {
      try {
        const pdf = await task.promise;
        const pdfPage = await pdf.getPage(page);
        if (cancelled || !canvas.current) return;
        const viewport = pdfPage.getViewport({ scale: 1.25 });
        const target = canvas.current;
        target.width = viewport.width;
        target.height = viewport.height;
        await pdfPage.render({ canvas: target, viewport }).promise;
      } catch {
        if (!cancelled)
          setError(
            "PDF preview unavailable. The extracted passage is shown above.",
          );
      }
    })();
    return () => {
      cancelled = true;
      void task.destroy();
    };
  }, [documentId, page]);
  return error ? (
    <p className="muted">{error}</p>
  ) : (
    <canvas
      ref={canvas}
      className="pdf-canvas"
      role="img"
      aria-label={`PDF preview, physical page ${page}`}
    />
  );
}

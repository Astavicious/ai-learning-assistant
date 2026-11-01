"""Isolated parser process. stdout is machine-readable and never logged by the API."""

import json
import os
import sys

from pypdf import PdfReader


def extract(path):
    if os.name == "posix":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (192 * 1024 * 1024, 192 * 1024 * 1024))
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            return {"error": "encrypted_pdf", "message": "Remove the PDF password before uploading."}
        if not reader.pages:
            return {"error": "empty_pdf", "message": "This PDF contains no pages."}
        if len(reader.pages) > 150:
            return {"error": "page_limit", "message": "A session supports at most 150 PDF pages."}
        pages, unreadable, total = [], [], 0
        for number, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                text = ""
            total += len(text)
            if total > 1_000_000:
                return {"error": "text_limit", "message": "This PDF exceeds the extracted-text limit."}
            if not text.strip():
                unreadable.append(number)
            pages.append(text)
        if len(unreadable) == len(pages):
            return {
                "error": "image_only_pdf",
                "message": "No readable text found. Scanned PDFs require OCR, which is not supported.",
            }
        return {"pages": pages, "unreadable": unreadable}
    except MemoryError:
        return {
            "error": "parse_memory_limit",
            "message": "This PDF requires too much memory to extract safely. Export a simpler text PDF.",
        }
    except Exception:
        return {
            "error": "corrupt_pdf",
            "message": "This PDF could not be read. Export a new text-based PDF and retry.",
        }


if __name__ == "__main__":
    print(json.dumps(extract(sys.argv[1])))

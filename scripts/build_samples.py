"""Build original, deterministic, publishable text PDFs from the editable course source."""

import json
import textwrap
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas

root = Path(__file__).resolve().parents[1] / "backend/samples"
course = json.loads((root / "source/course.json").read_text(encoding="utf-8"))
for document in course:
    canvas = Canvas(str(root / document["file"]), pagesize=(595, 842), invariant=1)
    canvas.setTitle(document["title"])
    canvas.setAuthor("Bilal Amin — AI Learning Assistant original sample course")
    for number, page in enumerate(document["pages"], 1):
        canvas.setFillColor(HexColor("#275fc6"))
        canvas.setFont("Helvetica", 10)
        canvas.drawString(48, 790, "AI Learning Assistant / Functional Programming")
        canvas.setFillColor(HexColor("#172d4d"))
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawString(48, 755, page["heading"])
        y = 715
        for paragraph in page["text"].split("\n"):
            code = paragraph.startswith("  ")
            canvas.setFont("Courier" if code else "Helvetica", 10.5)
            for line in textwrap.wrap(paragraph, width=76, replace_whitespace=False) or [""]:
                canvas.drawString(48, y, line)
                y -= 15
        if y < 65:
            raise ValueError(f"Sample page overflows: {document['file']}, page {number}")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(HexColor("#6c7d93"))
        canvas.drawString(48, 35, "Original educational material / CC BY 4.0 / Bilal Amin")
        canvas.drawRightString(547, 35, f"{number} / {len(document['pages'])}")
        canvas.showPage()
    canvas.save()
print(f"Built {len(course)} PDFs / {sum(len(d['pages']) for d in course)} pages")

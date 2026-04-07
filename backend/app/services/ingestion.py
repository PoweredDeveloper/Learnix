from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text()
        except Exception:
            continue
        if t:
            parts.append(t)
    return "\n\n".join(parts).strip()

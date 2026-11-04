"""Reading transcripts from uploaded TXT / DOCX files, with clear error messages."""
from __future__ import annotations

import io
import zipfile

from . import config


class InputError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.message, self.status = message, status


def decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = data.decode(enc)
            if enc == "utf-16" and not data[:2] in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return text
        except UnicodeDecodeError:
            continue
    raise InputError("The file could not be decoded as text. Save it as UTF-8 and try again.")


def read_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError as e:  # pragma: no cover
        raise InputError("DOCX support needs the 'python-docx' package (pip install python-docx).", 501) from e
    try:
        doc = Document(io.BytesIO(data))
    except (zipfile.BadZipFile, KeyError, ValueError) as e:
        raise InputError("This file is not a valid .docx document (it may be corrupted or an old .doc file).") from e
    lines = [p.text for p in doc.paragraphs]
    for table in doc.tables:  # transcripts exported as tables: speaker | text
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if len(cells) == 2:
                lines.append(f"{cells[0]}: {cells[1]}")
            elif cells:
                lines.append(" ".join(cells))
    return "\n".join(lines)


def extract_text(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if not data:
        raise InputError("The uploaded file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise InputError(f"File is too large (limit {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB).", 413)
    if name.endswith(".docx"):
        text = read_docx(data)
    elif name.endswith((".txt", ".text", ".md", ".log", ".vtt", ".srt")):
        text = decode_text(data)
    elif name.endswith(".doc"):
        raise InputError("Legacy .doc files are not supported. Please save the file as .docx or .txt.", 415)
    else:
        raise InputError("Unsupported file type. Please upload a .txt or .docx file.", 415)
    validate_transcript(text)
    return text


def validate_transcript(text: str) -> None:
    if not text or not text.strip():
        raise InputError("The transcript is empty. Paste text or upload a file that contains text.")
    if len(text.strip()) < config.MIN_TRANSCRIPT_CHARS:
        raise InputError(f"The transcript is too short to analyse (at least {config.MIN_TRANSCRIPT_CHARS} characters).")
    if len(text) > config.MAX_TRANSCRIPT_CHARS:
        raise InputError(f"The transcript is too long ({len(text):,} characters; limit {config.MAX_TRANSCRIPT_CHARS:,}).", 413)
    letters = sum(ch.isalpha() for ch in text)
    if letters < 0.3 * len(text.strip()):
        raise InputError("The text does not look like a conversation transcript (too few letters).")

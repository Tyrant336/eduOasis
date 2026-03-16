import fitz  # PyMuPDF


def extract_text(content: bytes, file_type: str) -> str:
    if file_type in ("txt", "md"):
        return content.decode("utf-8")
    elif file_type == "pdf":
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    char_limit = chunk_size * 4
    char_overlap = chunk_overlap * 4

    if len(text) <= char_limit:
        return [text.strip()] if text.strip() else []

    separators = ["\n\n", "\n", ". ", " "]
    return _recursive_split(text, separators, char_limit, char_overlap)


def _recursive_split(text, separators, char_limit, char_overlap):
    if len(text) <= char_limit:
        return [text.strip()] if text.strip() else []

    sep = separators[0] if separators else " "
    remaining_seps = separators[1:] if len(separators) > 1 else separators

    parts = text.split(sep)
    chunks = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) > char_limit and current:
            chunks.append(current.strip())
            overlap_text = current[-char_overlap:] if char_overlap else ""
            current = overlap_text + sep + part if overlap_text else part
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    final = []
    for chunk in chunks:
        if len(chunk) > char_limit and remaining_seps != separators:
            final.extend(_recursive_split(chunk, remaining_seps, char_limit, char_overlap))
        else:
            final.append(chunk)

    return final


def estimate_tokens(text: str) -> int:
    return len(text) // 4

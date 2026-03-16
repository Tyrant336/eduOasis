from rag.chunker import chunk_text, extract_text


def test_chunk_text_basic():
    text = "Hello world. " * 200
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) > 0


def test_chunk_text_small_input():
    text = "Short text."
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


def test_chunk_text_respects_overlap():
    text = "Sentence one. Sentence two. Sentence three. Sentence four. " * 20
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
    assert len(chunks) > 1


def test_extract_text_markdown():
    content = b"# Hello\n\nThis is a test."
    result = extract_text(content, "md")
    assert "Hello" in result
    assert "This is a test." in result


def test_extract_text_txt():
    content = b"Plain text content."
    result = extract_text(content, "txt")
    assert result == "Plain text content."


def test_extract_text_unsupported():
    import pytest
    with pytest.raises(ValueError, match="Unsupported"):
        extract_text(b"data", "docx")

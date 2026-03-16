import json
from unittest.mock import AsyncMock, patch


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "documents" in data
    assert "chunks" in data


def test_get_documents_empty(client):
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_nonexistent_document(client):
    resp = client.delete("/documents/999")
    assert resp.status_code == 404


@patch("routes.upload.get_embeddings_batch", new_callable=AsyncMock)
def test_upload_txt(mock_embed, client):
    mock_embed.return_value = [[0.1] * 1536]
    resp = client.post(
        "/upload",
        files={"file": ("test.txt", b"Hello world content for testing.", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "indexed"
    assert data["filename"] == "test.txt"
    assert data["chunks"] >= 1


def test_upload_unsupported_type(client):
    resp = client.post(
        "/upload",
        files={"file": ("test.docx", b"data", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


@patch("routes.chat.retrieve_context", new_callable=AsyncMock)
@patch("routes.chat.stream_response")
def test_chat_streams_response(mock_stream, mock_retrieve, client):
    mock_retrieve.return_value = [
        {"chunk_id": 1, "distance": 0.1, "text": "Test content", "filename": "test.md"}
    ]

    async def fake_stream(messages):
        yield "Hello "
        yield "world"

    mock_stream.return_value = fake_stream(None)

    resp = client.post(
        "/chat",
        json={"message": "What is this?", "history": []},
    )
    assert resp.status_code == 200
    text = resp.text
    assert "data:" in text

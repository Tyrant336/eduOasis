from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from rag.chunker import extract_text, chunk_text, estimate_tokens
from rag.embeddings import get_embeddings_batch
from db.models import insert_document, insert_chunk, insert_chunk_vector

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    from config import settings
    conn = request.app.state.db
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("txt", "md", "pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: .txt, .md, .pdf",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10 MB.")

    try:
        text = extract_text(content, ext)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {e}")

    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text content found in file.")

    try:
        embeddings = await get_embeddings_batch(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    doc_id = insert_document(conn, filename, ext)
    for i, (chunk_text_str, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = insert_chunk(conn, doc_id, chunk_text_str, i, estimate_tokens(chunk_text_str))
        insert_chunk_vector(conn, chunk_id, embedding)

    return {"document_id": doc_id, "filename": filename, "chunks": len(chunks), "status": "indexed"}

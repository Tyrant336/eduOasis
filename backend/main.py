import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.init import init_db
from db.models import get_document_count, get_chunk_count
from routes.chat import router as chat_router
from routes.upload import router as upload_router
from routes.documents import router as documents_router


async def seed_sample_docs(app: FastAPI):
    from config import settings
    conn = app.state.db
    if get_document_count(conn) > 0:
        return

    sample_dir = os.path.join(os.path.dirname(__file__), "sample_docs")
    if not os.path.isdir(sample_dir):
        return

    from rag.chunker import extract_text, chunk_text, estimate_tokens
    from rag.embeddings import get_embeddings_batch
    from db.models import insert_document, insert_chunk, insert_chunk_vector

    for filename in os.listdir(sample_dir):
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in ("txt", "md", "pdf"):
            continue
        filepath = os.path.join(sample_dir, filename)
        with open(filepath, "rb") as f:
            content = f.read()
        text = extract_text(content, ext)
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            continue
        try:
            embeddings = await get_embeddings_batch(chunks)
        except Exception as e:
            print(f"Warning: Failed to embed {filename}: {e}")
            continue
        doc_id = insert_document(conn, filename, ext)
        for i, (chunk_text_str, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = insert_chunk(conn, doc_id, chunk_text_str, i, estimate_tokens(chunk_text_str))
            insert_chunk_vector(conn, chunk_id, embedding)
    print(f"Seeded {get_document_count(conn)} sample documents.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from config import settings
    app.state.db = init_db(settings.db_path)
    await seed_sample_docs(app)
    yield
    app.state.db.close()


app = FastAPI(title="Edu Oasis RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(documents_router)


@app.get("/health")
async def health():
    conn = app.state.db
    return {
        "status": "ok",
        "documents": get_document_count(conn),
        "chunks": get_chunk_count(conn),
    }

import sqlite3
from rag.embeddings import get_embedding
from db.models import search_chunks
from config import settings


async def retrieve_context(conn: sqlite3.Connection, query: str) -> list[dict]:
    query_embedding = await get_embedding(query)
    results = search_chunks(conn, query_embedding, top_k=settings.top_k)
    return results

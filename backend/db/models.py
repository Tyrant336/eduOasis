import sqlite3
import struct


def insert_document(conn: sqlite3.Connection, filename: str, file_type: str) -> int:
    cursor = conn.execute(
        "INSERT INTO documents (filename, file_type) VALUES (?, ?)",
        (filename, file_type),
    )
    conn.commit()
    return cursor.lastrowid


def insert_chunk(
    conn: sqlite3.Connection,
    doc_id: int,
    text: str,
    position: int,
    token_count: int,
) -> int:
    cursor = conn.execute(
        "INSERT INTO chunks (doc_id, text, position, token_count) VALUES (?, ?, ?, ?)",
        (doc_id, text, position, token_count),
    )
    conn.commit()
    return cursor.lastrowid


def insert_chunk_vector(
    conn: sqlite3.Connection, chunk_id: int, embedding: list[float]
) -> None:
    conn.execute(
        "INSERT INTO chunks_vec (chunk_id, embedding) VALUES (?, ?)",
        (chunk_id, serialize_float32(embedding)),
    )
    conn.commit()


def search_chunks(
    conn: sqlite3.Connection, query_embedding: list[float], top_k: int = 5
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT chunks_vec.chunk_id, chunks_vec.distance, chunks.text, documents.filename
        FROM chunks_vec
        LEFT JOIN chunks ON chunks.id = chunks_vec.chunk_id
        LEFT JOIN documents ON documents.id = chunks.doc_id
        WHERE embedding MATCH ?
        AND k = ?
        ORDER BY distance
        """,
        (serialize_float32(query_embedding), top_k),
    ).fetchall()
    return [
        {"chunk_id": r[0], "distance": r[1], "text": r[2], "filename": r[3]}
        for r in rows
    ]


def get_documents(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT d.id, d.filename, d.file_type, d.uploaded_at,
               COUNT(c.id) as chunk_count
        FROM documents d
        LEFT JOIN chunks c ON c.doc_id = d.id
        GROUP BY d.id
        ORDER BY d.uploaded_at DESC
        """
    ).fetchall()
    return [
        {
            "id": r[0],
            "filename": r[1],
            "file_type": r[2],
            "uploaded_at": r[3],
            "chunk_count": r[4],
        }
        for r in rows
    ]


def delete_document(conn: sqlite3.Connection, doc_id: int) -> bool:
    # Explicit transaction: delete vectors, then document (cascades to chunks)
    conn.execute("BEGIN")
    try:
        chunk_ids = conn.execute(
            "SELECT id FROM chunks WHERE doc_id = ?", (doc_id,)
        ).fetchall()
        for (chunk_id,) in chunk_ids:
            conn.execute("DELETE FROM chunks_vec WHERE chunk_id = ?", (chunk_id,))
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


def get_document_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]


def get_chunk_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def serialize_float32(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)

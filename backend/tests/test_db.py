def test_init_db_creates_tables(test_db):
    cursor = test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    assert "documents" in tables
    assert "chunks" in tables


def test_init_db_creates_vec_table(test_db):
    cursor = test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    assert "chunks_vec" in tables


from db.models import insert_document, insert_chunk, get_documents, delete_document


def test_insert_and_get_document(test_db):
    doc_id = insert_document(test_db, "test.md", "md")
    docs = get_documents(test_db)
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id
    assert docs[0]["filename"] == "test.md"


def test_insert_chunk(test_db):
    doc_id = insert_document(test_db, "test.md", "md")
    chunk_id = insert_chunk(test_db, doc_id, "Hello world", 0, 2)
    cursor = test_db.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
    row = cursor.fetchone()
    assert row is not None


def test_delete_document_cascades(test_db):
    doc_id = insert_document(test_db, "test.md", "md")
    insert_chunk(test_db, doc_id, "Hello world", 0, 2)
    delete_document(test_db, doc_id)
    docs = get_documents(test_db)
    assert len(docs) == 0
    cursor = test_db.execute("SELECT COUNT(*) FROM chunks")
    assert cursor.fetchone()[0] == 0

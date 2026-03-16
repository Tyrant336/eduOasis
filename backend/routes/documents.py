from fastapi import APIRouter, Request, HTTPException
from db.models import get_documents, delete_document

router = APIRouter()


@router.get("/documents")
async def list_documents(request: Request):
    conn = request.app.state.db
    return get_documents(conn)


@router.delete("/documents/{doc_id}")
async def remove_document(doc_id: int, request: Request):
    conn = request.app.state.db
    deleted = delete_document(conn, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted"}

import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from rag.retrieval import retrieve_context
from rag.generation import build_prompt, stream_response

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    conn = request.app.state.db
    context_chunks = await retrieve_context(conn, req.message)
    messages = build_prompt(context_chunks, req.message, req.history)
    sources = list({c["filename"] for c in context_chunks if c["filename"]})

    async def event_stream():
        try:
            async for token in stream_response(messages):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# RAG Chatbot for Edu Oasis

**Date:** 2026-03-16
**Status:** Approved

## Summary

Replace the static Recipe Finder modal on Project_1 with an interactive RAG (Retrieval-Augmented Generation) chatbot. When the user clicks the Project_1 board in the 3D game world, a slide-in chat panel opens from the right. Users can ask questions about course materials and drag-and-drop documents directly into the panel to expand the knowledge base.

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   BROWSER (Client)                    │
│                                                       │
│  Three.js Game World                                  │
│    ├── Click Project_1 → opens slide-in chat panel    │
│    └── Chat panel:                                    │
│          ├── Message bubbles (chat history)            │
│          ├── Text input + send button                  │
│          ├── Drag-and-drop zone for file uploads       │
│          └── Close button → panel slides out           │
│                                                       │
│  Communicates via fetch() to backend                  │
└──────────────┬──────────────────┬─────────────────────┘
               │ POST /chat       │ POST /upload
               ▼                  ▼
┌──────────────────────────────────────────────────────┐
│                  FastAPI Backend                       │
│                                                       │
│  /chat endpoint:                                      │
│    1. Embed user query (OpenRouter)                   │
│    2. Vector search in SQLite (top-5 chunks)          │
│    3. Build prompt: system + chunks + user question   │
│    4. Stream response from OpenRouter LLM             │
│    5. Return streamed response to client via SSE      │
│                                                       │
│  /upload endpoint:                                    │
│    1. Receive file (PDF, TXT, MD)                     │
│    2. Extract text content                            │
│    3. Chunk text (500 tokens, 50 overlap)             │
│    4. Embed each chunk (OpenRouter)                   │
│    5. Store chunks + vectors in SQLite                │
│    6. Return success + document metadata              │
│                                                       │
│  SQLite + sqlite-vec:                                 │
│    ├── documents table (id, filename, uploaded_at)    │
│    ├── chunks table (id, doc_id, text, position)      │
│    └── chunks_vec virtual table (embedding vectors)   │
└──────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Vanilla JS (existing) | Chat panel UI, SSE consumption, drag-and-drop |
| Backend | Python FastAPI | API server, RAG pipeline orchestration |
| Database | SQLite + sqlite-vec | Document storage, vector search |
| Embeddings | OpenRouter (`openai/text-embedding-3-small`) | 1536-dim embeddings for queries and chunks |
| Generation | OpenRouter (configurable model, default `openai/gpt-4o-mini`) | Streaming chat responses |
| PDF parsing | PyMuPDF | Text extraction from PDF files |

## Frontend Changes

### Modified Files

**`main.js`** — In `handleInteraction()`, add a branch before the existing `showModal()` call. The current code (around line 526) calls `showModal(intersectObject)` for all non-Pokemon objects. Change this to:

The existing code at lines 508-531 uses an inline array check for Pokemon names, then falls through to `showModal()` in the `else` branch. Insert the Project_1 check inside that `else` branch:

```javascript
// Existing else branch (non-Pokemon objects), around line 525:
} else {
  if (intersectObject === "Project_1") {
    openChatPanel();
  } else {
    showModal(intersectObject);
  }
  playSound("projectsSFX");
}
```

This preserves the existing modal behavior for Project_2, Project_3, Picnic, and Chest while routing only Project_1 to the chat panel.

**`index.html`** — Add chat panel HTML as a sibling to the existing modal:

```
<div id="chat-panel" class="chat-panel hidden">
  ├── Header: title ("Course Assistant") + close button
  ├── Messages container (scrollable)
  │     ├── Bot message bubbles (left-aligned)
  │     └── User message bubbles (right-aligned)
  ├── Drop zone overlay (appears on file drag-over)
  └── Input bar: text input + send button
</div>
```

**`style.css`** — Chat panel styles with slide-in animation from right (`transform: translateX(100%)` → `translateX(0)`).

### Interaction Flow

1. Click Project_1 board → `openChatPanel()` called
2. Panel slides in from right, game controls disabled. Note: the existing `isModalOpen` flag only guards raycast interactions in `handleInteraction()`. The keyboard handlers (`onKeyDown`/`onKeyUp`) do NOT check this flag. `openChatPanel()` must also set a `isChatOpen` flag that the keyboard handlers check to suppress WASD/arrow/space inputs while the panel is open. Similarly, `closeChatPanel()` clears this flag to re-enable controls.
3. User types message → `POST /chat` with message + last 5 exchanges as history
4. Response streams in as bot bubble via SSE (Server-Sent Events)
5. User drags file onto panel → drop zone highlights → `POST /upload` → confirmation in chat
6. Click close or press Escape → panel slides out, game controls re-enabled

### Theme Support

Panel uses existing CSS variables (`--pastel-pink`, `--pastel-blue`) to respect the light/dark theme toggle already in the game.

### UI Style

- Slide-in panel from the right (~40% viewport width on desktop, 100% on mobile/screens < 1100px)
- 3D game world remains partially visible on the left (desktop only)
- Chat bubbles: bot messages left-aligned, user messages right-aligned
- Drop zone: dashed border overlay that appears when dragging files over the panel

## Backend Structure

```
backend/
├── main.py              # FastAPI app, CORS, routes
├── routes/
│   ├── chat.py          # /chat endpoint (SSE streaming)
│   ├── upload.py        # /upload endpoint (file processing)
│   └── documents.py     # /documents GET + DELETE endpoints
├── rag/
│   ├── embeddings.py    # OpenRouter embedding calls
│   ├── retrieval.py     # Vector search in SQLite
│   ├── generation.py    # Prompt building + LLM streaming
│   └── chunker.py       # Text extraction + chunking
├── db/
│   ├── init.py          # SQLite + sqlite-vec setup
│   └── models.py        # Table schemas
├── requirements.txt
├── .env.example         # OPENROUTER_API_KEY=your-key-here
└── sample_docs/         # Demo documents
    ├── intro-to-web-dev.md
    └── database-basics.md
```

### Chunking Strategy

- ~500-token chunks with ~50-token overlap (approximated as `chars / 4` — no tokenizer dependency needed)
- Recursive character splitter: split on `\n\n` → `\n` → `. ` → ` `
- No heavy library needed — simple custom implementation
- Max upload file size: **10 MB** (enforced at the endpoint level)

### System Prompt

```
You are a helpful course assistant for Edu Oasis. Answer questions
based on the provided course materials. If the answer isn't in the
materials, say so honestly. Keep responses concise and educational.
```

## Database Schema

```sql
CREATE TABLE documents (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  filename    TEXT NOT NULL,
  file_type   TEXT NOT NULL,
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chunks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id      INTEGER REFERENCES documents(id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  position    INTEGER NOT NULL,
  token_count INTEGER NOT NULL
);

-- sqlite-vec virtual table
CREATE VIRTUAL TABLE chunks_vec USING vec0(
  chunk_id INTEGER PRIMARY KEY,
  embedding FLOAT[1536]
);
```

### Data Integrity

The `chunks_vec` virtual table does not participate in SQLite foreign key cascades. All inserts and deletes must be handled at the application level in a transaction:

- **On insert:** Insert into `chunks`, then insert into `chunks_vec` with matching `chunk_id`, within a single transaction.
- **On delete (`DELETE /documents/{id}`):** First query all `chunk_id`s for the document, delete from `chunks_vec` by those IDs, then delete the document (which cascades to `chunks`). All in a single transaction.

### Retrieval Flow

1. Embed user query → 1536-dimensional vector
2. Vector search: `SELECT chunk_id, distance FROM chunks_vec WHERE embedding MATCH ? ORDER BY distance LIMIT 5`
3. Join to `chunks` table for text content
4. Feed top-5 chunks as context into the LLM prompt

## API Endpoints

### `POST /chat`

```
Request:
{
  "message": "What is a database?",
  "history": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi! How can I help?" }
  ]
}

Response: SSE stream
  data: {"token": "A "}
  data: {"token": "database "}
  ...
  data: {"done": true, "sources": ["database-basics.md (chunk 3)"]}
  data: {"error": "OpenRouter API timeout"}   // on failure mid-stream
```

History uses the `{ "role": "user"|"assistant", "content": "..." }` format (OpenAI-compatible). The frontend maintains the last 5 exchanges in memory and sends them with each request.

### `POST /upload`

```
Request:  multipart/form-data with file attachment
Response: { "document_id": 1, "filename": "slides.pdf", "chunks": 12, "status": "indexed" }
```

### `GET /documents`

```
Response: [{ "id": 1, "filename": "slides.pdf", "uploaded_at": "...", "chunk_count": 12 }]
```

### `DELETE /documents/{id}`

```
Response: { "status": "deleted" }
```

### `GET /health`

```
Response: { "status": "ok", "documents": 3, "chunks": 47 }
```

## Configuration

All configuration via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | (required) | API key for OpenRouter |
| `EMBEDDING_MODEL` | `openai/text-embedding-3-small` | Model for embeddings |
| `CHAT_MODEL` | `openai/gpt-4o-mini` | Model for chat generation |
| `DB_PATH` | `./data/rag.db` | SQLite database file path |
| `CHUNK_SIZE` | `500` | Token count per chunk |
| `CHUNK_OVERLAP` | `50` | Token overlap between chunks |
| `TOP_K` | `5` | Number of chunks to retrieve |
| `BACKEND_PORT` | `8081` | FastAPI server port |

## Supported File Types

| Type | Extension | Extraction Method |
|------|-----------|-------------------|
| Plain text | `.txt` | Direct read |
| Markdown | `.md` | Direct read |
| PDF | `.pdf` | PyMuPDF text extraction |

## Demo Content

Two sample markdown documents ship with the project:

- `intro-to-web-dev.md` — Basics of HTML, CSS, JavaScript
- `database-basics.md` — SQL fundamentals, tables, queries

These are pre-ingested on first backend startup via a FastAPI `lifespan` event. On startup, the app checks if the `documents` table is empty. If so, it reads files from `sample_docs/`, chunks, embeds, and inserts them. If documents already exist, the step is skipped (idempotent — no duplicate ingestion on restarts).

## Error Handling

- **No documents indexed:** Bot responds with "I don't have any course materials yet. Try uploading some documents!"
- **Upload fails:** Error message shown in chat bubble with retry suggestion
- **Backend unreachable:** Chat panel shows connection error with retry button
- **Unsupported file type:** Reject with message listing supported formats
- **OpenRouter API error:** Surface error to user, suggest checking API key

## Development Setup

During development, two servers run simultaneously:
- **Frontend:** Existing Python HTTP server (`python start_server.py`) on port 8080 serving static files
- **Backend:** FastAPI server (`uvicorn main:app`) on port 8081

The FastAPI backend has CORS configured to allow requests from `http://localhost:8080`. In production, the FastAPI server could optionally serve the static files too, but for development they remain separate.

### HTTP Error Codes (non-streaming endpoints)

| Endpoint | Success | Error Cases |
|----------|---------|-------------|
| `POST /upload` | 200 | 400 (unsupported type), 413 (file too large), 500 (embedding failure) |
| `GET /documents` | 200 | 500 (DB error) |
| `DELETE /documents/{id}` | 200 | 404 (not found) |
| `GET /health` | 200 | — |

## What This Does NOT Include

- User authentication or sessions
- Conversation persistence (chat history lives in browser memory only)
- Admin UI for document management (API-only for now)
- PPTX support (can be added later with `python-pptx`)
- Rate limiting

from collections.abc import AsyncGenerator
import json
import httpx

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """You are a helpful course assistant for Edu Oasis. Answer questions \
based on the provided course materials. If the answer isn't in the \
materials, say so honestly. Keep responses concise and educational."""


def build_prompt(context_chunks: list[dict], user_message: str, history: list[dict]) -> list[dict]:
    context_text = "\n\n---\n\n".join(
        f"[Source: {c['filename']}]\n{c['text']}" for c in context_chunks
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Relevant course materials:\n\n{context_text}"},
    ]

    for entry in history[-10:]:
        messages.append({"role": entry["role"], "content": entry["content"]})

    messages.append({"role": "user", "content": user_message})
    return messages


async def stream_response(messages: list[dict]) -> AsyncGenerator[str, None]:
    from config import settings
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.chat_model, "messages": messages, "stream": True},
            timeout=60.0,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

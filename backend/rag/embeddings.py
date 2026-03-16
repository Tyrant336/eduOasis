import httpx

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


async def get_embedding(text: str) -> list[float]:
    from config import settings
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.embedding_model, "input": text},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    from config import settings
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENROUTER_BASE}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.embedding_model, "input": texts},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

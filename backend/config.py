from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str
    embedding_model: str = "openai/text-embedding-3-small"
    chat_model: str = "openai/gpt-4o-mini"
    db_path: str = "./data/rag.db"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    backend_port: int = 8081

    model_config = {"env_file": ".env"}


settings = Settings()

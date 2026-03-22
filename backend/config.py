from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str
    supabase_url: str
    supabase_service_key: str

    llm_model: str = "llama-3.3-70b-versatile"
    max_tokens: int = 1024

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    top_k_results: int = 3
    similarity_threshold: float = 0.3

    max_conversation_turns: int = 20
    summarize_after_turns: int = 15
    max_context_tokens: int = 3000

settings = Settings()
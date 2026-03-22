"""
rag/embeddings.py — Local embeddings using sentence-transformers (completely free).

Model: all-MiniLM-L6-v2
- 384 dimensions (vs 1536 for OpenAI, but plenty for our use case)
- Runs on CPU, no API key needed
- First run downloads the model (~90MB), cached after that
"""
from sentence_transformers import SentenceTransformer
from backend.config import settings

# Loaded once at startup, reused for all requests
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("Loading embedding model (first time only)...")
        _model = SentenceTransformer(settings.embedding_model)
        print("Embedding model loaded!")
    return _model


async def embed_text(text: str) -> list[float]:
    """Embed a single query string."""
    model = _get_model()
    embedding = model.encode(text.replace("\n", " "), convert_to_tensor=False)
    return embedding.tolist()


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts at once (for seeding the knowledge base)."""
    model = _get_model()
    cleaned = [t.replace("\n", " ") for t in texts]
    embeddings = model.encode(cleaned, convert_to_tensor=False)
    return [e.tolist() for e in embeddings]
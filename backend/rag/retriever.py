from backend.config import settings
from backend.database.client import get_supabase
from backend.rag.embeddings import embed_text


async def retrieve_context(query: str) -> tuple[str, list[str]]:
    try:
        query_embedding = await embed_text(query)

        db = get_supabase()
        result = db.rpc(
            "match_knowledge",
            {
                "query_embedding": query_embedding,
                "match_threshold": settings.similarity_threshold,
                "match_count": settings.top_k_results,
            },
        ).execute()

        if not result or not result.data:
            return "", []

        parts = []
        used_ids = []

        for row in result.data:
            snippet = f"[{row['category'].upper()}] {row['title']}\n{row['content']}"
            parts.append(snippet)
            used_ids.append(str(row["id"]))

        context_str = "\n\n---\n\n".join(parts)
        return context_str, used_ids

    except Exception as e:
        print(f"RAG retrieval error: {e}")
        return "", []
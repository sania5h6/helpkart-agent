"""
scripts/seed_db.py — Embed and store knowledge base articles in Supabase.

Run ONCE after creating the schema:
    python -m scripts.seed_db

This script:
  1. Reads all rows from knowledge_base where embedding IS NULL
  2. Batch-embeds their content via OpenAI
  3. Updates each row with its embedding vector
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from backend.database.client import get_supabase
from backend.rag.embeddings import embed_batch


async def seed():
    db = get_supabase()

    # Fetch unembedded rows
    result = (
        db.table("knowledge_base")
        .select("id, content")
        .is_("embedding", "null")
        .execute()
    )
    rows = result.data or []

    if not rows:
        print("✓ All knowledge base rows already have embeddings.")
        return

    print(f"Embedding {len(rows)} knowledge base articles...")
    texts = [r["content"] for r in rows]
    embeddings = await embed_batch(texts)

    for row, embedding in zip(rows, embeddings):
        db.table("knowledge_base").update({"embedding": embedding}).eq(
            "id", row["id"]
        ).execute()
        print(f"  ✓ Embedded: {row['id']}")

    print(f"\n✅ Done. {len(rows)} articles embedded and stored.")


if __name__ == "__main__":
    asyncio.run(seed())
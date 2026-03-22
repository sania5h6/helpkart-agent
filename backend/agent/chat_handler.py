"""
agent/chat_handler.py — Streaming chat using Groq.
"""
from __future__ import annotations
import asyncio
import time
from uuid import UUID
from collections.abc import AsyncIterator
from groq import AsyncGroq
from backend.config import settings
from backend.database.client import get_supabase
from backend.database.models import Customer, Order, Conversation
from backend.rag.retriever import retrieve_context
from backend.agent.context_manager import (
    get_or_create_conversation,
    save_message,
    build_message_list,
)

_groq = AsyncGroq(api_key=settings.groq_api_key)


async def _fetch_customer(customer_id: str | None) -> Customer | None:
    if not customer_id:
        return None
    db = get_supabase()
    result = (
        db.table("customers")
        .select("*")
        .eq("id", customer_id)
        .maybe_single()
        .execute()
    )
    return Customer(**result.data) if result.data else None


async def _fetch_orders(customer_id: str | None) -> list[Order]:
    if not customer_id:
        return []
    db = get_supabase()
    result = (
        db.table("orders")
        .select("*")
        .eq("customer_id", customer_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    return [Order(**row) for row in (result.data or [])]


async def stream_response(
    session_token: str,
    user_message: str,
    customer_id: str | None = None,
) -> AsyncIterator[str]:
    t_start = time.monotonic()

    conversation: Conversation = await get_or_create_conversation(
        session_token, customer_id
    )

    # Parallel fetch: RAG + customer + orders at the same time
    (rag_context, chunk_ids), customer, orders = await asyncio.gather(
        retrieve_context(user_message),
        _fetch_customer(customer_id),
        _fetch_orders(customer_id),
    )

    t_retrieval_done = time.monotonic()

    system_prompt, messages = await build_message_list(
        conversation, rag_context, customer, orders, user_message
    )

    full_response = ""
    try:
        stream = await _groq.chat.completions.create(
            model=settings.llm_model,
            max_tokens=settings.max_tokens,
            messages=[{"role": "system", "content": system_prompt}] + messages,
            stream=True,
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                full_response += token
                yield f"data: {token}\n\n"

    except Exception as exc:
        yield f"event: error\ndata: {str(exc)}\n\n"
        return

    t_stream_done = time.monotonic()

    latency_meta = {
        "retrieval_ms": round((t_retrieval_done - t_start) * 1000),
        "total_ms": round((t_stream_done - t_start) * 1000),
        "rag_chunks": chunk_ids,
    }
    asyncio.create_task(
        _persist_turn(conversation.id, user_message, full_response, latency_meta)
    )

    yield "event: done\ndata: [DONE]\n\n"


async def _persist_turn(
    conversation_id: UUID,
    user_message: str,
    assistant_response: str,
    metadata: dict,
) -> None:
    await asyncio.gather(
        save_message(conversation_id, "user", user_message),
        save_message(conversation_id, "assistant", assistant_response, metadata),
    )
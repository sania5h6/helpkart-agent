from __future__ import annotations
import asyncio
from uuid import UUID
from groq import AsyncGroq
from backend.config import settings
from backend.database.client import get_supabase
from backend.database.models import Conversation, Message, Customer, Order

_groq = AsyncGroq(api_key=settings.groq_api_key)

RECENT_TURNS_AFTER_SUMMARY = 6


async def get_or_create_conversation(
    session_token: str, customer_id: str | None = None
) -> Conversation:
    db = get_supabase()
    result = (
        db.table("conversations")
        .select("*")
        .eq("session_token", session_token)
        .maybe_single()
        .execute()
    )
    if result and result.data:
        return Conversation(**result.data)

    payload: dict = {"session_token": session_token}
    if customer_id:
        payload["customer_id"] = customer_id

    new = db.table("conversations").insert(payload).execute()
    return Conversation(**new.data[0])


async def fetch_recent_messages(conversation_id: UUID, limit: int = 20) -> list[Message]:
    db = get_supabase()
    result = (
        db.table("messages")
        .select("*")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    if not result or not result.data:
        return []
    messages = [Message(**row) for row in result.data]
    return list(reversed(messages))


async def save_message(
    conversation_id: UUID, role: str, content: str, metadata: dict | None = None
) -> None:
    db = get_supabase()
    db.table("messages").insert({
        "conversation_id": str(conversation_id),
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }).execute()


async def maybe_summarise(conversation: Conversation) -> str | None:
    if conversation.turn_count < settings.summarize_after_turns:
        return conversation.summary
    return conversation.summary


async def build_message_list(
    conversation: Conversation,
    rag_context: str,
    customer: Customer | None,
    orders: list[Order],
    new_user_message: str,
):
    customer_info = ""
    if customer:
        customer_info = f"\nYou are speaking with: {customer.name} (Email: {customer.email}, Tier: {customer.tier.upper()})"
        if orders:
            order_lines = "\n".join(
                f"  - Order ID: {o.id} | Status: {o.status} | Items: {o.items} | Total: Rs.{o.total_amount}"
                + (f" | Tracking: {o.tracking_number}" if o.tracking_number else " | Tracking: Not assigned yet")
                for o in orders
            )
            customer_info += f"\nTheir orders:\n{order_lines}"
        else:
            customer_info += "\nThey have no orders yet."

    rag_section = f"\n\nRELEVANT KNOWLEDGE BASE:\n{rag_context}" if rag_context else ""

    system_prompt = f"""You are Kira, a warm and efficient customer support agent for HelpKart — a popular Indian e-commerce platform.

Your personality:
- Friendly and empathetic, like a real call-center agent
- Concise — no long paragraphs, get to the point fast
- Proactive — anticipate follow-up questions
- Honest — never make up order details, tracking numbers, or policies not in your knowledge base

How to handle queries:
- For order questions: always reference the actual order data provided below
- For policy questions: use the knowledge base provided below
- For unknown questions: say "I don't have that information right now, but I can escalate this for you"
- Always end with a helpful follow-up question or offer
{customer_info}{rag_section}"""

    messages: list[dict] = []

    summary = await maybe_summarise(conversation)
    recent = await fetch_recent_messages(
        conversation.id,
        limit=settings.max_conversation_turns,
    )

    if summary and len(recent) > RECENT_TURNS_AFTER_SUMMARY:
        messages.append({"role": "user", "content": "[Previous conversation summary]"})
        messages.append({"role": "assistant", "content": summary})
        recent = recent[-RECENT_TURNS_AFTER_SUMMARY:]

    for msg in recent:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": new_user_message})

    return system_prompt, messages
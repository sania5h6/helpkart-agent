"""
database/models.py — Pydantic models mirroring Supabase tables.
Used for type-safe deserialization of DB rows throughout the app.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel


class Customer(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None = None
    tier: str = "standard"
    created_at: datetime | None = None


class Order(BaseModel):
    id: UUID
    customer_id: UUID
    status: str
    items: list[dict[str, Any]]
    total_amount: float
    tracking_number: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KnowledgeChunk(BaseModel):
    id: UUID
    title: str
    content: str
    category: str
    similarity: float | None = None   # populated after vector search


class Conversation(BaseModel):
    id: UUID
    customer_id: UUID | None = None
    session_token: str
    summary: str | None = None
    turn_count: int = 0
    created_at: datetime | None = None
    last_active_at: datetime | None = None


class Message(BaseModel):
    id: UUID | None = None
    conversation_id: UUID
    role: str           # 'user' | 'assistant' | 'system'
    content: str
    metadata: dict[str, Any] = {}
    created_at: datetime | None = None
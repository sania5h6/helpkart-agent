from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.agent.chat_handler import stream_response

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    session_token: str
    message: str
    customer_id: str | None = None


class LoginRequest(BaseModel):
    email: str


@router.post("/login")
async def login(body: LoginRequest):
    """Look up customer by email and return their ID + name."""
    from backend.database.client import get_supabase
    db = get_supabase()
    try:
        result = (
            db.table("customers")
            .select("id, name, email, tier")
            .eq("email", body.email.lower().strip())
            .maybe_single()
            .execute()
        )
        if not result or not result.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, request: Request):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    async def event_generator():
        try:
            async for chunk in stream_response(
                session_token=body.session_token,
                user_message=body.message,
                customer_id=body.customer_id,
            ):
                if await request.is_disconnected():
                    break
                yield chunk
        except Exception as exc:
            yield f"event: error\ndata: {str(exc)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "HelpKart AI Agent"}


@router.get("/conversations/{session_token}/history")
async def get_history(session_token: str):
    from backend.database.client import get_supabase
    db = get_supabase()
    try:
        conv = (
            db.table("conversations")
            .select("id")
            .eq("session_token", session_token)
            .maybe_single()
            .execute()
        )
        if not conv or not conv.data:
            return {"messages": []}
        msgs = (
            db.table("messages")
            .select("role, content, created_at")
            .eq("conversation_id", conv.data["id"])
            .order("created_at")
            .execute()
        )
        return {"messages": msgs.data or []}
    except Exception:
        return {"messages": []}
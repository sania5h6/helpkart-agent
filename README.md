# HelpKart AI Voice Support Agent

> Low-latency, streaming AI customer support agent with RAG — built for real-time, phone-like conversations.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![Groq](https://img.shields.io/badge/LLM-Groq%20Llama3.3--70B-orange) ![Supabase](https://img.shields.io/badge/DB-Supabase%20pgvector-darkgreen) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What This Does

HelpKart is a fully functional AI customer support agent for a fictional e-commerce company. It holds fast, continuous, back-and-forth conversations — similar to a live phone call — while grounding every response in real customer data and a knowledge base.

**Live demo:** `http://localhost:8000` (run locally — see setup below)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (SSE Client)                  │
│   POST /api/chat/stream  ──►  EventSource token stream   │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   FastAPI Backend                        │
│                                                         │
│   asyncio.gather() ─────────────────────────────────┐  │
│     ├─ embed(query)        → sentence-transformers   │  │
│     ├─ fetch_customer()    → Supabase                │  │
│     └─ fetch_orders()      → Supabase                │  │
│                       ◄────────────────────────────--┘  │
│   retrieve_context()  → Supabase pgvector RPC           │
│   build_message_list() → context_manager.py             │
│   stream_response()   → Groq Llama 3.3 70B (streaming)  │
│   _persist_turn()     → Supabase messages (background)  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              Supabase (PostgreSQL + pgvector)            │
│   customers │ orders │ knowledge_base (vectors)         │
│   conversations │ messages                              │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| LLM | Groq — Llama 3.3 70B | Fastest inference available; LPU chips vs GPU |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Free, runs locally, no API dependency |
| Database | Supabase (PostgreSQL) | Managed Postgres + pgvector built-in |
| Vector Search | pgvector IVFFlat | Sub-10ms ANN search at scale |
| Backend | FastAPI + uvicorn | Async-native, ASGI, production-ready |
| Streaming | Server-Sent Events (SSE) | HTTP-native, no WS upgrade overhead |
| Frontend | Vanilla HTML/JS | Zero dependencies, instant load |

---

## Key Engineering Decisions

### 1. Parallel I/O — The Biggest Latency Win

Before any LLM call, three things must happen: embed the query, fetch the customer, fetch their orders. Doing these sequentially would cost ~110ms. Running them in parallel with `asyncio.gather()` cuts this to ~80ms — dominated only by the slowest call.

```python
(rag_context, chunk_ids), customer, orders = await asyncio.gather(
    retrieve_context(user_message),   # ~80ms (embedding + vector search)
    _fetch_customer(customer_id),     # ~15ms
    _fetch_orders(customer_id),       # ~15ms
)
```

### 2. SSE over WebSockets

SSE was chosen deliberately over WebSockets because:
- No TCP upgrade handshake — starts streaming immediately
- HTTP/2 multiplexes many SSE streams on one connection
- Browser `EventSource` handles reconnects automatically
- Chat is asymmetric — user sends once, server streams back — true bidirectionality isn't needed

### 3. Fire-and-Forget Persistence

DB writes run as `asyncio.create_task()` — they never hold the HTTP response open. The SSE stream closes the moment Groq finishes generating. Message persistence completes independently in the background, keeping perceived latency minimal.

### 4. Sliding Window + Summarisation

Context window size stays constant regardless of session length:
- Keep last 20 turns verbatim
- After 15 turns: Claude summarises older history into 3–5 bullets, stored in DB
- Long sessions: `[summary] + [last 6 turns] + [current]` — bounded size, no latency growth

### 5. RAG with Token Budget

Retrieved knowledge chunks are injected into the system prompt only up to a `max_context_tokens` cap. This keeps prompts small, reducing time-to-first-token and cost. Similarity threshold (0.3) acts as an adaptive gate — vague queries return nothing rather than noisy context.

---

## Database Schema

```
customers          — id, name, email, phone, tier
orders             — id, customer_id, status, items (JSONB), total, tracking_number
knowledge_base     — id, title, content, category, embedding (vector 384)
conversations      — id, customer_id, session_token, summary, turn_count
messages           — id, conversation_id, role, content, metadata (JSONB)
```

**Indexing strategy:**

| Index | Type | Purpose |
|---|---|---|
| `customers.email` | B-tree | Fast login lookup |
| `orders.customer_id` | B-tree | Per-customer order fetch |
| `messages(conv_id, created_at)` | Covering | Sorted history, no extra sort step |
| `conversations.session_token` | B-tree | Session resume on reconnect |
| `knowledge_base.embedding` | IVFFlat | ~10ms approximate vector search |

---

## RAG Pipeline

```
User message
    │
    ▼
embed_text(query)              ← runs locally, no API call
    │
    ▼
Supabase RPC: match_knowledge()
    ├─ cosine similarity vs all vectors (IVFFlat index)
    ├─ filter: similarity > 0.3
    └─ return top 3 chunks
    │
    ▼
Token budget check             ← stop adding chunks at max_context_tokens
    │
    ▼
Inject into system prompt as "RELEVANT KNOWLEDGE BASE:" section
```

**Hallucination prevention:** System prompt explicitly instructs the agent to say "I don't have that information" when no relevant context is found, rather than generating plausible-sounding but incorrect answers.

---

## Latency Profile

| Operation | Time |
|---|---|
| Query embedding (local) | ~5ms |
| pgvector search | ~10ms |
| Customer + orders DB fetch | ~15ms |
| Parallel gather total | ~20ms |
| Groq time-to-first-token | ~150ms |
| **End-to-end first token** | **~170ms** |
| DB persistence (background) | ~30ms (non-blocking) |

---

## Project Structure

```
helpkart-agent/
├── backend/
│   ├── main.py                   # FastAPI app, CORS, static serving
│   ├── config.py                 # Pydantic settings from .env
│   ├── database/
│   │   ├── client.py             # Supabase singleton
│   │   └── models.py             # Pydantic row models
│   ├── rag/
│   │   ├── embeddings.py         # Local sentence-transformers wrapper
│   │   └── retriever.py          # pgvector similarity search
│   ├── agent/
│   │   ├── context_manager.py    # Session state, history, summarisation
│   │   └── chat_handler.py       # Orchestration, parallel I/O, streaming
│   └── api/
│       └── routes.py             # SSE endpoint, login, history
├── frontend/
│   └── index.html                # Single-file chat UI with login
├── scripts/
│   └── seed_db.py                # One-time knowledge base embedding
├── supabase/
│   └── schema.sql                # Full schema + seed data + RPC function
├── .env.example
├── requirements.txt
└── README.md
```

---

## Setup & Running

### Prerequisites
- Python 3.10+
- Supabase project (free tier works)
- Groq API key (free at console.groq.com)

### 1. Clone & install
```bash
git clone https://github.com/sania5h6/helpkart-agent
cd helpkart-agent
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in GROQ_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
```

### 3. Set up Supabase
- Enable `pgvector` extension in Supabase Dashboard → Database → Extensions
- Run `supabase/schema.sql` in the SQL Editor
- Run the `match_knowledge` RPC function (included in schema.sql comments)

### 4. Seed knowledge base
```bash
python -m scripts.seed_db
```

### 5. Start server
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`

### Test accounts (already seeded)
| Email | Customer | Orders |
|---|---|---|
| priya@example.com | Priya Sharma | Shipped — Wireless Headphones |
| ravi@example.com | Ravi Kumar | Delivered — USB-C Hub |
| ananya@example.com | Ananya Mehta | Pending — Mechanical Keyboard |

---

## Sample Conversations

### Order tracking (logged in as Priya)
```
User:   where is my order?
Kira:   Hi Priya! Your order with Wireless Headphones and a Phone Case
        (₹2,897) is currently shipped with tracking number HK-TRK-20240001.
        It should arrive within 1–2 business days. Is there anything else
        I can help you with?

User:   i want to return the headphones
Kira:   No problem! HelpKart accepts returns within 30 days of delivery.
        Since your order is still in transit, I'd recommend waiting for
        delivery first. Once it arrives, just contact support with order
        ID and we'll kick off the return. Refund hits your original
        payment in 5–7 business days. Anything else?
```

### Policy questions (no login needed)
```
User:   do you accept UPI?
Kira:   Yes! HelpKart accepts UPI, credit/debit cards (Visa, Mastercard,
        Rupay), net banking, and Cash on Delivery for orders under ₹5,000.

User:   what about EMI?
Kira:   EMI is available on cards for orders above ₹3,000. You can select
        it at checkout. Want help with anything else?
```

---

## Trade-offs & Assumptions

| Decision | Trade-off |
|---|---|
| Groq (Llama 3.3 70B) over GPT-4 | Free, faster; slightly less instruction-following on edge cases |
| Local embeddings over OpenAI | Zero cost, zero latency for embedding; 384-dim vs 1536-dim (lower recall on ambiguous queries) |
| SSE over WebSockets | Simpler, HTTP-native; loses true bidirectionality (acceptable for chat) |
| Fire-and-forget persistence | Messages lost on server crash; acceptable for a support log use case |
| Sliding window context | Very old messages compressed/lost; intentional to keep latency flat |
| Service role key | Bypasses RLS; must stay server-side only |

-- ============================================================
-- HelpKart AI Support Agent — Supabase Schema
-- ============================================================
-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- CUSTOMERS
-- ============================================================
CREATE TABLE customers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    phone       TEXT,
    tier        TEXT DEFAULT 'standard' CHECK (tier IN ('standard', 'premium', 'vip')),
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Index for fast email lookup (used during session auth)
CREATE INDEX idx_customers_email ON customers(email);

-- ============================================================
-- ORDERS
-- ============================================================
CREATE TABLE orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','confirmed','shipped','delivered','cancelled','refunded')),
    items           JSONB NOT NULL DEFAULT '[]',   -- [{product_id, name, qty, price}]
    total_amount    NUMERIC(10, 2) NOT NULL,
    tracking_number TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Index for fast customer order lookups
CREATE INDEX idx_orders_customer_id  ON orders(customer_id);
CREATE INDEX idx_orders_status       ON orders(status);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- KNOWLEDGE BASE  (RAG source)
-- ============================================================
CREATE TABLE knowledge_base (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    category    TEXT NOT NULL,   -- e.g. 'returns', 'shipping', 'payments'
    embedding   vector(384),    -- OpenAI text-embedding-3-small dimension
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- IVFFlat index for fast ANN search (tune lists= based on row count)
CREATE INDEX idx_kb_embedding ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- B-tree index for category filter pre-pass
CREATE INDEX idx_kb_category ON knowledge_base(category);

-- ============================================================
-- CONVERSATIONS  (session container)
-- ============================================================
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    session_token   TEXT UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    summary         TEXT,        -- compressed context for long sessions
    turn_count      INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),
    last_active_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_conversations_session_token ON conversations(session_token);
CREATE INDEX idx_conversations_customer_id   ON conversations(customer_id);

-- ============================================================
-- MESSAGES  (individual turns)
-- ============================================================
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',  -- e.g. retrieved chunk ids, latency_ms
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Covering index: all messages for a session, ordered by time
CREATE INDEX idx_messages_conv_created ON messages(conversation_id, created_at ASC);

-- ============================================================
-- SEED: Knowledge Base Articles
-- ============================================================
INSERT INTO knowledge_base (title, content, category) VALUES
(
  'Return & Refund Policy',
  'HelpKart accepts returns within 30 days of delivery for most items. To initiate a return, customers must contact support with their order ID. Items must be unused and in original packaging. Refunds are processed within 5–7 business days to the original payment method. Digital products and perishables are non-returnable.',
  'returns'
),
(
  'Shipping & Delivery',
  'Standard shipping takes 3–5 business days. Express shipping (1–2 days) is available for an additional fee. Orders above ₹999 qualify for free standard shipping. Customers receive a tracking number by email once the order ships. International shipping is not currently supported.',
  'shipping'
),
(
  'Payment Methods',
  'HelpKart accepts UPI, credit/debit cards (Visa, Mastercard, Rupay), net banking, and Cash on Delivery (COD) for orders below ₹5000. EMI options are available on cards for orders above ₹3000. All transactions are secured with 256-bit SSL encryption.',
  'payments'
),
(
  'Order Cancellation',
  'Orders can be cancelled within 2 hours of placement at no charge. After 2 hours, cancellation may not be possible if the order is already dispatched. To cancel, use the Orders section in your account or contact support. Cancelled order refunds are processed within 3–5 business days.',
  'cancellation'
),
(
  'Account & Login Issues',
  'If you cannot log in, use the "Forgot Password" link on the login page. OTP-based login is also available via registered mobile number. If your account is locked after 5 failed attempts, wait 30 minutes or contact support. For account deletion requests, email privacy@helpkart.in.',
  'account'
),
(
  'Product Warranty',
  'Electronics purchased on HelpKart carry a minimum 1-year manufacturer warranty. Extended warranty plans (1–3 years) are available at checkout. To claim warranty, contact the manufacturer directly or use the HelpKart Warranty Portal with your order ID and purchase date.',
  'warranty'
),
(
  'Discount Codes & Offers',
  'Discount codes can be applied at checkout in the "Promo Code" field. Only one code can be applied per order. Codes are case-insensitive and cannot be combined with ongoing sale prices unless stated otherwise. Expired or already-used codes cannot be reapplied.',
  'offers'
);

-- ============================================================
-- SEED: Sample Customers & Orders
-- ============================================================
INSERT INTO customers (id, name, email, phone, tier) VALUES
  ('a1b2c3d4-0000-0000-0000-000000000001', 'Priya Sharma',  'priya@example.com',  '9876543210', 'premium'),
  ('a1b2c3d4-0000-0000-0000-000000000002', 'Ravi Kumar',    'ravi@example.com',   '9123456789', 'standard'),
  ('a1b2c3d4-0000-0000-0000-000000000003', 'Ananya Mehta',  'ananya@example.com', '9988776655', 'vip');

INSERT INTO orders (customer_id, status, items, total_amount, tracking_number) VALUES
(
  'a1b2c3d4-0000-0000-0000-000000000001',
  'shipped',
  '[{"name":"Wireless Headphones","qty":1,"price":2499},{"name":"Phone Case","qty":2,"price":199}]',
  2897.00,
  'HK-TRK-20240001'
),
(
  'a1b2c3d4-0000-0000-0000-000000000002',
  'delivered',
  '[{"name":"USB-C Hub","qty":1,"price":1299}]',
  1299.00,
  'HK-TRK-20240002'
),
(
  'a1b2c3d4-0000-0000-0000-000000000003',
  'pending',
  '[{"name":"Mechanical Keyboard","qty":1,"price":4599}]',
  4599.00,
  NULL
);
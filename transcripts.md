# Sample Conversation Transcripts — HelpKart AI Support Agent

These transcripts demonstrate the agent's ability to handle rapid, continuous
back-and-forth interactions grounded in real customer data and a knowledge base.

---

## Transcript 1: Order Tracking + Return Request
**Customer:** Priya Sharma (priya@example.com) | Tier: Premium
**Session:** Real-time streaming, ~170ms first token latency

```
User:    hi
Kira:    Hi Priya! 👋 Welcome back. How can I help you today?

User:    where is my order
Kira:    Your most recent order — Wireless Headphones + Phone Case (₹2,897) —
         is currently shipped with tracking number HK-TRK-20240001.
         Expected delivery is within 1–2 business days. Is there anything
         else I can help you with?

User:    i dont want it anymore
Kira:    Got it! Since your order is still in transit, I can't cancel it at
         this stage. But once it's delivered, you can return it within 30 days.
         Just contact support with your order ID and we'll sort it out —
         refund goes back to your original payment in 5–7 business days.
         Want me to make a note of this for you?

User:    yes please also what items were in the order exactly
Kira:    Sure, noted! Your order contains:
         • Wireless Headphones (x1) — ₹2,499
         • Phone Case (x2) — ₹199 each
         Total: ₹2,897

         Once delivered, just reach out and we'll initiate the return for
         both or either item — your choice. Anything else?

User:    no thanks
Kira:    No problem, Priya! Have a great day. Feel free to reach out anytime. 😊
```

---

## Transcript 2: Rapid-Fire Policy Questions
**Customer:** Guest (not logged in)
**Session:** Multiple fast messages — demonstrates real-time continuity

```
User:    do you accept upi
Kira:    Yes! HelpKart accepts UPI, credit/debit cards (Visa, Mastercard,
         Rupay), net banking, and Cash on Delivery for orders under ₹5,000.

User:    what about emi
Kira:    EMI is available on credit cards for orders above ₹3,000. You can
         select it at checkout. Plans range from 3 to 12 months depending
         on your bank.

User:    is cod available for 6000 rupee order
Kira:    Unfortunately no — Cash on Delivery is only available for orders
         below ₹5,000. For a ₹6,000 order you'd need to pay via UPI,
         card, or net banking. Would any of those work for you?

User:    ok what about returns
Kira:    HelpKart accepts returns within 30 days of delivery. Items must be
         unused and in original packaging. Refunds are processed in 5–7
         business days to your original payment method. Digital products
         and perishables are non-returnable.

User:    how do i start a return
Kira:    Just contact our support team with your order ID and reason for
         return — we'll guide you through the rest. You can also go to
         My Orders in your account and click "Return" directly. Need
         help with anything else?
```

---

## Transcript 3: Pending Order + Cancellation
**Customer:** Ananya Mehta (ananya@example.com) | Tier: VIP
**Session:** Demonstrates order-aware responses using real DB data

```
User:    hey kira whats the status of my order
Kira:    Hi Ananya! Your order — Mechanical Keyboard (₹4,599) — is currently
         pending. A tracking number hasn't been assigned yet, which means
         it's still being processed at our end. This usually takes 12–24
         hours. Is there anything specific you'd like to know?

User:    why is it still pending its been a day
Kira:    I understand that's frustrating! Pending status usually means the
         order is being verified or prepared for dispatch. Since you're a
         VIP member, I'm flagging this as a priority. I'd recommend
         reaching out to support@helpkart.in with your order ID for a
         faster update. Want me to help with anything else in the meantime?

User:    can i cancel it
Kira:    Since your order is still in pending status and hasn't been
         dispatched yet, cancellation should be possible! Orders can be
         cancelled within 2 hours of placement for free, but since it's
         been longer, please contact support immediately at
         support@helpkart.in to request cancellation before it ships.
         Refund would be processed in 3–5 business days. Shall I help
         with anything else?

User:    what payment method did i use i forgot
Kira:    I don't have payment method details stored for security reasons,
         but your refund will automatically go back to whichever method
         you used at checkout. You can also check your confirmation email
         for payment details. Anything else I can help with?
```

---

## Transcript 4: Warranty + Promo Code
**Customer:** Ravi Kumar (ravi@example.com) | Tier: Standard
**Session:** Demonstrates knowledge base retrieval across topic switches

```
User:    hi does my usb hub have warranty
Kira:    Hi Ravi! Yes — electronics purchased on HelpKart carry a minimum
         1-year manufacturer warranty. Your USB-C Hub (delivered, ₹1,299)
         should be covered. To claim warranty, you can contact the
         manufacturer directly or use the HelpKart Warranty Portal with
         your order ID. Need help with a warranty claim?

User:    not yet just checking. also i have a promo code SAVE20
Kira:    Great! You can apply SAVE20 at checkout in the "Promo Code" field.
         Just note — only one code can be used per order, and codes can't
         be combined with ongoing sale prices unless the offer says so.
         Promo codes are also case-insensitive, so no worries there!

User:    what if it doesnt work
Kira:    If the code isn't applying, it could be because:
         • The item is already on sale
         • The code has expired or been used before
         • The order doesn't meet the minimum value for the code

         If none of those apply, contact support with the code and they'll
         check it manually for you. Anything else?

User:    nope all good thanks
Kira:    Happy to help, Ravi! Come back anytime. 😊
```

---

## Notes on Agent Behaviour

- **Latency:** First token streams within ~170ms of sending a message
- **Grounding:** All order details (status, items, tracking) come from live Supabase data — the agent never guesses
- **RAG:** Policy answers (returns, payments, warranty) are retrieved from the knowledge base via pgvector similarity search, not hardcoded
- **Continuity:** The agent remembers context across all turns in a session — no need to repeat yourself
- **Honesty:** When information isn't available (e.g. payment method), the agent says so instead of hallucinating
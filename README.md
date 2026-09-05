🛍️ GlowCart — AI-Powered Agentic Commerce

From “What should I buy?” to “Payment completed” — through one intelligent, trustworthy commerce agent.

GlowCart is an AI-powered conversational commerce platform that lets users discover, compare, evaluate, purchase, and pay for products using natural language.

Unlike a typical shopping chatbot that only recommends products, GlowCart can orchestrate the complete commerce journey while keeping financially sensitive operations under deterministic backend control.

🚀 Why GlowCart?

Traditional online shopping makes users jump between search, product pages, reviews, comparisons, cart, checkout, and payment.

GlowCart turns that journey into a conversation:

Natural-language intent
        ↓
AI intent understanding
        ↓
Catalog search
        ↓
Product comparison & review evidence
        ↓
Deterministic recommendation
        ↓
Cart
        ↓
Checkout snapshot
        ↓
Explicit user confirmation
        ↓
Razorpay payment
        ↓
Success / bounded failure recovery
        ↓
Server-side payment verification
        ↓
Audit trail

The core principle

AI handles ambiguity. Deterministic systems handle correctness.

The AI decides what the user means and helps them make a decision.
The backend remains responsible for prices, inventory, cart state, orders, payment verification, retry limits, and auditability.

✨ Key Features

🤖 Conversational Shopping

Users can interact naturally instead of navigating through rigid filters.

Examples:

"I need a mascara under ₹2500 with good reviews."

"Compare all of them."

"Add the recommended one to my cart."

"Buy it."

GlowCart maintains conversational context so follow-up commands work naturally.

🔎 AI-Powered Product Discovery

GlowCart understands shopping intent such as:

Product category

Budget constraints

Descriptive preferences

Follow-up references

Comparison requests

Previous recommendations

The catalog layer then applies deterministic filtering so an AI interpretation cannot accidentally return unrelated products.

📊 Explainable Recommendations

Recommendations are not based only on star ratings.

GlowCart combines signals including:

Bayesian rating adjustment

Price fit

Review volume

Review evidence

Product availability

The system can explain why a product was recommended and surface alternatives such as:

🏆 Recommended

💰 Best Value

⭐ Highest Rated

🪙 Budget Pick

This makes the recommendation more transparent than a black-box ranking.

🛒 Context-Aware Cart & Checkout

The checkout flow creates an order snapshot from the current cart.

Before payment, the user gets an explicit confirmation step rather than allowing the AI to silently trigger a financial transaction.

CART
  ↓
PENDING_CONFIRMATION
  ↓
PAYMENT_PENDING
  ↓
PAID

This separation is intentional: conversational convenience should never remove user control over a monetary action.

💳 Razorpay Payment Integration

GlowCart integrates Razorpay for payment processing.

The payment flow includes:

Create a server-side order

Open Razorpay Checkout

Receive payment result

Verify the Razorpay signature on the backend

Verify the Razorpay order ID against the active GlowCart order

Verify the order is in the expected payment state

Mark the GlowCart order as paid only after successful verification

The browser callback is not treated as proof of payment.

🔄 Bounded Payment Failure Recovery

Payment failure is a first-class state, not a dead end.

If a payment fails:

PAYMENT_PENDING
      ↓
PAYMENT_FAILED
      ↓
PAYMENT_RECOVERY
      ↓
Retry Payment
      ↓
Fresh Razorpay Order
      ↓
PAYMENT_PENDING

GlowCart provides:

Bounded payment attempts

Fresh Razorpay order creation for retries

Payment-link fallback

Recovery without restarting the shopping journey

Audit events for recovery actions

The retry mechanism is intentionally bounded to prevent uncontrolled payment attempts.

🧾 Full Audit Trail

Important commerce and payment actions are recorded in an activity timeline.

Examples include:

Product searches

Recommendations

Cart actions

Checkout creation

Checkout confirmation

Payment attempts

Payment failures

Payment recovery

Retry attempts

Payment verification

Successful orders

This makes the agent's actions observable and easier to debug or review.

🧠 Architecture

┌──────────────────────────────────────────────┐
│                 GlowCart UI                  │
│ React • Shop • Compare • Cart • Checkout     │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                FastAPI Backend                │
│                                              │
│  Chat / Orchestrator                         │
│        │                                     │
│        ├── Intent Understanding               │
│        ├── Session Context                   │
│        ├── Catalog Search                    │
│        ├── Recommendations                   │
│        ├── Cart & Orders                     │
│        ├── Checkout                          │
│        └── Payment Recovery                  │
└──────────────────────┬───────────────────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      ┌─────────────┐     ┌──────────────┐
      │ PostgreSQL  │     │   Razorpay   │
      │ Products    │     │   Checkout   │
      │ Reviews     │     │   Payments   │
      │ Cart/Orders │     │   Test Mode  │
      │ Audit       │     └──────────────┘
      └─────────────┘
             ▲
             │
      ┌──────┴───────┐
      │   Gemini /   │
      │    LLM       │
      └──────────────┘

Responsibility Boundary

Layer

Responsibility

AI / LLM

Intent understanding, conversational context, explanations

Catalog service

Product search and category constraints

Recommendation service

Deterministic ranking and evidence

Cart service

Cart mutations and totals

Order service

Order lifecycle and state transitions

Razorpay service

Payment order creation and payment integration

Payment verification

Server-side signature/order/state validation

Audit service

Traceability of important actions

PostgreSQL

Persistent commerce state

🛡️ Trust & Safety for Agentic Commerce

GlowCart is designed around a simple rule:

The AI can recommend an action, but it should not be the authority that determines whether a financial action is valid.

Payment safeguards

Explicit user confirmation before payment

Server-side Razorpay signature verification

Razorpay order ID matching

Order-state validation

Bounded payment attempts

Fresh Razorpay order for retries

Payment-link fallback

Persistent audit trail

This prevents common failure modes such as:

Marking an order paid from a browser-only callback

Retrying an obsolete payment order indefinitely

Allowing payment for a stale order

Losing the user's commerce context after a failed payment

🗂️ Project Structure

backend/
├── agent/
│   ├── gemini_client.py
│   ├── intent.py
│   └── orchestrator.py
│
├── routers/
│   ├── audit.py
│   ├── cart.py
│   ├── chat.py
│   ├── checkout.py
│   └── payment.py
│
├── services/
│   ├── audit_service.py
│   ├── cart_service.py
│   ├── catalog_service.py
│   ├── order_service.py
│   ├── razorpay_service.py
│   ├── recommend_service.py
│   ├── review_service.py
│   ├── serializers.py
│   └── session_service.py
│
├── config.py
├── database.py
├── deps.py
├── main.py
├── models.py
└── schemas.py

frontend/
├── src/
│   ├── components/
│   ├── contexts/
│   ├── pages/
│   │   ├── ActivityPage.jsx
│   │   ├── CartPage.jsx
│   │   ├── CheckoutPage.jsx
│   │   ├── ComparePage.jsx
│   │   ├── OrderPage.jsx
│   │   ├── ProductPage.jsx
│   │   └── ShopPage.jsx
│   ├── router/
│   ├── utils/
│   ├── App.jsx
│   └── index.css
└── package.json

📦 Dataset

GlowCart uses a curated catalog derived from the UCSD/McAuley Amazon Reviews 2018 — All Beauty dataset.

Current application catalog:

312 products

11 product categories

16,679 reviews

Supported categories include:

Lipstick
Blush
Skincare
Foundation
Mascara
Concealer
Eyeshadow
Eyeliner
Lip Gloss
Bronzer
Primer

⚙️ Tech Stack

Frontend

React

Vite

JavaScript

Custom client-side routing

Razorpay Checkout

Backend

Python

FastAPI

SQLAlchemy

PostgreSQL

AI

Gemini API

Intent parsing

Conversational context

Recommendation explanations

Payments

Razorpay Test Mode

Server-side order creation

Signature verification

Payment recovery

🧪 Running Locally

1. Clone the repository

git clone <your-repository-url>
cd ai-agentic-commerce

2. Backend setup

Create and activate the Python virtual environment:

cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1

Install dependencies:

pip install -r requirements.txt

Create backend/.env:

DATABASE_URL=your_postgresql_connection_string
LLM_API_KEY=your_llm_api_key
RAZORPAY_KEY_ID=your_razorpay_test_key_id
RAZORPAY_KEY_SECRET=your_razorpay_test_key_secret

Start the backend:

uvicorn main:app --reload

3. Frontend setup

Open another terminal:

cd frontend
npm install
npm run dev

Then open the local URL shown by Vite.

Never commit .env, API keys, Razorpay secrets, virtual environments, or node_modules to GitHub.

💰 Testing Payment Recovery

GlowCart's payment recovery flow is designed to be demonstrated using Razorpay Test Mode.

A useful demo scenario is:

1. Search for a product
2. Compare recommendations
3. Add the recommended product to cart
4. Start checkout
5. Explicitly confirm the purchase
6. Open Razorpay Checkout
7. Simulate a payment failure
8. Return to GlowCart recovery
9. Choose Retry Payment
10. Observe a fresh payment attempt
11. Complete the payment
12. Open Activity
13. Show the complete audit trail

This demonstrates that a failed payment does not destroy the transaction context.

🧩 Example Agent Conversation

User:
I need a mascara under ₹2500 with good reviews.

GlowCart:
Finds relevant mascara products and ranks them using
price, ratings, review evidence, review volume and availability.

User:
Compare all of them.

GlowCart:
Provides a structured comparison and identifies the
recommended option, best value and highest-rated option.

User:
Add the recommended one to my cart.

GlowCart:
Adds the selected product.

User:
Buy it.

GlowCart:
Moves to checkout and asks for explicit confirmation.

User:
Confirm.

GlowCart:
Creates the payment order and opens Razorpay Checkout.

Payment fails.

GlowCart:
Your payment failed. You can retry or use a payment link.

User:
Retry payment.

GlowCart:
Creates a fresh Razorpay payment attempt.

Payment succeeds.

GlowCart:
Verifies the payment server-side and completes the order.

🔑 Design Decisions

1. AI is not the source of financial truth

The LLM never determines:

Final payable amount

Whether inventory exists

Whether an order is paid

Whether a payment signature is valid

Whether a retry is allowed

Those decisions belong to deterministic backend services.

2. Current cart wins over stale conversational state

Checkout is based on the current cart snapshot rather than blindly trusting an older frontend order.

This prevents a scenario where the user changes their cart but accidentally pays for a previous order.

3. Payment failure is recoverable

A payment failure should not force the user to repeat the entire shopping journey.

GlowCart preserves the commerce context and offers bounded recovery.

4. Every important action is observable

The audit trail provides a record of the agent's meaningful actions, particularly around checkout and payment.

🏆 Why This Is Agentic Commerce

GlowCart goes beyond conversational product search.

The agent can:

Understand intent
      ↓
Discover products
      ↓
Evaluate evidence
      ↓
Make a recommendation
      ↓
Maintain context
      ↓
Mutate cart
      ↓
Prepare checkout
      ↓
Request confirmation
      ↓
Initiate payment
      ↓
Handle failure
      ↓
Recover transaction
      ↓
Verify payment
      ↓
Complete order

The important distinction is that autonomy is bounded by deterministic controls.

That makes the system useful without making it uncontrolled.

🎯 Buildathon Focus

GlowCart was designed around the central challenge of AI-led agentic commerce:

How can an AI agent take a user from shopping intent to a real transaction while keeping monetary actions explainable, gated, verifiable, recoverable, and auditable?

The project specifically explores:

Conversational commerce

AI-assisted decision making

End-to-end transaction orchestration

Payment failure recovery

Trust in financial actions

Explainable recommendations

Auditability

🔮 Future Improvements

Potential extensions include:

Multi-merchant product aggregation

Personalized recommendations based on long-term preferences

Inventory reservation during checkout

Webhook-driven payment reconciliation

Fraud/risk scoring

Smarter review summarization

Merchant-side conversion analytics

Voice-based commerce

Multi-agent shopping workflows

Production-grade observability and distributed tracing

👩‍💻 Team / Project

GlowCart — AI-Powered Agentic Commerce

Built as a student project exploring the intersection of:

AI × E-commerce × Payments × Trust

📄 License

This project is intended for educational and buildathon purposes.

Dataset licensing and third-party service terms remain applicable to their respective sources.

<p align="center">

💜 GlowCart

Make commerce conversational. Keep transactions controlled.

</p>
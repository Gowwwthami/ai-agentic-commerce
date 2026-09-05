# Requirements Document

## Introduction

GlowCart is a conversational AI shopping assistant for beauty products built for the Razorpay AI Buildathon. The backend is substantially complete — FastAPI with PostgreSQL, a Gemini-powered orchestrator, and Razorpay Test Mode integration. This feature completes the application by:

1. Replacing the placeholder Vite/React frontend with a polished conversational shopping UI
2. Wiring all missing backend routers in `main.py`
3. Adding the REST endpoints (cart CRUD, checkout, payment verification, payment link, audit retrieval) that the frontend needs to drive the demo flow independently

The result is a fully functional end-to-end demo: a user can browse products, compare them, add to cart, check out, and complete a Razorpay Test Mode payment — all through natural language conversation plus structured UI actions.

---

## Glossary

- **System**: The GlowCart application (frontend + backend together)
- **Frontend**: The React SPA served by Vite at port 5173
- **Backend**: The FastAPI server running at port 8000
- **Orchestrator**: The `handle_chat` function in `backend/agent/orchestrator.py` that dispatches intents
- **Session**: A `ShoppingSession` record keyed by a UUID stored in `localStorage`; represents one user's browsing context
- **Chat_Context**: The React context (`ChatContext`) that holds messages, cart, order, payment, and audit state
- **Session_Context**: The React context (`SessionContext`) that holds the session UUID and initialization status
- **UI_Context**: The React context (`UIContext`) that holds side-panel and modal visibility state
- **Cart**: The set of `CartItem` rows associated with a session; returned as a `Cart` dict by `cart_service`
- **Order**: An `Order` record in the database representing a checkout snapshot; follows the order state machine
- **Order_State_Machine**: The seven-state transition graph: CART → PENDING_CONFIRMATION → PAYMENT_PENDING → PAID / PAYMENT_FAILED → PAYMENT_RECOVERY
- **Payment_View**: The `PaymentView` dict returned by the Backend containing Razorpay-safe fields (key_id, amount_paise, razorpay_order_id)
- **Razorpay_Widget**: The `window.Razorpay` checkout widget loaded from the Razorpay CDN script tag
- **API_Client**: The `src/api/client.js` module; all HTTP calls to the Backend flow through its `request()` function
- **ChatResponse**: The envelope returned by `POST /chat` and most checkout/payment endpoints; contains message, products, cart, order, payment, comparison, audit, needs_confirmation, open_checkout, recovery_options, actions, recommended_product_id
- **ProductCard**: The React component that renders a single product with image, pricing, rating, and review evidence chips
- **ComparisonTable**: The React component that renders a two-column side-by-side product comparison
- **OrderSummary**: The React component that renders the itemised order snapshot and Confirm/Cancel buttons
- **RecoveryOptions**: The React component that renders Retry and Payment Link buttons after a payment failure
- **PaymentModal**: The React portal component that triggers and hosts the Razorpay_Widget
- **AuditPanel**: The React component that renders the chronological audit trail
- **CartPanel**: The React component in the side panel that shows cart items, quantities, and totals
- **RAZORPAY_KEY_ID**: The Razorpay publishable key; safe to expose to the browser
- **RAZORPAY_KEY_SECRET**: The Razorpay secret key; must never leave the Backend
- **ApiError**: The error class in API_Client that captures HTTP status and detail message
- **Demo_Mode**: The application operates with synthetic INR prices and test-mode payment credentials; all pricing is clearly labelled as demo/synthetic

---

## Requirements

### Requirement 1: Session Persistence and Restoration

**User Story:** As a user, I want my session to persist across page reloads, so that my cart, order, and conversation context are restored when I return to the page.

#### Acceptance Criteria

1. WHEN the Frontend first loads, THE Session_Context SHALL read `glowcart_session_id` from `localStorage` and use it as the session ID
2. IF no `glowcart_session_id` key exists in `localStorage`, THEN THE Session_Context SHALL generate a UUID v4 using `crypto.randomUUID()` and write it to `localStorage` under `glowcart_session_id`
3. THE Session_Context SHALL call `GET /session/{session_id}` on mount to restore cart, order, payment, and audit state from the Backend
4. WHEN `GET /session/{session_id}` returns a session, THE Chat_Context SHALL initialise its `cart`, `order`, `payment`, and `audit` fields from the response
5. THE `getOrCreateSessionId()` function SHALL return the same ID on every call within the same browser session (idempotent)
6. THE Backend `GET /session/{session_id}` endpoint SHALL return cart, order, payment view, last product IDs, recommended product ID, and the 25 most recent audit events for the given session

---

### Requirement 2: Conversational Chat Interface

**User Story:** As a user, I want to converse with a shopping AI through a chat interface, so that I can discover, compare, and purchase products using natural language.

#### Acceptance Criteria

1. THE Frontend SHALL render a scrollable message list where each entry is either a user bubble or an assistant bubble
2. WHEN a user submits a message, THE Chat_Context SHALL optimistically append the user message to the message list before the Backend responds
3. WHEN a user submits a message, THE Chat_Context SHALL call `POST /chat` with `{session_id, message}` and set `isTyping: true` until the response arrives
4. WHEN `POST /chat` responds, THE Chat_Context SHALL append an assistant message to the message list containing the `message` text and all embedded rich data (products, comparison, order, needsConfirmation, recoveryOptions)
5. WHEN `POST /chat` responds, THE Chat_Context SHALL merge the top-level response fields (cart, order, payment, audit, openCheckout, recoveryOptions, needsConfirmation, recommendedProductId) into the context state
6. WHILE `isTyping` is true, THE ChatInput SHALL be disabled so the user cannot submit a second message
7. IF `POST /chat` returns an error, THEN THE Chat_Context SHALL append a client-side assistant message with the error description and re-enable ChatInput
8. THE ChatInput SHALL send the message on Enter key press and insert a newline on Shift+Enter
9. THE ChatInput SHALL auto-resize up to a maximum of 4 rows as the user types
10. WHEN at least one product recommendation has been shown, THE ChatInput SHALL render quick-action chips above the input for: "Compare first two", "Which would you pick?", "Add recommended", "Checkout"

---

### Requirement 3: Product Discovery and Recommendation Cards

**User Story:** As a user, I want to see structured product recommendation cards after searching, so that I can evaluate up to 3 products with pricing, ratings, and review evidence.

#### Acceptance Criteria

1. WHEN a ChatResponse contains a non-empty `products` array, THE AssistantMessage SHALL render a ProductGrid containing one ProductCard per product (up to 3)
2. THE ProductCard SHALL display: a product image (with lazy loading), a 1-based index badge, product name, brand, price formatted as ₹{amount}, star rating, and review count
3. WHEN `review_evidence.pros` contains entries, THE ProductCard SHALL render each pro as a green chip
4. WHEN `review_evidence.cons` contains entries, THE ProductCard SHALL render each con as an amber chip
5. WHEN a product's `id` matches `recommendedProductId`, THE ProductCard SHALL display a recommended badge
6. THE ProductCard SHALL include an "Add to cart" button that calls `POST /cart/add` with the product's ID
7. THE ProductCard SHALL display `pricing_note` as small-print disclaimer text beneath the price
8. WHEN `POST /cart/add` succeeds, THE Chat_Context SHALL update its `cart` state from the response

---

### Requirement 4: Product Comparison

**User Story:** As a user, I want to see a side-by-side comparison of two products, so that I can make an informed purchasing decision with clear evidence.

#### Acceptance Criteria

1. WHEN a ChatResponse contains a non-null `comparison`, THE AssistantMessage SHALL render a ComparisonTable
2. THE ComparisonTable SHALL display two columns (one per product) with rows for: price, rating, review count, pros, cons, and score
3. THE ComparisonTable SHALL visually highlight the column of the product whose `id` matches `comparison.recommended_id`
4. THE ComparisonTable SHALL display `comparison.summary` and `comparison.recommended_name` below the table
5. WHEN a comparison is shown, THE Chat_Context SHALL update `recommendedProductId` to `comparison.recommended_id`

---

### Requirement 5: Cart Management

**User Story:** As a user, I want to view and manage my cart in a side panel, so that I can review items, adjust quantities, and see accurate totals before checking out.

#### Acceptance Criteria

1. THE CartPanel SHALL display one CartItemRow per item in `cart.items`, showing: thumbnail, product name, brand, quantity, unit price, and line total
2. THE CartPanel SHALL display a CartTotals section showing `cart.subtotal` and `cart.total` in INR
3. WHEN the user changes an item's quantity using the QuantityStepper, THE Frontend SHALL call `PATCH /cart/items/{item_id}` and update `cart` state from the response
4. WHEN the user clicks RemoveButton on a CartItemRow, THE Frontend SHALL call `DELETE /cart/items/{item_id}?session_id=` and update `cart` state from the response
5. THE CartPanel SHALL show a checkout button that initiates the checkout flow
6. THE Header CartBadge SHALL display `cart.item_count` and update whenever `cart` state changes
7. THE Backend `GET /cart/{session_id}` endpoint SHALL return the current cart with items, item_count, subtotal, total, currency, merchant, and pricing_note
8. THE Backend `POST /cart/add` endpoint SHALL add one item to the cart and return the updated Cart; IF the product is unavailable or stock is insufficient, THEN THE Backend SHALL return a 409 error
9. THE Backend `PATCH /cart/items/{item_id}` endpoint SHALL update the quantity of the specified cart item and return the updated Cart; IF quantity is 0, THEN THE Backend SHALL remove the item
10. THE Backend `DELETE /cart/items/{item_id}` endpoint SHALL remove the specified item and return the updated Cart

---

### Requirement 6: Checkout Flow

**User Story:** As a user, I want a clear checkout flow that shows me an order summary and requires explicit confirmation before payment is initiated, so that I never pay accidentally.

#### Acceptance Criteria

1. WHEN checkout is initiated (via CartPanel button or chat message), THE Backend `POST /checkout/start` endpoint SHALL call `snapshot_cart_into_order`, transition the order to `PENDING_CONFIRMATION`, and return a ChatResponse-shaped payload with `needs_confirmation: true`
2. IF the cart is empty when checkout is initiated, THEN THE Backend SHALL return an error response and no order SHALL be created
3. WHEN a ChatResponse contains `needs_confirmation: true`, THE AssistantMessage SHALL render an OrderSummary component
4. THE OrderSummary SHALL display the itemised order snapshot, total amount, merchant name, and a Demo_Mode pricing disclaimer
5. THE OrderSummary SHALL include a Confirm button and a Cancel button
6. WHEN the user clicks Confirm, THE Frontend SHALL call `sendMessage("yes, confirm")` to trigger `POST /checkout/confirm` via the chat endpoint
7. WHEN `POST /checkout/confirm` is called and the order is in `PENDING_CONFIRMATION` state, THE Backend SHALL create a Razorpay order and transition the order status to `PAYMENT_PENDING`
8. WHEN `POST /checkout/confirm` succeeds, THE ChatResponse SHALL contain `open_checkout: true` and a `payment` block with `razorpay_order_id`, `razorpay_key_id`, `amount_paise`, and `currency`

---

### Requirement 7: Razorpay Payment Integration

**User Story:** As a user, I want to pay for my order using a Razorpay Test Mode checkout widget, so that I can complete the demo purchase flow without real money being charged.

#### Acceptance Criteria

1. THE Frontend SHALL load the Razorpay checkout script from `https://checkout.razorpay.com/v1/checkout.js` via a `<script>` tag in `index.html` and SHALL NOT bundle it
2. WHEN a ChatResponse contains `open_checkout: true` and `payment.razorpay_order_id` is non-null, THE PaymentModal SHALL open and trigger the Razorpay_Widget
3. THE Razorpay_Widget SHALL be configured with: `key` from `payment.razorpay_key_id`, `amount` from `payment.amount_paise`, `currency`, `order_id` from `payment.razorpay_order_id`, `name: "GlowCart"`, `description: "Beauty Products — Test Mode Demo"`, and `theme.color: "#E91E8C"`
4. THE RAZORPAY_KEY_ID SHALL be fetched at runtime from `GET /payment/key` and SHALL NOT be hardcoded in the frontend build
5. THE Backend `GET /payment/key` endpoint SHALL return `{"key_id": RAZORPAY_KEY_ID}` without exposing RAZORPAY_KEY_SECRET
6. WHEN the Razorpay_Widget `handler` callback fires (payment success), THE Frontend SHALL call `POST /payment/verify` with `{session_id, razorpay_order_id, razorpay_payment_id, razorpay_signature}`
7. WHEN `POST /payment/verify` succeeds, THE Backend SHALL call `verify_signature()` via the Razorpay SDK; IF the signature is valid, THEN THE Backend SHALL call `mark_paid()` and write a `payment_verified` audit event
8. WHEN `POST /payment/verify` succeeds with a valid signature, THE Backend SHALL return `{status: "PAID", order}` and THE Frontend SHALL display a PaymentSuccessView
9. IF `POST /payment/verify` returns a 400 error (invalid signature), THEN THE Frontend SHALL display an inline "Payment verification failed" message and offer retry options
10. THE Frontend SHALL NEVER display a payment success state without first receiving a successful `POST /payment/verify` response from the Backend

---

### Requirement 8: Payment Failure Recovery

**User Story:** As a user, I want bounded retry and payment link options when my payment fails, so that I can recover from transient failures without losing my order.

#### Acceptance Criteria

1. WHEN the Razorpay_Widget `modal.ondismiss` callback fires, THE Frontend SHALL call `POST /payment/failed` and transition to a failure state
2. WHEN the Razorpay_Widget `payment.failed` event fires, THE Frontend SHALL call `POST /payment/failed` and transition to a failure state
3. WHEN `POST /payment/failed` is called, THE Backend SHALL call `mark_failed()` on the active order; IF `attempts_remaining > 0`, THEN THE Backend SHALL transition the order to `PAYMENT_RECOVERY` and return `recovery_options: ["retry_payment", "payment_link"]`
4. WHEN a ChatResponse contains a non-empty `recovery_options` array, THE AssistantMessage SHALL render a RecoveryOptions component
5. THE RecoveryOptions component SHALL display a Retry button and a Payment Link button
6. WHEN `order.attempts_remaining === 0`, THE RecoveryOptions component SHALL disable both the Retry button and the Payment Link button
7. WHEN the user clicks Retry, THE Frontend SHALL call `POST /checkout/confirm` (respecting the attempt count tracked server-side)
8. WHEN the user clicks Payment Link, THE Frontend SHALL call `POST /payment/link`; THE Backend SHALL call `create_payment_link()` and return the `payment_link_url`
9. IF `order.payment_attempts >= order.max_attempts`, THEN THE Backend SHALL reject further retry or payment link requests and return an error indicating retry limit is reached
10. THE Backend `POST /payment/failed` endpoint SHALL be idempotent with respect to already-failed orders

---

### Requirement 9: Audit Trail

**User Story:** As a user, I want to see a real-time audit trail of all session events, so that I can understand what actions the system has taken on my behalf.

#### Acceptance Criteria

1. THE AuditPanel SHALL render audit events in reverse chronological order (newest first)
2. EACH audit event row SHALL display: ISO-8601 timestamp, `event_type` as a colour-coded badge, and `description` text
3. WHEN an audit event has non-empty `metadata`, THE AuditPanel SHALL provide an expandable section showing the metadata as formatted JSON
4. THE AuditPanel SHALL only be mounted in the DOM when the audit tab is active, to avoid rendering all events on every state update
5. THE Backend `GET /audit/{session_id}` endpoint SHALL return up to 50 audit events for the session ordered by `created_at` descending
6. WHEN `POST /chat` responds, THE Chat_Context SHALL replace the `audit` state with the `audit` array from the response (up to 25 events)

---

### Requirement 10: Backend Router Wiring

**User Story:** As a developer, I want all backend routers mounted in `main.py`, so that the frontend can reach all required API endpoints.

#### Acceptance Criteria

1. THE Backend `main.py` SHALL import and mount `routers/chat.py` (already exists) via `app.include_router()`
2. THE Backend SHALL contain a `routers/cart.py` file that exposes `GET /cart/{session_id}`, `POST /cart/add`, `PATCH /cart/items/{item_id}`, and `DELETE /cart/items/{item_id}` — all delegating to `cart_service` with no business logic in the router
3. THE Backend SHALL contain a `routers/checkout.py` file that exposes `POST /checkout/start` and `POST /checkout/confirm`
4. THE Backend SHALL contain a `routers/payment.py` file that exposes `POST /payment/verify`, `POST /payment/link`, `POST /payment/failed`, and `GET /payment/key`
5. THE Backend SHALL contain a `routers/audit.py` file that exposes `GET /audit/{session_id}`
6. THE Backend `main.py` SHALL mount all five routers (chat, cart, checkout, payment, audit) so every endpoint listed in Requirement 5–9 is reachable at port 8000

---

### Requirement 11: Security

**User Story:** As a system operator, I want sensitive credentials to be confined to the backend, and payment amounts to be calculated server-side, so that the demo cannot be exploited.

#### Acceptance Criteria

1. THE Backend SHALL never include `RAZORPAY_KEY_SECRET`, `LLM_API_KEY`, or `DATABASE_URL` in any HTTP response body
2. THE `GET /payment/key` endpoint SHALL return only `RAZORPAY_KEY_ID` (the publishable key) and SHALL NOT return `RAZORPAY_KEY_SECRET`
3. THE Frontend SHALL NOT hardcode `RAZORPAY_KEY_ID` in the build; THE Frontend SHALL fetch it at runtime from `GET /payment/key`
4. THE Backend SHALL calculate all payment amounts from `Order.total_amount` server-side; THE Frontend SHALL pass only the `razorpay_order_id` and the `amount_paise` returned by the Backend to the Razorpay_Widget
5. THE Backend `POST /payment/verify` endpoint SHALL perform HMAC-SHA256 signature verification using the Razorpay SDK before calling `mark_paid()`; THE Backend SHALL NOT call `mark_paid()` if signature verification fails
6. THE `write_audit_event` function SHALL strip any `key_secret` field from the metadata before persisting the audit event
7. THE Backend CORS configuration SHALL restrict allowed origins to `http://localhost:5173`

---

### Requirement 12: Error Handling

**User Story:** As a user, I want all failure modes handled gracefully, so that I never see raw error messages and I am never left in a stuck UI state.

#### Acceptance Criteria

1. WHEN any API call returns an HTTP error, THE API_Client SHALL throw an `ApiError` containing the HTTP status and the `detail` field from the response body
2. WHEN `sendMessage` catches an `ApiError`, THE Chat_Context SHALL append an assistant message with a human-readable error description and SHALL re-enable ChatInput
3. WHEN direct REST calls (cart, payment) catch an `ApiError`, THE Frontend SHALL display the `detail` message inline without crashing the component tree
4. THE Orchestrator SHALL catch all unhandled exceptions from `_dispatch` and return a safe error payload (no payment taken, cart and order still visible)
5. WHEN a Razorpay order cannot be created due to `RazorpayUnavailable`, THE Backend SHALL return a response with `recovery_options: ["retry_payment", "payment_link"]` rather than an HTTP 500
6. IF `POST /payment/verify` fails signature verification, THEN THE Backend SHALL return HTTP 400 with `detail: "Payment verification failed"` and shall not transition the order to PAID
7. THE Frontend SHALL NOT display a raw exception traceback or unformatted JSON error at any point in the user-facing UI

---

### Requirement 13: UI Quality and Polish

**User Story:** As a demo audience member, I want a polished, responsive, professional-grade conversational UI, so that the application makes a strong impression during the buildathon demo.

#### Acceptance Criteria

1. THE Frontend SHALL display a loading/typing indicator while `isTyping` is true
2. WHEN the message list is empty (no conversation yet), THE Frontend SHALL render a friendly empty state with a prompt to start shopping
3. THE Frontend SHALL clearly label all prices, totals, and order amounts with a Demo_Mode disclaimer (e.g., "DEMO/SYNTHETIC pricing")
4. THE Frontend SHALL be responsive and usable on both desktop and mobile viewport widths
5. THE Header SHALL display the GlowCart logo, a CartBadge showing `cart.item_count`, and an AuditToggle button
6. THE SidePanel SHALL be collapsible and contain two tabs: Cart and Audit
7. THE Frontend SHALL use no external UI component library; all styles SHALL be implemented with handwritten CSS
8. THE Frontend SHALL add no npm packages beyond those already present in `frontend/package.json` (react, react-dom, vite and dev tooling); the Razorpay script SHALL be loaded via CDN `<script>` tag only
9. WHEN product images are rendered, THE Frontend SHALL set `loading="lazy"` and explicit `width`/`height` attributes to prevent layout shift
10. THE AuditPanel SHALL only be added to the DOM when the audit tab is active

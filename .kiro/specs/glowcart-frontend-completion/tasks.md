# Implementation Plan: GlowCart Frontend Completion

## Overview

Implement the complete GlowCart application end-to-end: wire all backend routers, create the missing REST endpoints, replace the placeholder React frontend with a polished conversational shopping UI, integrate Razorpay Test Mode payment, and validate correctness with property-based tests. Tasks are ordered so that each phase is runnable/testable before the next begins.

## Tasks

- [x] 1. Wire backend routers and add missing REST endpoints
  - [x] 1.1 Fix `backend/main.py` to mount all routers
    - Import `routers.chat`, `routers.cart`, `routers.checkout`, `routers.payment`, and `routers.audit` and call `app.include_router()` for each
    - Keep the existing `routes.router` (products/search) mounted
    - Verify the root health endpoint still returns 200
    - _Requirements: 10.1, 10.6_

  - [x] 1.2 Create `backend/routers/cart.py`
    - Implement `GET /cart/{session_id}` — delegates to `cart_service.get_cart()`
    - Implement `POST /cart/add` — accepts `CartAddRequest`, delegates to `cart_service.add_to_cart()`
    - Implement `PATCH /cart/items/{item_id}` — accepts `CartUpdateRequest`, delegates to `cart_service.update_cart_item()`
    - Implement `DELETE /cart/items/{item_id}?session_id=` — delegates to `cart_service.remove_from_cart()`
    - No business logic in the router; all validation happens in the service layer
    - _Requirements: 5.7, 5.8, 5.9, 5.10, 10.2_

  - [x] 1.3 Create `backend/routers/checkout.py`
    - Implement `POST /checkout/start` — accepts `SessionRequest`, calls `snapshot_cart_into_order`, returns a ChatResponse-shaped payload with `needs_confirmation: true`
    - Implement `POST /checkout/confirm` — accepts `CheckoutConfirmRequest`, delegates to orchestrator's `_do_confirm_checkout` logic (create Razorpay order, transition to PAYMENT_PENDING), returns payload with `open_checkout: true` and `payment` block
    - Return 400 if cart is empty on `/checkout/start`
    - _Requirements: 6.1, 6.2, 6.7, 6.8, 10.3_

  - [x] 1.4 Create `backend/routers/payment.py`
    - Implement `GET /payment/key` — returns `{"key_id": RAZORPAY_KEY_ID}` without exposing KEY_SECRET
    - Implement `POST /payment/verify` — accepts `PaymentVerifyRequest`; calls `razorpay_service.verify_signature()`; on success calls `order_service.mark_paid()` and writes `payment_verified` audit event; returns `{status: "PAID", order}`; on failure returns HTTP 400
    - Implement `POST /payment/link` — accepts `PaymentActionRequest`, calls `razorpay_service.create_payment_link()`, updates order, writes audit event, returns `{order, payment_link_url}`
    - Implement `POST /payment/failed` — accepts `PaymentActionRequest`, calls `order_service.mark_failed()`, transitions to PAYMENT_RECOVERY if attempts remain, returns `{order, recovery_options}`; idempotent on already-failed orders
    - _Requirements: 7.5, 7.7, 8.3, 8.8, 8.9, 8.10, 11.1, 11.2, 11.5, 10.4_

  - [x] 1.5 Create `backend/routers/audit.py`
    - Implement `GET /audit/{session_id}` — calls `audit_service.list_audit_events(db, session_id, limit=50)` and returns the list
    - _Requirements: 9.5, 10.5_

  - [ ]* 1.6 Write property test for orchestrator safe error payload (Property 22)
    - **Property 22: Orchestrator returns a safe error payload for all exceptions from _dispatch**
    - Use `hypothesis` or manually call `handle_chat` with a patched `_dispatch` that raises arbitrary exceptions; assert response contains `message`, `products: []`, `cart`, `order`, `needs_confirmation: false`, `open_checkout: false`
    - **Validates: Requirement 12.4**

  - [ ]* 1.7 Write property test for audit metadata key_secret stripping (Property 23)
    - **Property 23: Audit event metadata is always stripped of key_secret before persistence**
    - Use `fast-check` (frontend) or Python property testing to assert that calling `write_audit_event` with metadata containing `key_secret` never persists that key
    - **Validates: Requirement 11.6**

- [x] 2. Checkpoint — Backend endpoints functional
  - Start the backend (`uvicorn main:app --reload` from `backend/`) and verify all new endpoints respond correctly with `curl` or the Swagger UI at `http://127.0.0.1:8000/docs`. Ensure all tests pass, ask the user if questions arise.

- [x] 3. Set up frontend API layer and session utilities
  - [x] 3.1 Create `frontend/src/api/client.js`
    - Implement the `request(method, path, body)` core function that reads `VITE_API_URL` (defaulting to `http://127.0.0.1:8000`), sets JSON headers, and throws `ApiError` on non-OK responses
    - Export the `api` object with all methods: `sendChat`, `getSession`, `getCart`, `addToCart`, `updateCartItem`, `removeCartItem`, `startCheckout`, `confirmCheckout`, `verifyPayment`, `createPaymentLink`, `reportPaymentFailed`, `getPaymentKey`, `getAudit`
    - Export `ApiError` class with `status` and `detail` fields
    - _Requirements: 12.1, 7.4_

  - [x] 3.2 Create `frontend/src/utils/session.js`
    - Implement `getOrCreateSessionId()`: reads `glowcart_session_id` from `localStorage`; if absent, generates a UUID via `crypto.randomUUID()`, writes it, and returns it
    - _Requirements: 1.1, 1.2, 1.5_

  - [ ]* 3.3 Write property test for `getOrCreateSessionId` idempotence (Property 1)
    - **Property 1: Session ID idempotence**
    - Use `fast-check` to verify that calling `getOrCreateSessionId()` N times (any N ≥ 1) in the same simulated localStorage state always returns the same UUID string
    - **Validates: Requirement 1.5**

  - [ ]* 3.4 Write property test for `ApiError` mapping (Property 21)
    - **Property 21: API_Client maps every HTTP error response to an ApiError with matching status and detail**
    - Use `fast-check` to generate arbitrary 4xx/5xx status codes and detail strings; mock `fetch` and assert `request()` throws `ApiError` with matching `status` and `detail`
    - **Validates: Requirement 12.1**

- [-] 4. Create React context providers
  - [-] 4.1 Create `frontend/src/contexts/SessionContext.jsx`
    - Provide `sessionId` (string) and `initialized` (boolean)
    - On mount: call `getOrCreateSessionId()`, then call `api.getSession(id)` and store the result so `ChatContext` can hydrate from it
    - Also fetch the Razorpay key via `api.getPaymentKey()` on mount and store `razorpayKeyId` in context for use in `PaymentModal`
    - _Requirements: 1.1, 1.2, 1.3, 7.4_

  - [ ] 4.2 Create `frontend/src/contexts/ChatContext.jsx`
    - Provide: `messages`, `isTyping`, `cart`, `order`, `payment`, `comparison`, `audit`, `openCheckout`, `recoveryOptions`, `needsConfirmation`, `recommendedProductId`
    - Implement `sendMessage(text)`: optimistically append user message → set `isTyping: true` → call `api.sendChat()` → merge all top-level response fields → append assistant message with embedded `products`, `comparison`, `order`, `needsConfirmation`, `recoveryOptions` → set `isTyping: false`; on error, append client-side error message and re-enable input
    - Provide `updateCart(cart)` for direct REST calls (cart PATCH/DELETE) to update cart state
    - Hydrate `cart`, `order`, `payment`, `audit` from `SessionContext`'s session response on first render
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 9.6, 12.2, 1.4_

  - [ ] 4.3 Create `frontend/src/contexts/UIContext.jsx`
    - Provide: `sidePanelTab` ("cart" | "audit"), `sidePanelOpen` (boolean), `paymentModalOpen` (boolean)
    - Provide setters: `setSidePanelTab`, `toggleSidePanel`, `openPaymentModal`, `closePaymentModal`
    - `openPaymentModal` is called from `ChatContext` when `open_checkout: true` in a response
    - _Requirements: 13.6_

  - [ ]* 4.4 Write property test for ChatContext response mapping (Property 3)
    - **Property 3: Chat response is faithfully mapped to assistant message and context state**
    - Use `fast-check` to generate arbitrary valid `ChatResponse` objects; render `ChatContext` in test environment; call `sendMessage`; assert all top-level fields and the appended assistant message fields match the generated response
    - **Validates: Requirements 2.4, 2.5**

  - [ ]* 4.5 Write property test for SessionContext initialisation (Property 2)
    - **Property 2: Session response fully initialises context state**
    - Use `fast-check` to generate arbitrary session responses; assert that after initialisation `cart`, `order`, `payment`, `audit` each equal the corresponding field from the response
    - **Validates: Requirement 1.4**

- [ ] 5. Update `frontend/src/App.jsx` and `frontend/src/main.jsx`
  - Replace the placeholder `App.jsx` content with the `AppShell` layout: wrap the tree in `SessionProvider → ChatProvider → UIContext.Provider`; render `Header`, `MainLayout` (ChatPanel + SidePanel side by side), and the `PaymentModal` portal
  - Update `main.jsx` only if strict-mode or entry-point changes are needed
  - _Requirements: 13.5, 13.6_

- [ ] 6. Create Header and navigation components
  - [ ] 6.1 Create `frontend/src/components/Header.jsx`
    - Render: GlowCart logo text/icon, `CartBadge` showing `cart.item_count` from `ChatContext`, and an `AuditToggle` button that calls `setSidePanelTab("audit")` / `toggleSidePanel()` from `UIContext`
    - `CartBadge` updates reactively whenever `cart` changes
    - _Requirements: 13.5, 5.6_

  - [ ]* 6.2 Write property test for CartBadge (Property 11, partial)
    - **Property 11: CartBadge reflects item_count for any Cart**
    - Use `fast-check` to generate arbitrary `Cart` objects; render `Header` with that cart; assert the badge text equals `cart.item_count`
    - **Validates: Requirement 5.6**

- [ ] 7. Create Chat UI components
  - [ ] 7.1 Create `frontend/src/components/chat/MessageList.jsx`
    - Render a scrollable list of `ChatMessage` objects from `ChatContext.messages`; auto-scroll to bottom on new messages
    - Render `UserMessage` for `role: "user"` and `AssistantMessage` for `role: "assistant"`
    - When `messages` is empty, render the welcome/empty state with a prompt to start shopping
    - _Requirements: 2.1, 13.2_

  - [ ]* 7.2 Write property test for MessageList bubble types (Property 5)
    - **Property 5: Message list renders the correct bubble type for every message**
    - Use `fast-check` to generate arbitrary arrays of `ChatMessage` with random `role` values; render `MessageList`; assert exactly one bubble per message and correct bubble type per role
    - **Validates: Requirement 2.1**

  - [ ] 7.3 Create `frontend/src/components/chat/UserMessage.jsx` and `AssistantMessage.jsx`
    - `UserMessage`: renders the message text in a right-aligned bubble with timestamp
    - `AssistantMessage`: renders message text, then conditionally renders `ProductGrid`, `ComparisonTable`, `OrderSummary`, and `RecoveryOptions` based on the message's embedded data fields
    - _Requirements: 2.1, 2.4, 3.1, 4.1, 6.3, 8.4_

  - [ ] 7.4 Create `frontend/src/components/chat/ChatInput.jsx`
    - Textarea that auto-resizes up to 4 rows; sends on Enter, inserts newline on Shift+Enter
    - Disabled when `isTyping` is true (sourced from `ChatContext`)
    - Renders quick-action chips above input once `recommendedProductId` is non-null: "Compare first two", "Which would you pick?", "Add recommended", "Checkout"
    - Each chip calls `sendMessage` with the appropriate text
    - _Requirements: 2.6, 2.8, 2.9, 2.10_

  - [ ]* 7.5 Write property test for ChatInput disabled state (Property 4)
    - **Property 4: ChatInput is always disabled while isTyping is true**
    - Use `fast-check` to generate arbitrary `isTyping` boolean; render `ChatInput` with that value; assert textarea and send button `disabled` attribute matches `isTyping`
    - **Validates: Requirement 2.6**

- [ ] 8. Create Product components
  - [ ] 8.1 Create `frontend/src/components/products/ProductCard.jsx`
    - Display: `loading="lazy"` image with explicit width/height, 1-based index badge, name, brand, price as `₹{amount}`, star rating, review count
    - Render `review_evidence.pros` entries as green chips and `review_evidence.cons` entries as amber chips
    - Show recommended badge (crown icon or "★ Recommended" label) when `product.id === recommendedProductId`
    - Show `pricing_note` as small-print disclaimer text
    - "Add to cart" button calls `api.addToCart()` and updates `ChatContext.cart` via `updateCart()`
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 7.9_

  - [ ]* 8.2 Write property test for ProductCard required fields (Property 7)
    - **Property 7: ProductCard renders all required fields for any product**
    - Use `fast-check` to generate arbitrary valid `Product` objects; render `ProductCard`; assert name, brand, formatted price, rating, review_count, and pricing_note are all present in the output
    - **Validates: Requirements 3.2, 3.7**

  - [ ]* 8.3 Write property test for ProductCard review evidence chips (Property 8)
    - **Property 8: ProductCard renders review evidence chips with correct count and type**
    - Use `fast-check` to generate products with N pros and M cons (N, M ≥ 0); render `ProductCard`; assert exactly N green chips and exactly M amber chips
    - **Validates: Requirements 3.3, 3.4**

  - [ ]* 8.4 Write property test for recommended badge logic (Property 9)
    - **Property 9: Recommended badge appears if and only if product.id matches recommendedProductId**
    - Use `fast-check` to generate arbitrary `product.id` and `recommendedProductId` pairs; assert badge is shown iff they are equal
    - **Validates: Requirement 3.5**

  - [ ] 8.5 Create `frontend/src/components/products/ProductGrid.jsx`
    - Accepts a `products` array; renders one `ProductCard` per entry (up to 3)
    - Passes `index` (1-based), `isRecommended`, and `onAddToCart` props to each card
    - _Requirements: 3.1_

  - [ ]* 8.6 Write property test for ProductGrid card count (Property 6)
    - **Property 6: ProductGrid always contains exactly as many cards as there are products**
    - Use `fast-check` to generate arrays of 1–3 products; render `ProductGrid`; assert exactly N `ProductCard` elements are rendered
    - **Validates: Requirement 3.1**

  - [ ] 8.7 Create `frontend/src/components/products/ComparisonTable.jsx`
    - Render two columns with rows for: price, rating, review count, pros, cons, score
    - Visually highlight the column whose `id` equals `comparison.recommended_id`
    - Display `comparison.summary` and `comparison.recommended_name` below the table
    - Update `recommendedProductId` in `ChatContext` to `comparison.recommended_id` when rendered
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [ ]* 8.8 Write property test for ComparisonTable (Property 12)
    - **Property 12: ComparisonTable renders all required rows and highlights the winning column**
    - Use `fast-check` to generate arbitrary `Comparison` objects; render `ComparisonTable`; assert all six rows are present, the winning column has its highlight class, and summary/recommended_name appear beneath
    - **Validates: Requirements 4.2, 4.3, 4.4**

- [ ] 9. Create Cart components
  - [ ] 9.1 Create `frontend/src/components/cart/CartItemRow.jsx` and `QuantityStepper.jsx`
    - `CartItemRow`: shows thumbnail, product name, brand, unit price, line total; includes `QuantityStepper` and a RemoveButton
    - `QuantityStepper`: decrement/increment buttons; on change calls `api.updateCartItem()` then `updateCart()`; on decrement to 0, calls `api.removeCartItem()`
    - RemoveButton calls `api.removeCartItem()` then `updateCart()`
    - _Requirements: 5.1, 5.3, 5.4_

  - [ ] 9.2 Create `frontend/src/components/cart/CartTotals.jsx`
    - Display `cart.subtotal` and `cart.total` in INR with Demo_Mode disclaimer
    - Total shown must equal `sum(item.line_total)` from `cart.items`
    - _Requirements: 5.2, 13.3_

  - [ ]* 9.3 Write property test for cart totals invariant (Property 10)
    - **Property 10: Cart totals invariant — displayed total equals the sum of line totals**
    - Use `fast-check` to generate arbitrary `Cart` objects with random items; render `CartTotals`; assert the displayed total equals `sum(item.line_total for item in cart.items)` and equals `cart.total`
    - **Validates: Requirement 5.2**

  - [ ] 9.4 Create `frontend/src/components/cart/CartPanel.jsx`
    - Render one `CartItemRow` per `cart.items` entry, followed by `CartTotals`
    - Include a "Checkout" button that calls `sendMessage("proceed to checkout")`
    - _Requirements: 5.1, 5.5_

  - [ ]* 9.5 Write property test for CartPanel row count (Property 11, partial)
    - **Property 11: CartPanel row count matches cart item count**
    - Use `fast-check` to generate arbitrary `Cart` objects with N items; render `CartPanel`; assert exactly N `CartItemRow` elements are rendered
    - **Validates: Requirement 5.1**

  - [ ] 9.6 Create `frontend/src/components/checkout/OrderSummary.jsx`
    - Show itemised order snapshot, total, merchant name, and Demo_Mode pricing disclaimer
    - Include a Confirm button (calls `sendMessage("yes, confirm")`) and a Cancel button
    - _Requirements: 6.3, 6.4, 6.5, 6.6, 13.3_

  - [ ] 9.7 Create `frontend/src/components/checkout/RecoveryOptions.jsx`
    - Render only when `recovery_options` is non-empty (a Retry button and a Payment Link button)
    - Both buttons disabled when `attemptsRemaining === 0`
    - Retry button calls `sendMessage("retry payment")` which hits `POST /checkout/confirm`
    - Payment Link button calls `api.createPaymentLink()` and updates order state
    - _Requirements: 8.4, 8.5, 8.6, 8.7, 8.8_

  - [ ]* 9.8 Write property test for RecoveryOptions rendering (Property 18)
    - **Property 18: RecoveryOptions renders iff recovery_options is non-empty; buttons disabled at zero attempts remaining**
    - Use `fast-check` to generate arbitrary recovery_options arrays and attemptsRemaining values; assert component renders iff array is non-empty, and buttons are disabled iff attemptsRemaining === 0
    - **Validates: Requirements 8.4, 8.6**

- [ ] 10. Checkpoint — Core UI functional
  - Ensure all tests pass, ask the user if questions arise. The chat, cart, product cards, comparison, order summary, and recovery options should all be functional end-to-end at this checkpoint.

- [ ] 11. Create Payment components
  - [ ] 11.1 Create `frontend/src/components/payment/PaymentModal.jsx`
    - Render as a React portal (`createPortal`) so it overlays the full page
    - On mount (when `paymentModalOpen` is true and `payment.razorpay_order_id` is non-null), call `openRazorpayCheckout()` imperatively via `window.Razorpay`
    - Configure widget with `key: payment.razorpay_key_id`, `amount: payment.amount_paise`, `currency`, `order_id: payment.razorpay_order_id`, `name: "GlowCart"`, `description: "Beauty Products — Test Mode Demo"`, `theme.color: "#E91E8C"`
    - On `handler` (success): call `api.verifyPayment()` with all three Razorpay fields; on success show `PaymentSuccessView`; on 400 show inline "Payment verification failed" with retry option
    - On `modal.ondismiss` or `payment.failed` event: call `api.reportPaymentFailed()` then dispatch to `ChatContext`
    - Never show success state without a successful `POST /payment/verify` response
    - _Requirements: 7.1, 7.2, 7.3, 7.6, 7.7, 7.8, 7.9, 7.10, 11.3, 11.4_

  - [ ] 11.2 Create `frontend/src/components/payment/PaymentSuccessView.jsx`
    - Displays a success state with order ID and total amount after `POST /payment/verify` returns `status: "PAID"`
    - _Requirements: 7.8_

  - [ ] 11.3 Create `frontend/src/components/payment/PaymentFailureView.jsx`
    - Displays failure state; shows Retry and Payment Link buttons (delegates to `RecoveryOptions` or inline equivalent)
    - _Requirements: 8.1, 8.2_

  - [ ]* 11.4 Write property test for PaymentModal open condition (Property 14)
    - **Property 14: PaymentModal only opens when open_checkout is true AND razorpay_order_id is non-null**
    - Use `fast-check` to generate arbitrary `ChatResponse` objects with all combinations of `open_checkout` and `payment.razorpay_order_id`; assert the modal is opened iff both conditions are true
    - **Validates: Requirement 7.2**

  - [ ]* 11.5 Write property test for payment verify fields (Property 17)
    - **Property 17: Payment verify call always includes all three Razorpay fields**
    - Use `fast-check` to generate arbitrary Razorpay handler callback payloads; mock `api.verifyPayment`; assert it is called with all three fields from the callback plus sessionId
    - **Validates: Requirement 7.6**

  - [ ]* 11.6 Write property test for Razorpay widget amount configuration (Property 16)
    - **Property 16: Razorpay widget is always configured with the backend-provided amount_paise**
    - Use `fast-check` to generate arbitrary `PaymentView` objects; mock `window.Razorpay`; assert the options object has `amount === payment.amount_paise` and `key === payment.razorpay_key_id`
    - **Validates: Requirements 7.3, 11.4**

  - [ ]* 11.7 Write property test for payment success gating (Property 15)
    - **Property 15: Payment success state is only shown after a successful /payment/verify response**
    - Use `fast-check` to simulate various widget callback sequences; assert `PaymentSuccessView` is never shown unless `api.verifyPayment` resolved with `status: "PAID"`
    - **Validates: Requirement 7.10**

- [ ] 12. Create SidePanel and AuditPanel components
  - [ ] 12.1 Create `frontend/src/components/layout/SidePanel.jsx`
    - Collapsible panel with two tabs: "Cart" and "Audit"
    - Renders `CartPanel` when tab is "cart" and `AuditPanel` only when tab is "audit" (unmount when not active per requirement 9.4)
    - Tab switching is driven by `UIContext.sidePanelTab`
    - _Requirements: 13.6, 9.4_

  - [ ] 12.2 Create `frontend/src/components/audit/AuditPanel.jsx` and `AuditEventRow.jsx`
    - `AuditPanel`: renders events newest-first; mounted only when audit tab is active
    - `AuditEventRow`: displays ISO-8601 timestamp, `event_type` as a colour-coded badge, description text, and a collapsible metadata JSON section when `metadata` is non-empty
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 12.3 Write property test for AuditPanel ordering and required fields (Property 20)
    - **Property 20: AuditPanel renders events newest-first with all required fields in every row**
    - Use `fast-check` to generate arbitrary arrays of `AuditEvent` objects with random `created_at` values; render `AuditPanel`; assert rows appear in reverse chronological order and every row contains timestamp, event_type badge, and description
    - **Validates: Requirements 9.1, 9.2**

- [ ] 13. Implement all CSS styles
  - [ ] 13.1 Write `frontend/src/index.css` with CSS custom properties and base reset
    - Define colour tokens: `--glow-pink: #E91E8C`, `--glow-dark`, `--glow-surface`, `--glow-border`, `--glow-text`, `--glow-muted`
    - Typography: Fraunces for headings/logo, Outfit for body (both already loaded via Google Fonts in `index.html`)
    - Base reset: box-sizing, margin/padding, font-family
    - _Requirements: 13.7_

  - [ ] 13.2 Write component-scoped CSS for layout and chat components
    - `App.css` / layout: full-viewport AppShell, Header (fixed top), MainLayout (flex row), ChatPanel (flex: 1), SidePanel (fixed width, collapsible)
    - Chat components: user bubble (right-aligned, pink bg), assistant bubble (left-aligned, surface bg), typing indicator (3-dot animation), welcome empty state
    - `ChatInput`: textarea with auto-resize, chip row, send button
    - _Requirements: 13.1, 13.2, 13.4_

  - [ ] 13.3 Write component-scoped CSS for product, cart, checkout, and payment components
    - `ProductCard`: card layout, index badge, recommended badge, green/amber chip styles, lazy image container with fixed aspect ratio
    - `ComparisonTable`: two-column grid, winner highlight (pink left border or background tint), below-table summary
    - `CartPanel`: scrollable item list, CartItemRow flex layout, QuantityStepper button pair
    - `CartTotals`: total line with demo disclaimer
    - `OrderSummary`: itemised list, total, confirm/cancel button pair
    - `RecoveryOptions`: inline button pair, disabled state
    - `PaymentModal`: portal overlay with dark backdrop
    - `AuditPanel`: monospace metadata block, event_type badge colours
    - _Requirements: 13.3, 13.7, 7.9_

  - [ ] 13.4 Add responsive layout media query
    - Below 768 px: SidePanel moves below ChatPanel (flex-direction: column), Header adapts to compact mode
    - _Requirements: 13.4_

  - [ ]* 13.5 Write property test for demo mode disclaimers (Property 24)
    - **Property 24: Demo mode disclaimers appear in all price-bearing rendered components**
    - Use `fast-check` to generate arbitrary products, carts, and orders; render `ProductCard`, `CartTotals`, and `OrderSummary`; assert each rendered output contains "DEMO", "SYNTHETIC", or "demo"
    - **Validates: Requirement 13.3**

- [ ] 14. Install `fast-check` and set up Vitest for frontend property tests
  - Add `vitest`, `@vitest/ui`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`, and `fast-check` as `devDependencies` in `frontend/package.json`
  - Update `frontend/vite.config.js` to include `test: { environment: "jsdom", globals: true }` configuration
  - Create `frontend/src/tests/setup.js` that imports `@testing-library/jest-dom`
  - All `*.test.jsx` / `*.test.js` files created in tasks 3–13 should be placed under `frontend/src/tests/`
  - _Requirements: (testing infrastructure — supports all property test sub-tasks)_

- [ ] 15. Checkpoint — Run property-based tests
  - Run `npx vitest --run` from `frontend/` to execute all property tests written in the `*` sub-tasks above
  - Fix any failing property tests before proceeding
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Integration wiring and runtime bug fixes
  - [ ] 16.1 Verify the full happy-path demo flow end-to-end
    - Start backend (`uvicorn main:app --reload`) and frontend (`npm run dev`) and walk through: search → compare → add to cart → checkout → confirm → Razorpay Test Mode payment → verify → PaymentSuccessView
    - Fix any runtime bugs found (missing CORS headers, mismatched field names between backend response and frontend interface, etc.)
    - _Requirements: 2.1–2.10, 3.1–3.8, 5.1–5.10, 6.1–6.8, 7.1–7.10_

  - [ ] 16.2 Verify payment failure recovery flow
    - Dismiss the Razorpay widget mid-flow and verify: `POST /payment/failed` is called → `PAYMENT_RECOVERY` state → `RecoveryOptions` rendered → Retry re-opens widget → success on retry shows `PaymentSuccessView`
    - _Requirements: 8.1–8.10_

  - [ ] 16.3 Verify session restoration on page reload
    - Reload the page mid-session and verify: `localStorage` session ID is reused → `GET /session/{id}` restores cart and order → conversation history does NOT need to be restored (messages are not persisted) but cart/order state is
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ] 16.4 Verify audit panel shows all events
    - Open the audit tab after a complete shopping flow; verify events appear newest-first with correct badges; verify metadata sections expand for events that have metadata
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 17. Final checkpoint — Ensure all tests pass and demo flow is complete
  - Run `npx vitest --run` from `frontend/` one final time to confirm no regressions
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP development
- Task 14 (fast-check / Vitest setup) should be done before executing any `*` sub-tasks
- All backend tasks run from the `backend/` directory with the `venv` activated; the `uvicorn` command is `uvicorn main:app --reload`
- All frontend tasks run from the `frontend/` directory; use `npm run dev` for the dev server and `npx vitest --run` for tests
- The Razorpay CDN script is already present in `frontend/index.html` — no changes needed
- The `VITE_API_URL` environment variable is optional; it defaults to `http://127.0.0.1:8000`
- Property tests validate universal correctness properties from the design document; unit tests validate specific examples
- Checkpoints at tasks 2, 10, 15, and 17 ensure incremental validation throughout the build

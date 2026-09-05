/**
 * GlowCart API client.
 * All HTTP calls flow through request() so error handling is consistent.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function request(method, path, body = null) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== null) {
    options.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, options);
  } catch {
    throw new ApiError(0, "Network error — is the backend running?");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail ?? detail;
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  return res.json();
}

export const api = {
  /** POST /chat */
  sendChat: (sessionId, message) =>
    request("POST", "/chat", { session_id: sessionId, message }),

  /** GET /session/{session_id} */
  getSession: (sessionId) => request("GET", `/session/${sessionId}`),

  /** GET /cart/{session_id} */
  getCart: (sessionId) => request("GET", `/cart/${sessionId}`),

  /** POST /cart/add */
  addToCart: (sessionId, productId, quantity = 1) =>
    request("POST", "/cart/add", {
      session_id: sessionId,
      product_id: productId,
      quantity,
    }),

  /** PATCH /cart/items/{item_id} */
  updateCartItem: (sessionId, itemId, quantity) =>
    request("PATCH", `/cart/items/${itemId}`, {
      session_id: sessionId,
      quantity,
    }),

  /** DELETE /cart/items/{item_id}?session_id= */
  removeCartItem: (sessionId, itemId) =>
    request("DELETE", `/cart/items/${itemId}?session_id=${encodeURIComponent(sessionId)}`),

  /** POST /checkout/start */
  startCheckout: (sessionId) =>
    request("POST", "/checkout/start", { session_id: sessionId }),

  /** POST /checkout/confirm */
  confirmCheckout: (sessionId) =>
    request("POST", "/checkout/confirm", { session_id: sessionId, confirm: true }),

  /** POST /payment/verify */
  verifyPayment: (sessionId, orderId, paymentId, signature) =>
    request("POST", "/payment/verify", {
      session_id: sessionId,
      razorpay_order_id: orderId,
      razorpay_payment_id: paymentId,
      razorpay_signature: signature,
    }),

  /** POST /payment/link */
  createPaymentLink: (sessionId) =>
    request("POST", "/payment/link", { session_id: sessionId }),

  /** POST /payment/failed */
  reportPaymentFailed: (sessionId) =>
    request("POST", "/payment/failed", { session_id: sessionId }),

  /** GET /payment/key */
  getPaymentKey: () => request("GET", "/payment/key"),

  /** GET /audit/{session_id} */
  getAudit: (sessionId) => request("GET", `/audit/${sessionId}`),
};

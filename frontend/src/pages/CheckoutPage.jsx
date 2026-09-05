import { useCallback, useEffect, useState } from "react";
import { useSession } from "../contexts/SessionContext";
import { api, ApiError } from "../api/client";
import { OrderSummary } from "../components/OrderSummary";
import { money, loadRazorpayScript } from "../utils/razorpay";
import { navigate } from "../router/router";

/**
 * Opens the Razorpay checkout modal.
 * Pure function — no hook calls — so it can be shared by both
 * confirmCheckout and the manual "Open Razorpay" button.
 */
async function doOpenRazorpay({
  currentOrder,
  razorpayKey,
  paymentKey,
  onSuccess,
  onFailed,
  onDismiss,
}) {
  await loadRazorpayScript();

  const key = razorpayKey || paymentKey || currentOrder?.razorpay_key_id;

  if (!key) throw new Error("Razorpay public key is unavailable. Check the backend configuration.");
  if (!currentOrder.razorpay_order_id) throw new Error("No Razorpay order was created for this checkout.");

  const options = {
    key,
    amount:
      currentOrder.amount_paise ??
      Math.round(Number(currentOrder.total_amount) * 100),
    currency: currentOrder.currency || "INR",
    name: currentOrder.merchant || "GlowCart",
    description: `GlowCart demo order #${currentOrder.id}`,
    order_id: currentOrder.razorpay_order_id,
    handler: onSuccess,
    modal: { ondismiss: onDismiss },
    theme: { color: "#635BFF" },
  };

  const rzp = new window.Razorpay(options);
  rzp.on("payment.failed", onFailed);
  rzp.open();
}

export function CheckoutPage() {
  const {
    sessionId,
    razorpayKeyId,
    cart,
    order, setOrder,
    payment, setPayment,
    setAudit,
    refreshSession,
  } = useSession();

  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [checkoutStarted, setCheckoutStarted] = useState(false);
  const [error, setError] = useState("");

  // Never show or pay an order whose snapshot no longer matches the cart.
  // This can happen when the user changes the cart after an older checkout
  // order was saved in the session. The next explicit checkout action will
  // create/snapshot an order from the current cart on the backend.
  useEffect(() => {
    if (!cart?.items?.length || !order?.items) return;

    const normalizeItems = (items) =>
      items
        .map((item) => ({
          product_id: Number(item.product_id),
          quantity: Number(item.quantity),
          unit_price: Number(item.unit_price),
        }))
        .sort((a, b) => a.product_id - b.product_id);

    const cartItems = normalizeItems(cart.items);
    const orderItems = normalizeItems(order.items);
    const itemsMatch =
      cartItems.length === orderItems.length &&
      cartItems.every(
        (item, index) =>
          item.product_id === orderItems[index].product_id &&
          item.quantity === orderItems[index].quantity &&
          item.unit_price === orderItems[index].unit_price,
      );
    const totalMatches =
      Math.round(Number(cart.total) * 100) ===
      Math.round(Number(order.total_amount) * 100);

    if (!itemsMatch || !totalMatches) {
      setOrder(null);
      setPayment(null);
      setCheckoutStarted(false);
      setError(
        "Your cart changed since the previous checkout. Please review the current cart before paying.",
      );
    }
  }, [cart, order, setOrder, setPayment]);

  const openRazorpayCheckout = useCallback(async (currentOrder) => {
    if (!currentOrder) return;

    setError("");
    setPaymentBusy(true);

    try {
      await doOpenRazorpay({
        currentOrder,
        sessionId,
        razorpayKey: razorpayKeyId,
        paymentKey: payment?.razorpay_key_id,
        onSuccess: async (response) => {
          setPaymentBusy(true);
          try {
            const verified = await api.verifyPayment(
              sessionId,
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature,
            );
            setOrder(verified.order ?? null);
            setPayment({ status: "PAID", paid: true, ...verified.order });
            await refreshSession();
            navigate(`/order/${verified.order?.id ?? currentOrder.id}`);
          } catch (err) {
            setError(err instanceof ApiError ? err.detail : "Payment verification failed.");
            setPaymentBusy(false);
          }
        },
        onFailed: async () => {
          try {
            const result = await api.reportPaymentFailed(sessionId);
            setOrder(result.order ?? null);
            setPayment(result.payment ?? null);
            await refreshSession();
            navigate(`/order/${result.order?.id ?? currentOrder.id}`);
          } catch (err) {
            setError(err instanceof ApiError ? err.detail : "Payment failed and recovery info could not be loaded.");
          } finally {
            setPaymentBusy(false);
          }
        },
        onDismiss: () => setPaymentBusy(false),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open Razorpay Checkout.");
      setPaymentBusy(false);
    }
  }, [sessionId, razorpayKeyId, payment, setOrder, setPayment, refreshSession]);

  // Step 1: Start checkout (creates PENDING_CONFIRMATION order)
  const startCheckout = useCallback(async () => {
    setError("");
    setCheckoutBusy(true);
    try {
      const response = await api.startCheckout(sessionId);
      setOrder(response.order ?? null);
      if (response.payment !== undefined) setPayment(response.payment ?? null);
      if (response.audit) setAudit(response.audit);
      setCheckoutStarted(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't start checkout.");
    } finally {
      setCheckoutBusy(false);
    }
  }, [sessionId, setOrder, setPayment, setAudit]);

  // Step 2: Confirm → create Razorpay order → optionally open checkout
  const confirmCheckout = useCallback(async () => {
    setError("");
    setCheckoutBusy(true);
    try {
      const response = await api.confirmCheckout(sessionId);
      setOrder(response.order ?? null);
      if (response.payment !== undefined) setPayment(response.payment ?? null);
      if (response.audit) setAudit(response.audit);

      if (response.open_checkout && response.order) {
        setCheckoutBusy(false);
        await doOpenRazorpay({
          currentOrder: response.order,
          sessionId,
          razorpayKey: razorpayKeyId,
          paymentKey: response.order.razorpay_key_id,
          onSuccess: async (rzpResponse) => {
            setPaymentBusy(true);
            try {
              const verified = await api.verifyPayment(
                sessionId,
                rzpResponse.razorpay_order_id,
                rzpResponse.razorpay_payment_id,
                rzpResponse.razorpay_signature,
              );
              setOrder(verified.order ?? null);
              setPayment({ status: "PAID", paid: true, ...verified.order });
              await refreshSession();
              navigate(`/order/${verified.order?.id ?? response.order.id}`);
            } catch (err) {
              setError(err instanceof ApiError ? err.detail : "Payment verification failed.");
              setPaymentBusy(false);
            }
          },
          onFailed: async () => {
            try {
              const result = await api.reportPaymentFailed(sessionId);
              setOrder(result.order ?? null);
              setPayment(result.payment ?? null);
              await refreshSession();
              navigate(`/order/${result.order?.id ?? response.order.id}`);
            } catch (err) {
              setError(err instanceof ApiError ? err.detail : "Recovery info could not be loaded.");
            } finally {
              setPaymentBusy(false);
            }
          },
          onDismiss: () => setPaymentBusy(false),
        });
        return;
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't create the payment order.");
    } finally {
      setCheckoutBusy(false);
    }
  }, [sessionId, razorpayKeyId, setOrder, setPayment, setAudit, refreshSession]);

  const anyBusy = checkoutBusy || paymentBusy;
  const hasCart = cart?.items?.length > 0;
  const pendingConfirmation = order?.status === "PENDING_CONFIRMATION";
  const paymentPending = order?.status === "PAYMENT_PENDING";

  return (
    <div className="page page--checkout">
      <div className="page__inner page__inner--narrow">
        <div className="page-header">
          <div>
            <span className="eyebrow">CHECKOUT</span>
            <h1>Confirm your order</h1>
          </div>
          <span className="test-pill">TEST MODE</span>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            <span aria-hidden="true">!</span>
            <p>{error}</p>
            <button onClick={() => setError("")} aria-label="Dismiss">×</button>
          </div>
        )}

        {/* No cart, no order */}
        {!hasCart && !order && (
          <div className="checkout-empty">
            <p>Your cart is empty.</p>
            <button className="btn btn--primary" onClick={() => navigate("/shop")}>
              Start shopping
            </button>
          </div>
        )}

        {/* Step 1: Cart preview */}
        {hasCart && !checkoutStarted && !pendingConfirmation && !paymentPending && (
          <div className="checkout-step">
            <h2 className="checkout-step__title">Review your cart</h2>
            <div className="checkout-review-items">
              {cart.items.map((item) => (
                <div className="checkout-review-line" key={item.id}>
                  <span>{item.name} × {item.quantity}</span>
                  <strong>{money(item.line_total)}</strong>
                </div>
              ))}
              <div className="checkout-review-line checkout-review-line--total">
                <span>Total</span>
                <strong>{money(cart.total)}</strong>
              </div>
            </div>

            <div className="checkout-gate">
              <span className="checkout-gate__icon" aria-hidden="true">✓</span>
              <p>
                Click below to create your order. This will not charge you yet — you&apos;ll
                confirm the exact amount before payment is requested.
              </p>
            </div>

            <button
              className="btn btn--primary btn--full"
              disabled={anyBusy}
              onClick={startCheckout}
            >
              {checkoutBusy ? "Creating order..." : "Review & create order"}
            </button>
          </div>
        )}

        {/* Step 2: PENDING_CONFIRMATION — explicit confirm gate */}
        {pendingConfirmation && order && (
          <div className="checkout-step">
            <OrderSummary order={order} />

            <div className="checkout-gate checkout-gate--warning">
              <span className="checkout-gate__icon" aria-hidden="true">✓</span>
              <div>
                <strong>Explicit confirmation required</strong>
                <p>
                  You&apos;re authorizing a payment of{" "}
                  <strong>{money(order.total_amount)}</strong> for this order.
                  A Razorpay Test Mode payment request will be created only after you confirm.
                </p>
              </div>
            </div>

            <div className="checkout-confirm-actions">
              <button
                className="btn btn--primary btn--lg"
                disabled={anyBusy}
                onClick={confirmCheckout}
              >
                {checkoutBusy ? "Creating payment..." : `Confirm & pay ${money(order.total_amount)}`}
              </button>
              <button
                className="btn btn--secondary"
                disabled={anyBusy}
                onClick={() => { setOrder(null); setCheckoutStarted(false); }}
              >
                Cancel
              </button>
            </div>

            <p className="pricing-note">
              {order.merchant} · Synthetic demo INR pricing · Razorpay Test Mode
            </p>
          </div>
        )}

        {/* Step 3: PAYMENT_PENDING — Razorpay ready */}
        {paymentPending && order && (
          <div className="checkout-step">
            <OrderSummary order={order} />

            <div className="checkout-gate">
              <span className="checkout-gate__icon" aria-hidden="true">✓</span>
              <p>
                The backend created a Test Mode order. Payment is not considered successful
                until the backend verifies it.
              </p>
            </div>

            <button
              className="btn btn--primary btn--lg btn--full"
              disabled={paymentBusy}
              onClick={() => openRazorpayCheckout(order)}
            >
              {paymentBusy ? "Opening Razorpay..." : "Open Razorpay checkout"}
            </button>

            <p className="pricing-note">
              Attempt {order.payment_attempts}/{order.max_attempts}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

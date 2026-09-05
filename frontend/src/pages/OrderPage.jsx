import { useCallback, useEffect, useState } from "react";
import { useSession } from "../contexts/SessionContext";
import { api, ApiError } from "../api/client";
import { money, loadRazorpayScript } from "../utils/razorpay";
import { StatusBadge } from "../components/StatusBadge";
import { navigate } from "../router/router";
import { Spinner } from "../components/Spinner";

// eslint-disable-next-line no-unused-vars
export function OrderPage({ orderId: _orderId }) {
  const {
    sessionId,
    razorpayKeyId,
    order, setOrder,
    payment, setPayment,
    setAudit,
    refreshSession,
  } = useSession();

  const [paymentBusy, setPaymentBusy] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(!order);

  // If we land here directly (e.g., via browser refresh), fetch session
  useEffect(() => {
    if (order) return;
    refreshSession().finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openRazorpayCheckout = useCallback(async (currentOrder) => {
    if (!currentOrder) return;
    setError("");
    setPaymentBusy(true);

    try {
      await loadRazorpayScript();

      const key =
        razorpayKeyId ||
        payment?.razorpay_key_id ||
        currentOrder?.razorpay_key_id;

      if (!key) throw new Error("Razorpay public key unavailable.");
      if (!currentOrder.razorpay_order_id) throw new Error("No Razorpay order ID.");

      const options = {
        key,
        amount:
          currentOrder.amount_paise ??
          Math.round(Number(currentOrder.total_amount) * 100),
        currency: currentOrder.currency || "INR",
        name: currentOrder.merchant || "GlowCart",
        description: `GlowCart demo order #${currentOrder.id}`,
        order_id: currentOrder.razorpay_order_id,

        handler: async (response) => {
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
          } catch (err) {
            setError(err instanceof ApiError ? err.detail : "Payment verification failed.");
          } finally {
            setPaymentBusy(false);
          }
        },

        modal: { ondismiss: () => setPaymentBusy(false) },
        theme: { color: "#635BFF" },
      };

      const razorpay = new window.Razorpay(options);

      let failureReported = false;
      razorpay.on("payment.failed", async () => {
        if (failureReported) return;
        failureReported = true;
        try {
          const result = await api.reportPaymentFailed(sessionId);
          setOrder(result.order ?? null);
          setPayment(result.payment ?? null);
          await refreshSession();
        } catch (err) {
          setError(err instanceof ApiError ? err.detail : "Recovery info could not be loaded.");
        } finally {
          setPaymentBusy(false);
        }
      });

      razorpay.open();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open Razorpay Checkout.");
      setPaymentBusy(false);
    }
  }, [sessionId, razorpayKeyId, payment, setOrder, setPayment, refreshSession]);

  const retryPayment = useCallback(async () => {
    setError("");
    setPaymentBusy(true);
    try {
      const response = await api.sendChat(sessionId, "retry payment");
      if (response.order !== undefined) setOrder(response.order ?? null);
      if (response.payment !== undefined) setPayment(response.payment ?? null);
      if (response.audit?.length) setAudit(response.audit);

      if (response.open_checkout && response.order) {
        await openRazorpayCheckout(response.order);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't retry payment.");
    } finally {
      setPaymentBusy(false);
    }
  }, [sessionId, setOrder, setPayment, setAudit, openRazorpayCheckout]);

  const createPaymentLink = useCallback(async () => {
    setError("");
    setPaymentBusy(true);
    try {
      const response = await api.createPaymentLink(sessionId);
      if (response.order !== undefined) setOrder(response.order ?? null);
      if (response.payment !== undefined) setPayment(response.payment ?? null);
      await refreshSession();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't create payment link.");
    } finally {
      setPaymentBusy(false);
    }
  }, [sessionId, setOrder, setPayment, refreshSession]);

  if (loading) {
    return (
      <div className="page page--loading">
        <Spinner size={32} />
        <span>Loading order...</span>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="page">
        <div className="page__inner page__inner--narrow">
          <p>Order not found.</p>
          <button className="btn btn--primary" onClick={() => navigate("/shop")}>
            Back to Shop
          </button>
        </div>
      </div>
    );
  }

  const isPaid = order.status === "PAID";
  const isFailed = order.status === "PAYMENT_FAILED" || order.status === "PAYMENT_RECOVERY";
  const isPending = order.status === "PAYMENT_PENDING";
  const remaining = order.attempts_remaining ?? 0;

  return (
    <div className="page page--order">
      <div className="page__inner page__inner--narrow">
        {error && (
          <div className="error-banner" role="alert">
            <span aria-hidden="true">!</span>
            <p>{error}</p>
            <button onClick={() => setError("")} aria-label="Dismiss">×</button>
          </div>
        )}

        {/* SUCCESS */}
        {isPaid && (
          <div className="order-status order-status--success">
            <div className="order-status__mark order-status__mark--success" aria-hidden="true">✓</div>
            <span className="eyebrow">PAYMENT VERIFIED</span>
            <h1>Payment successful</h1>
            <p>Your Razorpay payment was verified by the backend. Your order is confirmed.</p>

            <div className="order-details">
              <div className="order-details__row">
                <span>Order ID</span>
                <strong>#{order.id}</strong>
              </div>
              <div className="order-details__row">
                <span>Amount</span>
                <strong>{money(order.total_amount)}</strong>
              </div>
              <div className="order-details__row">
                <span>Status</span>
                <StatusBadge status={order.status} />
              </div>
              {order.razorpay_payment_id && (
                <div className="order-details__row">
                  <span>Payment ID</span>
                  <strong className="mono">{order.razorpay_payment_id}</strong>
                </div>
              )}
            </div>

            <div className="order-cta-row">
              <button className="btn btn--primary" onClick={() => navigate("/shop")}>
                Continue shopping
              </button>
              <button className="btn btn--secondary" onClick={() => navigate("/activity")}>
                View activity
              </button>
            </div>
          </div>
        )}

        {/* FAILURE / RECOVERY */}
        {isFailed && (
          <div className="order-status order-status--failure">
            <div className="order-status__mark order-status__mark--failure" aria-hidden="true">!</div>
            <span className="eyebrow">PAYMENT RECOVERY</span>
            <h1>Payment didn&apos;t go through</h1>
            <p>
              The order has <strong>not</strong> been marked as paid. No successful payment is
              being claimed.
            </p>

            <div className="order-details">
              <div className="order-details__row">
                <span>Order ID</span>
                <strong>#{order.id}</strong>
              </div>
              <div className="order-details__row">
                <span>Amount</span>
                <strong>{money(order.total_amount)}</strong>
              </div>
              <div className="order-details__row">
                <span>Recovery attempts remaining</span>
                <strong>{remaining}</strong>
              </div>
            </div>

            {/* AI recovery decision explanation */}
            <div className="recovery-reasoning">
              <h2 className="recovery-reasoning__title">AI recovery decision</h2>
              <p>
                The previous payment attempt failed, so the system is allowing another
                bounded attempt. Maximum recovery attempts are enforced — the agent will
                not retry indefinitely.
              </p>
            </div>

            {remaining > 0 ? (
              <div className="recovery-actions">
                <button
                  className="btn btn--primary"
                  disabled={paymentBusy}
                  onClick={retryPayment}
                >
                  {paymentBusy ? "Retrying..." : "Try payment again"}
                </button>
                <button
                  className="btn btn--secondary"
                  disabled={paymentBusy}
                  onClick={createPaymentLink}
                >
                  Use payment link instead
                </button>
              </div>
            ) : (
              <div className="recovery-exhausted">
                <strong>No more attempts available.</strong>
                <p>Maximum recovery attempts have been reached for this order.</p>
              </div>
            )}

            {/* Payment link if available */}
            {order.payment_link_url && (
              <div className="payment-link-card">
                <span className="eyebrow">RECOVERY OPTION</span>
                <h3>Razorpay payment link ready</h3>
                <p>This is a Test Mode link. Payment is not confirmed until you complete it.</p>
                <a
                  href={order.payment_link_url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn--primary btn--full"
                >
                  Open payment link ↗
                </a>
              </div>
            )}

            <div className="order-cta-row">
              <button className="btn btn--secondary" onClick={() => navigate("/activity")}>
                View activity
              </button>
            </div>
          </div>
        )}

        {/* PAYMENT PENDING */}
        {isPending && (
          <div className="order-status">
            <span className="eyebrow">PAYMENT PENDING</span>
            <h1>Continue with Razorpay</h1>
            <p>
              The backend created a Test Mode order. Payment is not considered successful until
              the backend verifies it.
            </p>

            <div className="order-details">
              <div className="order-details__row">
                <span>Order ID</span>
                <strong>#{order.id}</strong>
              </div>
              <div className="order-details__row">
                <span>Amount</span>
                <strong>{money(order.total_amount)}</strong>
              </div>
              <div className="order-details__row">
                <span>Attempts</span>
                <strong>{order.payment_attempts}/{order.max_attempts}</strong>
              </div>
            </div>

            <button
              className="btn btn--primary btn--lg btn--full"
              disabled={paymentBusy}
              onClick={() => openRazorpayCheckout(order)}
            >
              {paymentBusy ? "Opening Razorpay..." : "Open Razorpay checkout"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

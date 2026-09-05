import { useCallback } from "react";
import { useSession } from "../contexts/SessionContext";
import { api, ApiError } from "../api/client";
import { CartItem } from "../components/CartItem";
import { EmptyState } from "../components/EmptyState";
import { money } from "../utils/razorpay";
import { navigate } from "../router/router";
import { useState } from "react";
import { Toast } from "../components/Toast";

export function CartPage() {
  const {
    sessionId,
    cart, setCart,
    refreshSession,
  } = useSession();

  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const [error, setError] = useState("");

  const updateItem = useCallback(async (itemId, quantity) => {
    setError("");
    setBusy(true);
    try {
      const updated = await api.updateCartItem(sessionId, itemId, quantity);
      setCart(updated);
      await refreshSession();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't update cart.");
    } finally {
      setBusy(false);
    }
  }, [sessionId, setCart, refreshSession]);

  const removeItem = useCallback(async (itemId) => {
    setError("");
    setBusy(true);
    try {
      const updated = await api.removeCartItem(sessionId, itemId);
      setCart(updated);
      await refreshSession();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't remove item.");
    } finally {
      setBusy(false);
    }
  }, [sessionId, setCart, refreshSession]);

  const isEmpty = !cart?.items?.length;

  return (
    <div className="page page--cart">
      <Toast message={toast?.msg} type={toast?.type} onDismiss={() => setToast(null)} />

      <div className="page__inner">
        <div className="page-header">
          <h1>Your cart</h1>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            <span aria-hidden="true">!</span>
            <p>{error}</p>
            <button onClick={() => setError("")} aria-label="Dismiss">×</button>
          </div>
        )}

        {isEmpty ? (
          <EmptyState
            title="Your cart is empty."
            subtitle="Let AI help you find something."
            action={
              <button className="btn btn--primary" onClick={() => navigate("/shop")}>
                Start shopping
              </button>
            }
          />
        ) : (
          <div className="cart-layout">
            <div className="cart-layout__items">
              <h2 className="cart-layout__heading">Items</h2>
              {cart.items.map((item) => (
                <CartItem
                  key={item.id}
                  item={item}
                  onUpdate={updateItem}
                  onRemove={removeItem}
                  busy={busy}
                />
              ))}
            </div>

            <div className="cart-layout__summary">
              <div className="cart-summary-card">
                <h2 className="cart-summary-card__title">Order summary</h2>

                <div className="cart-summary-card__row">
                  <span>Items</span>
                  <span>{cart.item_count ?? 0}</span>
                </div>
                <div className="cart-summary-card__row">
                  <span>Subtotal</span>
                  <strong>{money(cart.subtotal)}</strong>
                </div>
                <div className="cart-summary-card__row cart-summary-card__row--total">
                  <span>Total</span>
                  <strong>{money(cart.total)}</strong>
                </div>

                {cart.pricing_note && (
                  <p className="pricing-note">{cart.pricing_note}</p>
                )}

                <button
                  className="btn btn--primary btn--full"
                  disabled={busy}
                  onClick={() => navigate("/checkout")}
                >
                  Continue to checkout →
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";
import { useSession } from "../contexts/SessionContext";
import { api, ApiError } from "../api/client";
import { CompareTable } from "../components/CompareTable";
import { EmptyState } from "../components/EmptyState";
import { Toast } from "../components/Toast";
import { money } from "../utils/razorpay";
import { navigate } from "../router/router";

export function ComparePage() {
  const { sessionId, setCart, refreshSession } = useSession();

  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cartBusy, setCartBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const [error, setError] = useState("");

  // Load last comparison from session on mount
  useEffect(() => {
    api.getSession(sessionId)
      .then((data) => {
        if (data.comparison) setComparison(data.comparison);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sessionId]);

  const addToCart = useCallback(async (productId) => {
    setCartBusy(true);
    try {
      const updated = await api.addToCart(sessionId, productId, 1);
      setCart(updated);
      await refreshSession();
      setToast({ msg: "Product added to cart.", type: "success" });
      setTimeout(() => navigate("/cart"), 1200);
    } catch (err) {
      setToast({
        msg: err instanceof ApiError ? err.detail : "Couldn't add to cart.",
        type: "error",
      });
    } finally {
      setCartBusy(false);
    }
  }, [sessionId, setCart, refreshSession]);

  // Trigger "compare all" by sending a chat message
  const triggerCompareAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.sendChat(sessionId, "compare all of them");
      if (result.comparison) {
        setComparison(result.comparison);
      } else if (result.message) {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Comparison failed.");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Derive winner and alternates from comparison
  const products = comparison?.products?.length
    ? comparison.products
    : [comparison?.left, comparison?.right].filter(Boolean);

  const winner = comparison
    ? products.find((p) => p?.id === comparison.recommended_id)
    : null;

  const bestValue = comparison?.best_value_id
    ? products.find((p) => p?.id === comparison.best_value_id)
    : null;

  const highestRated = comparison?.highest_rated_id
    ? products.find((p) => p?.id === comparison.highest_rated_id)
    : null;

  return (
    <div className="page page--compare">
      <Toast message={toast?.msg} type={toast?.type} onDismiss={() => setToast(null)} />

      <div className="page__inner">
        <div className="page-header">
          <div>
            <span className="eyebrow">SIDE BY SIDE</span>
            <h1>Compare products</h1>
            {products.length > 0 && (
              <p className="page-header__sub">
                Comparing {products.length} product{products.length !== 1 ? "s" : ""} from your last search
              </p>
            )}
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {products.length > 0 && (
              <button
                className="btn btn--secondary"
                onClick={triggerCompareAll}
                disabled={loading}
              >
                Compare all {products.length > 0 ? `(${products.length})` : ""}
              </button>
            )}
            <button className="btn btn--secondary" onClick={() => navigate("/shop")}>
              Back to shopping
            </button>
          </div>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            <p>{error}</p>
            <button onClick={() => setError("")} aria-label="Dismiss">×</button>
          </div>
        )}

        {loading ? (
          <div className="page--loading">
            <span>Loading comparison…</span>
          </div>
        ) : comparison ? (
          <>
            {/* Multi-product table */}
            <CompareTable
              comparison={comparison}
              onAdd={cartBusy ? null : addToCart}
            />

            {/* "Why this one?" section */}
            {winner && (
              <div className="compare-why">
                <h2 className="compare-why__title">
                  Best overall — {winner.name.split(",")[0]}
                </h2>
                <p className="compare-why__body">
                  {comparison.summary ||
                    "The AI evaluated price, rating, review volume, and stored review evidence."}
                </p>

                {/* Grounded reason bullets */}
                <div className="compare-why__reasons">
                  {winner.rating != null && (
                    <div className="compare-why__reason">
                      ✓ {winner.rating.toFixed(1)}★ catalog rating
                    </div>
                  )}
                  {winner.review_count > 0 && (
                    <div className="compare-why__reason">
                      ✓ {winner.review_count} stored reviews
                    </div>
                  )}
                  {winner.price && (
                    <div className="compare-why__reason">
                      ✓ Priced at {money(winner.price)} (synthetic demo pricing)
                    </div>
                  )}
                  {winner.available !== false && (
                    <div className="compare-why__reason">
                      ✓ Available in inventory
                    </div>
                  )}
                  {(winner.pros || []).slice(0, 2).map((pro) => (
                    <div key={pro} className="compare-why__reason">✓ {pro}</div>
                  ))}
                </div>

                <button
                  className="btn btn--primary"
                  disabled={cartBusy}
                  onClick={() => addToCart(winner.id)}
                >
                  {cartBusy ? "Adding…" : `Add ${winner.name.split(",")[0]} to cart`}
                </button>
              </div>
            )}

            {/* Alternatives */}
            {(bestValue || highestRated) && (
              <div className="compare-alternates">
                <h3 className="compare-alternates__title">Also worth considering</h3>
                <div className="compare-alternates__grid">
                  {bestValue && bestValue.id !== winner?.id && (
                    <div className="compare-alt-card">
                      <span className="compare-badge compare-badge--value">Best Value</span>
                      <div className="compare-alt-card__name">{bestValue.name.split(",")[0]}</div>
                      <div className="compare-alt-card__meta">
                        {money(bestValue.price)} · ★ {bestValue.rating?.toFixed(1) ?? "—"}
                      </div>
                      <button
                        className="btn btn--secondary btn--sm"
                        onClick={() => addToCart(bestValue.id)}
                        disabled={cartBusy}
                      >
                        Add to cart
                      </button>
                    </div>
                  )}
                  {highestRated && highestRated.id !== winner?.id && highestRated.id !== bestValue?.id && (
                    <div className="compare-alt-card">
                      <span className="compare-badge compare-badge--rated">Top Rated</span>
                      <div className="compare-alt-card__name">{highestRated.name.split(",")[0]}</div>
                      <div className="compare-alt-card__meta">
                        {money(highestRated.price)} · ★ {highestRated.rating?.toFixed(1) ?? "—"}
                      </div>
                      <button
                        className="btn btn--secondary btn--sm"
                        onClick={() => addToCart(highestRated.id)}
                        disabled={cartBusy}
                      >
                        Add to cart
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        ) : (
          <EmptyState
            title="Nothing to compare yet."
            subtitle="Search for products in Shop, then ask the AI to compare them."
            action={
              <button className="btn btn--primary" onClick={() => navigate("/shop")}>
                Go to Shop
              </button>
            }
          />
        )}
      </div>
    </div>
  );
}

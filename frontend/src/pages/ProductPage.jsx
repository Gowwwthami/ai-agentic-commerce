import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useSession } from "../contexts/SessionContext";
import { money } from "../utils/razorpay";
import { navigate } from "../router/router";
import { Spinner } from "../components/Spinner";
import { Toast } from "../components/Toast";

export function ProductPage({ productId }) {
  const { sessionId, setCart, refreshSession } = useSession();

  const [product, setProduct] = useState(null);
  const [reviews, setReviews] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cartBusy, setCartBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!productId) return;

    Promise.allSettled([
      fetch(`${import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"}/products/${productId}`).then((r) => r.json()),
      fetch(`${import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"}/products/${productId}/reviews`).then((r) => r.json()),
    ]).then(([prodRes, revRes]) => {
      if (prodRes.status === "fulfilled") setProduct(prodRes.value);
      else setError("Product not found.");
      if (revRes.status === "fulfilled") setReviews(revRes.value);
      setLoading(false);
    });

    return () => { setLoading(true); };
  }, [productId]);

  const addToCart = async () => {
    setCartBusy(true);
    try {
      const updated = await api.addToCart(sessionId, Number(productId), 1);
      setCart(updated);
      await refreshSession();
      setToast({ msg: `${product?.name ?? "Product"} added to your cart.`, type: "success" });
    } catch (err) {
      setToast({ msg: err instanceof ApiError ? err.detail : "Couldn't add to cart.", type: "error" });
    } finally {
      setCartBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="page page--loading">
        <Spinner size={32} />
        <span>Loading product...</span>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="page">
        <div className="page__inner">
          <button className="back-link" onClick={() => navigate("/shop")}>← Back to Shop</button>
          <div className="error-state">
            <p>{error || "Product not found."}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page page--product">
      <Toast
        message={toast?.msg}
        type={toast?.type}
        onDismiss={() => setToast(null)}
      />

      <div className="page__inner">
        <button className="back-link" onClick={() => navigate("/shop")}>← Back to Shop</button>

        <div className="product-detail">
          {/* Image */}
          <div className="product-detail__image-wrap">
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.name}
                className="product-detail__image"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                  e.currentTarget.nextElementSibling?.classList.remove("hidden");
                }}
              />
            ) : null}
            <div className={`product-detail__fallback${product.image_url ? " hidden" : ""}`}>GC</div>
          </div>

          {/* Info */}
          <div className="product-detail__info">
            <div className="product-detail__brand">{product.brand || "GlowCart"}</div>
            <h1 className="product-detail__name">{product.name}</h1>

            <div className="product-detail__price">{money(product.price)}</div>

            <div className="product-detail__stats">
              <span>★ {product.rating?.toFixed(1) ?? "—"}</span>
              <span>{product.review_count ?? 0} reviews</span>
              <span className={product.available === false ? "status--danger" : "status--success"}>
                {product.available === false ? "Unavailable" : "In stock"}
              </span>
            </div>

            {product.description && (
              <p className="product-detail__desc">{product.description}</p>
            )}

            <div className="product-detail__actions">
              <button
                className="btn btn--primary btn--lg"
                disabled={cartBusy || product.available === false}
                onClick={addToCart}
              >
                {cartBusy ? "Adding..." : "Add to Cart"}
              </button>
              <button
                className="btn btn--secondary"
                onClick={() => navigate("/compare")}
              >
                Compare
              </button>
            </div>

            <p className="pricing-note">
              Prices shown are synthetic demo prices. Review/rating evidence is derived from the
              project dataset.
            </p>
          </div>
        </div>

        {/* Why AI recommends */}
        {product.why && (
          <section className="product-section">
            <h2 className="product-section__title">Why AI recommends this</h2>
            <p className="product-section__body">{product.why}</p>
          </section>
        )}

        {/* Evidence */}
        <section className="product-section">
          <h2 className="product-section__title">Review evidence</h2>
          <p className="review-disclosure">
            Review evidence from the catalog. Prices shown are synthetic demo prices.
          </p>

          <div className="review-evidence">
            {product.pros?.length > 0 && (
              <div className="review-evidence__block">
                <span className="mini-label label--pos">Positive signals</span>
                {product.pros.map((item) => (
                  <div key={item} className="evidence-item evidence-item--pos">✓ {item}</div>
                ))}
              </div>
            )}
            {product.cons?.length > 0 && (
              <div className="review-evidence__block">
                <span className="mini-label label--neg">Negative signals</span>
                {product.cons.map((item) => (
                  <div key={item} className="evidence-item evidence-item--neg">! {item}</div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Sample reviews */}
        {reviews?.reviews?.length > 0 && (
          <section className="product-section">
            <h2 className="product-section__title">What reviewers say</h2>
            <div className="reviews-list">
              {reviews.reviews.slice(0, 6).map((review, i) => (
                <div key={i} className="review-item">
                  <div className="review-item__header">
                    <span className="review-item__rating">★ {review.rating?.toFixed(1) ?? "—"}</span>
                    {review.title && <strong className="review-item__title">{review.title}</strong>}
                  </div>
                  {review.text && <p className="review-item__text">{review.text}</p>}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

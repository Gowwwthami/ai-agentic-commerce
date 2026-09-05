import { money } from "../utils/razorpay";
import { navigate } from "../router/router";

export function ProductCard({ product, index, onAdd, onCompare, busy }) {
  const image = product.image_url;

  return (
    <article className="product-card">
      <div className="product-card__image-wrap">
        {image ? (
          <img
            src={image}
            alt={product.name}
            className="product-card__image"
            onError={(e) => {
              e.currentTarget.style.display = "none";
              e.currentTarget.nextElementSibling?.classList.remove("hidden");
            }}
          />
        ) : null}
        <div className={`product-card__fallback${image ? " hidden" : ""}`}>
          <span>GC</span>
        </div>
        {index === 0 && (
          <span className="product-card__top-badge">Top pick</span>
        )}
      </div>

      <div className="product-card__body">
        <div className="product-card__brand">{product.brand || "GlowCart"}</div>
        <h3 className="product-card__name">{product.name}</h3>

        <div className="product-card__meta">
          <strong className="product-card__price">{money(product.price)}</strong>
          <span className="product-card__rating">★ {product.rating?.toFixed(1) ?? "—"}</span>
          <span className="product-card__reviews">{product.review_count ?? 0} reviews</span>
          {product.available === false && (
            <span className="product-card__unavail">Unavailable</span>
          )}
        </div>

        {product.why && (
          <p className="product-card__why">
            <span>Why this pick</span>
            {product.why}
          </p>
        )}

        <div className="product-card__evidence">
          {product.pros?.slice(0, 2).map((pro) => (
            <span className="evidence-pos" key={pro}>✓ {pro}</span>
          ))}
          {product.cons?.slice(0, 2).map((con) => (
            <span className="evidence-neg" key={con}>! {con}</span>
          ))}
        </div>

        <div className="product-card__actions">
          <button
            className="btn btn--primary"
            disabled={busy || product.available === false}
            onClick={() => onAdd(product.id)}
          >
            {busy ? "Adding..." : "Add to cart"}
          </button>

          <button
            className="btn btn--secondary"
            onClick={() => onCompare && onCompare(product.id)}
          >
            Compare
          </button>

          <button
            className="btn-text"
            onClick={() => navigate(`/product/${product.id}`)}
          >
            View details
          </button>
        </div>
      </div>
    </article>
  );
}

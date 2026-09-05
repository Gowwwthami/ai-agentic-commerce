import { money } from "../utils/razorpay";

/**
 * CompareTable — renders a side-by-side comparison of N products.
 * Accepts the new multi-product comparison shape from the backend:
 *   { products: [...], recommended_id, best_value_id, highest_rated_id, budget_id, summary, reasons }
 * Also handles the legacy pairwise shape { left, right, ... } for backward compat.
 */
export function CompareTable({ comparison, onAdd }) {
  if (!comparison) return null;

  // Normalise to a products array
  const products = comparison.products?.length
    ? comparison.products
    : [comparison.left, comparison.right].filter(Boolean);

  if (!products.length) return null;

  const {
    recommended_id,
    best_value_id,
    highest_rated_id,
    budget_id,
  } = comparison;

  function badge(product) {
    if (product.id === recommended_id) return { label: "AI Pick", cls: "compare-badge compare-badge--winner" };
    if (product.id === best_value_id)  return { label: "Best Value", cls: "compare-badge compare-badge--value" };
    if (product.id === highest_rated_id) return { label: "Top Rated", cls: "compare-badge compare-badge--rated" };
    if (product.id === budget_id)      return { label: "Budget", cls: "compare-badge compare-badge--budget" };
    return null;
  }

  return (
    <div className="compare-table-wrap">
      <div
        className="compare-table-scroll"
        role="region"
        aria-label="Product comparison table"
      >
        <table className="compare-table">
          <thead>
            <tr>
              <th className="compare-table__attr-col" scope="col">Feature</th>
              {products.map((p) => {
                const b = badge(p);
                const isWinner = p.id === recommended_id;
                return (
                  <th
                    key={p.id}
                    scope="col"
                    className={`compare-table__product-col${isWinner ? " compare-table__product-col--winner" : ""}`}
                  >
                    {b && <span className={b.cls}>{b.label}</span>}
                    <div className="compare-table__product-name">{p.name}</div>
                    <div className="compare-table__product-brand">{p.brand || "GlowCart"}</div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {/* Price */}
            <tr>
              <td className="compare-table__label">Price</td>
              {products.map((p) => (
                <td key={p.id} className={`compare-table__cell${p.id === budget_id ? " compare-table__cell--highlight" : ""}`}>
                  <strong>{money(p.price)}</strong>
                </td>
              ))}
            </tr>
            {/* Rating */}
            <tr>
              <td className="compare-table__label">Rating</td>
              {products.map((p) => (
                <td key={p.id} className={`compare-table__cell${p.id === highest_rated_id ? " compare-table__cell--highlight" : ""}`}>
                  <strong>★ {p.rating?.toFixed(1) ?? "—"}</strong>
                </td>
              ))}
            </tr>
            {/* Reviews */}
            <tr>
              <td className="compare-table__label">Reviews</td>
              {products.map((p) => (
                <td key={p.id} className="compare-table__cell">
                  {p.review_count ?? 0}
                </td>
              ))}
            </tr>
            {/* Availability */}
            <tr>
              <td className="compare-table__label">Available</td>
              {products.map((p) => (
                <td key={p.id} className="compare-table__cell">
                  {p.available === false
                    ? <span className="compare-no">✗ No</span>
                    : <span className="compare-yes">✓ Yes</span>}
                </td>
              ))}
            </tr>
            {/* AI Score */}
            <tr>
              <td className="compare-table__label">AI Score</td>
              {products.map((p) => (
                <td key={p.id} className={`compare-table__cell${p.id === recommended_id ? " compare-table__cell--highlight" : ""}`}>
                  <strong>{p.score?.toFixed ? (p.score * 100).toFixed(0) : "—"}</strong>
                  <span className="compare-table__score-label">/100</span>
                </td>
              ))}
            </tr>
            {/* Strengths */}
            <tr>
              <td className="compare-table__label">Strengths</td>
              {products.map((p) => (
                <td key={p.id} className="compare-table__cell compare-table__cell--evidence">
                  {p.pros?.length
                    ? p.pros.slice(0, 3).map((pro) => (
                        <div key={pro} className="compare-evidence-item compare-evidence-item--pos">✓ {pro}</div>
                      ))
                    : <span className="compare-na">—</span>}
                </td>
              ))}
            </tr>
            {/* Watch-outs */}
            <tr>
              <td className="compare-table__label">Watch-outs</td>
              {products.map((p) => (
                <td key={p.id} className="compare-table__cell compare-table__cell--evidence">
                  {p.cons?.length
                    ? p.cons.slice(0, 2).map((con) => (
                        <div key={con} className="compare-evidence-item compare-evidence-item--neg">! {con}</div>
                      ))
                    : <span className="compare-na">—</span>}
                </td>
              ))}
            </tr>
            {/* Add to cart row */}
            {onAdd && (
              <tr>
                <td className="compare-table__label"></td>
                {products.map((p) => {
                  const isWinner = p.id === recommended_id;
                  return (
                    <td key={p.id} className="compare-table__cell">
                      <button
                        className={`btn ${isWinner ? "btn--primary" : "btn--secondary"} btn--sm`}
                        onClick={() => onAdd(p.id)}
                        aria-label={`Add ${p.name} to cart`}
                      >
                        Add to cart
                      </button>
                    </td>
                  );
                })}
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {comparison.summary && (
        <div className="compare-summary">
          <span className="compare-summary__icon" aria-hidden="true">✦</span>
          <p>{comparison.summary}</p>
        </div>
      )}
    </div>
  );
}

import { useEffect, useState, useMemo } from "react";
import { useSession } from "../contexts/SessionContext";
import { api } from "../api/client";
import { Spinner } from "../components/Spinner";
import { money } from "../utils/razorpay";

// ---------------------------------------------------------------------------
// Event classification
// ---------------------------------------------------------------------------

const FILTER_DEFS = [
  { id: "all",            label: "All" },
  { id: "shopping",       label: "Shopping" },
  { id: "recommendations",label: "Recommendations" },
  { id: "comparisons",    label: "Comparisons" },
  { id: "checkout",       label: "Checkout" },
  { id: "payments",       label: "Payments" },
  { id: "system",         label: "System" },
];

function classifyEvent(event) {
  const t = (event.event_type || "").toLowerCase();
  if (t === "user_shopping_request")            return "shopping";
  if (t === "product_search")                    return "shopping";
  if (t === "recommendation_generated")          return "recommendations";
  if (t === "product_compared")                  return "comparisons";
  if (t === "cart_changed" || t === "product_selected") return "shopping";
  if (t === "checkout_started")                  return "checkout";
  if (t === "confirmation_received")             return "checkout";
  if (t === "razorpay_order_created" || t === "payment_attempt") return "payments";
  if (t === "payment_verified" || t === "payment_success") return "payments";
  if (t === "payment_failure" || t === "payment_failed")   return "payments";
  if (t === "recovery_attempt")                  return "payments";
  if (t === "payment_link_created" || t === "payment_link_failed") return "payments";
  if (t === "razorpay_error")                    return "payments";
  return "system";
}

// ---------------------------------------------------------------------------
// Summary stats
// ---------------------------------------------------------------------------

function computeSummary(events) {
  let shopping = 0, reco = 0, compare = 0, checkout = 0, payment = 0;
  for (const e of events) {
    const cat = classifyEvent(e);
    if (cat === "shopping")         shopping++;
    else if (cat === "recommendations") reco++;
    else if (cat === "comparisons") compare++;
    else if (cat === "checkout")    checkout++;
    else if (cat === "payments")    payment++;
  }
  return { total: events.length, shopping, reco, compare, checkout, payment };
}

// ---------------------------------------------------------------------------
// Deduplication / grouping — collapse consecutive identical event_types
// to reduce visual noise without deleting records
// ---------------------------------------------------------------------------

function collapseEvents(events) {
  const result = [];
  for (const ev of events) {
    const prev = result[result.length - 1];
    // Merge consecutive identical search/recommendation pairs
    if (
      prev &&
      prev.event_type === ev.event_type &&
      ["recommendation_generated", "product_compared"].includes(ev.event_type)
    ) {
      // Keep the most recent (first in desc order, which is the newer one)
      // by replacing the grouped item with the latest
      prev._merged = (prev._merged || 1) + 1;
      continue;
    }
    result.push({ ...ev, _merged: 1 });
  }
  return result;
}

// ---------------------------------------------------------------------------
// Event card renderers
// ---------------------------------------------------------------------------

function fmt(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

function EventIcon({ type }) {
  const t = (type || "").toLowerCase();
  if (t === "user_shopping_request")       return <span className="ae-icon ae-icon--shop" aria-hidden="true">🔍</span>;
  if (t === "product_search")              return <span className="ae-icon ae-icon--search" aria-hidden="true">🗂</span>;
  if (t === "recommendation_generated")    return <span className="ae-icon ae-icon--reco" aria-hidden="true">⭐</span>;
  if (t === "product_compared")            return <span className="ae-icon ae-icon--compare" aria-hidden="true">⚖</span>;
  if (t === "cart_changed")               return <span className="ae-icon ae-icon--cart" aria-hidden="true">🛍</span>;
  if (t === "checkout_started")           return <span className="ae-icon ae-icon--checkout" aria-hidden="true">📋</span>;
  if (t === "confirmation_received")      return <span className="ae-icon ae-icon--confirm" aria-hidden="true">✅</span>;
  if (t === "razorpay_order_created")     return <span className="ae-icon ae-icon--pay" aria-hidden="true">💳</span>;
  if (t === "payment_attempt")            return <span className="ae-icon ae-icon--pay" aria-hidden="true">🔄</span>;
  if (t.includes("payment_verif") || t.includes("payment_success")) return <span className="ae-icon ae-icon--paid" aria-hidden="true">✓</span>;
  if (t.includes("payment_fail") || t.includes("payment_failure"))  return <span className="ae-icon ae-icon--fail" aria-hidden="true">✗</span>;
  if (t.includes("recovery"))            return <span className="ae-icon ae-icon--recovery" aria-hidden="true">↩</span>;
  if (t.includes("payment_link"))        return <span className="ae-icon ae-icon--link" aria-hidden="true">🔗</span>;
  return <span className="ae-icon" aria-hidden="true">·</span>;
}

function statusVariant(type) {
  const t = (type || "").toLowerCase();
  if (t.includes("paid") || t.includes("verified") || t.includes("success") || t === "confirmation_received") return "success";
  if (t.includes("fail") || t.includes("error"))  return "danger";
  if (t.includes("recovery") || t.includes("retry")) return "warning";
  return "neutral";
}

function RecoCard({ event }) {
  const meta = event.metadata || {};
  const ids = meta.product_ids || [];
  const topName = event.description?.match(/Top pick: (.+)/)?.[1] || "";

  return (
    <div className={`ae-card ae-card--${statusVariant(event.event_type)}`}>
      <div className="ae-card__header">
        <EventIcon type={event.event_type} />
        <div className="ae-card__title-group">
          <span className="ae-card__eyebrow">RECOMMENDATION</span>
          <h3 className="ae-card__title">
            Ranked {ids.length || "several"} product{ids.length !== 1 ? "s" : ""}
          </h3>
        </div>
        <time className="ae-card__time">{fmt(event.created_at)}</time>
      </div>
      {topName && (
        <div className="ae-card__body">
          <div className="ae-detail-row">
            <span className="ae-detail-label">Top recommendation</span>
            <span className="ae-detail-value ae-detail-value--strong">{topName}</span>
          </div>
          <div className="ae-reco-reasons">
            <span className="ae-mini-label">Why this recommendation?</span>
            <div className="ae-reco-reason-list">
              {meta.constraints?.max_price && (
                <span className="ae-reason-chip">✓ Within budget ₹{meta.constraints.max_price}</span>
              )}
              {meta.constraints?.min_rating && (
                <span className="ae-reason-chip">✓ Min rating {meta.constraints.min_rating}★ required</span>
              )}
              <span className="ae-reason-chip">✓ Rating + review volume scored</span>
              <span className="ae-reason-chip">✓ Review evidence evaluated</span>
              <span className="ae-reason-chip">✓ Availability checked</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SearchCard({ event }) {
  const meta = event.metadata || {};
  const q = meta.query;
  const maxP = meta.max_price;
  const minR = meta.min_rating;

  return (
    <div className="ae-card ae-card--neutral">
      <div className="ae-card__header">
        <EventIcon type={event.event_type} />
        <div className="ae-card__title-group">
          <span className="ae-card__eyebrow">CATALOG SEARCH</span>
          <h3 className="ae-card__title">
            {q ? `Searched: "${q}"` : "Full catalog search"}
          </h3>
        </div>
        <time className="ae-card__time">{fmt(event.created_at)}</time>
      </div>
      {(maxP || minR) && (
        <div className="ae-card__body">
          {maxP && (
            <div className="ae-detail-row">
              <span className="ae-detail-label">Max price filter</span>
              <span className="ae-detail-value">{money(maxP)}</span>
            </div>
          )}
          {minR && (
            <div className="ae-detail-row">
              <span className="ae-detail-label">Min rating filter</span>
              <span className="ae-detail-value">{minR}★ and above</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function UserRequestCard({ event }) {
  const msg = event.description?.replace(/^User said:\s*/i, "") || event.description;
  return (
    <div className="ae-card ae-card--neutral ae-card--user">
      <div className="ae-card__header">
        <EventIcon type={event.event_type} />
        <div className="ae-card__title-group">
          <span className="ae-card__eyebrow">SHOPPING REQUEST</span>
          <h3 className="ae-card__title">User asked</h3>
        </div>
        <time className="ae-card__time">{fmt(event.created_at)}</time>
      </div>
      {msg && (
        <div className="ae-card__body">
          <blockquote className="ae-quote">{msg}</blockquote>
        </div>
      )}
    </div>
  );
}

function CompareCard({ event }) {
  const meta = event.metadata || {};
  const count = meta.product_count || meta.ids?.length || 2;
  const recName = event.description?.match(/Recommended:\s*(.+?)\.?$/)?.[1] || "";

  return (
    <div className="ae-card ae-card--neutral">
      <div className="ae-card__header">
        <EventIcon type={event.event_type} />
        <div className="ae-card__title-group">
          <span className="ae-card__eyebrow">COMPARISON</span>
          <h3 className="ae-card__title">Compared {count} product{count !== 1 ? "s" : ""}</h3>
        </div>
        <time className="ae-card__time">{fmt(event.created_at)}</time>
      </div>
      {recName && (
        <div className="ae-card__body">
          <div className="ae-detail-row">
            <span className="ae-detail-label">AI recommendation</span>
            <span className="ae-detail-value ae-detail-value--strong">{recName}</span>
          </div>
          <div className="ae-reco-reasons">
            <span className="ae-mini-label">Factors considered</span>
            <div className="ae-reco-reason-list">
              <span className="ae-reason-chip">✓ Rating score</span>
              <span className="ae-reason-chip">✓ Review volume</span>
              <span className="ae-reason-chip">✓ Price fit</span>
              <span className="ae-reason-chip">✓ Review evidence</span>
              <span className="ae-reason-chip">✓ Availability</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CheckoutCard({ event }) {
  const isConfirm = event.event_type === "confirmation_received";
  const amtMatch = event.description?.match(/₹([\d,.]+)/);
  const amt = amtMatch ? amtMatch[0] : null;

  return (
    <div className={`ae-card ae-card--${isConfirm ? "success" : "neutral"}`}>
      <div className="ae-card__header">
        <EventIcon type={event.event_type} />
        <div className="ae-card__title-group">
          <span className="ae-card__eyebrow">
            {isConfirm ? "EXPLICIT CONFIRMATION" : "CHECKOUT"}
          </span>
          <h3 className="ae-card__title">
            {isConfirm ? "User explicitly confirmed checkout" : `Checkout started${amt ? ` for ${amt}` : ""}`}
          </h3>
        </div>
        <time className="ae-card__time">{fmt(event.created_at)}</time>
      </div>
      {isConfirm && (
        <div className="ae-card__body">
          <div className="ae-security-note">
            Payment request was only created after this explicit confirmation.
            No charge was authorised before this point.
          </div>
        </div>
      )}
    </div>
  );
}

function PaymentCard({ event }) {
  const t = (event.event_type || "").toLowerCase();
  const meta = event.metadata || {};
  const variant = statusVariant(event.event_type);

  const isVerified = t.includes("verif") || t.includes("success");
  const isFailed   = t.includes("fail");
  const isCreated  = t === "razorpay_order_created";
  const isAttempt  = t === "payment_attempt";
  const isRecovery = t === "recovery_attempt";
  const isLink     = t.includes("payment_link");

  let eyebrow = "PAYMENT";
  if (isVerified) eyebrow = "PAYMENT VERIFIED";
  else if (isFailed) eyebrow = "PAYMENT FAILED";
  else if (isCreated) eyebrow = "RAZORPAY ORDER CREATED";
  else if (isRecovery) eyebrow = "RECOVERY";
  else if (isLink) eyebrow = "PAYMENT LINK";

  return (
    <div className={`ae-card ae-card--${variant}`}>
      <div className="ae-card__header">
        <EventIcon type={event.event_type} />
        <div className="ae-card__title-group">
          <span className="ae-card__eyebrow">{eyebrow}</span>
          <h3 className="ae-card__title">
            {event.description?.split(".")[0] || eyebrow}
          </h3>
        </div>
        <time className="ae-card__time">{fmt(event.created_at)}</time>
      </div>
      <div className="ae-card__body">
        {meta.razorpay_order_id && (
          <div className="ae-detail-row">
            <span className="ae-detail-label">Order ID</span>
            <span className="ae-detail-value ae-mono">{meta.razorpay_order_id}</span>
          </div>
        )}
        {meta.amount && (
          <div className="ae-detail-row">
            <span className="ae-detail-label">Amount</span>
            <span className="ae-detail-value">{money(meta.amount)}</span>
          </div>
        )}
        {isAttempt && (
          <div className="ae-security-note">
            Payment success is not claimed until Razorpay verification.
          </div>
        )}
        {isFailed && (
          <div className="ae-security-note ae-security-note--danger">
            No successful charge is being claimed. The order was not marked as paid.
          </div>
        )}
        {isVerified && (
          <div className="ae-security-note ae-security-note--success">
            Payment was independently verified by the backend. Order marked PAID.
          </div>
        )}
      </div>
    </div>
  );
}

function CartCard({ event }) {
  return (
    <div className="ae-card ae-card--neutral">
      <div className="ae-card__header">
        <EventIcon type={event.event_type} />
        <div className="ae-card__title-group">
          <span className="ae-card__eyebrow">CART</span>
          <h3 className="ae-card__title">{event.description || "Cart updated"}</h3>
        </div>
        <time className="ae-card__time">{fmt(event.created_at)}</time>
      </div>
    </div>
  );
}

function DefaultCard({ event }) {
  const title = (event.event_type || "event")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());

  return (
    <div className="ae-card ae-card--neutral">
      <div className="ae-card__header">
        <EventIcon type={event.event_type} />
        <div className="ae-card__title-group">
          <span className="ae-card__eyebrow">SYSTEM</span>
          <h3 className="ae-card__title">{title}</h3>
        </div>
        <time className="ae-card__time">{fmt(event.created_at)}</time>
      </div>
      {event.description && (
        <div className="ae-card__body">
          <p className="ae-card__desc">{event.description}</p>
        </div>
      )}
    </div>
  );
}

function EventCard({ event }) {
  const t = (event.event_type || "").toLowerCase();
  if (t === "user_shopping_request")    return <UserRequestCard event={event} />;
  if (t === "product_search")           return <SearchCard event={event} />;
  if (t === "recommendation_generated") return <RecoCard event={event} />;
  if (t === "product_compared")         return <CompareCard event={event} />;
  if (t === "cart_changed" || t === "product_selected") return <CartCard event={event} />;
  if (t === "checkout_started" || t === "confirmation_received") return <CheckoutCard event={event} />;
  if (
    t.includes("razorpay") ||
    t.includes("payment") ||
    t === "recovery_attempt"
  ) return <PaymentCard event={event} />;
  return <DefaultCard event={event} />;
}

// ---------------------------------------------------------------------------
// Payment lifecycle section — render as a connected flow when present
// ---------------------------------------------------------------------------

function PaymentLifecycle({ events }) {
  const paymentEvents = events.filter((e) => {
    const t = (e.event_type || "").toLowerCase();
    return (
      t === "checkout_started" ||
      t === "confirmation_received" ||
      t.includes("razorpay") ||
      t.includes("payment") ||
      t === "recovery_attempt"
    );
  });

  if (!paymentEvents.length) return null;

  const LIFECYCLE_STEPS = [
    { key: "checkout_started",     label: "Checkout Started",       status: "done" },
    { key: "confirmation_received",label: "User Confirmed",         status: "done" },
    { key: "razorpay_order_created",label: "Payment Order Created", status: "done" },
    { key: "payment_attempt",      label: "Payment Attempted",      status: "done" },
    { key: "payment_verified",     label: "Verified — PAID",        status: "success" },
    { key: "payment_failure",      label: "Payment Failed",         status: "danger" },
    { key: "recovery_attempt",     label: "Recovery Offered",       status: "warning" },
  ];

  const reached = new Set(paymentEvents.map((e) => e.event_type));

  return (
    <div className="ae-lifecycle">
      <h3 className="ae-lifecycle__title">Payment lifecycle</h3>
      <div className="ae-lifecycle__steps">
        {LIFECYCLE_STEPS.filter((s) => reached.has(s.key)).map((step) => (
          <div key={step.key} className={`ae-lifecycle__step ae-lifecycle__step--${step.status}`}>
            <span className="ae-lifecycle__step-dot" />
            <span className="ae-lifecycle__step-label">{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ActivityPage() {
  const { sessionId, audit, setAudit } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");

  useEffect(() => {
    api.getAudit(sessionId)
      .then((data) => {
        setAudit(Array.isArray(data) ? data : (data.events ?? []));
      })
      .catch(() => setError("Couldn't load activity."))
      .finally(() => setLoading(false));
  }, [sessionId, setAudit]);

  // Events are returned newest-first from backend; display newest first
  const allEvents = useMemo(() => audit ?? [], [audit]);

  const summary = useMemo(() => computeSummary(allEvents), [allEvents]);

  const filteredEvents = useMemo(() => {
    if (activeFilter === "all") return allEvents;
    return allEvents.filter((e) => classifyEvent(e) === activeFilter);
  }, [allEvents, activeFilter]);

  const collapsedEvents = useMemo(() => collapseEvents(filteredEvents), [filteredEvents]);

  const hasPaymentEvents = allEvents.some((e) => {
    const t = (e.event_type || "").toLowerCase();
    return t.includes("payment") || t.includes("razorpay") || t === "checkout_started";
  });

  return (
    <div className="page page--activity">
      <div className="page__inner">
        {/* Header */}
        <div className="ae-header">
          <div>
            <span className="eyebrow">TRANSPARENCY</span>
            <h1 className="ae-header__title">AI Activity &amp; Audit Trail</h1>
            <p className="ae-header__sub">
              See what the AI searched, recommended, compared, and executed —
              with a clear record of why and what happened.
            </p>
          </div>
        </div>

        {/* Summary chips */}
        {!loading && allEvents.length > 0 && (
          <div className="ae-summary-strip">
            <div className="ae-summary-chip">
              <strong>{summary.total}</strong>
              <span>Total activities</span>
            </div>
            {summary.shopping > 0 && (
              <div className="ae-summary-chip">
                <strong>{summary.shopping}</strong>
                <span>Shopping</span>
              </div>
            )}
            {summary.reco > 0 && (
              <div className="ae-summary-chip">
                <strong>{summary.reco}</strong>
                <span>Recommendations</span>
              </div>
            )}
            {summary.compare > 0 && (
              <div className="ae-summary-chip">
                <strong>{summary.compare}</strong>
                <span>Comparisons</span>
              </div>
            )}
            {(summary.checkout + summary.payment) > 0 && (
              <div className="ae-summary-chip ae-summary-chip--payment">
                <strong>{summary.checkout + summary.payment}</strong>
                <span>Checkout / Payment</span>
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="error-banner" role="alert">
            <p>{error}</p>
            <button onClick={() => setError("")} aria-label="Dismiss">×</button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="page--loading">
            <Spinner size={28} />
            <span>Loading activity…</span>
          </div>
        )}

        {/* Empty */}
        {!loading && !allEvents.length && (
          <div className="ae-empty">
            <p>No activity yet.</p>
            <p>Start shopping to see the AI&apos;s actions here.</p>
          </div>
        )}

        {/* Filters + Timeline */}
        {!loading && allEvents.length > 0 && (
          <>
            {/* Filter tabs */}
            <div className="ae-filters" role="tablist" aria-label="Filter activities">
              {FILTER_DEFS.filter((f) => {
                if (f.id === "all") return true;
                if (f.id === "system") return allEvents.some((e) => classifyEvent(e) === "system");
                if (f.id === "shopping") return summary.shopping > 0;
                if (f.id === "recommendations") return summary.reco > 0;
                if (f.id === "comparisons") return summary.compare > 0;
                if (f.id === "checkout") return summary.checkout > 0;
                if (f.id === "payments") return summary.payment > 0;
                return false;
              }).map((f) => (
                <button
                  key={f.id}
                  role="tab"
                  aria-selected={activeFilter === f.id}
                  className={`ae-filter-btn${activeFilter === f.id ? " ae-filter-btn--active" : ""}`}
                  onClick={() => setActiveFilter(f.id)}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Payment lifecycle visual (only in All or Payments view) */}
            {(activeFilter === "all" || activeFilter === "payments") && hasPaymentEvents && (
              <PaymentLifecycle events={allEvents} />
            )}

            {/* Timeline */}
            {collapsedEvents.length === 0 ? (
              <div className="ae-empty">
                <p>No {activeFilter} events in this session.</p>
              </div>
            ) : (
              <div className="ae-timeline" role="feed" aria-label="Activity timeline">
                {collapsedEvents.map((event, idx) => (
                  <div key={`${event.id ?? idx}-${event.event_type}`} className="ae-timeline__entry">
                    <div className="ae-timeline__connector" aria-hidden="true" />
                    <EventCard event={event} />
                    {event._merged > 1 && (
                      <div className="ae-merged-note">
                        + {event._merged - 1} similar event{event._merged > 2 ? "s" : ""} grouped
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

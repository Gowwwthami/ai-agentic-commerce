/**
 * StatusBadge — small colored pill for order/payment statuses.
 */
export function StatusBadge({ status }) {
  const label = (status || "").replaceAll("_", " ").replace(/\b\w/g, (l) => l.toUpperCase());

  let cls = "badge";
  if (status === "PAID") cls += " badge--success";
  else if (status === "PAYMENT_FAILED" || status === "PAYMENT_RECOVERY") cls += " badge--danger";
  else if (status === "PAYMENT_PENDING") cls += " badge--warning";
  else cls += " badge--neutral";

  return <span className={cls}>{label}</span>;
}

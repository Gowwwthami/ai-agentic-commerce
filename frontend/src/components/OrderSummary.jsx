import { money } from "../utils/razorpay";

export function OrderSummary({ order }) {
  if (!order) return null;

  return (
    <div className="order-summary">
      <h3 className="order-summary__title">Order summary</h3>
      <div className="order-summary__items">
        {order.items?.map((item) => (
          <div className="order-summary__line" key={`${item.product_id}-${item.quantity}`}>
            <span>{item.name} × {item.quantity}</span>
            <strong>{money(item.line_total)}</strong>
          </div>
        ))}
      </div>
      <div className="order-summary__total">
        <span>Total</span>
        <strong>{money(order.total_amount)}</strong>
      </div>
      {order.merchant && (
        <p className="order-summary__note">
          {order.merchant} · Synthetic demo INR pricing · Razorpay Test Mode
        </p>
      )}
    </div>
  );
}

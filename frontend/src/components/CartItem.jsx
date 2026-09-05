import { money } from "../utils/razorpay";

export function CartItem({ item, onUpdate, onRemove, busy }) {
  return (
    <div className="cart-item">
      <div className="cart-item__image">
        {item.image_url ? (
          <img src={item.image_url} alt="" />
        ) : (
          <span>GC</span>
        )}
      </div>

      <div className="cart-item__info">
        <strong>{item.name}</strong>
        <span>{money(item.unit_price)} each</span>

        <div className="qty-control" role="group" aria-label={`Quantity for ${item.name}`}>
          <button
            disabled={busy}
            onClick={() => onUpdate(item.id, Math.max(0, item.quantity - 1))}
            aria-label={`Decrease quantity of ${item.name}`}
          >
            −
          </button>
          <span>{item.quantity}</span>
          <button
            disabled={busy || item.quantity >= item.inventory}
            onClick={() => onUpdate(item.id, item.quantity + 1)}
            aria-label={`Increase quantity of ${item.name}`}
          >
            +
          </button>
        </div>
      </div>

      <div className="cart-item__right">
        <strong>{money(item.line_total)}</strong>
        <button
          className="cart-item__remove"
          disabled={busy}
          onClick={() => onRemove(item.id)}
        >
          Remove
        </button>
      </div>
    </div>
  );
}

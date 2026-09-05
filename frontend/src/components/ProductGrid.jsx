import { ProductCard } from "./ProductCard";

export function ProductGrid({ products, onAdd, onCompare, busy }) {
  if (!products?.length) return null;

  return (
    <div className="product-grid">
      {products.map((product, index) => (
        <ProductCard
          key={product.id}
          product={product}
          index={index}
          onAdd={onAdd}
          onCompare={onCompare}
          busy={busy}
        />
      ))}
    </div>
  );
}

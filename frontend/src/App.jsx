import { useEffect } from "react";
import { useRouter, matchRoute, navigate } from "./router/router";
import { useSession } from "./contexts/SessionContext";
import { AppShell } from "./components/AppShell";
import { ShopPage } from "./pages/ShopPage";
import { ProductPage } from "./pages/ProductPage";
import { ComparePage } from "./pages/ComparePage";
import { CartPage } from "./pages/CartPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { OrderPage } from "./pages/OrderPage";
import { ActivityPage } from "./pages/ActivityPage";
import "./App.css";

const ROUTES = [
  { pattern: "/shop", component: () => <ShopPage /> },
  { pattern: "/product/:id", component: ({ id }) => <ProductPage productId={id} /> },
  { pattern: "/compare", component: () => <ComparePage /> },
  { pattern: "/cart", component: () => <CartPage /> },
  { pattern: "/checkout", component: () => <CheckoutPage /> },
  { pattern: "/order/:id", component: ({ id }) => <OrderPage orderId={id} /> },
  { pattern: "/activity", component: () => <ActivityPage /> },
];

function resolveRoute(path) {
  for (const route of ROUTES) {
    const { matched, params } = matchRoute(route.pattern, path);
    if (matched) return { component: route.component, params };
  }
  return null;
}

export default function App() {
  const { initialized } = useSession();
  const path = useRouter();

  // Normalize root and unknown paths → /shop (synchronous check)
  const match = resolveRoute(path);

  // Redirect immediately via useEffect to avoid render loops
  useEffect(() => {
    if (!match) navigate("/shop");
  }, [path, match]);

  if (!initialized) {
    return (
      <div className="app-loading">
        <div className="loading-logo" aria-hidden="true">G</div>
        <strong>Starting GlowCart...</strong>
        <span>Connecting to your shopping session</span>
      </div>
    );
  }

  const PageContent = match ? match.component(match.params) : (
    <div className="page page--loading">
      <span>Redirecting to shop...</span>
    </div>
  );

  return (
    <AppShell currentPath={path}>
      {PageContent}
    </AppShell>
  );
}

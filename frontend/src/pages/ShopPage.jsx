import { useCallback, useState } from "react";
import { useSession } from "../contexts/SessionContext";
import { api, ApiError } from "../api/client";
import { ChatPanel } from "../components/ChatPanel";
import { ProductGrid } from "../components/ProductGrid";
import { CompareTable } from "../components/CompareTable";
import { navigate } from "../router/router";

export function ShopPage() {
  const {
    sessionId,
    initialized,
    setCart,
    setOrder,
    setPayment,
    setAudit,
    refreshSession,
  } = useSession();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [products, setProducts] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [sending, setSending] = useState(false);
  const [cartBusy, setCartBusy] = useState(false);
  const [error, setError] = useState("");

  const sendMessage = useCallback(async (text) => {
    const message = (text ?? input).trim();
    if (!message || sending || !initialized) return;

    setError("");
    setInput("");
    setMessages((c) => [...c, { role: "user", text: message }]);
    setSending(true);

    try {
      const response = await api.sendChat(sessionId, message);

      setMessages((c) => [...c, {
        role: "assistant",
        text: response.message || "I completed that action.",
      }]);

      if (response.products?.length) {
        setProducts(response.products);
      } else if (response.actions?.includes("search")) {
        setProducts([]);
      }

      setComparison(response.comparison ?? null);
      if (response.cart !== undefined) setCart(response.cart ?? null);
      if (response.order !== undefined) setOrder(response.order ?? null);
      if (response.payment !== undefined) setPayment(response.payment ?? null);
      if (response.audit?.length) setAudit(response.audit);

      // If the agent signals checkout should open, navigate to checkout
      if (response.open_checkout && response.order) {
        navigate("/checkout");
      }
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "I couldn't reach the shopping agent.";
      setMessages((c) => [...c, { role: "assistant", text: detail }]);
      setError(detail);
    } finally {
      setSending(false);
    }
  }, [input, sending, initialized, sessionId, setCart, setOrder, setPayment, setAudit]);

  const addToCart = useCallback(async (productId) => {
    setError("");
    setCartBusy(true);
    try {
      const updated = await api.addToCart(sessionId, productId, 1);
      setCart(updated);
      await refreshSession();
      const product = products.find((p) => p.id === productId);
      setMessages((c) => [...c, {
        role: "assistant",
        text: product ? `${product.name} is now in your cart.` : "Product added to your cart.",
      }]);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't add to cart.");
    } finally {
      setCartBusy(false);
    }
  }, [sessionId, products, setCart, refreshSession]);

  const compareProducts = useCallback(async (productId) => {
    const index = products.findIndex((p) => p.id === productId);
    if (index < 0) {
      navigate("/compare");
      return;
    }
    const ordinal = index === 0 ? "first" : index === 1 ? "second" : "third";
    await sendMessage(`compare the ${ordinal} two`);
    // After comparison loads, navigate to /compare
    // The comparison state is already set on sendMessage return
  }, [products, sendMessage]);

  if (!initialized) {
    return (
      <div className="app-loading">
        <div className="loading-logo" aria-hidden="true">G</div>
        <strong>Starting GlowCart...</strong>
        <span>Connecting to your shopping session</span>
      </div>
    );
  }

  return (
    <div className="page page--shop">
      {/* Hero */}
      <section className="shop-hero">
        <div className="shop-hero__inner">
          <span className="eyebrow">PERSONAL SHOPPER</span>
          <h1 className="shop-hero__title">Shop smarter with AI.</h1>
          <p className="shop-hero__sub">
            Tell me what you&apos;re looking for. I&apos;ll compare products,
            weigh review evidence, and help you choose.
          </p>
          <div className="trust-strip">
            <span>Evidence-backed</span>
            <span>Explicit payment gate</span>
            <span>Bounded recovery</span>
          </div>
        </div>
      </section>

      <div className="shop-layout">
        {/* Chat */}
        <section className="shop-layout__chat">
          <ChatPanel
            messages={messages}
            sending={sending}
            input={input}
            onInput={setInput}
            onSend={() => sendMessage(input)}
            onPrompt={sendMessage}
            error={error}
            onDismissError={() => setError("")}
          />
        </section>

        {/* Products */}
        {products.length > 0 && (
          <section className="shop-layout__results">
            <div className="section-header">
              <div>
                <span className="eyebrow">MATCHES</span>
                <h2>My strongest picks</h2>
              </div>
              <span className="count-pill">{products.length} options</span>
            </div>
            <ProductGrid
              products={products}
              onAdd={addToCart}
              onCompare={compareProducts}
              busy={cartBusy}
            />
          </section>
        )}

        {/* Comparison */}
        {comparison && (
          <section className="shop-layout__comparison">
            <div className="section-header">
              <div>
                <span className="eyebrow">SIDE BY SIDE</span>
                <h2>Which one fits better?</h2>
              </div>
            </div>
            <CompareTable comparison={comparison} onAdd={addToCart} />
          </section>
        )}
      </div>
    </div>
  );
}

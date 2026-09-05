import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../api/client";
import { getOrCreateSessionId } from "../utils/session";

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [sessionId] = useState(() => getOrCreateSessionId());
  const [initialized, setInitialized] = useState(false);
  const [sessionData, setSessionData] = useState(null);
  const [razorpayKeyId, setRazorpayKeyId] = useState(null);

  // Shared state lifted here so pages share it across navigation
  const [cart, setCart] = useState(null);
  const [order, setOrder] = useState(null);
  const [payment, setPayment] = useState(null);
  const [audit, setAudit] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const [session, keyResp] = await Promise.allSettled([
          api.getSession(sessionId),
          api.getPaymentKey(),
        ]);

        if (cancelled) return;

        if (session.status === "fulfilled") {
          const data = session.value;
          setSessionData(data);
          setCart(data.cart ?? null);
          setOrder(data.order ?? null);
          setPayment(data.payment ?? null);
          setAudit(data.audit ?? []);
        }
        if (keyResp.status === "fulfilled") {
          setRazorpayKeyId(keyResp.value.key_id ?? null);
        }
      } catch {
        // non-fatal
      } finally {
        if (!cancelled) setInitialized(true);
      }
    }

    init();
    return () => { cancelled = true; };
  }, [sessionId]);

  const refreshSession = useCallback(async () => {
    const data = await api.getSession(sessionId);
    setSessionData(data);
    setCart(data.cart ?? null);
    setOrder(data.order ?? null);
    setPayment(data.payment ?? null);
    setAudit(data.audit ?? []);
    return data;
  }, [sessionId]);

  const refreshCart = useCallback(async () => {
    const data = await api.getCart(sessionId);
    setCart(data);
    return data;
  }, [sessionId]);

  return (
    <SessionContext.Provider value={{
      sessionId,
      initialized,
      sessionData,
      razorpayKeyId,
      cart, setCart,
      order, setOrder,
      payment, setPayment,
      audit, setAudit,
      refreshSession,
      refreshCart,
    }}>
      {children}
    </SessionContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}

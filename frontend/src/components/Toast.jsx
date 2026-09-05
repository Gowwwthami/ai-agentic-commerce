import { useEffect } from "react";

/**
 * Toast notification — auto-dismisses after `duration` ms.
 * type: "success" | "error" | "info"
 */
export function Toast({ message, type = "info", onDismiss, duration = 3500 }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDismiss, duration);
    return () => clearTimeout(t);
  }, [message, duration, onDismiss]);

  if (!message) return null;

  return (
    <div className={`toast toast--${type}`} role="alert" aria-live="polite">
      <span className="toast__msg">{message}</span>
      <button className="toast__close" onClick={onDismiss} aria-label="Dismiss">×</button>
    </div>
  );
}

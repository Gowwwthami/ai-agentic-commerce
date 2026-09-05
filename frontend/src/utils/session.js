const SESSION_KEY = "glowcart_session_id";

/**
 * Returns the persisted session ID from localStorage, creating and
 * storing a new UUID v4 if none exists.  Idempotent — safe to call
 * many times in the same browser session.
 */
export function getOrCreateSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

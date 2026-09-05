/**
 * Lightweight SPA router using window.history.pushState + popstate.
 * No external dependency.
 */

import { useState, useEffect } from "react";

export function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function useRouter() {
  const [path, setPath] = useState(() => window.location.pathname);

  useEffect(() => {
    const handler = () => setPath(window.location.pathname);
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  return path;
}

/**
 * Match a route pattern against the current path.
 * Supports :param segments.
 * Returns { matched: bool, params: {} }
 */
export function matchRoute(pattern, path) {
  const patternParts = pattern.split("/").filter(Boolean);
  const pathParts = path.split("/").filter(Boolean);

  if (patternParts.length !== pathParts.length) return { matched: false, params: {} };

  const params = {};
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(":")) {
      params[patternParts[i].slice(1)] = decodeURIComponent(pathParts[i]);
    } else if (patternParts[i] !== pathParts[i]) {
      return { matched: false, params: {} };
    }
  }
  return { matched: true, params };
}

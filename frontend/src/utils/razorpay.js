/**
 * Lazily loads the Razorpay Checkout script.
 * Safe to call multiple times — resolves immediately if already loaded.
 */
export function loadRazorpayScript() {
  if (window.Razorpay) return Promise.resolve(true);

  if (window.__glowcartRazorpayPromise) {
    return window.__glowcartRazorpayPromise;
  }

  window.__glowcartRazorpayPromise = new Promise((resolve, reject) => {
    const src = "https://checkout.razorpay.com/v1/checkout.js";
    const existing = document.querySelector(`script[src="${src}"]`);

    const finish = () => {
      if (window.Razorpay) {
        resolve(true);
      } else {
        reject(new Error("Razorpay Checkout loaded without exposing the SDK."));
      }
    };

    if (existing) {
      existing.addEventListener("load", finish, { once: true });
      existing.addEventListener(
        "error",
        () => reject(new Error("Could not load Razorpay Checkout.")),
        { once: true },
      );
      // The script may already have finished before this call.
      if (window.Razorpay) finish();
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = finish;
    script.onerror = () =>
      reject(new Error("Could not load Razorpay Checkout. Check your internet connection."));
    document.body.appendChild(script);
  }).catch((error) => {
    window.__glowcartRazorpayPromise = null;
    throw error;
  });

  return window.__glowcartRazorpayPromise;
}

/** Format a number as Indian Rupees */
export function money(value) {
  const amount = Number(value ?? 0);
  return `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

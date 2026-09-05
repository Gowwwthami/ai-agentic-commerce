/**
 * Lazily loads the Razorpay Checkout script.
 * Safe to call multiple times — resolves immediately if already loaded.
 */
export function loadRazorpayScript() {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }

    const existing = document.querySelector(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]',
    );

    if (existing) {
      existing.addEventListener("load", () => resolve(true), { once: true });
      existing.addEventListener(
        "error",
        () => reject(new Error("Could not load Razorpay Checkout.")),
        { once: true },
      );
      return;
    }

    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () =>
      reject(new Error("Could not load Razorpay Checkout. Check your internet connection."));

    document.body.appendChild(script);
  });
}

/** Format a number as Indian Rupees */
export function money(value) {
  const amount = Number(value ?? 0);
  return `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

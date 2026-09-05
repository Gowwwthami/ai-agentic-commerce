import { Navbar } from "./Navbar";

export function AppShell({ currentPath, children }) {
  return (
    <div className="app-shell">
      <Navbar currentPath={currentPath} />
      <main className="app-shell__main">{children}</main>
      <footer className="app-footer">
        <span>GlowCart · AI Agentic Commerce</span>
        <span>Demo store · Synthetic INR pricing · Razorpay Test Mode</span>
      </footer>
    </div>
  );
}

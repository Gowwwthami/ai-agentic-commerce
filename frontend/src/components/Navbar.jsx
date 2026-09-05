import { useSession } from "../contexts/SessionContext";
import { navigate } from "../router/router";

export function Navbar({ currentPath }) {
  const { cart } = useSession();
  const cartCount = cart?.item_count ?? 0;

  function navTo(path) {
    navigate(path);
  }

  const links = [
    { label: "Shop", path: "/shop" },
    { label: "Compare", path: "/compare" },
    { label: "Cart", path: "/cart", badge: cartCount || null },
    { label: "Activity", path: "/activity" },
  ];

  return (
    <header className="navbar">
      <div className="navbar__inner">
        {/* Brand */}
        <button
          className="navbar__brand"
          onClick={() => navTo("/shop")}
          aria-label="Go to shop"
        >
          <div className="navbar__logo" aria-hidden="true">G</div>
          <div className="navbar__brand-text">
            <strong>GlowCart</strong>
            <span>AI Shopping</span>
          </div>
        </button>

        {/* Nav links */}
        <nav className="navbar__links" aria-label="Main navigation">
          {links.map(({ label, path, badge }) => {
            const active = currentPath === path || currentPath.startsWith(path + "/");
            return (
              <button
                key={path}
                className={`navbar__link${active ? " navbar__link--active" : ""}`}
                onClick={() => navTo(path)}
                aria-current={active ? "page" : undefined}
              >
                {label}
                {badge ? <span className="navbar__badge">{badge}</span> : null}
              </button>
            );
          })}
        </nav>

        {/* Right badge */}
        <div className="navbar__right">
          <span className="ai-badge">AI-powered commerce</span>
        </div>
      </div>
    </header>
  );
}

import { Compass, Map, Menu, X, WifiOff } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";

import { DemoNotice } from "./DemoNotice";

export function Layout() {
  const [online, setOnline] = useState(navigator.onLine);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink className="brand" to="/" aria-label="PahadPath home">
          <span className="brand-mark" aria-hidden="true">
            <Compass size={21} strokeWidth={1.8} />
          </span>
          <span className="brand-name">pahad<span>path</span></span>
        </NavLink>
        <button className="mobile-menu-toggle" type="button" aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
        <nav className={`main-nav${menuOpen ? " is-open" : ""}`} aria-label="Main navigation">
          <NavLink to="/plan" onClick={() => setMenuOpen(false)}>Plan a trip</NavLink>
          <NavLink to="/saved" onClick={() => setMenuOpen(false)}><Map size={16} /> Saved trips</NavLink>
          <a href="/#how-it-works" onClick={() => setMenuOpen(false)}>A gentler way uphill</a>
          <NavLink className="nav-cta" to="/plan" onClick={() => setMenuOpen(false)}>Find a homestay</NavLink>
        </nav>
      </header>
      {!online && (
        <div className="offline-banner" role="status">
          <WifiOff size={16} /> You're offline. Saved plans are still here on this device.
        </div>
      )}
      <main id="main-content"><Outlet /></main>
      <footer className="site-footer">
        <NavLink className="footer-brand" to="/">pahadpath</NavLink>
        <span>A gentler way uphill.</span>
        <span><NavLink to="/plan">Plan a trip</NavLink> · <NavLink to="/saved">Saved trips</NavLink></span>
      </footer>
      <DemoNotice />
    </div>
  );
}

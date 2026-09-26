import Link from "next/link";
import type { ReactNode } from "react";

const nav = [
  { href: "/", label: "Terminal" },
  { href: "/markets", label: "Markets" },
  { href: "/velocity", label: "Velocity" },
  { href: "/ops", label: "Ops" },
  { href: "/architecture", label: "Architecture" },
];

export default function Shell({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand">EDGEATLAS</div>
          <div className="brand-sub">
            Prediction Market Intelligence
          </div>
        </div>

        <nav className="nav">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="nav-link"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div>SignalAtlas · Intelligence</div>
          <div>VelocityAtlas · Execution</div>
          <div>EdgeAtlas · Terminal</div>
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}

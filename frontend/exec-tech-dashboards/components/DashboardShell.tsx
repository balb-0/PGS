"use client";

import Link from "next/link";
import type { Route } from "next";
import { ReactNode, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

type Props = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

const nav: Array<{ href: Route; label: string }> = [
  { href: "/business", label: "Negócio" },
  { href: "/system-health", label: "Saúde" },
  { href: "/testing-gap", label: "Testes Restantes" },
];

const THEME_STORAGE_KEY = "asis-theme";
const THEME_TRANSITION_CLASS = "theme-animating";

export function DashboardShell({ title, subtitle, children }: Props) {
  const pathname = usePathname();
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    const initialTheme =
      storedTheme === "light" || storedTheme === "dark"
        ? storedTheme
        : window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";

    document.documentElement.setAttribute("data-theme", initialTheme);
    setTheme(initialTheme);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "light" ? "dark" : "light";
    document.documentElement.classList.add(THEME_TRANSITION_CLASS);
    document.documentElement.setAttribute("data-theme", nextTheme);
    window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    setTheme(nextTheme);

    window.setTimeout(() => {
      document.documentElement.classList.remove(THEME_TRANSITION_CLASS);
    }, 520);
  };

  return (
    <main className="page-wrap">
      <header className="topbar reveal">
        <div className="topbar-brand-wrap">
          <p className="topbar-kicker">ASIS Executive Console</p>
          <p className="topbar-brand">Navegação de Decisão</p>
        </div>
        <nav className="topbar-nav" aria-label="Navegação dos dashboards">
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={active ? "topbar-link is-active" : "topbar-link"}
                aria-current={active ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="topbar-actions">
          <button
            type="button"
            className="theme-toggle"
            data-theme-state={theme}
            onClick={toggleTheme}
            aria-label={`Alternar para tema ${theme === "light" ? "escuro" : "claro"}`}
          >
            <span className="theme-icon theme-icon-sun" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 1.8v2.4M12 19.8v2.4M22.2 12h-2.4M4.2 12H1.8M19.1 4.9l-1.7 1.7M6.6 17.4l-1.7 1.7M19.1 19.1l-1.7-1.7M6.6 6.6 4.9 4.9" />
              </svg>
            </span>
            <span className="theme-icon theme-icon-moon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M21 14.2A8.9 8.9 0 1 1 9.8 3a7.4 7.4 0 1 0 11.2 11.2Z" />
              </svg>
            </span>
            <span className="theme-toggle-track" aria-hidden="true">
              <span className="theme-toggle-thumb" />
            </span>
            <span className="theme-toggle-text">{theme === "light" ? "Modo Claro" : "Modo Escuro"}</span>
          </button>
        </div>
      </header>

      <header className="top-hero reveal">
        <div>
          <p className="eyebrow">Executive + Technical Intelligence</p>
          <h1>{title}</h1>
          <p className="subtitle">{subtitle}</p>
        </div>
        <p className="hero-context">Navegue entre Negócio, Saúde e Testes Restantes pela barra superior.</p>
      </header>
      <section className="content-grid">{children}</section>
    </main>
  );
}

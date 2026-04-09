"use client";

import Link from "next/link";
import type { Route } from "next";
import { ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

type Props = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

const nav: Array<{ href: Route; label: string }> = [
  { href: "/business", label: "Negócio" },
  { href: "/system-health", label: "Saúde" },
  { href: "/ai-search", label: "Busca IA" },
];

const THEME_STORAGE_KEY = "asis-theme";
const CONTRAST_STORAGE_KEY = "asis-contrast";
const SHORTCUTS_STORAGE_KEY = "asis-shortcuts";
const THEME_TRANSITION_CLASS = "theme-animating";
const CONTRAST_TRANSITION_CLASS = "contrast-animating";

type ContrastMode = "default" | "high";
type ShortcutAction = "goBusiness" | "goSystemHealth" | "goAISearch" | "focusFilters" | "openReport";
type Shortcuts = Record<ShortcutAction, string>;

const DEFAULT_SHORTCUTS: Shortcuts = {
  goBusiness: "Alt+1",
  goSystemHealth: "Alt+2",
  goAISearch: "Alt+3",
  focusFilters: "Alt+F",
  openReport: "Alt+E",
};

const SHORTCUT_LABELS: Record<ShortcutAction, string> = {
  goBusiness: "Abrir dashboard de Negócio",
  goSystemHealth: "Abrir dashboard de Saúde",
  goAISearch: "Abrir Busca IA",
  focusFilters: "Focar filtros globais",
  openReport: "Abrir exportação de relatório",
};

const SHORTCUT_OPTIONS = [
  "Alt+1",
  "Alt+2",
  "Alt+3",
  "Alt+4",
  "Alt+F",
  "Alt+E",
  "Alt+Q",
  "Ctrl+1",
  "Ctrl+2",
  "Ctrl+3",
  "Ctrl+F",
  "Ctrl+E",
  "Ctrl+Shift+F",
  "Ctrl+Shift+E",
];

function readStoredShortcuts() {
  try {
    const raw = window.localStorage.getItem(SHORTCUTS_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_SHORTCUTS;
    }

    const parsed = JSON.parse(raw) as Partial<Shortcuts>;
    return {
      goBusiness: parsed.goBusiness ?? DEFAULT_SHORTCUTS.goBusiness,
      goSystemHealth: parsed.goSystemHealth ?? DEFAULT_SHORTCUTS.goSystemHealth,
      goAISearch: parsed.goAISearch ?? DEFAULT_SHORTCUTS.goAISearch,
      focusFilters: parsed.focusFilters ?? DEFAULT_SHORTCUTS.focusFilters,
      openReport: parsed.openReport ?? DEFAULT_SHORTCUTS.openReport,
    };
  } catch {
    return DEFAULT_SHORTCUTS;
  }
}

function isTextInputTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
}

function matchShortcut(event: KeyboardEvent, shortcut: string) {
  const parts = shortcut
    .toLowerCase()
    .split("+")
    .map((item) => item.trim())
    .filter(Boolean);

  const requiredCtrl = parts.includes("ctrl");
  const requiredAlt = parts.includes("alt");
  const requiredShift = parts.includes("shift");
  const requiredMeta = parts.includes("meta");
  const key = parts.find((item) => !["ctrl", "alt", "shift", "meta"].includes(item));

  if (!key) {
    return false;
  }

  if (
    event.ctrlKey !== requiredCtrl ||
    event.altKey !== requiredAlt ||
    event.shiftKey !== requiredShift ||
    event.metaKey !== requiredMeta
  ) {
    return false;
  }

  return event.key.toLowerCase() === key;
}

export function DashboardShell({ title, subtitle, children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [contrast, setContrast] = useState<ContrastMode>("default");
  const [shortcuts, setShortcuts] = useState<Shortcuts>(DEFAULT_SHORTCUTS);
  const [shortcutStatus, setShortcutStatus] = useState("");
  const [isShortcutModalOpen, setIsShortcutModalOpen] = useState(false);

  useEffect(() => {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    const storedContrast = window.localStorage.getItem(CONTRAST_STORAGE_KEY);
    const initialTheme =
      storedTheme === "light" || storedTheme === "dark"
        ? storedTheme
        : window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";
    const initialContrast = storedContrast === "high" ? "high" : "default";

    document.documentElement.setAttribute("data-theme", initialTheme);
    document.documentElement.setAttribute("data-contrast", initialContrast);
    setTheme(initialTheme);
    setContrast(initialContrast);
    setShortcuts(readStoredShortcuts());
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

  const toggleContrast = () => {
    const nextContrast = contrast === "high" ? "default" : "high";
    document.documentElement.classList.add(CONTRAST_TRANSITION_CLASS);
    document.documentElement.setAttribute("data-contrast", nextContrast);
    window.localStorage.setItem(CONTRAST_STORAGE_KEY, nextContrast);
    setContrast(nextContrast);

    window.setTimeout(() => {
      document.documentElement.classList.remove(CONTRAST_TRANSITION_CLASS);
    }, 300);
  };

  const shortcutHint = useMemo(
    () =>
      `Atalhos: ${shortcuts.goBusiness} Negócio, ${shortcuts.goSystemHealth} Saúde, ${shortcuts.goAISearch} Busca IA, ${shortcuts.focusFilters} filtros, ${shortcuts.openReport} relatório.`,
    [shortcuts],
  );

  useEffect(() => {
    const runAction = (action: ShortcutAction) => {
      if (action === "goBusiness") {
        router.push("/business");
        return;
      }
      if (action === "goSystemHealth") {
        router.push("/system-health");
        return;
      }
      if (action === "goAISearch") {
        router.push("/ai-search");
        return;
      }
      if (action === "focusFilters") {
        document.getElementById("global-filter-primary")?.focus();
        return;
      }
      document.getElementById("report-builder-trigger")?.click();
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (isShortcutModalOpen) {
        return;
      }

      if (isTextInputTarget(event.target) && !event.altKey && !event.ctrlKey && !event.metaKey) {
        return;
      }

      const action = (Object.keys(shortcuts) as ShortcutAction[]).find((key) => matchShortcut(event, shortcuts[key]));
      if (!action) {
        return;
      }

      event.preventDefault();
      runAction(action);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isShortcutModalOpen, router, shortcuts]);

  useEffect(() => {
    if (!isShortcutModalOpen) {
      return;
    }

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsShortcutModalOpen(false);
      }
    };

    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [isShortcutModalOpen]);

  const updateShortcut = (action: ShortcutAction, nextShortcut: string) => {
    const duplicateAction = (Object.keys(shortcuts) as ShortcutAction[]).find(
      (key) => key !== action && shortcuts[key] === nextShortcut,
    );
    if (duplicateAction) {
      setShortcutStatus(`Atalho já usado por "${SHORTCUT_LABELS[duplicateAction]}".`);
      return;
    }

    const next = { ...shortcuts, [action]: nextShortcut };
    setShortcuts(next);
    window.localStorage.setItem(SHORTCUTS_STORAGE_KEY, JSON.stringify(next));
    setShortcutStatus(`Atalho atualizado para ${SHORTCUT_LABELS[action]}.`);
  };

  const restoreDefaultShortcuts = () => {
    setShortcuts(DEFAULT_SHORTCUTS);
    window.localStorage.setItem(SHORTCUTS_STORAGE_KEY, JSON.stringify(DEFAULT_SHORTCUTS));
    setShortcutStatus("Atalhos restaurados para o padrão.");
  };

  return (
    <main className="page-wrap">
      <a href="#dashboard-main-content" className="skip-link">
        Pular para conteúdo principal
      </a>
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
          <button
            type="button"
            className="ghost-action"
            onClick={toggleContrast}
            aria-pressed={contrast === "high"}
          >
            {contrast === "high" ? "Contraste padrão" : "Alto contraste"}
          </button>
          <button
            type="button"
            className="ghost-action"
            onClick={() => setIsShortcutModalOpen(true)}
            aria-haspopup="dialog"
            aria-label="Configurar atalhos de teclado"
          >
            Atalhos
          </button>
        </div>
      </header>

      <header className="top-hero reveal">
        <div>
          <p className="eyebrow">Executive + Technical Intelligence</p>
          <h1>{title}</h1>
          <p className="subtitle">{subtitle}</p>
        </div>
        <p className="hero-context">Navegue entre Negócio, Saúde e Busca IA pela barra superior.</p>
      </header>
      <p className="sr-only" aria-live="polite">{shortcutHint}</p>
      <section id="dashboard-main-content" className="content-grid" tabIndex={-1}>
        {children}
      </section>

      {isShortcutModalOpen ? (
        <div className="shortcut-modal-overlay" onClick={() => setIsShortcutModalOpen(false)}>
          <section
            className="shortcut-modal panel"
            role="dialog"
            aria-modal="true"
            aria-label="Configuração de atalhos"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="panel-head">
              <h3>Configurar atalhos</h3>
              <button type="button" className="ghost-action" onClick={() => setIsShortcutModalOpen(false)}>
                Fechar
              </button>
            </div>
            <p className="panel-inline-note">Use combinações únicas para evitar conflito na navegação.</p>
            <div className="shortcut-list">
              {(Object.keys(shortcuts) as ShortcutAction[]).map((action) => (
                <label key={action} className="shortcut-item">
                  <span>{SHORTCUT_LABELS[action]}</span>
                  <select
                    value={shortcuts[action]}
                    onChange={(event) => updateShortcut(action, event.target.value)}
                  >
                    {SHORTCUT_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <div className="shortcut-actions">
              <button type="button" className="ghost-action" onClick={restoreDefaultShortcuts}>
                Restaurar padrão
              </button>
            </div>
            <p className="search-meta" role="status">{shortcutStatus || " "}</p>
          </section>
        </div>
      ) : null}
    </main>
  );
}

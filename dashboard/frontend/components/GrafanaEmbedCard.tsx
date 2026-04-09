"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

type Props = {
  dashboardUid: string;
  panelId: number;
  title: string;
  narrative: string;
  from?: string;
  to?: string;
  refresh?: "off" | "15s" | "30s" | "1m";
  interpretation?: string[];
};

export function GrafanaEmbedCard({
  dashboardUid,
  panelId,
  title,
  narrative,
  from = "now-6h",
  to = "now",
  refresh = "15s",
  interpretation = [],
}: Props) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [grafanaTheme, setGrafanaTheme] = useState<"light" | "dark">("dark");
  const titleId = useId();
  const narrativeId = useId();
  const frameWrapRef = useRef<HTMLDivElement | null>(null);
  const modalRef = useRef<HTMLElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const previousFocusedRef = useRef<HTMLElement | null>(null);
  const baseUrl = process.env.NEXT_PUBLIC_GRAFANA_URL ?? "http://localhost:3000";
  const defaultTheme = process.env.NEXT_PUBLIC_GRAFANA_THEME === "light" ? "light" : "dark";

  useEffect(() => {
    const applyThemeFromDom = () => {
      const activeTheme = document.documentElement.getAttribute("data-theme");
      if (activeTheme === "light" || activeTheme === "dark") {
        setGrafanaTheme(activeTheme);
      } else {
        setGrafanaTheme(defaultTheme);
      }
    };

    applyThemeFromDom();
    const observer = new MutationObserver(applyThemeFromDom);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    return () => {
      observer.disconnect();
    };
  }, [defaultTheme]);

  useEffect(() => {
    const node = frameWrapRef.current;
    if (!node || isVisible) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "240px 0px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [isVisible]);

  const embedUrl = useMemo(() => {
    const params = new URLSearchParams({
      orgId: "1",
      from,
      to,
      panelId: String(panelId),
      theme: grafanaTheme,
    });
    if (refresh !== "off") {
      params.set("refresh", refresh);
    }

    return `${baseUrl}/d-solo/${dashboardUid}?${params.toString()}`;
  }, [baseUrl, dashboardUid, from, grafanaTheme, panelId, refresh, to]);

  const dashboardUrl = useMemo(() => {
    const params = new URLSearchParams({
      orgId: "1",
      viewPanel: String(panelId),
      from,
      to,
      theme: grafanaTheme,
    });
    return `${baseUrl}/d/${dashboardUid}?${params.toString()}`;
  }, [baseUrl, dashboardUid, from, grafanaTheme, panelId, to]);

  useEffect(() => {
    if (!isExpanded) {
      return;
    }

    previousFocusedRef.current = document.activeElement as HTMLElement | null;
    closeButtonRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsExpanded(false);
      }

      if (event.key !== "Tab" || !modalRef.current) {
        return;
      }

      const focusable = modalRef.current.querySelectorAll<HTMLElement>(
        "a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex='-1'])",
      );
      if (focusable.length === 0) {
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
      previousFocusedRef.current?.focus();
    };
  }, [isExpanded]);

  return (
    <>
      <article className="grafana-card reveal">
        <div className="panel-head">
          <h3>{title}</h3>
          <div className="panel-head-actions">
            <button
              type="button"
              className="grafana-expand-btn"
              onClick={() => setIsExpanded(true)}
              aria-label={`Expandir gráfico ${title}`}
            >
              Expandir
            </button>
          </div>
        </div>
        <p className="grafana-note">{narrative}</p>
        {interpretation.length > 0 ? (
          <details className="grafana-context">
            <summary>Como interpretar esta métrica</summary>
            <ul className="list">
              {interpretation.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </details>
        ) : null}
        <div className="grafana-frame-wrap" ref={frameWrapRef}>
          {isVisible ? (
            <iframe
              title={`${title} (${dashboardUid}-${panelId})`}
              src={embedUrl}
              className="grafana-frame"
              loading="lazy"
              referrerPolicy="strict-origin-when-cross-origin"
            />
          ) : (
            <button
              type="button"
              className="grafana-lazy-trigger"
              onClick={() => setIsVisible(true)}
              aria-label={`Carregar gráfico ${title}`}
            >
              Carregar gráfico
            </button>
          )}
        </div>
      </article>

      {isExpanded ? (
        <div className="grafana-modal-overlay" onClick={() => setIsExpanded(false)}>
          <section
            className="grafana-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={narrativeId}
            onClick={(event) => event.stopPropagation()}
            ref={modalRef}
          >
            <header className="grafana-modal-head">
              <h3 id={titleId}>{title}</h3>
              <div className="grafana-modal-actions">
                <a
                  href={dashboardUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="grafana-modal-open"
                >
                  Abrir no Grafana
                </a>
                <button
                  type="button"
                  className="grafana-modal-close"
                  onClick={() => setIsExpanded(false)}
                  aria-label={`Fechar visualização expandida do gráfico ${title}`}
                  ref={closeButtonRef}
                >
                  Fechar
                </button>
              </div>
            </header>
            <p className="grafana-note" id={narrativeId}>{narrative}</p>
            <div className="grafana-modal-frame-wrap">
              <iframe
                title={`expanded-${dashboardUid}-${panelId}`}
                src={embedUrl}
                className="grafana-modal-frame"
                loading="eager"
                referrerPolicy="strict-origin-when-cross-origin"
              />
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}

"use client";

import { useEffect, useId, useState } from "react";

type Props = {
  dashboardUid: string;
  panelId: number;
  title: string;
  narrative: string;
  timeRange?: string;
};

export function GrafanaEmbedCard({
  dashboardUid,
  panelId,
  title,
  narrative,
  timeRange = "now-6h",
}: Props) {
  const [isExpanded, setIsExpanded] = useState(false);
  const titleId = useId();
  const baseUrl = process.env.NEXT_PUBLIC_GRAFANA_URL ?? "http://localhost:3000";
  const theme = process.env.NEXT_PUBLIC_GRAFANA_THEME ?? "dark";
  const params = new URLSearchParams({
    orgId: "1",
    from: timeRange,
    to: "now",
    panelId: String(panelId),
    theme,
    refresh: "15s",
  });

  const embedUrl = `${baseUrl}/d-solo/${dashboardUid}?${params.toString()}`;
  const dashboardUrl = `${baseUrl}/d/${dashboardUid}?orgId=1&viewPanel=${panelId}&from=${timeRange}&to=now&theme=${theme}`;

  useEffect(() => {
    if (!isExpanded) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsExpanded(false);
      }
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
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
        <div className="grafana-frame-wrap">
          <iframe
            title={`${dashboardUid}-${panelId}`}
            src={embedUrl}
            className="grafana-frame"
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
          />
        </div>
      </article>

      {isExpanded ? (
        <div className="grafana-modal-overlay" onClick={() => setIsExpanded(false)}>
          <section
            className="grafana-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onClick={(event) => event.stopPropagation()}
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
                >
                  Fechar
                </button>
              </div>
            </header>
            <p className="grafana-note">{narrative}</p>
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

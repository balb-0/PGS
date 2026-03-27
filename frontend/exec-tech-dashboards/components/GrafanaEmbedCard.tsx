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

  return (
    <article className="grafana-card reveal">
      <div className="panel-head">
        <h3>{title}</h3>
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
  );
}

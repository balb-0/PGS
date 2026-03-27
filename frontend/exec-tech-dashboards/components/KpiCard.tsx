type Props = {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "good" | "warn" | "bad";
};

export function KpiCard({ label, value, hint, tone = "neutral" }: Props) {
  return (
    <article className={`kpi-card tone-${tone}`}>
      <p className="kpi-label">{label}</p>
      <strong className="kpi-value">{value}</strong>
      {hint ? <p className="kpi-hint">{hint}</p> : null}
    </article>
  );
}

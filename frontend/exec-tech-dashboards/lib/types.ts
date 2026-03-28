export type DashboardKind = "business" | "system-health" | "testing-gap";

export type ApiEnvelope = {
  dashboard: DashboardKind;
  generated_at: string;
  filters: Record<string, string>;
  degradation?: {
    prometheus: "ok" | "degraded";
    details?: string | null;
  };
  summary: Record<string, string | number | boolean | null>;
  breakdown?: Record<string, unknown>;
  trends?: Record<string, unknown>;
  coverage?: Record<string, unknown>;
};

export type Kpi = {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "good" | "warn" | "bad";
};

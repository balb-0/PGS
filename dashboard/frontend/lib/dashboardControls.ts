export type TimeRange = "now-1h" | "now-6h" | "now-24h" | "now-7d";
export type CompareMode = "none" | "previous";
export type RefreshInterval = "off" | "15s" | "30s" | "1m";

export type DashboardFilterState = {
  timeRange: TimeRange;
  compareMode: CompareMode;
  refresh: RefreshInterval;
  category: string;
  search: string;
};

export const TIME_RANGE_OPTIONS: Array<{ value: TimeRange; label: string }> = [
  { value: "now-1h", label: "Última 1 hora" },
  { value: "now-6h", label: "Últimas 6 horas" },
  { value: "now-24h", label: "Últimas 24 horas" },
  { value: "now-7d", label: "Últimos 7 dias" },
];

export const COMPARE_MODE_OPTIONS: Array<{ value: CompareMode; label: string }> = [
  { value: "none", label: "Sem comparação" },
  { value: "previous", label: "Comparar com período anterior" },
];

export const REFRESH_OPTIONS: Array<{ value: RefreshInterval; label: string }> = [
  { value: "off", label: "Sem atualização automática" },
  { value: "15s", label: "Atualizar a cada 15s" },
  { value: "30s", label: "Atualizar a cada 30s" },
  { value: "1m", label: "Atualizar a cada 1 min" },
];

const apiWindowByRange: Record<TimeRange, { interval: string; step: string }> = {
  "now-1h": { interval: "1h", step: "1m" },
  "now-6h": { interval: "6h", step: "5m" },
  "now-24h": { interval: "24h", step: "15m" },
  "now-7d": { interval: "7d", step: "1h" },
};

const previousByRange: Record<TimeRange, { from: string; to: string; label: string }> = {
  "now-1h": { from: "now-2h", to: "now-1h", label: "janela anterior de 1 hora" },
  "now-6h": { from: "now-12h", to: "now-6h", label: "janela anterior de 6 horas" },
  "now-24h": { from: "now-48h", to: "now-24h", label: "janela anterior de 24 horas" },
  "now-7d": { from: "now-14d", to: "now-7d", label: "janela anterior de 7 dias" },
};

export function getApiWindow(range: TimeRange) {
  return apiWindowByRange[range];
}

export function getPreviousWindow(range: TimeRange) {
  return previousByRange[range];
}

export function buildGrafanaWindowLabel(range: TimeRange) {
  return TIME_RANGE_OPTIONS.find((option) => option.value === range)?.label ?? range;
}

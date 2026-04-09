"use client";

import { useEffect, useMemo, useState } from "react";

import { DashboardFilterBar } from "@/components/DashboardFilterBar";
import { DashboardShell } from "@/components/DashboardShell";
import { GrafanaEmbedCard } from "@/components/GrafanaEmbedCard";
import { KpiCard } from "@/components/KpiCard";
import { ReportBuilder } from "@/components/ReportBuilder";
import { TrendChart } from "@/components/TrendChart";
import { getDashboard } from "@/lib/dashboardApi";
import {
  buildGrafanaWindowLabel,
  DashboardFilterState,
  getApiWindow,
  getPreviousWindow,
} from "@/lib/dashboardControls";
import { ApiEnvelope } from "@/lib/types";

type TrendSeries = { metric?: { [k: string]: string }; points?: Array<{ t: number; v: number }> };
type HealthCategory = "confiabilidade" | "incidentes" | "capacidade";
type HealthPanel = {
  panelId: number;
  title: string;
  narrative: string;
  category: HealthCategory;
  tags: string[];
  interpretation: string[];
};

const dashboardUid = "asis-system-health-dashboard";

const categoryMeta: Record<HealthCategory, { label: string; description: string }> = {
  confiabilidade: {
    label: "Confiabilidade do Serviço",
    description: "Continuidade, estabilidade e comportamento de proteção sob carga real.",
  },
  incidentes: {
    label: "Gestão de Incidentes",
    description: "Sinais de degradação, alertas e risco de indisponibilidade.",
  },
  capacidade: {
    label: "Capacidade e Saturação",
    description: "Pressão por tenant e uso estrutural de recursos críticos.",
  },
};

const categoryOptions = [
  { value: "all", label: "Todos os contextos" },
  { value: "confiabilidade", label: "Confiabilidade" },
  { value: "incidentes", label: "Incidentes" },
  { value: "capacidade", label: "Capacidade" },
];

const operationsPanels: HealthPanel[] = [
  {
    panelId: 1,
    title: "Health Score",
    narrative: "Resume risco operacional em um indicador único para priorização rápida.",
    category: "confiabilidade",
    tags: ["health", "score", "risco"],
    interpretation: [
      "Queda contínua do score indica acúmulo de degradações.",
      "Correlacione com alertas ativos para priorizar resposta.",
    ],
  },
  {
    panelId: 2,
    title: "Taxa de Erro",
    narrative: "Sinaliza quando o sistema aproxima do ponto de alerta de disponibilidade.",
    category: "incidentes",
    tags: ["erro", "disponibilidade", "incidente"],
    interpretation: [
      "Escalada abrupta exige análise de causa raiz em minutos.",
      "Combine com circuit breaker para avaliar contenção.",
    ],
  },
  {
    panelId: 3,
    title: "Uptime",
    narrative: "Mostra continuidade do serviço e resiliência ao longo do período.",
    category: "confiabilidade",
    tags: ["uptime", "resiliencia", "continuidade"],
    interpretation: [
      "Quedas de uptime impactam diretamente contratos de serviço.",
      "Use a comparação temporal para verificar recuperação.",
    ],
  },
  {
    panelId: 4,
    title: "Circuit Breaker",
    narrative: "Indica estado de proteção e possibilidade de degradação controlada.",
    category: "incidentes",
    tags: ["circuit breaker", "protecao", "degradacao"],
    interpretation: [
      "Estados abertos recorrentes indicam instabilidade persistente.",
      "Avalie taxa de erro junto com latência para entender gatilhos.",
    ],
  },
  {
    panelId: 5,
    title: "Tendência de Error Rate",
    narrative: "Antecipação de incidentes por leitura temporal de erro.",
    category: "incidentes",
    tags: ["tendencia", "error rate", "tempo"],
    interpretation: [
      "Subida constante sugere incidente em formação.",
      "Quedas após intervenção confirmam efetividade da mitigação.",
    ],
  },
  {
    panelId: 7,
    title: "Rate Limit por Conta",
    narrative: "Revela pressão por tenant e potenciais pontos de saturação.",
    category: "capacidade",
    tags: ["rate limit", "conta", "tenant"],
    interpretation: [
      "Contas próximas do limite podem degradar a experiência.",
      "Útil para ações preventivas de capacity planning.",
    ],
  },
  {
    panelId: 8,
    title: "Alertas Ativos",
    narrative: "Painel tático para resposta imediata a eventos críticos.",
    category: "incidentes",
    tags: ["alerta", "critico", "on-call"],
    interpretation: [
      "Priorize alertas com maior impacto de negócio.",
      "Use em conjunto com Health Score para priorização operacional.",
    ],
  },
  {
    panelId: 9,
    title: "Capacidade dos Stores",
    narrative: "Mostra consumo estrutural para prevenir gargalos de memória e persistência.",
    category: "capacidade",
    tags: ["capacidade", "store", "memoria"],
    interpretation: [
      "Consumo alto sustentado exige plano de expansão.",
      "Saltos repentinos podem indicar carga anômala.",
    ],
  },
];

const initialFilters: DashboardFilterState = {
  timeRange: "now-6h",
  compareMode: "none",
  refresh: "15s",
  category: "all",
  search: "",
};

type RatePressure = { account_key_hash: string; remaining: number };

export default function SystemHealthPage() {
  const [data, setData] = useState<ApiEnvelope | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filters, setFilters] = useState<DashboardFilterState>(initialFilters);

  useEffect(() => {
    const { interval, step } = getApiWindow(filters.timeRange);
    let active = true;

    setIsLoading(true);
    setError(null);

    getDashboard("system-health", { interval, step })
      .then((payload) => {
        if (!active) {
          return;
        }
        setData(payload);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "Erro");
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [filters.timeRange]);

  const errorTrend = useMemo(() => {
    const trendBlock = (data?.trends?.error_rate ?? []) as TrendSeries[];
    return trendBlock[0]?.points ?? [];
  }, [data]);

  const pressure = useMemo(() => {
    return (data?.breakdown?.rate_limit_pressure as RatePressure[] | undefined) ?? [];
  }, [data]);

  const filteredPanels = useMemo(() => {
    const search = filters.search.trim().toLowerCase();

    return operationsPanels.filter((panel) => {
      const byCategory = filters.category === "all" ? true : panel.category === filters.category;
      const bySearch =
        search.length === 0
          ? true
          : [panel.title, panel.narrative, ...panel.tags].join(" ").toLowerCase().includes(search);
      return byCategory && bySearch;
    });
  }, [filters.category, filters.search]);

  const groupedPanels = useMemo(() => {
    return (Object.keys(categoryMeta) as HealthCategory[]).map((category) => ({
      category,
      panels: filteredPanels.filter((panel) => panel.category === category),
    }));
  }, [filteredPanels]);

  const previousWindow = useMemo(() => getPreviousWindow(filters.timeRange), [filters.timeRange]);
  const timeRangeLabel = useMemo(() => buildGrafanaWindowLabel(filters.timeRange), [filters.timeRange]);

  const reportItems = useMemo(() => {
    const summary = [
      {
        id: "health-score",
        label: "Health Score",
        value: `${data?.summary.health_score ?? 0}`,
        description: "Indicador composto de saúde operacional.",
        group: "KPIs",
      },
      {
        id: "health-error-rate",
        label: "Error Rate",
        value: `${data?.summary.error_rate_percent ?? 0}%`,
        description: "Taxa de erro consolidada na janela ativa.",
        group: "KPIs",
      },
      {
        id: "health-circuit",
        label: "Circuit Breaker",
        value: `${data?.summary.circuit_breaker_state ?? "unknown"}`,
        description: "Estado atual do mecanismo de proteção.",
        group: "KPIs",
      },
      {
        id: "health-alerts",
        label: "Alertas Ativos",
        value: `${data?.summary.firing_alerts ?? 0}`,
        description: "Quantidade de alertas em estado firing.",
        group: "KPIs",
      },
    ];

    const selectedPanels = filteredPanels.map((panel) => ({
      id: `panel-${panel.panelId}`,
      label: panel.title,
      value: "Embed Grafana",
      description: panel.narrative,
      group: categoryMeta[panel.category].label,
    }));

    return [...summary, ...selectedPanels];
  }, [data, filteredPanels]);

  const filterSummary = useMemo(() => {
    const categoryLabel = categoryOptions.find((option) => option.value === filters.category)?.label ?? "Todos";
    return [
      `Período: ${timeRangeLabel}`,
      `Contexto: ${categoryLabel}`,
      `Comparação: ${filters.compareMode === "previous" ? "Ativa" : "Desativada"}`,
      `Busca: ${filters.search.trim() || "sem termo"}`,
    ];
  }, [filters.category, filters.compareMode, filters.search, timeRangeLabel]);

  return (
    <DashboardShell
      title="Dashboard de Saúde do Sistema"
      subtitle="Observabilidade operacional para diagnóstico rápido de estabilidade, disponibilidade e performance."
    >
      {error ? <div className="empty-state" role="status">Falha ao carregar: {error}</div> : null}
      {isLoading ? <div className="empty-state" role="status">Atualizando saúde técnica...</div> : null}

      <DashboardFilterBar
        value={filters}
        categoryOptions={categoryOptions}
        onChange={(patch) => setFilters((previous) => ({ ...previous, ...patch }))}
      />

      <ReportBuilder title="Relatório de Saúde do Sistema" items={reportItems} filters={filterSummary} />

      {data ? (
        <>
          <section className="kpi-grid reveal">
            <KpiCard label="Health Score" value={`${data.summary.health_score ?? 0}`} tone="good" hint="Visão consolidada de risco operacional." />
            <KpiCard label="Error Rate" value={`${data.summary.error_rate_percent ?? 0}%`} tone="bad" hint="Principal sinal de degradação ativa." />
            <KpiCard label="Circuit" value={String(data.summary.circuit_breaker_state ?? "unknown")} tone="warn" hint="Estado de proteção contra cascata de falhas." />
            <KpiCard label="Alertas" value={String(data.summary.firing_alerts ?? 0)} tone="warn" hint="Use para priorização tática de resposta." />
          </section>

          <TrendChart title="Tendência da Taxa de Erro" data={errorTrend} color="#ff5a78" valueSuffix="%" />

          <article className="panel reveal comparison-summary">
            <h3>Pressão de Rate Limit</h3>
            <p>Janela em análise: {timeRangeLabel}</p>
            {pressure.length === 0 ? (
              <p>Nenhuma conta pressionando o limite no período.</p>
            ) : (
              <ul className="list">
                {pressure.map((item) => (
                  <li key={item.account_key_hash}>
                    {item.account_key_hash}: {item.remaining} restantes
                  </li>
                ))}
              </ul>
            )}
          </article>

          <article className="panel reveal strategic-note">
            <h3>Camada de decisão operacional</h3>
            <p>
              Os painéis abaixo são embeds diretos do Grafana e concentram sinais para operação de alta confiabilidade:
              saúde corrente, comportamento de erro, saturação por conta e estado de resposta a incidente.
            </p>
          </article>
        </>
      ) : null}

      {filteredPanels.length === 0 ? (
        <div className="empty-state">Nenhum gráfico encontrado para os filtros atuais.</div>
      ) : null}

      {groupedPanels.map(({ category, panels }) =>
        panels.length === 0 ? null : (
          <section className="dashboard-section" key={category} aria-labelledby={`health-section-${category}`}>
            <header className="section-head">
              <h2 id={`health-section-${category}`}>{categoryMeta[category].label}</h2>
              <p>{categoryMeta[category].description}</p>
            </header>
            <div className="grafana-grid">
              {panels.map((panel) => (
                <GrafanaEmbedCard
                  key={panel.panelId}
                  dashboardUid={dashboardUid}
                  panelId={panel.panelId}
                  title={panel.title}
                  narrative={panel.narrative}
                  from={filters.timeRange}
                  to="now"
                  refresh={filters.refresh}
                  interpretation={panel.interpretation}
                />
              ))}
            </div>
          </section>
        ),
      )}

      {filters.compareMode === "previous" && filteredPanels.length > 0 ? (
        <section className="dashboard-section comparison-section" aria-labelledby="health-comparison">
          <header className="section-head">
            <h2 id="health-comparison">Comparação com período anterior</h2>
            <p>Visualização da {previousWindow.label} para contrastar comportamento operacional.</p>
          </header>
          <div className="grafana-grid comparison-grid">
            {filteredPanels.map((panel) => (
              <GrafanaEmbedCard
                key={`compare-${panel.panelId}`}
                dashboardUid={dashboardUid}
                panelId={panel.panelId}
                title={`${panel.title} • ${previousWindow.label}`}
                narrative={panel.narrative}
                from={previousWindow.from}
                to={previousWindow.to}
                refresh="off"
                interpretation={panel.interpretation}
              />
            ))}
          </div>
        </section>
      ) : null}
    </DashboardShell>
  );
}

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
type BusinessCategory = "financeiro" | "operacional" | "tecnico";
type BusinessPanel = {
  panelId: number;
  title: string;
  narrative: string;
  category: BusinessCategory;
  tags: string[];
  interpretation: string[];
};

const dashboardUid = "asis-business-dashboard";

const categoryMeta: Record<BusinessCategory, { label: string; description: string }> = {
  financeiro: {
    label: "Contexto Financeiro e SLA",
    description: "Métricas de risco de receita e experiência percebida pelo cliente.",
  },
  operacional: {
    label: "Contexto Operacional",
    description: "Métricas de vazão e eficiência para sustentar escala com previsibilidade.",
  },
  tecnico: {
    label: "Contexto Técnico e Qualidade",
    description: "Métricas de estabilidade e causas raiz para prevenção de incidentes.",
  },
};

const categoryOptions = [
  { value: "all", label: "Todos os contextos" },
  { value: "financeiro", label: "Financeiro e SLA" },
  { value: "operacional", label: "Operacional" },
  { value: "tecnico", label: "Técnico e Qualidade" },
];

const decisionPanels: BusinessPanel[] = [
  {
    panelId: 1,
    title: "Taxa de Sucesso",
    narrative: "Mostra consistência operacional para não perder receita por falhas evitáveis.",
    category: "financeiro",
    tags: ["sucesso", "receita", "sla"],
    interpretation: [
      "Quedas sustentadas indicam risco de impacto financeiro.",
      "Correlacione com erros por fonte para priorizar mitigação.",
    ],
  },
  {
    panelId: 2,
    title: "Latência P90 (SLA)",
    narrative: "Indica risco de violação de SLA e impacto direto em satisfação do cliente.",
    category: "financeiro",
    tags: ["sla", "latencia", "cliente"],
    interpretation: [
      "Monitore tendências antes de estourar o alvo de SLA.",
      "Use junto com throughput para evitar otimizações isoladas.",
    ],
  },
  {
    panelId: 3,
    title: "Throughput Atual",
    narrative: "Capacidade de vazão no ritmo de negócio real.",
    category: "operacional",
    tags: ["throughput", "capacidade", "escala"],
    interpretation: [
      "Aumento de throughput com latência estável indica eficiência.",
      "Se throughput cai e erro sobe, há gargalo operacional.",
    ],
  },
  {
    panelId: 5,
    title: "Tendência P50/P90/P99",
    narrative: "Permite antecipar degradação antes de ruptura operacional.",
    category: "tecnico",
    tags: ["latencia", "percentil", "degradacao"],
    interpretation: [
      "Abertura entre P50 e P99 indica degradação de cauda.",
      "Aumente observabilidade de endpoints críticos se a dispersão crescer.",
    ],
  },
  {
    panelId: 6,
    title: "Volume por Endpoint",
    narrative: "Identifica onde a demanda se concentra e onde investir em otimização.",
    category: "operacional",
    tags: ["volume", "endpoint", "demanda"],
    interpretation: [
      "Concentração extrema sugere risco de ponto único de saturação.",
      "Combine com taxa de erro por endpoint para ranking de prioridade.",
    ],
  },
  {
    panelId: 7,
    title: "Erros por Status/Fonte",
    narrative: "Compara impacto de erros entre origem real e mock para governança de qualidade.",
    category: "tecnico",
    tags: ["erro", "status", "fonte"],
    interpretation: [
      "Erros de origem real devem ser priorizados por impacto em produção.",
      "Mudanças no mix por status ajudam a detectar regressões de integração.",
    ],
  },
  {
    panelId: 8,
    title: "Erros de Validação",
    narrative: "Evidencia perdas por qualidade de entrada e orienta ações de redução de retrabalho.",
    category: "tecnico",
    tags: ["validacao", "qualidade", "entrada"],
    interpretation: [
      "Altos níveis indicam necessidade de melhorias de contrato e onboarding.",
      "Use como gatilho para ações de prevenção e documentação.",
    ],
  },
  {
    panelId: 9,
    title: "Throughput por Método",
    narrative: "Sinaliza gargalos por tipo de operação e potencial de ganho rápido.",
    category: "operacional",
    tags: ["throughput", "metodo", "api"],
    interpretation: [
      "Compare métodos para identificar rotas com desequilíbrio de carga.",
      "Concentração em poucos métodos pode indicar oportunidade de cache.",
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

export default function BusinessPage() {
  const [data, setData] = useState<ApiEnvelope | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filters, setFilters] = useState<DashboardFilterState>(initialFilters);

  useEffect(() => {
    const { interval, step } = getApiWindow(filters.timeRange);
    let active = true;

    setIsLoading(true);
    setError(null);

    getDashboard("business", { interval, step })
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

  const trend = useMemo(() => {
    const trendBlock = (data?.trends?.p90_latency ?? []) as TrendSeries[];
    return trendBlock[0]?.points ?? [];
  }, [data]);

  const trendDeltaHint = useMemo(() => {
    if (trend.length < 2) {
      return "Sem base comparável no período.";
    }

    const first = trend[0].v;
    const last = trend[trend.length - 1].v;
    const delta = last - first;
    const sign = delta > 0 ? "+" : "";
    return `Variação no período: ${sign}${delta.toFixed(2)} ms`;
  }, [trend]);

  const filteredPanels = useMemo(() => {
    const search = filters.search.trim().toLowerCase();

    return decisionPanels.filter((panel) => {
      const byCategory = filters.category === "all" ? true : panel.category === filters.category;
      const bySearch =
        search.length === 0
          ? true
          : [panel.title, panel.narrative, ...panel.tags].join(" ").toLowerCase().includes(search);
      return byCategory && bySearch;
    });
  }, [filters.category, filters.search]);

  const groupedPanels = useMemo(() => {
    return (Object.keys(categoryMeta) as BusinessCategory[]).map((category) => ({
      category,
      panels: filteredPanels.filter((panel) => panel.category === category),
    }));
  }, [filteredPanels]);

  const previousWindow = useMemo(() => getPreviousWindow(filters.timeRange), [filters.timeRange]);
  const timeRangeLabel = useMemo(() => buildGrafanaWindowLabel(filters.timeRange), [filters.timeRange]);

  const reportItems = useMemo(() => {
    const summary = [
      {
        id: "business-success",
        label: "Taxa de Sucesso",
        value: `${data?.summary.success_rate_percent ?? 0}%`,
        description: "Indicador agregado de confiabilidade de execução.",
        group: "KPIs",
      },
      {
        id: "business-p90",
        label: "P90 Latência",
        value: `${data?.summary.p90_latency_ms ?? 0} ms`,
        description: "Latência de cauda associada ao cumprimento de SLA.",
        group: "KPIs",
      },
      {
        id: "business-throughput",
        label: "Throughput",
        value: `${data?.summary.throughput_rps ?? 0} req/s`,
        description: "Volume processado por segundo na janela selecionada.",
        group: "KPIs",
      },
      {
        id: "business-errors",
        label: "Erros atuais",
        value: `${data?.summary.total_errors ?? 0}`,
        description: "Total de erros contabilizados no período ativo.",
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
      title="Dashboard de Negócio"
      subtitle="Leitura executiva de volume, eficiência e sinais de SLA para decisão rápida."
    >
      {error ? <div className="empty-state" role="status">Falha ao carregar: {error}</div> : null}
      {isLoading ? <div className="empty-state" role="status">Atualizando indicadores executivos...</div> : null}

      <DashboardFilterBar
        value={filters}
        categoryOptions={categoryOptions}
        onChange={(patch) => setFilters((previous) => ({ ...previous, ...patch }))}
      />

      <ReportBuilder title="Relatório de Negócio" items={reportItems} filters={filterSummary} />

      {data ? (
        <>
          <section className="kpi-grid reveal">
            <KpiCard
              label="Sucesso"
              value={`${data.summary.success_rate_percent ?? 0}%`}
              tone="good"
              hint="Métrica principal de confiabilidade do fluxo de negócio."
            />
            <KpiCard
              label="P90 Latência"
              value={`${data.summary.p90_latency_ms ?? 0} ms`}
              tone="warn"
              hint={trendDeltaHint}
            />
            <KpiCard
              label="Throughput"
              value={`${data.summary.throughput_rps ?? 0} req/s`}
              hint="Capacidade atual de processamento."
            />
            <KpiCard
              label="Processos"
              value={`${data.summary.process_store_size ?? 0}`}
              hint="Volume persistido no período selecionado."
            />
          </section>

          <TrendChart title="Tendência de Latência P90" data={trend} color="#fe6f5e" valueSuffix=" ms" />

          <article className="panel reveal comparison-summary">
            <h3>Sinais para decisão</h3>
            <p>Status SLA: <span className="status-chip status-warn">{String(data.summary.sla_status ?? "unknown")}</span></p>
            <p>Erros atuais: {String(data.summary.total_errors ?? 0)}</p>
            <p>Requisições totais: {String(data.summary.total_requests ?? 0)}</p>
            <p>Janela em análise: {timeRangeLabel}</p>
            <p>
              Fonte Prometheus: <span className={data.degradation?.prometheus === "ok" ? "status-chip status-good" : "status-chip status-bad"}>{data.degradation?.prometheus ?? "degraded"}</span>
            </p>
          </article>

          <article className="panel reveal strategic-note">
            <h3>Camada de decisão executiva</h3>
            <p>
              Os gráficos abaixo são exportados diretamente do Grafana e trazem uma leitura de negócio orientada a
              resultado: estabilidade de SLA, produtividade operacional, risco financeiro por erro e pressão de crescimento.
            </p>
          </article>
        </>
      ) : null}

      {filteredPanels.length === 0 ? (
        <div className="empty-state">Nenhum gráfico encontrado para os filtros atuais.</div>
      ) : null}

      {groupedPanels.map(({ category, panels }) =>
        panels.length === 0 ? null : (
          <section className="dashboard-section" key={category} aria-labelledby={`business-section-${category}`}>
            <header className="section-head">
              <h2 id={`business-section-${category}`}>{categoryMeta[category].label}</h2>
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
        <section className="dashboard-section comparison-section" aria-labelledby="business-comparison">
          <header className="section-head">
            <h2 id="business-comparison">Comparação com período anterior</h2>
            <p>Os mesmos painéis são renderizados na {previousWindow.label} para comparação lado a lado.</p>
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

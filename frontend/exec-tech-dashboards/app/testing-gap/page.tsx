"use client";

import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { GrafanaEmbedCard } from "@/components/GrafanaEmbedCard";
import { KpiCard } from "@/components/KpiCard";
import { TrendChart } from "@/components/TrendChart";
import { getDashboard } from "@/lib/dashboardApi";
import { ApiEnvelope } from "@/lib/types";

type TrendSeries = { metric?: { [k: string]: string }; points?: Array<{ t: number; v: number }> };
type AreaStatus = { area: string; priority: string; status: string };

const dashboardUid = "asis-testing-gap-dashboard";

const qualityPanels = [
  { panelId: 1, title: "Cobertura Geral", narrative: "Indica quanto do escopo funcional está protegido por validação automatizada." },
  { panelId: 2, title: "Pass Rate", narrative: "Sinal de confiança no pipeline e qualidade corrente de entrega." },
  { panelId: 3, title: "Instabilidade", narrative: "Mostra volatilidade de execução que aumenta custo de manutenção." },
  { panelId: 4, title: "Defeitos por KLOC", narrative: "Aproxima risco técnico relativo ao tamanho do código." },
  { panelId: 5, title: "Cobertura por Squad", narrative: "Permite priorização de investimento em automação por equipe." },
  { panelId: 6, title: "Tempo de Correção", narrative: "Evidencia velocidade real de resposta a defeitos reportados." },
  { panelId: 7, title: "Shift-Left", narrative: "Mostra maturidade de prevenção ao mover verificações para mais cedo." },
  { panelId: 8, title: "Debt Index", narrative: "Consolida backlog técnico e orienta cadência de saneamento." },
];

export default function TestingGapPage() {
  const [data, setData] = useState<ApiEnvelope | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard("testing-gap", { interval: "24h", step: "5m" })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Erro"));
  }, []);

  const trend = useMemo(() => {
    const trendBlock = (data?.trends?.validation_errors ?? []) as TrendSeries[];
    return trendBlock[0]?.points ?? [];
  }, [data]);

  const areas = useMemo(() => {
    return (data?.breakdown?.areas as AreaStatus[] | undefined) ?? [];
  }, [data]);

  const coverage = (data?.coverage as Record<string, number> | undefined) ?? {};

  return (
    <DashboardShell
      title="Dashboard de Testes Restantes"
      subtitle="Visibilidade de pendências, risco e cobertura para priorização técnica orientada a impacto."
    >
      {error ? <div className="empty-state">Falha ao carregar: {error}</div> : null}
      {!data && !error ? <div className="empty-state">Carregando risco de testes...</div> : null}
      {data ? (
        <>
          <section className="kpi-grid reveal">
            <KpiCard label="Pass Rate" value={`${data.summary.pass_rate_percent ?? 0}%`} tone="good" />
            <KpiCard label="Falhas" value={String(data.summary.failed_tests ?? 0)} tone="bad" />
            <KpiCard label="Pendentes" value={String(data.summary.pending_tests ?? 0)} tone="warn" />
            <KpiCard label="Risco" value={String(data.summary.risk_level ?? "low")} tone="warn" />
          </section>

          <TrendChart title="Tendência de Erros de Validação" data={trend} color="#f0af5e" />

          <article className="panel reveal">
            <h3>Cobertura e Lacunas</h3>
            <p>Line coverage: {String(coverage.line_rate_percent ?? 0)}%</p>
            <p>Branch coverage: {String(coverage.branch_rate_percent ?? 0)}%</p>
            {areas.length === 0 ? (
              <p>Sem áreas mapeadas para este período.</p>
            ) : (
              <ul className="list">
                {areas.map((area) => (
                  <li key={area.area}>
                    {area.area} - prioridade {area.priority} - status {area.status}
                  </li>
                ))}
              </ul>
            )}
          </article>

          <article className="panel reveal strategic-note">
            <h3>Camada de decisão de qualidade</h3>
            <p>
              Esta visão combina sinais de cobertura, estabilidade e produtividade de correção para orientar sprint planning,
              definição de metas de qualidade e alocação de esforço em automação de testes.
            </p>
          </article>
        </>
      ) : null}

      <section className="grafana-grid">
        {qualityPanels.map((panel) => (
          <GrafanaEmbedCard
            key={panel.panelId}
            dashboardUid={dashboardUid}
            panelId={panel.panelId}
            title={panel.title}
            narrative={panel.narrative}
            timeRange="now-30d"
          />
        ))}
      </section>
    </DashboardShell>
  );
}

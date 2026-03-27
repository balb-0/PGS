"use client";

import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { GrafanaEmbedCard } from "@/components/GrafanaEmbedCard";
import { KpiCard } from "@/components/KpiCard";
import { TrendChart } from "@/components/TrendChart";
import { getDashboard } from "@/lib/dashboardApi";
import { ApiEnvelope } from "@/lib/types";

type TrendSeries = { metric?: { [k: string]: string }; points?: Array<{ t: number; v: number }> };

const dashboardUid = "asis-system-health-dashboard";

const operationsPanels = [
  { panelId: 1, title: "Health Score", narrative: "Resume risco operacional em um indicador único para priorização rápida." },
  { panelId: 2, title: "Taxa de Erro", narrative: "Sinaliza quando o sistema aproxima do ponto de alerta de disponibilidade." },
  { panelId: 3, title: "Uptime", narrative: "Mostra continuidade do serviço e resiliência ao longo do período." },
  { panelId: 4, title: "Circuit Breaker", narrative: "Indica estado de proteção e possibilidade de degradação controlada." },
  { panelId: 5, title: "Tendência de Error Rate", narrative: "Antecipação de incidentes por leitura temporal de erro." },
  { panelId: 7, title: "Rate Limit por Conta", narrative: "Revela pressão por tenant e potenciais pontos de saturação." },
  { panelId: 8, title: "Alertas Ativos", narrative: "Painel tático para resposta imediata a eventos críticos." },
  { panelId: 9, title: "Capacidade dos Stores", narrative: "Mostra consumo estrutural para prevenir gargalos de memória e persistência." },
];

type RatePressure = { account_key_hash: string; remaining: number };

export default function SystemHealthPage() {
  const [data, setData] = useState<ApiEnvelope | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard("system-health", { interval: "6h", step: "1m" })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Erro"));
  }, []);

  const errorTrend = useMemo(() => {
    const trendBlock = (data?.trends?.error_rate ?? []) as TrendSeries[];
    return trendBlock[0]?.points ?? [];
  }, [data]);

  const pressure = useMemo(() => {
    return (data?.breakdown?.rate_limit_pressure as RatePressure[] | undefined) ?? [];
  }, [data]);

  return (
    <DashboardShell
      title="Dashboard de Saúde do Sistema"
      subtitle="Observabilidade operacional para diagnóstico rápido de estabilidade, disponibilidade e performance."
    >
      {error ? <div className="empty-state">Falha ao carregar: {error}</div> : null}
      {!data && !error ? <div className="empty-state">Carregando saúde técnica...</div> : null}
      {data ? (
        <>
          <section className="kpi-grid reveal">
            <KpiCard label="Health Score" value={`${data.summary.health_score ?? 0}`} tone="good" />
            <KpiCard label="Error Rate" value={`${data.summary.error_rate_percent ?? 0}%`} tone="bad" />
            <KpiCard label="Circuit" value={String(data.summary.circuit_breaker_state ?? "unknown")} tone="warn" />
            <KpiCard label="Alertas" value={String(data.summary.firing_alerts ?? 0)} tone="warn" />
          </section>

          <TrendChart title="Tendência da Taxa de Erro" data={errorTrend} color="#ff5a78" valueSuffix="%" />

          <article className="panel reveal">
            <h3>Pressão de Rate Limit</h3>
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

      <section className="grafana-grid">
        {operationsPanels.map((panel) => (
          <GrafanaEmbedCard
            key={panel.panelId}
            dashboardUid={dashboardUid}
            panelId={panel.panelId}
            title={panel.title}
            narrative={panel.narrative}
            timeRange="now-6h"
          />
        ))}
      </section>
    </DashboardShell>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { GrafanaEmbedCard } from "@/components/GrafanaEmbedCard";
import { KpiCard } from "@/components/KpiCard";
import { TrendChart } from "@/components/TrendChart";
import { getDashboard } from "@/lib/dashboardApi";
import { ApiEnvelope } from "@/lib/types";

type TrendSeries = { metric?: { [k: string]: string }; points?: Array<{ t: number; v: number }> };

const dashboardUid = "asis-business-dashboard";

const decisionPanels = [
  { panelId: 1, title: "Taxa de Sucesso", narrative: "Mostra consistência operacional para não perder receita por falhas evitáveis." },
  { panelId: 2, title: "Latência P90 (SLA)", narrative: "Indica risco de violação de SLA e impacto direto em satisfação do cliente." },
  { panelId: 3, title: "Throughput Atual", narrative: "Capacidade de vazão no ritmo de negócio real." },
  { panelId: 5, title: "Tendência P50/P90/P99", narrative: "Permite antecipar degradação antes de ruptura operacional." },
  { panelId: 6, title: "Volume por Endpoint", narrative: "Identifica onde a demanda se concentra e onde investir em otimização." },
  { panelId: 7, title: "Erros por Status/Fonte", narrative: "Compara impacto de erros entre origem real e mock para governança de qualidade." },
  { panelId: 8, title: "Erros de Validação", narrative: "Evidencia perdas por qualidade de entrada e orienta ações de redução de retrabalho." },
  { panelId: 9, title: "Throughput por Método", narrative: "Sinaliza gargalos por tipo de operação e potencial de ganho rápido." },
];

export default function BusinessPage() {
  const [data, setData] = useState<ApiEnvelope | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard("business", { interval: "6h", step: "5m" })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Erro"));
  }, []);

  const trend = useMemo(() => {
    const trendBlock = (data?.trends?.p90_latency ?? []) as TrendSeries[];
    return trendBlock[0]?.points ?? [];
  }, [data]);

  return (
    <DashboardShell
      title="Dashboard de Negócio"
      subtitle="Leitura executiva de volume, eficiência e sinais de SLA para decisão rápida."
    >
      {error ? <div className="empty-state">Falha ao carregar: {error}</div> : null}
      {!data && !error ? <div className="empty-state">Carregando indicadores executivos...</div> : null}
      {data ? (
        <>
          <section className="kpi-grid reveal">
            <KpiCard label="Sucesso" value={`${data.summary.success_rate_percent ?? 0}%`} tone="good" />
            <KpiCard label="P90 Latência" value={`${data.summary.p90_latency_ms ?? 0} ms`} tone="warn" />
            <KpiCard label="Throughput" value={`${data.summary.throughput_rps ?? 0} req/s`} />
            <KpiCard label="Processos" value={`${data.summary.process_store_size ?? 0}`} />
          </section>

          <TrendChart title="Tendência de Latência P90" data={trend} color="#fe6f5e" valueSuffix=" ms" />

          <article className="panel reveal">
            <h3>Sinais para decisão</h3>
            <p>Status SLA: <span className="status-chip status-warn">{String(data.summary.sla_status ?? "unknown")}</span></p>
            <p>Erros atuais: {String(data.summary.total_errors ?? 0)}</p>
            <p>Requisições totais: {String(data.summary.total_requests ?? 0)}</p>
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

      <section className="grafana-grid">
        {decisionPanels.map((panel) => (
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

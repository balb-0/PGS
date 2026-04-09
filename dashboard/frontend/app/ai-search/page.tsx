"use client";

import { useCallback, useMemo, useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { GrafanaEmbedCard } from "@/components/GrafanaEmbedCard";
import { SearchBar } from "@/components/SearchBar";
import { graphCatalogById } from "@/lib/graphCatalog";
import { AISearchResponse } from "@/types/graph";

export default function AISearchPage() {
  const [searchResult, setSearchResult] = useState<AISearchResponse | null>(null);

  const handleSearchResult = useCallback((result: AISearchResponse | null) => {
    setSearchResult(result);
  }, []);

  const selectedGraphs = useMemo(() => {
    if (!searchResult) {
      return [];
    }

    return searchResult.results
      .map((item) => {
        const graph = graphCatalogById.get(item.graph_id);
        if (!graph) {
          return null;
        }
        return {
          ...graph,
          reason: item.reason,
        };
      })
      .filter((item): item is NonNullable<typeof item> => Boolean(item));
  }, [searchResult]);

  return (
    <DashboardShell
      title="Busca Inteligente de Gráficos"
      subtitle="Descreva em linguagem natural o que deseja investigar e a IA seleciona os painéis mais relevantes."
    >
      <article className="panel reveal strategic-note">
        <h3>Como funciona</h3>
        <p>
          Primero escreva o que deseja investigar e clique em "Buscar IA". A plataforma interpreta sua intenção e
          seleciona os gráficos mais úteis já existentes no catálogo. Os painéis retornados aparecem abaixo, prontos
          para análise, sem criar novos gráficos e sem alterar a forma atual de renderização do Grafana.
        </p>
      </article>

      <SearchBar onResult={handleSearchResult} inputId="global-filter-primary" />

      {!searchResult ? (
        <div className="empty-state">Digite uma consulta para começar. Exemplo: "quero investigar erros por serviço".</div>
      ) : null}

      {searchResult?.results.length === 0 ? (
        <div className="empty-state">{searchResult.fallback_message ?? "Nenhum gráfico relevante encontrado"}</div>
      ) : null}

      {searchResult && selectedGraphs.length > 0 ? (
        <article className="panel reveal">
          <h3>Intenção detectada</h3>
          <p>{searchResult.intent}</p>
        </article>
      ) : null}

      <section className="grafana-grid">
        {selectedGraphs.map((graph) => (
          <GrafanaEmbedCard
            key={`${graph.dashboardUid}-${graph.panelId}`}
            dashboardUid={graph.dashboardUid}
            panelId={graph.panelId}
            title={graph.title}
            narrative={graph.reason}
            from="now-24h"
            to="now"
            refresh="off"
          />
        ))}
      </section>
    </DashboardShell>
  );
}

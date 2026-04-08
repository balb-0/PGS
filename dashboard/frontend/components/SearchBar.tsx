"use client";

import { FormEvent, useRef, useState } from "react";

import { AISearchResponse } from "@/types/graph";

type Props = {
  onResult: (result: AISearchResponse | null) => void;
  inputId?: string;
};

export function SearchBar({ onResult, inputId }: Props) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<"openai" | "fallback" | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const runSearch = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = query.trim();

    if (!trimmed) {
      setLoading(false);
      setError(null);
      setProvider(null);
      abortRef.current?.abort();
      onResult(null);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/ai-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
        signal: controller.signal,
      });

      const payload = (await response.json()) as AISearchResponse | { error?: string };

      if (!response.ok) {
        const message = (payload as { error?: string }).error || "Falha na busca inteligente";
        throw new Error(message);
      }

      const typed = payload as AISearchResponse;
      setProvider(typed.provider);
      onResult(typed);
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        return;
      }
      setError(err instanceof Error ? err.message : "Falha na busca inteligente");
      setProvider(null);
      onResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="search-box reveal" aria-label="Busca inteligente de gráficos">
      <div className="search-head">
        <h3>Busca Inteligente de Gráficos</h3>
        <span className={provider === "openai" ? "ai-status ai-online" : provider === "fallback" ? "ai-status ai-fallback" : "ai-status"}>
          <span className="ai-status-icon" aria-hidden="true" />
          {provider === "openai" ? "IA conectada" : provider === "fallback" ? "Fallback local" : "Aguardando busca"}
        </span>
      </div>

      <form className="search-input-wrap" onSubmit={runSearch}>
        <input
          id={inputId}
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Descreva o que você quer ver: erros, performance, cobertura..."
          className="search-input"
          disabled={loading}
        />
        <div className="search-actions">
          <button type="submit" className="search-submit" disabled={loading || !query.trim()}>
            {loading ? "Buscando..." : "Buscar IA"}
          </button>
          {query ? (
          <button
            type="button"
            className="search-clear"
            disabled={loading}
            onClick={() => {
              setQuery("");
              setError(null);
              setLoading(false);
              setProvider(null);
              onResult(null);
            }}
          >
            Limpar
          </button>
          ) : null}
        </div>
      </form>

      <p className="search-meta" role="status">
        {loading ? "Buscando gráficos com IA..." : error ? `Erro: ${error}` : "Digite e pressione Buscar IA para consultar"}
      </p>
    </section>
  );
}

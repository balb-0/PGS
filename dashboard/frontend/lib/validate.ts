import { AISearchResponse, GraphCatalogItem } from "@/types/graph";

const MAX_QUERY_LENGTH = 240;

export function validateQueryInput(rawQuery: unknown): { ok: true; query: string } | { ok: false; error: string } {
  if (typeof rawQuery !== "string") {
    return { ok: false, error: "Query invalida" };
  }

  const query = rawQuery.trim();

  if (!query) {
    return { ok: false, error: "Informe uma busca" };
  }

  if (query.length > MAX_QUERY_LENGTH) {
    return { ok: false, error: `Query muito longa (max ${MAX_QUERY_LENGTH} caracteres)` };
  }

  return { ok: true, query };
}

function clampScore(score: unknown): number {
  const parsed = typeof score === "number" ? score : Number(score);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  if (parsed < 0) {
    return 0;
  }
  if (parsed > 1) {
    return 1;
  }
  return Number(parsed.toFixed(4));
}

export function validateAndFilterResponse(
  raw: unknown,
  catalog: GraphCatalogItem[],
  query: string,
  maxResults: number,
): AISearchResponse {
  const validIds = new Set(catalog.map((g) => g.graphId));

  const base: AISearchResponse = {
    query,
    intent: "buscar graficos relevantes",
    results: [],
    fallback_message: "Nenhum gráfico relevante encontrado",
    provider: "fallback",
  };

  if (!raw || typeof raw !== "object") {
    return base;
  }

  const candidate = raw as Partial<AISearchResponse> & { results?: unknown };
  const inputResults = Array.isArray(candidate.results) ? candidate.results : [];
  const dedupe = new Set<string>();

  const results = inputResults
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }

      const source = item as { graph_id?: unknown; score?: unknown; reason?: unknown };
      const graphId = typeof source.graph_id === "string" ? source.graph_id : "";
      if (!graphId || !validIds.has(graphId) || dedupe.has(graphId)) {
        return null;
      }

      dedupe.add(graphId);

      return {
        graph_id: graphId,
        score: clampScore(source.score),
        reason: typeof source.reason === "string" && source.reason.trim() ? source.reason.trim() : "Relevancia semantica",
      };
    })
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
    .sort((a, b) => b.score - a.score)
    .slice(0, maxResults);

  return {
    query: typeof candidate.query === "string" && candidate.query.trim() ? candidate.query.trim() : query,
    intent: typeof candidate.intent === "string" && candidate.intent.trim() ? candidate.intent.trim() : "buscar graficos relevantes",
    results,
    fallback_message:
      results.length > 0
        ? null
        : typeof candidate.fallback_message === "string" && candidate.fallback_message.trim()
          ? candidate.fallback_message.trim()
          : "Nenhum gráfico relevante encontrado",
    provider: "fallback",
  };
}

export function validateResponse(response: AISearchResponse, catalog: GraphCatalogItem[]) {
  const validIds = new Set(catalog.map((g) => g.graphId));
  return response.results.filter((r) => validIds.has(r.graph_id));
}

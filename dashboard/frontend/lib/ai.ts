import OpenAI from "openai";

import { graphCatalog } from "@/lib/graphCatalog";
import { AISearchResponse, GraphCatalogItem } from "@/types/graph";

const systemPrompt = `Voce e um assistente especializado em observabilidade.

Sua funcao e selecionar graficos relevantes com base na busca do usuario.

REGRAS:
- Responda SOMENTE em JSON
- NAO invente graficos
- USE apenas os IDs fornecidos no catalogo
- NAO explique nada fora do JSON
- Se nao houver resultado, retorne lista vazia

Criterios:
- Similaridade semantica com tags
- Utilidade pratica para diagnostico
- Contexto da busca (erro, performance, etc.)

Formato obrigatorio:
{
  "query": "...",
  "intent": "...",
  "results": [
    {
      "graph_id": "...",
      "score": 0.0,
      "reason": "..."
    }
  ],
  "fallback_message": null
}`;

const responseSchema = {
  name: "ai_graph_search_response",
  strict: true,
  schema: {
    type: "object",
    additionalProperties: false,
    required: ["query", "intent", "results", "fallback_message"],
    properties: {
      query: { type: "string" },
      intent: { type: "string" },
      fallback_message: { anyOf: [{ type: "string" }, { type: "null" }] },
      results: {
        type: "array",
        items: {
          type: "object",
          additionalProperties: false,
          required: ["graph_id", "score", "reason"],
          properties: {
            graph_id: { type: "string" },
            score: { type: "number" },
            reason: { type: "string" },
          },
        },
      },
    },
  },
} as const;

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function tokenize(text: string): string[] {
  return normalize(text)
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length > 1);
}

function localScore(query: string, graph: GraphCatalogItem): number {
  const queryTokens = tokenize(query);
  if (queryTokens.length === 0) {
    return 0;
  }

  const bag = [graph.title, graph.description, ...graph.tags].map(normalize).join(" ");
  const exactHits = queryTokens.filter((token) => bag.includes(token)).length;
  const ratio = exactHits / queryTokens.length;

  let score = ratio;

  if (bag.includes("erro") && /erro|falha|incidente|quebra/.test(normalize(query))) {
    score += 0.15;
  }
  if (bag.includes("latencia") && /latencia|tempo|resposta|performance/.test(normalize(query))) {
    score += 0.15;
  }
  if (bag.includes("cobertura") && /teste|cobertura|qualidade/.test(normalize(query))) {
    score += 0.15;
  }

  return Math.min(1, Number(score.toFixed(4)));
}

export async function aiSearchWithOpenAI(
  query: string,
  catalog: GraphCatalogItem[],
  maxResults: number,
): Promise<unknown | null> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return null;
  }

  const model = process.env.OPENAI_MODEL || "gpt-4.1-mini";
  const client = new OpenAI({ apiKey });

  const catalogForPrompt = catalog.map((item) => ({
    graph_id: item.graphId,
    title: item.title,
    description: item.description,
    tags: item.tags,
  }));

  const completion = await client.chat.completions.create({
    model,
    temperature: 0.2,
    response_format: {
      type: "json_schema",
      json_schema: responseSchema,
    },
    messages: [
      { role: "system", content: systemPrompt },
      {
        role: "user",
        content: JSON.stringify({
          query,
          max_results: maxResults,
          catalog: catalogForPrompt,
        }),
      },
    ],
  });

  const content = completion.choices[0]?.message?.content;
  if (!content) {
    return null;
  }

  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

export function aiSearchFallbackLocal(
  query: string,
  catalog: GraphCatalogItem[] = graphCatalog,
  maxResults = 5,
): AISearchResponse {
  const scored = catalog
    .map((item) => ({
      graph_id: item.graphId,
      score: localScore(query, item),
      reason: `Relevancia por tags e descricao: ${item.title}`,
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, maxResults);

  return {
    query,
    intent: "busca local por relevancia semantica",
    results: scored,
    fallback_message: scored.length ? null : "Nenhum gráfico relevante encontrado",
    provider: "fallback",
  };
}

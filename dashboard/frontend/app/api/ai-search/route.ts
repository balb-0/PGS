import { NextRequest, NextResponse } from "next/server";

import { aiSearchFallbackLocal, aiSearchWithOpenAI } from "@/lib/ai";
import { graphCatalog } from "@/lib/graphCatalog";
import { validateAndFilterResponse, validateQueryInput, validateResponse } from "@/lib/validate";

function parseMaxResults(): number {
  const raw = Number(process.env.MAX_RESULTS ?? "5");
  if (!Number.isFinite(raw)) {
    return 5;
  }
  return Math.max(1, Math.min(12, Math.trunc(raw)));
}

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const validation = validateQueryInput(payload?.query);

    if (!validation.ok) {
      return NextResponse.json({ error: validation.error }, { status: 400 });
    }

    const query = validation.query;
    const maxResults = parseMaxResults();

    let rawResult: unknown | null = null;
    let provider: "openai" | "fallback" = "fallback";

    try {
      rawResult = await aiSearchWithOpenAI(query, graphCatalog, maxResults);
      if (rawResult) {
        provider = "openai";
      }
    } catch {
      rawResult = null;
      provider = "fallback";
    }

    const normalized = validateAndFilterResponse(
      rawResult ?? aiSearchFallbackLocal(query, graphCatalog, maxResults),
      graphCatalog,
      query,
      maxResults,
    );

    normalized.results = validateResponse(normalized, graphCatalog);

    if (normalized.results.length === 0 && !normalized.fallback_message) {
      normalized.fallback_message = "Nenhum gráfico relevante encontrado";
    }

    normalized.provider = provider;

    return NextResponse.json(normalized, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Falha interna na busca inteligente",
        details: error instanceof Error ? error.message : "unknown",
      },
      { status: 500 },
    );
  }
}

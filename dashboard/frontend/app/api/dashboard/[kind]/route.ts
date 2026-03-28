import { NextRequest, NextResponse } from "next/server";

const validKinds = new Set(["business", "system-health", "testing-gap"]);

export async function GET(req: NextRequest, ctx: { params: { kind: string } }) {
  const kind = ctx.params.kind;
  if (!validKinds.has(kind)) {
    return NextResponse.json({ error: "Dashboard not found" }, { status: 404 });
  }

  const baseUrl = process.env.DASHBOARD_API_BASE_URL ?? "http://localhost:8000";
  const accountKey = process.env.DASHBOARD_ACCOUNT_KEY ?? "conta-teste-123";
  const appKey = process.env.DASHBOARD_APP_KEY ?? "app-teste-456";

  const url = new URL(`/api/v1/dashboard/${kind}`, baseUrl);
  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "account-key": accountKey,
        "app-key": appKey,
      },
      cache: "no-store",
    });

    const raw = await response.text();
    let payload: unknown;

    try {
      payload = raw ? JSON.parse(raw) : {};
    } catch {
      payload = {
        error: "Invalid backend response",
        details: raw || "empty body",
      };
    }

    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Backend unavailable",
        details: error instanceof Error ? error.message : "unknown",
      },
      { status: 503 },
    );
  }
}

import { ApiEnvelope, DashboardKind } from "@/lib/types";

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getDashboard(kind: DashboardKind, params?: Record<string, string>): Promise<ApiEnvelope> {
  const query = new URLSearchParams(params ?? {}).toString();
  const suffix = query ? `?${query}` : "";
  return getJson<ApiEnvelope>(`/api/dashboard/${kind}${suffix}`);
}

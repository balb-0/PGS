export type DashboardKind = "business" | "system-health" | "testing-gap";

export type GraphCatalogItem = {
  graphId: string;
  dashboardKind: DashboardKind;
  dashboardUid: string;
  panelId: number;
  title: string;
  description: string;
  tags: string[];
};

export type AISearchRequest = {
  query: string;
};

export type AISearchResultItem = {
  graph_id: string;
  score: number;
  reason: string;
};

export type AISearchResponse = {
  query: string;
  intent: string;
  results: AISearchResultItem[];
  fallback_message: string | null;
  provider: "openai" | "fallback";
};

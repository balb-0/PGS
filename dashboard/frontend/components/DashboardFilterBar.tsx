"use client";

import {
  COMPARE_MODE_OPTIONS,
  DashboardFilterState,
  REFRESH_OPTIONS,
  TIME_RANGE_OPTIONS,
} from "@/lib/dashboardControls";

type CategoryOption = {
  value: string;
  label: string;
};

type Props = {
  value: DashboardFilterState;
  categoryOptions: CategoryOption[];
  onChange: (patch: Partial<DashboardFilterState>) => void;
};

export function DashboardFilterBar({ value, categoryOptions, onChange }: Props) {
  const showResetSearch = value.search.trim().length > 0;

  return (
    <section className="panel reveal filter-toolbar" aria-label="Filtros globais de dashboard">
      <div className="filter-toolbar-grid">
        <label className="filter-field">
          <span>Período</span>
          <select
            id="global-filter-primary"
            value={value.timeRange}
            onChange={(event) => onChange({ timeRange: event.target.value as DashboardFilterState["timeRange"] })}
          >
            {TIME_RANGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span>Comparação</span>
          <select
            value={value.compareMode}
            onChange={(event) => onChange({ compareMode: event.target.value as DashboardFilterState["compareMode"] })}
          >
            {COMPARE_MODE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span>Atualização</span>
          <select
            value={value.refresh}
            onChange={(event) => onChange({ refresh: event.target.value as DashboardFilterState["refresh"] })}
          >
            {REFRESH_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span>Contexto</span>
          <select value={value.category} onChange={(event) => onChange({ category: event.target.value })}>
            {categoryOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="filter-search-row">
        <label className="filter-search-field">
          <span>Buscar métrica ou gráfico</span>
          <input
            type="search"
            value={value.search}
            onChange={(event) => onChange({ search: event.target.value })}
            placeholder="Ex: latência, erro, throughput..."
          />
        </label>
        {showResetSearch ? (
          <button type="button" className="ghost-action" onClick={() => onChange({ search: "" })}>
            Limpar busca
          </button>
        ) : null}
      </div>
    </section>
  );
}

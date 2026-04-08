"use client";

import { useEffect, useMemo, useState } from "react";

type ReportItem = {
  id: string;
  label: string;
  value: string;
  description: string;
  group: string;
};

type Props = {
  title: string;
  items: ReportItem[];
  filters: string[];
};

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

function buildCsv(items: ReportItem[], filters: string[]) {
  const lines = [
    ["Gerado em", new Date().toLocaleString("pt-BR")].join(";"),
    ["Filtros", filters.join(" | ")].join(";"),
    "",
    ["Grupo", "Métrica", "Valor", "Descrição"].join(";"),
    ...items.map((item) => [item.group, item.label, item.value, item.description].map((field) => `"${field.replaceAll("\"", "\"\"")}"`).join(";")),
  ];

  return lines.join("\n");
}

function download(filename: string, content: string, contentType: string) {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReportBuilder({ title, items, filters }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(items.map((item) => item.id)));
  const [statusMessage, setStatusMessage] = useState<string>("Nenhum relatório exportado ainda.");

  useEffect(() => {
    setSelectedIds(new Set(items.map((item) => item.id)));
  }, [items]);

  const selectedItems = useMemo(() => items.filter((item) => selectedIds.has(item.id)), [items, selectedIds]);

  const toggleItem = (id: string) => {
    setSelectedIds((previous) => {
      const next = new Set(previous);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set(items.map((item) => item.id)));
  const clearAll = () => setSelectedIds(new Set());

  const exportCsv = () => {
    if (selectedItems.length === 0) {
      setStatusMessage("Selecione ao menos uma métrica para exportar.");
      return;
    }

    const content = buildCsv(selectedItems, filters);
    download("relatorio-dashboard.csv", content, "text/csv;charset=utf-8;");
    setStatusMessage(`${selectedItems.length} métricas exportadas em CSV.`);
  };

  const exportPdf = () => {
    if (selectedItems.length === 0) {
      setStatusMessage("Selecione ao menos uma métrica para exportar.");
      return;
    }

    const htmlRows = selectedItems
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.group)}</td><td>${escapeHtml(item.label)}</td><td>${escapeHtml(item.value)}</td><td>${escapeHtml(item.description)}</td></tr>`,
      )
      .join("");

    const printWindow = window.open("", "_blank", "noopener,noreferrer");
    if (!printWindow) {
      setStatusMessage("Não foi possível abrir a janela de impressão.");
      return;
    }

    printWindow.document.write(`
      <html lang="pt-BR">
        <head>
          <title>Relatório - ${escapeHtml(title)}</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 24px; color: #111; }
            h1 { margin-bottom: 8px; }
            p { margin: 4px 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 16px; }
            th, td { border: 1px solid #bbb; padding: 8px; text-align: left; font-size: 12px; }
            th { background: #f2f2f2; }
          </style>
        </head>
        <body>
          <h1>${escapeHtml(title)}</h1>
          <p><strong>Gerado em:</strong> ${new Date().toLocaleString("pt-BR")}</p>
          <p><strong>Filtros ativos:</strong> ${escapeHtml(filters.join(" | "))}</p>
          <table>
            <thead>
              <tr><th>Grupo</th><th>Métrica</th><th>Valor</th><th>Descrição</th></tr>
            </thead>
            <tbody>${htmlRows}</tbody>
          </table>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
    setStatusMessage(`${selectedItems.length} métricas preparadas para PDF (impressão).`);
  };

  return (
    <section className="panel reveal report-builder" aria-label="Geração de relatórios personalizados">
      <div className="panel-head">
        <h3>Relatórios personalizados</h3>
        <button
          id="report-builder-trigger"
          type="button"
          className="ghost-action"
          onClick={() => setIsOpen((previous) => !previous)}
          aria-expanded={isOpen}
          aria-controls="report-builder-content"
        >
          {isOpen ? "Ocultar seleção" : "Selecionar métricas"}
        </button>
      </div>
      <p className="panel-inline-note">Escolha as métricas relevantes e exporte em CSV ou PDF.</p>

      {isOpen ? (
        <div id="report-builder-content" className="report-builder-content">
          <div className="report-builder-actions">
            <button type="button" className="ghost-action" onClick={selectAll}>
              Selecionar tudo
            </button>
            <button type="button" className="ghost-action" onClick={clearAll}>
              Limpar seleção
            </button>
          </div>

          <ul className="report-item-list">
            {items.map((item) => (
              <li key={item.id} className="report-item">
                <label>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.id)}
                    onChange={() => toggleItem(item.id)}
                  />
                  <span className="report-item-main">
                    <strong>{item.label}</strong>
                    <span>{item.value}</span>
                  </span>
                  <span className="report-item-description">{item.group} • {item.description}</span>
                </label>
              </li>
            ))}
          </ul>

          <div className="report-export-actions">
            <button type="button" className="search-submit" onClick={exportCsv}>
              Exportar CSV
            </button>
            <button type="button" className="search-submit" onClick={exportPdf}>
              Exportar PDF
            </button>
          </div>
        </div>
      ) : null}

      <p className="search-meta" role="status">{statusMessage}</p>
    </section>
  );
}

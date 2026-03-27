# Exec Tech Dashboards (Next.js)

> Status: camada narrativa e executiva que reutiliza paineis exportados diretamente do Grafana.

Frontend dedicado com 3 dashboards:
- `/business`
- `/system-health`
- `/ai-search`

Cada tela combina:
- KPIs e resumo textual para contexto de decisao
- Embeds diretos de paineis Grafana (`/d-solo/:uid?panelId=...`)
- Busca inteligente por linguagem natural para selecionar graficos relevantes ja existentes

## Setup

```bash
npm install
npm run dev
```

Aplicacao roda em `http://localhost:3100`.

## Variaveis de ambiente

Crie `.env.local` com:

```bash
DASHBOARD_API_BASE_URL=http://localhost:8000
DASHBOARD_ACCOUNT_KEY=conta-teste-123
DASHBOARD_APP_KEY=app-teste-456
NEXT_PUBLIC_GRAFANA_URL=http://localhost:3000
NEXT_PUBLIC_GRAFANA_THEME=dark
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
MAX_RESULTS=5
```

As credenciais de API ficam apenas no backend do Next.js (`app/api/dashboard/[kind]/route.ts`).
As variaveis `NEXT_PUBLIC_*` controlam a origem e o tema dos iframes Grafana no browser.

## Busca Inteligente (IA + fallback local)

- Endpoint: `POST /api/ai-search`
- Entrada: `{ "query": "..." }`
- Saida: JSON com `graph_id`, `score`, `reason`, `fallback_message`

Com `OPENAI_API_KEY` configurada, a rota usa OpenAI com saida estruturada em JSON.
Sem chave (ou indisponibilidade externa), o sistema entra automaticamente em fallback local por tags, sem banco de dados.

Importante:
- A busca apenas seleciona graficos existentes.
- Nenhum grafico novo e criado.
- O mecanismo de renderizacao dos cards Grafana permanece o mesmo.

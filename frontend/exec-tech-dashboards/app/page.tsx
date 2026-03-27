import Link from "next/link";

export default function HomePage() {
  return (
    <main className="page-wrap landing-wrap">
      <section className="landing-hero reveal">
        <p className="eyebrow">ASIS Intelligence Center</p>
        <h1>Plataforma de Decisão Técnica em Tempo Real</h1>
        <p className="subtitle">
          Acompanhe saúde operacional, risco de negócio e encontre gráficos com IA em uma experiência unificada.
        </p>

        <div className="landing-cta-row">
          <Link href="/business" className="landing-cta primary">Entrar em Negócio</Link>
          <Link href="/system-health" className="landing-cta">Ver Saúde do Sistema</Link>
          <Link href="/ai-search" className="landing-cta">Buscar com IA</Link>
        </div>
      </section>

      <section className="landing-grid">
        <article className="panel reveal landing-card">
          <h2>Negócio</h2>
          <p>Leitura de SLA, throughput e impacto de erro para priorização executiva.</p>
          <Link href="/business" className="landing-inline-link">Abrir dashboard</Link>
        </article>

        <article className="panel reveal landing-card">
          <h2>Saúde do Sistema</h2>
          <p>Visão operacional com erro, uptime, circuit breaker e alertas ativos.</p>
          <Link href="/system-health" className="landing-inline-link">Abrir dashboard</Link>
        </article>

        <article className="panel reveal landing-card">
          <h2>Busca IA</h2>
          <p>Descreva sua necessidade e a IA seleciona painéis relevantes já existentes.</p>
          <Link href="/ai-search" className="landing-inline-link">Abrir busca inteligente</Link>
        </article>
      </section>
    </main>
  );
}

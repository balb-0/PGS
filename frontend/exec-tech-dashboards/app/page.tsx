import Link from "next/link";

export default function HomePage() {
  return (
    <main className="page-wrap">
      <section className="top-hero reveal">
        <div>
          <p className="eyebrow">ASIS Intelligence Center</p>
          <h1>Dashboards para decisão</h1>
          <p className="subtitle">
            Três visões separadas para negócio, saúde técnica e lacunas de testes.
          </p>
        </div>
      </section>

      <section className="content-grid">
        <article className="panel reveal">
          <h2>Navegar</h2>
          <p>Escolha o dashboard de acordo com o tipo de decisão que precisa tomar agora.</p>
          <div className="topbar-nav">
            <Link href="/business" className="topbar-link">Dashboard de Negócio</Link>
            <Link href="/system-health" className="topbar-link">Dashboard de Saúde do Sistema</Link>
            <Link href="/testing-gap" className="nav-pill">Dashboard de Testes Restantes</Link>
          </div>
        </article>
      </section>
    </main>
  );
}

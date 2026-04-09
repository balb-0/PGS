<Table>
  <tr>
    <td><a href= "https://www.sankhya.com.br/software-de-gestao-erp/erp-para-gestao-empresarial/produtos/asis/"><img src="docs/img/asis.png" alt="Asis" border="0"></td>
    <td>
      <a href= "https://www.inteli.edu.br/"><img src="docs/img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0"></a>
    </td>
  </tr>
</table>

# Nome do Projeto: P.G.S (Projeto do Grupo Seis)

## Nome do Grupo: O.G.S (O Grupo Seis)

## Integrantes:

- <a href="https://www.linkedin.com/in/arthur-bretas/">Arthur Bretas Oliveira</a>
- <a href="https://www.linkedin.com/in/daviversan/">Davi D'avila Versan</a>
- <a href="https://www.linkedin.com/in/gabriel-nascimento3/">Gabriel Santos do Nascimento</a>
- <a href="https://www.linkedin.com/in/nicolasramons/">Nicolas Ramon da Silva</a>
- <a href="https://www.linkedin.com/in/otavio-vasc/">Otavio de Carvalho Vasconcelos</a>
- <a href="https://www.linkedin.com/in/vitor-balbo/">Vitor Margarido Balbo</a>
- <a href="https://www.linkedin.com/in/viniciussavian/">Vinicius dos Reis Savian</a>


## Professores:
### Orientador(a) 
- <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">Reginaldo Arakaki</a>
### Instrutores
- <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">Computação - Reginaldo</a>
- <a href="https://www.linkedin.com/in/ovidio-netto/">Computação - Ovídio</a>
- <a href="https://www.linkedin.com/in/fernando-pizzo-208b526a/">Matemática e Física - Pizzo</a>
- <a href="https://www.linkedin.com/in/pedroteberga/">Negócios - Pedro</a>
- <a href="https://www.linkedin.com/in/gui-cestari/">Design - Cestari</a> 
- <a href="https://www.linkedin.com/in/filipe-gon%C3%A7alves-08a55015b/">Liderança - Filipe Gonçalves</a>

## 📝 Descrição

Em um contexto **API First** na ASIS TaxTech, o desafio deste projeto é tratar **qualidade e resiliência como ativo de software**, garantindo que o comportamento da API permaneça correto e estável sob diferentes condições. Para isso, estruturamos uma base de **testes automatizados orientados a dados (TDD/Test Data Driven)**, com critérios objetivos (ex.: latência, integridade de payload, disponibilidade, não-repúdio) e evidências reproduzíveis, além de insumos para análises de qualidade/arquitetura/segurança e evolução para execução em **esteira de CI/CD**.

## 📝 LINKS

<a href="/docs/index.md">Link para a documentação geral</a> do projeto.
<br>
<a href="/docs/projeto.pdf">Versão em PDF do documento do projeto</a>.

## 📊 Dashboards Implementados

O repositório adota **Grafana como camada principal de decisão** com 3 dashboards separados:

- **Dashboard de Negócio**: `ASIS TaxTech - Dashboard de Negocio`
- **Dashboard de Saúde do Sistema**: `ASIS TaxTech - Dashboard de Saude do Sistema`
- **Dashboard de Testes Restantes**: `ASIS TaxTech - Dashboard de Testes Restantes`

Esses dashboards são provisionados automaticamente via Docker em `grafana/dashboards/`.

Novos endpoints backend para alimentar os dashboards:

- `GET /api/v1/dashboard/business`
- `GET /api/v1/dashboard/system-health`
- `GET /api/v1/dashboard/testing-gap`
- `GET /api/v1/dashboard/metadata`

## 📁 Estrutura de pastas

```
g06/
├─ docs/
│  ├─ index.md                          # Índice da documentação
│  ├─ projeto.md                        # Documento principal do produto
│  ├─ gestao-projeto.md                 # Gestão de sprints e riscos
│  ├─ gestao-configuração.md            # Políticas de repo e branches
│  ├─ dev-rules.md                      # Padrões de código e testes
│  ├─ dashboard.md                      # Dashboard da Qualidade (Grafana/Prometheus)
│  ├─ plano_integracao_prometheus.md    # Plano de integração Prometheus
│  ├─ catalogo_servicos_monitorados.md  # Catálogo de endpoints monitorados
│  └─ ESMD9_ASIS_TAP_2025.md           # TAP do projeto parceiro
├─ src/
│  ├─ core/
│  │  ├─ api.py                         # API FastAPI principal
│  │  ├─ metrics.py                     # Métricas Prometheus
│  │  ├─ dashboard_services.py          # Serviços de dashboard
│  │  ├─ auth_clerk.py                  # Autenticação Clerk
│  │  └─ auth_hybrid.py                 # Autenticação híbrida
│  ├─ scripts/
│  │  ├─ pytest_metrics_exporter.py     # Exporter de métricas pytest
│  │  ├─ collect_pytest_metrics.py      # Coletor de métricas
│  │  └─ verifica_versao_gitlab.py      # Sincronismo GitLab
│  └─ tests/
│     ├─ blue_team/                     # Testes de qualidade (Blue Team)
│     └─ red_team/                      # Testes adversariais (Red Team)
├─ grafana/
│  ├─ dashboards/                       # JSONs dos dashboards Grafana
│  └─ provisioning/                     # Datasources e provisioning
├─ dashboard/
│  └─ frontend/                         # App Next.js (dashboards executivos)
├─ docker-compose.yml                   # Stack Prometheus + Grafana + Alertmanager
├─ requirements.txt                     # Dependências Python
├─ pytest.ini                           # Configuração pytest
├─ sonar-project.properties             # Configuração SonarCloud
└─ README.md
```

Dentre os principais diretórios:

- **docs/**: documentação completa do projeto (produto, gestão, padrões, observabilidade).
- **src/core/**: API FastAPI, métricas Prometheus e serviços de dashboard.
- **src/tests/**: testes automatizados Blue Team (qualidade) e Red Team (adversariais).
- **grafana/**: dashboards Grafana provisionados automaticamente via Docker.
- **dashboard/frontend/**: aplicação Next.js com dashboards executivos e busca IA.
- **dashboard/execucao-dashboard.md**: guia unificado para subir API, Prometheus, Grafana e frontend.

## ✅ Requisitos

Para executar o projeto localmente, utilize as versões abaixo (ou superiores compatíveis):

- **Git**: 2.40+
- **Python**: 3.12+ (alinhado ao pipeline CI)
- **pip**: 23+
- **Node.js**: 20+
- **npm**: 10+
- **Docker Engine**: 24+
- **Docker Compose plugin**: 2.20+

Dependências Python do projeto estão em `requirements.txt` (FastAPI, pytest, pytest-cov, pytest-html, Locust, Prometheus client, JWT).

## 💻 Configuração para desenvolvimento

Para configurar o desenvolvimento da aplicação, [instale o git](https://git-scm.com/downloads) e clone esse repositório em seu computador através do comando:

```
git clone https://git.inteli.edu.br/graduacao/2026-1a/t13/g06
```

Entre na pasta do projeto e instale as dependências com versionamento de ambiente:

```bash
cd g06
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# Linux/macOS
# source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Para o frontend de dashboards:

```bash
cd dashboard/frontend
npm install
```

Em seguida siga as instruções presentes no <a href="dashboard/execucao-dashboard.md">guia de execução</a> para configurar o ambiente e subir a stack completa (API, Prometheus, Grafana e frontend).

## 🗃 Histórico de lançamentos

* 0.1.0 - 13/02/2026
    * ESPECIFICAÇÃO DOS BUSINESS DRIVERS (Documento de Negócio como Ativo de Software)
* 0.2.0 - 27/02/2026
    * REQUISITOS FUNCIONAIS E NÃO FUNCIONAIS COMO CÓDIGO
* 0.3.0 - 13/03/2026
    * ESPECIFICAÇÃO DA SOLUÇÃO TÉCNICA COMO CÓDIGO
* 0.4.0 - 27/03/2026
    * DASHBOARD DE CÓDIGOS DE QUALIDADE (Negócio, Requisitos, Soluções e demais estatísticas)
* 0.5.0 - 10/04/2026
    * PROJETO FINALIZADO STORYTELLING DO PROJETO REPOSITÓRIO ORGANIZADO


## 📋 Licença/License

<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://git.inteli.edu.br/graduacao/2026-1a/t13/g06">P.G.S (Projeto do Grupo Seis)</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://git.inteli.edu.br/graduacao/2026-1a/t13/g06">INTELI, Arthur Bretas Oliveira, Davi D'avila Versan, Gabriel Santos do Nascimento, Nicolas Ramon da Silva, Otavio de Carvalho Vasconcelos, Vitor Margarido Balbo, Vinicius dos Reis Savian</a> is licensed under <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"></a></p>
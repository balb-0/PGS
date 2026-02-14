<Table>
  <tr>
    <td><a href= "https://www.sankhya.com.br/software-de-gestao-erp/erp-para-gestao-empresarial/produtos/asis/"><img src="img/asis.png" alt="Asis" border="0"></td>
    <td>
      <a href= "https://www.inteli.edu.br/"><img src="img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0"></a>
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


# Sumário

- [1. Introdução](#1-introdução)
  - [1.1 Objetivo do Documento](#11-objetivo-do-documento)
- [2. Política de Branches](#2-política-de-branches)
  - [2.1 Visão Geral do Gitflow](#21-visão-geral-do-gitflow)
  - [2.2 Estrutura de Branches](#22-estrutura-de-branches)
  - [2.3 Diretrizes de Uso das Branches](#23-diretrizes-de-uso-das-branches)
- [3. Políticas de Commit](#3-políticas-de-commit)
- [4. Política de Push e Pull Requests](#4-política-de-push-e-pull-requests)
- [5. Infraestrutura como Código](#5-infraestrutura-como-código)
- [6. Gestão de Arquivos Sensíveis](#6-gestao-de-arquivos-sensiveis)
- [7. Política de Rollback](#7-política-de-rollback)
- [8. Registro de Variáveis de Ambiente](#8-registro-de-variáveis-de-ambiente)
- [Referências](#referências)

# 1. Introdução
Este documento descreve as práticas de **gestão de configuração** adotadas no repositório, garantindo rastreabilidade, reprodutibilidade e segurança no desenvolvimento. O foco é assegurar que a evolução do código em `src/` (API FastAPI e testes automatizados) ocorra de forma controlada, com histórico consistente e critérios mínimos de qualidade antes de integração nas branches principais.

## 1.1 Objetivo do Documento
Este documento estabelece diretrizes claras para a utilização de boas práticas no desenvolvimento de software, visando a organização e a qualidade do código. Todos os membros da equipe devem seguir as instruções definidas.

# 2. Política de Branches
As branches representam ambientes lógicos de trabalho e integração. Este repositório utiliza um fluxo inspirado em Gitflow, adaptado ao contexto do projeto: evolução rápida, porém com disciplina (revisão, testes e documentação).

## 2.1 Visão Geral do Gitflow
Gitflow é uma estratégia de branching que separa claramente o que está “estável” do que está em “evolução”, reduzindo conflitos e facilitando a integração contínua. Neste repositório, a adaptação é:

- `main`: branch estável (marcos/entregas).
- `develop`: branch de integração contínua (onde features e correções são consolidadas).
- branches de trabalho (`feat/`, `fix/`, `docs/`, `test/`, `chore/`): branches temporárias para mudanças específicas, integradas via Merge Request (MR).

## 2.2 Estrutura de Branches
Padrão de Nomenclatura das Branches:

> **main**: Contém o código pronto para produção.
> **develop**: Integração contínua das novas funcionalidades em desenvolvimento.
> **feat/[nome]**: Desenvolvimento de novas funcionalidades. Exemplo: feat/mock-api
> **fix/[nome]**: Correção de bugs. Exemplo: fix/validacao-valor
> **docs/[nome]**: Atualizações de documentação. Exemplo: docs/sumario-projeto
> **test/[nome]**: Adição/ajuste de testes. Exemplo: test/dn3-availability
> **chore/[nome]**: Tarefas operacionais (deps, configs, build). Exemplo: chore/atualiza-requirements
>
> *Opcional (quando fizer sentido):* `release/[versao]` e `hotfix/[nome]`.

## 2.3 Diretrizes de Uso das Branches
- Toda mudança deve ser feita em branch própria criada a partir de `develop`.
- A integração em `develop` deve ocorrer via **Merge Request (MR)** com revisão (GitLab).
- Commits diretos em `main` e `develop` não são permitidos (branches protegidas).
- Ao final de cada sprint, o(a) responsável pelo fechamento da sprint consolida o que está em `develop` e realiza a atualização de `main` (merge/tag conforme combinado pelo grupo).
- Recomenda-se manter branches pequenas e de curta duração, reduzindo conflito e facilitando revisão.

# 3. Políticas de Commit
Integrar "Conventional Commits" nas políticas de commit ajuda a manter um histórico de commits claro e estruturado, facilitando a automação de processos como geração de changelogs e versionamento semântico.

As mensagens de commit devem seguir o padrão de Conventional Commits para garantir clareza e consistência.

Formato: `tipo(escopo opcional): mensagem clara e descritiva`

Os tipos devem ser:

> **feat**: Uma nova funcionalidade para o usuário.
> **fix**: Correção de bug.
> **docs**: Mudanças na documentação.
> **style**: Mudanças que não afetam o significado do código (espaços em branco, formatação, etc.).
> **refactor**: Uma mudança de código que não corrige um bug nem adiciona uma funcionalidade.
> **test**: Adição ou correção de testes.
> **chore**: Atualizações de tarefas de build ou ferramentas auxiliares e bibliotecas, como a geração de documentação.

Escopos recomendados (alinhados ao repositório): `core`, `tests`, `docs`, `ci`, `deps`.

Exemplos:

- `feat(core): adicionar endpoint resiliente com circuit breaker`
- `test(tests): incluir cenários adversariais de disponibilidade (DN3)`
- `docs(docs): atualizar documentação e sumários`

Proibido:
- O uso de emojis nas mensagens de commit, e commits com mensagens vagas como "melhorias" ou "atualizações".

IMPORTANTE!
- Realizar commits frequentes (diários) para facilitar o rastreamento de mudanças e a colaboração.

# 4. Política de Push e Pull Requests

**Políticas de Push**:
- Não é permitido fazer push diretamente para `main` ou `develop`.
- Todas as contribuições devem ser feitas via branches e submetidas por meio de **Merge Requests (MR)** no GitLab.

**Regras de Push**:
- Todo código deve passar por revisão de código por pares antes de ser mergeado.
- A revisão só deve ser aprovada se os testes automatizados forem bem-sucedidos e os critérios de qualidade definidos pelo time forem atendidos.

**Revisão por Pares - Critério de Aprovação**:
- O pull request deve ser revisado por, no mínimo, uma pessoa.
- A revisão de código deve considerar: 
  - Está funcional e resolve o problema proposto.
  - Passou em todos os testes automatizados aplicáveis.
  - Não reduz qualidade (ex.: remove validações, piora contrato, quebra testes).
  - Verificação de boas práticas de código.
  - Não introduz duplicidade de código.
- Após a aprovação, a branch deve ser mergeada em `develop` e o MR pode ser concluído. 
- O(a) responsável pela sprint consolida os artefatos em `main` ao final do ciclo.

Critério mínimo de validação local (alinhado ao repositório):

- Subir a API localmente: `make run`
- Rodar suíte(s) de testes:
  - `make test-dn2`
  - `make test-nr`
  - `make test-all`


## 5. Infraestrutura como Código
O repositório padroniza o ambiente de desenvolvimento usando **Python + virtualenv** e um **Makefile** com atalhos para execução e testes, alinhado ao código em `src/`:

- Dependências: `requirements.txt`
- Execução da API (FastAPI/uvicorn): `make run` (aponta para `src.core.mock_api:app`)
- Testes automatizados (pytest):
  - `make test-dn2` (validação/integridade)
  - `make test-nr` (não-repúdio)
  - `make test-all` (suítes principais)
  - `make stress` (carga/latência)

Observação: Docker não é requisito no estado atual do repositório (não há `Dockerfile`/`docker-compose.yml`). Caso o time opte por containerização, essa seção deve ser revisada e os arquivos adicionados.

## 6. Gestão de Arquivos Sensíveis
- É obrigatório o uso de .gitignore bem configurado para bloquear:
  - Arquivos contendo senhas, segredos ou informações sensíveis.
  - Arquivos de configuração individuais (por exemplo, .env, configs locais, etc).
- Recomenda-se padronizar nomes de arquivos de configuração, quando existirem (ex.: `.env.local`, `.env.dev`, `.env.prod`), evitando commits acidentais.
- Nunca commitar dados sensíveis ou credenciais diretamente no repositório.

Alinhamento com o repositório:

- `.env` e `*.env` são ignorados.
- Pastas/arquivos típicos de credenciais (`credentials/`, `config.json`, `secrets.py`) são ignorados.

## 7. Política de Rollback
O rollback deve ser simples, rastreável e baseado no histórico Git.

- Passos mínimos recomendados:
  - Identificar rapidamente a versão estável anterior (tag/release/commit).
  - Se a mudança já foi mergeada, preferir `git revert` do merge/commit problemático (mantém histórico).
  - Aplicar a reversão via branch (`hotfix/...` ou `fix/...`) e integrar por MR.
  - Comunicar o time e stakeholders sobre a reversão.

Quando houver releases formais, recomenda-se criar tags para facilitar rollback por versão.

## 8. Registro de Variáveis de Ambiente
No estado atual do repositório, **não há variáveis de ambiente obrigatórias** para execução local (API mock e suítes de teste). Caso variáveis sejam introduzidas (por exemplo, segredos de assinatura, integrações externas ou configurações por ambiente), deve-se:

- criar um arquivo `.env.example` com as chaves necessárias (sem valores sensíveis);
- documentar finalidade e valores esperados (ex.: formato, obrigatoriedade, defaults);
- manter `.env`/`*.env` sempre ignorados pelo Git.

Exemplo de formato (quando aplicável):

- `SECRET_KEY=` # chave de assinatura/segredo (NUNCA commitada)
- `ENVIRONMENT=` # local/dev/prod

# Referências
- Conventional Commits: https://www.conventionalcommits.org/en/v1.0.0/
- GitFlow: https://nvie.com/posts/a-successful-git-branching-model/
- Gitihub/iuricode: https://github.com/iuricode/padroes-de-commits
- .gitignore (documentação oficial): https://git-scm.com/docs/gitignore
- gitignore.io (gerador de .gitignore para diferentes stacks): https://www.toptal.com/developers/gitignore/
- Handling secrets in Git repos (GitHub Guide): https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-and-storing-encrypted-secrets
- Creating a pull request template for your repository: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository
- Exemplo de Checklists para PRs: https://github.com/othneildrew/Best-README-Template#pull-request-template
- Best Practices for Rollbacks (Atlassian): https://www.atlassian.com/continuous-delivery/principles/rollback-strategies
- How to Use Git Revert and Git Reset: https://www.git-tower.com/learn/git/faq/git-reset-vs-revert/
- 12 Factor App: Config: https://12factor.net/config
- Dotenv (Exemplo e uso de arquivos .env): https://github.com/motdotla/dotenv#usage
- GitLab - Protected branches: https://docs.gitlab.com/user/project/protected_branches/
- GitLab - Merge requests: https://docs.gitlab.com/user/project/merge_requests/
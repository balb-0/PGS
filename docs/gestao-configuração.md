<Table>
  <tr>
    <td><a href= "link"><img src="img/logo.png" alt="Nome" border="0"></td>
    <td>
      <a href= "https://www.inteli.edu.br/"><img src="img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0"></a>
    </td>
  </tr>
</table>

# Nome do Projeto: <nome do projeto>

## Nome do Grupo: <nome do grupo>

## Integrantes:

- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>


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
- [8. Registro de Variáveis de Ambiente][#8-registro-de-variaveis-de-ambiente]
- [Referências](#referências)

# 1. Introdução
_conteúdo_

## 1.1 Objetivo do Documento
Este documento estabelece diretrizes claras para a utilização de boas práticas no desenvolvimento de software, visando a organização e a qualidade do código. Todos os membros da equipe devem seguir as instruções definidas.

# 2. Política de Branches
_conteúdo_

## 2.1 Visão Geral do Gitflow
Nota: Fornecer uma breve explicação sobre o Gitflow e sua importância para o gerenciamento eficiente do código fonte.

## 2.2 Estrutura de Branches
Padrão de Nomenclatura das Branches:

> **main**: Contém o código pronto para produção.
> **dev**: Integração contínua das novas funcionalidades em desenvolvimento.
> **feature/[nome-da-feature]**: Para desenvolvimento de novas funcionalidades. Exemplo: feature/integracao-api
> **bugfix/[nome-do-bug]**: Para correção de bugs. Exemplo: bugfix/corrige-login
> **release/[versao]**: Preparação para lançamento de uma nova versão. Exemplo: release/v1.0.0
> **hotfix/[nome-do-hotfix]**: Correção urgente diretamente na produção. Exemplo: hotfix/corrige-bug-em-producao

## 2.3 Diretrizes de Uso das Branches
- Cada nova funcionalidade deve ser desenvolvida em uma branch de feature criada a partir da branch develop.
  - Nomeação das branches de features deve seguir o padrão feature/[nome-da-feature].
- Todas as novas funcionalidades devem ser desenvolvidas em branches de features e integradas na branch develop através de pull requests.
- Commits diretos na branch main são proibidos! 
  - Configurem o Github para proteger de commits direto para a main.
- Branches de hotfix devem ser criadas a partir da branch main para corrigir problemas críticos em produção.
  - Nomeação das branches de hotfix deve seguir o padrão hotfix/[nome-do-hotfix].

# 3. Políticas de Commit
Integrar "Conventional Commits" nas políticas de commit ajuda a manter um histórico de commits claro e estruturado, facilitando a automação de processos como geração de changelogs e versionamento semântico.

As mensagens de commit devem seguir o padrão de Conventional Commits para garantir clareza e consistência.

Formato: [Tipo][Escopo opcional]: Mensagem clara e descritiva.

Os tipos devem ser:

> **feat**: Uma nova funcionalidade para o usuário.
> **fix**: Correção de bug.
> **docs**: Mudanças na documentação.
> **style**: Mudanças que não afetam o significado do código (espaços em branco, formatação, etc.).
> **refactor**: Uma mudança de código que não corrige um bug nem adiciona uma funcionalidade.
> **test**: Adição ou correção de testes.
> **chore**: Atualizações de tarefas de build ou ferramentas auxiliares e bibliotecas, como a geração de documentação.

Exemplo de commit: feat(auth): add login feature with JWT

Proibido:
- O uso de emojis nas mensagens de commit, e commits com mensagens vagas como "melhorias" ou "atualizações".

IMPORTANTE!
- Realizar commits frequentes (diários) para facilitar o rastreamento de mudanças e a colaboração.

# 4. Política de Push e Pull Requests

**Políticas de Push**:
- Não é permitido fazer push diretamente para a main ou dev.
- Todas as contribuições devem ser feitas via branches e submetidas por meio de pull requests.

**Regras de Push**:
- Todo código deve passar por revisão de código por pares antes de ser mergeado.
- A revisão só deve ser aprovada se os testes automatizados forem bem-sucedidos e os critérios de qualidade (cobertura de testes, análise de código) forem atendidos.

**Revisão por Pares - Critério de Aprovação**:
- O pull request deve ser revisado por, no mínimo, uma pessoa.
- A revisão de código deve considerar: 
  - Está funcional e resolve o problema proposto.
  - Passou em todos os testes automatizados.
  - Cobertura mínima de testes (60% ou mais). 
  - Verificação de boas práticas de código.
  - Não introduz duplicidade de código.
- Após a aprovação, a branch deve ser mergeada na dev e o pull request pode ser fechado. 
- O Scrum Master da Sprint é responsável por subir os artefatos para a MAIN ao final da Sprint.


## 5. Infraestrutura como Código
- Uso obrigatório de Docker para padronizar ambientes de desenvolvimento e produção.
- Incluir na raiz do repositório:
  - Dockerfile(s) para build de aplicações e serviços.
  - .dockerignore para excluir arquivos desnecessários do contexto de build.
  - docker-compose.yml para orquestrar múltiplos serviços/containers localmente.
- Cada serviço/contêiner deve ter seu próprio Dockerfile customizável, se necessário.
- O Docker Compose deve funcionar para rodar toda a stack do sistema localmente com um único comando (docker-compose up).

## 6. Gestão de Arquivos Sensíveis
- É obrigatório o uso de .gitignore bem configurado para bloquear:
  - Arquivos contendo senhas, segredos ou informações sensíveis.
  - Arquivos de configuração individuais (por exemplo, .env, configs locais, etc).
- Explicação/documentação das diferenças entre arquivos de configuração locais, de desenvolvimento e de produção (ex.: .env.local, .env.dev, .env.prod).
- Nunca commitar dados sensíveis ou credenciais diretamente no repositório.

## 7. Política de Rollback
- Documentar o processo básico para rollback de uma release defeituosa.
- Passos mínimos recomendados:
  - Identificar rapidamente a versão estável anterior (tag/release/commit).
  - Criar uma branch/selecione a tag da versão a ser restaurada.
  - Realizar o deploy dessa versão, conforme procedimento do time.
  - Comunicar o time e stakeholders sobre a reversão.
- Deixar esses procedimentos registrados no repositório (ex: docs/rollback.md).

## 8. Registro de Variáveis de Ambiente
- Obrigatório manter um arquivo .env.example documentando todas as variáveis de ambiente exigidas pela aplicação.
- O arquivo deve listar todas as keys (sem valores reais/sensíveis) e breve explicação de cada variável.
- Todos os membros devem usar esse exemplo para criar seus próprios arquivos .env locais.
- Exemplo:
  - DB_HOST= # Endereço do banco de dados
  - DB_USER= # Usuário do banco
  - DB_PASS= # Senha do banco (NUNCA commitada)
  - SECRET_KEY= # Chave secreta do sistema

# Referências
- Conventional Commits: https://www.conventionalcommits.org/en/v1.0.0/
- GitFlow: https://nvie.com/posts/a-successful-git-branching-model/
- Gitihub/iuricode: https://github.com/iuricode/padroes-de-commits
- Docker (documentação oficial): https://docs.docker.com/
- Best Practices for Writing Dockerfiles: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
- Docker Compose (documentação oficial): https://docs.docker.com/compose/
- .dockerignore Reference: https://docs.docker.com/engine/reference/builder/#dockerignore-file
- .gitignore (documentação oficial): https://git-scm.com/docs/gitignore
- gitignore.io (gerador de .gitignore para diferentes stacks): https://www.toptal.com/developers/gitignore/
- Handling secrets in Git repos (GitHub Guide): https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-and-storing-encrypted-secrets
- Creating a pull request template for your repository: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository
- Exemplo de Checklists para PRs: https://github.com/othneildrew/Best-README-Template#pull-request-template
- Best Practices for Rollbacks (Atlassian): https://www.atlassian.com/continuous-delivery/principles/rollback-strategies
- How to Use Git Revert and Git Reset: https://www.git-tower.com/learn/git/faq/git-reset-vs-revert/
- 12 Factor App: Config: https://12factor.net/config
- Dotenv (Exemplo e uso de arquivos .env): https://github.com/motdotla/dotenv#usage
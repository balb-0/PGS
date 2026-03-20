# Ponderada - Mapeamento Arquitetural RF e RNF de Seguranca

## Contexto de Dominio

Empresa digital escolhida: Nubank (fintech digital).

Dominio funcional delimitado: autorizacao de transferencia instantanea com foco em autenticidade e prevencao de fraude.

## Requisito Funcional (RF)

RF: Autorizar transferencia instantanea quando identidade for valida e o contexto de risco for aceitavel.

Criterios funcionais:
- A requisicao autenticada corretamente deve retornar 201 em fluxo valido.
- A resposta deve conter rastreabilidade minima (tracking_id) e identidade normalizada.
- O fluxo deve preservar compatibilidade com autenticacao hibrida (JWT Clerk e API key legada).

## Requisito Nao Funcional Critico (RNF)

RNF critico: Seguranca - Autenticidade e resistencia a fraude/replay.

Criterios mensuraveis:
- Taxa de aceite indevido de tokens invalidos: 0% nos cenarios de assinatura invalida.
- Ausencia de bypass em claims adulterados: 0% de autorizacao para claim forging.
- Protecao contra replay: 100% de bloqueio da segunda tentativa no cenario de ataque.

## Relacao RF -> RNF

O RF de autorizacao so e considerado atendido quando o RNF de autenticidade garante:
- integridade da identidade do ator;
- isolamento por tenant;
- rejeicao de fraude por token invalido, claim adulterado e replay.

Sem o RNF atendido, uma autorizacao 201 nao possui confiabilidade de seguranca.

Regra objetiva de decisao (RF -> RNF por status HTTP):

| Status | Decisao objetiva | Leitura RF/RNF |
| --- | --- | --- |
| 201 | Autorizacao permitida | RF atendido com RNF preservado (identidade valida e risco aceitavel) |
| 401 | Negacao por autenticidade ausente/invalida | RNF atuou para impedir aceite indevido |
| 403 | Negacao por violacao de autorizacao/tenant/claim forging | RNF atuou para bloquear escalacao de privilegio |
| 409 | Negacao por replay detectado | RNF atuou para bloquear reexecucao maliciosa |

## Taticas Arquiteturais 

- Autenticacao hibrida JWT/API key em `core.auth_hybrid.authenticate_hybrid`.
- Validacao JWT/JWKS com cache TTL em `core.auth_clerk.JWKSCache`.
- Isolamento por tenant e actor hash em `core.auth_clerk.extract_clerk_identity` e `core.api.hash_actor`.
- Protecao anti-replay em `core.api.processar_auditoria_nr` com `_replay_cache`.
- Validacoes negativas e erros tipados (401, 403, 409) para fluxos adversariais.
- Trilha de auditoria e nao-repudio com `core.api.AuditLog` e recibo digital.

## Justificativas arquiteturais causais (tatica -> risco mitigado -> evidencia)

| Tatica | Risco mitigado | Evidencia de teste |
| --- | --- | --- |
| `authenticate_hybrid` com prioridade para Bearer | Bypass por ambiguidade entre metodos de autenticacao | Cenarios BDD de falha para token invalido e red team INT3.R6 |
| `JWKSCache` + falha controlada (503) | Falha de IDP gerar autorizacao indevida ou 500 instavel | Cenario de borda com timeout JWKS e retry legitimo aprovado |
| `extract_clerk_identity` com `actor` hasheado | Vazamento de PII e colisao de identidade entre tenants | Asserts de ausencia de email/PII e diferenca de actor por tenant |
| `_replay_cache` em `processar_auditoria_nr` | Reenvio malicioso da mesma transacao | Cenario BDD de replay com segunda tentativa retornando 409 |
| `get_transaction_history` com comparacao de actor | Acesso cross-tenant a historico sensivel | Asserts de bloqueio cross-tenant com retorno 403 |



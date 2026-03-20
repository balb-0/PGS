# Ponderada - Validacao de Qualidade e Evidencias

## Matriz Cenario -> Metrica -> Evidencia

| Cenario | Metrica | Evidencia Esperada | Criterio de aceite explicito |
| --- | --- | --- | --- |
| Caminho feliz (JWT valido) | Taxa de autorizacao valida | HTTP 201, `tracking_id`, `identity.auth_type`, `identity.actor` presentes | Aprovado somente com status 201 e campos obrigatorios preenchidos |
| Edge (timeout JWKS + retry legitimo) | Continuidade segura da autorizacao | Primeira tentativa 503, retry legitimo 201 no endpoint hibrido | Aprovado somente se houver falha controlada sem 500 e recuperacao segura |
| Falha assinatura invalida | Aceite indevido de token invalido | HTTP 401 e ausencia de `tracking_id` | Aprovado somente se taxa de aceite indevido for 0% |
| Falha claim adulterado | Bypass de claims adulterados | HTTP 403 e ausencia de `tracking_id` | Aprovado somente se taxa de bypass for 0% |
| Falha replay | Bloqueio de replay | Segunda tentativa HTTP 409 com indicio de replay | Aprovado somente se bloqueio da segunda tentativa for 100% |
| Invariante LGPD | Exposicao de PII em resposta | Ausencia de email e identificadores pessoais em body de erro | Aprovado somente sem ocorrencia de PII nos cenarios de erro |
| Invariante tenant | Isolamento entre tenants | Consulta cross-tenant ao historico com HTTP 403 | Aprovado somente com bloqueio cross-tenant em 100% dos cenarios aplicaveis |

## O que é medido

- Taxa de aceitação indevida de tokens invalidos: esperado 0%.
- Taxa de bloqueio de replay no ataque: esperado 100%.
- Taxa de bloqueio cross-tenant em cenarios adversariais aplicaveis: esperado 100%.
- Consistencia de isolamento de tenant: sem colisao de actor e sem acesso cross-tenant.

## Riscos e Limitacoes

- Execucao in-process com TestClient, sem latencia real de rede/proxy/IDP.
- Nao ha HSM/KMS real para assinatura e guarda de segredos.
- Nao ha carga concorrente real no pacote Ponderada (cobertura de stress fica para Locust).
- Mocks simplificados podem gerar falso negativo ou falso positivo em corner cases de infraestrutura.

## Execucao e Verificacao

```bash
pytest Ponderada/tests -q
```

Checklist de verificacao:
- `pytest-bdd` importavel no ambiente.
- 3 tipos de cenario cobertos: feliz, borda, falha.
- side_effect aplicado para expiração/assinatura invalida/timeout JWKS/replay/claim forging.
- asserts de seguranca cobrindo status, campos obrigatorios (`tracking_id`, `identity.auth_type`, `identity.actor`), PII, cross-tenant e replay.

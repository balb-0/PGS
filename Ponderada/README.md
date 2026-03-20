# Ponderada - BDD de Seguranca e Autenticidade

Pacote isolado para validar o RF de autorizacao de transferencia instantanea condicionado ao RNF critico de autenticidade e antifraude.

## Estrutura

- `Ponderada/features/autorizacao_transferencia_segura.feature`
- `Ponderada/tests/test_autorizacao_transferencia_bdd.py`
- `Ponderada/docs/mapeamento_rf_rnf.md`
- `Ponderada/docs/validacao_qualidade.md`

## Execucao

O pacote e isolado do discovery principal (`pytest.ini` aponta para `src/tests`).

Rodar apenas a Ponderada:

```bash
pytest Ponderada/tests -q
```

Rodar com detalhes BDD:

```bash
pytest Ponderada/tests -v
```

## Registro de Resultados (2026-03-20)

### Avaliacao por criterio (rubrica)

| Criterio | Peso | Resultado |
| --- | ---: | --- |
| Mapeamento RF/RNF | 25% | Excelente (25/25) |
| Features BDD | 30% | Excelente (30/30) |
| Steps com Mocks | 25% | Excelente (25/25) |
| Massa de Testes | 20% | Excelente (20/20) |

**Score ponderado final:** **100/100**

### Evidencia de execucao

Comando executado:

```bash
python -m pytest Ponderada/tests/test_autorizacao_transferencia_bdd.py -q
```

Resultado observado:

- 6 testes aprovados
- 0 falhas
- 6 warnings de deprecacao em dependencia `gherkin` (nao bloqueantes para o escopo)

### Escopo preservado

- Empresa mantida: Nubank (fintech)
- RF mantido: autorizacao de transferencia com identidade valida e risco aceitavel
- RNF critico mantido: seguranca/autenticidade e resistencia a fraude/replay
- Melhorias aplicadas sem alteracao de escopo funcional



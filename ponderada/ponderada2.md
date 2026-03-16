# 1. Fluxo escolhido

O fluxo escolhido foi o fluxo de submissao de auditoria fiscal com geracao e afericao de contrato SPED a partir do endpoint `POST /api/v1/auditar`. No projeto, ele aparece na implementacao do endpoint em `src/core/api.py`, que valida a requisicao, tenta o envio para a ASIS e, no caminho de fallback, gera o objeto `payload_sped_gerado`; em seguida, esse contrato e aferido pelo motor `validar_layout_sped` e pelo relatorio `aferir_layout_int5` em `src/tests/blue_team/test_int5_sped_afericao.py`. Esse fluxo e adequado para a atividade porque atravessa entrada HTTP, validacao, integracao/fallback, geracao de contrato versionado e controle de qualidade codificado em testes automatizados.

---

# 2. Descricao do fluxo de ponta a ponta

O fluxo comeca quando um cliente envia uma requisicao HTTP `POST /api/v1/auditar` com os headers `account-key` e `app-key` e um payload JSON contendo `sessao_cliente`, `valor` e `destino`. O endpoint em `src/core/api.py` usa a dependencia `authenticate_request` para validar as credenciais e, em seguida, executa as validacoes de integridade do payload: presenca de campos obrigatorios, `valor` numerico maior que zero e `destino` pertencente a lista de modulos fiscais aceitos. Depois dessa validacao, o endpoint tenta integrar com a ASIS por meio da funcao assincrona `asis_upload_file`. Quando a chamada externa falha, o fluxo entra no fallback mock, registra o processo em memoria em `process_store`, gera um `tracking_id` local e monta o `payload_sped_gerado`, que representa o contrato que seria enviado ao padrao SPED/RFB. Esse contrato e entao aferido fora do endpoint pelo motor `validar_layout_sped`, que checa campos obrigatorios, tipos, tamanho e valor fixo da versao `v2026`; o relatorio `aferir_layout_int5` consolida o resultado como `CONFORME` ou `LAYOUT INVALIDO`. O resultado final esperado e a geracao de um contrato aderente ao layout previsto, com retorno HTTP `201` no endpoint e relatorio de conformidade nos testes. Os erros relevantes do fluxo sao: autenticacao ausente ou invalida, payload de entrada incompleto, `valor` invalido, `destino` fora do contrato, falha de comunicacao com o servico externo e quebra de contrato de layout durante a afericao.

---

# 3. Demonstracao do fluxo com codigo

## 3.1 Ponto de entrada do fluxo

Trecho real de `src/core/api.py`:

```python
@app.post("/api/v1/auditar", status_code=201)
async def processar_auditoria(
    auth: Dict[str, str] = Depends(authenticate_request),
    payload: Dict[str, Any] = Body(...)
):
```

Esse trecho mostra o ponto de entrada HTTP do fluxo de submissao de auditoria com geracao de contrato SPED. Ele e importante porque comprova que a integracao nasce de um contrato de API real, com dependencia de autenticacao e corpo JSON.

## 3.2 Validacao inicial e passagem entre camadas

Trecho real de `src/core/api.py`:

```python
sessao = payload.get("sessao_cliente")
volume_docs = payload.get("valor")
modulo_fiscal = payload.get("destino")

if sessao is None or modulo_fiscal is None or volume_docs is None:
    raise HTTPException(status_code=400, detail="Parâmetros obrigatórios ausentes")

if not isinstance(volume_docs, (int, float)) or math.isnan(volume_docs) or math.isinf(volume_docs) or volume_docs <= 0 or volume_docs > 1e100:
    raise HTTPException(status_code=400, detail="Valor deve ser um número maior que zero")

modulo_fiscal = validar_destino(modulo_fiscal)
```

Esse trecho vem do endpoint principal e demonstra a passagem da camada de transporte para a camada de regra de negocio. Ele e importante porque mostra que a integracao so continua apos validacao fail-fast, reduzindo custo e evitando gerar contrato invalido.

## 3.3 Logica principal de integracao e geracao do contrato SPED

Trecho real de `src/core/api.py`:

```python
try:
    real_process_id = await asis_upload_file(auth["account_key"], auth["app_key"])
    tracking_id = str(real_process_id)
except Exception as e:
    print(f"[FALLBACK] Erro na API real: {str(e)}")
    await asyncio.sleep(random.uniform(0.01, 0.1))
    tracking_id = str(uuid.uuid4())

    payload_sped_gerado = {
        "versao": "v2026",
        "cnpj_emissor": "00000000000191",
        "competencia": datetime.now(timezone.utc).strftime("%Y-%m"),
        "hash_lote": hashlib.sha256(f"{sessao}{volume_docs}{tracking_id}".encode()).hexdigest(),
        "volume_transacoes": int(volume_docs)
    }
```

Esse trecho mostra a parte mais importante do fluxo: a tentativa de comunicacao com a ASIS e, no fallback, a geracao do contrato SPED versionado. Ele comprova a integracao como codigo porque liga um evento HTTP a um contrato tecnico concreto que pode ser validado automaticamente.

## 3.4 Persistencia/rastreabilidade do processo

Trecho real de `src/core/api.py`:

```python
process_store.record_process(
    tracking_id=tracking_id,
    sessao_cliente=sessao,
    destino=modulo_fiscal,
    valor=volume_docs,
    status=ProcessStatus.CONCLUIDO,
)
```

Esse trecho registra o processamento em memoria e mostra que o fluxo nao termina apenas na resposta HTTP: ha rastreabilidade do lote processado. Isso ajuda a caracterizar o fluxo de integracao ponta a ponta.

## 3.5 Afericao do contrato de integracao

Trecho real de `src/tests/blue_team/test_int5_sped_afericao.py`:

```python
LAYOUT_RF1_V2026 = {
    "versao": {"type": str, "required": True, "value": "v2026"},
    "cnpj_emissor": {"type": str, "required": True, "length": 14},
    "competencia": {"type": str, "required": True},
    "hash_lote": {"type": str, "required": True},
    "volume_transacoes": {"type": int, "required": False},
}

def validar_layout_sped(payload: Dict[str, Any]) -> Dict[str, Any]:
    erros: List[str] = []
    for campo, regras in LAYOUT_RF1_V2026.items():
        if regras.get("required") and campo not in payload:
            erros.append(f"Campo obrigatório ausente: '{campo}'")
            continue
```

Esse trecho vem do motor de afericao do contrato SPED e demonstra o contrato formal da integracao. Ele e importante porque transforma o padrao externo em regra verificavel por codigo, com campos obrigatorios, tipo e versao.

## 3.6 Relatorio de conformidade e controle de qualidade

Trecho real de `src/tests/blue_team/test_int5_sped_afericao.py`:

```python
def aferir_layout_int5(payload_recebido: Dict[str, Any]) -> Dict[str, Any]:
    relatorio: Dict[str, Any] = {
        "integracao": "INT5_SPED_RF1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "versao_layout": EXPECTED_VERSION,
    }

    resultado_validacao = validar_layout_sped(payload_recebido)

    if resultado_validacao["valido"] is True:
        relatorio["status"] = IntegracaoStatus.CONFORME
    else:
        relatorio["status"] = IntegracaoStatus.LAYOUT_INVALIDO
        relatorio["detalhes_erros"] = resultado_validacao["erros"]
```

Esse trecho mostra como o controle de qualidade e codificado: a integracao gera um relatorio com identificacao da integracao, timestamp, versao do layout e status final. Isso atende diretamente a exigencia de documentar e codificar controle da integracao.

## 3.7 Tratamento de erro e quebra de contrato

Trecho real de `src/tests/blue_team/test_int5_sped_afericao.py`:

```python
LAYOUT_RF1_V2026["chave_nova_secreta_da_receita"] = {"type": str, "required": True}

try:
    resp = client.post("/api/v1/auditar", json=PAYLOAD_ENTRADA_ASIS_PERFEITO, headers=HEADERS_VALIDOS)
    contrato_gerado = resp.json()["payload_sped_gerado"]
    resultado_afericao = aferir_layout_int5(contrato_gerado)
    self.assertEqual(resultado_afericao["status"], IntegracaoStatus.LAYOUT_INVALIDO)
finally:
    del LAYOUT_RF1_V2026["chave_nova_secreta_da_receita"]
```

Esse trecho prova que o fluxo detecta quebra de contrato quando a versao do layout evolui e o payload antigo deixa de atender ao schema. Ele e importante porque traduz compatibilidade e excecao de integracao em codigo executavel.

## 3.8 Teste em pytest usado como evidencia

Trecho complementar criado em `src/tests/blue_team/test_int5_quality_flow.py`:

```python
async def _falha_externa_forcada(*args, **kwargs):
    raise TimeoutError("falha externa simulada para validar fallback INT5")

def test_int5_fluxo_responde_com_contrato_no_tempo_esperado(monkeypatch):
    monkeypatch.setattr(core_api, "asis_upload_file", _falha_externa_forcada)

    inicio = time.perf_counter()
    resposta = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)
    duracao = time.perf_counter() - inicio

    assert resposta.status_code == 201
    assert duracao < 1.0
    assert resposta.json()["payload_sped_gerado"]["versao"] == EXPECTED_VERSION
```

Esse trecho foi criado para complementar o barema no ponto de tempos e excecoes. Ele demonstra que, mesmo com falha do servico externo simulada, o fluxo ainda responde com contrato versionado dentro de um limite de tempo verificavel.

Para esta entrega, foram executados os arquivos `src/tests/blue_team/test_int5_sped_afericao.py` e `src/tests/blue_team/test_int5_quality_flow.py`. O primeiro comprova conformidade, quebra de contrato e estrutura do relatorio; o segundo comprova tempo de resposta, fallback controlado e tratamento de entrada invalida.

---

# 4. Estrutura de integracao

**Camadas.** O fluxo envolve a camada de apresentacao/transporte (endpoint FastAPI `POST /api/v1/auditar`), a camada de validacao de negocio (checagem de campos obrigatorios, valor e destino), a camada de integracao externa/proxy (`asis_upload_file`) e a camada de verificacao de contrato (`validar_layout_sped` e `aferir_layout_int5`).

**Modulos.** Os modulos centrais sao `src/core/api.py`, que implementa o endpoint e a geracao do contrato, e `src/tests/blue_team/test_int5_sped_afericao.py`, que implementa o motor de afericao. Como complemento de qualidade, foi adicionado `src/tests/blue_team/test_int5_quality_flow.py`.

**Componentes.** Os principais componentes sao: `authenticate_request`, `validar_destino`, `processar_auditoria`, `asis_upload_file`, `process_store`, `payload_sped_gerado`, `LAYOUT_RF1_V2026`, `validar_layout_sped` e `aferir_layout_int5`.

**Servicos.** O fluxo integra a API local ASIS/Mock, a tentativa de servico externo ASIS por HTTP e o contrato externo representado pelo padrao RFB/SPED `v2026`. Mesmo quando a RFB nao e chamada diretamente, o layout externo atua como servico/contrato de referencia da integracao.

**Hardware.** O fluxo depende de um cliente consumidor da API, de uma maquina/servidor executando Python/FastAPI e, no cenario real, de infraestrutura de rede para comunicacao com a ASIS. Em ambiente de teste, o `TestClient` executa in-process, sem rede real.

**Software.** O software envolvido inclui Python 3, FastAPI, httpx, requests, pytest, unittest e os modulos da aplicacao. O versionamento de dependencias aparece em `requirements.txt`, e a execucao automatizada dos testes aparece em `.gitlab-ci.yml`.

**Processos.** O processo de integracao e: receber requisicao -> autenticar -> validar payload -> tentar chamada externa -> aplicar fallback -> gerar contrato SPED -> registrar processo -> aferir contrato -> emitir relatorio de conformidade -> reprovar em caso de quebra de contrato.

---

# 5. Controle de qualidade da integracao

## 5.1 Tempos

Os tempos relevantes do fluxo aparecem em dois pontos. Primeiro, a chamada externa usa um `httpx.AsyncClient(timeout=0.01)` em `src/core/api.py`, o que mostra que ha uma expectativa agressiva de timeout para a integracao externa. Segundo, o fallback aplica `await asyncio.sleep(random.uniform(0.01, 0.1))`, modelando um pequeno tempo de processamento antes de devolver o contrato mockado. Para transformar isso em controle de qualidade executavel, o teste complementar `test_int5_fluxo_responde_com_contrato_no_tempo_esperado` mede a duracao ponta a ponta do fluxo com falha externa simulada e exige resposta em menos de 1 segundo. Assim, o tempo deixa de ser apenas documentado e passa a ser um criterio verificavel.

## 5.2 Protocolos

O fluxo usa HTTP como protocolo de entrada (`POST /api/v1/auditar`) e JSON como formato do payload e da resposta. A autenticacao e feita por headers `account-key` e `app-key`, definidos pelo contrato da API. Internamente, o endpoint conversa com a funcao `asis_upload_file`, que representa a integracao com a ASIS por HTTP/HTTPS. O contrato de saida mais importante do fluxo e o objeto `payload_sped_gerado`, tambem serializado em JSON, que assume o papel de artefato de integracao com o padrao SPED/RFB. No controle de qualidade, `validar_layout_sped` formaliza esse protocolo por meio de um schema codificado.

## 5.3 Versoes

As versoes aparecem em tres niveis. O primeiro e a versao da API, visivel no caminho `/api/v1/auditar`. O segundo e a versao da propria aplicacao FastAPI, registrada como `version="2.0.0"` em `app = FastAPI(...)` em `src/core/api.py`. O terceiro, e mais importante para o fluxo escolhido, e a versao do contrato externo: `v2026`, codificada tanto em `payload_sped_gerado` quanto em `EXPECTED_VERSION` e em `LAYOUT_RF1_V2026` em `src/tests/blue_team/test_int5_sped_afericao.py`. Essa combinacao permite discutir compatibilidade futura: se a Receita exigir `v2027`, o contrato atual quebrara, e os testes de afericao detectarao a incompatibilidade imediatamente.

## 5.4 Tratamento de excecoes

O fluxo trata diferentes excecoes. Na entrada, credenciais ausentes ou invalidas geram `401` ou `403` via `authenticate_request`. Na validacao de payload, campos obrigatorios ausentes geram `400`, assim como `valor` invalido e `destino` fora da lista aceita. Na integracao externa, falhas em `asis_upload_file` nao derrubam o fluxo; elas ativam o fallback mock e permitem a geracao do contrato SPED, o que representa tratamento de excecao com degradacao controlada. Na etapa de afericao, contrato invalido nao gera HTTP 500; ele gera relatorio `LAYOUT INVALIDO` com `detalhes_erros`, como nos testes que forcam campo obrigatorio novo ou versao incorreta. O teste complementar `test_int5_payload_invalido_retorna_400_sem_gerar_contrato` reforca esse comportamento ao codificar a falha esperada para entrada incompleta.

---

# 6. Como documentar esse fluxo no projeto

Neste trabalho, a documentacao do fluxo foi construida a partir do proprio caminho que o codigo percorre. O primeiro ponto documentado foi a entrada do processo em `POST /api/v1/auditar`, porque e ali que o contrato com o cliente fica explicito: headers `account-key` e `app-key`, payload JSON com `sessao_cliente`, `valor` e `destino`, e retorno `201` quando a submissao e aceita. O segundo ponto documentado foi o artefato central da integracao, `payload_sped_gerado`, pois ele representa o contrato tecnico que sera validado contra o layout SPED. Por isso, na documentacao faz sentido listar cada campo do contrato (`versao`, `cnpj_emissor`, `competencia`, `hash_lote`, `volume_transacoes`), indicar que `versao` precisa ser `v2026` e registrar que esse objeto surge no caminho de fallback mockado.

O terceiro ponto documentado foi a regra de qualidade. Em vez de deixar apenas uma orientacao abstrata, o projeto ja mostra como essa documentacao pode nascer do codigo de afericao em `src/tests/blue_team/test_int5_sped_afericao.py`: o dicionario `LAYOUT_RF1_V2026` funciona como especificacao executavel do contrato, e o relatorio de `aferir_layout_int5` funciona como evidência documentada de conformidade ou quebra. O que fizemos, portanto, foi transformar o pensamento do fluxo em tres blocos documentais concretos: contrato de entrada, contrato gerado e criterio de aceite. Isso ajuda manutencao porque qualquer mudanca no endpoint ou no layout pode ser comparada com uma referencia objetiva; ajuda testes porque os cenarios documentados ja correspondem aos testes executados; e ajuda evolucao futura porque uma migracao para `v2027`, por exemplo, exigiria atualizar o contrato, o validador e a documentacao de forma sincronizada.

---

# 7. Como codificar o controle de qualidade da integracao

No fluxo de submissao de auditoria com geracao e afericao de contrato SPED, o controle de qualidade nao ficou apenas como recomendacao; ele foi codificado em camadas bem visiveis. A primeira camada esta no proprio endpoint `processar_auditoria`, que barra entradas ruins antes de qualquer efeito colateral. Foi assim que o grupo tratou qualidade na borda da integracao: campos obrigatorios ausentes geram `400`, `valor` invalido tambem gera `400`, e `destino` passa por `validar_destino` antes da geracao do contrato. Esse desenho mostra o pensamento adotado: se o dado de entrada ja esta errado, o sistema nao deve nem chegar na etapa de gerar artefato SPED.

A segunda camada foi codificar o contrato externo como regra interna. Em `src/tests/blue_team/test_int5_sped_afericao.py`, o layout esperado foi materializado no dicionario `LAYOUT_RF1_V2026`; ou seja, a equipe nao deixou a qualidade dependente de leitura humana de documento, mas transformou a especificacao em estrutura executavel. Em seguida, `validar_layout_sped` percorre esse layout e produz erros objetivos, enquanto `aferir_layout_int5` converte o resultado em um relatorio padronizado com `integracao`, `timestamp`, `versao_layout` e `status`. O pensamento por tras disso foi simples e forte para o barema: protocolo e versao precisam existir como constantes verificaveis, e nao apenas como texto na documentacao.

A terceira camada foi codificar falhas controladas e evidencias de teste. Os testes existentes em `src/tests/blue_team/test_int5_sped_afericao.py` ja demonstravam conformidade do contrato, quebra de contrato quando um novo campo obrigatorio e introduzido e consistencia da estrutura do relatorio. Para reforcar especificamente o barema em tempos e excecoes, foi criado `src/tests/blue_team/test_int5_quality_flow.py`. Nele, a funcao `asis_upload_file` e substituida por uma falha simulada (`TimeoutError`) para reproduzir o pensamento arquitetural do fluxo: mesmo com erro externo, o fallback deve continuar funcionando e devolver um contrato valido. O teste mede o tempo da resposta, verifica o status `201`, garante a presenca de `payload_sped_gerado` e confirma a versao do contrato. Outro teste garante que entrada incompleta retorna `400` e interrompe o fluxo. Assim, o controle de qualidade foi codificado como combinacao de validacao de entrada, contrato versionado, relatorio padronizado e testes automatizados de sucesso e falha.

---

# 8. Conclusao

O fluxo de submissao de auditoria com geracao e afericao de contrato SPED atende bem a atividade porque mostra uma integracao completa e concreta: a API recebe uma requisicao, processa o lote, gera um contrato SPED versionado e valida sua conformidade por codigo. Com isso, o item (a) pode ser respondido pela descricao clara de camadas, modulos, componentes, servicos, hardware, software e processos, e o item (b) pode ser respondido por um controle de qualidade que ja existe no projeto e foi reforcado com teste automatizado de tempos, versao e tratamento de excecoes.

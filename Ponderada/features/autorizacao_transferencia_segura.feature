# language: pt
@security @critical
Funcionalidade: Autorizacao de transferencia instantanea com autenticidade reforcada
  Como uma fintech digital inspirada na Nubank
  Quero autorizar transferencias apenas com identidade valida e risco aceitavel
  Para preservar autenticidade, integridade e resistencia a fraude/replay

  @security @critical @happy_path
  Cenario: Caminho feliz com JWT valido e trilha de auditoria
    Dado um token JWT valido com identidade consistente de tenant
    Quando solicito autorizacao de transferencia no endpoint hibrido
    Entao a autorizacao deve ser aprovada com status 201
    E a resposta deve conter tracking_id e identidade segura
    E o acesso cross-tenant ao historico deve ser bloqueado com 403

  @security @critical @edge_case
  Cenario: Continuidade segura apos indisponibilidade temporaria do JWKS
    Dado um timeout de JWKS na primeira tentativa e retry legitimo por API key
    Quando reenvio a solicitacao de autorizacao no endpoint hibrido
    Entao a primeira tentativa deve falhar de forma controlada sem autorizacao indevida
    E o retry legitimo deve ser aprovado com status 201
    E o actor hash deve permanecer consistente com o tenant autenticado

  @security @critical @failure_case
  Esquema do Cenario: Falhas criticas de autenticidade e anti-fraude
    Dado um vetor de ataque "<ataque>" com side_effect "<side_effect>"
    Quando envio uma requisicao maliciosa de autorizacao
    Entao o sistema deve rejeitar com status <status_esperado>
    E os invariantes de seguranca devem permanecer preservados

    Exemplos:
      | ataque               | side_effect            | status_esperado |
      | token_expirado       | jwt_expired_token      | 401             |
      | assinatura_invalida  | jwt_invalid_signature  | 401             |
      | claim_adulterado     | identity_claim_forging | 403             |
      | replay_transacao     | replay_second_attempt  | 409             |

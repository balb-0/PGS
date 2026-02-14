import requests
import time
import json
import argparse
from datetime import datetime

# Configurações de SLA baseadas no direcionador de negócio (DN1)
SLA_ALVO_MS = 500
LIMITE_ALERTA_MS = SLA_ALVO_MS * 1.30 # 650ms (30% acima do SLA)

def executar_afericao_qualidade(url, iteracoes):
    print(f"--- Iniciando Aferição Blue Team: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    payload = {
        "sessao_cliente": "SESSAO_INTELI_G06", # Identificador da sessão
        "valor": 1000,                        # Volumetria de documentos fiscais
        "destino": "EFD_CONTRIBUICOES"        # Módulo fiscal de destino
    }
    
    # Headers obrigatórios conforme documentação oficial ASIS
    headers = {
        "account-key": "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e",
        "app-key": "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb",
        "Content-Type": "application/json"
    }

    tempos = []
    
    for i in range(iteracoes):
        try:
            inicio = time.time()
            # Chamada ao endpoint de auditoria programática
            response = requests.post(f"{url}/api/v1/auditar", json=payload, headers=headers)
            fim = (time.time() - inicio) * 1000
            
            tempos.append(fim)
            status_sla = "PASS" if fim <= SLA_ALVO_MS else "FAIL"
            
            if fim > LIMITE_ALERTA_MS:
                status_sla = "!!! ALERTA DE LENTIDÃO CRÍTICA !!!"

            if response.status_code == 201:
                dados = response.json()
                print(f"Round {i+1:02d}: {fim:6.2f}ms | ID: {dados['id']} | Status: {status_sla}")
            else:
                print(f"Round {i+1:02d}: Erro na API (Status {response.status_code})")
                
        except Exception as e:
            print(f"Round {i+1:02d}: Falha de conexão - {str(e)}")

    gerar_relatorio_final(tempos, iteracoes)

def gerar_relatorio_final(tempos, total):
    if not tempos: return
    
    media = sum(tempos) / len(tempos)
    conformidade = (len([t for t in tempos if t <= SLA_ALVO_MS]) / total) * 100
    aprovado = conformidade >= 90

    relatorio = {
        "projeto": "ESMD9 - ASIS TaxTech",
        "metricas": {
            "sla_alvo_ms": SLA_ALVO_MS,
            "latencia_media_ms": round(media, 2),
            "taxa_conformidade": f"{conformidade:.2f}%"
        },
        "resultado_final": "APROVADO" if aprovado else "REPROVADO"
    }

    print("\n" + "="*40)
    print("RELATÓRIO DE CONFORMIDADE DE NEGÓCIO")
    print(json.dumps(relatorio, indent=4))
    print("="*40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Ativo de Software - Aferição de Qualidade API ASIS')
    parser.add_argument('--url', default='http://127.0.0.1:8000', help='URL da API Mock')
    parser.add_argument('--iter', type=int, default=10, help='Número de iterações')
    args = parser.parse_args()
    
    executar_afericao_qualidade(args.url, args.iter)
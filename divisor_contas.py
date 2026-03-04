import json
import os
import math
import sys

# Cores para manter o padrão visual
class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    NEGRITO = '\033[1m'

ARQUIVO_ORIGEM = "accounts.json"
PASTA_SAIDA = "arquivos_vm"

def carregar_contas():
    if not os.path.exists(ARQUIVO_ORIGEM):
        print(f"{Cores.VERMELHO}❌ Arquivo '{ARQUIVO_ORIGEM}' não encontrado!{Cores.RESET}")
        return []
    try:
        with open(ARQUIVO_ORIGEM, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"{Cores.VERMELHO}❌ Erro ao ler JSON: {e}{Cores.RESET}")
        return []

def salvar_lote(nome_arquivo, contas):
    caminho = os.path.join(PASTA_SAIDA, nome_arquivo)
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(contas, f, indent=4)
        print(f"   💾 Salvo: {Cores.VERDE}{nome_arquivo}{Cores.RESET} ({len(contas)} contas)")
    except Exception as e:
        print(f"   ❌ Erro ao salvar {nome_arquivo}: {e}")

def executar():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"""{Cores.CIANO}
    ╔══════════════════════════════════════════════════════════════╗
    ║ ✂️  DIVISOR DE CONTAS (LOAD BALANCER) ✂️                     ║
    ╚══════════════════════════════════════════════════════════════╝
    {Cores.RESET}""")

    todas_contas = carregar_contas()
    total = len(todas_contas)
    
    if total == 0:
        input("\nNenhuma conta para dividir. Enter para voltar..."); return

    print(f"   📊 Total de contas carregadas: {Cores.AMARELO}{total}{Cores.RESET}")
    
    try:
        print(f"\n{Cores.NEGRITO}   Em quantas partes (VMs) você quer dividir?{Cores.RESET}")
        num_partes = int(input("   >> ").strip())
        
        if num_partes <= 0: raise ValueError
    except:
        print(f"\n{Cores.VERMELHO}❌ Número inválido.{Cores.RESET}")
        time.sleep(1); return

    # Garante a pasta de saída
    if not os.path.exists(PASTA_SAIDA):
        os.makedirs(PASTA_SAIDA)

    # Lógica de Divisão (Chunking)
    tamanho_lote = math.ceil(total / num_partes)
    
    print(f"\n{Cores.AMARELO}🚀 Gerando {num_partes} arquivos na pasta '{PASTA_SAIDA}'...{Cores.RESET}\n")

    for i in range(num_partes):
        inicio = i * tamanho_lote
        fim = inicio + tamanho_lote
        
        # Pega a fatia da lista
        lote_atual = todas_contas[inicio:fim]
        
        if not lote_atual: break # Se não tiver mais contas, para
        
        nome_arquivo = f"accounts_vm_{i+1}.json"
        salvar_lote(nome_arquivo, lote_atual)

    print(f"\n{Cores.VERDE}✅ Processo Concluído!{Cores.RESET}")
    print(f"   Agora copie cada arquivo gerado para a pasta raiz da respectiva VM")
    print(f"   e renomeie para 'accounts.json'.")
    
    input("\nEnter para voltar...")

if __name__ == "__main__":
    executar()
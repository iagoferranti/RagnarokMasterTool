import os
import sys
import json
import time
import requests
import subprocess
import ctypes
import re
import json_cleaner 
import provider_email
import divisor_contas
from datetime import datetime
from fabricador.modules.excluir_conta import menu_deletar_conta
import autologin.bot_login
import ctypes

try:
    import verificador_afk
except ImportError:
    verificador_afk = None

# Tenta importar premios_manager
try:
    import premios_manager
except ImportError:
    premios_manager = None



os.system('')

class Cores:
    RESET = '\033[0m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'

# ===== CONFIGURAÇÕES GLOBAIS =====
ARQUIVO_NOVAS = "novas_contas.json"
ARQUIVO_PRINCIPAL = "accounts.json"
ARQUIVO_CONFIG = "config.json"
URL_VERSION_TXT = "https://raw.githubusercontent.com/iagoferranti/ragnarok-autocheckin/main/version.txt"
URL_DOWNLOAD_EXE = "https://github.com/iagoferranti/ragnarok-autocheckin/releases/latest/download/RagnarokMasterTool.exe"

# --- UTILS DE VERSÃO ---
def _is_newer_version(local, cloud):
    nums = re.findall(r"\d+", cloud or "")
    cloud_ver = tuple(int(n) for n in nums[:4]) if nums else (0,)
    nums_loc = re.findall(r"\d+", local or "")
    local_ver = tuple(int(n) for n in nums_loc[:4]) if nums_loc else (0,)
    return cloud_ver > local_ver

def obter_versao_local():
    try:
        base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "version.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f: return f.read().strip()
    except: pass
    return "2.0.0"

VERSAO_ATUAL = obter_versao_local()

def definir_titulo():
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW(f"Ragnarok Master Tool v{VERSAO_ATUAL} | Local Mode")

# --- IMPORTAÇÃO SEGURA ---
try:
    import provider_email 
    from fabricador.main import executar as executar_fabricador
    import checkin_bot_v2
    import gerador_otp
    import uti_contas 
    MODULOS_OK = True
except ImportError as e:
    MODULOS_OK = False
    ERRO_MODULO = str(e)

def limpar_tela(): os.system('cls' if os.name == 'nt' else 'clear')

def exibir_logo():
    print(f"""{Cores.CIANO}
    ██████╗  █████╗  ██████╗     ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗ 
    ██╔══██╗██╔══██╗██╔════╝     ████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗
    ██████╔╝███████║██║  ███╗    ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝
    ██╔══██╗██╔══██║██║   ██║    ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗
    ██║  ██║██║  ██║╚██████╔╝    ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║
    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
                                {Cores.AMARELO}⚡ LATAM EDITION v{VERSAO_ATUAL} ⚡{Cores.RESET}
    """)

def carregar_config():
    if not os.path.exists(ARQUIVO_CONFIG):
        cfg = {"headless": False, "tag_email": "rag", "sobrenome_padrao": "Silva"}
        try:
            with open(ARQUIVO_CONFIG, "w") as f: json.dump(cfg, f, indent=4)
        except: pass
        return cfg
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

CONF = carregar_config()

def _is_newer_version(atual, remota):
    """Compara strings de versão simples (ex: 1.0.0 vs 1.0.1)"""
    try:
        return [int(x) for x in remota.split('.')] > [int(x) for x in atual.split('.')]
    except:
        return remota != atual

def verificar_atualizacao():
    # Só verifica se estiver rodando o .exe (frozen)
    if not getattr(sys, 'frozen', False): return

    URL_VERSION_RAW = "https://raw.githubusercontent.com/iagoferranti/RagnarokMasterTool/main/version.txt"
    URL_RELEASES = "https://github.com/iagoferranti/RagnarokMasterTool/releases"

    print(f"{Cores.CINZA}🔄 Checando updates... (v{VERSAO_ATUAL}){Cores.RESET}")
    
    try:
        r = requests.get(URL_VERSION_RAW, timeout=10)
        if r.status_code == 200:
            versao_remota = r.text.strip()
            
            if _is_newer_version(VERSAO_ATUAL, versao_remota):
                print(f"\n{Cores.AMARELO}🚨 NOVA VERSÃO DISPONÍVEL: {versao_remota}{Cores.RESET}")
                
                # Alerta sonoro ou visual (Caixa de mensagem do Windows)
                import ctypes
                import webbrowser
                
                msg = f"Uma nova versao ({versao_remota}) foi encontrada!\n\nVoce deseja baixar a atualizacao agora?"
                res = ctypes.windll.user32.MessageBoxW(0, msg, "Atualizacao Disponivel", 0x24) # 0x24 = Sim/Não + Ícone de Interrogação
                
                if res == 6: # 6 é o código para "Sim"
                    webbrowser.open(URL_RELEASES)
                    print(f"{Cores.VERDE}🚀 Abrindo pagina de downloads... O bot sera fechado.{Cores.RESET}")
                    time.sleep(2)
                    sys.exit()
            else:
                print(f"{Cores.VERDE}✅ Bot atualizado.{Cores.RESET}")
    except Exception as e:
        print(f"{Cores.VERMELHO}⚠️ Falha ao verificar update: {e}{Cores.RESET}")


if __name__ == "__main__":
    # 1. Primeiro verifica se tem update
    verificar_atualizacao()

def verificar_sessao_criacao(silencioso=False):
    if not os.path.exists(ARQUIVO_NOVAS): return 0
    try:
        with open(ARQUIVO_NOVAS, "r", encoding="utf-8") as f: novas = json.load(f)
    except: return 0
    
    validas = [c for c in novas if c.get('status') == 'PRONTA_PARA_FARMAR']
    qtd = len(validas)
    
    if not silencioso and qtd > 0:
        print(f"  -> Sessão atual: {qtd} contas prontas.")
    return qtd

# --- MENU PRINCIPAL ---
def main():
    definir_titulo()
    if not MODULOS_OK:
        print(f"Erro de Módulos: {ERRO_MODULO}"); input(); sys.exit()
    
    verificar_atualizacao()

    while True:
        limpar_tela()
        exibir_logo()
        print(f"👤 {Cores.CIANO}Admin / Local User{Cores.RESET}\n")
        
        # --- MENU COMPLETO E ATUALIZADO ---
        print(f"   {Cores.VERDE}[1]{Cores.RESET} 🏭 Fabricador de Contas")
        print(f"   {Cores.AMARELO}[2]{Cores.RESET} 👤 Fila de Criação (Manual OTP)") 
        print(f"   {Cores.CIANO}[3]{Cores.RESET} 🤖 Auto Create Char (Bot Inteligente)") # NOVO: O Bot 100% AFK
        print(f"   {Cores.VERDE}[4]{Cores.RESET} 🔐 Gerador de OTP (Só Prêmios)")      
        print(f"   {Cores.MAGENTA}[5]{Cores.RESET} 🔑 Gerador de OTP (Todas as Contas)")
        print(f"   {Cores.VERDE}[6]{Cores.RESET} 🎁 Configurar Prêmios (Manual)")      
        print(f"   {Cores.CINZA}[7]{Cores.RESET} 🐢 Farm Single (Visual)")              
        print(f"   {Cores.AMARELO}[8]{Cores.RESET} ✂️  Dividir Arquivo (VMs)")           
        print(f"   {Cores.VERMELHO}[9]{Cores.RESET} 🤖 Faxina de Bans (100% AFK)")       
        print(f"   {Cores.VERMELHO}[10]{Cores.RESET} 🗑️ Excluir Conta do Registro")     
        print(f"\n   {Cores.VERMELHO}[0]{Cores.RESET} Sair")

        opt = input("\n>> ").strip()

        # [1] FABRICADOR
        if opt == '1': 
            limpar_tela()
            try: 
                if os.path.exists(ARQUIVO_NOVAS): 
                    with open(ARQUIVO_NOVAS, "w") as f: json.dump([], f)
                executar_fabricador()
                qtd = verificar_sessao_criacao(silencioso=True)
                if qtd > 0:
                    print(f"\n{Cores.AMARELO}🚀 {qtd} Contas Novas!{Cores.RESET}")
                    time.sleep(3)
                else:
                    print(f"\n{Cores.CINZA}⚠️ Nenhuma conta nova criada. Voltando...{Cores.RESET}")
                    time.sleep(3)
            except Exception as e: print(f"Erro: {e}"); input()

        # [2] FILA DE CRIAÇÃO (MANUAL OTP)
        elif opt == '2':
            try: gerador_otp.executar(modo="apenas_novas")
            except Exception as e: print(f"Erro ao abrir Fila: {e}"); time.sleep(2)

        # [3] AUTO CREATE CHAR (BOT INTELIGENTE) - A NOVA MÁQUINA!
        elif opt == '3':
            limpar_tela()
            try:
                import autologin.bot_login
                autologin.bot_login.executar_bot_criacao()
            except Exception as e: 
                import traceback
                from datetime import datetime
                
                erro_detalhado = traceback.format_exc() # Pega o rastro completo do erro
                
                print(f"{Cores.VERMELHO}❌ Erro Crítico ao rodar o Bot Inteligente:{Cores.RESET}")
                print(e)
                print(f"\n{Cores.AMARELO}Salvando detalhes no arquivo de log...{Cores.RESET}")
                
                # Escreve o erro no TXT sem apagar os erros anteriores (modo "a" de append)
                with open("log_erros_bot.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n========================================\n")
                    f.write(f"DATA/HORA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{erro_detalhado}\n")
                
                print("✅ Log salvo em 'log_erros_bot.txt'.")
                
                # CONGELA A TELA ATÉ VOCÊ DAR ENTER
                input("\n⚠️ Pressione ENTER para voltar ao menu principal...")

        # [4] GERADOR DE OTP (SÓ PRÊMIOS)
        elif opt == '4':
            try: gerador_otp.executar(modo="premios")
            except Exception as e: print(f"Erro ao abrir Prêmios: {e}"); time.sleep(2)

        # [5] GERADOR DE OTP (TODAS AS CONTAS)
        elif opt == '5':
            try: gerador_otp.executar(modo="todos")
            except Exception as e: print(f"Erro ao abrir Lista Geral: {e}"); time.sleep(2)

        # [6] CONFIGURAR PRÊMIOS (MANUAL)
        elif opt == '6': 
            if premios_manager: premios_manager.configurar_watchlist_manual()

        # [7] FARM SINGLE (VISUAL)
        elif opt == '7': 
            if 'checkin_bot_v2' in globals(): checkin_bot_v2.executar()

        # [8] DIVIDIR ARQUIVO (VMS)
        elif opt == '8':
            if divisor_contas: divisor_contas.executar()
            else: print(f"{Cores.VERMELHO}Módulo não encontrado.{Cores.RESET}"); time.sleep(2)

        # [9] FAXINA DE BANS (AFK)
        elif opt == '9':
            if verificador_afk: verificador_afk.executar()
            else: print(f"{Cores.VERMELHO}Módulo não encontrado.{Cores.RESET}"); time.sleep(2)

        # [10] EXCLUIR CONTA DO REGISTRO
        elif opt == '10':
            menu_deletar_conta()

        # [0] SAIR
        elif opt == '0':
            break

if __name__ == "__main__":
    main()
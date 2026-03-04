# fabricador/provider_outlook.py

import time
import re
import subprocess
import sys
import os
import pyautogui
from DrissionPage.common import Keys

# Nome do arquivo de contas na raiz do projeto [cite: 10]
ARQUIVO_CONTAS = "contas_hotmail.txt"

def obter_caminho_recurso(relative_path: str) -> str:
    """Retorna o caminho absoluto para recursos, compatível com PyInstaller [cite: 11, 17]"""
    try:
        base_path = sys._MEIPASS # [cite: 18]
    except Exception:
        base_path = os.path.abspath(".") # [cite: 22, 23]
    return os.path.join(base_path, relative_path) # [cite: 19, 20]

def matar_passkey_sistema():
    """Protocolo de cancelamento de Passkey usando múltiplas camadas (ESC Global) [cite: 25, 26]"""
    print("⌨️ [Sistema] Acionando protocolo de cancelamento de Passkey...")
    
    # Camada 1: PyAutoGUI [cite: 27, 28]
    try:
        import pyautogui as _pyautogui
        _pyautogui.press("esc") # [cite: 29]
    except: pass

    # Camada 2: PyDirectInput [cite: 30, 31]
    try:
        import pydirectinput as _pydirectinput
        _pydirectinput.press("esc") # [cite: 32]
    except: pass

    # Camada 3: AutoHotkey (AHK) [cite: 33, 36]
    ahk_path = obter_caminho_recurso("AutoHotkey64.exe")
    if os.path.exists(ahk_path): # [cite: 34, 35]
        try:
            subprocess.run([ahk_path, "/ErrorStdOut", "*"], input="Send, {Esc}", encoding="utf-8", timeout=2) # [cite: 37, 39]
            print("🚀 [Sistema] ESC enviado via camada AHK.") # [cite: 40]
        except Exception as e:
            print(f"⚠️ Erro ao executar AHK: {e}") # [cite: 49, 50]
    
    time.sleep(1) # [cite: 44]

def ativar_tab(tab) -> bool:
    """Traz a aba e a janela do navegador para o foco principal [cite: 55, 58]"""
    if not tab: return False # [cite: 56]
    try:
        tab.set.activate() # [cite: 57]
        tab.set.window.to_front() # [cite: 59, 60]
        return True
    except:
        return False # [cite: 62]

class SessaoOutlook:
    """Objeto para armazenar as credenciais e a string original da conta [cite: 63, 67]"""
    def __init__(self, email: str, senha: str, full_string: str = ""):
        self.email = email # [cite: 68, 69]
        self.senha = senha # [cite: 69]
        # Atributo crucial para o Checker Web funcionar [cite: 67]
        self.full_string = full_string 

class ProviderOutlook:
    def __init__(self):
        self.contas = self._carregar_contas() # [cite: 79, 80]

    def _carregar_contas(self):
        """Lê o arquivo e preserva o token OAuth2 para o resgate """
        if not os.path.exists(ARQUIVO_CONTAS): # [cite: 82, 83]
            print(f"⚠️ Arquivo {ARQUIVO_CONTAS} não encontrado na raiz!") # [cite: 84, 85]
            return []

        contas_validas = []
        with open(ARQUIVO_CONTAS, 'r', encoding='utf-8') as f: # [cite: 87, 88]
            for linha in f:
                raw_linha = linha.strip() # [cite: 93, 94]
                if not raw_linha or 'usado' in raw_linha.lower(): continue # [cite: 91, 92]

                # Dividimos a linha pelo separador | usado no arquivo comprado [cite: 95, 96]
                partes = raw_linha.split('|')
                
                if len(partes) >= 2:
                    email = partes[0].strip() # [cite: 103]
                    senha = partes[1].strip()
                    
                    # Armazenamos os dados e a linha bruta (que contém o Token OAuth2) [cite: 151]
                    contas_validas.append({
                        'email': email,
                        'senha': senha,
                        'full_string': raw_linha
                    })
        return contas_validas

    def gerar(self) -> "SessaoOutlook | None":
        """Retira e retorna a próxima conta disponível com suporte a full_string [cite: 119]"""
        if not self.contas: return None # [cite: 120]
        
        dados = self.contas.pop(0) # [cite: 121, 122]
        return SessaoOutlook(dados['email'], dados['senha'], dados['full_string']) # [cite: 123]

    def confirmar_uso(self, sessao: SessaoOutlook) -> None:
        """Marca a conta como usada no arquivo TXT [cite: 685, 694]"""
        try:
            with open(ARQUIVO_CONTAS, "r", encoding="utf-8") as f: # [cite: 686, 688]
                linhas = f.readlines() # [cite: 689]

            with open(ARQUIVO_CONTAS, "w", encoding="utf-8") as f: # [cite: 691, 693]
                for linha in linhas:
                    if sessao.email in linha and "usado" not in linha.lower(): # [cite: 695, 697]
                        f.write(f"{linha.strip()}|usado\n") # [cite: 698, 700]
                    else:
                        f.write(linha) # [cite: 702]
            print(f"✅ [Outlook] E-mail {sessao.email} marcado como |usado.") # [cite: 705, 706]
        except Exception as e:
            print(f"⚠️ Erro ao marcar usado: {e}") # [cite: 714, 715]
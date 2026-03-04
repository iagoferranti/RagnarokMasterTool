import subprocess
import time
import json
import os
import sys
import pyotp
import win32gui
import win32con
from PIL import Image
import pyautogui
import ctypes
import win32com.client

# ============================================================
# CONFIGURAÇÕES E SUPORTE
# ============================================================
ARQUIVO_CONTAS = "accounts.json"
ARQUIVO_BANIDAS = "contas_banidas.json"
COORD_EMAIL = (0, 0)
COORD_SENHA = (0, 0)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    caminho_direto = os.path.join(base_path, relative_path)
    caminho_assets = os.path.join(base_path, "assets", relative_path)
    return caminho_assets if os.path.exists(caminho_assets) else caminho_direto

# ============================================================
# MOTOR AHK v2 (COM SUPORTE A MÚLTIPLOS ARGUMENTOS)
# ============================================================

def rodar_ahk(script_nome, *args):
    caminho_script = resource_path(script_nome)
    ahk_exe = r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe" 
    
    cmd = [ahk_exe, caminho_script]
    for arg in args:
        cmd.append(str(arg))
        
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"❌ Erro AHK: {e}")
        return False

def clicar_hardware(coords):
    print(f"   🖱️ Clique Hardware em: {coords}")
    return rodar_ahk("pressionar_tecla.ahk", coords[0], coords[1])

def digitar_interception(texto):
    print(f"   ⌨️ Digitando: {texto[:4]}***")
    return rodar_ahk("digitar.ahk", texto)

def pressionar_tecla(tecla):
    print(f"   🎹 Tecla: {tecla.upper()}")
    return rodar_ahk("pressionar_tecla.ahk", tecla)

def limpar_campo(coords):
    print(f"   🧹 Limpando campo em {coords}...")
    # Agora envia 'limpar', X e Y como 3 argumentos separados
    return rodar_ahk("pressionar_tecla.ahk", "limpar", coords[0], coords[1])

# ============================================================
# CALIBRAÇÃO E LÓGICA
# ============================================================

def resetar_posicao_janela():
    hwnd = win32gui.FindWindow(None, "Ragnarok")
    if hwnd:
        # Força a janela para o canto superior esquerdo (0, 0) 
        # ou mantenha onde você calibrou. 
        # Se você calibrou com ela no meio, não use 0,0.
        # Mas garantir que ela NÃO SE MOVEU é o segredo.
        rect = win32gui.GetWindowRect(hwnd)
        print(f"   📐 Posição atual da janela: {rect}")

def calibrar_coordenadas():
    global COORD_EMAIL, COORD_SENHA
    print("\n" + "="*50)
    print("🎯 MODO DE CALIBRAÇÃO (1440p @ 150%)")
    print("="*50)
    print("Posicione o mouse e aguarde o timer.")
    
    print("\n1. Mouse no campo EMAIL...")
    for i in range(5, 0, -1):
        print(f"Capturando em {i}s...", end="\r")
        time.sleep(1)
    COORD_EMAIL = pyautogui.position()
    print(f"✅ EMAIL: {COORD_EMAIL}")
    largura_tela, altura_tela = pyautogui.size()

    print(f"🖥️ Resolução Detectada pelo Python: {largura_tela}x{altura_tela}")

    if COORD_EMAIL[0] > largura_tela or COORD_EMAIL[0] < 0:
        print("⚠️ AVISO: O campo de e-mail parece estar em um SEGUNDO MONITOR!")

    print("\n2. Mouse no campo SENHA...")
    for i in range(5, 0, -1):
        print(f"Capturando em {i}s...", end="\r")
        time.sleep(1)
    COORD_SENHA = pyautogui.position()
    print(f"✅ SENHA: {COORD_SENHA}")
    print("\n🚀 Calibração OK! Iniciando...")

def focar_jogo():
    hwnd = win32gui.FindWindow(None, "Ragnarok")
    if hwnd:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%') 
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        if win32gui.GetForegroundWindow() == hwnd:
            print(f"✅ Foco confirmado no HWND: {hwnd}")
            return True
    return False

def detectar_imagem(nome_arquivo, confianca=0.75, timeout=5):
    caminho = resource_path(nome_arquivo)
    if not os.path.exists(caminho): return False, None
    img_obj = Image.open(caminho)
    tempo_inicial = time.time()
    while time.time() - tempo_inicial < timeout:
        try:
            pos = pyautogui.locateOnScreen(img_obj, confidence=confianca)
            if pos: return True, pos
        except: pass
        time.sleep(0.5)
    return False, None

def carregar_json(caminho):
    if not os.path.exists(caminho): return []
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# ============================================================
# EXECUÇÃO
# ============================================================

def executar():
    print("🚀 INICIANDO FAXINA DE BANS")
    calibrar_coordenadas()
    contas = carregar_json(ARQUIVO_CONTAS)
    
    idx = 0
    while idx < len(contas):
        progresso = (idx / len(contas)) * 100
        print(f"📊 Progresso: {progresso:.2f}% | Restam: {len(contas) - idx} contas")
        conta = contas[idx]
        hoje = time.strftime("%Y-%m-%d")

        # --- FILTRO DE DATA: Pula o que já foi feito hoje ---
        if conta.get('data_teste') == hoje:
            print(f"⏩ Pulando {conta['email']} (Já testada hoje)")
            idx += 1
            continue

        print(f"\n" + "="*40)
        print(f"TESTANDO [{idx+1}/{len(contas)}]: {conta['email']}")
        print("="*40)
        
        if not focar_jogo():
            print("❌ Jogo não focado. Pulando...")
            idx += 1; continue

        time.sleep(1.0) 

        # 1. EMAIL
        print(f"   🎯 Focando EMAIL: {COORD_EMAIL}")
        clicar_hardware(COORD_EMAIL)
        time.sleep(0.3)
        limpar_campo(COORD_EMAIL)
        time.sleep(0.8)
        digitar_interception(conta['email'])
        time.sleep(1.5) 
        # --- DEBUG DE MINIMIZAÇÃO ---
        time.sleep(0.5)
        hwnd_atual = win32gui.FindWindow(None, "Ragnarok")
        if hwnd_atual:
            style = win32gui.GetWindowLong(hwnd_atual, win32con.GWL_STYLE)
            if style & win32con.WS_MINIMIZE:
                print("🚨 [DETECÇÃO] A janela foi MINIMIZADA logo após o ENTER!")
                # Tira um print para você ver o que estava na tela no milissegundo do erro
                pyautogui.screenshot(f"debug_minimized_{idx}.png")

        # 2. SENHA
        print(f"   🎯 Focando SENHA: {COORD_SENHA}")
        if not focar_jogo():
            print("⚠️ Perda de foco detectada! Tentando recuperar...")
            focar_jogo()
            time.sleep(1)
        clicar_hardware(COORD_SENHA)
        time.sleep(0.3)
        limpar_campo(COORD_SENHA)
        time.sleep(0.8)
        digitar_interception(conta['password'])
        time.sleep(0.5)
        pressionar_tecla("enter")

        # --- VERIFICAÇÃO PÓS-ENTER (RECUPERAÇÃO DE MINIMIZAÇÃO) ---
        time.sleep(0.5)
        hwnd_jogo = win32gui.FindWindow(None, "Ragnarok")
        if hwnd_jogo:
            style = win32gui.GetWindowLong(hwnd_jogo, win32con.GWL_STYLE)
            if style & win32con.WS_MINIMIZE:
                print("🚨 [RECUPERAÇÃO] Janela minimizada por caractere especial! Restaurando...")
                win32gui.ShowWindow(hwnd_jogo, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd_jogo)
                time.sleep(1.0)
        
        # 3. OTP
        print("⏳ Aguardando tela de OTP...")
        encontrou_otp, _ = detectar_imagem('tela_otp.png', timeout=12)
        if encontrou_otp:
            seed = conta.get('seed_otp', '').replace(" ", "")
            if seed and seed != "SEM_OTP":
                otp = pyotp.TOTP(seed).now()
                print(f"🔑 OTP Gerado: {otp}")
                limpar_campo(COORD_EMAIL) 
                digitar_interception(otp)
                time.sleep(0.5)
                pressionar_tecla("enter")
                time.sleep(3) 
            else:
                print("⚠️ Seed OTP não encontrada.")
                idx += 1; continue
        
        # 4. VERIFICAÇÃO DE RESULTADOS
        print("🔍 Verificando resultado...")
        time.sleep(1) 
        
        # 4.1. BANIMENTO
        ban, _ = detectar_imagem('erro_5062.png', timeout=6)
        if ban:
            print("💀 STATUS: BANIDA!")
            banidas = carregar_json(ARQUIVO_BANIDAS)
            conta['data_ban'] = time.strftime("%Y-%m-%d %H:%M:%S")
            banidas.append(conta)
            salvar_json(ARQUIVO_BANIDAS, banidas)
            
            contas.pop(idx)
            salvar_json(ARQUIVO_CONTAS, contas)
            
            pressionar_tecla("enter")
            time.sleep(5) 
            continue 

        # 4.2. SENHA INCORRETA
        encontrou_senha_errada, _ = detectar_imagem('senha_incorreta.png', timeout=5)
        if encontrou_senha_errada:
            print(f"❌ STATUS: SENHA INCORRETA para {conta['email']}!")
            contas.pop(idx)
            salvar_json(ARQUIVO_CONTAS, contas)
            pressionar_tecla("enter")
            time.sleep(3)
            continue

        # --- 4. VERIFICAÇÃO DE RESULTADOS (RESILIENTE A OVERLAP) ---
        print("🔍 Verificando resultado...")
        time.sleep(1) 
        
        # 1. Checagem de Erros Graves Primeiro
        ban, _ = detectar_imagem('erro_5062.png', timeout=3)
        if ban:
            # ... (seu código de remoção de banidas)
            continue

        senha_errada, _ = detectar_imagem('senha_incorreta.png', timeout=3)
        if senha_errada:
            # ... (seu código de remoção de senha incorreta)
            continue

        # 2. Checagem de Ativas (Sucesso, Já Logada OU Timeout Precoce)
        sucesso, _ = detectar_imagem('tela_sucesso.png', timeout=4, confianca=0.8)
        ja_logada, _ = detectar_imagem('ja_testou.png', timeout=2)
        timeout_precoce, _ = detectar_imagem('timeout.png', timeout=2) # <--- A CHAVE AQUI

        if sucesso or ja_logada or timeout_precoce:
            status_msg = "ATIVA (TIMEOUT)" if timeout_precoce else ("SESSÃO ATIVA" if ja_logada else "ATIVA")
            print(f"✅ STATUS: {status_msg} para {conta['email']}")
            
            # Registra data
            conta['data_teste'] = hoje
            salvar_json(ARQUIVO_CONTAS, contas)

            # Limpeza de Tela
            if ja_logada or timeout_precoce:
                pressionar_tecla("enter")
            else:
                # Se for o sucesso padrão, aguarda o timeout normal
                foi_desconectado, _ = detectar_imagem('timeout.png', timeout=15)
                pressionar_tecla("enter")
            
            time.sleep(1.5)
            idx += 1
            continue


        print("⚠️ STATUS: INCONCLUSIVO (PULANDO)")
        idx += 1

if __name__ == "__main__":
    executar()
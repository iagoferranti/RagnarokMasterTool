import pyautogui
import time
import os
import json
import pyotp
import re
import sys
import subprocess
import random
import string
import interception
import ctypes
from datetime import datetime


# def reiniciar_jogo_completo():
#     log_status("🚨 Iniciando REBOOT do cliente Ragnarok...")
    
#     # 1. Mata o processo do jogo à força (Force Close)
#     try:
#         subprocess.run(['taskkill', '/F', '/IM', 'Ragexe.exe'], capture_output=True)
#         time.sleep(2)
#         log_status("💀 Processo encerrado com sucesso.")
#     except:
#         pass

#     # 2. Abre o jogo novamente (Caminho que você usa para abrir o Rag)
#     # Ajuste o caminho abaixo para o seu executável real
#     caminho_jogo = r"C:\123_Gravity\Ragnarok\Ragnarok.exe" 
#     try:
#         subprocess.Popen(caminho_jogo)
#         log_status("🚀 Cliente reiniciado. Aguardando 30s para carregamento...")
#         time.sleep(30) # Tempo para o jogo abrir e chegar na tela de login
#         return True
#     except Exception as e:
#         log_status(f"❌ Erro ao abrir o jogo: {e}")
#         return False

# ============================================================
# CONFIGURAÇÕES, LOGS E CAMINHOS
# ============================================================

def log_status(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [STATUS] {msg}")

def get_resource_path(filename):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    path_autologin = os.path.join(base_path, "autologin", filename)
    path_raiz = os.path.join(base_path, filename)
    return path_autologin if os.path.exists(path_autologin) else path_raiz

def get_accounts_path():
    return os.path.join(os.path.abspath("."), "accounts.json")

# ============================================================
# INICIALIZAÇÃO KERNEL E AUTO-INSTALADOR (MODO DEUS)
# ============================================================
_interception_capturado = False

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def instalar_driver_interception():
    log_status("⚠️ Driver Kernel não detectado! Iniciando instalação...")
    if not is_admin():
        print("❌ ERRO: Execute como Administrador para instalar o driver.")
        sys.exit()
    caminho_instalador = get_resource_path(os.path.join("instalador", "install-interception.exe"))
    try:
        resultado = subprocess.run([caminho_instalador, "/install"], capture_output=True, text=True)
        if "successfully" in resultado.stdout.lower() or resultado.returncode == 0:
            print("\n✅ Driver Instalado com SUCESSO! REINICIE O PC AGORA.")
            input("Pressione ENTER para fechar e reinicie o seu computador...")
            sys.exit()
    except Exception as e:
        print(f"❌ Erro crítico ao instalar driver: {e}")
        sys.exit()

def iniciar_interception_seguro():
    global _interception_capturado
    if not _interception_capturado:
        try:
            # Captura o mouse para clonar a identidade e evitar bloqueios
            interception.auto_capture_devices(keyboard=False, mouse=True)
            _interception_capturado = True
            log_status("✅ Blindagem Kernel Ativada.")
        except:
            instalar_driver_interception()

# ============================================================
# MOTOR DE HARDWARE (KERNEL E AHK)
# ============================================================

def clicar_hardware_blindado(x, y, press_time=120):
    """Clique via Kernel (Interception) - Indetectável pelo Anti-Cheat."""
    interception.move_to(int(x), int(y))
    time.sleep(0.2) 
    delay_sec = press_time / 1000.0
    interception.click(int(x), int(y), button="left", delay=delay_sec)
    time.sleep(0.1)

def afastar_mouse(coord_email=(1619, 702)):
    """Move o mouse para área neutra para evitar interferência visual (Hover)."""
    fuga_x = max(int(coord_email[0]) - 300, 100)
    fuga_y = max(int(coord_email[1]) - 350, 100)
    interception.move_to(fuga_x, fuga_y)
    time.sleep(0.1)

def rodar_ahk(script_nome, *args):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    caminho_script = os.path.join(base_path, script_nome)
    ahk_exe = os.path.join(base_path, "AutoHotkey64.exe") 
    cmd = [ahk_exe, caminho_script] + [str(arg) for arg in args]
    try:
        subprocess.run(cmd, check=True)
        return True
    except:
        return False

def digitar_interception(texto):
    return rodar_ahk("digitar.ahk", texto)

def pressionar_tecla(tecla):
    return rodar_ahk("pressionar_tecla.ahk", tecla)

def limpar_campo(coords):
    return rodar_ahk("pressionar_tecla.ahk", "limpar", int(coords[0]), int(coords[1]))

# ============================================================
# VISÃO COMPUTACIONAL PROTEGIDA (ANTI-CRASH)
# ============================================================

def imagem_esta_na_tela(nome_imagem, conf=0.80):
    try:
        if pyautogui.locateCenterOnScreen(get_resource_path(nome_imagem), confidence=conf):
            return True
    except:
        return False
    return False

def esperar_imagem(nome_imagem, timeout=20, confidence=0.85):
    caminho_img = get_resource_path(nome_imagem)
    tempo_inicial = time.time()
    while time.time() - tempo_inicial < timeout:
        try:
            posicao = pyautogui.locateCenterOnScreen(caminho_img, confidence=confidence)
            if posicao: return posicao
        except:
            pass
        time.sleep(0.5)
    return None

def fechar_erros_inesperados():
    """Vassoura de erros: Fecha janelas 'zumbis' (04-confirmar.png)."""
    try:
        pos = pyautogui.locateCenterOnScreen(get_resource_path('04-confirmar.png'), confidence=0.80)
        if pos:
            log_status("⚠️ Janela de aviso detectada. Limpando interface...")
            clicar_hardware_blindado(int(pos[0]), int(pos[1]))
            time.sleep(1.0)
            return True
    except:
        pass
    return False

# ============================================================
# LÓGICA DE DADOS E GERAÇÃO
# ============================================================

def gerar_token_fresco(seed):
    """Gera o OTP garantindo que ele não expire nos próximos segundos."""
    while True:
        segundo_atual = datetime.now().second
        if (segundo_atual >= 25 and segundo_atual <= 30) or (segundo_atual >= 55):
            time.sleep(1)
        else:
            break
    seed_clean = re.sub(r'[^A-Z2-7]', '', seed.upper().replace(" ", ""))
    totp = pyotp.TOTP(seed_clean)
    return totp.now()

def gerar_nome_aleatorio():
    parte1 = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    parte2 = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"{parte1} {parte2}"

def carregar_e_filtrar_contas():
    caminho = get_accounts_path()
    if not os.path.exists(caminho): return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            contas = json.load(f)
        return [c for c in contas if c.get('char_created') == False]
    except: return []

def remover_conta_do_json(email_alvo):
    caminho = get_accounts_path()
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            contas = json.load(f)
        contas_filtradas = [c for c in contas if c.get("email") != email_alvo]
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(contas_filtradas, f, indent=4, ensure_ascii=False)
        log_status(f"🗑️ Conta {email_alvo} removida do banco (Banida).")
    except: pass

def atualizar_status_json(email_alvo):
    caminho = get_accounts_path()
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            contas = json.load(f)
        for c in contas:
            if c.get("email") == email_alvo:
                c["char_created"] = True
                break
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(contas, f, indent=4, ensure_ascii=False)
        log_status(f"📝 Conta {email_alvo} marcada como CONCLUÍDA.")
    except: pass

# ============================================================
# ESTADOS DO JOGO
# ============================================================

def detectar_etapa_inicial():
    log_status("🔍 Analisando estado inicial do jogo...")
    tempo_limite = time.time() + 5
    
    while time.time() < tempo_limite:
        # 1. Checkpoint: Tela de Licença/Contrato (imagem 01-inicio.png ou botão 02-concordo.png)
        if imagem_esta_na_tela('01-inicio.png', conf=0.80) or imagem_esta_na_tela('02-concordo.png', conf=0.80):
            log_status("📍 Detectado: Tela de Licença/Contrato.")
            return 1 # Passo 1: Aceitar contrato
            
        # 2. Checkpoint: Seleção de Serviço (03-servico.png)
        if imagem_esta_na_tela('03-servico.png', conf=0.80):
            log_status("📍 Detectado: Seleção de Serviço.")
            return 2 # Passo 2: Escolher servidor/serviço
            
        # 3. Checkpoint: Tela de Login (Campos de Email/Senha)
        if imagem_esta_na_tela('06-email.png', conf=0.80) or imagem_esta_na_tela('05-dados.png', conf=0.75):
            log_status("📍 Detectado: Janela de Login.")
            return 3 # Passo 3: Preencher dados
            
        # 4. Checkpoint: Tela de OTP
        if imagem_esta_na_tela('09-otp.png', conf=0.80):
            log_status("📍 Detectado: Aguardando OTP.")
            return 4
            
        # 5. Checkpoint: Seleção de Servidores (Pós-Login)
        if imagem_esta_na_tela('10-servidores.png', conf=0.80):
            log_status("📍 Detectado: Seleção de Servidores.")
            return 5
            
        time.sleep(0.5)
        
    log_status("⚠️ Estado não identificado. Começando do zero (Passo 1).")
    return 1

def mapear_estado_atual():
    # Referência neutra para o mouse não tapar nada
    afastar_mouse((1619, 702))
    time.sleep(1.0)
    if imagem_esta_na_tela('21-digitar_pin.png'): return "DIGITAR_PIN"
    if imagem_esta_na_tela('17-pin1.png') or imagem_esta_na_tela('18-pin2.png'): return "CADASTRAR_PIN"
    if imagem_esta_na_tela('22-criar_char.png'):
        if imagem_esta_na_tela('24-char_criado.png', conf=0.70): return "PRONTO_PARA_ENTRAR"
        return "CRIAR_PERSONAGEM"
    if imagem_esta_na_tela('10-servidores.png'): return "SELECIONAR_SERVIDOR"
    if imagem_esta_na_tela('06-email.png'): return "LOGIN_INICIAL"
    return "DESCONHECIDO"

# ============================================================
# FLUXO DE LOGIN E PIN
# ============================================================

def iniciar_login(email, senha, seed):
    # Scanner inicial
    etapa = detectar_etapa_inicial()
    ancora = (1619, 702) 

    # Tratativa para a tela de Licença (01-inicio.png / 02-concordo.png)
    if etapa == 1:
        log_status("📜 Tela de Licença detectada. Aceitando termos...")
        pos_concordo = esperar_imagem('02-concordo.png', timeout=5)
        if pos_concordo:
            clicar_hardware_blindado(int(pos_concordo[0]), int(pos_concordo[1]))
            time.sleep(2.0)
            # Re-scaneia para ver se foi para o serviço ou login
            etapa = detectar_etapa_inicial()

    if etapa == 2:
        log_status("🖱️ Selecionando Serviço...")
        pressionar_tecla("enter")
        time.sleep(3.0)
        etapa = 3

    # Agora segue o fluxo normal de login apenas se estiver na etapa 3
    if etapa == 3:
        log_status(f"🚀 Iniciando preenchimento: {email}")
        fechar_erros_inesperados()
        
        pos_email = esperar_imagem('06-email.png', timeout=10)
        if not pos_email:
            fechar_erros_inesperados()
            pos_email = esperar_imagem('06-email.png', timeout=5)
            if not pos_email: return "ERRO", ancora
        
        ancora = pos_email
        coord_email = (pos_email[0] + 60, pos_email[1] + 15)
        clicar_hardware_blindado(coord_email[0], coord_email[1])
        time.sleep(1.0)
        limpar_campo(coord_email)
        digitar_interception(email)
        
        # Inserção Senha - Reforçada
        pos_senha = esperar_imagem('07-senha.png', timeout=5)
        if pos_senha:
            coord_senha = (pos_senha[0] + 60, pos_senha[1] + 15)
            clicar_hardware_blindado(coord_senha[0], coord_senha[1], press_time=150)
            time.sleep(1.2)
            limpar_campo(coord_senha)
            time.sleep(0.5)
            log_status("⌨️ Inserindo senha...")
            digitar_interception(senha)
            time.sleep(0.8)
        
        afastar_mouse(ancora)
        pos_conexao = esperar_imagem('conexao.png', timeout=5)
        if pos_conexao:
            log_status("🖱️ Clicando em Conexão...")
            clicar_hardware_blindado(int(pos_conexao[0]), int(pos_conexao[1]), press_time=180)
        else: 
            pressionar_tecla("enter")

    # 5. FLUXO DE OTP (Sempre acontece após o Passo 3)
    log_status("⏳ Aguardando janela de OTP aparecer...")
    pos_otp = esperar_imagem('09-otp.png', confidence=0.80, timeout=20)
    
    if pos_otp:
        time.sleep(1.0) 
        token = gerar_token_fresco(seed)
        log_status(f"🔥 OTP Gerado: {token}. Inserindo...")
        digitar_interception(token)
        time.sleep(0.5)
        pressionar_tecla("enter")
        log_status("➡️ Token enviado, aguardando validação...")
    else:
        log_status("❌ ERRO: Tela de OTP não apareceu.")
        fechar_erros_inesperados()
        return "ERRO", ancora 

    # 6. VALIDAÇÃO FINAL (BAN OU SUCESSO)
    tempo_limite = time.time() + 20
    while time.time() < tempo_limite:
        if imagem_esta_na_tela('11-ban.png'):
            log_status("💀 CONTA BANIDA!")
            pressionar_tecla("enter") 
            return "BANIDO", ancora
        if imagem_esta_na_tela('10-servidores.png'):
            log_status("✅ Servidor alcançado.")
            time.sleep(1.5) 
            pressionar_tecla("enter")
            return "SUCESSO", ancora
        if fechar_erros_inesperados(): return "ERRO", ancora
        time.sleep(0.5)
        
    return "ERRO", ancora



def digitar_pin_virtual(pin, imagem_botao_final, coord_ancora_fuga):
    log_status(f"🔢 Digitando PIN via Kernel...")
    for tentativa in range(3):
        afastar_mouse(coord_ancora_fuga)
        time.sleep(0.8)
        sucesso_digitacao = True
        for digito in pin:
            time.sleep(1.6)
            pos = None
            for sufixo in ["", "_hover"]:
                try:
                    caminho = get_resource_path(f"{digito}{sufixo}.png")
                    pos = pyautogui.locateCenterOnScreen(caminho, confidence=0.80)
                    if pos: break
                except: continue
            if pos:
                clicar_hardware_blindado(int(pos[0]), int(pos[1]), press_time=80)
                afastar_mouse(coord_ancora_fuga)
            else:
                sucesso_digitacao = False; break
        
        if sucesso_digitacao:
            time.sleep(1.0)
            pos_conf = esperar_imagem(imagem_botao_final, timeout=10)
            if pos_conf:
                clicar_hardware_blindado(int(pos_conf[0]), int(pos_conf[1]), press_time=150)
                time.sleep(3.0)
                return True
        else:
            log_status("⚠️ Falha no dígito. Resetando PIN...")
            pos_reset = esperar_imagem('reset_pin.png', timeout=3)
            if pos_reset:
                clicar_hardware_blindado(int(pos_reset[0]), int(pos_reset[1]))
                time.sleep(1.5)
    return False

def lidar_com_pin(pin_padrao="0707", coord_ancora=None):
    if coord_ancora is None: coord_ancora = (1619, 702)
    afastar_mouse(coord_ancora)
    
    estado_pin = None
    if imagem_esta_na_tela('17-pin1.png'): estado_pin = "CRIAR"
    elif imagem_esta_na_tela('21-digitar_pin.png'): estado_pin = "LOGAR"
    
    if not estado_pin: return False
    log_status(f"🔐 Protocolo PIN: {estado_pin}")
    time.sleep(2.0)

    if estado_pin == "CRIAR":
        if not digitar_pin_virtual(pin_padrao, '22-proximo.png', coord_ancora): return False
        log_status("👉 Confirmando novo PIN...")
        if not digitar_pin_virtual(pin_padrao, '19-confirmar_pin.png', coord_ancora): return False
        if esperar_imagem('20-pin_cadastrado.png', timeout=10):
            pos_c = esperar_imagem('19-confirmar_pin.png', timeout=5)
            if pos_c: clicar_hardware_blindado(int(pos_c[0]), int(pos_c[1]))
            else: pressionar_tecla("enter")
            time.sleep(4.0)

    if esperar_imagem('21-digitar_pin.png', timeout=12):
        return digitar_pin_virtual(pin_padrao, '19-confirmar_pin.png', coord_ancora)
    return False

# ============================================================
# PERSONAGEM E LOGOUT
# ============================================================

def forcar_retorno_ao_login():
    log_status("🔄 Iniciando recuperação de estado: Voltando ao Login...")
    
    # Tentativa por 30 segundos
    tempo_limite = time.time() + 30
    while time.time() < tempo_limite:
        # Checkpoint A: Já estou na tela de login?
        if imagem_esta_na_tela('06-email.png', conf=0.80):
            log_status("✅ Sucesso: Já estamos na tela de login.")
            return True

        # Checkpoint B: Estou na tela de Seleção de Personagem?
        if imagem_esta_na_tela('22-criar_char.png', conf=0.75):
            log_status("📍 Detectado: Tela de Seleção. Tentando ESC...")
            pressionar_tecla("esc")
            time.sleep(1.5)

        # Checkpoint C: A mensagem de confirmação (29-voltar.png) apareceu?
        pos_voltar = esperar_imagem('29-voltar.png', timeout=2, confidence=0.80)
        if pos_voltar:
            log_status("🎯 Mensagem de confirmação detectada. Apertando ENTER...")
            pressionar_tecla("enter")
            time.sleep(2.0)
            continue

        # Checkpoint D: O ESC falhou? Tentar o clique no 'X' (x.png) como plano B
        pos_x = pyautogui.locateCenterOnScreen(get_resource_path('x.png'), confidence=0.80)
        if pos_x:
            log_status("🖱️ ESC ignorado. Clicando no botão 'X' de fechamento...")
            clicar_hardware_blindado(int(pos_x[0]), int(pos_x[1]))
            time.sleep(1.5)

        # Checkpoint E: Tem algum erro ou aviso travando a tela?
        fechar_erros_inesperados()
        
        time.sleep(1.0)

    log_status("❌ FALHA CRÍTICA: Não foi possível retornar ao login.")
    return False

def criar_personagem():
    log_status("🎭 Iniciando criação de personagem...")
    
    for tentativa_nome in range(5): # Tenta até 5 nomes diferentes
        pos_criar = esperar_imagem('22-criar_char.png', timeout=10, confidence=0.75)
        if pos_criar:
            clicar_hardware_blindado(int(pos_criar[0]), int(pos_criar[1]))
            time.sleep(2.0)
        
        pos_nome = esperar_imagem('23-inserir_nome.png', timeout=10)
        if pos_nome:
            clicar_hardware_blindado(int(pos_nome[0]), int(pos_nome[1]))
            time.sleep(1.0)
            
            nome_tentativa = gerar_nome_aleatorio()
            log_status(f"🎲 Tentando nome: {nome_tentativa}")
            digitar_interception(nome_tentativa)
            time.sleep(0.5)
            pressionar_tecla("enter")
            
            time.sleep(2.5) # Espera o servidor validar o nome
            
            # Se aparecer o botão de confirmar, o nome foi recusado (palavrão/em uso)
            if fechar_erros_inesperados():
                log_status(f"⚠️ Nome '{nome_tentativa}' recusado. Gerando novo...")
                # Clica no campo de nome de novo para limpar
                clicar_hardware_blindado(int(pos_nome[0]), int(pos_nome[1]))
                limpar_campo((pos_nome[0], pos_nome[1]))
                continue 
            
            # Se não deu erro, verifica se o char foi criado com sucesso
            if imagem_esta_na_tela('24-char_criado.png', conf=0.70):
                pos_char = esperar_imagem('24-char_criado.png', timeout=5)
                clicar_hardware_blindado(int(pos_char[0]), int(pos_char[1]))
                time.sleep(1.0)
                
                pos_jogar = esperar_imagem('25-entrar.png', timeout=5)
                if pos_jogar:
                    clicar_hardware_blindado(int(pos_jogar[0]), int(pos_jogar[1]))
                    return True
    return False

def realizar_logout_completo():
    log_status("🚪 Iniciando Logout Controlado (Apenas ESC)...")
    
    # Passo 1: Sair do Mapa para a Seleção de Personagem
    sucesso_menu = False
    for t in range(6):
        # Se o botão 'Seleção de personagem' já apareceu, não aperta ESC de novo
        if imagem_esta_na_tela('28-selecao.png', conf=0.85):
            log_status("🎯 Menu de logout detectado.")
            sucesso_menu = True
            break
        
        log_status(f"🎹 Apertando ESC para abrir menu (Tentativa {t+1})...")
        pressionar_tecla("esc")
        time.sleep(1.8) # Tempo maior para o jogo processar o menu/daily rewards
        
        # Limpa avisos ou daily rewards que o ESC possa ter fechado antes do menu
        fechar_erros_inesperados()

    if sucesso_menu:
        pos_sel = esperar_imagem('28-selecao.png', timeout=3)
        if pos_sel:
            clicar_hardware_blindado(int(pos_sel[0]), int(pos_sel[1]))
            log_status("🖱️ Clicado em Seleção de Personagem.")
    else:
        log_status("❌ Não foi possível abrir o menu de logout.")
        return False

    # Passo 2: Sair da Seleção de Personagem para o Login
    log_status("⏳ Aguardando tela de Seleção carregar...")
    time.sleep(4.0) # Tempo para o servidor carregar a lista de chars
    
    for t in range(6):
        # Se a pergunta "Você gostaria de retornar..." já apareceu, para de apertar ESC
        if imagem_esta_na_tela('29-voltar.png', conf=0.85):
            log_status("🎯 Pergunta de retorno detectada.")
            pressionar_tecla("enter")
            time.sleep(2.0)
            break
            
        # Se já voltou para a tela de login por algum motivo, encerra
        if imagem_esta_na_tela('06-email.png', conf=0.80):
            break

        log_status(f"🎹 Apertando ESC para voltar ao Login (Tentativa {t+1})...")
        pressionar_tecla("esc")
        time.sleep(2.0)
        fechar_erros_inesperados()

    # Validação Final: Verifica se realmente caiu na tela de e-mail
    if esperar_imagem('06-email.png', timeout=10):
        log_status("✅ Logout concluído com sucesso.")
        return True
    
    return False
# ============================================================
# LOOP PRINCIPAL
# ============================================================

def executar_bot_criacao():
    iniciar_interception_seguro()
    contas = carregar_e_filtrar_contas()
    if not contas:
        log_status("✅ Nenhuma conta pendente.")
        return 

    log_status(f"🔍 Fila: {len(contas)} contas identificadas.")
    ancora_global = (1619, 702)

    for conta in contas:
        email = conta.get("email")
        senha = conta.get("password") or conta.get("senha")
        seed = conta.get("seed_otp")
        
        log_status(f"💎 Processando: {email}")
        tentativas_conta = 0
        while tentativas_conta < 2:
            fechar_erros_inesperados()
            estado = mapear_estado_atual()
            
            if estado == "LOGIN_INICIAL":
                res, anc = iniciar_login(email, senha, seed)
                if res == "BANIDO": remover_conta_do_json(email); break
                if res == "ERRO": tentativas_conta += 1; continue
                ancora_global = anc

            elif estado in ["CADASTRAR_PIN", "DIGITAR_PIN"]:
                if lidar_com_pin(pin_padrao="0707", coord_ancora=ancora_global):
                    time.sleep(2)
                else: break

            elif estado == "CRIAR_PERSONAGEM":
                # Agora a função criar_personagem() retorna True apenas se clicar em JOGAR
                if criar_personagem():
                    atualizar_status_json(email)
                    log_status(f"✨ Personagem criado. Aguardando entrada no mapa...")
                    
                    # CHECKLIST: Esperamos 8 segundos para garantir que o mapa carregou
                    time.sleep(8) 
                    entrou_no_jogo = True # Agora o bot tem permissão para deslogar
                    
                    if entrou_no_jogo:
                        log_status(f"🚀 Checklist OK: Personagem validado no mundo. Desconectando...")
                        
                        sucesso_saida = False
                        for tentativa in range(3):
                            if realizar_logout_completo():
                                sucesso_saida = True
                                break
                        
                        if sucesso_saida:
                            log_status(f"✅ Conta {email} finalizada!")
                            break

            elif estado == "PRONTO_PARA_ENTRAR":
                atualizar_status_json(email)
                realizar_logout_completo()
                break
            time.sleep(2)

if __name__ == "__main__":
    executar_bot_criacao()
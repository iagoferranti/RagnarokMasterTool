import os
import sys
import json
import time
import random
import datetime
import ctypes
import re
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys

# === INTEGRAÇÃO MODULAR ===
from fabricador import config
from fabricador.modules.logger import (
    Cores, log_sucesso, log_erro, log_aviso, log_info, log_debug, log_sistema
)
from fabricador.modules.browser import (
    clicar_com_seguranca,
    garantir_carregamento,
    medir_consumo,
    iniciar_medidor
)
from fabricador.modules.cloudflare_solver import (
    vencer_cloudflare_obrigatorio,
    checar_bloqueio_ip,
    fechar_cookies
)
from fabricador.modules.files import (
    carregar_json_seguro,
    salvar_json_seguro
)

try:
    from premios_manager import carregar_watchlist, normalizar_premio
    TEM_PREMIOS = True
except ImportError:
    TEM_PREMIOS = False

# ===== VARIÁVEIS GLOBAIS =====
def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
ARQUIVO_HISTORICO = os.path.join(BASE_DIR, "historico_diario.json")
ARQUIVO_BANCO = os.path.join(BASE_DIR, "banco_dados.json")

LOGS_SESSAO = []
SESSION_ID = None
LOG_FILE_PATH = None
PREMIOS_BRUTO_FILE_PATH = None
PREMIOS_FILTRADO_FILE_PATH = None

# --- VISUAL ---
def definir_titulo(texto):
    if os.name == 'nt':
        try: ctypes.windll.kernel32.SetConsoleTitleW(texto)
        except: pass

def exibir_banner_farm():
    print(f"""{Cores.MAGENTA}
    ╔══════════════════════════════════════════════════════════════╗
    ║ 🛡️ RAGNAROK FARM V18 - GOLDEN RULE (FAIL-SAFE) 🛡️           ║
    ╚══════════════════════════════════════════════════════════════╝
    {Cores.RESET}""")

# --- LOGS E TIMERS ---
def log_step(icone, texto, cor=Cores.RESET):
    print(f"   {cor}{icone} {texto}{Cores.RESET}")

def formatar_tempo(inicio):
    delta = time.time() - inicio
    cor = Cores.VERDE if delta < 5 else (Cores.AMARELO if delta < 10 else Cores.VERMELHO)
    return f"{cor}{delta:.2f}s{Cores.RESET}"

def log_telemetria(nome_etapa, inicio):
    print(f"      ↳ ⏱️  {nome_etapa}: {formatar_tempo(inicio)}")

def registrar_log(email, status, obs=""):
    agora = datetime.datetime.now().strftime("%H:%M:%S")
    linha = f"[{agora}] {email} -> {status} {f'({obs})' if obs else ''}"

    cor_status = Cores.VERDE if status in ["SUCESSO", "JÁ FEITO"] else Cores.VERMELHO
    if status == "EXPIRADO": cor_status = Cores.AMARELO
    icone = "✅" if status in ["SUCESSO", "JÁ FEITO"] else "❌"
    
    print(f"\n   {Cores.NEGRITO}STATUS:{Cores.RESET} {icone} {cor_status}{status}{Cores.RESET}")
    if obs: print(f"   {Cores.CINZA}OBS: {obs}{Cores.RESET}")

    LOGS_SESSAO.append(linha)
    append_log_operacional(linha)

# --- SISTEMA DE ARQUIVOS ---
def garantir_pastas_logs():
    logs_dir = os.path.join(BASE_DIR, "logs")
    premios_dir = os.path.join(BASE_DIR, "premios")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(os.path.join(premios_dir, "bruto"), exist_ok=True)
    os.makedirs(os.path.join(premios_dir, "filtrado"), exist_ok=True)
    return logs_dir, os.path.join(premios_dir, "bruto"), os.path.join(premios_dir, "filtrado")

def iniciar_sessao_logs():
    global SESSION_ID, LOG_FILE_PATH, PREMIOS_BRUTO_FILE_PATH, PREMIOS_FILTRADO_FILE_PATH
    logs_dir, pb_dir, pf_dir = garantir_pastas_logs()

    if SESSION_ID is None:
        SESSION_ID = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    LOG_FILE_PATH = os.path.join(logs_dir, f"log_execucao_{SESSION_ID}.txt")
    PREMIOS_BRUTO_FILE_PATH = os.path.join(pb_dir, f"premios_{SESSION_ID}.txt")
    PREMIOS_FILTRADO_FILE_PATH = os.path.join(pf_dir, "premios_filtrados.txt")

    if not os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"===== LOG EXECUCAO {SESSION_ID} =====\n")

def append_log_operacional(linha):
    if not LOG_FILE_PATH: iniciar_sessao_logs()
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha.rstrip() + "\n")
    except: pass

def append_log_premios_bruto(email, premios, giros):
    if not premios: return
    if not PREMIOS_BRUTO_FILE_PATH: iniciar_sessao_logs()
    try:
        agora = datetime.datetime.now().strftime("%H:%M:%S")
        premios_txt = " + ".join([str(p).strip() for p in premios if p])
        linha = f"[{agora}] {email} | giros={giros} | {premios_txt}"
        with open(PREMIOS_BRUTO_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except: pass

def append_log_premios_filtrado(email, premios, giros):
    if not premios: return
    if not PREMIOS_FILTRADO_FILE_PATH: iniciar_sessao_logs()
    try:
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        premios_txt = " + ".join(premios)
        linha = f"[{agora}] {email} | giros={giros} | {premios_txt}"
        with open(PREMIOS_FILTRADO_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except: pass

# --- HISTÓRICO ---
def carregar_historico_hoje():
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    dados = {}
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if conteudo: dados = json.loads(conteudo)
        except: dados = {}
    if not isinstance(dados, dict): dados = {}
    if dados.get("data") == hoje: return set(dados.get("contas", []))
    return set()

def adicionar_ao_historico(email):
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    dados = {}
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if conteudo: dados = json.loads(conteudo)
        except: dados = {}
    
    if not isinstance(dados, dict) or dados.get("data") != hoje:
        dados = {"data": hoje, "contas": []}
    
    if "contas" not in dados: dados["contas"] = []
    
    if email not in dados["contas"]:
        dados["contas"].append(email)
        try:
            with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
        except: pass

# --- BANCO DE DADOS (DIAS) ---
def carregar_banco_dias():
    if os.path.exists(ARQUIVO_BANCO):
        try:
            with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def atualizar_banco_dias(email, dias):
    dados = carregar_banco_dias()
    dados[email] = dias
    try:
        caminho_final = os.path.join(get_base_path(), ARQUIVO_BANCO)
        with open(caminho_final, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4)
    except Exception as e: 
        print(f"      [ERRO BANCO] Não salvou: {e}")

# --- NAVEGAÇÃO ---
def preparar_navegador_fast(page):
    try:
        page.run_cdp('Network.clearBrowserCookies')
        page.run_js('try { sessionStorage.clear(); localStorage.clear(); } catch(e) {}')
    except: pass

def digitar_rapido(page, seletor, texto):
    try:
        ele = page.ele(seletor, timeout=2)
        if ele:
            ele.input(texto)
            return True
    except: pass
    return False

def descobrir_url_evento(page):
    path = os.path.join(get_base_path(), "config_evento.json")
    agora = datetime.datetime.now()
    
    if os.path.exists(path):
        try:
            d = json.load(open(path))
            ts_salvo = d.get("ts", 0)
            data_salva = datetime.datetime.fromtimestamp(ts_salvo)
            
            # LÓGICA DO DIA 05:
            # Se hoje for dia 5 ou mais, e o mês salvo for diferente do mês atual -> EXPIRA
            # Caso contrário, mantém o link salvo (mesmo que tenha passado 24h)
            expirou = False
            if agora.day >= 5 and (agora.month != data_salva.month or agora.year != data_salva.year):
                expirou = True
            
            if not expirou:
                return d['url']
            else:
                log_step("📅", "Novo mês detectado (Dia >= 05). Solicitando novo link...", Cores.AMARELO)
                
        except: pass

    log_step("🔍", "Buscando Evento...", Cores.CIANO)
    try:
        page.get("https://www.gnjoylatam.com/pt")
        # Tenta achar o botão sozinho primeiro
        btn = page.ele('text=Máquina PonPon', timeout=5) or \
              page.ele('css:a[href*="roulette"]', timeout=2) or \
              page.ele('css:a[href*="event"]', timeout=2)
        
        if btn:
            l = btn.attr('href')
            url = l if l.startswith('http') else "https://www.gnjoylatam.com" + l
            # Salva com o timestamp de agora
            json.dump({"url": url, "ts": time.time()}, open(path, "w"))
            return url
    except: pass
    
    # Se não achou, pede pro usuário
    nova_url = input(f"{Cores.AMARELO}URL do evento não encontrada/expirada. Cole aqui: {Cores.RESET}").strip()
    if nova_url:
        json.dump({"url": nova_url, "ts": time.time()}, open(path, "w"))
    return nova_url

def obter_dias_presenca(page):
    try:
        ele_dt = page.ele('tag:dt@@text:dias de presença', timeout=1)
        if ele_dt:
            ele_span = ele_dt.parent().ele('tag:dd').ele('tag:span')
            if ele_span:
                texto = ele_span.text.strip()
                match = re.search(r'^(\d+)', texto)
                if match: return int(match.group(1))

        container = page.ele('.styles_checkin_util__mLhLp', timeout=1)
        if container:
            texto_full = container.text
            match = re.search(r'(\d+)\s*/\s*29', texto_full)
            if match: return int(match.group(1))
    except Exception: pass
    return -1

# --- LÓGICA DA ROLETA ---
def processar_roleta(page):
    premios = []
    giros_total = 0
    
    try:
        # === 1. DETECÇÃO DE GIROS ===
        qtd = 0
        # Tenta pelo texto padrão
        ele_dt = page.ele('tag:dt@@text:Tentativas disponíveis', timeout=1)
        if ele_dt:
            try: 
                ele_num = ele_dt.parent().ele('tag:dd').ele('tag:span')
                qtd = int(ele_num.text.strip())
            except: pass
        
        # Fallback: Tenta pelo container numérico isolado
        if qtd == 0:
            try:
                # Procura caixa que tem números mas não tem barras de data
                box = page.ele('.styles_checkin_util__ibfOi', timeout=1)
                if box:
                    spans = box.eles('tag:span')
                    for s in spans:
                        txt = s.text.strip()
                        if txt.isdigit() and "/" not in s.parent().text:
                            qtd = int(txt)
                            break
            except: pass

        giros_total = qtd
        
        if qtd == 0: return premios, 0
        
        log_step("🎟️", f"Giros detectados: {qtd}", Cores.AMARELO)

        # === 2. LOOP DE GIROS ===
        while qtd > 0:
            clicou = False
            
            # Tenta clicar no botão de girar (Seletores Inteligentes)
            if clicar_com_seguranca(page, 'css:button[class*="roulette_button"]', "Girar"): clicou = True
            elif clicar_com_seguranca(page, 'css:img[src*="start-button"]', "Girar (Img)"): clicou = True
            elif clicar_com_seguranca(page, 'css:button[class*="complete_button"]', "Girar (Complete)"): clicou = True

            if not clicou:
                # Força bruta JS
                try:
                    page.run_js('document.querySelector("img[src*=\'start-button\']").closest("button").click()')
                    clicou = True
                except: pass

            if not clicou:
                log_step("⚠️", "Botão de girar sumiu!", Cores.VERMELHO)
                break

            # Pequena pausa pro alerta ou animação
            time.sleep(1) 
            if page.handle_alert(accept=True): 
                qtd -= 1
                continue

            # === 3. DETECÇÃO DO PRÊMIO (ATUALIZADO) ===
            # Espera aparecer qualquer elemento que tenha "prize_object" na classe
            # Isso resolve o problema da mudança de hash (__QMyGR)
            if page.wait.ele_displayed('css:span[class*="prize_object"]', timeout=15):
                
                # Captura o texto do prêmio
                el_premio = page.ele('css:span[class*="prize_object"]')
                nm = (el_premio.text or "").strip()
                
                if nm:
                    print(f"      {Cores.MAGENTA}★ PRÊMIO: {nm}{Cores.RESET}")
                    premios.append(nm)
                
                # === 4. FECHAR POPUP (ATUALIZADO) ===
                fechou = False
                
                # Tenta fechar pelo botão que contém "btn_close" na classe
                if clicar_com_seguranca(page, 'css:button[class*="btn_close"]', "Fechar"): 
                    fechou = True
                elif clicar_com_seguranca(page, 'text:CLOSE', "Fechar Texto"): 
                    fechou = True
                
                # Fallback JS para fechar
                if not fechou:
                    page.run_js('try{document.querySelector("button[class*=\'btn_close\']").click()}catch(e){}')

                time.sleep(1.5) 
            else:
                print("      [DEBUG] Timeout esperando prêmio aparecer.")
                # Se girou mas o prêmio não apareceu, pode ter travado ou acabado os giros
                # Vamos tentar ler a qtd de novo pra ver se decrementou
            
            # Atualiza a quantidade real lendo da tela
            qtd -= 1
            try:
                # Re-lê o número na tela para garantir sincronia
                ele_dt = page.ele('tag:dt@@text:Tentativas disponíveis', timeout=0.5)
                if ele_dt:
                    qtd = int(ele_dt.parent().ele('tag:dd').ele('tag:span').text.strip())
            except: pass

    except Exception as e: 
        print(f"Erro crítico na roleta: {e}")
        pass
        
    return premios, giros_total

# --- FLUXO PRINCIPAL (V18 - GOLDEN RULE) ---
def processar(page, conta, url, index, total):
    email = conta['email']
    definir_titulo(f"Farm | {index}/{total} | {email}")
    t_conta_inicio = time.time()
    
    banco_dias = carregar_banco_dias()
    dias_registrados = banco_dias.get(email, "?")
    
    txt = f" 👤 CONTA {str(index).zfill(2)}/{str(total).zfill(2)}: {email} (Dias: {dias_registrados}) "
    w = max(len(txt), 60)
    print(f"\n{Cores.AZUL}┌{'─'*w}┐")
    print(f"│{Cores.RESET}{txt}{' '*(w-len(txt))}{Cores.AZUL}│")
    print(f"└{'─'*w}┘{Cores.RESET}")
    
    sucesso_conta = False
    log_st = "ERRO" 
    msg = ""
    
    try:
        preparar_navegador_fast(page)
        t_load = time.time()
        page.get(url)
        log_telemetria("Load URL", t_load)
        
        # LOGIN V18: ESTRATÉGIA "GOLDEN RULE"
        if page.ele('#email', timeout=1) or page.ele('@alt=LOGIN BUTTON', timeout=1) or page.ele('text:Login', timeout=1):
            if page.ele('@alt=LOGIN BUTTON'): page.ele('@alt=LOGIN BUTTON').click()
            elif page.ele('text:Login'):
                 try: page.ele('.header_loginBtn__Wd2K_').click()
                 except: pass

            t_cf = time.time()
            if garantir_carregamento(page, '#email', timeout=40):
                
                # 1. ESPERA OBRIGATÓRIA (3s a 5s)
                # Dá tempo ao site e ao Cloudflare se entenderem sem interferência
                log_step("⏳", "Aguardando verificação (3-5s)...", Cores.CINZA)
                time.sleep(random.randint(3, 5))
                
                # 2. VERIFICAÇÃO BINÁRIA (A REGRA DE OURO)
                # Só passa se o texto de SUCESSO estiver VISÍVEL. Caso contrário, SOLVER.
                texto_sucesso = page.ele('text:Verificação de segurança para acesso concluída', timeout=1)
                
                if texto_sucesso and texto_sucesso.states.is_displayed:
                    # SINAL VERDE
                    log_telemetria("CF Auto-Resolvido", t_cf)
                else:
                    # SINAL VERMELHO (Qualquer outra coisa = Solver)
                    log_step("🛡️", "Verificação pendente. Ativando Solver...", Cores.AMARELO)
                    if not vencer_cloudflare_obrigatorio(page):
                         log_st = "ERRO CF"
                         raise Exception("Falha Cloudflare")
                    log_telemetria("CF Resolvido Manualmente", t_cf)

                # SEGUINDO LOGIN...
                digitar_rapido(page, '#email', email)
                digitar_rapido(page, '#password', conta['password'])
                
                t_login_click = time.time()
                
                # Clique único com espera (V17 Logic)
                log_in_success = False
                for tentativa in range(1, 4):
                    clicou = False
                    if clicar_com_seguranca(page, '.page_loginBtn__JUYeS', "Entrar"): clicou = True
                    elif clicar_com_seguranca(page, 'text=CONTINUAR', "Continuar"): clicou = True
                    if not clicou: page.actions.key_down(Keys.ENTER).key_up(Keys.ENTER)
                    
                    if page.wait.ele_displayed('text:Logout', timeout=6):
                        log_in_success = True
                        break
                    
                    # Se reaparecer iframe, resolve de novo
                    if page.ele('xpath://iframe[contains(@src, "turnstile")]', timeout=1):
                         if page.ele('xpath://iframe[contains(@src, "turnstile")]').states.is_displayed:
                             vencer_cloudflare_obrigatorio(page)
                
                if log_in_success:
                    log_telemetria("Login Sucesso", t_login_click)
                    if "event" not in page.url: page.get(url)
                else:
                    erro = page.ele('.input_errorMsg__hM_98', timeout=1)
                    if erro: raise Exception(f"Erro Login: {erro.text}")
                    else: raise Exception("Timeout Login")
            else: raise Exception("Formulário não carregou")
        
        dias_atuais = obter_dias_presenca(page)
        
        t_checkin = time.time()
        btn_check = page.ele('tag:img@@alt=attendance button', timeout=3) or page.ele('text:FAZER CHECK-IN', timeout=2)
        check_in_ok = False

        if btn_check:
            src = str(btn_check.attr("src") or "")
            if "complete" in src:
                log_st = "JÁ FEITO"
                check_in_ok = True
            else:
                btn_check.click()
                for _ in range(10): 
                    time.sleep(0.5)
                    if "complete" in str(btn_check.attr("src") or ""):
                        log_st = "SUCESSO"
                        check_in_ok = True
                        log_step("📅", "Check-in Visual OK", Cores.VERDE)
                        if dias_atuais != -1: dias_atuais += 1 
                        break
                    alerta = page.handle_alert(accept=True)
                    if alerta:
                        if "not" in alerta.lower() or "período" in alerta.lower():
                            log_st = "EXPIRADO"
                            msg = alerta
                        else:
                            log_st = "SUCESSO"
                            check_in_ok = True
                            log_step("📅", "Check-in Alerta OK", Cores.VERDE)
                            if dias_atuais != -1: dias_atuais += 1
                        break
                log_telemetria("Ação Check-in", t_checkin)
        else:
             if page.ele('text:Logout'): check_in_ok = True 
             else: log_st = "ERRO CARREGAMENTO"

        if check_in_ok and dias_atuais != -1:
            atualizar_banco_dias(email, dias_atuais)

        if check_in_ok:
            premios, giros = processar_roleta(page)
            if giros > 0:
                 sucesso_conta = True
                 if premios:
                     append_log_premios_bruto(email, premios, giros)
                     msg = f"Prêmios: {', '.join(premios)}"
            else:
                 sucesso_conta = True

    except Exception as e: msg = str(e)

    registrar_log(email, log_st, msg)
    if sucesso_conta: adicionar_ao_historico(email)
    
    tempo_total = time.time() - t_conta_inicio
    print(f"   🏁 {Cores.NEGRITO}TOTAL: {Cores.CIANO}{tempo_total:.2f}s{Cores.RESET}")
    return sucesso_conta 

def main():
    if not config.CONF: config.carregar_user_config()
    try: 
        from fabricador.main import verificar_licenca_online as check_lic
        if not check_lic("checkin"): return
    except: pass 

    os.system('cls' if os.name == 'nt' else 'clear')
    exibir_banner_farm()
    
    contas = carregar_json_seguro(config.ARQUIVO_PRINCIPAL)
    if not contas: return

    print(f"\n{Cores.CINZA}>>> Inicializando Motor...{Cores.RESET}")
    co = ChromiumOptions()
    co.set_argument('--start-maximized') 
    co.set_argument('--window-size=1920,1080')
    
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-software-rasterizer')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-accelerated-2d-canvas')
    co.set_argument('--disable-gpu-sandbox')
    
    co.set_argument('--disable-blink-features=AutomationControlled')
    if config.CONF.get("headless", False): co.headless(True)
    
    page = ChromiumPage(addr_or_opts=co)
    iniciar_medidor(page)
    iniciar_sessao_logs()

    url = descobrir_url_evento(page)
    ja_foi = carregar_historico_hoje()
    
    banco_dias = carregar_banco_dias()
    
    def calcular_prioridade(conta):
        email = conta['email']
        dias_salvos = banco_dias.get(email, -1)
        if dias_salvos == -1: return 0
        if (dias_salvos + 1) % 5 == 0: return 2
        return 1
    
    lista_pendentes = [c for c in contas if c['email'] not in ja_foi]
    lista_pendentes.sort(key=calcular_prioridade, reverse=True)
    
    print(f"{Cores.CIANO}📊 Fila Otimizada: {len(lista_pendentes)} contas pendentes{Cores.RESET}")
    time.sleep(1)
    
    count_sucesso = 0
    for i, acc in enumerate(lista_pendentes):
        if processar(page, acc, url, i+1, len(lista_pendentes)): count_sucesso += 1
        if i < len(lista_pendentes) - 1:
            t = random.randint(1, 2)
            print(f"   {Cores.CINZA}⏳ Próxima em {t}s...{Cores.RESET}")
            time.sleep(t)
        
    msg = f"FARM FINALIZADO - {count_sucesso} SUCESSOS"
    print(f"\n{Cores.VERDE}╔{'═'*(len(msg)+4)}╗\n║  {msg}  ║\n╚{'═'*(len(msg)+4)}╝{Cores.RESET}")
    medir_consumo(page, "Fluxo Finalizado")
    page.quit()
    input("\nEnter para sair...")

def executar(): main()
if __name__ == "__main__": executar()
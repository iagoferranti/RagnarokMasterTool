import os
import time
import random
import imaplib
import email
import re
import sys
import json
from datetime import datetime
from email.header import decode_header
from urllib.parse import urlparse
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys

try: import pyotp
except ImportError: pass

# === INTEGRAÇÃO COM MÓDULOS ===
from fabricador import config
from fabricador.modules.network import TunelAuth, obter_proxy_novada
from fabricador.modules.files import carregar_json_seguro, salvar_json_seguro, salvar_conta_nova
from fabricador.modules.browser import garantir_logout
from fabricador.modules.cloudflare_solver import vencer_cloudflare_obrigatorio, fechar_cookies 
from fabricador.modules.logger import Cores, log_erro, log_sucesso, log_sistema

# === CONFIGURAÇÃO ===
# Agora usa o JSON padrão
ARQUIVO_UTI_JSON = os.path.join(config.BASE_PATH, "uti_contas.json")
SENHA_JOGO = "Ragnarok@2025"

# === GERENCIAMENTO DO JSON DA UTI ===
def remover_da_uti(email_alvo):
    """Remove a conta do JSON da UTI após sucesso."""
    if not os.path.exists(ARQUIVO_UTI_JSON): return

    try:
        dados = carregar_json_seguro(ARQUIVO_UTI_JSON)
        # Filtra mantendo apenas quem NÃO é o alvo
        novos_dados = [c for c in dados if c.get("email") != email_alvo]
        
        salvar_json_seguro(ARQUIVO_UTI_JSON, novos_dados)
        log_sucesso(f"Conta {email_alvo} removida da UTI!")
    except Exception as e:
        log_erro(f"Falha ao remover do JSON: {e}")

# === IMAP ESPECÍFICO DA UTI ===
def limpar_caixa_email(email_addr, senha_addr):
    print(f"   🧹 Faxinando e-mail {email_addr}...")
    imap_server = "outlook.office365.com"
    pastas = ["INBOX", "Junk"]
    
    if any(d in email_addr for d in ["rambler", "lenta.ru", "ro.ru", "myrambler"]):
        imap_server = "imap.rambler.ru"; pastas = ["INBOX", "Spam"]
    elif "yandex" in email_addr:
        imap_server = "imap.yandex.com"; pastas = ["INBOX", "Spam", "Junk"]

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_addr, senha_addr)
        for pasta in pastas:
            try:
                mail.select(pasta)
                mail.search(None, 'ALL')
                mail.store("1:*", '+FLAGS', '\\Deleted') 
                mail.expunge() 
            except: pass
        mail.logout()
        print(f"   {Cores.VERDE}✨ E-mail limpo!{Cores.RESET}")
    except Exception as e:
        print(f"   {Cores.AMARELO}⚠️ Falha leve na limpeza: {e}{Cores.RESET}")

def buscar_codigo_imap(email_addr, senha_addr):
    imap_server = "outlook.office365.com"
    pastas = ["INBOX", "Junk"]
    
    if any(d in email_addr for d in ["rambler", "lenta.ru", "ro.ru"]):
        imap_server = "imap.rambler.ru"; pastas = ["INBOX", "Spam"]
    elif "yandex" in email_addr:
        imap_server = "imap.yandex.com"; pastas = ["INBOX", "Spam"]

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_addr, senha_addr)
        
        for pasta in pastas:
            try:
                mail.select(pasta)
                status, messages = mail.search(None, '(UNSEEN)')
                
                if status != "OK" or not messages[0]:
                    status, messages = mail.search(None, 'ALL')
                
                if status != "OK" or not messages[0]: continue

                for num in reversed(messages[0].split()):
                    _, data = mail.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    
                    subject = str(decode_header(msg["Subject"] or "")[0][0])
                    if not any(x in subject.lower() for x in ["otp", "autenticação", "código"]): 
                        continue
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/html":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    
                    match_cor = re.search(r'color:#da0c0c[^>]*>\s*([A-Za-z0-9]{6})\s*<', body)
                    if match_cor:
                        mail.logout(); return match_cor.group(1)
                    
                    clean_text = re.sub(r'<[^>]+>', ' ', body)
                    candidates = re.findall(r'\b[A-Za-z0-9]{6}\b', clean_text)
                    blacklist = ["device", "access", "member", "system", "please", "gnjoy", "height", "width"]
                    
                    for cand in candidates:
                        if cand.lower() not in blacklist:
                            mail.logout(); return cand
            except: continue
        mail.logout()
    except: pass
    return None

# ==========================================
# LÓGICA DE RECUPERAÇÃO
# ==========================================
def processar_conta(email_user, senha_user, usar_proxy=False) -> bool:
    print(f"\n{Cores.CIANO}🔧 Processando conta: {Cores.NEGRITO}{email_user}{Cores.RESET}")
    
    limpar_caixa_email(email_user, senha_user)

    tunel = None
    page = None

    try:
        co = ChromiumOptions()
        co.set_argument("--ignore-certificate-errors")
        co.set_argument("--start-maximized")
        co.set_user_data_path(os.path.join(config.BASE_PATH, "chrome_profile_UTI"))

        if usar_proxy:
            print(f"   {Cores.AMARELO}🔄 Subindo Proxy...{Cores.RESET}")
            try:
                dados_proxy = obter_proxy_novada()
                proxy_url = dados_proxy['http']
                p = urlparse(proxy_url)
                local_port = random.randint(35000, 45000)
                
                tunel = TunelAuth(local_port, p.hostname, p.port, p.username, p.password)
                tunel.start()
                
                co.set_argument(f"--proxy-server=127.0.0.1:{local_port}")
                print(f"   🛡️ Proxy OK ({local_port})")
            except:
                log_erro("Erro ao iniciar Proxy. Pulando conta.")
                return False
        else:
            print(f"   {Cores.CINZA}🚀 Modo Direto (Sem Proxy){Cores.RESET}")
        
        if config.CONF.get("headless", False): co.headless(True)
        page = ChromiumPage(addr_or_opts=co)

        garantir_logout(page)

        print("   🔑 Acessando Login...")
        page.get("https://login.gnjoylatam.com/pt")
        
        # USA MÓDULO CLOUDFLARE
        vencer_cloudflare_obrigatorio(page)

        if page.ele('#email'):
            page.ele('#email').input(email_user)
            page.ele('#password').input(SENHA_JOGO)
            time.sleep(1)

            try:
                if page.wait.ele_displayed('text=CONTINUAR', timeout=5):
                    page.ele('text=CONTINUAR').click()
            except: pass
            
            try:
                if page.ele('text=Entrar'): page.ele('text=Entrar').click()
            except: 
                # Enter caso o clique falhe
                page.actions.key_down(Keys.ENTER).key_up(Keys.ENTER)

            time.sleep(6)

        if page.ele('#email') and page.ele('#password'):
            log_erro("Falha Login (continuou na tela)")
            return False

        print(f"   {Cores.VERDE}✅ Login OK! Indo para OTP...{Cores.RESET}")
        page.get("https://member.gnjoylatam.com/pt/mypage/gotp")

        if not page.wait.url_change('gotp', timeout=10):
            page.get("https://member.gnjoylatam.com/pt/mypage/gotp")
            time.sleep(3)

        if page.ele('text=Alterar a OTP'):
            print(f"   {Cores.AMARELO}⚠️ Já tem OTP! (Nada a fazer aqui){Cores.RESET}")
            # Se já tem, salvamos como sucesso para sair da UTI
            # CORREÇÃO: Passa status explicitamente e seed vazia ou None
            salvar_conta_nova(email_user, SENHA_JOGO, "", status="JA_POSSUIA_OTP")
            return True 

        btn = page.ele('text:Solicitação de serviço') or page.ele('css:button[class*="page_otp_join_btn"]')
        if not btn:
            log_erro("Botão OTP não achado")
            return False

        btn.click()
        print("   📨 Solicitando código...")

        for i in range(15):
            print(f"      ⏳ Aguardando e-mail... ({i+1}/15)", end="\r", flush=True)
            cod = buscar_codigo_imap(email_user, senha_user)
            if cod:
                print(f"\n   {Cores.VERDE}🔥 CÓDIGO: {cod}{Cores.RESET}")
                page.ele('#authnumber').input(cod)
                page.ele('text=Verificação concluída').click()
                time.sleep(2)

                ele_seed = page.ele('.page_otp_key__nk3eO')
                if not ele_seed:
                    log_erro("Erro ao pegar Seed")
                    return False

                seed = (ele_seed.text or "").strip()
                print(f"   💎 SEED: {seed}")

                try:
                    totp = pyotp.TOTP(seed.replace(" ", ""))
                    otp_code = totp.now()
                except Exception as e:
                    log_erro(f"Erro gerando TOTP: {e}")
                    return False

                # === INSERÇÃO BLINDADA (IGUAL AO ACTIONS.PY) ===
                try:
                    # Busca DIRETA pelo input correto name="otpNumber"
                    ele_input_otp = page.ele('@name=otpNumber') or \
                                    page.ele('css:input[name="otpNumber"]') or \
                                    page.ele('css:input[placeholder*="código de verificação OTP"]')

                    if ele_input_otp:
                        ele_input_otp.clear()
                        ele_input_otp.input(otp_code)
                    else:
                        log_erro("Campo de input OTP não encontrado (name=otpNumber).")
                        return False
                except: return False

                try:
                    if page.ele('text=Confirme'): page.ele('text=Confirme').click()
                except: pass

                time.sleep(2.0)
                texto_final = (page.ele('tag:body').text or "").lower()

                if "atividade anormal" in texto_final:
                    log_erro("Bloqueio temporário. Mantendo na UTI.")
                    # Não remove do JSON, apenas loga
                    return False

                if page.ele('text=OK') or "o serviço otp está sendo usado" in texto_final:
                    try: page.ele('text=OK').click()
                    except: pass
                    
                    print(f"   {Cores.VERDE}✅ SUCESSO TOTAL!{Cores.RESET}")
                    # Salva no arquivo final
                    # CORREÇÃO: Status explícito
                    salvar_conta_nova(email_user, SENHA_JOGO, seed, status="PRONTA_PARA_FARMAR")
                    return True

        log_erro("Timeout esperando e-mail OTP")
        return False

    except Exception as e:
        log_erro(f"Erro Processo: {e}")
        return False

    finally:
        try: page.quit()
        except: pass
        if tunel: tunel.stop()

def executar():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{Cores.VERMELHO}🚑 UTI DE CONTAS RAGNAROK (JSON EDITION) 🚑{Cores.RESET}")
    print("1. Modo Manual (Uma conta)")
    print("2. Modo Lote (Ler 'uti_contas.json')")
    
    op = input("\nEscolha: ").strip()
    p_op = input("Usar Proxy Novada? (S/N): ").strip().lower()
    usar_proxy = True if p_op == 's' else False

    if op == "1":
        entrada = input("\nDigite a conta (email:senha_email): ").strip()
        if ":" in entrada:
            e, s = entrada.split(":", 1)
            processar_conta(e.strip(), s.strip(), usar_proxy)
    
    elif op == "2":
        if not os.path.exists(ARQUIVO_UTI_JSON):
            print(f"❌ Arquivo {ARQUIVO_UTI_JSON} não encontrado!")
            input("Enter para voltar...")
            return
        
        # Carrega do JSON
        dados = carregar_json_seguro(ARQUIVO_UTI_JSON)
        
        # Filtra só quem tem os campos necessários
        contas_validas = [c for c in dados if c.get("email") and c.get("password")]
        
        print(f"\n📂 {len(contas_validas)} contas carregadas para reparo.")
        
        for idx, conta in enumerate(contas_validas):
            email = conta.get("email")
            senha_email = conta.get("password") # Note que aqui é senha do EMAIL
            motivo = conta.get("motivo", "Desconhecido")
            
            print(f"\n>>> Conta {idx+1}/{len(contas_validas)} | Erro Original: {motivo}")

            ok = processar_conta(email, senha_email, usar_proxy)

            if ok:
                remover_da_uti(email)
            else:
                print("   🧾 Mantendo conta na UTI (falhou).")
            
            time.sleep(2)
            
    print("\n🏁 Processo Finalizado.")
    input("Enter para sair...")

if __name__ == "__main__":
    executar()
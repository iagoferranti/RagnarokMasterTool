# fabricador/core/actions.py

import time
import random
import re
import pyotp
from datetime import datetime
from DrissionPage.common import Keys

from ..modules.outlook_imap import buscar_codigo_outlook_imap

from ..modules.logger import (
    log_info,
    log_sucesso,
    log_erro,
    log_sistema,
    log_aviso,
    Cores,
)
from ..modules.files import salvar_uti, salvar_conta_nova
from ..modules.cloudflare_solver import vencer_cloudflare_obrigatorio
from ..modules.utils import gerar_dados_pessoais, extrair_codigo_seguro
from ..modules.browser import (
    digitar_como_humano,
    clicar_com_seguranca,
    garantir_carregamento,
    mover_mouse_humano,
    marcar_etapa,
)


URL_CADASTRO = "https://member.gnjoylatam.com/pt/join"
URL_LOGIN = "https://login.gnjoylatam.com/pt"
URL_OTP = "https://member.gnjoylatam.com/pt/mypage/gotp"

FATOR_VELOCIDADE: float = 1.0


def definir_velocidade(rapido: bool = False) -> None:
    """Define o fator de velocidade global (0.5 = rápido, 1.0 = normal)."""
    global FATOR_VELOCIDADE
    if rapido:
        FATOR_VELOCIDADE = 0.5
    else:
        FATOR_VELOCIDADE = 1.0


def sleep_dinamico(segundos: float) -> None:
    """Sleep ajustado pelo fator de velocidade."""
    time.sleep(segundos * FATOR_VELOCIDADE)


def _gerar_nova_variacao_pontos(email_atual: str) -> str:
    """
    Gera nova variação de e-mail colocando pontos aleatórios na parte antes do @.
    Se não tiver @ ou qualquer erro, devolve o original.
    """
    try:
        if "@" not in email_atual:
            return email_atual

        user, domain = email_atual.split("@")
        user_clean = user.replace(".", "")

        if len(user_clean) < 2:
            return email_atual

        novo_user = list(user_clean)

        # quantidade de pontos entre 1 e len-1
        num_pontos = random.randint(1, len(user_clean) - 1)

        # posições entre 1 e len-1 (não no índice 0)
        posicoes = random.sample(range(1, len(user_clean)), num_pontos)
        posicoes.sort(reverse=True)

        for pos in posicoes:
            novo_user.insert(pos, ".")

        return "".join(novo_user) + "@" + domain
    except Exception:
        return email_atual


def verificar_envio_sucesso(page) -> bool:
    """
    Confere se o campo de código ou o timer de autenticação aparecem,
    indicando que o e-mail foi enviado.
    """
    try:
        ele = page.ele("#authnumber", timeout=0.5)
        if ele and ele.states.is_displayed:
            return True

        ele_timer = page.ele(".mailauth_timer__3lW1_", timeout=0.5)
        if ele_timer and ele_timer.states.is_displayed:
            return True

        return False
    except Exception:
        return False


def preencher_formulario_cadastro(page, sessao, senha_jogo):
    """
    Preenche o formulário inicial de cadastro com o e-mail da sessão
    e dispara o envio do código de verificação.

    Retorna tupla (sucesso: bool, motivo: str)
    Motivos possíveis principais:
        - 'OK'
        - 'CLOUDFLARE_FAIL'
        - 'EMAIL_BANNED'
        - 'EMAIL_EM_USO'
        - 'FAIL_CLICK_SEND'
        - 'SCRIPT_ERROR'
    """
    email = sessao.email
    log_info(f"Tentando cadastro com: {email}")

    try:
        # Se NÃO contém URL_CADASTRO na URL atual, então navega
        if URL_CADASTRO not in page.url:
            page.get(URL_CADASTRO)
            page.wait.doc_loaded()
            marcar_etapa(page, "Abertura Cadastro")

        # Cloudflare obrigatório
        if not vencer_cloudflare_obrigatorio(page, FATOR_VELOCIDADE):
            return False, "CLOUDFLARE_FAIL"

        log_info("Cloudflare OK. Preenchendo e-mail...")

        time.sleep(1)

        # Campo de email (id #email)
        if page.ele("#email"):
            ele = page.ele("#email")
            ele.click()
            ele.clear()
            digitar_como_humano(page, ele, email)

        # Botão de enviar verificação
        btn_verificar = page.ele(
            "xpath://button[contains(@class, 'mailauth_inputBtn')] | "
            "//button[contains(text(), 'Enviar verificação')]",
            timeout=2,
        )

        if btn_verificar:
            btn_verificar.click(by_js=True)
            log_sistema("⏳ Botão 'Enviar' clicado, aguardando resposta...")

            time.sleep(2.5)

            # mensagem de erro abaixo do campo de email
            erro_msg = page.ele(".mailauth_errorMessage__Umj_A", timeout=1)

            if erro_msg and erro_msg.states.is_displayed:
                txt_erro = erro_msg.text.lower()

                if "não pode ser utilizado" in txt_erro:
                    return False, "EMAIL_BANNED"

                if "em uso" in txt_erro:
                    return False, "EMAIL_EM_USO"

            # fallbacks por texto na página
            fallback_ban = page.ele("text:não pode ser utilizado", timeout=0.5)
            if fallback_ban and fallback_ban.states.is_displayed:
                return False, "EMAIL_BANNED"

            fallback_uso = page.ele("text:em uso", timeout=0.5)
            if fallback_uso and fallback_uso.states.is_displayed:
                return False, "EMAIL_EM_USO"

            # Verifica se surgiu timer de contagem
            ele_timer = page.ele(".mailauth_timer__3lW1_", timeout=1)
            if ele_timer and ele_timer.states.is_displayed:
                log_sucesso("✅ Timer de contagem regressiva ATIVO!")
                return True, "OK"

            # Ou o campo de código em si
            input_cod = page.ele("#authnumber", timeout=1)
            if input_cod and input_cod.states.is_displayed:
                log_sucesso("✅ Campo de código VISÍVEL!")
                return True, "OK"

            log_erro(
                "Nem erro, nem sucesso detectados. Possível timeout do site."
            )
            return False, "FAIL_CLICK_SEND"

        # Não achou botão
        log_erro("Botão 'Enviar verificação' não encontrado.")
        return False, "FAIL_CLICK_SEND"

    except Exception as e:
        log_erro(f"Erro no form: {e}")
        return False, "SCRIPT_ERROR"


def inserir_codigo_e_finalizar(page, codigo, senha, nome, sobrenome):
    """
    Insere o código de verificação, preenche o restante dos dados
    (nome, sobrenome, nascimento, telefone opcional, termos) e tenta
    finalizar o cadastro.

    Retorna:
        True  -> sucesso de cadastro e saída da tela
        False -> falha em qualquer etapa
    """
    try:
        # Campo de código
        input_cod = page.ele("#authnumber")
        if input_cod and input_cod.states.is_displayed:
            input_cod.clear()
            digitar_como_humano(page, input_cod, codigo)
            sleep_dinamico(1)

        # Botão "Verificação concluída"
        btn_validar = page.ele("text:Verificação concluída")
        if btn_validar:
            clicar_com_seguranca(page, btn_validar, "Verificação concluída")

        # Espera pelo campo de senha ficar editável
        inp_senha1 = None
        start_wait = time.time()
        while time.time() - start_wait < 15:
            inp_senha1 = page.ele("#password")
            if inp_senha1 and not inp_senha1.attr("readonly"):
                break
            time.sleep(0.5)

        if inp_senha1:
            # senha
            inp_senha1.clear()
            digitar_como_humano(page, inp_senha1, senha)
            time.sleep(random.uniform(0.3, 0.7))

            # confirmação de senha
            inp_senha2 = page.ele("#password2") or page.ele(
                'css:input[placeholder*="Confirme"]'
            )
            if inp_senha2:
                inp_senha2.clear()
                digitar_como_humano(page, inp_senha2, senha)
                time.sleep(random.uniform(0.3, 0.7))
    except Exception as e:
        log_erro(f"Erro senhas: {e}")
        return False

    try:
        # País
        btn_pais = page.ele(".page_selectBtn__XfETd")
        if btn_pais:
            btn_pais.click()
            page.ele("text=Brasil").click()

        # Dados pessoais aleatórios (sobrescreve se nome/sobrenome vieram vazios)
        r_nome, r_sobrenome = gerar_dados_pessoais()
        # ddds válidos
        ddds_validos = [
            "11",
            "15",
            "19",
            "21",
            "24",
            "31",
            "41",
            "51",
            "61",
            "62",
            "71",
            "81",
            "85",
        ]
        ddd_aleatorio = random.choice(ddds_validos)
        telefone_falso = f"{ddd_aleatorio}9{random.randint(10000000, 99999999)}"

        # Nome
        ele_nome = page.ele("#firstname")
        ele_nome.clear()
        digitar_como_humano(page, ele_nome, r_nome)

        # Sobrenome
        ele_sobrenome = page.ele("#lastname")
        ele_sobrenome.clear()
        digitar_como_humano(page, ele_sobrenome, r_sobrenome)

        # Nascimento
        ele_nasc = page.ele("#birthday")
        ele_nasc.clear()
        digitar_como_humano(page, ele_nasc, "01/01/1995")

        # Telefone opcional
        ele_mobile = page.ele("#mobile")
        if ele_mobile:
            page.run_js(
                "document.getElementById('mobile').removeAttribute('readonly')"
            )
            ele_mobile.clear()
            log_sistema(f"📱 Inserindo telefone opcional: {telefone_falso}")
            digitar_como_humano(page, ele_mobile, telefone_falso)

        # Pequena pausa, marca termos e finaliza
        time.sleep(random.uniform(0.5, 1.0))
        page.run_js("document.getElementById('terms1').click()")
        page.run_js("document.getElementById('terms2').click()")

        # Botão final
        btn_final = page.ele(".page_submitBtn__hk_C0") or page.ele(
            "button[type='submit']"
        )
        if not btn_final:
            return False

        clicar_com_seguranca(page, btn_final, "Botão FINALIZAR")
        sleep_dinamico(3)

        # Erros críticos
        if page.ele("text:atividade anormal"):
            return False
        if page.ele("text:não coincidem"):
            return False

        # Espera sair da página de registro ou aparecer mensagem de sucesso
        for _ in range(15):
            if (
                "register" in page.url
                or page.ele("text:Cadastro concluído")
            ):
                return True
            sleep_dinamico(1)

        return False

    except Exception as e:
        log_erro(f"Erro finalizar: {e}")
        return False


def login_e_capturar_otp(page, email, senha):
    """
    Faz login no site e tenta chegar à página de OTP.

    Retorno:
        (True, 'WAIT_EMAIL') -> precisa solicitar ativação OTP (botão aparecendo)
        (True, 'ACTIVE')     -> OTP já está ativo
        (None, 'NO_BTN_OTP') -> não achou botão nem mensagem
        (None, 'CF_FAIL_LOGIN')
        (None, 'ERR_LOGIN')
    """
    try:
        # Página de login (rota antiga usada no fluxo)
        page.get("https://www.gnjoylatam.com/Account/Login")

        # Se já logado, tenta sair
        if page.ele("text:Sair", timeout=1) or page.ele(
            "text:Logout", timeout=1
        ):
            page.get("https://www.gnjoylatam.com/")
            btn_logout = page.ele(
                "css:.header_logoutBtn__6Pv_m", timeout=2
            )
            if btn_logout:
                print(
                    "🧹 [Resgate] Sessão detectada no Ragnarok. Fazendo logout..."
                )
                btn_logout.click()
                time.sleep(2)

        log_sistema("⏳ Acessando página de Login...")
        page.get(URL_LOGIN)

        if not vencer_cloudflare_obrigatorio(page, FATOR_VELOCIDADE):
            return None, "CF_FAIL_LOGIN"

        # email
        if page.ele("#email"):
            ele_email = page.ele("#email")
            ele_email.clear()
            digitar_como_humano(page, ele_email, email)

            # senha
            ele_senha = page.ele("#password")
            ele_senha.clear()
            digitar_como_humano(page, ele_senha, senha)

            # botão submit ou Enter no password
            btn_submit = page.ele("button[type='submit']")
            if btn_submit:
                btn_submit.click()
            else:
                page.ele("#password").input("\n")

            # espera sair da rota /login
            for _ in range(15):
                if "login" not in page.url:
                    break
                time.sleep(0.5)

        log_sistema("⏳ Login OK! Acessando página de OTP...")
        page.get(URL_OTP)
        page.wait.doc_loaded()

        # Botão para solicitar OTP
        btn_solicitar = (
            page.ele("text:Solicitação de serviço OTP")
            or page.ele(".page_otp_join_btn__KKBJq")
        )
        if btn_solicitar:
            clicar_com_seguranca(page, btn_solicitar, "Solicitação OTP")
            return True, "WAIT_EMAIL"

        # Ou já está ativo
        if page.ele("text:OTP ativado"):
            return True, "ACTIVE"

        return None, "NO_BTN_OTP"

    except Exception:
        return None, "ERR_LOGIN"


def criar_conta(page, blacklist, sessao, provedor_email, config):

    token_do_site = config.get("nppr_api_key")

    """ Fluxo completo de criação de conta usando Checker Web para evitar bloqueios """
    # 1. limpar cookies
    try:
        page.run_cdp("Network.clearBrowserCookies")
        log_sistema("Sweep 🧹 Cookies limpos via CDP.")
    except Exception as e:
        log_erro(f"Erro ao limpar cookies: {e}")

    MAX_TENTATIVAS_EMAIL = 3
    try:
        for tentativa_idx in range(MAX_TENTATIVAS_EMAIL):
            senha_jogo = "Ragnarok@01"
            log_info(f"Iniciando tentativa {tentativa_idx + 1} com: {sessao.email}")
            
            sucesso_form, motivo_form = preencher_formulario_cadastro(page, sessao, senha_jogo)
            if not sucesso_form:
                if motivo_form in ("EMAIL_BANNED", "EMAIL_EM_USO"):
                    novo_email = _gerar_nova_variacao_pontos(sessao.email)
                    if novo_email == sessao.email: return False, motivo_form
                    sessao.email = novo_email
                    page.refresh()
                    continue
                else: return False, motivo_form
            break
    except Exception as e:
        return False, "FAIL_FORM"

    # 3. BUSCA CÓDIGO VIA CHECKER (Substituindo IMAP que falhou)
    log_sistema("   📧 Buscando código de Cadastro via Checker Web...")
    from ..modules.outlook_checker import buscar_codigo_via_checker

    # Pega a chave que você salvou no JSON
    token_do_site = config.get("nppr_api_key")
    
    # IMPORTANTE: Passamos a string completa (sessao.full_string) que contém o Token OAuth2
    codigo = buscar_codigo_via_checker(page, sessao.full_string, tipo_codigo="cadastro",token_nppr=token_do_site)

    if not codigo: return False, "NO_CODE_CHECKER"
    log_sistema(f"   🔥 Código de Cadastro recebido: {codigo}")

    # 4. inserir código, finalizar formulário
    ok = inserir_codigo_e_finalizar(page, codigo, senha_jogo, "Player", sessao.email[:5])
    if not ok: return False, "FAIL_SUBMIT"

    log_sistema("⏳ Verificando sucesso...")
    sleep_dinamico(5)

    # 5. tentar login e ver status OTP
    ok, status = login_e_capturar_otp(page, sessao.email, senha_jogo)
    if not ok:
        salvar_uti(sessao.email, senha_jogo, status)
        return True, "UTI"

    # 6. BUSCA OTP VIA CHECKER
    log_sistema("   📧 Buscando código OTP via Checker Web...")
    otp = buscar_codigo_via_checker(page, sessao.full_string, tipo_codigo="otp")

    if not otp:
        salvar_conta_nova(sessao.email, senha_jogo, "", status="SEM_OTP")
        return True, "SALVO_SEM_OTP"

    log_sistema(f"   🔥 Código OTP recebido: {otp}")

    # 7 a 11. Digitação final e captura de SEED
    try:
        log_info("⌨️  Digitando OTP do Email (Humano)...")
        ele_otp = page.ele("#authnumber")
        ele_otp.clear()
        digitar_como_humano(page, ele_otp, otp)
        
        btn_otp_ok = page.ele("text:Verificação concluída")
        if btn_otp_ok: btn_otp_ok.click(by_js=True)
        sleep_dinamico(3)

        seed_final = ""
        for i in range(40):
            # [cite_start]Usando o seletor correto identificado no bytecode [cite: 405-408]
            ele_seed = page.ele(".page_otp_key__nk3eO")
            if ele_seed and ele_seed.text.strip():
                seed_final = ele_seed.text.strip()
                break
            time.sleep(0.5)

        if not seed_final:
            salvar_conta_nova(sessao.email, senha_jogo, "", status="SEM_OTP")
            return True, "SALVO_SEM_OTP"

        # 9. Janela de tempo segura para TOTP
        while datetime.now().second >= 55 or 25 <= datetime.now().second <= 30:
            time.sleep(1)

        seed_clean = re.sub(r"[^A-Z2-7]", "", seed_final.upper().replace(" ", ""))
        token_gerado = pyotp.TOTP(seed_clean).now()

        # 10. Digitar token com proteção "erro chinês" e clique JS
        ele_input_otp = page.ele("@name=otpNumber") or page.ele('css:input[name="otpNumber"]')
        if ele_input_otp:
            ele_input_otp.wait.displayed()
            ele_input_otp.clear()
            digitar_como_humano(page, ele_input_otp, token_gerado)
            
            time.sleep(1.5)
            btn_conf = page.ele("text:Confirme")
            if btn_conf: btn_conf.click(by_js=True) # Força o clique via DOM
            
            sleep_dinamico(2)
            btn_ok = page.ele("text:OK")
            if btn_ok: btn_ok.click(by_js=True)

        salvar_conta_nova(sessao.email, senha_jogo, seed_final, status="PRONTA_PARA_FARMAR")
        log_sucesso("🚀 CONTA FINALIZADA!")
        return True, "SUCCESS"

    except Exception as e:
        log_erro(f"Erro final: {e}")
        return False, "FAIL_FINAL"


def recuperar_otp_pendente(page, email, senha_jogo, senha_email, provedor_email, token_nppr=None):
    """
    Fluxo de resgate de OTP/SEED para contas já cadastradas com limpeza de sessão.
    """
    log_sistema(f"🔄 Iniciando resgate OTP para: {email}")

    # --- 🧹 LIMPEZA DE SESSÃO ANTERIOR ---
    try:
        # Acessa a página de login para verificar o estado
        page.get("https://www.gnjoylatam.com/pt")
        
        # Procura o botão de Logout que você identificou no log
        btn_logout = page.ele('.header_logoutBtn__6Pv_m', timeout=3)
        if btn_logout:
            log_sistema("🧹 [Resgate] Conta anterior detectada. Fazendo logout...")
            btn_logout.click()
            page.wait.load_start()
        
        # Garante que não sobrou nenhum rastro de login nos cookies do navegador
        page.run_cdp('Network.clearBrowserCookies')
        log_info("✨ Navegador limpo para novo login.")
    except Exception as e_clean:
        log_info(f"ℹ️ Aviso na limpeza de sessão: {e_clean}")
    # -------------------------------------

    class SessaoTemp:
        __firstlineno__ = 473
        __static_attributes__ = ("email", "senha")
        def __init__(self, e, s):
            self.email = e
            self.senha = s

    sessao = SessaoTemp(email, senha_email)

    try:
        # Agora o site estará na tela de login vazia, pronto para receber HershelJewesszesd
        ok, status = login_e_capturar_otp(page, email, senha_jogo)
        if not ok:
            log_erro(f"Falha ao logar na conta para resgate: {status}")
            return False, None

        log_sistema("⏳ Buscando código OTP no Outlook...")

        from fabricador.modules.outlook_checker import buscar_codigo_via_checker

        otp = buscar_codigo_via_checker(
            page, 
            senha_email,      # String full e-mail|senha|rec
            tipo_codigo='otp', 
            token_nppr=token_nppr
        )
        
        if not otp:
            log_erro("Falha ao capturar o OTP no webmail via NPPR.")
            return False, None

        # --- Inserção do OTP e captura da Seed (mesmo código que você já tem) ---
        log_info("⌨️ Digitando OTP resgatado...")
        ele_otp = page.ele("#authnumber")
        ele_otp.clear()
        digitar_como_humano(page, ele_otp, otp)
        sleep_dinamico(1)

        btn_otp_ok = page.ele("text:Verificação concluída")
        if btn_otp_ok:
            clicar_com_seguranca(page, btn_otp_ok, "Verificação OTP")

        sleep_dinamico(3)

        seed_final = ""
        for i in range(40):
            ele_seed = page.ele(".page_otp_key__nk3eO")
            if ele_seed and ele_seed.text.strip():
                seed_final = ele_seed.text.strip()
                break
            if i == 20 and page.ele("text:Verificação concluída"):
                page.ele("text:Verificação concluída").click()
            time.sleep(0.5)

        if not seed_final or len(seed_final) < 8:
            log_erro("⛔ Erro: Seed não carregou no resgate.")
            return False, None

        log_sistema(f"💎 Seed Recuperada com Sucesso: {seed_final}")

        # --- Validação Final do TOTP ---
        seed_clean = re.sub(r"[^A-Z2-7]", "", seed_final.upper().replace(" ", ""))
        import pyotp as _pyotp
        totp = _pyotp.TOTP(seed_clean)
        token_gerado = totp.now()

        ele_input_otp = page.ele("@name=otpNumber") or page.ele('css:input[name="otpNumber"]')
        if ele_input_otp:
            ele_input_otp.clear()
            digitar_como_humano(page, ele_input_otp, token_gerado)
            
            btn_confirme = page.ele("text:Confirme")
            if btn_confirme:
                clicar_com_seguranca(page, btn_confirme, "Confirmar Final")

        sleep_dinamico(3)
        html_final = page.ele("tag:body").text.lower()

        if ("incorreto" in html_final) or ("atividade anormal" in html_final):
            log_erro("Erro de validação final no resgate.")
            return False, None

        return True, seed_final

    except Exception as e:
        log_erro(f"Erro durante o resgate do OTP: {e}")
        return False, None
# fabricador/modules/cloudflare_solver.py

import time

from DrissionPage.common import Keys
from .logger import (
    log_sistema,
    log_sucesso,
    log_erro,
    log_aviso,
    Cores,
)


def fechar_cookies(page):
    """
    Fecha banners de cookies mais comuns usados pela GNJoy/Cloudflare.

    Tenta na ordem:
      - '.cookieprivacy_btn__Pqz8U'
      - 'text=concordo.'
      - '#onetrust-accept-btn-handler'
    """
    try:
        el = page.ele(".cookieprivacy_btn__Pqz8U", timeout=0.1)
        if el:
            page.ele(".cookieprivacy_btn__Pqz8U").click()
            return

        el = page.ele("text=concordo.", timeout=0.1)
        if el:
            page.ele("text=concordo.").click()
            return

        el = page.ele("#onetrust-accept-btn-handler", timeout=0.1)
        if el:
            page.ele("#onetrust-accept-btn-handler").click()
            return

        return
    except Exception:
        return


def checar_bloqueio_ip(page) -> bool:
    """
    Verifica se há sinais claros de bloqueio de IP:

      - Mensagem de "segurança para acesso é insuficiente" OU
        "tente novamente em ambiente diferente"
      - Título da página contendo "429" ou "access denied"

    Se detectar situação de IP bloqueado, levanta Exception("IP_BLOCKED").
    Retorna:
        True  se houver mensagem de bloqueio na tela (sem exception)
        False se não encontrar bloqueio evidente
    """
    try:
        # Mensagens na página
        msg = (
            page.ele(
                "text:segurança para acesso é insuficiente",
                timeout=0.1,
            )
            or page.ele(
                "text:tente novamente em ambiente diferente",
                timeout=0.1,
            )
        )

        if msg and msg.states.is_displayed:
            return True

        # Título com 429 ou access denied
        title_lower = (page.title or "").lower()

        if "429" in title_lower or "access denied" in title_lower:
            raise Exception("IP_BLOCKED")

        return False

    except Exception as e:
        # Propaga apenas se já for IP_BLOCKED
        if "IP_BLOCKED" in str(e):
            raise
        return False


def is_success(page) -> bool:
    """
    Verifica se o desafio Cloudflare / Turnstile foi concluído com sucesso.

    Checa:
      - '#success'
      - '.page_success__gilOx'
      - '#success-text'
      - Mensagens dentro de '.turnstile_turnstileMessage__grLkv p'
        ou '#verifying-text' ou 'text:acesso concluída' contendo
        'concluída', 'sucesso' ou 'success'.
    """
    try:
        # Elementos de sucesso direto
        if (
            page.ele("#success", timeout=0.1)
            and page.ele("#success").states.is_displayed
        ):
            return True

        if (
            page.ele(".page_success__gilOx", timeout=0.1)
            and page.ele(".page_success__gilOx").states.is_displayed
        ):
            return True

        if (
            page.ele("#success-text", timeout=0.1)
            and page.ele("#success-text").states.is_displayed
        ):
            return True

        # Mensagens textuais
        ele_msg = (
            page.ele(".turnstile_turnstileMessage__grLkv p", timeout=0.1)
            or page.ele("#verifying-text", timeout=0.1)
            or page.ele("text:acesso concluída", timeout=0.1)
        )

        if ele_msg and ele_msg.states.is_displayed:
            txt = (ele_msg.text or "").lower()
            if (
                "concluída" in txt
                or "sucesso" in txt
                or "success" in txt
            ):
                return True

        return False

    except Exception:
        return False


def resolver_cloudflare_tentativa_unica(page, fator_tempo: float = 1.0) -> bool:
    """
    Faz uma tentativa de resolver o desafio Cloudflare/Turnstile na página atual.

    Passos:
      1. Fecha cookies
      2. Aguarda alguns segundos
      3. Dentro de um limite (60 * fator_tempo, mínimo 30s), faz:
         - Checagem de sucesso (`is_success`)
         - Checagem de IP bloqueado (`checar_bloqueio_ip`)
         - Clique em checkbox, se existir
         - Foca no campo de e-mail ou no body
         - Faz um "tab cycling" (SHIFT+TAB) algumas vezes
         - Pressiona SPACE
         - Espera alguns segundos e reavalia
    """
    fechar_cookies(page)
    time.sleep(4 * fator_tempo)

    start_time = time.time()
    max_wait = 60 * fator_tempo
    if max_wait < 30:
        max_wait = 30

    while time.time() - start_time < max_wait:
        # Sucesso?
        if is_success(page):
            return True

        # Bloqueio IP?
        if checar_bloqueio_ip(page):
            log_aviso("   ❌ Falso positivo (Erro IP Visível).")
            return False

        # Tenta clicar em checkbox (diferentes seletores)
        try:
            el = page.ele(".cb-lb", timeout=0.2)
            if el:
                el.click()
            else:
                el = page.ele("input[type='checkbox']", timeout=0.2)
                if el:
                    el.click()
        except Exception:
            pass

        # Foca no campo de email, se existir, ou no body
        try:
            el = page.ele("#email", timeout=0.1)
            if el:
                el.click()
            else:
                page.ele("tag:body").click()
        except Exception:
            pass

        time.sleep(0.1)

        # Pressiona SHIFT+TAB algumas vezes (varia o foco)
        for _ in range(4):
            page.actions.key_down(Keys.SHIFT).key_down(Keys.TAB).key_up(
                Keys.TAB
            ).key_up(Keys.SHIFT)
            time.sleep(0.05)

        # Por fim, espaçadora
        page.actions.key_down(Keys.SPACE).key_up(Keys.SPACE)

        time.sleep(5 * fator_tempo)

    return False


def resolver_cloudflare(page, fator_tempo: float = 1.0) -> bool:
    """
    Tenta resolver o Cloudflare de forma persistente, com até 3 tentativas
    de recarregar a página se necessário.

    Usa `resolver_cloudflare_tentativa_unica` internamente.
    """
    log_sistema(
        f"{Cores.AMARELO}"
        "🛡️  Analisando Cloudflare (Modo Persistente)..."
        f"{Cores.RESET}"
    )

    for tentativa in range(1, 4):
        if tentativa > 1:
            log_aviso(
                f"   🔄 Cloudflare falhou. Recarregando página (Tentativa "
                f"{tentativa}/3)..."
            )
            page.refresh()
            time.sleep(5)

        if resolver_cloudflare_tentativa_unica(page, fator_tempo):
            log_sucesso("Cloudflare Validado!")
            return True

    log_erro("Timeout Cloudflare após 3 tentativas.")
    return False


# Alias semântica usada em vários módulos
vencer_cloudflare_obrigatorio = resolver_cloudflare
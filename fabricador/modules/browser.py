# fabricador/modules/browser.py

import time
import random
import math

from DrissionPage.common import Keys

from .. import config
from .logger import log_erro, log_info, log_sistema, Cores
from .utils import delay_humano
from .cloudflare_solver import checar_bloqueio_ip


# Controle de tráfego / consumo de rede monitorado pelo CDP
ACUMULADO_MB = 0.0
ULTIMO_CHECKPOINT = 0.0
ARQUIVOS_PESADOS: list[str] = []


def iniciar_medidor(page):
    """Inicia o listener de rede da página, se disponível."""
    try:
        page.listen.start()
    except Exception:
        # Falhou em iniciar o listener, ignora
        pass


def medir_consumo(page, etapa: str = ""):
    """
    Percorre os pacotes recentes do listener da DrissionPage e acumula
    o consumo em MB em ACUMULADO_MB.

    Também registra em ARQUIVOS_PESADOS quando um único recurso > 0.5 MB.
    """
    global ACUMULADO_MB, ARQUIVOS_PESADOS

    try:
        for packet in page.listen.steps(timeout=0.1):
            try:
                tamanho = 0
                headers = packet.response.headers
                url = packet.request.url

                # Prioriza Content-Length do header
                if "Content-Length" in headers:
                    tamanho = int(headers["Content-Length"])
                elif "content-length" in headers:
                    tamanho = int(headers["content-length"])
                else:
                    # fallback: tamanho do body
                    if packet.response.body:
                        tamanho = len(packet.response.body)
                    else:
                        tamanho = 0

                mb_novo = tamanho / 1048576  # bytes -> MB

                if mb_novo > 0:
                    ACUMULADO_MB += mb_novo

                    # Arquivos grandes, logar
                    if mb_novo > 0.5:
                        tipo = headers.get("Content-Type", "desconhecido")
                        ARQUIVOS_PESADOS.append(
                            "["
                            f"{mb_novo:.2f} MB"
                            "] "
                            f"{tipo}"
                            " -> "
                            f"{url[:60]}..."
                        )
            except Exception:
                # Erro em um pacote específico não deve quebrar o loop
                continue

    except Exception:
        # Em caso de erro geral, apenas ignora e segue
        pass


def marcar_etapa(page, nome_etapa: str):
    """
    Marca um checkpoint de consumo de rede para a etapa atual.

    Calcula o delta de consumo desde o último checkpoint e, se for
    significativo, imprime no console.
    """
    global ACUMULADO_MB, ULTIMO_CHECKPOINT

    # Atualiza consumo antes do cálculo
    medir_consumo(page)

    delta = ACUMULADO_MB - ULTIMO_CHECKPOINT
    ULTIMO_CHECKPOINT = ACUMULADO_MB

    # só loga se consumiu mais de 0.01 MB
    if delta > 0.01:
        print(
            f"{Cores.AMARELO}"
            f"   📉 CONSUMO [{nome_etapa}]: "
            f"{delta:.2f} MB (Total: {ACUMULADO_MB:.2f} MB)"
            f"{Cores.RESET}"
        )


def relatorio_final_consumo():
    """
    Mostra um pequeno relatório dos arquivos mais pesados carregados.
    """
    global ARQUIVOS_PESADOS

    if not ARQUIVOS_PESADOS:
        return

    print(
        "\n"
        f"{Cores.VERMELHO}"
        "🚨 ARQUIVOS PESADOS DETECTADOS (>500KB):"
        f"{Cores.RESET}"
    )
    for arq in ARQUIVOS_PESADOS:
        print("   " + arq)

    print("------------------------------")
    ARQUIVOS_PESADOS = []


def mover_mouse_humano(page, elemento):
    """
    Move o mouse até o elemento com um pequeno offset e duração randomizada,
    simulando um movimento humano.
    """
    try:
        rect = elemento.rect

        target_x = (
            rect.location[0] + rect.size[0] / 2
        )
        target_y = (
            rect.location[1] + rect.size[1] / 2
        )

        offset_x = random.randint(-10, 10)
        offset_y = random.randint(-5, 5)

        page.actions.move_to(
            ele_or_loc=elemento,
            offset_x=offset_x,
            offset_y=offset_y,
            duration=random.uniform(0.3, 0.8),
        )
    except Exception:
        # Se falhar, não quebra o fluxo
        pass


def digitar_como_humano(page, seletor, texto) -> bool:
    """
    Digita texto em um campo de forma mais realista:
      - Move o mouse até o elemento
      - Pequenos delays antes/depois do clique
      - Digita caractere a caractere com delays aleatórios
    """
    try:
        if isinstance(seletor, str):
            ele = page.ele(seletor)
        else:
            ele = seletor

        if not ele:
            return False

        mover_mouse_humano(page, ele)
        time.sleep(random.uniform(0.1, 0.3))

        ele.click()
        time.sleep(random.uniform(0.2, 0.5))

        for char in texto:
            page.actions.type(char)
            time.sleep(random.uniform(0.08, 0.25))

        time.sleep(random.uniform(0.3, 0.6))
        return True

    except Exception as e:
        log_erro(f"Erro ao digitar humano: {e}")
        return False


def clicar_com_seguranca(page, seletor, nome_elemento: str = "Elemento") -> bool:
    """
    Tenta clicar em um elemento de forma mais robusta:
      1. Mede consumo antes do clique (etapa 'Pré-Clique')
      2. Tenta achar o elemento com wait.ele_displayed por até TIMEOUT_PADRAO
      3. Faz scroll até o elemento, move o mouse de forma humana e clica
      4. Se der exceção, tenta um fallback via JS (arguments[0].click())
      5. Até 3 tentativas, com pequenos waits entre elas

    Retorna True em caso de clique realizado, False caso contrário.
    """
    medir_consumo(page, "Pré-Clique")

    for tentativa in range(3):
        try:
            btn = page.wait.ele_displayed(
                seletor, timeout=config.TIMEOUT_PADRAO
            )

            if btn:
                page.scroll.to_see(btn)
                time.sleep(random.uniform(0.2, 0.5))
                mover_mouse_humano(page, btn)
                btn.click()
                return True

        except Exception:
            try:
                btn = page.ele(seletor)
                if btn:
                    page.run_js("arguments[0].click()", btn)
                    return True
            except Exception:
                pass

            time.sleep(1)

    log_erro(f"Falha ao clicar em {nome_elemento}.")
    return False


def garantir_carregamento(page, seletor_esperado, timeout: int = 30) -> bool:
    """
    Garante que um determinado seletor esteja visível dentro de um timeout.

    - Enquanto espera:
      * verifica elemento visível
      * chama checar_bloqueio_ip(page)
      * dorme 1s entre as tentativas
    - Se detectar uma Exception contendo 'IP_BLOCKED', relança para ser tratada
      por camadas superiores.

    Retorna:
        True  se o seletor apareceu
        False se o timeout foi atingido sem sucesso
    """
    inicio = time.time()

    try:
        while time.time() - inicio < timeout:
            if (
                page.ele(seletor_esperado)
                and page.ele(seletor_esperado).states.is_displayed
            ):
                medir_consumo(page, "Carregamento")
                return True

            # verifica se IP foi bloqueado
            try:
                checar_bloqueio_ip(page)
            except Exception as e:
                if "IP_BLOCKED" in str(e):
                    raise
                # se não for IP_BLOCKED, ignora

            time.sleep(1)

        return False

    except Exception as e:
        if "IP_BLOCKED" in str(e):
            # propaga explicitamente
            raise
        # outros erros são ignorados como timeout normal
        return False


def garantir_logout(page):
    """
    Faz logout completo e limpa armazenamento:
      - Limpa cookies via CDP
      - Limpa cache
      - Limpa localStorage / sessionStorage
      - Procura e clica no botão de logout (várias formas)
    """
    medir_consumo(page, "Pré-Logout")

    try:
        page.run_cdp("Network.clearBrowserCookies")
        page.run_cdp("Network.clearBrowserCache")
        page.run_js("localStorage.clear(); sessionStorage.clear();")
        page.delete_cookies()
    except Exception:
        # Mesmo se der erro, tentar o botão de logout
        pass

    while True:
        try:
            # várias formas de localizar botão de logout
            btn_logout = (
                page.ele(".header_logoutBtn__6Pv_m")
                or page.ele("text=Sair")
                or page.ele("text=Logout")
                or page.ele('css:a[href*="logout"]')
            )

            if btn_logout:
                try:
                    page.run_js("arguments[0].click()", btn_logout)
                except Exception:
                    # fallback para click normal
                    try:
                        btn_logout.click()
                    except Exception:
                        pass

                time.sleep(2)
                return

            return

        except Exception:
            # Em qualquer erro na localização do botão, tenta de novo o loop
            continue


def capturar_erro_email(page):
    """
    Varre mensagens de erro relacionadas a e-mail na tela de cadastro,
    tentando identificar um código de erro semântico.

    Retorna:
        ('EMAIL_INVALIDO', 'Email inválido.')
        ('DOMINIO_BLOQUEADO', 'Domínio bloqueado.')
        ('SEGURANCA_INSUFICIENTE', 'Erro segurança.')
        ('EMAIL_EM_USO', 'Email em uso.')
        ('EMAIL_FORMATO_RUIM', 'Formato inválido.')
        (None, '') se nada for detectado.
    """
    seletores = [
        ".mailauth_errorMessage__Umj_A",
        ".input_errorMsg__hM_98",
    ]

    deadline = time.time() + 4

    while time.time() < deadline:
        textos: list[str] = []

        # Erros específicos próximos aos campos
        for sel in seletores:
            try:
                el = page.ele(sel, timeout=0.2)
                if el and el.states.is_displayed:
                    textos.append((el.text or "").strip())
            except Exception:
                # Só ignora
                continue

        # Também coleta o texto do body inteiro
        try:
            textos.append(
                (page.ele("tag:body").text or "").strip()
            )
        except Exception:
            pass

        low = " | ".join(textos).lower()

        if "não pode ser utilizado" in low:
            return "EMAIL_INVALIDO", "Email inválido."

        if "cannot be used" in low:
            return "EMAIL_INVALIDO", "Email inválido."

        if "não é possível se cadastrar" in low:
            return "DOMINIO_BLOQUEADO", "Domínio bloqueado."

        if "segurança" in low and "insuficiente" in low:
            return "SEGURANCA_INSUFICIENTE", "Erro segurança."

        if "em uso" in low:
            return "EMAIL_EM_USO", "Email em uso."

        if "digite um e-mail válido" in low:
            return "EMAIL_FORMATO_RUIM", "Formato inválido."

        if "enter a valid email" in low:
            return "EMAIL_FORMATO_RUIM", "Formato inválido."

        time.sleep(0.2)

    return None, ""
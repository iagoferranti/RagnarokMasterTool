# fabricador/main.py

import time
import os
import random
import shutil
import requests
import sys
import traceback

import autologin.bot_login as autologin

from .provider_gmail_proprio import ProviderGmailProprio
from urllib.parse import urlparse
from DrissionPage import ChromiumPage, ChromiumOptions
from .provider_outlook import ProviderOutlook

# AQUI: relativo para dentro do pacote fabricador
from .modules.provider_dataimpulse import ProviderDataImpulse
from . import config
from .core.actions import criar_conta, definir_velocidade
from .modules.network import TunelAuth
from .modules.logger import (
    exibir_banner,
    log_info,
    log_sucesso,
    log_erro,
    log_sistema,
    log_aviso,
    Cores,
    barra_progresso,
)
from .provider_gmail import (
    gerar_email_variacao_dot,
    buscar_codigo_no_gmail,
)
from .modules import browser
from .modules.browser import iniciar_medidor

print("--------------------------------------------------")
print(f"📂 DEBUG: BASE_PATH identificado: {config.BASE_PATH}")
sys.path.append(config.BASE_PATH)

try:
    from provider_email import ProviderLista
except Exception:
    print("\n❌ ERRO CRÍTICO NO PROVIDER_EMAIL:")
    sys.exit()

try:
    from api_smail import ProviderSmailPro
except Exception:
    print("\n❌ ERRO CRÍTICO NO API_SMAIL:")
    sys.exit()

print("--------------------------------------------------")


def executar():
    """
    Função principal do fabricador de contas Ragnarok Online (GNJoy Latam).

    Fluxo resumido:
      1. Pergunta quantas contas criar.
      2. Configura lotes (anti-ban) e proxy.
      3. Configura provider de e-mail (SmailPro / Outlook).
      4. Faz varredura inicial de contas SEM_OTP (resgate OTP pendente).
      5. Loop principal: cria contas, gerencia erros e rotação de proxy.
      6. Ao final, chama o bot de criação de personagens.
    """
    # Limpa tela
    os.system("cls" if os.name == "nt" else "clear")
    exibir_banner()

    # Garante que CONF está carregado
    if not config.CONF:
        config.carregar_user_config()

    # ── Quantidade de contas ──────────────────────────────────────────
    while True:
        try:
            qtd_str = input(
                f"{Cores.CIANO}Quantas contas deseja criar?: {Cores.RESET}"
            ).strip()
            qtd_alvo = int(qtd_str)
            break
        except Exception:
            qtd_alvo = 1

    # ── Configuração de lotes ─────────────────────────────────────────
    tamanho_lote = qtd_alvo
    tempo_descanso = 0

    if qtd_alvo > 5:
        while True:
            try:
                print(
                    f"\n{Cores.AMARELO}"
                    "📦 CONFIGURAÇÃO DE LOTES (Proteção Anti-Ban)"
                    f"{Cores.RESET}"
                )
                lote_input = input(
                    "   >> Tamanho do Lote (0 = sem pausa) [10]: "
                ).strip()

                if lote_input and int(lote_input) > 0:
                    tamanho_lote = int(lote_input)
                    descanso_min = float(
                        input(
                            "   >> Minutos de descanso entre lotes [2.0]: "
                        ).strip()
                        or "2"
                    )
                    tempo_descanso = int(descanso_min * 60)
                break
            except Exception:
                break

    # ── Proxy ─────────────────────────────────────────────────────────
    usar_proxy = False
    prov_proxy = None

    print(
        f"\n{Cores.CIANO}Configuração de Rede:{Cores.RESET}"
    )

    resp_proxy = (
        input(
            "   >> Usar Proxy Premium (DataImpulse)? "
            "(S/N) [Padrão: S]: "
        )
        .strip()
        .upper()
    )

    if resp_proxy != "N":
        usar_proxy = True
        print(
            f"    └── 🛡️  Modo: "
            f"{Cores.VERDE}DATAIMPULSE RESIDENCIAL ATIVADO{Cores.RESET}"
        )

        di_login = config.CONF.get("dataimpulse_login", "")
        di_pass = config.CONF.get("dataimpulse_pass", "")

        if not (di_login and di_pass):
            print(
                f"\n{Cores.AMARELO}"
                "=== Configuração Inicial do DataImpulse ==="
                f"{Cores.RESET}"
            )
            print("Cole as credenciais do seu painel DataImpulse.")
            di_login = input("Login: ").strip()
            di_pass = input("Senha: ").strip()

            config.CONF["dataimpulse_login"] = di_login
            config.CONF["dataimpulse_pass"] = di_pass

            try:
                import json as _json
                with open(
                    os.path.join(config.BASE_PATH, "config.json"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    _json.dump(config.CONF, f, indent=4)
                print(
                    f"{Cores.VERDE}"
                    "Credenciais de Proxy salvas com sucesso!"
                    f"{Cores.RESET}"
                )
            except Exception as e:
                print(f"{Cores.VERMELHO}Erro ao salvar: {e}{Cores.RESET}")

        prov_proxy = ProviderDataImpulse(di_login, di_pass)
        definir_velocidade(rapido=False)

    else:
        print(
            f"    └── 🚀 Modo: "
            f"{Cores.AMARELO}Rodando com IP Local/VPN do usuário."
            f"{Cores.RESET}"
        )
        definir_velocidade(rapido=True)

    # ── Provider de e-mail (SmailPro / Outlook) ───────────────────────
    prov = None

    api_key = config.CONF.get("smailpro_key", "")

    if not api_key:
        print(
            f"\n{Cores.AMARELO}"
            "=== Configuração Inicial do SmailPro ==="
            f"{Cores.RESET}"
        )
        api_key = input("Cole sua API Key do SmailPro: ").strip()

        if api_key:
            config.CONF["smailpro_key"] = api_key

            try:
                import json as _json
                with open(
                    os.path.join(config.BASE_PATH, "config.json"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    _json.dump(config.CONF, f, indent=4)
                print(
                    f"{Cores.VERDE}"
                    "API Key do SmailPro salva com sucesso!"
                    f"{Cores.RESET}"
                )
            except Exception as e:
                print(
                    f"{Cores.VERMELHO}Erro ao salvar config: {e}"
                    f"{Cores.RESET}"
                )
        else:
            log_erro("Nenhuma chave inserida. Encerrando...")
            time.sleep(2)
            return

    # Provider padrão: Outlook
    prov = ProviderOutlook()
    log_sistema("📧 Provedor: OUTLOOK/HOTMAIL ATIVADO")

    # ── Blacklist global de domínios ──────────────────────────────────
    blacklist_global: set[str] = set()

    if os.path.exists(config.ARQUIVO_BLACKLIST):
        with open(config.ARQUIVO_BLACKLIST, "r") as f:
            for l in f:
                blacklist_global.add(l.strip())

    # ── Contadores ────────────────────────────────────────────────────
    sucessos = 0
    bloqueios_consecutivos = 0

    # ── Varredura inicial: resgatar contas SEM_OTP ────────────────────
    import json as _json

    arquivo_json = os.path.join(config.BASE_PATH, "accounts.json")

    if os.path.exists(arquivo_json):
        try:
            with open(arquivo_json, "r", encoding="utf-8") as f:
                contas_json: list[dict] = _json.load(f)

            contas_pendentes = [
                c for c in contas_json
                if c.get("status") == "SEM_OTP"
            ]

            if contas_pendentes:
                from fabricador.core.actions import recuperar_otp_pendente

                # Abre um browser temporário apenas para o resgate
                co_resgate = ChromiumOptions()
                co_resgate.set_argument("--no-sandbox")
                page_resgate = ChromiumPage(addr_or_opts=co_resgate)

                for conta in contas_pendentes:
                    email_pendente = conta["email"]
                    senha_jogo = conta["password"]

                    senha_email = prov.buscar_senha_txt(email_pendente)
                    if not senha_email:
                        print(
                            f"{Cores.VERMELHO}"
                            f"⚠️ Senha do Outlook não encontrada no TXT "
                            f"para {email_pendente}. Pulando."
                            f"{Cores.RESET}"
                        )
                        continue

                    sucesso, seed_resgatada = recuperar_otp_pendente(
                        page_resgate,
                        email_pendente,
                        senha_jogo,
                        senha_email,
                        prov,
                    )

                    if sucesso and seed_resgatada:
                        conta["seed_otp"] = seed_resgatada
                        conta["status"] = "PRONTA_PARA_FARMAR"
                        print(
                            f"{Cores.VERDE}"
                            f"✅ Conta {email_pendente} 100% recuperada e salva!"
                            f"{Cores.RESET}"
                        )
                    else:
                        print(
                            f"{Cores.VERMELHO}"
                            f"⚠️ Falha ao resgatar {email_pendente}. "
                            "Ela permanecerá no hospital (SEM_OTP)."
                            f"{Cores.RESET}"
                        )

                # Salva contas atualizadas
                with open(arquivo_json, "w", encoding="utf-8") as f:
                    _json.dump(contas_json, f, indent=4)

                page_resgate.quit()

                print(
                    f"\n{Cores.CIANO}"
                    "🧹 Resgate concluído! Retornando ao fluxo normal "
                    f"de fabricação...\n{Cores.RESET}"
                )
                time.sleep(2)

        except Exception as e:
            print(
                f"{Cores.VERMELHO}Erro na varredura inicial: {e}"
                f"{Cores.RESET}"
            )

    # ── Loop principal de criação ─────────────────────────────────────
    for i in range(qtd_alvo):

        # Parada de emergência: 3 bloqueios seguidos
        if bloqueios_consecutivos >= 3:
            print(
                f"\n{Cores.VERMELHO}"
                "⛔ PARADA DE EMERGÊNCIA: Rede Queimada ou Erro Crítico!"
                f"{Cores.RESET}"
            )
            break

        conta_num = i + 1

        print(
            f"\n{Cores.AZUL}"
            f"=== CONTA {conta_num} DE {qtd_alvo} ==="
            f"{Cores.RESET}"
        )

        tentativas_email = 0
        tentativas_rede = 0
        conta_feita = False
        sessao = None
        reusar_sessao = False

        # Até 3 e-mails por conta
        while tentativas_email < 3 and not conta_feita:

            # Obtém ou reutiliza sessão de e-mail
            if not reusar_sessao:
                sessao = prov.gerar()
                if not sessao:
                    log_erro("Fim dos e-mails (ou erro na API).")
                    break

                print(
                    f"   ✉️  Testando E-mail: "
                    f"{Cores.MAGENTA}{sessao.email}{Cores.RESET}"
                )
                tentativas_rede = 0
            else:
                log_sistema(
                    f"   ♻️  Reutilizando e-mail ({sessao.email}) "
                    "em novo Proxy..."
                )
                reusar_sessao = False

            proxy_local_str = None
            tunel_ativo = None

            try:
                # Configura proxy e túnel se necessário
                if usar_proxy:
                    dados_proxy = prov_proxy.get_proxy()
                    proxy_bruto = dados_proxy["http"]
                    u = urlparse(proxy_bruto)

                    print(
                        f"   🛡️  Gerando sessão: "
                        f"{Cores.VERDE}{u.hostname}:{u.port}{Cores.RESET}"
                    )

                    porta_local = random.randint(35000, 45000)
                    tunel_ativo = TunelAuth(
                        porta_local,
                        u.hostname,
                        u.port,
                        u.username,
                        u.password,
                    )
                    proxy_local_str = tunel_ativo.start()

                    if proxy_local_str:
                        print(
                            f"   🚇 Túnel estabilizado em: "
                            f"{Cores.VERDE}{proxy_local_str}{Cores.RESET}"
                        )
                    else:
                        raise Exception("Falha ao iniciar o túnel local.")

                # Configura ChromiumOptions
                co = ChromiumOptions()
                co.set_argument("--disable-blink-features=WebAuthn")

                user_data = os.path.join(
                    config.BASE_PATH, "profiles", "perfil_mestre"
                )

                os.makedirs(user_data, exist_ok=True)
                co.set_user_data_path(user_data)

                # Argumentos de otimização e privacidade
                co.set_argument(
                    "--disable-features="
                    "OptimizationGuideModelDownloading,"
                    "OptimizationHints,"
                    "OptimizationTargetPrediction,"
                    "OptimizationGuide"

                )

                regras_dns = (
                    "MAP optimizationguide-pa.googleapis.com 127.0.0.1, "
                    "MAP safebrowsing.googleapis.com 127.0.0.1, "
                    "MAP clients2.googleusercontent.com 127.0.0.1, "
                    "MAP passwordsleakcheck-pa.googleapis.com 127.0.0.1, "
                    "MAP *.gvt1.com 127.0.0.1"
                )

                co.set_argument(f'--host-resolver-rules="{regras_dns}"')
                co.set_argument("--disable-quic")
                co.set_argument("--disable-background-networking")
                co.set_argument("--disable-client-side-phishing-detection")
                co.set_argument("--disable-component-update")
                co.set_pref("safebrowsing.enabled", False)
                co.set_argument("--no-first-run")
                co.set_argument("--disable-ipv6")
                co.set_argument("--ignore-certificate-errors")
                co.set_argument("--no-sandbox")
                co.set_argument("--disable-default-apps")
                co.set_argument("--disable-sync")
                co.set_pref(
                    "profile.managed_default_content_settings.images", 1
                )

                if proxy_local_str:
                    co.set_argument(
                        f"--proxy-server={proxy_local_str}"
                    )

                co.headless(bool(config.CONF.get("headless")))

                page = None
                page = ChromiumPage(addr_or_opts=co)
                iniciar_medidor(page)

                # Bloqueia URLs pesadas via CDP
                try:
                    page.run_cdp("Network.enable")
                    page.run_cdp(
                        "Network.setBlockedURLs",
                        urls=[
                            "*.mp4*", "*.webm*", "*.mp3*", "*.wav*",
                            "*.avi*", "*.mkv*",
                            "*customer_section_bg*", "*indieConsoleGame*",
                            "*eventBanner*",
                            "*/static/web/member/assets/*",
                            "*/static/web/gnjoy/assets/*",
                            "*/static/upload/*",
                            "*google-analytics*", "*facebook*",
                            "*doubleclick*", "*tiktok*",
                            "*googletagmanager*", "*youtube*",
                            "*hotjar*",
                            "*optimizationguide-pa.googleapis.com*",
                            "*clients2.googleusercontent.com*",
                            "*safebrowsing.googleapis.com*",
                            "*passwordsleakcheck-pa.googleapis.com*",
                            "*gvt1.com*",
                            "*clientservices.googleapis.com*",
                            "*mtalk.google.com*",
                            "*browser.events.data.microsoft.com*",
                            "*android.clients.google.com*",
                            "*pagead2.googlesyndication.com*",
                            "*eu.adventori.com*", "*adnxs.com*",
                            "*taboola.com*", "*ads.pubmatic.com*",
                        ],
                    )
                    print(
                        "✅ [Proxy] Bloqueios de economia de tráfego "
                        "aplicados com sucesso."
                    )
                except Exception:
                    pass

                # Verifica IP externo se usando proxy
                if usar_proxy:
                    try:
                        page.get(
                            "https://api.ipify.org?format=json",
                            timeout=10,
                        )
                        if "ip" in page.html:
                            import json as _j
                            ip_site = _j.loads(
                                page.ele("tag:body").text
                            )["ip"]
                            print(
                                f"   🎭 IP Externo da Sessão: "
                                f"{Cores.VERDE}{ip_site}{Cores.RESET}"
                            )
                    except Exception:
                        print("   ⚠️ Falha de timeout no verificador de IP.")

                # Cria a conta
                resultado, motivo = criar_conta(
                    page, blacklist_global, sessao, prov
                )

                if resultado:
                    sucessos += 1
                    prov.confirmar_uso(sessao)
                    conta_feita = True
                    bloqueios_consecutivos = 0

                elif motivo in (
                    "EMAIL_BANNED", "EMAIL_EM_USO",
                    "NO_CODE", "NO_OTP_EMAIL"
                ):
                    log_aviso(
                        f"   🗑️  Email Ruim ({motivo}). Descartando..."
                    )
                    prov.confirmar_uso(sessao)
                    tentativas_email += 1
                    reusar_sessao = False

                elif motivo in (
                    "IP_BLOCKED", "CLOUDFLARE_FAIL",
                    "FAIL_FORM", "SELECTOR_ERROR"
                ):
                    tentativas_rede += 1

                    if tentativas_rede < 4:
                        log_aviso(
                            f"   🛡️  Falha de Rede ({motivo}). "
                            f"Trocando Proxy (Tentativa {tentativas_rede}/3)..."
                        )
                        reusar_sessao = True
                        bloqueios_consecutivos += 1
                    else:
                        log_erro(
                            "   ❌ Muitas falhas de rede. Descartando email."
                        )
                        prov.confirmar_uso(sessao)
                        reusar_sessao = False
                        tentativas_email += 1

                else:
                    log_erro(f"Falha ({motivo}).")
                    prov.confirmar_uso(sessao)
                    reusar_sessao = False
                    tentativas_email += 1

            except Exception as e:
                log_erro(f"Erro ao gerar proxy ou túnel: {e}")
                reusar_sessao = True

            finally:
                # Sempre fecha page e túnel
                try:
                    if page:
                        page.quit()
                except Exception:
                    pass

                if tunel_ativo:
                    tunel_ativo.stop()

                if not conta_feita:
                    time.sleep(2)

        # ── Lote completo: pausa + bot de personagens ─────────────────
        if (
            tamanho_lote > 0
            and conta_num % tamanho_lote == 0
            and conta_num < qtd_alvo
            and bloqueios_consecutivos < 3
        ):
            lote_atual = conta_num // tamanho_lote

            print(
                f"\n{Cores.AMARELO}"
                f"📦 LOTE {lote_atual} FINALIZADO!"
                f"{Cores.RESET}"
            )
            print(
                f"\n{Cores.CIANO}"
                "🤖 Pausando fábrica para criar personagens nas contas "
                f"do lote...{Cores.RESET}"
            )

            try:
                import autologin.bot_login as _autologin
                _autologin.bot_login.executar_bot_criacao()
                print(
                    f"\n{Cores.VERDE}"
                    "🔙 Personagens do lote criados! Retornando para "
                    f"a fábrica...{Cores.RESET}"
                )
            except Exception as e:
                print(
                    f"{Cores.VERMELHO}"
                    f"❌ Erro ao chamar o Bot Inteligente: {e}"
                    f"{Cores.RESET}"
                )

            barra_progresso(
                tempo_descanso,
                prefixo="   Resfriando Lote",
                sufixo="",
            )

        else:
            # Pausa aleatória entre contas
            tempo = random.randint(15, 25)
            if not usar_proxy:
                tempo = int(tempo / 2)

            barra_progresso(
                tempo,
                prefixo="   Próxima conta em",
                sufixo="s",
            )

    # ── Encerramento ──────────────────────────────────────────────────
    print(
        f"\n{Cores.AZUL}"
        f"=== Fim. Sucessos: {sucessos}/{qtd_alvo} ==="
        f"{Cores.RESET}"
    )
    print(
        f"Consumo medido: {browser.ACUMULADO_MB:.2f} MB"
    )

    # Varredura final: bot de personagens em contas residuais
    if sucessos > 0:
        print(
            f"\n{Cores.CIANO}"
            "🧹 Varredura Final: Verificando se sobraram contas "
            f"sem personagem...{Cores.RESET}"
        )

        try:
            import autologin.bot_login as _autologin
            _autologin.bot_login.executar_bot_criacao()
            print(
                f"\n{Cores.VERDE}"
                "✅ Todas as contas estão 100% prontas e blindadas!"
                f"{Cores.RESET}"
            )
        except Exception as e:
            print(
                f"{Cores.VERMELHO}"
                f"❌ Erro ao chamar o Bot Inteligente no resíduo final: {e}"
                f"{Cores.RESET}"
            )

    browser.relatorio_final_consumo()

    # Salva blacklist
    if blacklist_global:
        with open(config.ARQUIVO_BLACKLIST, "w") as f:
            for d in blacklist_global:
                f.write(f"{d}\n")

    input("\nEnter para voltar...")


if __name__ == "__main__":
    executar()
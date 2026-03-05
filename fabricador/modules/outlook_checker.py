# fabricador/modules/outlook_checker.py
import time
import re

def _wait_dom_ready(tab, timeout=20):
    """Espera document.readyState ficar interactive/complete."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            state = tab.run_js("return document.readyState;")
            if state in ("interactive", "complete"):
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False

def _safe_get_value(ele):
    """Tenta ler o value de input/textarea de forma tolerante."""
    try:
        return ele.value
    except Exception:
        try:
            return ele.attr("value")
        except Exception:
            return ""

def _force_set_value(tab, css_selector, value: str):
    """Seta value via JS e dispara eventos (alguns forms só pegam assim)."""
    js = r"""
    const sel = arguments[0];
    const val = arguments[1];
    const el = document.querySelector(sel);
    if (!el) return false;
    el.focus();
    el.value = val;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
    """
    return bool(tab.run_js(js, css_selector, value))

def _wait_for_any(tab, selectors, timeout=10, poll=0.25):
    """
    Espera até um dos seletores existir.
    selectors: lista de seletores DrissionPage (ex: 'text:...', '#id', 'css:...')
    Retorna o elemento encontrado (primeiro que aparecer) ou None.
    """
    t0 = time.time()
    while time.time() - t0 < timeout:
        for sel in selectors:
            try:
                ele = tab.ele(sel, timeout=0.2)
                if ele:
                    return ele
            except Exception:
                pass
        time.sleep(poll)
    return None

def buscar_codigo_via_checker(page, conta_full_string, tipo_codigo='cadastro', token_nppr=None):
    URL_CHECKER_FINAL = "https://npprservices.pro/pt/hotmailchecker"
    assunto_chave = 'Guia de verificação de cadastro' if tipo_codigo == 'cadastro' else 'Guia de autenticação do serviço'

    tab_checker = page.new_tab(URL_CHECKER_FINAL)

    try:
        # 0) Espera base de DOM (substitui o .wait.displayed que não existe)
        _wait_dom_ready(tab_checker, timeout=25)

        # 1) TOKEN (só se a página pedir)
        for _ in range(2):
            campo_token = tab_checker.ele('@name=token', timeout=3)
            if not campo_token:
                break  # não pediu token

            if not token_nppr:
                print("❌ [Checker] Tela de token detectada, mas nenhum token foi fornecido.")
                tab_checker.close()
                return None

            print("🔑 [Checker] Inserindo Token...")

            # tenta input normal
            try:
                campo_token.input(token_nppr, clear=True)
            except Exception:
                pass

            # valida e força via JS se necessário
            val = _safe_get_value(campo_token) or ""
            if token_nppr not in val:
                ok = _force_set_value(tab_checker, 'input[name="token"]', token_nppr)
                if not ok:
                    print("❌ [Checker] Não consegui setar o token no campo.")
                    tab_checker.close()
                    return None

            # garante que ficou mesmo
            campo_token = tab_checker.ele('@name=token', timeout=2)
            val2 = (_safe_get_value(campo_token) or "").strip()
            if val2 != token_nppr:
                print(f"❌ [Checker] Token não permaneceu no campo. value='{val2}'")
                tab_checker.close()
                return None

            # clica no botão "Usar token"
            btn_token = (
                tab_checker.ele('text:Usar token', timeout=2)
                or tab_checker.ele('css:button.btn[type="submit"]', timeout=2)
                or tab_checker.ele('css:form button[type="submit"]', timeout=2)
            )
            if not btn_token:
                print("❌ [Checker] Botão 'Usar token' não encontrado.")
                tab_checker.close()
                return None

            try:
                btn_token.click(by_js=True)
            except Exception:
                btn_token.click()

            # espera navegação / carregamento
            try:
                tab_checker.wait.load_start()
            except Exception:
                pass
            _wait_dom_ready(tab_checker, timeout=25)

            # garante que estamos na URL final
            try:
                if URL_CHECKER_FINAL not in tab_checker.url:
                    tab_checker.get(URL_CHECKER_FINAL)
                    _wait_dom_ready(tab_checker, timeout=25)
            except Exception:
                tab_checker.get(URL_CHECKER_FINAL)
                _wait_dom_ready(tab_checker, timeout=25)

        # 2) Loader (se existir)
        print("⏳ [Checker] Aguardando dissipação do loader...")
        try:
            tab_checker.wait.absent('#loader', timeout=15)
        except Exception:
            pass

        # 3) Campo accs + botão começar
        campo_texto = tab_checker.ele('#accs', timeout=10)
        if not campo_texto:
            print("❌ [Checker] Campo #accs não encontrado (não estamos na tela final?).")
            tab_checker.close()
            return None

        # preenche
        try:
            campo_texto.wait.clickable()
        except Exception:
            pass

        try:
            campo_texto.input(conta_full_string, clear=True)
        except Exception:
            _force_set_value(tab_checker, '#accs', conta_full_string)

        # valida que entrou
        val_accs = (_safe_get_value(campo_texto) or "").strip()
        if val_accs != conta_full_string.strip():
            ok = _force_set_value(tab_checker, '#accs', conta_full_string)
            if not ok:
                print("❌ [Checker] Falha ao inserir linha no #accs.")
                tab_checker.close()
                return None

            # revalida
            campo_texto = tab_checker.ele('#accs', timeout=3)
            val_accs2 = (_safe_get_value(campo_texto) or "").strip()
            if val_accs2 != conta_full_string.strip():
                print("❌ [Checker] Linha não permaneceu no #accs após tentativa via JS.")
                tab_checker.close()
                return None

        btn_start = (
            tab_checker.ele('text:Começar', timeout=5)
            or tab_checker.ele('css:#checker-form button[type="submit"]', timeout=5)
            or tab_checker.ele('css:button.btn[type="submit"]', timeout=5)
        )
        if not btn_start:
            print("❌ [Checker] Botão 'Começar' não encontrado.")
            tab_checker.close()
            return None

        try:
            btn_start.wait.clickable()
        except Exception:
            pass

        try:
            btn_start.click(by_js=True)
        except Exception:
            btn_start.click()

        print(f"🚀 [Checker] Busca iniciada para: {tipo_codigo}")

        # ✅ SUBSTITUI sleep(2): espera dinâmica do primeiro resultado/tabela aparecer
        _wait_for_any(
            tab_checker,
            selectors=[
                f'text:{assunto_chave}',   # se o e-mail já aparecer
                'css:#results table',      # ou se a tabela já renderizar
                'css:#results',            # ou ao menos o container aparecer
            ],
            timeout=10
        )

        # 4) Busca o e-mail e extrai o código (sem mexer na sua lógica)
        for tentativa in range(12):
            _wait_dom_ready(tab_checker, timeout=10)

            linha_email = tab_checker.ele(f'text:{assunto_chave}', timeout=3)
            if linha_email:
                print(f"✅ [Checker] E-mail localizado!")

                celula = tab_checker.ele('css:td.clickable.view-email', timeout=3)
                if celula:
                    try:
                        celula.click(by_js=True)
                    except Exception:
                        celula.click()
                else:
                    tab_checker.run_js(
                        'document.querySelector("#results > table > tbody > tr > td.clickable.view-email")?.click();'
                    )

                # ✅ SUBSTITUI sleep(3): espera dinâmica do iframe aparecer (ou o conteúdo carregar)
                _wait_for_any(
                    tab_checker,
                    selectors=['tag:iframe'],
                    timeout=8
                )

                iframe = tab_checker.ele('tag:iframe', timeout=5)
                if iframe:
                    ele_codigo = (
                        iframe.ele('css:p[style*="letter-spacing:12px"]', timeout=2)
                        or iframe.ele('css:p[style*="color:#da0c0c"]', timeout=2)
                    )

                    if ele_codigo:
                        txt = (ele_codigo.text or "").strip()
                        match = re.search(r'\b[A-Za-z0-9]{6}\b', txt)
                        if match:
                            codigo = match.group(0)
                            print(f"🔑 [SUCESSO] Código extraído: {codigo}")
                            tab_checker.close()
                            return codigo

            print(f"⏳ Tentativa {tentativa+1}/12: Aguardando e-mail...")

            # tenta reenviar
            try:
                btn_start.click(by_js=True)
            except Exception:
                try:
                    btn_start.click()
                except Exception:
                    pass

            # ✅ SUBSTITUI sleep(8): wait dinâmico pela próxima “onda” de resultado
            _wait_for_any(
                tab_checker,
                selectors=[
                    f'text:{assunto_chave}',
                    'css:#results table',
                    'css:#results'
                ],
                timeout=10
            )

    except Exception as e:
        print(f"❌ Erro crítico no Checker: {e}")

    try:
        tab_checker.close()
    except Exception:
        pass
    return None
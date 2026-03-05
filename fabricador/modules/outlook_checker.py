# fabricador/modules/outlook_checker.py
import time
import re

def buscar_codigo_via_checker(page, conta_full_string, tipo_codigo='cadastro', token_nppr=None):
    # URL direta do serviço que queremos usar
    URL_CHECKER_FINAL = "https://npprservices.pro/pt/hotmailchecker"
    assunto_chave = 'Guia de verificação de cadastro' if tipo_codigo == 'cadastro' else 'Guia de autenticação do serviço'
    
    # Abrimos a aba diretamente na URL do serviço. 
    # Se o token não estiver ativo nos cookies, o site carregará a tela de "Token não especificado"
    tab_checker = page.new_tab(URL_CHECKER_FINAL)
    
    try:
        # --- 1. INTELIGÊNCIA DE TOKEN (DETECÇÃO DE BLOQUEIO) ---
        # Verifica se o campo de input de token está presente na página atual
        campo_token = tab_checker.ele('@name=token', timeout=3)
        
        if campo_token:
            if not token_nppr:
                print("❌ [Checker] Token necessário, mas não foi fornecido no config.json")
                tab_checker.close()
                return None

            print("🔑 [Checker] Bloqueio detectado: Inserindo Token...")
            campo_token.input(token_nppr)
            
            # Clica no botão "Usar token"
            btn_token = tab_checker.ele('text:Usar token') or tab_checker.ele('.btn')
            if btn_token:
                btn_token.click()
                # Após clicar, o site redireciona para a home ou dashboard. 
                # Forçamos a volta para a URL final do serviço.
                tab_checker.get(URL_CHECKER_FINAL)

        # --- 2. DEFINIÇÃO DE ELEMENTOS DO CHECKER ---
        # Garantimos que os elementos da página do serviço (Print 1) estejam carregados
        campo_texto = tab_checker.ele('#accs', timeout=10)
        btn_start = tab_checker.ele('text:Começar') or tab_checker.ele('.btn-red')

        # --- 3. INSERÇÃO DOS DADOS DA CONTA ---
        if campo_texto:
            campo_texto.clear()
            # Insere a String Full (e-mail|senha|recovery)
            campo_texto.input(conta_full_string)
            time.sleep(1)
            
            if btn_start:
                btn_start.click(by_js=True)
                print(f"🚀 [Checker] Iniciando busca por e-mail de {tipo_codigo}...")
                time.sleep(5)

        # --- 4. BUSCA NA TABELA E EXTRAÇÃO ---
        for tentativa in range(12):
            # Tenta localizar a linha com o assunto específico
            linha_email = tab_checker.ele(f'text:{assunto_chave}', timeout=3)
            
            if linha_email:
                print(f"✅ [Checker] E-mail localizado na tentativa {tentativa+1}!")
                
                # Clique via JavaScript no contêiner da visualização (o "olho")
                # Isso evita o erro de "elemento sem posição ou tamanho"
                script_clique = 'document.querySelector("#results > table > tbody > tr > td.clickable.view-email").click();'
                
                try:
                    tab_checker.run_js(script_clique)
                    print("👁️ Visualização aberta.")
                    time.sleep(5) # Aguarda o carregamento do Iframe dentro do modal

                    # Foco no Iframe (srcdoc) que contém o corpo do e-mail real
                    iframe = tab_checker.ele('tag:iframe')
                    if iframe:
                        # Busca o código no parágrafo vermelho com letter-spacing de 12px
                        ele_codigo = iframe.ele('css:p[style*="letter-spacing:12px"]') or \
                                     iframe.ele('css:p[style*="color:#da0c0c"]')
                        
                        if ele_codigo:
                            texto_limpo = ele_codigo.text.strip()
                            # Regex para capturar os 6 caracteres alfanuméricos exatos
                            match = re.search(r'\b[A-Za-z0-9]{6}\b', texto_limpo)
                            
                            if match:
                                codigo = match.group(0)
                                print(f"🔑 [SUCESSO] Código extraído: {codigo}")
                                tab_checker.close()
                                return codigo
                    else:
                        print("⚠️ Falha: Conteúdo do e-mail (Iframe) não carregou.")
                        
                except Exception as e_js:
                    print(f"⚠️ Erro ao interagir com o modal via JS: {e_js}")

            # Se não encontrou, clica em Começar novamente (Refresh)
            print(f"⏳ Tentativa {tentativa+1}/12: Aguardando e-mail...")
            if btn_start: 
                btn_start.click(by_js=True)
            time.sleep(8)

    except Exception as e:
        print(f"❌ Erro crítico no fluxo do Checker: {e}")
    
    if tab_checker: 
        tab_checker.close()
    return None
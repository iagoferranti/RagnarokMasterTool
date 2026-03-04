# fabricador/modules/outlook_checker.py
import time
import re

def buscar_codigo_via_checker(page, conta_full_string, tipo_codigo='cadastro'):
    URL_CHECKER = "https://npprteam.shop/en/hotmailchecker/"
    assunto_chave = 'Guia de verificação de cadastro' if tipo_codigo == 'cadastro' else 'Guia de autenticação do serviço'
    
    tab_checker = page.new_tab(URL_CHECKER)
    
    try:
        # 1. Inserção e Start
        campo_texto = tab_checker.ele('#accs')
        if campo_texto:
            campo_texto.click()
            campo_texto.clear()
            campo_texto.input(conta_full_string)
            time.sleep(1)

        btn_start = tab_checker.ele('xpath://*[@id="checker-form"]/div[4]/button')
        if btn_start:
            btn_start.click(by_js=True)
            time.sleep(8)

        # 2. Busca na Tabela
        for tentativa in range(12):
            linha_email = tab_checker.ele(f'text:{assunto_chave}', timeout=3)
            
            if linha_email:
                print(f"✅ [Checker] E-mail localizado! Abrindo visualização...")
                btn_view = linha_email.parent('tag:tr').ele('css:td:nth-child(6) span')
                
                if btn_view:
                    btn_view.click()
                    
                    # --- AJUSTE CRÍTICO: AGUARDAR O CONTEÚDO REAL ---
                    # O checker abre um modal que pode carregar o e-mail via iframe ou renderização lenta
                    time.sleep(4) 
                    
                    # Procuramos especificamente o parágrafo vermelho com letter-spacing de 12px
                    # Esse é o seletor mais seguro baseado no seu HTML
                    ele_codigo = tab_checker.ele('css:p[style*="letter-spacing:12px"]', timeout=10) or \
                                 tab_checker.ele('css:p[style*="da0c0c"]', timeout=5)

                    if ele_codigo:
                        texto_final = ele_codigo.text.strip()
                        print(f"DEBUG Texto no elemento alvo: {repr(texto_final)}")
                        
                        # Regex focada: 6 caracteres alfanuméricos
                        match = re.search(r'\b[A-Za-z0-9]{6}\b', texto_final)
                        
                        if match:
                            codigo = match.group(0)
                            print(f"🔑 [SUCESSO] Código extraído: {codigo}")
                            
                            # Fechar modal para limpar o ambiente
                            btn_close = tab_checker.ele('css:.remodal-close') or \
                                        tab_checker.ele('xpath://*[@id="modal"]/div[4]/button')
                            if btn_close:
                                btn_close.click(by_js=True)
                            
                            tab_checker.close()
                            return codigo
                    else:
                        print("⚠️ Conteúdo do código não renderizou a tempo no modal.")

            print(f"⏳ Tentativa {tentativa+1}/12: Aguardando e-mail...")
            if btn_start: btn_start.click(by_js=True)
            time.sleep(6)
            
    except Exception as e:
        print(f"❌ Erro no fluxo: {e}")
    
    if tab_checker: tab_checker.close()
    return None
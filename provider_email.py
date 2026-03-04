import os
import imaplib
import email
import time
from email.header import decode_header

# === IMPORTS DO PROJETO ===
from fabricador import config
from fabricador.modules.logger import log_info, log_erro, log_sistema, Cores

# ==========================================
# 📦 DTO
# ==========================================
class EmailSession:
    def __init__(self, email, password):
        self.email = email
        self.password = password 
        self.provider_name = "ListaFile"
        self.tipo = "local" # Compatibilidade

# ==========================================
# 🏭 CLASSE PROVEDOR LISTA
# ==========================================
class ProviderLista:
    def __init__(self):
        # Usa o caminho centralizado do config
        self.arquivo_entrada = os.path.join(config.BASE_PATH, "emails.txt")
        self.arquivo_saida = os.path.join(config.BASE_PATH, "emails_usados.txt")

    def gerar(self):
        """Lê a primeira linha disponível do arquivo."""
        if not os.path.exists(self.arquivo_entrada): 
            # Cria vazio se não existir
            with open(self.arquivo_entrada, "w") as f: pass
            return None
        
        try:
            with open(self.arquivo_entrada, "r", encoding="utf-8") as f:
                linhas = f.readlines()
        except: return None
        
        linhas_uteis = [l.strip() for l in linhas if l.strip()]
        if not linhas_uteis: return None

        conta_atual = linhas_uteis[0]
        
        # Se a linha não tiver formato email:senha, move para usados e tenta próxima
        if ":" not in conta_atual:
            self.confirmar_uso_string(conta_atual)
            return self.gerar()

        partes = conta_atual.split(":", 1)
        return EmailSession(partes[0].strip(), partes[1].strip())

    def confirmar_uso(self, sessao_obj):
        if not sessao_obj: return
        self.confirmar_uso_string(f"{sessao_obj.email}:{sessao_obj.password}")

    def confirmar_uso_string(self, linha_raw):
        """Move a linha de emails.txt para emails_usados.txt"""
        try:
            # 1. Adiciona no arquivo de usados
            with open(self.arquivo_saida, "a", encoding="utf-8") as f:
                f.write(linha_raw.strip() + "\n")
            
            # 2. Lê o arquivo original
            with open(self.arquivo_entrada, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            
            # 3. Filtra removendo a linha usada
            novas = [l for l in linhas if l.strip() != linha_raw.strip() and l.strip()]
            
            # 4. Reescreve o arquivo original
            with open(self.arquivo_entrada, "w", encoding="utf-8") as f:
                f.writelines(novas)
        except Exception as e:
            log_erro(f"Erro ao atualizar lista de emails: {e}")

    # ==========================================
    # 🕵️‍♂️ FUNÇÕES IMAP (Compatibilidade Total)
    # ==========================================
    
    def _get_imap_config(self, email_addr):
        """Retorna (servidor, lista_de_pastas) baseado no domínio."""
        imap_db = {
            "outlook": ("outlook.office365.com", ["INBOX", "Junk"]),
            "hotmail": ("outlook.office365.com", ["INBOX", "Junk"]),
            "live":    ("outlook.office365.com", ["INBOX", "Junk"]),
            "rambler": ("imap.rambler.ru", ["INBOX", "Spam"]),
            "yandex":  ("imap.yandex.com", ["INBOX", "Spam", "Junk"]),
            "gmail":   ("imap.gmail.com", ["INBOX", "[Gmail]/Spam"]),
            "mail.ru": ("imap.mail.ru", ["INBOX", "Spam"]),
            "yahoo":   ("imap.mail.yahoo.com", ["INBOX", "Bulk"]),
        }
        domain = email_addr.split("@")[1].lower()
        
        # Busca direta
        for key, val in imap_db.items():
            if key in domain: return val
        
        # Casos especiais Russos (Rambler Family)
        if any(x in domain for x in ["lenta.ru", "ro.ru", "autorambler", "myrambler"]):
             return imap_db["rambler"]
        
        # Casos especiais Mail.ru Family
        if any(x in domain for x in ["bk.ru", "list.ru", "inbox.ru", "internet.ru"]):
             return imap_db["mail.ru"]
             
        # Default (Geralmente Outlook ou cPanel)
        return ("outlook.office365.com", ["INBOX", "Junk"]) 

    def limpar_caixa(self, obj):
        """Marca todos os emails como LIDOS para não confundir."""
        server, pastas = self._get_imap_config(obj.email)
        try:
            mail = imaplib.IMAP4_SSL(server, timeout=10)
            mail.login(obj.email, obj.password)
            for pasta in pastas:
                try:
                    mail.select(pasta)
                    status, messages = mail.search(None, 'UNSEEN')
                    if status == "OK":
                        for num in messages[0].split():
                            mail.store(num, '+FLAGS', '\\Seen')
                except: pass
            mail.logout()
            return True
        except: return False

    def validar_acesso_imap(self, obj):
        """Testa login rápido."""
        server, _ = self._get_imap_config(obj.email)
        try:
            mail = imaplib.IMAP4_SSL(server, timeout=10)
            mail.login(obj.email, obj.password)
            mail.logout()
            return True
        except: return False

    def esperar_codigo(self, obj, filtro_assunto=""):
        """Busca email não lido e retorna o CORPO HTML."""
        server, pastas = self._get_imap_config(obj.email)
        try:
            mail = imaplib.IMAP4_SSL(server)
            mail.login(obj.email, obj.password)
            
            for pasta in pastas:
                try:
                    status, _ = mail.select(pasta)
                    if status != "OK": continue
                except: continue

                # Busca UNSEEN (novos)
                status, messages = mail.search(None, 'UNSEEN')
                
                # Se não achar novos, tenta ALL (caso tenha marcado lido sem querer)
                if status != "OK" or not messages[0]: 
                    status, messages = mail.search(None, 'ALL')

                if status != "OK" or not messages[0]: continue 
                
                # Pega os 3 últimos emails (garantia)
                email_ids = messages[0].split()
                for num in reversed(email_ids[-3:]):
                    try:
                        _, data = mail.fetch(num, "(RFC822)")
                        msg = email.message_from_bytes(data[0][1])
                        
                        subject = self._decodificar_header(msg["Subject"])
                        
                        # Filtro básico de assunto
                        keywords = ["otp", "autenticação", "código", "verification", "code", "gnjoy"]
                        if not any(k in subject.lower() for k in keywords):
                            continue

                        print(f"   🔎 [IMAP] Chegou: '{subject[:40]}...'")

                        if filtro_assunto and filtro_assunto.lower() not in subject.lower():
                            continue

                        body = self._extrair_corpo(msg)
                        
                        mail.logout()
                        return body # Retorna o corpo HTML para o actions.py extrair o código
                    except: continue
            mail.logout()
            return None
        except: return None

    def _decodificar_header(self, header_raw):
        if not header_raw: return ""
        try:
            decoded_list = decode_header(header_raw)
            texto = ""
            for bytes_part, encoding in decoded_list:
                if isinstance(bytes_part, bytes):
                    texto += bytes_part.decode(encoding or "utf-8", errors="ignore")
                else: texto += str(bytes_part)
            return texto
        except: return str(header_raw)

    def _extrair_corpo(self, msg):
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try: return part.get_payload(decode=True).decode(errors="ignore")
                    except: pass
        else:
            try: return msg.get_payload(decode=True).decode(errors="ignore")
            except: pass
        return body
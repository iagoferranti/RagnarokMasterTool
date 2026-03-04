# fabricador/provider_gmail.py

import imaplib
import email
import time
import random

from .modules.utils import extrair_codigo_seguro, delay_humano

# Atenção: esses dados estavam hardcoded no binário.
# Se você não quiser expor, altere manualmente depois.
GMAIL_USER = "rag.na.rok.08064@gmail.com"
GMAIL_PASS = "yflnowkvkmcjsitg"


def gerar_email_variacao_dot() -> str:
    """
    Gera uma variação do e-mail GMAIL_USER inserindo pontos de forma
    pseudo-aleatória na parte local (antes do @), aproveitando o recurso
    de aliases do Gmail.
    """
    nome, dominio = GMAIL_USER.split("@")
    caracteres = list(nome.replace(".", ""))

    for i in range(len(caracteres) - 1, 0, -1):
        if random.choice([True, False]):
            caracteres.insert(i, ".")

    email_gerado = "".join(caracteres) + "@" + dominio
    return email_gerado



def buscar_codigo_no_gmail(timeout: int = 60) -> str | None:
    """
    Fica monitorando a caixa de entrada do GMAIL_USER via IMAP,
    aguardando um e-mail da GNJOY com código de verificação.

    Estratégia:
      - Conecta em imap.gmail.com usando IMAP4_SSL
      - Faz login com GMAIL_USER / GMAIL_PASS
      - Seleciona INBOX
      - Busca e-mails não lidos (UNSEEN)
      - Pega o último, extrai corpo HTML ou texto
      - Usa extrair_codigo_seguro() para localizar código de 6 chars
      - Se achar, marca e-mail como \\Deleted e expunge
      - Loop até timeout expirar (checa a cada ~5s)

    Retorna:
        str  -> código encontrado
        None -> se não encontrar no tempo limite ou em caso de erro
    """
    start_time = time.time()
    print(f"📧 Aguardando e-mail da GNJOY em {GMAIL_USER}...")

    while time.time() - start_time < timeout:
        try:
            # Conexão IMAP
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_PASS)
            mail.select("inbox")

            status, data = mail.search(None, "(UNSEEN)")
            mail_ids = data[0].split()

            if mail_ids:
                latest_id = mail_ids[-1]

                status, data = mail.fetch(latest_id, "(RFC822)")
                raw_email = data[0][1].decode("utf-8", errors="ignore")
                msg = email.message_from_string(raw_email)

                corpo = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/html":
                            corpo = (
                                part.get_payload(decode=True)
                                .decode()
                            )
                            break
                else:
                    corpo = (
                        msg.get_payload(decode=True)
                        .decode()
                    )

                codigo = extrair_codigo_seguro(corpo)

                if codigo:
                    print(f"✅ Código encontrado: {codigo}")

                    # Marca como apagado e expunge
                    mail.store(latest_id, "+FLAGS", "\\Deleted")
                    mail.expunge()
                    mail.logout()
                    return codigo

                mail.logout()

        except Exception as e:
            print(f"⚠️ Erro ao acessar Gmail: {e}")

        time.sleep(5)

    print("❌ Timeout: E-mail da GNJOY não chegou.")
    return None
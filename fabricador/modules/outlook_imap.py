# fabricador/modules/outlook_imap.py

import re
import time
from imap_tools import MailBox, AND


IMAP_SERVER = "imap-mail.outlook.com"


def _extrair_codigo(corpo_texto: str) -> str | None:
    """
    Tenta extrair o código de 6 caracteres alfanuméricos do corpo do e-mail.
    Prioriza padrões comuns do GNJOY antes de fazer match genérico.
    """
    if not corpo_texto:
        return None

    # Padrão 1: código isolado numa linha (comum em e-mails transacionais)
    match = re.search(r'(?:código|code)[^\n]*?([A-Za-z0-9]{6})', corpo_texto, re.IGNORECASE)
    if match:
        return match.group(1)

    # Padrão 2: linha com apenas 6 caracteres alfanuméricos
    for linha in corpo_texto.splitlines():
        linha = linha.strip()
        if re.fullmatch(r'[A-Za-z0-9]{6}', linha):
            if linha.lower() not in ('vindas', 'online', 'latam.'):
                return linha

    # Padrão 3: fallback genérico
    matches = re.findall(r'\b[A-Za-z0-9]{6}\b', corpo_texto)
    ignorar = {'vindas', 'online', 'latam.', 'gnjoy.', 'click', 'email'}
    for m in matches:
        if m.lower() not in ignorar:
            return m

    return None


def buscar_codigo_outlook_imap(
    email: str,
    senha: str,
    tipo_codigo: str = 'cadastro',
    timeout: int = 90,
    intervalo: int = 8,
) -> str | None:
    """
    Acessa o Outlook via IMAP e extrai o código de verificação do GNJOY.

    Args:
        email:       Endereço da conta Outlook.
        senha:       Senha da conta.
        tipo_codigo: 'cadastro' ou 'otp'.
        timeout:     Tempo máximo de espera em segundos (padrão 90s).
        intervalo:   Intervalo entre tentativas em segundos (padrão 8s).

    Retorna:
        str  -> código encontrado
        None -> não encontrou dentro do timeout
    """
    assunto_chave = (
        'Guia de verificação de cadastro'
        if tipo_codigo == 'cadastro'
        else 'Guia de autenticação do serviço'
    )

    print(f"📧 [IMAP] Conectando para {email}...")

    pastas = ['INBOX', 'Junk']
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with MailBox(IMAP_SERVER).login(email, senha) as mailbox:

                for pasta in pastas:
                    try:
                        mailbox.folder.set(pasta)
                    except Exception:
                        continue

                    msgs = list(
                        mailbox.fetch(
                            AND(subject=assunto_chave),
                            limit=5,
                            reverse=True,
                            mark_seen=False,  # não marca como lido ainda
                        )
                    )

                    for msg in msgs:
                        # Prefere texto puro; se não tiver, limpa o HTML
                        if msg.text:
                            corpo = msg.text
                        elif msg.html:
                            # Remove tags HTML antes de procurar o código
                            corpo = re.sub(r'<[^>]+>', ' ', msg.html)
                        else:
                            continue

                        codigo = _extrair_codigo(corpo)
                        if codigo:
                            print(
                                f"🔑 [IMAP] Código '{codigo}' encontrado "
                                f"na pasta '{pasta}'."
                            )
                            return codigo

        except Exception as e:
            print(f"❌ [IMAP] Erro: {e}")

        restante = deadline - time.time()
        if restante <= 0:
            break

        print(
            f"⏳ [IMAP] Código ainda não chegou. "
            f"Aguardando {intervalo}s... "
            f"(restam ~{int(restante)}s)"
        )
        time.sleep(intervalo)

    print(f"⌛ [IMAP] Timeout atingido para {email}. Código não encontrado.")
    return None
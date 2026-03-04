# fabricador/provider_gmail_proprio.py

import imaplib
import email
import time
import os

from .modules.utils import extrair_codigo_seguro
from email.header import decode_header

# Atenção: estavam hardcoded no executável
GMAIL_USER = "rag.na.rok.08064@gmail.com"
GMAIL_PASS = "yflnowkvkmcjsitg"

ARQUIVO_ALIASES = "meus_aliases.txt"


class SessaoBridge:
    """Sessão simples que só carrega um e-mail (alias)."""

    __firstlineno__ = 13
    __static_attributes__ = ("email",)

    def __init__(self, email: str):
        self.email = email


class ProviderGmailProprio:
    """
    Provider que usa seus próprios aliases de Gmail, listados em
    `meus_aliases.txt` (um e-mail por linha).

    Fluxo:
      - `gerar()` entrega o próximo alias disponível.
      - `esperar_codigo()` conecta no Gmail via IMAP e busca o e-mail
        da GNJOY com assunto correspondente (cadastro / autenticação),
        retornando o corpo HTML bruto do e-mail.
    """

    __firstlineno__ = 17
    __static_attributes__ = ("aliases",)

    def __init__(self):
        self.aliases = self._carregar_aliases()

    def _carregar_aliases(self):
        """
        Carrega a lista de aliases a partir de `meus_aliases.txt`.

        Retorna lista de strings (e-mails). Linhas vazias são ignoradas.
        """
        if not os.path.exists(ARQUIVO_ALIASES):
            print(f"⚠️ Erro: Arquivo {ARQUIVO_ALIASES} não encontrado!")
            return []

        try:
            with open(ARQUIVO_ALIASES, "r", encoding="utf-8") as f:
                return [
                    linha.strip()
                    for linha in f
                    if linha.strip()
                ]
        except Exception:
            # Em caso de erro de leitura, retorna None no bytecode,
            # mas aqui devolvemos [] para simplificar o uso.
            return []

    def gerar(self) -> SessaoBridge:
        """
        Retira o próximo alias disponível e o persiste de volta no arquivo
        (sem o alias já utilizado).

        Levanta Exception se não houver mais aliases.
        """
        if not self.aliases:
            raise Exception(
                "Todos os Aliases do Outlook foram utilizados!"
            )

        email_da_vez = self.aliases.pop(0)

        with open(ARQUIVO_ALIASES, "w", encoding="utf-8") as f:
            f.writelines(l + "\n" for l in self.aliases)

        return SessaoBridge(email_da_vez)

    def confirmar_uso(self, sessao: SessaoBridge) -> None:
        """
        Mantida por compatibilidade com outros providers.
        Aqui, o alias já é removido no momento do `gerar()`,
        então não há nada para fazer.
        """
        return None

    def esperar_codigo(
        self,
        sessao: SessaoBridge,
        filtro_assunto: str,
        _placeholder: str = "",
    ):
        """
        Aguarda até ~90 segundos por um e-mail da GNJOY na caixa
        `INBOX` do GMAIL_USER, não necessariamente enviado ao alias.

        `filtro_assunto`:
            "cadastro"    -> 'verificação de cadastro'
            "autenticacao"-> 'autenticação do serviço'
            outro         -> não filtra por termo específico

        Retorna:
            str  -> corpo HTML bruto do e-mail encontrado
            None -> timeout ou erro IMAP
        """
        start = time.time()

        termos_busca = {
            "cadastro": "verificação de cadastro",
            "autenticacao": "autenticação do serviço",
        }

        termo_alvo = termos_busca.get(
            filtro_assunto, ""
        ).lower()

        while time.time() - start < 90:
            try:
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(GMAIL_USER, GMAIL_PASS)
                mail.select("inbox")

                status, data = mail.search(
                    None, "(UNSEEN)"
                )

                mail_ids = data[0].split()

                for m_id in reversed(mail_ids):
                    status, data = mail.fetch(
                        m_id, "(RFC822)"
                    )
                    raw = data[0][1].decode(
                        "utf-8",
                        errors="ignore",
                    )
                    msg = email.message_from_string(raw)

                    # Decodifica Subject com suporte a múltiplos encodes
                    subject_raw = msg.get("Subject", "")
                    decoded_parts = decode_header(subject_raw)

                    assunto = ""
                    for content, encoding in decoded_parts:
                        if isinstance(content, bytes):
                            assunto += content.decode(
                                encoding or "utf-8",
                                errors="ignore",
                            )
                        else:
                            assunto += str(content)

                    assunto = assunto.lower()

                    print(
                        "   🔎 Chegou no Gmail: '"
                        f"{assunto[:40]}...'"
                    )

                    # Se há termo alvo e não está no assunto, ignora
                    if termo_alvo and termo_alvo in assunto:
                        # nesse caso o bytecode volta pro loop sem tratar
                        # (parece um "pré-filtro"), então continua
                        continue

                    corpo = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            if (
                                part.get_content_type()
                                == "text/html"
                            ):
                                corpo = (
                                    part.get_payload(
                                        decode=True
                                    )
                                    .decode(
                                        "utf-8",
                                        errors="ignore",
                                    )
                                )
                                break
                    else:
                        corpo = (
                            msg.get_payload(
                                decode=True
                            )
                            .decode(
                                "utf-8",
                                errors="ignore",
                            )
                        )

                    # Marca como lido/apagado
                    mail.store(
                        m_id, "+FLAGS", "\\Deleted"
                    )
                    mail.expunge()
                    mail.logout()

                    return corpo

                # nada útil:
                mail.logout()
                time.sleep(5)

            except Exception as e:
                print(f"      ⚠️ Erro IMAP Gmail: {e}")
                time.sleep(5)

        return None
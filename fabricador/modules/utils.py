# fabricador/modules/utils.py

import re
import unicodedata
import time
import random


def gerar_senha_ragnarok() -> str:
    """Retorna a senha padrão usada nas contas do Ragnarok."""
    return "Ragnarok@2025"


def delay_humano() -> None:
    """Pausa com um delay aleatório, simulando comportamento humano."""
    time.sleep(random.uniform(0.8, 1.5))


def gerar_dados_pessoais() -> tuple[str, str]:
    """Gera um par (nome, sobrenome) simples em PT-BR."""
    nomes = [
        "Lucas",
        "Pedro",
        "Marcos",
        "Gabriel",
        "Rafael",
        "Daniel",
        "Thiago",
        "Matheus",
        "Bruno",
    ]
    sobrenomes = [
        "Silva",
        "Santos",
        "Oliveira",
        "Souza",
        "Pereira",
        "Lima",
        "Carvalho",
        "Ferreira",
    ]

    return random.choice(nomes), random.choice(sobrenomes)


def limpar_html(texto_html: str) -> str:
    """Remove tags HTML básicas de um texto, retornando só o conteúdo plano."""
    if not texto_html:
        return ""
    # remove qualquer coisa entre <...>
    return re.sub(re.compile(r"<.*?>"), " ", texto_html)


def extrair_codigo_seguro(texto_bruto: str) -> str | None:
    """
    Extrai com segurança um código de 6 caracteres (letras/dígitos) de um HTML ou texto de e-mail.

    Estratégia:
      1. Tenta padrão em span vermelho específico (color:#da0c0c)
      2. Limpa HTML, normaliza, colapsa espaços
      3. Tenta achar uma frase tipo 'código de verificação: XXXXXX'
      4. Se falhar, procura QUALQUER token de 6 caracteres A-Za-z0-9,
         ignorando palavras da BLACKLIST, preferindo códigos numéricos.
    """
    if not texto_bruto:
        return None

    # 1) Padrão de código em cor específica (vermelho) no HTML
    match_cor = re.search(
        r"color:#da0c0c[^>]*>\s*([A-Za-z0-9]{6})\s*<",
        texto_bruto,
    )
    if match_cor:
        return match_cor.group(1).strip()

    # 2) Limpa HTML, normaliza entidade &nbsp; e espaços
    texto = limpar_html(texto_bruto).replace("&nbsp;", " ")

    texto = unicodedata.normalize("NFKC", texto)

    texto_body = re.sub(r"[ \t]+", " ", texto).strip()

    # Conjunto de palavras a ignorar quando forem confundidas com códigos
    BLACKLIST = {
        "yellow",
        "vinda",
        "border",
        "please",
        "script",
        "verifi",
        "guia",
        "assets",
        "access",
        "simple",
        "source",
        "codigo",
        "window",
        "bottom",
        "styles",
        "target",
        "active",
        "center",
        "system",
        "title",
        "select",
        "email",
        "service",
        "member",
        "sign",
        "server",
        "online",
        "strong",
        "abaixo",
        "follow",
        "client",
        "format",
        "cation",
        "family",
        "public",
        "style",
        "guide",
        "segura",
        "serviço",
        "button",
        "header",
        "weight",
        "device",
        "gnjoy",
        "ground",
        "latam",
        "width",
        "height",
    }

    # 3) Padrão textual explícito: "código de verificação: XXXXXX"
    m = re.search(
        r"c[oó]digo\s+de\s+verifica[cç][aã]o\s*[:\-]?\s*[\r\n]*\s*([A-Za-z0-9]{6})\b",
        texto_body,
        re.IGNORECASE,
    )
    if m:
        cod = m.group(1).strip()
        # Se o código em minúsculas estiver NA BLACKLIST, descarta (parece palavra)
        if cod.lower() not in BLACKLIST:
            return cod

    # 4) Fallback: qualquer token de 6 chars alfanuméricos
    candidates = re.findall(r"\b[A-Za-z0-9]{6}\b", texto_body)

    for cand in candidates:
        # Prioriza totalmente numérico
        if cand.isnumeric():
            return cand

        # Depois, qualquer outro token de 6 chars que não esteja na blacklist
        if cand.lower() not in BLACKLIST:
            return cand

    return None
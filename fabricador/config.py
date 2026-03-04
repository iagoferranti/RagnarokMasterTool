# fabricador/config.py

import os
import sys
import json

# Detecta se está rodando frozen (PyInstaller)
if getattr(sys, "frozen", False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    CAMINHO_ATUAL = os.path.dirname(os.path.abspath(__file__))
    BASE_PATH = os.path.dirname(CAMINHO_ATUAL)

ARQUIVO_CONFIG        = os.path.join(BASE_PATH, "config.json")
ARQUIVO_SALVAR        = os.path.join(BASE_PATH, "novas_contas.json")
ARQUIVO_PRINCIPAL     = os.path.join(BASE_PATH, "accounts.json")
ARQUIVO_BLACKLIST     = os.path.join(BASE_PATH, "blacklist_dominios.txt")
ARQUIVO_EMAILS        = os.path.join(BASE_PATH, "emails.txt")
ARQUIVO_EMAILS_USADOS = os.path.join(BASE_PATH, "emails_usados.txt")
ARQUIVO_UTI_JSON      = os.path.join(BASE_PATH, "uti_contas.json")

URL_LISTA_VIP = (
    "https://gist.githubusercontent.com/iagoferranti/"
    "2675637690215af512e1e83e1eaf5e84/raw/emails.json"
)

MODO_ECONOMICO  = True
TIMEOUT_PADRAO  = 40

# Configs padrão embutidos (podem ser sobrescritos pelo config.json)
CONF = {
    "owner_email":     "iago.cortellini@gmail.com",
    "licenca_email":   "",
    "headless":        False,
    "tag_email":       "rag",
    "sobrenome_padrao": "Silva",
    "telegram_token":  "",
    "telegram_chat_id": "",
    "smailpro_key":    "",
}


def carregar_user_config():
    """
    Lê o arquivo config.json (se existir) e atualiza o dicionário CONF
    com os valores personalizados do usuário.
    """
    if not os.path.exists(ARQUIVO_CONFIG):
        return CONF

    try:
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                user_config = json.load(f)

            CONF.update(user_config)
            return CONF

        except Exception:
            # erro no with/parse: cai no bloco externo
            return CONF

    except Exception as e:
        print(f"Erro ao ler config.json: {e}")
        return CONF


# Aplica config do usuário na importação
carregar_user_config()
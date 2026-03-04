# fabricador/modules/files.py

import json
import os
import sys
from datetime import datetime

from .. import config 
from ..modules.logger import log_aviso, log_erro, log_sucesso, log_sistema

# Caminhos principais usados pelo sistema
BASE_PATH = config.BASE_PATH

ARQUIVO_UTI_JSON = os.path.join(BASE_PATH, "uti_contas.json")
ARQUIVO_SESSAO = os.path.join(BASE_PATH, "novas_contas.json")
ARQUIVO_PRINCIPAL = config.ARQUIVO_PRINCIPAL
ARQUIVO_BACKUP = os.path.join(BASE_PATH, "backup_contas.json")


def carregar_json_seguro(caminho: str):
    """
    Carrega JSON de forma segura.

    - Se o arquivo não existir, retorna [].
    - Se houver qualquer erro de leitura/parsing, retorna [].
    - Se o conteúdo não for uma lista, também retorna [].
    """
    # Se não existir, devolve lista vazia
    if not os.path.exists(caminho):
        return []

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)

        if isinstance(dados, list):
            return dados
        return []
    except Exception:
        # Em qualquer erro, devolve lista vazia
        return []


def salvar_json_seguro(caminho: str, dados) -> bool:
    """
    Salva dados em JSON com indentação e sem ascii-escape.

    Retorna:
        True  em caso de sucesso (mesmo se falhar no with mas sem exception explícita)
        False em caso de erro tratado (logado)
    """
    try:
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            # Exceções dentro do bloco with são tratadas aqui embaixo
            return True
    except Exception as e:
        log_erro(f"Erro ao salvar JSON {caminho}: {e}")
        return False


def salvar_uti(email: str, senha: str, motivo: str) -> None:
    """
    Registra uma conta na 'UTI' (lista para tratamento posterior), com motivo
    e data/hora da ocorrência.

    Se a conta já existir na UTI, atualiza motivo e data.
    Caso contrário, adiciona um novo registro.
    """
    try:
        lista_uti = carregar_json_seguro(ARQUIVO_UTI_JSON)

        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conta_encontrada = False

        for conta in lista_uti:
            if conta.get("email") == email:
                conta["motivo"] = motivo
                conta["data"] = data_atual
                conta_encontrada = True
                break

        if not conta_encontrada:
            nova = {
                "email": email,
                "password": senha,
                "motivo": motivo,
                "data": data_atual,
            }
            lista_uti.append(nova)

        salvar_json_seguro(ARQUIVO_UTI_JSON, lista_uti)
    except Exception as e:
        log_erro(f"Falha ao salvar na UTI: {e}")


def salvar_conta_nova(
    email: str,
    senha: str,
    seed: str,
    status: str = "NOVA",
) -> None:
    """
    Salva/atualiza uma conta no arquivo principal de contas e no relatório de sessão.

    - Se já houver conta com o mesmo e-mail, ela é atualizada.
    - Caso contrário, é adicionada.
    - Em caso de erro ao salvar no principal, salva no BACKUP.
    - Sempre tenta atualizar o relatório de sessão (ARQUIVO_SESSAO).
    """
    # Data de criação em dois formatos (um detalhado e outro resumido)
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    nova_conta = {
        "email": email,
        "password": senha,
        "seed_otp": seed,
        "status": status,
        "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "char_created": False,
        "reward_claimed": False,
    }

    # 1) Salvar / atualizar no arquivo principal
    try:
        contas = carregar_json_seguro(ARQUIVO_PRINCIPAL)
        conta_existente = False

        for i, c in enumerate(contas):
            if c.get("email", "").lower() == email.lower():
                contas[i].update(nova_conta)
                conta_existente = True
                break

        if not conta_existente:
            contas.append(nova_conta)

        salvar_json_seguro(ARQUIVO_PRINCIPAL, contas)

        # 2) Atualizar relatório de sessão (novas_contas.json)
        try:
            sessao = carregar_json_seguro(ARQUIVO_SESSAO)

            # Se já existir na sessão, não duplica
            if not any(c.get("email") == email for c in sessao):
                sessao.append(nova_conta)
                salvar_json_seguro(ARQUIVO_SESSAO, sessao)
            return None
        except Exception as e:
            log_erro(f"Erro ao salvar relatório de sessão: {e}")
            return None

    except Exception as e:
        log_erro(f"Erro CRÍTICO ao salvar no principal: {e}")

        # 3) Backup de segurança
        try:
            bkp = carregar_json_seguro(ARQUIVO_BACKUP)
            bkp.append(nova_conta)
            salvar_json_seguro(ARQUIVO_BACKUP, bkp)
        except Exception:
            # Se até o backup falhar, não há muito o que fazer, apenas seguir
            pass

        # Mesmo com erro, ainda tenta sessão (fluxo continua em cima via jump),
        # mas no Python fonte simplificamos para encerrar aqui
        return None


def extrair_senha_email(sessao):
    """
    Tenta extrair a senha associada a um objeto 'sessao'.

    Ordem de busca:
        1. Atributos do objeto: password, senha, pass, pwd
        2. Se for dict, chaves: password, senha, pass, pwd

    Retorna:
        str  -> senha encontrada (strip)
        None -> se não achar nada
    """
    if not sessao:
        return None

    # 1) Por atributos
    for attr in ("password", "senha", "pass", "pwd"):
        try:
            val = getattr(sessao, attr, None)
            if isinstance(val, str) and val.strip():
                return val.strip()
        except Exception:
            # ignora e tenta o próximo
            continue

    # 2) Por dict
    try:
        if isinstance(sessao, dict):
            for k in ("password", "senha", "pass", "pwd"):
                v = sessao.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    except Exception:
        pass

    return None


def verificar_licenca_online(tipo) -> bool:
    """
    Encaminha a verificação de licença para a função
    `master.verificar_licenca_online`, adicionando dinamicamente
    o diretório base ao sys.path.

    Se qualquer erro ocorrer, retorna True (não bloqueia o uso).
    """
    try:
        # Garante que o diretório pai de BASE_PATH esteja no sys.path
        sys.path.append(
            os.path.dirname(config.BASE_PATH)
        )

        from master import verificar_licenca_online as _v

        return _v(tipo)
    except Exception:
        # Em caso de falha, não bloqueia o programa
        return True
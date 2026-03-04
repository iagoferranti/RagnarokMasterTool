# fabricador/modules/logger.py

import sys
import time
from datetime import datetime


class Cores:
    __firstlineno__ = 6
    __static_attributes__ = ()

    RESET = "\x1b[0m"

    VERDE = "\x1b[92m"
    AMARELO = "\x1b[93m"
    VERMELHO = "\x1b[91m"
    CIANO = "\x1b[96m"
    AZUL = "\x1b[94m"
    MAGENTA = "\x1b[95m"
    CINZA = "\x1b[90m"

    NEGRITO = "\x1b[1m"
    ITALICO = "\x1b[3m"


def exibir_banner():
    print(
        f"{Cores.CIANO}"
        "\n    ╔══════════════════════════════════════════════════════════════╗\n"
        "    ║      🏭   R A G N A R O K   A C C O U N T   F A C T O R Y    ║\n"
        "    ╚══════════════════════════════════════════════════════════════╝\n"
        f"    {Cores.RESET}"
    )


def log_info(msg: str):
    print(
        f"{Cores.CIANO}"
        " ℹ️  "
        f"{Cores.NEGRITO}"
        "INFO:"
        f"{Cores.RESET} "
        f"{msg}"
    )


def log_sucesso(msg: str):
    print(
        f"{Cores.VERDE}"
        " ✅ "
        f"{Cores.NEGRITO}"
        "SUCESSO:"
        f"{Cores.RESET} "
        f"{msg}"
    )


def log_aviso(msg: str):
    print(
        f"{Cores.AMARELO}"
        " ⚠️  "
        f"{Cores.NEGRITO}"
        "ALERTA:"
        f"{Cores.RESET} "
        f"{msg}"
    )


def log_erro(msg: str):
    print(
        f"{Cores.VERMELHO}"
        " ❌ "
        f"{Cores.NEGRITO}"
        "ERRO:"
        f"{Cores.RESET} "
        f"{msg}"
    )


def log_sistema(msg: str):
    print(
        f"{Cores.CINZA}"
        "    └── "
        f"{msg}"
        f"{Cores.RESET}"
    )


def log_debug(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(
        f"{Cores.CINZA}"
        f"    [DEBUG {ts}] "
        f"{msg}"
        f"{Cores.RESET}"
    )


def barra_progresso(
    tempo_total: float,
    prefixo: str = "",
    sufixo: str = "",
    comprimento: int = 30,
    preenchimento: str = "█",
):
    """
    Barra de progresso temporal (não baseada em steps, mas no tempo total).

    Exemplo:
        barra_progresso(10, prefixo="Progresso", sufixo="Completado")
    """
    start_time = time.time()

    while True:
        elapsed_time = time.time() - start_time

        if elapsed_time > tempo_total:
            break

        percent = 100 * (elapsed_time / float(tempo_total))
        filled_length = int(comprimento * elapsed_time // tempo_total)

        bar = preenchimento * filled_length + "-" * (comprimento - filled_length)

        sys.stdout.write(
            "\r"
            f"{prefixo}"
            " |"
            f"{Cores.CIANO}{bar}{Cores.RESET}"
            "| "
            f"{percent:.1f}% "
            f"{sufixo}"
        )
        sys.stdout.flush()
        time.sleep(0.1)

    sys.stdout.write("\n")
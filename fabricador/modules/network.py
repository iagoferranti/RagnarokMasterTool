# fabricador/modules/network.py

import socket
import threading
import select
import base64
import random
import requests
import time
from urllib.parse import urlparse

try:
    from .logger import (
        log_sistema,
        log_erro,
        log_info,
        log_aviso,
        Cores,
    )
except ImportError:
    # Fallback simples para ambientes sem logger
    log_sistema = print
    log_erro = print
    log_info = print
    log_aviso = print

    class Cores:
        __firstlineno__ = 18
        __static_attributes__ = ()

        AMARELO = ""
        RESET = ""
        VERDE = ""


# ──────────────────────────────────────────────────────────────────────
#  PROXY LUNA
# ──────────────────────────────────────────────────────────────────────


def obter_credenciais_luna(region: str = "br") -> dict:
    """
    Gera um usuário/proxy de sessão para LunaProxy.

    Retorna um dict de proxies no formato aceito por requests:
        {
            "http":  "http://user-...:pass@host:port",
            "https": "http://user-...:pass@host:port",
        }
    """
    # Credenciais embutidas (podem ser sobrescritas depois)
    LUNA_USER = "y2ykbl1mumcl"
    LUNA_PASS = "Nbj77zLkb9div"
    LUNA_HOST = "pr-new.lunaproxy.com"
    LUNA_PORT = "12233"

    session_id = f"sess{random.randint(100000, 999999)}"
    sess_time = "10"  # minutos

    proxy_user = (
        "user-"
        f"{LUNA_USER}"
        f"-region-{region}"
        f"-sessid-{session_id}"
        f"-sesstime-{sess_time}"
    )

    full_url = (
        "http://"
        f"{proxy_user}"
        f":{LUNA_PASS}"
        f"@{LUNA_HOST}"
        f":{LUNA_PORT}"
    )

    return {
        "http": full_url,
        "https": full_url,
    }


def obter_proxy_novada(
    email_usuario_ignorado, region: str = "br"
) -> dict:
    """
    Tenta obter e testar um proxy Luna "premium", medindo a latência
    contra http://www.google.com/generate_204.

    - Faz até MAX_TENTATIVAS, tentando obter latência <= LIMITE_LATENCIA.
    - Se conseguir, loga em verde e retorna o dict de proxies.
    - Se só conseguir conexões lentas/instáveis, retorna o último proxy
      mesmo assim, com aviso.

    email_usuario_ignorado existe só por compat e não é usado aqui.
    """
    MAX_TENTATIVAS = 10
    LIMITE_LATENCIA = 2.5

    log_sistema(f"🔎 Gerando Proxy Premium (Meta: < {LIMITE_LATENCIA}s)...")

    proxies = None

    for i in range(MAX_TENTATIVAS):
        proxies = obter_credenciais_luna(region)

        try:
            parsed = urlparse(proxies["http"])

            ok, latencia = testar_conexao_direta(
                parsed.hostname,
                parsed.port,
                parsed.username,
                parsed.password,
            )

            if ok:
                if latencia <= LIMITE_LATENCIA:
                    log_sistema(
                        f"{Cores.VERDE}"
                        f"🚀 Proxy Premium Ativo! Latência: {latencia:.2f}s"
                        f"{Cores.RESET}"
                    )
                    return proxies
                else:
                    print(
                        f"   ♻️  Proxy lento ({latencia:.2f}s). "
                        "Buscando outro..."
                    )
            else:
                print("   ❌ Proxy instável. Tentando outro...")

        except Exception:
            # erro em um teste específico; tenta outro
            pass

        time.sleep(0.5)

    log_aviso("⚠️ Proxy Premium instável, mas seguindo.")
    return proxies


def testar_conexao_direta(
    host: str, port: int, user: str, password: str
) -> tuple[bool, float]:
    """
    Testa a conexão através de um proxy HTTP básico usando requests.

    Retorna:
        (True, latência_segundos)  em caso de sucesso
        (False, 99.0)              em caso de erro
    """
    proxy_url = (
        "http://"
        f"{user}:{password}@{host}:{port}"
    )
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }

    try:
        inicio = time.time()
        requests.get(
            "http://www.google.com/generate_204",
            proxies=proxies,
            timeout=5,
        )
        fim = time.time()
        return True, fim - inicio
    except Exception:
        return False, 99.0


# ──────────────────────────────────────────────────────────────────────
#  TÚNEL HTTP COM AUTENTICAÇÃO BASIC (CONNECT)
# ──────────────────────────────────────────────────────────────────────


class TunelAuth:
    """
    Pequeno túnel HTTP local que injeta cabeçalho
    `Proxy-Authorization: Basic ...` ao redirecionar o tráfego
    para um proxy remoto.

    Uso típico:
        t = TunelAuth(local_port=8888,
                      remote_host='host_proxy',
                      remote_port=12345,
                      user='usuario',
                      password='senha')
        print("Túnel em:", t.start())
        ...
        t.stop()
    """

    __firstlineno__ = 103
    __static_attributes__ = (
        "auth_b64",
        "local_host",
        "local_port",
        "remote_addr",
        "running",
        "server",
        "thread",
    )

    def __init__(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        user: str,
        password: str,
    ):
        self.local_host = "127.0.0.1"
        self.local_port = int(local_port)
        self.remote_addr = (remote_host, int(remote_port))

        auth_str = f"{user}:{password}"
        self.auth_b64 = base64.b64encode(
            auth_str.encode()
        ).decode()

        self.server = None
        self.running = False
        self.thread = None

    def start(self) -> str | None:
        """
        Inicia o servidor local e a thread de aceitação.

        Retorna "host:port" em caso de sucesso, ou None em caso de erro.
        """
        try:
            self.server = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            )
            self.server.bind((self.local_host, self.local_port))
            self.server.listen(50)

            self.running = True

            self.thread = threading.Thread(
                target=self._accept_loop,
                daemon=True,
            )
            self.thread.start()

            return f"{self.local_host}:{self.local_port}"

        except Exception as e:
            log_erro(
                f"Falha ao iniciar túnel na porta "
                f"{self.local_port}: {e}"
            )
            return None

    def stop(self):
        """Encerra o túnel e fecha o socket servidor."""
        self.running = False
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass

    def _accept_loop(self):
        """Loop de aceitação de conexões no servidor local."""
        if not self.running:
            return

        while self.running:
            try:
                client, addr = self.server.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client,),
                    daemon=True,
                ).start()
            except Exception:
                if self.running:
                    return
                return

    def _handle_client(self, client: socket.socket):
        """
        Recebe o primeiro request do cliente, injeta Proxy-Authorization
        e encaminha o tráfego entre cliente e remote.
        """
        remote = None

        try:
            request = client.recv(4096)
            if not request:
                client.close()
                if remote:
                    remote.close()
                return

            # Abre conexão com o proxy remoto
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.settimeout(15)
            remote.connect(self.remote_addr)

            # Encontra fim da primeira linha / cabeçalho
            first_line_end = request.find(b"\r\n")

            if first_line_end != -1:
                header = (
                    "Proxy-Authorization: Basic "
                    f"{self.auth_b64}\r\n"
                )
                new_request = (
                    request[: first_line_end + 2]
                    + header.encode()
                    + request[first_line_end + 2 :]
                )
            else:
                new_request = request

            # Envia requisição modificada ao proxy
            remote.sendall(new_request)

            sockets = [client, remote]

            # Loop de encaminhamento entre cliente e remote
            while True:
                r, _, _ = select.select(sockets, [], [], 15)
                if not r:
                    break

                for s in r:
                    data = s.recv(8192)
                    if not data:
                        client.close()
                        if remote:
                            remote.close()
                        return

                    if s is client:
                        remote.sendall(data)
                    else:
                        client.sendall(data)

        except Exception:
            try:
                client.close()
            except Exception:
                pass

            if remote:
                try:
                    remote.close()
                except Exception:
                    pass
            # re-raise silenciosamente? bytecode indica re-raise interno,
            # mas aqui encerramos a conexão.

        finally:
            try:
                client.close()
            except Exception:
                pass
            if remote:
                try:
                    remote.close()
                except Exception:
                    pass
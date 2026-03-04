# fabricador/modules/provider_dataimpulse.py

import random
import string


class ProviderDataImpulse:
    """
    Provider de proxy para o serviço DataImpulse.

    Gera um usuário de sessão baseado em login/password fixos
    e devolve o dict de proxies compatível com requests.
    """

    __firstlineno__ = 4
    __static_attributes__ = ("host", "login", "password", "port")

    def __init__(
        self,
        login: str,
        password: str,
        host: str = "gw.dataimpulse.com",
        port: str = "823",
    ):
        self.login = login
        self.password = password
        self.host = host
        self.port = port

    def get_proxy(self) -> dict:
        """
        Gera um proxy novo com session id aleatório.

        Retorna:
            {
                "http":  "http://<login>__cr.br__sid-<sess>@host:port",
                "https": "http://<login>__cr.br__sid-<sess>@host:port",
            }
        """
        # session_id: 8 caracteres [a-z0-9]
        session_id = "".join(
            random.choices(
                string.ascii_lowercase + string.digits,
                k=8,
            )
        )

        proxy_user = f"{self.login}__cr.br__sid-{session_id}"

        proxy_str = (
            "http://"
            f"{proxy_user}"
            f":{self.password}"
            f"@{self.host}"
            f":{self.port}"
        )

        return {
            "http": proxy_str,
            "https": proxy_str,
        }

    def obter_proxy_novada(
        self, usuario=None, region=None
    ) -> dict:
        """
        Mantida por compatibilidade com a interface de outros providers.
        Ignora `usuario` e `region` e apenas delega para get_proxy().
        """
        return self.get_proxy()
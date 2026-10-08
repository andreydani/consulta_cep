from __future__ import annotations

from .engine_cep import ConsultaCEP, Endereco, texto
from .util import TIMEOUT_PADRAO, consulta_cep_https


class ConsultaCEPBrasilAPI(ConsultaCEP):
    nome = "BrasilAPI"
    URL = "https://brasilapi.com.br/api/cep/v1/{cep}"

    def consultar_normalizado(
        self, cep: str, *, timeout: float = TIMEOUT_PADRAO
    ) -> Endereco:
        res = consulta_cep_https(self.URL, cep, timeout=timeout)
        return Endereco(
            servico=self.nome,
            bairro=texto(res, "neighborhood"),
            estado=str(res["state"]),
            logradouro=texto(res, "street"),
            cidade=str(res["city"]),
        )


class ConsultaCEPPostmon(ConsultaCEP):
    nome = "PostMon"
    URL = "http://api.postmon.com.br/v1/cep/{cep}"

    def consultar_normalizado(
        self, cep: str, *, timeout: float = TIMEOUT_PADRAO
    ) -> Endereco:
        res = consulta_cep_https(self.URL, cep, timeout=timeout)
        return Endereco(
            servico=self.nome,
            bairro=texto(res, "bairro"),
            estado=str(res["estado"]),
            logradouro=texto(res, "logradouro"),
            cidade=str(res["cidade"]),
        )


SERVICOS_CEP: list[ConsultaCEP] = [ConsultaCEPPostmon(), ConsultaCEPBrasilAPI()]

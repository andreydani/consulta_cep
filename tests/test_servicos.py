from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
import respx

from consulta_cep import (
    SERVICOS_PADRAO,
    CEPInvalidoError,
    CEPNaoEncontradoError,
    Endereco,
    servicos_disponiveis,
)
from consulta_cep.engine_cep import ConsultaCEP
from consulta_cep.servicos import (
    ConsultaCEPBrasilAPI,
    ConsultaCEPViaCEP,
    obter_servico,
    registrar_servico,
)
from consulta_cep.util import consulta_cep_https

from .dados import CEP, CEP_INEXISTENTE, fixture, resposta, simular, url

BASE: dict[str, Any] = {
    "estado": "SP",
    "cidade": "São Paulo",
    "bairro": "Sé",
    "logradouro": "Praça da Sé",
    "cep": "01001-000",
    "complemento": None,
    "ibge": None,
    "ddd": None,
    "latitude": None,
    "longitude": None,
}

ESPERADO_SUCESSO: dict[str, dict[str, Any]] = {
    "brasilapi": {**BASE, "latitude": -23.5502, "longitude": -46.6339},
    "viacep": {**BASE, "complemento": "lado ímpar", "ibge": "3550308", "ddd": "11"},
    "opencep": {**BASE, "complemento": "lado ímpar", "ibge": "3550308"},
    "awesomeapi": {
        **BASE,
        "ibge": "3550308",
        "ddd": "11",
        "latitude": -23.5502,
        "longitude": -46.6339,
    },
}

VAZIOS = {"bairro": None, "logradouro": None, "complemento": None, "ddd": None}
ESPERADO_VAZIOS: dict[str, dict[str, Any]] = {
    "brasilapi": {**BASE, **VAZIOS},
    "viacep": {**BASE, **VAZIOS, "ibge": "3550308"},
    "opencep": {**BASE, **VAZIOS},
    "awesomeapi": {**BASE, **VAZIOS, "ibge": "3550308"},
}

NAO_ENCONTRADO = [
    ("brasilapi", "nao_encontrado"),
    ("viacep", "nao_encontrado"),
    ("viacep", "nao_encontrado_bool"),
    ("opencep", "nao_encontrado"),
    ("awesomeapi", "nao_encontrado"),
]


def test_registro() -> None:
    assert servicos_disponiveis() == [
        "brasilapi",
        "viacep",
        "opencep",
        "awesomeapi",
    ]
    assert SERVICOS_PADRAO == ("brasilapi", "viacep", "opencep", "awesomeapi")
    assert tuple(servicos_disponiveis()) == SERVICOS_PADRAO


def test_postmon_foi_removido() -> None:
    # A API do Postmon foi desativada (o domínio não resolve mais).
    with pytest.raises(ValueError, match="postmon"):
        obter_servico("postmon")


def test_montar_url() -> None:
    assert (
        obter_servico("viacep").montar_url(CEP)
        == "https://viacep.com.br/ws/01001000/json/"
    )


def test_obter_servico() -> None:
    assert isinstance(obter_servico("brasilapi"), ConsultaCEPBrasilAPI)
    with pytest.raises(ValueError, match="Disponíveis"):
        obter_servico("correios")


def test_registrar_exige_nome_unico() -> None:
    class SemNome(ConsultaCEP):
        def converter(self, dados: dict[str, Any], cep: str) -> Endereco:
            raise NotImplementedError

    class Repetido(SemNome):
        nome = "viacep"

    with pytest.raises(ValueError, match="nome"):
        registrar_servico(SemNome)
    with pytest.raises(ValueError, match="Já existe"):
        registrar_servico(Repetido)
    assert servicos_disponiveis().count("viacep") == 1


# --- conversão (sem HTTP) -----------------------------------------------------


@pytest.mark.parametrize("nome", sorted(ESPERADO_SUCESSO))
def test_converter_sucesso(nome: str) -> None:
    endereco = obter_servico(nome).converter(fixture(nome, "sucesso")["body"], CEP)
    assert endereco == Endereco(servico=nome, **ESPERADO_SUCESSO[nome])


@pytest.mark.parametrize("nome", sorted(ESPERADO_VAZIOS))
def test_converter_campos_vazios(nome: str) -> None:
    endereco = obter_servico(nome).converter(fixture(nome, "vazios")["body"], CEP)
    assert endereco == Endereco(servico=nome, **ESPERADO_VAZIOS[nome])


# --- HTTP sync e async ----------------------------------------------------------


@pytest.mark.parametrize("nome", sorted(ESPERADO_SUCESSO))
def test_sucesso_sync(nome: str, api: respx.MockRouter) -> None:
    simular(api, nome, "sucesso")
    endereco = obter_servico(nome).consultar("01001-000")
    assert endereco == Endereco(servico=nome, **ESPERADO_SUCESSO[nome])


@pytest.mark.parametrize("nome", sorted(ESPERADO_SUCESSO))
def test_sucesso_async(nome: str, api: respx.MockRouter) -> None:
    simular(api, nome, "sucesso")
    endereco = asyncio.run(obter_servico(nome).consultar_async("01.001-000"))
    assert endereco == Endereco(servico=nome, **ESPERADO_SUCESSO[nome])


@pytest.mark.parametrize(("nome", "arquivo"), NAO_ENCONTRADO)
def test_nao_encontrado_sync(nome: str, arquivo: str, api: respx.MockRouter) -> None:
    simular(api, nome, arquivo, cep=CEP_INEXISTENTE)
    with pytest.raises(CEPNaoEncontradoError) as info:
        obter_servico(nome).consultar(CEP_INEXISTENTE)
    assert info.value.cep == CEP_INEXISTENTE


@pytest.mark.parametrize(("nome", "arquivo"), NAO_ENCONTRADO)
def test_nao_encontrado_async(nome: str, arquivo: str, api: respx.MockRouter) -> None:
    simular(api, nome, arquivo, cep=CEP_INEXISTENTE)
    with pytest.raises(CEPNaoEncontradoError):
        asyncio.run(obter_servico(nome).consultar_async(CEP_INEXISTENTE))


def test_todo_servico_tem_fixtures() -> None:
    for nome in servicos_disponiveis():
        assert fixture(nome, "sucesso")["status"] == 200
        assert fixture(nome, "vazios")["status"] == 200
        assert fixture(nome, "nao_encontrado")


def test_cep_da_resposta_ausente_usa_o_consultado() -> None:
    body = dict(fixture("viacep", "sucesso")["body"])
    del body["cep"]
    assert obter_servico("viacep").converter(body, CEP).cep == "01001-000"


def test_campo_obrigatorio_ausente_e_erro() -> None:
    with pytest.raises(KeyError):
        obter_servico("awesomeapi").converter({"state": "SP"}, CEP)


def test_erro_http_e_propagado(api: respx.MockRouter) -> None:
    api.get(url("brasilapi")).respond(503)
    with pytest.raises(httpx.HTTPStatusError):
        obter_servico("brasilapi").consultar(CEP)


@pytest.mark.parametrize("status", [201, 203])
def test_respostas_2xx_diferentes_de_200(status: int, api: respx.MockRouter) -> None:
    api.get(url("brasilapi")).respond(
        status, json=fixture("brasilapi", "sucesso")["body"]
    )
    assert obter_servico("brasilapi").consultar(CEP).cidade == "São Paulo"


def test_resposta_que_nao_e_objeto_json(api: respx.MockRouter) -> None:
    api.get(url("brasilapi")).respond(json=["inesperado"])
    with pytest.raises(ValueError):
        obter_servico("brasilapi").consultar(CEP)


def test_cep_invalido_nao_faz_requisicao(api: respx.MockRouter) -> None:
    with pytest.raises(CEPInvalidoError):
        obter_servico("viacep").consultar("123")
    with pytest.raises(CEPInvalidoError):
        asyncio.run(obter_servico("viacep").consultar_async("123"))
    assert not api.calls


@pytest.mark.parametrize("nome", servicos_disponiveis())
def test_timeout_e_repassado(nome: str) -> None:
    timeouts: list[dict[str, float | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeouts.append(request.extensions["timeout"])
        return resposta(nome, "sucesso")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        obter_servico(nome).consultar(CEP, timeout=1.5, client=client)
        obter_servico(nome).consultar(CEP, client=client)
    assert timeouts[0]["read"] == 1.5
    assert timeouts[1]["read"] == 5


def test_client_e_reaproveitado_sync() -> None:
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return resposta("viacep", "sucesso")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        obter_servico("viacep").consultar(CEP, client=client)
    assert urls == [url("viacep")]


def test_client_e_reaproveitado_async() -> None:
    urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return resposta("opencep", "sucesso")

    async def rodar() -> Endereco:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await obter_servico("opencep").consultar_async(CEP, client=c)

    assert asyncio.run(rodar()).servico == "opencep"
    assert urls == [url("opencep")]


def test_consulta_cep_https_compativel(api: respx.MockRouter) -> None:
    simular(api, "viacep", "sucesso")
    assert consulta_cep_https(ConsultaCEPViaCEP.URL, CEP)["uf"] == "SP"
    simular(api, "viacep", "nao_encontrado", cep=CEP_INEXISTENTE)
    dados = consulta_cep_https(ConsultaCEPViaCEP.URL, CEP_INEXISTENTE)
    assert dados == {"erro": "true"}

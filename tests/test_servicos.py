from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest import mock

import pytest
import requests
import responses

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
    ConsultaCEPPostmon,
    obter_servico,
    registrar_servico,
)

from .dados import CEP, CEP_INEXISTENTE, fixture, simular, url

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
    "postmon": {**BASE, "complemento": "lado ímpar", "ibge": "3550308"},
}

VAZIOS = {"bairro": None, "logradouro": None, "complemento": None, "ddd": None}
ESPERADO_VAZIOS: dict[str, dict[str, Any]] = {
    "brasilapi": {**BASE, **VAZIOS},
    "viacep": {**BASE, **VAZIOS, "ibge": "3550308"},
    "opencep": {**BASE, **VAZIOS},
    "awesomeapi": {**BASE, **VAZIOS, "ibge": "3550308"},
    "postmon": {**BASE, **VAZIOS},
}

NAO_ENCONTRADO = [
    ("brasilapi", "nao_encontrado"),
    ("viacep", "nao_encontrado"),
    ("viacep", "nao_encontrado_bool"),
    ("opencep", "nao_encontrado"),
    ("awesomeapi", "nao_encontrado"),
    ("postmon", "nao_encontrado"),
]


@pytest.fixture
def api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock() as rsps:
        yield rsps


def test_registro() -> None:
    assert servicos_disponiveis() == [
        "brasilapi",
        "viacep",
        "opencep",
        "awesomeapi",
        "postmon",
    ]
    assert SERVICOS_PADRAO == ("brasilapi", "viacep", "opencep", "awesomeapi")
    assert "postmon" not in SERVICOS_PADRAO


def test_postmon_usa_https() -> None:
    assert ConsultaCEPPostmon.URL.startswith("https://")


def test_obter_servico() -> None:
    assert isinstance(obter_servico("brasilapi"), ConsultaCEPBrasilAPI)
    with pytest.raises(ValueError, match="Disponíveis"):
        obter_servico("correios")


def test_registrar_exige_nome_unico() -> None:
    class SemNome(ConsultaCEP):
        def consultar_normalizado(self, cep: str, *, timeout: float = 5) -> Endereco:
            raise NotImplementedError

    class Repetido(SemNome):
        nome = "viacep"

    with pytest.raises(ValueError, match="nome"):
        registrar_servico(SemNome)
    with pytest.raises(ValueError, match="Já existe"):
        registrar_servico(Repetido)
    assert servicos_disponiveis().count("viacep") == 1


@pytest.mark.parametrize("nome", sorted(ESPERADO_SUCESSO))
def test_mapeamento_sucesso(nome: str, api: responses.RequestsMock) -> None:
    simular(api, nome, "sucesso")
    endereco = obter_servico(nome).consultar("01001-000")
    assert endereco == Endereco(servico=nome, **ESPERADO_SUCESSO[nome])


@pytest.mark.parametrize("nome", sorted(ESPERADO_VAZIOS))
def test_mapeamento_campos_vazios(nome: str, api: responses.RequestsMock) -> None:
    simular(api, nome, "vazios")
    endereco = obter_servico(nome).consultar(CEP)
    assert endereco == Endereco(servico=nome, **ESPERADO_VAZIOS[nome])


@pytest.mark.parametrize(("nome", "arquivo"), NAO_ENCONTRADO)
def test_nao_encontrado(nome: str, arquivo: str, api: responses.RequestsMock) -> None:
    simular(api, nome, arquivo, cep=CEP_INEXISTENTE)
    with pytest.raises(CEPNaoEncontradoError) as info:
        obter_servico(nome).consultar(CEP_INEXISTENTE)
    assert info.value.cep == CEP_INEXISTENTE


def test_todo_servico_tem_fixtures() -> None:
    for nome in servicos_disponiveis():
        assert fixture(nome, "sucesso")["status"] == 200
        assert fixture(nome, "vazios")["status"] == 200
        assert fixture(nome, "nao_encontrado")


def test_cep_da_resposta_ausente_usa_o_consultado(api: responses.RequestsMock) -> None:
    body = dict(fixture("viacep", "sucesso")["body"])
    del body["cep"]
    api.get(url("viacep"), json=body)
    assert obter_servico("viacep").consultar(CEP).cep == "01001-000"


def test_campo_obrigatorio_ausente_e_erro(api: responses.RequestsMock) -> None:
    api.get(url("awesomeapi"), json={"state": "SP"})
    with pytest.raises(KeyError):
        obter_servico("awesomeapi").consultar(CEP)


def test_erro_http_e_propagado(api: responses.RequestsMock) -> None:
    api.get(url("brasilapi"), status=503)
    with pytest.raises(requests.HTTPError):
        obter_servico("brasilapi").consultar(CEP)


@pytest.mark.parametrize("status", [201, 203])
def test_respostas_2xx_diferentes_de_200(
    status: int, api: responses.RequestsMock
) -> None:
    api.get(
        url("brasilapi"), status=status, json=fixture("brasilapi", "sucesso")["body"]
    )
    assert obter_servico("brasilapi").consultar(CEP).cidade == "São Paulo"


def test_resposta_que_nao_e_objeto_json(api: responses.RequestsMock) -> None:
    api.get(url("brasilapi"), json=["inesperado"])
    with pytest.raises(ValueError):
        obter_servico("brasilapi").consultar(CEP)


def test_cep_invalido_nao_faz_requisicao() -> None:
    with (
        mock.patch("requests.get") as get,
        pytest.raises(CEPInvalidoError),
    ):
        obter_servico("viacep").consultar("123")
    get.assert_not_called()


@pytest.mark.parametrize("nome", servicos_disponiveis())
def test_timeout_e_repassado_ao_requests(nome: str) -> None:
    resposta = mock.Mock(status_code=200)
    resposta.json.return_value = fixture(nome, "sucesso")["body"]
    with mock.patch("requests.get", return_value=resposta) as get:
        obter_servico(nome).consultar(CEP, timeout=1.5)
    get.assert_called_once_with(url(nome), timeout=1.5)


def test_timeout_padrao_e_5_segundos() -> None:
    resposta = mock.Mock(status_code=200)
    resposta.json.return_value = fixture("viacep", "sucesso")["body"]
    with mock.patch("requests.get", return_value=resposta) as get:
        obter_servico("viacep").consultar(CEP)
    assert get.call_args.kwargs["timeout"] == 5

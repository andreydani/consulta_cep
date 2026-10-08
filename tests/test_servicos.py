from __future__ import annotations

import json
from unittest import mock

import pytest
import requests
import responses

from consulta_cep import CEPInvalidoError, CEPNaoEncontradoError, Endereco
from consulta_cep.servicos import ConsultaCEPBrasilAPI, ConsultaCEPPostmon

from .dados import CEP, RESPOSTA_BRASILAPI, RESPOSTA_POSTMON

URL_BRASILAPI = ConsultaCEPBrasilAPI.URL.format(cep=CEP)
URL_POSTMON = ConsultaCEPPostmon.URL.format(cep=CEP)

ESPERADO = {
    "estado": "SP",
    "cidade": "São Paulo",
    "bairro": "Sé",
    "logradouro": "Praça da Sé",
}


@responses.activate
def test_brasilapi_sucesso() -> None:
    responses.get(URL_BRASILAPI, json=RESPOSTA_BRASILAPI)
    endereco = ConsultaCEPBrasilAPI().consultar("01001-000")
    assert endereco == Endereco(servico="BrasilAPI", **ESPERADO)


@responses.activate
def test_postmon_sucesso() -> None:
    responses.get(URL_POSTMON, json=RESPOSTA_POSTMON)
    endereco = ConsultaCEPPostmon().consultar("01.001-000")
    assert endereco == Endereco(servico="PostMon", **ESPERADO)


@responses.activate
def test_campos_opcionais_ausentes_viram_texto_vazio() -> None:
    responses.get(URL_POSTMON, json={"estado": "SP", "cidade": "São Paulo"})
    responses.get(
        URL_BRASILAPI,
        json={"state": "SP", "city": "São Paulo", "street": None},
    )
    for servico in (ConsultaCEPPostmon(), ConsultaCEPBrasilAPI()):
        endereco = servico.consultar(CEP)
        assert (endereco.bairro, endereco.logradouro) == ("", "")


@responses.activate
@pytest.mark.parametrize("classe", [ConsultaCEPBrasilAPI, ConsultaCEPPostmon])
def test_404_e_cep_nao_encontrado(
    classe: type[ConsultaCEPBrasilAPI | ConsultaCEPPostmon],
) -> None:
    responses.get(classe.URL.format(cep=CEP), status=404, json={})
    with pytest.raises(CEPNaoEncontradoError):
        classe().consultar(CEP)


@responses.activate
def test_erro_http_e_propagado() -> None:
    responses.get(URL_BRASILAPI, status=503)
    with pytest.raises(requests.HTTPError):
        ConsultaCEPBrasilAPI().consultar(CEP)


@responses.activate
@pytest.mark.parametrize("status", [201, 203])
def test_respostas_2xx_diferentes_de_200(status: int) -> None:
    responses.get(URL_BRASILAPI, status=status, json=RESPOSTA_BRASILAPI)
    assert ConsultaCEPBrasilAPI().consultar(CEP).cidade == "São Paulo"


@responses.activate
def test_resposta_que_nao_e_objeto_json() -> None:
    responses.get(URL_BRASILAPI, json=["inesperado"])
    with pytest.raises(ValueError):
        ConsultaCEPBrasilAPI().consultar(CEP)


def test_cep_invalido_nao_faz_requisicao() -> None:
    with (
        mock.patch("requests.get") as get,
        pytest.raises(CEPInvalidoError),
    ):
        ConsultaCEPBrasilAPI().consultar("123")
    get.assert_not_called()


def test_timeout_e_repassado_ao_requests() -> None:
    resposta = mock.Mock(status_code=200)
    resposta.json.return_value = RESPOSTA_BRASILAPI
    with mock.patch("requests.get", return_value=resposta) as get:
        ConsultaCEPBrasilAPI().consultar(CEP, timeout=1.5)
    get.assert_called_once_with(URL_BRASILAPI, timeout=1.5)


def test_timeout_padrao_e_5_segundos() -> None:
    resposta = mock.Mock(status_code=200)
    resposta.json.return_value = RESPOSTA_POSTMON
    with mock.patch("requests.get", return_value=resposta) as get:
        ConsultaCEPPostmon().consultar(CEP)
    assert get.call_args.kwargs["timeout"] == 5


def test_str_do_endereco_preserva_acentos() -> None:
    endereco = Endereco(servico="BrasilAPI", **ESPERADO)
    texto = str(endereco)
    assert "São Paulo" in texto
    assert "Praça da Sé" in texto
    assert json.loads(texto) == {"servico": "BrasilAPI", **ESPERADO}

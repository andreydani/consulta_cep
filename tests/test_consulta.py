from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from unittest import mock

import pytest
import requests
import responses

import consulta_cep as pacote
from consulta_cep import (
    CEPInvalidoError,
    CEPNaoEncontradoError,
    Endereco,
    ServicosIndisponiveisError,
    consulta_cep,
)
from consulta_cep.servicos import ConsultaCEPBrasilAPI, ConsultaCEPPostmon

from .dados import CEP, RESPOSTA_BRASILAPI, RESPOSTA_POSTMON

URL_BRASILAPI = ConsultaCEPBrasilAPI.URL.format(cep=CEP)
URL_POSTMON = ConsultaCEPPostmon.URL.format(cep=CEP)


@pytest.fixture
def api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


def test_sucesso_brasilapi(api: responses.RequestsMock) -> None:
    api.get(URL_BRASILAPI, json=RESPOSTA_BRASILAPI)
    api.get(URL_POSTMON, status=500)
    endereco = consulta_cep("01001-000")
    assert isinstance(endereco, Endereco)
    assert endereco.servico == "BrasilAPI"
    assert endereco.cidade == "São Paulo"


def test_sucesso_postmon(api: responses.RequestsMock) -> None:
    api.get(URL_POSTMON, json=RESPOSTA_POSTMON)
    api.get(URL_BRASILAPI, body=requests.ConnectionError("fora do ar"))
    endereco = consulta_cep(" 01.001-000 ")
    assert endereco.servico == "PostMon"
    assert endereco.logradouro == "Praça da Sé"


def test_cep_invalido_nao_dispara_consultas() -> None:
    with (
        mock.patch("requests.get") as get,
        pytest.raises(CEPInvalidoError),
    ):
        consulta_cep("1234")
    get.assert_not_called()


def test_cep_invalido_continua_sendo_value_error() -> None:
    with pytest.raises(ValueError):
        consulta_cep("abc")


def test_nao_encontrado_em_todos(api: responses.RequestsMock) -> None:
    api.get(URL_BRASILAPI, status=404, json={})
    api.get(URL_POSTMON, status=404)
    with pytest.raises(CEPNaoEncontradoError) as info:
        consulta_cep("01001-000")
    assert info.value.cep == CEP


def test_nao_encontrado_em_um_e_falha_no_outro(api: responses.RequestsMock) -> None:
    api.get(URL_BRASILAPI, status=404, json={})
    api.get(URL_POSTMON, status=503)
    with pytest.raises(CEPNaoEncontradoError):
        consulta_cep(CEP)


def test_nao_encontrado_em_um_mas_outro_devolve(
    api: responses.RequestsMock,
) -> None:
    api.get(URL_BRASILAPI, status=404, json={})
    api.get(URL_POSTMON, json=RESPOSTA_POSTMON)
    assert consulta_cep(CEP).servico == "PostMon"


def test_todos_falhando(
    api: responses.RequestsMock, caplog: pytest.LogCaptureFixture
) -> None:
    api.get(URL_BRASILAPI, status=500)
    api.get(URL_POSTMON, body=requests.ConnectionError("recusada"))
    with (
        caplog.at_level(logging.WARNING, logger="consulta_cep"),
        pytest.raises(ServicosIndisponiveisError) as info,
    ):
        consulta_cep(CEP)
    erros = info.value.erros
    assert set(erros) == {"BrasilAPI", "PostMon"}
    assert isinstance(erros["BrasilAPI"], requests.HTTPError)
    assert isinstance(erros["PostMon"], requests.ConnectionError)
    assert {r.name for r in caplog.records} == {"consulta_cep"}
    assert len(caplog.records) == 2


def test_timeout_em_todos(api: responses.RequestsMock) -> None:
    api.get(URL_BRASILAPI, body=requests.ReadTimeout("lento"))
    api.get(URL_POSTMON, body=requests.ConnectTimeout("lento"))
    with pytest.raises(ServicosIndisponiveisError) as info:
        consulta_cep(CEP, timeout=0.1)
    assert all(isinstance(e, requests.Timeout) for e in info.value.erros.values())


def test_timeout_e_repassado_a_todos_os_servicos() -> None:
    with (
        mock.patch("requests.get", return_value=mock.Mock(status_code=404)) as get,
        pytest.raises(CEPNaoEncontradoError),
    ):
        consulta_cep(CEP, timeout=2.5)
    assert get.call_count == 2
    assert {c.kwargs["timeout"] for c in get.call_args_list} == {2.5}


def test_timeout_e_keyword_only() -> None:
    with pytest.raises(TypeError):
        consulta_cep(CEP, 3)  # type: ignore[call-arg]


def test_nao_espera_servico_lento(api: responses.RequestsMock) -> None:
    liberar = threading.Event()

    def lento(request: requests.PreparedRequest) -> tuple[int, dict[str, str], str]:
        liberar.wait(timeout=10)
        return (500, {}, "")

    api.add_callback(responses.GET, URL_POSTMON, callback=lento)
    api.get(URL_BRASILAPI, json=RESPOSTA_BRASILAPI)
    try:
        inicio = time.monotonic()
        endereco = consulta_cep(CEP)
        duracao = time.monotonic() - inicio
    finally:
        liberar.set()
    assert endereco.servico == "BrasilAPI"
    assert duracao < 2


def test_sem_servicos_configurados() -> None:
    with (
        mock.patch.object(pacote, "SERVICOS_CEP", []),
        pytest.raises(ServicosIndisponiveisError) as info,
    ):
        consulta_cep(CEP)
    assert info.value.erros == {}


def test_versao() -> None:
    assert pacote.__version__ == "1.0.0.dev0"

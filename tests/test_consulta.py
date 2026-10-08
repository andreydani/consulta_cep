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
    SERVICOS_PADRAO,
    CEPInvalidoError,
    CEPNaoEncontradoError,
    ConsultaCEP,
    Endereco,
    ServicosIndisponiveisError,
    consulta_cep,
)
from consulta_cep import servicos as modulo_servicos

from .dados import CEP, simular, url


class Falso(ConsultaCEP):
    """Serviço simulado que registra as chamadas."""

    def __init__(
        self,
        nome: str,
        erro: Exception | None = None,
        espera: threading.Event | None = None,
    ) -> None:
        self.nome = nome
        self.erro = erro
        self.espera = espera
        self.chamadas: list[tuple[str, float]] = []

    def consultar_normalizado(self, cep: str, *, timeout: float = 5) -> Endereco:
        self.chamadas.append((cep, timeout))
        if self.espera is not None:
            self.espera.wait(timeout=10)
        if self.erro is not None:
            raise self.erro
        return Endereco(self.nome, "SP", "São Paulo", "Sé", "Praça da Sé", cep=cep)


@pytest.fixture
def api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


# --- lista padrão, com HTTP simulado -------------------------------------


@pytest.mark.parametrize("vencedor", SERVICOS_PADRAO)
def test_sucesso_de_cada_servico_padrao(
    vencedor: str, api: responses.RequestsMock
) -> None:
    for nome in SERVICOS_PADRAO:
        if nome == vencedor:
            simular(api, nome, "sucesso")
        else:
            api.get(url(nome), status=500)
    endereco = consulta_cep(" 01.001-000 ")
    assert endereco.servico == vencedor
    assert endereco.cidade == "São Paulo"
    assert endereco.cep == "01001-000"


def test_lista_padrao_nao_consulta_postmon(api: responses.RequestsMock) -> None:
    for nome in SERVICOS_PADRAO:
        api.get(url(nome), status=500)
    with pytest.raises(ServicosIndisponiveisError) as info:
        consulta_cep(CEP)
    assert set(info.value.erros) == set(SERVICOS_PADRAO)
    assert all("postmon" not in c.request.url for c in api.calls)  # type: ignore[operator]


def test_nao_encontrado_em_todos(api: responses.RequestsMock) -> None:
    for nome in SERVICOS_PADRAO:
        simular(api, nome, "nao_encontrado")
    with pytest.raises(CEPNaoEncontradoError) as info:
        consulta_cep("01001-000")
    assert info.value.cep == CEP


def test_todos_falhando(
    api: responses.RequestsMock, caplog: pytest.LogCaptureFixture
) -> None:
    api.get(url("brasilapi"), status=500)
    api.get(url("viacep"), body=requests.ConnectionError("recusada"))
    api.get(url("opencep"), body=requests.ReadTimeout("lento"))
    api.get(url("awesomeapi"), json={"inesperado": True})
    with (
        caplog.at_level(logging.WARNING, logger="consulta_cep"),
        pytest.raises(ServicosIndisponiveisError) as info,
    ):
        consulta_cep(CEP)
    erros = info.value.erros
    assert isinstance(erros["brasilapi"], requests.HTTPError)
    assert isinstance(erros["viacep"], requests.ConnectionError)
    assert isinstance(erros["opencep"], requests.Timeout)
    assert isinstance(erros["awesomeapi"], KeyError)
    assert {r.name for r in caplog.records} == {"consulta_cep"}
    assert len(caplog.records) == 4


# --- parâmetros -------------------------------------------------------------


def test_cep_invalido_nao_dispara_consultas() -> None:
    falso = Falso("a")
    with pytest.raises(CEPInvalidoError):
        consulta_cep("1234", servicos=[falso])
    with pytest.raises(ValueError):
        consulta_cep("abc", servicos=[falso])
    assert falso.chamadas == []


def test_servicos_por_nome(api: responses.RequestsMock) -> None:
    simular(api, "postmon", "sucesso")
    assert consulta_cep(CEP, servicos=["postmon"]).servico == "postmon"
    assert consulta_cep(CEP, servicos="postmon").servico == "postmon"


def test_servicos_mistura_nomes_e_instancias(api: responses.RequestsMock) -> None:
    simular(api, "viacep", "nao_encontrado")
    falso = Falso("falso")
    endereco = consulta_cep(CEP, servicos=["viacep", falso], estrategia="sequencial")
    assert endereco.servico == "falso"


def test_servico_unico_como_instancia() -> None:
    assert consulta_cep(CEP, servicos=Falso("x")).servico == "x"


@pytest.mark.parametrize("servicos", [[], ["correios"]])
def test_servicos_invalidos(servicos: list[str]) -> None:
    with pytest.raises(ValueError):
        consulta_cep(CEP, servicos=servicos)


def test_servico_de_tipo_errado() -> None:
    with pytest.raises(TypeError):
        consulta_cep(CEP, servicos=[object()])  # type: ignore[list-item]


def test_estrategia_invalida() -> None:
    with pytest.raises(ValueError, match="Estratégia"):
        consulta_cep(CEP, estrategia="aleatoria")  # type: ignore[arg-type]


def test_parametros_sao_keyword_only() -> None:
    with pytest.raises(TypeError):
        consulta_cep(CEP, 3)  # type: ignore[call-arg]


@pytest.mark.parametrize("estrategia", ["concorrente", "sequencial"])
def test_timeout_e_repassado(estrategia: pacote.Estrategia) -> None:
    falsos = [Falso("a", erro=RuntimeError()), Falso("b")]
    consulta_cep(CEP, timeout=2.5, servicos=falsos, estrategia=estrategia)
    for falso in falsos:
        assert falso.chamadas == [(CEP, 2.5)]


def test_timeout_padrao_repassado_ao_requests() -> None:
    with (
        mock.patch("requests.get", return_value=mock.Mock(status_code=404)) as get,
        pytest.raises(CEPNaoEncontradoError),
    ):
        consulta_cep(CEP)
    assert get.call_count == len(SERVICOS_PADRAO)
    assert {c.kwargs["timeout"] for c in get.call_args_list} == {5}


# --- estratégias ------------------------------------------------------------


def test_sequencial_para_no_primeiro_sucesso() -> None:
    a = Falso("a", erro=RuntimeError("fora"))
    b = Falso("b")
    c = Falso("c")
    endereco = consulta_cep(CEP, servicos=[a, b, c], estrategia="sequencial")
    assert endereco.servico == "b"
    assert len(a.chamadas) == len(b.chamadas) == 1
    assert c.chamadas == []


def test_sequencial_respeita_a_ordem() -> None:
    a, b = Falso("a"), Falso("b")
    assert consulta_cep(CEP, servicos=[b, a], estrategia="sequencial").servico == "b"
    assert a.chamadas == []


def test_sequencial_nao_encontrado() -> None:
    falsos = [Falso("a", erro=CEPNaoEncontradoError(CEP)), Falso("b", erro=OSError())]
    with pytest.raises(CEPNaoEncontradoError):
        consulta_cep(CEP, servicos=falsos, estrategia="sequencial")
    assert all(len(f.chamadas) == 1 for f in falsos)


def test_sequencial_todos_falhando() -> None:
    falsos = [Falso("a", erro=OSError("x")), Falso("b", erro=ValueError("y"))]
    with pytest.raises(ServicosIndisponiveisError) as info:
        consulta_cep(CEP, servicos=falsos, estrategia="sequencial")
    assert list(info.value.erros) == ["a", "b"]


def test_concorrente_consulta_todos() -> None:
    falsos = [Falso("a", erro=OSError()), Falso("b", erro=OSError()), Falso("c")]
    assert consulta_cep(CEP, servicos=falsos).servico == "c"
    assert all(len(f.chamadas) == 1 for f in falsos)


def test_concorrente_nao_encontrado_em_um_e_falha_no_outro() -> None:
    falsos = [Falso("a", erro=CEPNaoEncontradoError(CEP)), Falso("b", erro=OSError())]
    with pytest.raises(CEPNaoEncontradoError):
        consulta_cep(CEP, servicos=falsos)


def test_concorrente_nao_espera_servico_lento() -> None:
    liberar = threading.Event()
    lento = Falso("lento", espera=liberar)
    try:
        inicio = time.monotonic()
        endereco = consulta_cep(CEP, servicos=[lento, Falso("rapido")])
        duracao = time.monotonic() - inicio
    finally:
        liberar.set()
    assert endereco.servico == "rapido"
    assert duracao < 2


def test_concorrente_nao_espera_servico_lento_http(
    api: responses.RequestsMock,
) -> None:
    liberar = threading.Event()

    def lento(request: requests.PreparedRequest) -> tuple[int, dict[str, str], str]:
        liberar.wait(timeout=10)
        return (500, {}, "")

    api.add_callback(responses.GET, url("viacep"), callback=lento)
    simular(api, "brasilapi", "sucesso")
    try:
        inicio = time.monotonic()
        endereco = consulta_cep(CEP, servicos=["viacep", "brasilapi"])
        duracao = time.monotonic() - inicio
    finally:
        liberar.set()
    assert endereco.servico == "brasilapi"
    assert duracao < 2


def test_lista_padrao_vazia() -> None:
    with (
        mock.patch.object(modulo_servicos, "SERVICOS_CEP", []),
        pytest.raises(ServicosIndisponiveisError) as info,
    ):
        consulta_cep(CEP)
    assert info.value.erros == {}


def test_versao() -> None:
    assert pacote.__version__ == "1.0.0.dev0"

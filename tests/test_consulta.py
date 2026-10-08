from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from typing import Any
from unittest import mock

import httpx
import pytest
import respx

import consulta_cep as pacote
from consulta_cep import (
    SERVICOS_PADRAO,
    CEPInvalidoError,
    CEPNaoEncontradoError,
    Endereco,
    Estrategia,
    ServicosIndisponiveisError,
    consulta_cep,
    consulta_cep_async,
)
from consulta_cep import servicos as modulo_servicos

from .dados import CEP, resposta, simular, url
from .falsos import Falso

Consulta = Callable[..., Endereco]


def _async(cep: str, **kwargs: Any) -> Endereco:
    return asyncio.run(consulta_cep_async(cep, **kwargs))


@pytest.fixture(params=["sync", "async"])
def consultar(request: pytest.FixtureRequest) -> Consulta:
    """Roda o mesmo teste com consulta_cep e consulta_cep_async."""
    return consulta_cep if request.param == "sync" else _async


# --- lista padrão, com HTTP simulado -------------------------------------


@pytest.mark.parametrize("vencedor", SERVICOS_PADRAO)
def test_sucesso_de_cada_servico_padrao(
    vencedor: str, consultar: Consulta, api: respx.MockRouter
) -> None:
    for nome in SERVICOS_PADRAO:
        if nome == vencedor:
            simular(api, nome, "sucesso")
        else:
            api.get(url(nome)).respond(500)
    endereco = consultar(" 01.001-000 ")
    assert endereco.servico == vencedor
    assert endereco.cep == "01001-000"


def test_lista_padrao_nao_consulta_postmon(
    consultar: Consulta, api: respx.MockRouter
) -> None:
    for nome in SERVICOS_PADRAO:
        api.get(url(nome)).respond(500)
    with pytest.raises(ServicosIndisponiveisError) as info:
        consultar(CEP)
    assert set(info.value.erros) == set(SERVICOS_PADRAO)
    assert all("postmon" not in str(c.request.url) for c in api.calls)


def test_nao_encontrado_em_todos(consultar: Consulta, api: respx.MockRouter) -> None:
    for nome in SERVICOS_PADRAO:
        simular(api, nome, "nao_encontrado")
    with pytest.raises(CEPNaoEncontradoError) as info:
        consultar("01001-000")
    assert info.value.cep == CEP


def test_todos_falhando(
    consultar: Consulta, api: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    api.get(url("brasilapi")).respond(500)
    api.get(url("viacep")).mock(side_effect=httpx.ConnectError("recusada"))
    api.get(url("opencep")).mock(side_effect=httpx.ReadTimeout("lento"))
    api.get(url("awesomeapi")).respond(json={"inesperado": True})
    with (
        caplog.at_level(logging.WARNING, logger="consulta_cep"),
        pytest.raises(ServicosIndisponiveisError) as info,
    ):
        consultar(CEP)
    erros = info.value.erros
    assert isinstance(erros["brasilapi"], httpx.HTTPStatusError)
    assert isinstance(erros["viacep"], httpx.ConnectError)
    assert isinstance(erros["opencep"], httpx.TimeoutException)
    assert isinstance(erros["awesomeapi"], KeyError)
    assert {r.name for r in caplog.records} == {"consulta_cep"}
    assert len(caplog.records) == 4


# --- parâmetros -------------------------------------------------------------


def test_cep_invalido_nao_dispara_consultas(consultar: Consulta) -> None:
    falso = Falso("a")
    with pytest.raises(CEPInvalidoError):
        consultar("1234", servicos=[falso])
    with pytest.raises(ValueError):
        consultar("abc", servicos=[falso])
    assert falso.chamadas == []


def test_servicos_por_nome(consultar: Consulta, api: respx.MockRouter) -> None:
    simular(api, "postmon", "sucesso")
    assert consultar(CEP, servicos=["postmon"]).servico == "postmon"
    assert consultar(CEP, servicos="postmon").servico == "postmon"


def test_servicos_mistura_nomes_e_instancias(
    consultar: Consulta, api: respx.MockRouter
) -> None:
    simular(api, "viacep", "nao_encontrado")
    endereco = consultar(CEP, servicos=["viacep", Falso("f")], estrategia="sequencial")
    assert endereco.servico == "f"


def test_servico_unico_como_instancia(consultar: Consulta) -> None:
    assert consultar(CEP, servicos=Falso("x")).servico == "x"


@pytest.mark.parametrize("servicos", [[], ["correios"]])
def test_servicos_invalidos(consultar: Consulta, servicos: list[str]) -> None:
    with pytest.raises(ValueError):
        consultar(CEP, servicos=servicos)


def test_servico_de_tipo_errado(consultar: Consulta) -> None:
    with pytest.raises(TypeError):
        consultar(CEP, servicos=[object()])


def test_estrategia_invalida(consultar: Consulta) -> None:
    with pytest.raises(ValueError, match="Estratégia"):
        consultar(CEP, estrategia="aleatoria")


def test_parametros_sao_keyword_only() -> None:
    with pytest.raises(TypeError):
        consulta_cep(CEP, 3)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        consulta_cep_async(CEP, 3)  # type: ignore[call-arg, unused-coroutine]


@pytest.mark.parametrize("estrategia", ["concorrente", "sequencial"])
def test_timeout_e_repassado(consultar: Consulta, estrategia: str) -> None:
    falsos = [Falso("a", erro=RuntimeError()), Falso("b")]
    consultar(CEP, timeout=2.5, servicos=falsos, estrategia=estrategia)
    for falso in falsos:
        assert falso.chamadas == [(CEP, 2.5)]


def test_timeout_padrao_chega_ao_httpx(
    consultar: Consulta, api: respx.MockRouter
) -> None:
    rota = api.get(url("viacep")).mock(return_value=resposta("viacep", "sucesso"))
    consultar(CEP, servicos=["viacep"])
    assert rota.calls.last.request.extensions["timeout"]["read"] == 5


# --- client -----------------------------------------------------------------


@pytest.mark.parametrize("estrategia", ["concorrente", "sequencial"])
def test_client_sync_e_repassado(estrategia: Estrategia) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return resposta("viacep", "sucesso")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        endereco = consulta_cep(
            CEP, servicos=["viacep"], client=client, estrategia=estrategia
        )
        assert not client.is_closed
    assert endereco.servico == "viacep"


@pytest.mark.parametrize("estrategia", ["concorrente", "sequencial"])
def test_client_async_e_repassado_e_nao_e_fechado(estrategia: Estrategia) -> None:
    falso = Falso("f")

    async def rodar() -> None:
        async with httpx.AsyncClient() as client:
            await consulta_cep_async(
                CEP, servicos=[falso], client=client, estrategia=estrategia
            )
            assert falso.clientes == [client]
            assert not client.is_closed

    asyncio.run(rodar())


def test_async_sem_client_usa_um_temporario_compartilhado() -> None:
    falsos = [Falso("a", erro=OSError()), Falso("b")]
    asyncio.run(consulta_cep_async(CEP, servicos=falsos))
    primeiro, segundo = (f.clientes[0] for f in falsos)
    assert isinstance(primeiro, httpx.AsyncClient)
    assert primeiro is segundo
    assert primeiro.is_closed


# --- estratégias ------------------------------------------------------------


def test_sequencial_para_no_primeiro_sucesso(consultar: Consulta) -> None:
    a, b, c = Falso("a", erro=RuntimeError("fora")), Falso("b"), Falso("c")
    endereco = consultar(CEP, servicos=[a, b, c], estrategia="sequencial")
    assert endereco.servico == "b"
    assert len(a.chamadas) == len(b.chamadas) == 1
    assert c.chamadas == []


def test_sequencial_respeita_a_ordem(consultar: Consulta) -> None:
    a, b = Falso("a"), Falso("b")
    assert consultar(CEP, servicos=[b, a], estrategia="sequencial").servico == "b"
    assert a.chamadas == []


def test_sequencial_nao_encontrado(consultar: Consulta) -> None:
    falsos = [Falso("a", erro=CEPNaoEncontradoError(CEP)), Falso("b", erro=OSError())]
    with pytest.raises(CEPNaoEncontradoError):
        consultar(CEP, servicos=falsos, estrategia="sequencial")
    assert all(len(f.chamadas) == 1 for f in falsos)


def test_sequencial_todos_falhando(consultar: Consulta) -> None:
    falsos = [Falso("a", erro=OSError("x")), Falso("b", erro=ValueError("y"))]
    with pytest.raises(ServicosIndisponiveisError) as info:
        consultar(CEP, servicos=falsos, estrategia="sequencial")
    assert list(info.value.erros) == ["a", "b"]


def test_concorrente_consulta_todos(consultar: Consulta) -> None:
    falsos = [Falso("a", erro=OSError()), Falso("b", erro=OSError()), Falso("c")]
    assert consultar(CEP, servicos=falsos).servico == "c"
    assert all(len(f.chamadas) == 1 for f in falsos)


def test_concorrente_nao_encontrado_em_um_e_falha_no_outro(
    consultar: Consulta,
) -> None:
    falsos = [Falso("a", erro=CEPNaoEncontradoError(CEP)), Falso("b", erro=OSError())]
    with pytest.raises(CEPNaoEncontradoError):
        consultar(CEP, servicos=falsos)


def test_sync_concorrente_nao_espera_servico_lento() -> None:
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


def test_sync_concorrente_nao_espera_servico_lento_http() -> None:
    liberar = threading.Event()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "viacep.com.br":
            liberar.wait(timeout=10)
            return httpx.Response(500)
        return resposta("brasilapi", "sucesso")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        try:
            inicio = time.monotonic()
            endereco = consulta_cep(
                CEP, servicos=["viacep", "brasilapi"], client=client
            )
            duracao = time.monotonic() - inicio
        finally:
            liberar.set()
    assert endereco.servico == "brasilapi"
    assert duracao < 2


def test_async_concorrente_cancela_tarefas_lentas() -> None:
    lentos = [Falso("lento1", travar=True), Falso("lento2", travar=True)]

    async def rodar() -> tuple[Endereco, list[asyncio.Task[Any]]]:
        endereco = await asyncio.wait_for(
            consulta_cep_async(CEP, servicos=[*lentos, Falso("rapido")]), timeout=2
        )
        restantes = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        return endereco, restantes

    endereco, restantes = asyncio.run(rodar())
    assert endereco.servico == "rapido"
    assert all(lento.cancelado for lento in lentos)
    assert restantes == []


def test_async_concorrente_cancela_requisicoes_lentas_http() -> None:
    canceladas: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "viacep.com.br":
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                canceladas.append(request.url.host)
                raise
        return resposta("awesomeapi", "sucesso")

    async def rodar() -> Endereco:
        transporte = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transporte) as client:
            return await consulta_cep_async(
                CEP, servicos=["viacep", "awesomeapi"], client=client
            )

    inicio = time.monotonic()
    endereco = asyncio.run(rodar())
    assert time.monotonic() - inicio < 2
    assert endereco.servico == "awesomeapi"
    assert canceladas == ["viacep.com.br"]


def test_async_cancelamento_externo_cancela_os_servicos() -> None:
    lento = Falso("lento", travar=True)

    async def rodar() -> None:
        tarefa = asyncio.ensure_future(consulta_cep_async(CEP, servicos=[lento]))
        await asyncio.sleep(0.05)
        tarefa.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarefa

    asyncio.run(rodar())
    assert lento.cancelado


class Pare(BaseException):
    pass


def test_async_base_exception_nao_e_engolida() -> None:
    class Interrompe(Falso):
        async def consultar_normalizado_async(
            self, cep: str, **kwargs: Any
        ) -> Endereco:
            raise Pare

    with pytest.raises(Pare):
        asyncio.run(consulta_cep_async(CEP, servicos=[Interrompe("x")]))


def test_lista_padrao_vazia(consultar: Consulta) -> None:
    with (
        mock.patch.object(modulo_servicos, "SERVICOS_CEP", []),
        pytest.raises(ServicosIndisponiveisError) as info,
    ):
        consultar(CEP)
    assert info.value.erros == {}


def test_versao() -> None:
    assert pacote.__version__ == "1.0.0.dev0"

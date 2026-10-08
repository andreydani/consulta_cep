"""Testes contra as APIs reais. Rodam apenas com ``pytest -m live``."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest

from consulta_cep import (
    CEPNaoEncontradoError,
    Endereco,
    consulta_cep,
    consulta_cep_async,
    servicos_disponiveis,
)
from consulta_cep.servicos import obter_servico

pytestmark = pytest.mark.live

TIMEOUT = 15

# Nenhuma faixa de CEP começa abaixo de 01000-000; 99999-999 não serve, porque
# BrasilAPI e OpenCEP devolveram um endereço para ele.
CEP_INEXISTENTE = "00000-000"


@contextmanager
def _sem_limite_de_requisicoes() -> Iterator[None]:
    """Pula o teste se a API recusar por excesso de requisições (HTTP 429).

    Os runners do GitHub Actions compartilham IPs, e algumas APIs (como a
    AwesomeAPI) limitam por IP; isso não indica mudança na API.
    """
    try:
        yield
    except httpx.HTTPStatusError as erro:
        if erro.response.status_code == 429:
            pytest.skip(f"limite de requisições atingido: {erro.request.url}")
        raise


def _verificar_praca_da_se(endereco: Endereco) -> None:
    assert endereco.estado == "SP"
    assert endereco.cidade == "São Paulo"
    assert endereco.bairro == "Sé"
    assert endereco.logradouro == "Praça da Sé"
    assert endereco.cep == "01001-000"


@pytest.mark.parametrize("nome", servicos_disponiveis())
def test_servico_real(nome: str) -> None:
    with _sem_limite_de_requisicoes():
        endereco = obter_servico(nome).consultar("01001-000", timeout=TIMEOUT)
    assert endereco.servico == nome
    _verificar_praca_da_se(endereco)


@pytest.mark.parametrize("nome", servicos_disponiveis())
def test_servico_real_cep_inexistente(nome: str) -> None:
    try:
        with _sem_limite_de_requisicoes():
            endereco = obter_servico(nome).consultar(CEP_INEXISTENTE, timeout=TIMEOUT)
    except CEPNaoEncontradoError:
        return
    pytest.fail(f"{nome} devolveu um endereço para {CEP_INEXISTENTE}: {endereco}")


@pytest.mark.parametrize("estrategia", ["concorrente", "sequencial"])
def test_consulta_cep_real(estrategia: str) -> None:
    endereco = consulta_cep(
        "01001-000",
        timeout=TIMEOUT,
        estrategia=estrategia,  # type: ignore[arg-type]
    )
    _verificar_praca_da_se(endereco)


@pytest.mark.parametrize("nome", servicos_disponiveis())
def test_servico_real_async(nome: str) -> None:
    servico = obter_servico(nome)
    with _sem_limite_de_requisicoes():
        endereco = asyncio.run(servico.consultar_async("01001-000", timeout=TIMEOUT))
    _verificar_praca_da_se(endereco)


@pytest.mark.parametrize("estrategia", ["concorrente", "sequencial"])
def test_consulta_cep_async_real(estrategia: str) -> None:
    endereco = asyncio.run(
        consulta_cep_async(
            "01001-000",
            timeout=TIMEOUT,
            estrategia=estrategia,  # type: ignore[arg-type]
        )
    )
    _verificar_praca_da_se(endereco)

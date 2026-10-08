"""Testes contra as APIs reais. Rodam apenas com ``pytest -m live``."""

from __future__ import annotations

import asyncio

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


def _verificar_praca_da_se(endereco: Endereco) -> None:
    assert endereco.estado == "SP"
    assert endereco.cidade == "São Paulo"
    assert endereco.bairro == "Sé"
    assert endereco.logradouro == "Praça da Sé"
    assert endereco.cep == "01001-000"


@pytest.mark.parametrize("nome", servicos_disponiveis())
def test_servico_real(nome: str) -> None:
    endereco = obter_servico(nome).consultar("01001-000", timeout=TIMEOUT)
    assert endereco.servico == nome
    _verificar_praca_da_se(endereco)


@pytest.mark.parametrize("nome", servicos_disponiveis())
def test_servico_real_cep_inexistente(nome: str) -> None:
    with pytest.raises(CEPNaoEncontradoError):
        obter_servico(nome).consultar("99999-999", timeout=TIMEOUT)


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

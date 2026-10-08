"""Testes contra as APIs reais. Rodam apenas com ``pytest -m live``."""

from __future__ import annotations

import pytest

from consulta_cep import CEPNaoEncontradoError, Endereco, consulta_cep
from consulta_cep.engine_cep import ConsultaCEP
from consulta_cep.servicos import SERVICOS_CEP

pytestmark = pytest.mark.live


def _verificar_praca_da_se(endereco: Endereco) -> None:
    assert endereco.estado == "SP"
    assert endereco.cidade == "São Paulo"
    assert endereco.bairro == "Sé"
    assert endereco.logradouro == "Praça da Sé"


@pytest.mark.parametrize("servico", SERVICOS_CEP, ids=lambda s: s.nome)
def test_servico_real(servico: ConsultaCEP) -> None:
    _verificar_praca_da_se(servico.consultar("01001-000", timeout=10))


@pytest.mark.parametrize("servico", SERVICOS_CEP, ids=lambda s: s.nome)
def test_servico_real_cep_inexistente(servico: ConsultaCEP) -> None:
    with pytest.raises(CEPNaoEncontradoError):
        servico.consultar("99999-999", timeout=10)


def test_consulta_cep_real() -> None:
    _verificar_praca_da_se(consulta_cep("01001-000", timeout=10))

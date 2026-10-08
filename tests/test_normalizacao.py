from __future__ import annotations

import pytest

from consulta_cep import CEPInvalidoError, ConsultaCEPError, normalizar_cep
from consulta_cep.util import sanitizar_cep, validar_cep


@pytest.mark.parametrize(
    "cep",
    ["01001-000", "01001000", "01.001-000", "  01001-000 ", "\t01001000\n"],
)
def test_formatos_aceitos(cep: str) -> None:
    assert normalizar_cep(cep) == "01001000"


@pytest.mark.parametrize(
    "cep",
    [
        "",
        "   ",
        "0100-1000",
        "0100100",
        "010010000",
        "01001_000",
        "01 001-000",
        "01001--000",
        "abcde-fgh",
        "\uff10\uff11\uff10\uff10\uff11\uff10\uff10\uff10",  # dígitos de largura total
        "01001-000a",
    ],
)
def test_formatos_rejeitados(cep: str) -> None:
    with pytest.raises(CEPInvalidoError) as info:
        normalizar_cep(cep)
    assert info.value.cep == cep


def test_cep_invalido_e_value_error() -> None:
    erro = CEPInvalidoError("x")
    assert isinstance(erro, ValueError)
    assert isinstance(erro, ConsultaCEPError)


def test_nao_string_e_rejeitado() -> None:
    with pytest.raises(CEPInvalidoError):
        normalizar_cep(1001000)  # type: ignore[arg-type]


def test_funcoes_antigas_continuam_disponiveis() -> None:
    assert validar_cep("01001-000") is True
    assert sanitizar_cep("01001-000") == "01001000"
    with pytest.raises(ValueError):
        validar_cep("123")

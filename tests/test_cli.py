from __future__ import annotations

import json
import subprocess
import sys
from unittest import mock

import pytest

from consulta_cep import (
    CEPNaoEncontradoError,
    Endereco,
    ServicosIndisponiveisError,
)
from consulta_cep.__main__ import main

ENDERECO = Endereco(
    servico="BrasilAPI",
    estado="SP",
    cidade="São Paulo",
    bairro="Sé",
    logradouro="Praça da Sé",
)


def test_sucesso(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch(
        "consulta_cep.__main__.consulta_cep", return_value=ENDERECO
    ) as consulta:
        assert main(["01001-000", "--timeout", "2"]) == 0
    consulta.assert_called_once_with("01001-000", timeout=2.0)
    saida = capsys.readouterr().out
    assert "São Paulo" in saida
    assert json.loads(saida)["logradouro"] == "Praça da Sé"


def test_cep_invalido(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["123"]) == 2
    assert "erro" in json.loads(capsys.readouterr().err)


@pytest.mark.parametrize(
    "erro",
    [CEPNaoEncontradoError("01001000"), ServicosIndisponiveisError({})],
)
def test_erros_da_consulta(erro: Exception, capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch("consulta_cep.__main__.consulta_cep", side_effect=erro):
        assert main(["01001-000"]) == 1
    assert json.loads(capsys.readouterr().err) == {"erro": str(erro)}


def test_importar_main_nao_executa() -> None:
    # Antes, importar consulta_cep.__main__ executava main() e lia sys.argv.
    resultado = subprocess.run(
        [sys.executable, "-c", "import consulta_cep.__main__"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0
    assert resultado.stdout == resultado.stderr == ""


def test_python_m_sem_argumentos_mostra_uso() -> None:
    resultado = subprocess.run(
        [sys.executable, "-m", "consulta_cep"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 2
    assert "usage" in resultado.stderr

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import responses

from consulta_cep.servicos import _REGISTRO

CEP = "01001000"
CEP_INEXISTENTE = "99999999"
FIXTURES = Path(__file__).parent / "fixtures"


def fixture(servico: str, nome: str) -> dict[str, Any]:
    """Lê ``tests/fixtures/<servico>/<nome>.json``."""
    dados: dict[str, Any] = json.loads(
        (FIXTURES / servico / f"{nome}.json").read_text(encoding="utf-8")
    )
    return dados


def url(servico: str, cep: str = CEP) -> str:
    return str(vars(_REGISTRO[servico])["URL"]).format(cep=cep)


def simular(
    mock: responses.RequestsMock,
    servico: str,
    nome: str,
    cep: str = CEP,
) -> None:
    """Registra no ``mock`` a fixture ``nome`` do serviço."""
    dados = fixture(servico, nome)
    body = dados["body"]
    if body is None:
        mock.get(url(servico, cep), status=dados["status"])
    else:
        mock.get(url(servico, cep), status=dados["status"], json=body)

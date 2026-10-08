from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import respx

from consulta_cep.servicos import obter_servico

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
    return obter_servico(servico).montar_url(cep)


def resposta(servico: str, nome: str) -> httpx.Response:
    """Monta a resposta HTTP da fixture ``nome`` do serviço."""
    dados = fixture(servico, nome)
    if dados["body"] is None:
        return httpx.Response(dados["status"])
    return httpx.Response(dados["status"], json=dados["body"])


def simular(
    router: respx.MockRouter,
    servico: str,
    nome: str,
    cep: str = CEP,
) -> respx.Route:
    """Registra no ``router`` a fixture ``nome`` do serviço."""
    return router.get(url(servico, cep)).mock(return_value=resposta(servico, nome))

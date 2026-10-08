from __future__ import annotations

import re
from typing import Any

import requests

from .excecoes import CEPInvalidoError, CEPNaoEncontradoError

TIMEOUT_PADRAO: float = 5.0
"""Tempo máximo, em segundos, de cada requisição HTTP."""

_PADRAO_CEP = re.compile(r"([0-9]{2})\.?([0-9]{3})-?([0-9]{3})")


def normalizar_cep(cep: str) -> str:
    """Valida o CEP e devolve apenas os seus 8 dígitos.

    Aceita ``01001-000``, ``01001000`` e ``01.001-000``, com espaços nas
    pontas. Qualquer outro formato lança :class:`CEPInvalidoError`.
    """
    if not isinstance(cep, str):
        raise CEPInvalidoError(repr(cep))
    correspondencia = _PADRAO_CEP.fullmatch(cep.strip())
    if correspondencia is None:
        raise CEPInvalidoError(cep)
    return "".join(correspondencia.groups())


def validar_cep(cep: str) -> bool:
    """Lança :class:`CEPInvalidoError` se o CEP for inválido."""
    normalizar_cep(cep)
    return True


def sanitizar_cep(cep: str) -> str:
    """Mantido por compatibilidade; equivale a :func:`normalizar_cep`."""
    return normalizar_cep(cep)


def consulta_cep_https(
    url: str, cep: str, *, timeout: float = TIMEOUT_PADRAO
) -> dict[str, Any]:
    """Faz o GET em ``url`` (com ``{cep}`` substituído) e devolve o JSON.

    Lança :class:`CEPNaoEncontradoError` para respostas 404 e
    :class:`requests.HTTPError` para outros erros HTTP.
    """
    response = requests.get(url.format(cep=cep), timeout=timeout)
    if response.status_code == 404:
        raise CEPNaoEncontradoError(cep)
    response.raise_for_status()
    dados = response.json()
    if not isinstance(dados, dict):
        raise ValueError(f"Resposta inesperada de {response.url}: {dados!r}")
    return dados

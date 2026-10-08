from __future__ import annotations

import dataclasses
import json
import unicodedata
from abc import ABC, abstractmethod
from typing import Any

import httpx

from .util import TIMEOUT_PADRAO, ler_resposta, normalizar_cep

UFS: dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}
"""Siglas das unidades federativas e seus nomes."""


def _sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


_SIGLA_POR_NOME = {_sem_acentos(nome).casefold(): uf for uf, nome in UFS.items()}


def sigla_uf(estado: str) -> str:
    """Devolve a sigla da UF a partir da sigla ou do nome do estado.

    Lança :class:`ValueError` se o estado não for reconhecido.
    """
    texto = " ".join(estado.split())
    if texto.upper() in UFS:
        return texto.upper()
    sigla = _SIGLA_POR_NOME.get(_sem_acentos(texto).casefold())
    if sigla is None:
        raise ValueError(f"Estado desconhecido: {estado!r}")
    return sigla


def texto_opcional(valor: Any) -> str | None:
    """Converte o valor para texto, trocando ausente, null e vazio por None."""
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def numero_opcional(valor: Any) -> float | None:
    """Converte o valor para float, trocando ausente, null e vazio por None."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, int | float):
        return float(valor)
    texto = str(valor).strip()
    return float(texto) if texto else None


@dataclasses.dataclass
class Endereco:
    """Endereço devolvido pela consulta.

    Campos de texto vazios viram ``None``; ``estado`` é sempre a sigla da UF e
    ``cep`` fica no formato ``12345-678``.
    """

    servico: str
    estado: str
    cidade: str
    bairro: str | None
    logradouro: str | None
    cep: str | None = None
    complemento: str | None = None
    ibge: str | None = None
    ddd: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    def __post_init__(self) -> None:
        self.estado = sigla_uf(self.estado)
        self.bairro = texto_opcional(self.bairro)
        self.logradouro = texto_opcional(self.logradouro)
        self.complemento = texto_opcional(self.complemento)
        self.ibge = texto_opcional(self.ibge)
        self.ddd = texto_opcional(self.ddd)
        cep = texto_opcional(self.cep)
        if cep is not None:
            digitos = normalizar_cep(cep)
            cep = f"{digitos[:5]}-{digitos[5:]}"
        self.cep = cep

    def to_dict(self) -> dict[str, Any]:
        """Devolve o endereço como dicionário."""
        return dataclasses.asdict(self)

    def to_json(self, **kwargs: Any) -> str:
        """Devolve o endereço como JSON, preservando acentos."""
        kwargs.setdefault("ensure_ascii", False)
        return json.dumps(self.to_dict(), **kwargs)

    def __str__(self) -> str:
        return self.to_json()


class ConsultaCEP(ABC):
    """Base dos serviços de consulta de CEP.

    Subclasses definem ``nome`` (nome curto, usado no registro e em
    ``Endereco.servico``), ``URL`` (com o marcador ``{cep}``) e implementam
    :meth:`converter`. Os caminhos síncrono e assíncrono compartilham
    :meth:`montar_url` e :meth:`converter`.
    """

    nome: str = ""
    URL: str = ""

    def montar_url(self, cep: str) -> str:
        """URL da consulta para um CEP já normalizado (8 dígitos)."""
        return self.URL.format(cep=cep)

    @abstractmethod
    def converter(self, dados: dict[str, Any], cep: str) -> Endereco:
        """Converte o JSON da resposta em :class:`Endereco`.

        Lança :class:`CEPNaoEncontradoError` se a resposta indicar que o CEP
        não existe.
        """

    def interpretar(self, resposta: httpx.Response, cep: str) -> Endereco:
        """Valida a resposta HTTP e converte o JSON."""
        return self.converter(ler_resposta(resposta, cep), cep)

    def consultar(
        self,
        cep: str,
        *,
        timeout: float = TIMEOUT_PADRAO,
        client: httpx.Client | None = None,
    ) -> Endereco:
        """Valida, normaliza e consulta o CEP neste serviço."""
        return self.consultar_normalizado(
            normalizar_cep(cep), timeout=timeout, client=client
        )

    async def consultar_async(
        self,
        cep: str,
        *,
        timeout: float = TIMEOUT_PADRAO,
        client: httpx.AsyncClient | None = None,
    ) -> Endereco:
        """Versão assíncrona de :meth:`consultar`."""
        return await self.consultar_normalizado_async(
            normalizar_cep(cep), timeout=timeout, client=client
        )

    def consultar_normalizado(
        self,
        cep: str,
        *,
        timeout: float = TIMEOUT_PADRAO,
        client: httpx.Client | None = None,
    ) -> Endereco:
        """Consulta um CEP já normalizado (8 dígitos)."""
        url = self.montar_url(cep)
        if client is None:
            resposta = httpx.get(url, timeout=timeout)
        else:
            resposta = client.get(url, timeout=timeout)
        return self.interpretar(resposta, cep)

    async def consultar_normalizado_async(
        self,
        cep: str,
        *,
        timeout: float = TIMEOUT_PADRAO,
        client: httpx.AsyncClient | None = None,
    ) -> Endereco:
        """Versão assíncrona de :meth:`consultar_normalizado`."""
        url = self.montar_url(cep)
        if client is None:
            async with httpx.AsyncClient() as novo:
                resposta = await novo.get(url, timeout=timeout)
        else:
            resposta = await client.get(url, timeout=timeout)
        return self.interpretar(resposta, cep)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

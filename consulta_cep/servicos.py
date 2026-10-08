from __future__ import annotations

from typing import Any, TypeVar

from .engine_cep import ConsultaCEP, Endereco, numero_opcional, texto_opcional
from .excecoes import CEPNaoEncontradoError

_REGISTRO: dict[str, type[ConsultaCEP]] = {}

_C = TypeVar("_C", bound=type[ConsultaCEP])


def registrar_servico(classe: _C) -> _C:
    """Decorador que registra a classe do serviço pelo seu ``nome``."""
    if not classe.nome:
        raise ValueError(f"{classe.__name__} precisa definir o atributo 'nome'.")
    if classe.nome in _REGISTRO:
        raise ValueError(f"Já existe um serviço registrado como {classe.nome!r}.")
    _REGISTRO[classe.nome] = classe
    return classe


def servicos_disponiveis() -> list[str]:
    """Nomes de todos os serviços registrados, na ordem de registro."""
    return list(_REGISTRO)


def obter_servico(nome: str) -> ConsultaCEP:
    """Cria o serviço registrado com esse nome.

    Lança :class:`ValueError` se o nome não estiver registrado.
    """
    try:
        classe = _REGISTRO[nome]
    except KeyError:
        disponiveis = ", ".join(_REGISTRO)
        raise ValueError(
            f"Serviço desconhecido: {nome!r}. Disponíveis: {disponiveis}."
        ) from None
    return classe()


def _primeiro(*valores: Any) -> Any:
    """Primeiro valor que não seja None nem vazio."""
    return next((v for v in valores if v not in (None, "")), None)


def _cep(res: dict[str, Any], cep: str) -> str:
    return str(_primeiro(res.get("cep"), cep))


@registrar_servico
class ConsultaCEPBrasilAPI(ConsultaCEP):
    nome = "brasilapi"
    URL = "https://brasilapi.com.br/api/cep/v2/{cep}"

    def converter(self, res: dict[str, Any], cep: str) -> Endereco:
        location = res.get("location") or {}
        coordenadas = location.get("coordinates") or {}
        return Endereco(
            servico=self.nome,
            estado=str(res["state"]),
            cidade=str(res["city"]),
            bairro=texto_opcional(res.get("neighborhood")),
            logradouro=texto_opcional(res.get("street")),
            cep=_cep(res, cep),
            latitude=numero_opcional(coordenadas.get("latitude")),
            longitude=numero_opcional(coordenadas.get("longitude")),
        )


@registrar_servico
class ConsultaCEPViaCEP(ConsultaCEP):
    nome = "viacep"
    URL = "https://viacep.com.br/ws/{cep}/json/"

    def converter(self, res: dict[str, Any], cep: str) -> Endereco:
        # CEP inexistente: status 200 com {"erro": "true"} ou {"erro": true}.
        if str(res.get("erro", "")).lower() == "true":
            raise CEPNaoEncontradoError(cep)
        return Endereco(
            servico=self.nome,
            estado=str(res["uf"]),
            cidade=str(res["localidade"]),
            bairro=texto_opcional(res.get("bairro")),
            logradouro=texto_opcional(res.get("logradouro")),
            cep=_cep(res, cep),
            complemento=texto_opcional(res.get("complemento")),
            ibge=texto_opcional(res.get("ibge")),
            ddd=texto_opcional(res.get("ddd")),
        )


@registrar_servico
class ConsultaCEPOpenCEP(ConsultaCEP):
    nome = "opencep"
    URL = "https://opencep.com/v1/{cep}"

    def converter(self, res: dict[str, Any], cep: str) -> Endereco:
        return Endereco(
            servico=self.nome,
            estado=str(_primeiro(res.get("uf"), res.get("estado"))),
            cidade=str(res["localidade"]),
            bairro=texto_opcional(res.get("bairro")),
            logradouro=texto_opcional(res.get("logradouro")),
            cep=_cep(res, cep),
            complemento=texto_opcional(res.get("complemento")),
            ibge=texto_opcional(res.get("ibge")),
        )


@registrar_servico
class ConsultaCEPAwesomeAPI(ConsultaCEP):
    nome = "awesomeapi"
    URL = "https://cep.awesomeapi.com.br/json/{cep}"

    def converter(self, res: dict[str, Any], cep: str) -> Endereco:
        return Endereco(
            servico=self.nome,
            estado=str(res["state"]),
            cidade=str(res["city"]),
            bairro=texto_opcional(res.get("district")),
            logradouro=texto_opcional(res.get("address")),
            cep=_cep(res, cep),
            ibge=texto_opcional(res.get("city_ibge")),
            ddd=texto_opcional(res.get("ddd")),
            latitude=numero_opcional(res.get("lat")),
            longitude=numero_opcional(res.get("lng")),
        )


SERVICOS_PADRAO: tuple[str, ...] = ("brasilapi", "viacep", "opencep", "awesomeapi")
"""Serviços consultados quando ``servicos`` não é informado."""

SERVICOS_CEP: list[ConsultaCEP] = [obter_servico(nome) for nome in SERVICOS_PADRAO]
"""Instâncias dos serviços padrão (mantido por compatibilidade)."""

"""Consulta de endereços a partir do CEP em vários serviços ao mesmo tempo."""

from __future__ import annotations

from .consulta import Estrategia, consulta_cep
from .engine_cep import ConsultaCEP, Endereco
from .excecoes import (
    CEPInvalidoError,
    CEPNaoEncontradoError,
    ConsultaCEPError,
    ServicosIndisponiveisError,
)
from .servicos import SERVICOS_CEP, SERVICOS_PADRAO, servicos_disponiveis
from .util import TIMEOUT_PADRAO, normalizar_cep

__version__ = "1.0.0.dev0"

__all__ = [
    "SERVICOS_CEP",
    "SERVICOS_PADRAO",
    "TIMEOUT_PADRAO",
    "CEPInvalidoError",
    "CEPNaoEncontradoError",
    "ConsultaCEP",
    "ConsultaCEPError",
    "Endereco",
    "Estrategia",
    "ServicosIndisponiveisError",
    "__version__",
    "consulta_cep",
    "normalizar_cep",
    "servicos_disponiveis",
]

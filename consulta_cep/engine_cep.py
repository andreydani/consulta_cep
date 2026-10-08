from __future__ import annotations

import dataclasses
import json
from abc import ABC, abstractmethod
from typing import Any

from .util import TIMEOUT_PADRAO, normalizar_cep


@dataclasses.dataclass
class Endereco:
    servico: str
    estado: str
    cidade: str
    bairro: str
    logradouro: str

    def __str__(self) -> str:
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False)


class ConsultaCEP(ABC):
    """Base dos serviços de consulta de CEP."""

    nome: str = ""

    def consultar(self, cep: str, *, timeout: float = TIMEOUT_PADRAO) -> Endereco:
        """Valida, normaliza e consulta o CEP neste serviço."""
        return self.consultar_normalizado(normalizar_cep(cep), timeout=timeout)

    @abstractmethod
    def consultar_normalizado(
        self, cep: str, *, timeout: float = TIMEOUT_PADRAO
    ) -> Endereco:
        """Consulta um CEP já normalizado (8 dígitos)."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


def texto(dados: dict[str, Any], chave: str) -> str:
    """Lê um campo opcional da resposta, trocando ausência/null por ''."""
    valor = dados.get(chave)
    return "" if valor is None else str(valor)

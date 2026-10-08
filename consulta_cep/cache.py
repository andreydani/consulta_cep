"""Cache em memória dos endereços encontrados."""

from __future__ import annotations

import dataclasses
import threading
import time
from collections import OrderedDict
from collections.abc import Callable

from .engine_cep import Endereco

TTL_PADRAO: float = 24 * 60 * 60
"""Validade padrão de cada entrada, em segundos (24 horas)."""

MAXIMO_PADRAO = 1024
"""Quantidade máxima padrão de CEPs guardados."""


class CacheLRU:
    """Cache LRU com validade (TTL), seguro para uso entre threads.

    Guarda apenas endereços encontrados, indexados pelo CEP normalizado
    (8 dígitos). Quando cheio, descarta o CEP usado há mais tempo.
    """

    def __init__(
        self,
        maximo: int = MAXIMO_PADRAO,
        ttl: float = TTL_PADRAO,
        *,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        if maximo < 1:
            raise ValueError("maximo deve ser pelo menos 1.")
        if ttl <= 0:
            raise ValueError("ttl deve ser positivo.")
        self.maximo = maximo
        self.ttl = ttl
        self._relogio = relogio
        self._dados: OrderedDict[str, tuple[float, Endereco]] = OrderedDict()
        self._trava = threading.Lock()

    def obter(self, cep: str) -> Endereco | None:
        """Devolve uma cópia do endereço guardado, ou None se ausente/expirado."""
        with self._trava:
            item = self._dados.get(cep)
            if item is None:
                return None
            expira_em, endereco = item
            if self._relogio() >= expira_em:
                del self._dados[cep]
                return None
            self._dados.move_to_end(cep)
            return dataclasses.replace(endereco)

    def guardar(self, cep: str, endereco: Endereco) -> None:
        """Guarda uma cópia do endereço para o CEP."""
        with self._trava:
            self._dados[cep] = (
                self._relogio() + self.ttl,
                dataclasses.replace(endereco),
            )
            self._dados.move_to_end(cep)
            while len(self._dados) > self.maximo:
                self._dados.popitem(last=False)

    def limpar(self) -> None:
        """Remove todas as entradas."""
        with self._trava:
            self._dados.clear()

    def __len__(self) -> int:
        with self._trava:
            return len(self._dados)

    def __contains__(self, cep: object) -> bool:
        return isinstance(cep, str) and self.obter(cep) is not None


CACHE_PADRAO = CacheLRU()
"""Cache usado por ``consulta_cep(..., cache=True)`` e pela versão async."""


def limpar_cache() -> None:
    """Esvazia o cache padrão."""
    CACHE_PADRAO.limpar()

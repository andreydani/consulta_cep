from __future__ import annotations

import asyncio
import threading
from typing import Any

import httpx

from consulta_cep import ConsultaCEP, Endereco


class Falso(ConsultaCEP):
    """Serviço simulado, sem HTTP, que registra as chamadas.

    ``erro`` é lançado em vez de devolver o endereço. ``espera`` (sync) bloqueia
    até o evento ser liberado; ``travar`` (async) espera para sempre, até ser
    cancelado.
    """

    def __init__(
        self,
        nome: str,
        erro: Exception | None = None,
        espera: threading.Event | None = None,
        travar: bool = False,
    ) -> None:
        self.nome = nome
        self.erro = erro
        self.espera = espera
        self.travar = travar
        self.chamadas: list[tuple[str, float]] = []
        self.clientes: list[object] = []
        self.cancelado = False

    def converter(self, dados: dict[str, Any], cep: str) -> Endereco:
        return Endereco(self.nome, "SP", "São Paulo", "Sé", "Praça da Sé", cep=cep)

    def _resultado(self, cep: str) -> Endereco:
        if self.erro is not None:
            raise self.erro
        return self.converter({}, cep)

    def consultar_normalizado(
        self, cep: str, *, timeout: float = 5, client: httpx.Client | None = None
    ) -> Endereco:
        self.chamadas.append((cep, timeout))
        self.clientes.append(client)
        if self.espera is not None:
            self.espera.wait(timeout=10)
        return self._resultado(cep)

    async def consultar_normalizado_async(
        self,
        cep: str,
        *,
        timeout: float = 5,
        client: httpx.AsyncClient | None = None,
    ) -> Endereco:
        self.chamadas.append((cep, timeout))
        self.clientes.append(client)
        if self.travar:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelado = True
                raise
        await asyncio.sleep(0)
        return self._resultado(cep)

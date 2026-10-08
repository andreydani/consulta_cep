"""Consulta de endereços a partir do CEP em vários serviços ao mesmo tempo."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from .engine_cep import ConsultaCEP, Endereco
from .excecoes import (
    CEPInvalidoError,
    CEPNaoEncontradoError,
    ConsultaCEPError,
    ServicosIndisponiveisError,
)
from .servicos import SERVICOS_CEP
from .util import TIMEOUT_PADRAO, normalizar_cep

__version__ = "1.0.0.dev0"

__all__ = [
    "TIMEOUT_PADRAO",
    "CEPInvalidoError",
    "CEPNaoEncontradoError",
    "ConsultaCEP",
    "ConsultaCEPError",
    "Endereco",
    "ServicosIndisponiveisError",
    "__version__",
    "consulta_cep",
    "normalizar_cep",
]

logger = logging.getLogger("consulta_cep")


def consulta_cep(cep: str, *, timeout: float = TIMEOUT_PADRAO) -> Endereco:
    """Consulta o CEP em todos os serviços ao mesmo tempo.

    Devolve o endereço do primeiro serviço que responder com sucesso, sem
    esperar os demais.

    :param cep: CEP nos formatos ``12345-678``, ``12345678`` ou ``12.345-678``.
    :param timeout: tempo máximo, em segundos, de cada requisição HTTP.
    :raises CEPInvalidoError: o CEP não tem formato válido.
    :raises CEPNaoEncontradoError: algum serviço informou que o CEP não existe
        e nenhum devolveu endereço.
    :raises ServicosIndisponiveisError: nenhum serviço respondeu.
    """
    cep_normalizado = normalizar_cep(cep)
    servicos = list(SERVICOS_CEP)
    erros: dict[str, BaseException] = {}

    executor = ThreadPoolExecutor(
        max_workers=max(len(servicos), 1), thread_name_prefix="consulta_cep"
    )
    try:
        futuros: dict[Future[Endereco], ConsultaCEP] = {
            executor.submit(
                servico.consultar_normalizado, cep_normalizado, timeout=timeout
            ): servico
            for servico in servicos
        }
        for futuro in as_completed(futuros):
            nome = futuros[futuro].nome or type(futuros[futuro]).__name__
            try:
                return futuro.result()
            except CEPNaoEncontradoError as erro:
                logger.info("%s: CEP %s não encontrado", nome, cep_normalizado)
                erros[nome] = erro
            except Exception as erro:
                logger.warning("Erro ao consultar %s: %s", nome, erro, exc_info=erro)
                erros[nome] = erro
    finally:
        # Não espera os serviços mais lentos: as threads restantes terminam
        # sozinhas (no máximo após ``timeout``) e o resultado é descartado.
        executor.shutdown(wait=False, cancel_futures=True)

    if any(isinstance(erro, CEPNaoEncontradoError) for erro in erros.values()):
        raise CEPNaoEncontradoError(cep_normalizado)
    raise ServicosIndisponiveisError(erros)

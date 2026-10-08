from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Literal, get_args

from . import servicos as _servicos
from .engine_cep import ConsultaCEP, Endereco
from .excecoes import CEPNaoEncontradoError, ServicosIndisponiveisError
from .util import TIMEOUT_PADRAO, normalizar_cep

logger = logging.getLogger("consulta_cep")

Estrategia = Literal["concorrente", "sequencial"]
"""``concorrente``: consulta todos ao mesmo tempo e devolve o primeiro que
responder. ``sequencial``: tenta um por vez, na ordem, e para no primeiro
sucesso."""

ServicosParam = str | ConsultaCEP | Iterable[str | ConsultaCEP]


def _resolver_servicos(servicos: ServicosParam | None) -> list[ConsultaCEP]:
    if servicos is None:
        return list(_servicos.SERVICOS_CEP)
    if isinstance(servicos, str | ConsultaCEP):
        servicos = [servicos]
    resolvidos = [
        _servicos.obter_servico(s) if isinstance(s, str) else s for s in servicos
    ]
    for servico in resolvidos:
        if not isinstance(servico, ConsultaCEP):
            raise TypeError(
                "servicos deve conter nomes ou instâncias de ConsultaCEP, "
                f"não {servico!r}."
            )
    if not resolvidos:
        raise ValueError("Informe pelo menos um serviço.")
    return resolvidos


def _nome(servico: ConsultaCEP) -> str:
    return servico.nome or type(servico).__name__


def _registrar_erro(
    erros: dict[str, BaseException], servico: ConsultaCEP, cep: str, erro: Exception
) -> None:
    nome = _nome(servico)
    if isinstance(erro, CEPNaoEncontradoError):
        logger.info("%s: CEP %s não encontrado", nome, cep)
    else:
        logger.warning("Erro ao consultar %s: %s", nome, erro, exc_info=erro)
    erros[nome] = erro


def _concorrente(
    servicos: Sequence[ConsultaCEP],
    cep: str,
    timeout: float,
    erros: dict[str, BaseException],
) -> Endereco | None:
    executor = ThreadPoolExecutor(
        max_workers=len(servicos), thread_name_prefix="consulta_cep"
    )
    try:
        futuros: dict[Future[Endereco], ConsultaCEP] = {
            executor.submit(s.consultar_normalizado, cep, timeout=timeout): s
            for s in servicos
        }
        for futuro in as_completed(futuros):
            try:
                return futuro.result()
            except Exception as erro:
                _registrar_erro(erros, futuros[futuro], cep, erro)
    finally:
        # Não espera os serviços mais lentos: as threads restantes terminam
        # sozinhas (no máximo após ``timeout``) e o resultado é descartado.
        executor.shutdown(wait=False, cancel_futures=True)
    return None


def _sequencial(
    servicos: Sequence[ConsultaCEP],
    cep: str,
    timeout: float,
    erros: dict[str, BaseException],
) -> Endereco | None:
    for servico in servicos:
        try:
            return servico.consultar_normalizado(cep, timeout=timeout)
        except Exception as erro:
            _registrar_erro(erros, servico, cep, erro)
    return None


def consulta_cep(
    cep: str,
    *,
    timeout: float = TIMEOUT_PADRAO,
    servicos: ServicosParam | None = None,
    estrategia: Estrategia = "concorrente",
) -> Endereco:
    """Consulta o CEP nos serviços e devolve o primeiro endereço obtido.

    :param cep: CEP nos formatos ``12345-678``, ``12345678`` ou ``12.345-678``.
    :param timeout: tempo máximo, em segundos, de cada requisição HTTP.
    :param servicos: nomes (veja :func:`servicos_disponiveis`) ou instâncias de
        :class:`ConsultaCEP`, na ordem de preferência. Padrão: brasilapi,
        viacep, opencep e awesomeapi.
    :param estrategia: ``"concorrente"`` (padrão) consulta todos ao mesmo tempo
        e devolve o primeiro que responder; ``"sequencial"`` tenta um por vez,
        na ordem, e para no primeiro sucesso.
    :raises CEPInvalidoError: o CEP não tem formato válido.
    :raises CEPNaoEncontradoError: algum serviço informou que o CEP não existe
        e nenhum devolveu endereço.
    :raises ServicosIndisponiveisError: nenhum serviço respondeu.
    :raises ValueError: serviço ou estratégia desconhecidos.
    """
    if estrategia not in get_args(Estrategia):
        raise ValueError(
            f"Estratégia desconhecida: {estrategia!r}. "
            "Use 'concorrente' ou 'sequencial'."
        )
    cep_normalizado = normalizar_cep(cep)
    lista = _resolver_servicos(servicos)
    erros: dict[str, BaseException] = {}

    executar = _concorrente if estrategia == "concorrente" else _sequencial
    endereco = executar(lista, cep_normalizado, timeout, erros) if lista else None
    if endereco is not None:
        return endereco

    if any(isinstance(erro, CEPNaoEncontradoError) for erro in erros.values()):
        raise CEPNaoEncontradoError(cep_normalizado)
    raise ServicosIndisponiveisError(erros)

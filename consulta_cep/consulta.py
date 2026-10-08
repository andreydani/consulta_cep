from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Literal, NoReturn, get_args

import httpx

from . import servicos as _servicos
from .cache import CACHE_PADRAO, CacheLRU
from .engine_cep import ConsultaCEP, Endereco
from .excecoes import CEPNaoEncontradoError, ServicosIndisponiveisError
from .util import TIMEOUT_PADRAO, normalizar_cep

logger = logging.getLogger("consulta_cep")

Estrategia = Literal["concorrente", "sequencial"]
"""``concorrente``: consulta todos ao mesmo tempo e devolve o primeiro que
responder. ``sequencial``: tenta um por vez, na ordem, e para no primeiro
sucesso."""

ServicosParam = str | ConsultaCEP | Iterable[str | ConsultaCEP]


# --- partes compartilhadas entre sync e async ---------------------------------


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


def _resolver_cache(cache: bool | CacheLRU) -> CacheLRU | None:
    if isinstance(cache, CacheLRU):
        return cache
    return CACHE_PADRAO if cache else None


def _preparar(
    cep: str,
    servicos: ServicosParam | None,
    estrategia: str,
) -> tuple[str, list[ConsultaCEP]]:
    if estrategia not in get_args(Estrategia):
        raise ValueError(
            f"Estratégia desconhecida: {estrategia!r}. "
            "Use 'concorrente' ou 'sequencial'."
        )
    return normalizar_cep(cep), _resolver_servicos(servicos)


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


def _falhar(cep: str, erros: dict[str, BaseException]) -> NoReturn:
    if any(isinstance(erro, CEPNaoEncontradoError) for erro in erros.values()):
        raise CEPNaoEncontradoError(cep)
    raise ServicosIndisponiveisError(erros)


# --- síncrono -----------------------------------------------------------------


def _concorrente(
    servicos: Sequence[ConsultaCEP],
    cep: str,
    timeout: float,
    client: httpx.Client | None,
    erros: dict[str, BaseException],
) -> Endereco | None:
    executor = ThreadPoolExecutor(
        max_workers=len(servicos), thread_name_prefix="consulta_cep"
    )
    try:
        futuros: dict[Future[Endereco], ConsultaCEP] = {
            executor.submit(
                s.consultar_normalizado, cep, timeout=timeout, client=client
            ): s
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
    client: httpx.Client | None,
    erros: dict[str, BaseException],
) -> Endereco | None:
    for servico in servicos:
        try:
            return servico.consultar_normalizado(cep, timeout=timeout, client=client)
        except Exception as erro:
            _registrar_erro(erros, servico, cep, erro)
    return None


def consulta_cep(
    cep: str,
    *,
    timeout: float = TIMEOUT_PADRAO,
    servicos: ServicosParam | None = None,
    estrategia: Estrategia = "concorrente",
    client: httpx.Client | None = None,
    cache: bool | CacheLRU = False,
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
    :param client: :class:`httpx.Client` a reaproveitar (conexões, proxy etc.).
        Não é fechado pela função.
    :param cache: ``True`` usa o cache em memória padrão (LRU, 24 h, 1024
        CEPs), compartilhado com :func:`consulta_cep_async`; também aceita um
        :class:`CacheLRU` próprio. O cache é indexado só pelo CEP: um acerto
        devolve o endereço guardado, seja qual for o serviço que o obteve.
    :raises CEPInvalidoError: o CEP não tem formato válido.
    :raises CEPNaoEncontradoError: algum serviço informou que o CEP não existe
        e nenhum devolveu endereço.
    :raises ServicosIndisponiveisError: nenhum serviço respondeu.
    :raises ValueError: serviço ou estratégia desconhecidos.
    """
    cep_normalizado, lista = _preparar(cep, servicos, estrategia)
    armazenamento = _resolver_cache(cache)
    if armazenamento is not None:
        guardado = armazenamento.obter(cep_normalizado)
        if guardado is not None:
            return guardado

    erros: dict[str, BaseException] = {}
    executar = _concorrente if estrategia == "concorrente" else _sequencial
    endereco = (
        executar(lista, cep_normalizado, timeout, client, erros) if lista else None
    )
    if endereco is None:
        _falhar(cep_normalizado, erros)
    if armazenamento is not None:
        armazenamento.guardar(cep_normalizado, endereco)
    return endereco


# --- assíncrono ---------------------------------------------------------------


async def _concorrente_async(
    servicos: Sequence[ConsultaCEP],
    cep: str,
    timeout: float,
    client: httpx.AsyncClient,
    erros: dict[str, BaseException],
) -> Endereco | None:
    tarefas: dict[asyncio.Future[Endereco], ConsultaCEP] = {
        asyncio.ensure_future(
            s.consultar_normalizado_async(cep, timeout=timeout, client=client)
        ): s
        for s in servicos
    }
    ordem = list(tarefas)
    pendentes: set[asyncio.Future[Endereco]] = set(tarefas)
    try:
        while pendentes:
            concluidas, pendentes = await asyncio.wait(
                pendentes, return_when=asyncio.FIRST_COMPLETED
            )
            for tarefa in sorted(concluidas, key=ordem.index):
                erro = tarefa.exception()
                if erro is None:
                    return tarefa.result()
                if not isinstance(erro, Exception):
                    raise erro
                _registrar_erro(erros, tarefas[tarefa], cep, erro)
    finally:
        # Cancela os serviços que ainda não responderam e espera o
        # cancelamento terminar, para não deixar tarefas soltas.
        for tarefa in pendentes:
            tarefa.cancel()
        if pendentes:
            await asyncio.gather(*pendentes, return_exceptions=True)
    return None


async def _sequencial_async(
    servicos: Sequence[ConsultaCEP],
    cep: str,
    timeout: float,
    client: httpx.AsyncClient,
    erros: dict[str, BaseException],
) -> Endereco | None:
    for servico in servicos:
        try:
            return await servico.consultar_normalizado_async(
                cep, timeout=timeout, client=client
            )
        except Exception as erro:
            _registrar_erro(erros, servico, cep, erro)
    return None


async def consulta_cep_async(
    cep: str,
    *,
    timeout: float = TIMEOUT_PADRAO,
    servicos: ServicosParam | None = None,
    estrategia: Estrategia = "concorrente",
    client: httpx.AsyncClient | None = None,
    cache: bool | CacheLRU = False,
) -> Endereco:
    """Versão assíncrona (asyncio) de :func:`consulta_cep`.

    Tem os mesmos parâmetros e exceções. Na estratégia concorrente, devolve o
    primeiro sucesso e cancela as consultas que ainda não terminaram.

    :param client: :class:`httpx.AsyncClient` a reaproveitar. Se omitido, um
        cliente temporário é criado e fechado ao final.
    """
    cep_normalizado, lista = _preparar(cep, servicos, estrategia)
    armazenamento = _resolver_cache(cache)
    if armazenamento is not None:
        guardado = armazenamento.obter(cep_normalizado)
        if guardado is not None:
            return guardado

    erros: dict[str, BaseException] = {}
    executar = _concorrente_async if estrategia == "concorrente" else _sequencial_async
    endereco: Endereco | None = None
    if lista:
        if client is None:
            async with httpx.AsyncClient() as temporario:
                endereco = await executar(
                    lista, cep_normalizado, timeout, temporario, erros
                )
        else:
            endereco = await executar(lista, cep_normalizado, timeout, client, erros)
    if endereco is None:
        _falhar(cep_normalizado, erros)
    if armazenamento is not None:
        armazenamento.guardar(cep_normalizado, endereco)
    return endereco

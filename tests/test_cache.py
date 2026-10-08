from __future__ import annotations

import asyncio
import threading

import httpx
import pytest
import respx

from consulta_cep import (
    CacheLRU,
    CEPNaoEncontradoError,
    Endereco,
    ServicosIndisponiveisError,
    consulta_cep,
    consulta_cep_async,
    limpar_cache,
)
from consulta_cep.cache import CACHE_PADRAO, MAXIMO_PADRAO, TTL_PADRAO

from .dados import CEP, simular, url
from .falsos import Falso


class Relogio:
    def __init__(self) -> None:
        self.agora = 0.0

    def __call__(self) -> float:
        return self.agora


def _endereco(servico: str = "teste", cep: str = CEP) -> Endereco:
    return Endereco(servico, "SP", "São Paulo", "Sé", "Praça da Sé", cep=cep)


# --- CacheLRU -------------------------------------------------------------------


def test_padroes() -> None:
    assert TTL_PADRAO == 24 * 60 * 60
    assert MAXIMO_PADRAO == 1024
    assert CACHE_PADRAO.ttl == TTL_PADRAO
    assert CACHE_PADRAO.maximo == MAXIMO_PADRAO


def test_acerto_e_falta() -> None:
    cache = CacheLRU()
    assert cache.obter(CEP) is None
    cache.guardar(CEP, _endereco())
    assert cache.obter(CEP) == _endereco()
    assert CEP in cache
    assert len(cache) == 1


def test_expiracao() -> None:
    relogio = Relogio()
    cache = CacheLRU(ttl=10, relogio=relogio)
    cache.guardar(CEP, _endereco())
    relogio.agora = 9.9
    assert cache.obter(CEP) is not None
    relogio.agora = 10
    assert cache.obter(CEP) is None
    assert len(cache) == 0


def test_descarta_o_usado_ha_mais_tempo() -> None:
    cache = CacheLRU(maximo=2)
    cache.guardar("00000001", _endereco())
    cache.guardar("00000002", _endereco())
    cache.obter("00000001")  # passa a ser o mais recente
    cache.guardar("00000003", _endereco())
    assert "00000001" in cache
    assert "00000002" not in cache
    assert "00000003" in cache


def test_devolve_copias() -> None:
    cache = CacheLRU()
    original = _endereco()
    cache.guardar(CEP, original)
    original.cidade = "alterado"
    obtido = cache.obter(CEP)
    assert obtido is not None
    assert obtido.cidade == "São Paulo"
    obtido.cidade = "alterado"
    assert cache.obter(CEP) == _endereco()


def test_limpar() -> None:
    cache = CacheLRU()
    cache.guardar(CEP, _endereco())
    cache.limpar()
    assert len(cache) == 0


@pytest.mark.parametrize(("maximo", "ttl"), [(0, 1), (1, 0)])
def test_parametros_invalidos(maximo: int, ttl: float) -> None:
    with pytest.raises(ValueError):
        CacheLRU(maximo=maximo, ttl=ttl)


def test_thread_safe() -> None:
    cache = CacheLRU(maximo=50)

    def trabalhar(inicio: int) -> None:
        for i in range(inicio, inicio + 500):
            cep = f"{i % 80:08d}"
            cache.guardar(cep, _endereco(cep=cep))
            cache.obter(cep)

    threads = [threading.Thread(target=trabalhar, args=(n * 7,)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(cache) == 50


# --- integração com consulta_cep ------------------------------------------------


def test_desligado_por_padrao(api: respx.MockRouter) -> None:
    rota = simular(api, "viacep", "sucesso")
    consulta_cep(CEP, servicos=["viacep"])
    consulta_cep(CEP, servicos=["viacep"])
    assert rota.call_count == 2
    assert len(CACHE_PADRAO) == 0


def test_acerto_evita_requisicao(api: respx.MockRouter) -> None:
    rota = simular(api, "viacep", "sucesso")
    primeiro = consulta_cep("01001-000", servicos=["viacep"], cache=True)
    segundo = consulta_cep("01.001-000", servicos=["viacep"], cache=True)
    assert rota.call_count == 1
    assert primeiro == segundo
    assert primeiro is not segundo


def test_compartilhado_entre_sync_e_async(api: respx.MockRouter) -> None:
    rota = simular(api, "opencep", "sucesso")
    consulta_cep(CEP, servicos=["opencep"], cache=True)
    endereco = asyncio.run(consulta_cep_async(CEP, servicos=["opencep"], cache=True))
    assert endereco.servico == "opencep"
    assert rota.call_count == 1

    limpar_cache()
    asyncio.run(consulta_cep_async(CEP, servicos=["opencep"], cache=True))
    consulta_cep(CEP, servicos=["opencep"], cache=True)
    assert rota.call_count == 2


def test_limpar_cache(api: respx.MockRouter) -> None:
    rota = simular(api, "viacep", "sucesso")
    consulta_cep(CEP, servicos=["viacep"], cache=True)
    limpar_cache()
    consulta_cep(CEP, servicos=["viacep"], cache=True)
    assert rota.call_count == 2


def test_expiracao_na_consulta() -> None:
    relogio = Relogio()
    cache = CacheLRU(ttl=60, relogio=relogio)
    falso = Falso("f")
    consulta_cep(CEP, servicos=[falso], cache=cache)
    consulta_cep(CEP, servicos=[falso], cache=cache)
    assert len(falso.chamadas) == 1
    relogio.agora = 61
    consulta_cep(CEP, servicos=[falso], cache=cache)
    assert len(falso.chamadas) == 2


def test_nao_guarda_falha_de_rede(api: respx.MockRouter) -> None:
    rota = api.get(url("viacep")).mock(
        side_effect=[httpx.ConnectError("fora"), httpx.Response(500)]
    )
    for _ in range(2):
        with pytest.raises(ServicosIndisponiveisError):
            consulta_cep(CEP, servicos=["viacep"], cache=True)
    assert rota.call_count == 2
    assert len(CACHE_PADRAO) == 0


def test_nao_guarda_nao_encontrado(api: respx.MockRouter) -> None:
    rota = simular(api, "viacep", "nao_encontrado")
    for _ in range(2):
        with pytest.raises(CEPNaoEncontradoError):
            asyncio.run(consulta_cep_async(CEP, servicos=["viacep"], cache=True))
    assert rota.call_count == 2
    assert len(CACHE_PADRAO) == 0


def test_acerto_ignora_servicos_pedidos() -> None:
    # O cache é indexado só pelo CEP (comportamento documentado).
    consulta_cep(CEP, servicos=[Falso("a")], cache=True)
    b = Falso("b")
    assert consulta_cep(CEP, servicos=[b], cache=True).servico == "a"
    assert b.chamadas == []


def test_cep_invalido_nao_consulta_o_cache() -> None:
    with pytest.raises(ValueError):
        consulta_cep("123", cache=True)

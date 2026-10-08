from __future__ import annotations

from collections.abc import Iterator

import pytest
import respx

from consulta_cep import limpar_cache


@pytest.fixture(autouse=True)
def _cache_limpo() -> Iterator[None]:
    limpar_cache()
    yield
    limpar_cache()


@pytest.fixture
def api() -> Iterator[respx.MockRouter]:
    """Intercepta todas as requisições httpx (sync e async)."""
    with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        yield router

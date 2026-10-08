# consulta-cep

Biblioteca que consulta um CEP em várias APIs públicas ao mesmo tempo e devolve
o primeiro endereço obtido.

## Convenções

- Nomes de módulos, classes, funções, variáveis, exceções e mensagens em
  português (ex.: `normalizar_cep`, `CEPNaoEncontradoError`, `servicos.py`).
- Suporte a Python >= 3.10: nada de sintaxe ou APIs exclusivas de versões mais
  novas (ex.: `typing.Self`, `except*`, `tomllib` são 3.11+). Use
  `from __future__ import annotations`.
- Type hints completos; `mypy --strict` precisa passar (`consulta_cep` e `tests`).
- Dependência de runtime: apenas `requests`. A versão fica só em
  `consulta_cep/__init__.py` (`__version__`), lida pelo hatchling.
- `consulta_cep()` nunca retorna `None`: devolve `Endereco` ou lança uma
  exceção de `consulta_cep/excecoes.py`. Parâmetros novos são keyword-only.
- Erros vão para `logging.getLogger("consulta_cep")`; nunca `print()` na
  biblioteca e nunca configurar handlers.
- Toda requisição HTTP tem `timeout`.

## Desenvolvimento

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy
pytest --cov=consulta_cep        # testes simulados (padrão)
pytest -m live                   # testes contra as APIs reais
```

## Testes

- Testes normais **não** acessam a rede: simule as respostas com `responses`
  ou `unittest.mock`.
- Testes que chamam as APIs reais recebem `@pytest.mark.live` (ou
  `pytestmark = pytest.mark.live`). Eles ficam desligados por padrão e rodam
  semanalmente no workflow `.github/workflows/live.yml`.

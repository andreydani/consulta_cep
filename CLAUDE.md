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

## Como adicionar um serviço novo

1. Em `consulta_cep/servicos.py`, crie uma classe `ConsultaCEP<Nome>` que
   herde de `ConsultaCEP`, decorada com `@registrar_servico`, com:
   - `nome`: nome curto, minúsculo e único (ex.: `"viacep"`); é o que vai em
     `Endereco.servico` e no parâmetro `servicos=`;
   - `URL` com o marcador `{cep}` (8 dígitos);
   - `consultar_normalizado(self, cep, *, timeout)`, que chama
     `consulta_cep_https(self.URL, cep, timeout=timeout)` e monta o `Endereco`.
2. Mapeamento: `estado` e `cidade` são obrigatórios (use `res["..."]`, para
   que a falta deles conte como erro do serviço); o resto usa
   `texto_opcional` / `numero_opcional`. O `Endereco` já converte vazio em
   `None`, nome de estado em sigla e formata o CEP.
3. CEP inexistente deve virar `CEPNaoEncontradoError`. HTTP 404 já é tratado
   por `consulta_cep_https`; se a API responder 200 com um corpo de erro (como
   o ViaCEP), detecte isso na classe.
4. Só entre em `SERVICOS_PADRAO` depois de verificado ao vivo.
5. Testes:
   - fixtures em `tests/fixtures/<nome>/`: `sucesso.json` (CEP 01001-000),
     `vazios.json` e `nao_encontrado.json`, no formato
     `{"status": ..., "body": ...}`;
   - adicione o resultado esperado em `ESPERADO_SUCESSO` e `ESPERADO_VAZIOS`
     e o caso em `NAO_ENCONTRADO` (`tests/test_servicos.py`);
   - os testes `live` em `tests/test_live.py` já cobrem todo serviço
     registrado.
6. Documente o serviço no `readme.md`.

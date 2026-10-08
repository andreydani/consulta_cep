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
- Dependência de runtime: apenas `httpx`. A versão fica só em
  `consulta_cep/__init__.py` (`__version__`), lida pelo hatchling.
- `consulta_cep()` nunca retorna `None`: devolve `Endereco` ou lança uma
  exceção de `consulta_cep/excecoes.py`. Parâmetros novos são keyword-only.
- Erros vão para `logging.getLogger("consulta_cep")`; nunca `print()` na
  biblioteca e nunca configurar handlers.
- Toda requisição HTTP tem `timeout`.

## Documentação e versão

- `README.md` (para usuários), `CONTRIBUTING.md` (para contribuidores),
  `CHANGELOG.md` (Keep a Changelog; toda mudança visível entra em
  `[Não lançado]`).
- Publicação: `.github/workflows/publish.yml` roda ao publicar uma release
  `vX.Y.Z` (Trusted Publishing, environment `pypi`); a tag precisa bater com
  `__version__`. Nunca publique, crie tags ou releases sem pedido explícito.

## Desenvolvimento

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy
pytest --cov=consulta_cep        # testes simulados (padrão)
pytest -m live                   # testes contra as APIs reais
```

## Testes

- Testes normais **não** acessam a rede: simule as respostas com `respx`
  (fixture `api` em `tests/conftest.py`) ou `httpx.MockTransport`, e use
  `tests/falsos.py::Falso` para serviços sem HTTP.
- Todo comportamento de `consulta_cep()` vale também para
  `consulta_cep_async()`: em `tests/test_consulta.py`, a fixture `consultar`
  roda o mesmo teste nas duas versões. Testes async usam `asyncio.run` (sem
  pytest-asyncio).
- O cache padrão é limpo antes e depois de cada teste (`tests/conftest.py`).
- Os exemplos do `README.md` são executados por `tests/test_readme.py`
  (blocos `python`, `pycon`, `console` e `bash`). Tudo que o README mostrar
  precisa existir e funcionar; para um bloco ilustrativo que não deve rodar,
  coloque `<!-- readme: não testar -->` na linha anterior.
- Testes que chamam as APIs reais recebem `@pytest.mark.live` (ou
  `pytestmark = pytest.mark.live`). Eles ficam desligados por padrão e rodam
  semanalmente no workflow `.github/workflows/live.yml`.

## Como adicionar um serviço novo

1. Em `consulta_cep/servicos.py`, crie uma classe `ConsultaCEP<Nome>` que
   herde de `ConsultaCEP`, decorada com `@registrar_servico`, com:
   - `nome`: nome curto, minúsculo e único (ex.: `"viacep"`); é o que vai em
     `Endereco.servico` e no parâmetro `servicos=`;
   - `URL` com o marcador `{cep}` (8 dígitos); sobrescreva `montar_url` se
     a URL não for um simples `format`;
   - `converter(self, res, cep)`, que recebe o JSON já validado e monta o
     `Endereco`. Não faça HTTP na classe: `consultar`/`consultar_async` da base
     fazem a requisição (sync com `httpx.Client`, async com `httpx.AsyncClient`)
     e chamam `converter`, então os dois caminhos usam o mesmo parsing.
2. Mapeamento: `estado` e `cidade` são obrigatórios (use `res["..."]`, para
   que a falta deles conte como erro do serviço); o resto usa
   `texto_opcional` / `numero_opcional`. O `Endereco` já converte vazio em
   `None`, nome de estado em sigla e formata o CEP.
3. CEP inexistente deve virar `CEPNaoEncontradoError`. HTTP 404 já é tratado
   pela base; se a API responder 200 com um corpo de erro (como o ViaCEP),
   detecte isso em `converter`.
4. Só entre em `SERVICOS_PADRAO` depois de verificado ao vivo.
5. Testes:
   - fixtures em `tests/fixtures/<nome>/`: `sucesso.json` (CEP 01001-000),
     `vazios.json` e `nao_encontrado.json`, no formato
     `{"status": ..., "body": ...}`;
   - adicione o resultado esperado em `ESPERADO_SUCESSO` e `ESPERADO_VAZIOS`
     e o caso em `NAO_ENCONTRADO` (`tests/test_servicos.py`);
   - os testes `live` em `tests/test_live.py` já cobrem todo serviço
     registrado.
6. Documente o serviço na tabela de serviços do `README.md` e registre a
   novidade em `CHANGELOG.md` (seção `[Não lançado]`).

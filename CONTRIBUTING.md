# Contribuindo com o consulta-cep

Obrigado pelo interesse! Este guia mostra como preparar o ambiente, rodar os
testes e adicionar uma nova API de CEP.

## Ambiente

Requer Python 3.10 ou mais recente.

```bash
git clone https://github.com/andreydani/consulta_cep.git
cd consulta_cep
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Convenções

- Código, mensagens e documentação em português (`normalizar_cep`,
  `CEPNaoEncontradoError`).
- Compatível com Python 3.10: nada de `typing.Self`, `except*`, `tomllib`,
  `asyncio.TaskGroup` ou `asyncio.timeout`.
- Type hints completos; `mypy --strict` precisa passar.
- A única dependência de runtime é `httpx`. Não adicione outras.
- `consulta_cep()` nunca devolve `None`; erros são exceções de
  `consulta_cep/excecoes.py`. Parâmetros novos são keyword-only.
- Nada de `print()` na biblioteca: use `logging.getLogger("consulta_cep")`.

## Testes e lint

```bash
ruff check .
ruff format --check .
mypy
pytest --cov=consulta_cep
```

Os mesmos passos rodam no CI, de Python 3.10 a 3.14.

- **Testes normais não acessam a rede.** Simule as respostas com
  [respx](https://lundberg.github.io/respx/) (fixture `api` em
  `tests/conftest.py`) ou `httpx.MockTransport`.
- **Testes contra as APIs reais** recebem o marcador `live` e ficam
  desligados por padrão. Rode com `pytest -m live`. Eles também rodam toda
  semana no workflow "APIs reais", para detectar quando alguma API muda ou sai
  do ar.
- Comportamentos de `consulta_cep()` também valem para
  `consulta_cep_async()`; a fixture `consultar` em `tests/test_consulta.py`
  roda o mesmo teste nas duas versões.
- **Os exemplos do README são testados** (`tests/test_readme.py`): blocos
  `python` são executados (as linhas após `# Saída:` são comparadas com o que
  foi impresso), blocos `pycon` rodam como doctest e blocos `console` têm a
  saída conferida. Ao mudar o README, rode `pytest tests/test_readme.py`.

## Adicionando uma nova API de CEP

1. Abra uma issue com o modelo "Nova API de CEP", com a documentação e um
   exemplo de resposta de sucesso e de CEP inexistente.
2. Em `consulta_cep/servicos.py`, crie a classe:

   ```python
   @registrar_servico
   class ConsultaCEPExemplo(ConsultaCEP):
       nome = "exemplo"  # curto, minúsculo e único
       URL = "https://api.exemplo.com.br/cep/{cep}"  # {cep}: 8 dígitos

       def converter(self, res: dict[str, Any], cep: str) -> Endereco:
           return Endereco(
               servico=self.nome,
               estado=str(res["uf"]),  # obrigatório
               cidade=str(res["cidade"]),  # obrigatório
               bairro=texto_opcional(res.get("bairro")),
               logradouro=texto_opcional(res.get("logradouro")),
               cep=str(res.get("cep") or cep),
               ibge=texto_opcional(res.get("ibge")),
           )
   ```

   - A classe base faz a requisição (sync e async) e chama `converter`.
     Sobrescreva `montar_url` se a URL não for um simples `format`.
   - HTTP 404 já vira `CEPNaoEncontradoError`. Se a API responder 200 com um
     corpo de erro (como o ViaCEP), lance `CEPNaoEncontradoError(cep)` em
     `converter`.
   - O `Endereco` já converte textos vazios em `None`, nome de estado em
     sigla e formata o CEP.
3. Crie as fixtures em `tests/fixtures/<nome>/`, no formato
   `{"status": <HTTP>, "body": <JSON>}`: `sucesso.json` (CEP 01001-000),
   `vazios.json` (campos vazios ou nulos) e `nao_encontrado.json`.
4. Em `tests/test_servicos.py`, adicione o resultado esperado em
   `ESPERADO_SUCESSO` e `ESPERADO_VAZIOS` e o caso em `NAO_ENCONTRADO`. Os
   testes `live` já cobrem todo serviço registrado; rode `pytest -m live -k
   <nome>` para conferir contra a API real.
5. Só coloque o serviço em `SERVICOS_PADRAO` depois de verificado ao vivo.
6. Atualize a tabela de serviços do `README.md` e a seção `[Não lançado]` do
   `CHANGELOG.md`.

## Pull requests

- Um assunto por PR, com testes.
- Descreva mudanças de comportamento e registre-as no `CHANGELOG.md`.
- O CI precisa passar (ruff, mypy e pytest em todas as versões de Python).

## Publicação (mantenedores)

A publicação no PyPI é feita pelo workflow `publish.yml` ao publicar uma
release no GitHub com a tag `vX.Y.Z`, que precisa ser igual a
`__version__` em `consulta_cep/__init__.py`.

# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adota o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [1.0.0] - 2026-10-08

Primeira versão estável. Reescreve a biblioteca com exceções próprias, novas
APIs de CEP, versão assíncrona, cache e uma linha de comando completa. Veja
"Migrando da 0.2" no [README](README.md#migrando-da-02).

### ⚠️ Mudanças incompatíveis

- Requer Python 3.10 ou mais recente (antes: 3.6).
- A dependência `requests` foi trocada por `httpx`. Erros de rede guardados em
  `ServicosIndisponiveisError.erros` agora são exceções do httpx.
- `consulta_cep()` nunca devolve `None`: lança `CEPInvalidoError`,
  `CEPNaoEncontradoError` ou `ServicosIndisponiveisError` (todas herdam de
  `ConsultaCEPError`; `CEPInvalidoError` também herda de `ValueError`).
- Os erros não são mais impressos com `print()`; vão para o logger
  `consulta_cep`.
- `Endereco.servico` agora é o nome curto do serviço (`"brasilapi"`,
  `"postmon"`), em vez de `"BrasilAPI"`/`"PostMon"`.
- `Endereco.bairro` e `Endereco.logradouro` podem ser `None` quando o serviço
  não os informa.
- `Endereco.estado` é sempre a sigla da UF; criar um `Endereco` com uma UF
  inexistente lança `ValueError`.
- `str(Endereco)` mantém os acentos (`ensure_ascii=False`) e inclui os campos
  novos.
- Lista padrão de serviços: BrasilAPI (v2), ViaCEP, OpenCEP e AwesomeAPI. O
  Postmon saiu da lista padrão.
- Subclasses de `ConsultaCEP` implementam `converter(dados, cep)` e definem
  `nome` e `URL`; a classe base faz as requisições (sync e async).
- Linha de comando: saída em texto por padrão (`--formato json` para JSON),
  erros na saída de erro e códigos de saída 1 (não encontrado), 2 (CEP
  inválido) e 3 (serviços indisponíveis).

### Adicionado

- Exceções `ConsultaCEPError`, `CEPInvalidoError`, `CEPNaoEncontradoError` e
  `ServicosIndisponiveisError` (com o atributo `erros`, por serviço).
- Novos serviços: ViaCEP, OpenCEP e AwesomeAPI; registro de serviços por nome
  e `servicos_disponiveis()`.
- Campos novos em `Endereco`: `cep`, `complemento`, `ibge`, `ddd`, `latitude`
  e `longitude`; métodos `to_dict()` e `to_json()`.
- Parâmetros keyword-only em `consulta_cep()`: `timeout` (padrão 5 s),
  `servicos`, `estrategia` (`"concorrente"` ou `"sequencial"`), `client` e
  `cache`.
- `consulta_cep_async()`, com os mesmos parâmetros e exceções; na estratégia
  concorrente, cancela as consultas restantes após o primeiro sucesso.
- Cache em memória opcional (`cache=True`): LRU com validade de 24 h e até
  1024 CEPs, seguro entre threads e compartilhado entre sync e async;
  `CacheLRU` e `limpar_cache()`.
- Linha de comando com vários CEPs e as opções `--servico`, `--estrategia`,
  `--timeout`, `--formato` e `--version`.
- CEP aceito nos formatos `01001-000`, `01001000` e `01.001-000`.
- Type hints completos e `py.typed`.

### Corrigido

- O comando `consulta-cep` instalado pelo pip apontava para um módulo
  inexistente.
- A consulta esperava o serviço mais lento terminar mesmo com outro já pronto.
- Requisições sem timeout.
- `Endereco.__str__` escapava os acentos.
- Respostas 2xx diferentes de 200 eram tratadas como falha.
- Importar `consulta_cep.__main__` executava a linha de comando.

### Alterado

- Postmon passou a usar HTTPS.
- BrasilAPI passou da v1 para a v2.
- Empacotamento com `pyproject.toml` (hatchling) no lugar de `setup.py`.
- Publicação no PyPI via Trusted Publishing.

## [0.2.0]

Versão anterior, publicada no PyPI. Consultava BrasilAPI e Postmon.

[Não lançado]: https://github.com/andreydani/consulta_cep/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/andreydani/consulta_cep/releases/tag/v1.0.0
[0.2.0]: https://pypi.org/project/consulta-cep/0.2.0/

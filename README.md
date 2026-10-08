# consulta-cep

**Endereço a partir do CEP em uma linha, consultando várias APIs públicas
brasileiras ao mesmo tempo e devolvendo a primeira que responder.**

[![PyPI](https://img.shields.io/pypi/v/consulta-cep)](https://pypi.org/project/consulta-cep/)
[![Python](https://img.shields.io/pypi/pyversions/consulta-cep)](https://pypi.org/project/consulta-cep/)
[![CI](https://github.com/andreydani/consulta_cep/actions/workflows/python-package.yml/badge.svg)](https://github.com/andreydani/consulta_cep/actions/workflows/python-package.yml)
[![Licença: MIT](https://img.shields.io/github/license/andreydani/consulta_cep)](https://github.com/andreydani/consulta_cep/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/consulta-cep/month)](https://pepy.tech/project/consulta-cep)

## Por que usar

- **Várias APIs gratuitas, sem chave:** BrasilAPI, ViaCEP, OpenCEP e
  AwesomeAPI (e Postmon, opcional).
- **Fallback automático:** se uma API cair, demorar ou não conhecer o CEP, a
  resposta vem de outra. Por padrão todas são consultadas ao mesmo tempo e
  vale a primeira que responder.
- **Síncrona e assíncrona:** `consulta_cep()` e `consulta_cep_async()`, com
  os mesmos parâmetros.
- **Tipada:** `py.typed`, verificada com `mypy --strict`.
- **Uma dependência só:** [httpx](https://www.python-httpx.org/).
- **Erros claros:** exceções específicas para CEP inválido, CEP inexistente e
  serviços fora do ar, em vez de `None`.
- **Extras:** cache em memória opcional, cliente `httpx` próprio (proxy,
  conexões reaproveitadas) e linha de comando.

## Instalação

```bash
pip install consulta-cep
```

Requer Python 3.10 ou mais recente.

## Uso rápido

```python
from consulta_cep import consulta_cep

endereco = consulta_cep("01001-000")
print(f"{endereco.logradouro}, {endereco.bairro} - {endereco.cidade}/{endereco.estado}")
# Saída:
# Praça da Sé, Sé - São Paulo/SP
```

O CEP pode vir como `01001-000`, `01001000` ou `01.001-000` (espaços nas
pontas são ignorados).

### O endereço

`consulta_cep()` devolve um `Endereco`:

```pycon
>>> from consulta_cep import consulta_cep
>>> endereco = consulta_cep("01001-000", servicos="viacep")
>>> endereco
Endereco(servico='viacep', estado='SP', cidade='São Paulo', bairro='Sé', logradouro='Praça da Sé', cep='01001-000', complemento='lado ímpar', ibge='3550308', ddd='11', latitude=None, longitude=None)
>>> endereco.to_dict()["ibge"]
'3550308'
>>> print(endereco.to_json())
{"servico": "viacep", "estado": "SP", "cidade": "São Paulo", "bairro": "Sé", "logradouro": "Praça da Sé", "cep": "01001-000", "complemento": "lado ímpar", "ibge": "3550308", "ddd": "11", "latitude": null, "longitude": null}
```

| Campo | Tipo | Observação |
| --- | --- | --- |
| `servico` | `str` | Nome do serviço que respondeu. |
| `estado` | `str` | Sempre a sigla da UF (`"SP"`). |
| `cidade` | `str` | |
| `bairro` | `str \| None` | |
| `logradouro` | `str \| None` | |
| `cep` | `str \| None` | Formato `12345-678`. |
| `complemento` | `str \| None` | |
| `ibge` | `str \| None` | Código IBGE do município. |
| `ddd` | `str \| None` | |
| `latitude`, `longitude` | `float \| None` | |

Campos que o serviço não informa (ou informa vazios) ficam `None`.
`str(endereco)` devolve o mesmo JSON de `to_json()`.

## Serviços

| Nome | API | Campos além de estado, cidade, bairro, logradouro e CEP | Na lista padrão |
| --- | --- | --- | --- |
| `brasilapi` | [BrasilAPI](https://brasilapi.com.br/docs#tag/CEP-V2) (`brasilapi.com.br/api/cep/v2/{cep}`) | `latitude`, `longitude` (quando disponíveis) | sim |
| `viacep` | [ViaCEP](https://viacep.com.br) (`viacep.com.br/ws/{cep}/json/`) | `complemento`, `ibge`, `ddd` | sim |
| `opencep` | [OpenCEP](https://opencep.com) (`opencep.com/v1/{cep}`) | `complemento`, `ibge` | sim |
| `awesomeapi` | [AwesomeAPI](https://docs.awesomeapi.com.br/api-cep) (`cep.awesomeapi.com.br/json/{cep}`) | `ibge`, `ddd`, `latitude`, `longitude` | sim |
| `postmon` | [Postmon](https://postmon.com.br) (`api.postmon.com.br/v1/cep/{cep}`) | `complemento`, `ibge` | não |

```pycon
>>> from consulta_cep import SERVICOS_PADRAO, servicos_disponiveis
>>> servicos_disponiveis()
['brasilapi', 'viacep', 'opencep', 'awesomeapi', 'postmon']
>>> SERVICOS_PADRAO
('brasilapi', 'viacep', 'opencep', 'awesomeapi')
```

## Escolhendo serviços e estratégia

```python
from consulta_cep import consulta_cep

# Só alguns serviços, na ordem de preferência (nomes ou instâncias)
endereco = consulta_cep("01001-000", servicos=["viacep", "awesomeapi"])

# Um por vez, na ordem, parando no primeiro sucesso: poupa requisições
endereco = consulta_cep(
    "01001-000",
    servicos=["viacep", "brasilapi", "postmon"],
    estrategia="sequencial",
)

# Tempo máximo de cada requisição, em segundos (padrão: 5)
endereco = consulta_cep("01001-000", timeout=2)
```

| Estratégia | Comportamento |
| --- | --- |
| `"concorrente"` (padrão) | Consulta todos ao mesmo tempo e devolve o primeiro que responder com sucesso, sem esperar os demais. |
| `"sequencial"` | Tenta um por vez, na ordem de `servicos`, e para no primeiro sucesso. |

## Tratando erros

`consulta_cep()` nunca devolve `None`: ou devolve um `Endereco`, ou lança uma
exceção. Todas herdam de `ConsultaCEPError`.

| Exceção | Quando |
| --- | --- |
| `CEPInvalidoError` (também é `ValueError`) | O CEP não tem um formato válido. Nenhuma requisição é feita. |
| `CEPNaoEncontradoError` | Algum serviço respondeu que o CEP não existe e nenhum devolveu endereço. |
| `ServicosIndisponiveisError` | Nenhum serviço respondeu; o atributo `erros` traz o erro de cada um. |

```python
from consulta_cep import (
    CEPInvalidoError,
    CEPNaoEncontradoError,
    ServicosIndisponiveisError,
    consulta_cep,
)

for cep in ["01001-000", "99999-999", "123"]:
    try:
        endereco = consulta_cep(cep)
    except CEPInvalidoError:
        print(f"{cep}: formato inválido")
    except CEPNaoEncontradoError:
        print(f"{cep}: CEP não existe")
    except ServicosIndisponiveisError as erro:
        for servico, falha in erro.erros.items():
            print(f"{cep}: {servico} falhou ({falha})")
    else:
        print(f"{cep}: {endereco.cidade}/{endereco.estado}")
# Saída:
# 01001-000: São Paulo/SP
# 99999-999: CEP não existe
# 123: formato inválido
```

## Assíncrono (asyncio)

`consulta_cep_async()` tem os mesmos parâmetros e exceções. Na estratégia
concorrente, devolve o primeiro sucesso e cancela as consultas que ainda não
terminaram.

```python
import asyncio

from consulta_cep import consulta_cep_async


async def main() -> None:
    endereco = await consulta_cep_async("01001-000")
    print(endereco.cidade)


asyncio.run(main())
# Saída:
# São Paulo
```

## Cache

Desligado por padrão. Com `cache=True`, os endereços encontrados ficam num
cache em memória (LRU, até 1024 CEPs, válidos por 24 horas), seguro entre
threads e compartilhado entre `consulta_cep()` e `consulta_cep_async()`.
Falhas e CEPs não encontrados nunca são guardados.

```python
from consulta_cep import CacheLRU, consulta_cep, limpar_cache

consulta_cep("01001-000", cache=True)  # consulta os serviços
consulta_cep("01001-000", cache=True)  # vem do cache, sem requisição
limpar_cache()

# Cache próprio, com outro tamanho e validade (em segundos)
meu_cache = CacheLRU(maximo=100, ttl=60 * 60)
consulta_cep("01001-000", cache=meu_cache)
```

O cache é indexado só pelo CEP: um acerto devolve o endereço guardado, seja
qual for o serviço que o obteve.

## Usando seu próprio cliente httpx

Passe um `httpx.Client` (ou `httpx.AsyncClient` na versão assíncrona) para
reaproveitar conexões entre consultas ou configurar proxy, cabeçalhos e
certificados. O cliente não é fechado pela biblioteca. O `timeout` da consulta
vale para cada requisição, mesmo que o cliente tenha outro configurado.

```python
import httpx

from consulta_cep import consulta_cep

with httpx.Client(proxy="http://proxy.empresa.local:3128") as client:
    endereco = consulta_cep("01001-000", client=client)
```

```python
import asyncio

import httpx

from consulta_cep import consulta_cep_async


async def consultar_varios(ceps: list[str]) -> None:
    async with httpx.AsyncClient(headers={"User-Agent": "minha-app/1.0"}) as client:
        enderecos = await asyncio.gather(
            *(consulta_cep_async(cep, client=client) for cep in ceps)
        )
    for endereco in enderecos:
        print(endereco.cep, endereco.cidade)


asyncio.run(consultar_varios(["01001-000", "01.001-000"]))
# Saída:
# 01001-000 São Paulo
# 01001-000 São Paulo
```

## Logs

As falhas de cada serviço são registradas no logger `consulta_cep` do módulo
`logging` (nível `WARNING`; CEP não encontrado em `INFO`). Se a sua aplicação
não configura logging, o Python mostra esses avisos na saída de erro. Para
escondê-los:

```python
import logging

logging.getLogger("consulta_cep").setLevel(logging.ERROR)
```

## Linha de comando

Instalar o pacote também instala o comando `consulta-cep` (equivalente a
`python -m consulta_cep`).

```console
$ consulta-cep 01001-000 --servico viacep
CEP: 01001-000
Logradouro: Praça da Sé
Complemento: lado ímpar
Bairro: Sé
Cidade: São Paulo
Estado: SP
IBGE: 3550308
DDD: 11
Serviço: viacep
$ consulta-cep 01001000 --servico viacep --formato json
{"servico": "viacep", "estado": "SP", "cidade": "São Paulo", "bairro": "Sé", "logradouro": "Praça da Sé", "cep": "01001-000", "complemento": "lado ímpar", "ibge": "3550308", "ddd": "11", "latitude": null, "longitude": null}
$ consulta-cep 99999-999 --servico viacep
99999-999: CEP não encontrado: 99999999.
$ echo $?
1
```

```bash
consulta-cep 01001-000 01.001-000 --formato json   # vários CEPs: um JSON por linha
consulta-cep 01001-000 -s viacep -s brasilapi --estrategia sequencial
consulta-cep 01001-000 --timeout 2
python -m consulta_cep 01001-000
```

| Opção | |
| --- | --- |
| `-s`, `--servico` | Serviço a consultar; repita para usar mais de um, na ordem de preferência. |
| `-e`, `--estrategia` | `concorrente` (padrão) ou `sequencial`. |
| `-t`, `--timeout` | Tempo máximo de cada requisição, em segundos (padrão: 5). |
| `-f`, `--formato` | `texto` (padrão) ou `json` (um objeto por linha). |
| `--version` | Mostra a versão. |

Erros vão para a saída de erro (em JSON, com `--formato json`). Códigos de
saída: `0` sucesso, `1` CEP não encontrado, `2` CEP inválido, `3` serviços
indisponíveis. Com vários CEPs, vale o maior código.

## Migrando da 0.2

A 1.0 tem mudanças incompatíveis. As principais:

- **Python 3.10 ou mais recente** (antes: 3.6).
- **`httpx` no lugar de `requests`.** Erros de rede guardados em
  `ServicosIndisponiveisError.erros` são exceções do httpx
  (`httpx.HTTPStatusError`, `httpx.ConnectError`, `httpx.TimeoutException`…).
- **Exceções no lugar de `None`.** Antes, se nenhum serviço respondia,
  `consulta_cep()` imprimia o erro e devolvia `None`:

  <!-- readme: não testar -->
  ```python
  # 0.2
  endereco = consulta_cep("01001-000")
  if endereco is None:
      ...
  ```

  Agora:

  <!-- readme: não testar -->
  ```python
  # 1.0
  try:
      endereco = consulta_cep("01001-000")
  except ConsultaCEPError:
      ...
  ```

  CEP inválido continua sendo `ValueError` (`CEPInvalidoError` herda dele).
- **Sem `print()`.** As falhas de cada serviço vão para o logger
  `consulta_cep` (veja [Logs](#logs)).
- **`Endereco`:**
  - `servico` passa a ser o nome curto (`"brasilapi"`, `"postmon"`), não
    mais `"BrasilAPI"`/`"PostMon"`;
  - `bairro` e `logradouro` podem ser `None`;
  - novos campos `cep`, `complemento`, `ibge`, `ddd`, `latitude` e
    `longitude` (no fim, com padrão `None`; a ordem dos campos antigos não
    mudou);
  - `str(endereco)` mantém os acentos e inclui os campos novos;
  - `estado` é validado: criar um `Endereco` com uma UF inexistente lança
    `ValueError`.
- **Serviços:** a lista padrão agora é BrasilAPI (v2), ViaCEP, OpenCEP e
  AwesomeAPI. O Postmon passou a usar HTTPS e saiu da lista padrão
  (`servicos=["postmon"]` para usá-lo).
- **Serviços próprios:** subclasses de `ConsultaCEP` implementam
  `converter(dados, cep)` (e definem `nome` e `URL`) em vez de `consultar`.
- **Linha de comando:** a saída padrão agora é texto (use `--formato json`
  para JSON); erros vão para a saída de erro com código de saída diferente de
  zero.

O [CHANGELOG](https://github.com/andreydani/consulta_cep/blob/main/CHANGELOG.md) tem a lista completa.

## Contribuindo

Contribuições são bem-vindas, inclusive novas APIs de CEP. Veja o
[CONTRIBUTING.md](https://github.com/andreydani/consulta_cep/blob/main/CONTRIBUTING.md) para preparar o ambiente, rodar os testes e
adicionar um serviço. Encontrou um problema? Abra uma
[issue](https://github.com/andreydani/consulta_cep/issues/new/choose).

## Licença

[MIT](https://github.com/andreydani/consulta_cep/blob/main/LICENSE)

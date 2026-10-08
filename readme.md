# Consulta CEP

Biblioteca para consulta de endereços a partir de CEP usando serviços variados.
Veja no PyPI: https://pypi.org/project/consulta-cep/

## Instalação

Você pode instalar a biblioteca via pip:

```bash
pip install consulta-cep
```

## Uso em programas

```python
from consulta_cep import consulta_cep

endereco = consulta_cep("01001-000")  # também aceita "01001000" e "01.001-000"
print(endereco)
# {"servico": "viacep", "estado": "SP", "cidade": "São Paulo", "bairro": "Sé",
#  "logradouro": "Praça da Sé", "cep": "01001-000", "complemento": "lado ímpar",
#  "ibge": "3550308", "ddd": "11", "latitude": null, "longitude": null}

endereco.to_dict()  # dicionário
endereco.to_json()  # JSON (com acentos)

# Tempo máximo de cada requisição, em segundos (padrão: 5)
consulta_cep("01001-000", timeout=2)

# Escolher os serviços (nomes ou instâncias), na ordem de preferência
consulta_cep("01001-000", servicos=["viacep", "awesomeapi"])

# Tentar um por vez, parando no primeiro sucesso (poupa requisições)
consulta_cep("01001-000", servicos=["viacep", "brasilapi"], estrategia="sequencial")
```

### Endereço

| Campo | Observação |
| --- | --- |
| `servico` | Nome do serviço que respondeu. |
| `estado` | Sempre a sigla da UF (`"SP"`). |
| `cidade`, `bairro`, `logradouro`, `complemento` | |
| `cep` | Formato `12345-678`. |
| `ibge` | Código IBGE do município. |
| `ddd` | |
| `latitude`, `longitude` | `float`. |

Campos que o serviço não informa (ou informa vazios) ficam `None`.

### Serviços

| Nome | API | Na lista padrão |
| --- | --- | --- |
| `brasilapi` | [BrasilAPI](https://brasilapi.com.br) (v2) | sim |
| `viacep` | [ViaCEP](https://viacep.com.br) | sim |
| `opencep` | [OpenCEP](https://opencep.com) | sim |
| `awesomeapi` | [AwesomeAPI](https://docs.awesomeapi.com.br/api-cep) | sim |
| `postmon` | [Postmon](https://postmon.com.br) | não |

`servicos_disponiveis()` devolve a lista de nomes.

Por padrão (`estrategia="concorrente"`), a consulta é feita em todos os
serviços ao mesmo tempo e devolve o resultado do primeiro que responder com
sucesso. Em caso de erro, `consulta_cep()` lança uma
exceção (todas herdam de `ConsultaCEPError`):

| Exceção | Quando |
| --- | --- |
| `CEPInvalidoError` (também `ValueError`) | O CEP não tem um formato válido. |
| `CEPNaoEncontradoError` | Os serviços responderam, mas o CEP não existe. |
| `ServicosIndisponiveisError` | Nenhum serviço respondeu; o atributo `erros` traz o erro de cada um. |

```python
from consulta_cep import CEPNaoEncontradoError, ConsultaCEPError, consulta_cep

try:
    endereco = consulta_cep("99999-999")
except CEPNaoEncontradoError:
    ...
except ConsultaCEPError:
    ...
```

Os erros de cada serviço são registrados no logger `consulta_cep`, do módulo
`logging`.

### Assíncrono (asyncio)

`consulta_cep_async()` tem os mesmos parâmetros e exceções. Na estratégia
concorrente, devolve o primeiro sucesso e cancela as consultas restantes.

```python
import asyncio

from consulta_cep import consulta_cep_async

endereco = asyncio.run(consulta_cep_async("01001-000"))
```

### Reaproveitando conexões (`client`)

Passe um `httpx.Client` (ou `httpx.AsyncClient` na versão assíncrona) para
reaproveitar conexões ou configurar proxy, certificados etc. O cliente não é
fechado pela biblioteca.

```python
import httpx

from consulta_cep import consulta_cep

with httpx.Client(proxy="http://proxy.local:8080") as client:
    for cep in ["01001-000", "20040-020"]:
        print(consulta_cep(cep, client=client))
```

### Cache

Desligado por padrão. Com `cache=True`, os endereços encontrados ficam num
cache em memória (LRU, até 1024 CEPs, válidos por 24 horas), compartilhado
entre `consulta_cep()` e `consulta_cep_async()` e seguro entre threads. Falhas
e CEPs não encontrados nunca são guardados. O cache é indexado só pelo CEP: um
acerto devolve o endereço guardado, seja qual for o serviço que o obteve.

```python
from consulta_cep import CacheLRU, consulta_cep, limpar_cache

consulta_cep("01001-000", cache=True)  # consulta os serviços
consulta_cep("01001-000", cache=True)  # vem do cache
limpar_cache()

# Cache próprio, com outro tamanho e validade (em segundos)
meu_cache = CacheLRU(maximo=100, ttl=3600)
consulta_cep("01001-000", cache=meu_cache)
```

## Linha de comando

```bash
consulta-cep 01001-000
# ou: python -m consulta_cep 01001-000

CEP: 01001-000
Logradouro: Praça da Sé
Complemento: lado ímpar
Bairro: Sé
Cidade: São Paulo
Estado: SP
IBGE: 3550308
DDD: 11
Serviço: viacep
```

```bash
consulta-cep 01001-000 20040-020 --formato json   # um objeto JSON por linha
consulta-cep 01001-000 -s viacep -s brasilapi --estrategia sequencial
consulta-cep 01001-000 --timeout 2
consulta-cep --version
```

| Opção | |
| --- | --- |
| `-s`, `--servico` | Serviço a consultar; repita para usar mais de um, na ordem de preferência. |
| `-e`, `--estrategia` | `concorrente` (padrão) ou `sequencial`. |
| `-t`, `--timeout` | Tempo máximo de cada requisição, em segundos (padrão: 5). |
| `-f`, `--formato` | `texto` (padrão) ou `json`. |
| `--version` | Mostra a versão. |

Erros vão para a saída de erro (em JSON com `--formato json`). Códigos de
saída: `0` sucesso, `1` CEP não encontrado, `2` CEP inválido, `3` serviços
indisponíveis. Com vários CEPs, vale o maior código.

## Desenvolvimento

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy
pytest            # testes com respostas simuladas
pytest -m live    # testes contra as APIs reais
```
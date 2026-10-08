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

## Uso utilitário

Você pode executar como utilitário:

```bash
consulta-cep 01001-000
# ou: python -m consulta_cep 01001-000

{"servico": "brasilapi", "estado": "SP", "cidade": "São Paulo", "bairro": "Sé", "logradouro": "Praça da Sé", "cep": "01001-000", "complemento": null, "ibge": null, "ddd": null, "latitude": -23.5502, "longitude": -46.6339}
```

Em caso de erro, uma mensagem `{"erro": ...}` é escrita na saída de erro e o
código de saída é 2 (CEP inválido) ou 1 (CEP não encontrado ou serviços
indisponíveis).

## Desenvolvimento

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy
pytest            # testes com respostas simuladas
pytest -m live    # testes contra as APIs reais
```
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

endereco = consulta_cep("05010-000")  # também aceita "05010000" e "05.010-000"
print(endereco)
# {"servico": "BrasilAPI", "estado": "SP", "cidade": "São Paulo", "bairro": "Perdizes", "logradouro": "Rua Caiubi"}

# Tempo máximo de cada requisição, em segundos (padrão: 5)
endereco = consulta_cep("05010-000", timeout=2)
```

A consulta é feita em todos os serviços ao mesmo tempo e devolve o resultado do
primeiro que responder com sucesso. Em caso de erro, `consulta_cep()` lança uma
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

{"servico": "BrasilAPI", "estado": "SP", "cidade": "São Paulo", "bairro": "Sé", "logradouro": "Praça da Sé"}
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
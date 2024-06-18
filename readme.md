# Consulta CEP

Biblioteca para consulta de endereços a partir de CEP usando serviços variados.
Veja no PyPI: https://pypi.org/project/consulta-cep/

## Instalação

Você pode instalar a biblioteca via pip:

```bash
pip install consulta-cep
```

## Uso em programas

```bash
from consulta_cep import consulta_cep
endereco = consulta_cep('05010-000')
print(endereco)
Endereco(servico='BrasilAPI', estado='SP', cidade='São Paulo', bairro='Perdizes', logradouro='Rua Caiubi')
```

## Uso utilitário

Você pode executar como utilitário:

```bash
python -m consulta_cep 01001-000

{"servico": "BrasilAPI", "estado": "SP", "cidade": "S\u00e3o Paulo", "bairro": "S\u00e9", "logradouro": "Pra\u00e7a da S\u00e9"}
```
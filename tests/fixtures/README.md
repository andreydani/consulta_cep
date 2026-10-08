# Fixtures

Uma pasta por serviço (o nome é o `nome` do serviço). Cada arquivo JSON tem o
formato `{"status": <HTTP>, "body": <corpo da resposta>}`.

- `sucesso.json`: resposta para o CEP 01001-000 (Praça da Sé, São Paulo/SP).
- `nao_encontrado*.json`: resposta para um CEP que não existe.
- `vazios.json`: resposta de sucesso com campos vazios ou nulos.

Os formatos vêm da documentação de cada API e ainda não foram conferidos ao
vivo; os testes `live` (`pytest -m live`) servem para isso.

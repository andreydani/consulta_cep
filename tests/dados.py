from __future__ import annotations

CEP = "01001000"

RESPOSTA_BRASILAPI = {
    "cep": CEP,
    "state": "SP",
    "city": "São Paulo",
    "neighborhood": "Sé",
    "street": "Praça da Sé",
    "service": "open-cep",
}

RESPOSTA_POSTMON = {
    "cep": CEP,
    "estado": "SP",
    "cidade": "São Paulo",
    "bairro": "Sé",
    "logradouro": "Praça da Sé",
    "estado_info": {"nome": "São Paulo"},
}

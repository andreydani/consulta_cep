import re
import requests


def validar_cep(cep: str) -> bool:
    padrao = re.compile(r'^\d{5}-?\d{3}$')
    if not padrao.match(cep):
        raise ValueError("CEP inválido. Deve seguir o formato 12345-678 ou 12345678.")
    return True


def sanitizar_cep(cep: str) -> str:
    return cep.replace("-", "")


def consulta_cep_https(url : str, cep : str) -> dict:
    url = url.format(cep=cep)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

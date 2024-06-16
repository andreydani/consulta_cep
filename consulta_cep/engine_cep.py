import json
import dataclasses

from .util import validar_cep, sanitizar_cep


@dataclasses.dataclass
class Endereco:
    servico: str
    estado: str
    cidade: str
    bairro: str
    logradouro: str

    def __str__(self):
        return json.dumps(dataclasses.asdict(self))


class ConsultaCEP(object):
    def consultar(self, cep: str) -> Endereco:
        """Método a ser implementado pelas subclasses"""
        pass

    def _validar_cep(self, cep: str) -> str:
        validar_cep(cep)
        return sanitizar_cep(cep)

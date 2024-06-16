from .engine_cep import ConsultaCEP, Endereco
from .util import consulta_cep_https


class ConsultaCEPBrasilAPI(ConsultaCEP):
    URL = "https://brasilapi.com.br/api/cep/v1/{cep}"
    def consultar(self, cep):
        cep = self._validar_cep(cep)
        res = consulta_cep_https(self.URL, cep)
        return Endereco(
            servico="BrasilAPI",
            bairro=res['neighborhood'],
            estado=res['state'],
            logradouro=res['street'],
            cidade=res['city']
        )


class ConsultaCEPPostmon(ConsultaCEP):
    URL = "http://api.postmon.com.br/v1/cep/{cep}"
    def consultar(self, cep):
        cep = self._validar_cep(cep)
        res = consulta_cep_https(self.URL, cep)
        return Endereco(
            servico="PostMon",
            bairro=res['bairro'],
            estado=res['estado'],
            logradouro=res['logradouro'],
            cidade=res['cidade']
        )


SERVICOS_CEP = [ConsultaCEPPostmon(), ConsultaCEPBrasilAPI()]

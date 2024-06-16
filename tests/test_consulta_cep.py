import unittest
from consulta_cep.engine_cep import Endereco
from consulta_cep.servicos import ConsultaCEPPostmon, ConsultaCEPBrasilAPI


class TestConsultaCEP(unittest.TestCase):
    def test_consulta_postmon(self):
        resultado = ConsultaCEPPostmon().consultar('01001-000')
        self.assertIsInstance(resultado, Endereco)
        self.assertEqual(resultado.estado, "SP")
        self.assertEqual(resultado.cidade, "São Paulo")
        self.assertEqual(resultado.bairro, "Sé")
        self.assertEqual(resultado.logradouro, "Praça da Sé")

    def test_consulta_brasilapi(self):
        resultado = ConsultaCEPBrasilAPI().consultar('01001-000')
        self.assertIsInstance(resultado, Endereco)
        self.assertEqual(resultado.estado, "SP")
        self.assertEqual(resultado.cidade, "São Paulo")
        self.assertEqual(resultado.bairro, "Sé")
        self.assertEqual(resultado.logradouro, "Praça da Sé")


if __name__ == "__main__":
    unittest.main()

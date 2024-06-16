import unittest
from consulta_cep.servicos import ConsultaCEPPostmon, ConsultaCEPBrasilAPI


class TestConsultaCEP(unittest.TestCase):
    def test_consulta_postmon(self):
        resultado = ConsultaCEPPostmon().consultar('05010040')
        self.assertIsInstance(resultado, dict)
        self.assertIn('bairro', resultado)

    def test_consulta_brasilapi(self):
        resultado = ConsultaCEPBrasilAPI().consultar('05010040')
        self.assertIsInstance(resultado, dict)
        self.assertIn('bairro', resultado)


if __name__ == "__main__":
    unittest.main()

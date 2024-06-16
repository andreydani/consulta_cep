import concurrent.futures
from .servicos import SERVICOS_CEP
import argparse


def consulta_concorrente(cep):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futuros = {executor.submit(servico.consultar, cep): servico for servico in SERVICOS_CEP}
        for futuro in concurrent.futures.as_completed(futuros):
            try:
                endereco = futuro.result()
                return endereco
            except Exception as e:
                print(f"Erro ao consultar {futuros[futuro].__class__.__name__}: {e}")


import concurrent.futures
from .servicos import SERVICOS_CEP


def consulta_cep(cep):
    """
    Consulta o CEP em mais de um serviço de forma concorrente,
    devolvendo o primeiro resultado
    :param cep: CEP
    :return: Endereco
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futuros = {
            executor.submit(servico.consultar, cep):
                servico for servico in SERVICOS_CEP
        }
        for futuro in concurrent.futures.as_completed(futuros):
            try:
                endereco = futuro.result()
                return endereco
            except Exception as e:
                print(
                    f"Erro ao consultar "
                    f"{futuros[futuro].__class__.__name__}: {e}"
                )

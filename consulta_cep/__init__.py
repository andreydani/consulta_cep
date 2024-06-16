import concurrent.futures
from servicos import SERVICOS_CEP
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


def main():
    parser = argparse.ArgumentParser(description="Consultar endereço a partir do CEP.")
    parser.add_argument("cep", type=str, help="CEP para consulta (formato: 12345-678 ou 12345678)")
    args = parser.parse_args()

    cep = args.cep

    try:
        endereco = consulta_concorrente(cep)
        if endereco:
            print(endereco)
        else:
            print(dict(erro="Nenhum serviço conseguiu retornar um endereço válido."))
    except Exception as e:
        print(dict(erro="Erro ao realizar consulta:", excecao=e))


if __name__ == "__main__":
    main()

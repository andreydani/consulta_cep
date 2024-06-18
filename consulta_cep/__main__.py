from . import consulta_cep
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Consultar endereço a partir do CEP."
    )
    parser.add_argument(
        "cep",
        type=str,
        help="CEP para consulta (formato: 12345-678 ou 12345678)"
    )
    args = parser.parse_args()

    cep = args.cep

    try:
        endereco = consulta_cep(cep)
        if endereco:
            print(endereco)
        else:
            print(
                dict(
                    erro="Nenhum serviço conseguiu retornar"
                         " um endereço válido."
                )
            )
    except Exception as e:
        print(
            dict(
                erro="Erro ao realizar consulta: " + str(e)
            )
        )


main()

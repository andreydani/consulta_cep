from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import TIMEOUT_PADRAO, __version__, consulta_cep
from .excecoes import CEPInvalidoError, ConsultaCEPError


def _erro(mensagem: str) -> None:
    print(json.dumps({"erro": mensagem}, ensure_ascii=False), file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="consulta-cep",
        description="Consultar endereço a partir do CEP.",
    )
    parser.add_argument(
        "cep",
        help="CEP para consulta (formato: 12345-678 ou 12345678)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=TIMEOUT_PADRAO,
        help="tempo máximo de cada requisição, em segundos (padrão: %(default)s)",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    args = parser.parse_args(argv)

    try:
        endereco = consulta_cep(args.cep, timeout=args.timeout)
    except CEPInvalidoError as erro:
        _erro(str(erro))
        return 2
    except ConsultaCEPError as erro:
        _erro(str(erro))
        return 1
    print(endereco)
    return 0


if __name__ == "__main__":
    sys.exit(main())

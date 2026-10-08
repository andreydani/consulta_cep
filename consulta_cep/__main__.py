"""Linha de comando: ``consulta-cep`` ou ``python -m consulta_cep``."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Sequence
from typing import get_args

import httpx

from . import __version__
from .consulta import Estrategia, consulta_cep_async
from .engine_cep import Endereco
from .excecoes import (
    CEPInvalidoError,
    CEPNaoEncontradoError,
    ConsultaCEPError,
)
from .servicos import servicos_disponiveis
from .util import TIMEOUT_PADRAO

SUCESSO = 0
NAO_ENCONTRADO = 1
CEP_INVALIDO = 2
INDISPONIVEL = 3

_ROTULOS: list[tuple[str, str]] = [
    ("cep", "CEP"),
    ("logradouro", "Logradouro"),
    ("complemento", "Complemento"),
    ("bairro", "Bairro"),
    ("cidade", "Cidade"),
    ("estado", "Estado"),
    ("ibge", "IBGE"),
    ("ddd", "DDD"),
]


def formatar_texto(endereco: Endereco) -> str:
    """Formata o endereço em texto legível, omitindo campos vazios."""
    dados = endereco.to_dict()
    linhas = [
        f"{rotulo}: {dados[campo]}"
        for campo, rotulo in _ROTULOS
        if dados[campo] is not None
    ]
    if endereco.latitude is not None and endereco.longitude is not None:
        linhas.append(f"Coordenadas: {endereco.latitude}, {endereco.longitude}")
    linhas.append(f"Serviço: {endereco.servico}")
    return "\n".join(linhas)


def _codigo(erro: BaseException) -> int:
    if isinstance(erro, CEPInvalidoError):
        return CEP_INVALIDO
    if isinstance(erro, CEPNaoEncontradoError):
        return NAO_ENCONTRADO
    return INDISPONIVEL


def _tipo(erro: BaseException) -> str:
    if isinstance(erro, CEPInvalidoError):
        return "cep_invalido"
    if isinstance(erro, CEPNaoEncontradoError):
        return "nao_encontrado"
    return "servicos_indisponiveis"


def _timeout(valor: str) -> float:
    try:
        numero = float(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"valor inválido: {valor!r}") from None
    if numero <= 0:
        raise argparse.ArgumentTypeError("deve ser maior que zero")
    return numero


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="consulta-cep",
        description="Consulta endereços a partir do CEP.",
        epilog=(
            "Códigos de saída: 0 sucesso, 1 CEP não encontrado, 2 CEP inválido, "
            "3 serviços indisponíveis. Com vários CEPs, vale o maior código."
        ),
    )
    parser.add_argument(
        "ceps",
        nargs="+",
        metavar="CEP",
        help="um ou mais CEPs (formato: 12345-678 ou 12345678)",
    )
    parser.add_argument(
        "-s",
        "--servico",
        action="append",
        dest="servicos",
        choices=servicos_disponiveis(),
        metavar="SERVICO",
        help=(
            "serviço a consultar; repita para usar mais de um, na ordem de "
            f"preferência ({', '.join(servicos_disponiveis())})"
        ),
    )
    parser.add_argument(
        "-e",
        "--estrategia",
        choices=get_args(Estrategia),
        default="concorrente",
        help="concorrente (padrão) ou sequencial",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=_timeout,
        default=TIMEOUT_PADRAO,
        help="tempo máximo de cada requisição, em segundos (padrão: %(default)s)",
    )
    parser.add_argument(
        "-f",
        "--formato",
        choices=("texto", "json"),
        default="texto",
        help=(
            "texto (padrão) ou json (um objeto por linha; erros também em JSON, "
            "na saída de erro)"
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


async def _consultar_todos(
    args: argparse.Namespace,
) -> list[Endereco | BaseException]:
    async with httpx.AsyncClient() as client:
        tarefas = [
            consulta_cep_async(
                cep,
                timeout=args.timeout,
                servicos=args.servicos,
                estrategia=args.estrategia,
                client=client,
            )
            for cep in args.ceps
        ]
        return await asyncio.gather(*tarefas, return_exceptions=True)


def _silenciar_logs() -> None:
    # Sem handler, o logging do Python escreveria cada falha de serviço (com
    # traceback) na saída de erro; a CLI já resume os erros por CEP.
    logger = logging.getLogger("consulta_cep")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())


def main(argv: Sequence[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)
    _silenciar_logs()
    resultados = asyncio.run(_consultar_todos(args))

    codigo = SUCESSO
    blocos: list[str] = []
    for cep, resultado in zip(args.ceps, resultados, strict=True):
        if isinstance(resultado, Endereco):
            if args.formato == "json":
                print(resultado.to_json())
            else:
                blocos.append(formatar_texto(resultado))
            continue
        if not isinstance(resultado, ConsultaCEPError):
            raise resultado
        codigo = max(codigo, _codigo(resultado))
        if args.formato == "json":
            erro = {"cep": cep, "tipo": _tipo(resultado), "erro": str(resultado)}
            print(json.dumps(erro, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"{cep}: {resultado}", file=sys.stderr)

    if blocos:
        print("\n\n".join(blocos))
    return codigo


if __name__ == "__main__":
    sys.exit(main())

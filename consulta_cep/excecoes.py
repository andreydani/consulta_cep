"""Exceções lançadas pela biblioteca."""

from __future__ import annotations

from collections.abc import Mapping


class ConsultaCEPError(Exception):
    """Base de todas as exceções da biblioteca."""


class CEPInvalidoError(ConsultaCEPError, ValueError):
    """O CEP informado não tem um formato válido."""

    def __init__(self, cep: str) -> None:
        self.cep = cep
        super().__init__(f"CEP inválido: {cep!r}. Use o formato 12345-678 ou 12345678.")


class CEPNaoEncontradoError(ConsultaCEPError):
    """Os serviços responderam, mas o CEP não existe."""

    def __init__(self, cep: str) -> None:
        self.cep = cep
        super().__init__(f"CEP não encontrado: {cep}.")


class ServicosIndisponiveisError(ConsultaCEPError):
    """Nenhum serviço conseguiu responder à consulta.

    O atributo ``erros`` associa o nome de cada serviço à exceção que ele
    lançou.
    """

    def __init__(self, erros: Mapping[str, BaseException]) -> None:
        self.erros: dict[str, BaseException] = dict(erros)
        detalhes = "; ".join(
            f"{servico}: {erro!r}" for servico, erro in self.erros.items()
        )
        mensagem = "Nenhum serviço de CEP respondeu."
        if detalhes:
            mensagem = f"{mensagem} {detalhes}"
        super().__init__(mensagem)

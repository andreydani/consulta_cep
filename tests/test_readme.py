"""Executa os exemplos do README.md com respostas simuladas.

- Blocos ``python`` são executados; se tiverem uma linha ``# Saída:``, as linhas
  de comentário seguintes são comparadas com o que foi impresso.
- Blocos ``pycon`` rodam como doctest.
- Blocos ``console`` rodam cada ``$ consulta-cep ...`` e comparam a saída
  (padrão e de erro); ``$ echo $?`` mostra o código de saída anterior.
- Blocos ``bash`` rodam cada linha ``consulta-cep``/``python -m consulta_cep``
  e exigem código de saída 0.
- Um bloco precedido de ``<!-- readme: não testar -->`` é ignorado.

As APIs respondem com as fixtures de ``sucesso`` para qualquer CEP, exceto
99999999, que responde com ``nao_encontrado``.
"""

from __future__ import annotations

import contextlib
import doctest
import io
import re
import shlex
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
import respx

from consulta_cep import limpar_cache, servicos_disponiveis
from consulta_cep.__main__ import main
from consulta_cep.servicos import obter_servico

from .dados import CEP_INEXISTENTE, resposta

README = Path(__file__).parent.parent / "README.md"
NAO_TESTAR = "<!-- readme: não testar -->"


@dataclass
class Bloco:
    linguagem: str
    codigo: str
    linha: int

    @property
    def id(self) -> str:
        return f"{self.linguagem}-linha{self.linha}"


def _blocos() -> list[Bloco]:
    blocos: list[Bloco] = []
    linhas = README.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(linhas):
        abertura = re.match(r"^(\s*)```(\w+)\s*$", linhas[i])
        if abertura is None:
            i += 1
            continue
        recuo, linguagem = abertura.groups()
        anterior = next((x.strip() for x in reversed(linhas[:i]) if x.strip()), "")
        inicio = i + 1
        i = inicio
        while linhas[i].strip() != "```":
            i += 1
        corpo = "\n".join(linha[len(recuo) :] for linha in linhas[inicio:i])
        if anterior != NAO_TESTAR:
            blocos.append(Bloco(linguagem, corpo + "\n", inicio))
        i += 1
    return blocos


BLOCOS = _blocos()


def _de(linguagem: str) -> list[Bloco]:
    return [b for b in BLOCOS if b.linguagem == linguagem]


def _responder(nome: str) -> respx.types.SideEffectTypes:
    def lado(request: httpx.Request) -> httpx.Response:
        if CEP_INEXISTENTE in str(request.url):
            return resposta(nome, "nao_encontrado")
        return resposta(nome, "sucesso")

    return lado


@pytest.fixture
def apis() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        for nome in servicos_disponiveis():
            modelo = re.escape(obter_servico(nome).URL).replace(
                re.escape("{cep}"), r"\d{8}"
            )
            router.get(url__regex=f"^{modelo}$").mock(side_effect=_responder(nome))
        yield router


def test_readme_tem_exemplos_de_cada_tipo() -> None:
    linguagens = {b.linguagem for b in BLOCOS}
    assert {"python", "pycon", "console", "bash"} <= linguagens
    assert len(_de("python")) >= 8


def _saida_esperada(codigo: str) -> str | None:
    linhas = codigo.splitlines()
    if "# Saída:" not in linhas:
        return None
    resto = linhas[linhas.index("# Saída:") + 1 :]
    return "".join(linha.removeprefix("# ") + "\n" for linha in resto)


@pytest.mark.parametrize("bloco", _de("python"), ids=lambda b: b.id)
def test_bloco_python(bloco: Bloco, apis: respx.MockRouter) -> None:
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        exec(compile(bloco.codigo, f"README.md:{bloco.linha}", "exec"), {})
    esperada = _saida_esperada(bloco.codigo)
    if esperada is not None:
        assert saida.getvalue() == esperada
    limpar_cache()


@pytest.mark.parametrize("bloco", _de("pycon"), ids=lambda b: b.id)
def test_bloco_pycon(bloco: Bloco, apis: respx.MockRouter) -> None:
    teste = doctest.DocTestParser().get_doctest(
        bloco.codigo, {}, f"README.md:{bloco.linha}", str(README), bloco.linha
    )
    executor = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    relatorio = io.StringIO()
    resultado = executor.run(teste, out=relatorio.write)
    assert resultado.failed == 0, relatorio.getvalue()


def _rodar_cli(comando: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    argv = shlex.split(comando, comments=True)
    if argv[:3] == ["python", "-m", "consulta_cep"]:
        argv = argv[3:]
    else:
        assert argv[0] == "consulta-cep", comando
        argv = argv[1:]
    codigo = main(argv)
    capturado = capsys.readouterr()
    return codigo, capturado.err + capturado.out


@pytest.mark.parametrize("bloco", _de("console"), ids=lambda b: b.id)
def test_bloco_console(
    bloco: Bloco, apis: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    sessoes = re.split(r"^\$ ", bloco.codigo, flags=re.MULTILINE)[1:]
    assert sessoes
    ultimo_codigo = 0
    for sessao in sessoes:
        comando, _, esperada = sessao.partition("\n")
        if comando == "echo $?":
            assert esperada == f"{ultimo_codigo}\n"
            continue
        ultimo_codigo, saida = _rodar_cli(comando, capsys)
        assert saida == esperada, comando


@pytest.mark.parametrize("bloco", _de("bash"), ids=lambda b: b.id)
def test_bloco_bash(
    bloco: Bloco, apis: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    for linha in bloco.codigo.splitlines():
        if linha.startswith(("consulta-cep ", "python -m consulta_cep ")):
            codigo, saida = _rodar_cli(linha, capsys)
            assert codigo == 0, f"{linha}\n{saida}"


def test_parser_dos_blocos_ignora_os_marcados() -> None:
    texto = README.read_text(encoding="utf-8")
    assert texto.count(NAO_TESTAR) == 2
    assert all("# 0.2" not in b.codigo for b in BLOCOS)
    assert textwrap.dedent(_de("python")[0].codigo).startswith("from consulta_cep")


@pytest.mark.parametrize("silenciar", [False, True])
def test_secao_logs(silenciar: bool) -> None:
    """Confere a seção "Logs": sem configuração, as falhas aparecem na saída de
    erro; com ``setLevel(logging.ERROR)``, somem."""
    script = textwrap.dedent(
        f"""
        import logging, httpx, respx
        from consulta_cep import consulta_cep
        if {silenciar}:
            logging.getLogger("consulta_cep").setLevel(logging.ERROR)
        with respx.mock() as r:
            r.get(url__regex="viacep").mock(side_effect=httpx.ConnectError("fora"))
            r.get(url__regex="opencep").respond(json={{
                "cep": "01001-000", "uf": "SP", "localidade": "São Paulo"}})
            print(consulta_cep("01001000", servicos=["viacep", "opencep"],
                               estrategia="sequencial").servico)
        """
    )
    resultado = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout == "opencep\n"
    if silenciar:
        assert resultado.stderr == ""
    else:
        assert "Erro ao consultar viacep" in resultado.stderr

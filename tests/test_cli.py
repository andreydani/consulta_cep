from __future__ import annotations

import json
import subprocess
import sys

import httpx
import pytest
import respx

from consulta_cep import SERVICOS_PADRAO, Endereco, __version__
from consulta_cep.__main__ import formatar_texto, main

from .dados import CEP, CEP_INEXISTENTE, simular, url

Saida = pytest.CaptureFixture[str]


def _so_viacep(api: respx.MockRouter, nome: str = "sucesso", cep: str = CEP) -> None:
    simular(api, "viacep", nome, cep=cep)


def test_texto_padrao(api: respx.MockRouter, capsys: Saida) -> None:
    _so_viacep(api)
    assert main(["01001-000", "--servico", "viacep"]) == 0
    saida = capsys.readouterr()
    assert saida.err == ""
    assert saida.out.splitlines() == [
        "CEP: 01001-000",
        "Logradouro: Praça da Sé",
        "Complemento: lado ímpar",
        "Bairro: Sé",
        "Cidade: São Paulo",
        "Estado: SP",
        "IBGE: 3550308",
        "DDD: 11",
        "Serviço: viacep",
    ]


def test_texto_com_coordenadas_e_sem_campos_vazios() -> None:
    endereco = Endereco(
        "awesomeapi", "SP", "São Paulo", None, None, latitude=-23.5, longitude=-46.6
    )
    assert formatar_texto(endereco).splitlines() == [
        "Cidade: São Paulo",
        "Estado: SP",
        "Coordenadas: -23.5, -46.6",
        "Serviço: awesomeapi",
    ]


def test_json(api: respx.MockRouter, capsys: Saida) -> None:
    _so_viacep(api)
    assert main(["01001000", "-s", "viacep", "--formato", "json"]) == 0
    dados = json.loads(capsys.readouterr().out)
    assert dados["cep"] == "01001-000"
    assert dados["cidade"] == "São Paulo"


def test_varios_ceps(api: respx.MockRouter, capsys: Saida) -> None:
    _so_viacep(api)
    simular(api, "viacep", "sucesso", cep="01310100")
    assert main([CEP, "01310-100", "-s", "viacep", "-f", "json"]) == 0
    linhas = capsys.readouterr().out.splitlines()
    assert len(linhas) == 2
    assert all(json.loads(linha)["servico"] == "viacep" for linha in linhas)


def test_varios_ceps_em_texto_separados(api: respx.MockRouter, capsys: Saida) -> None:
    _so_viacep(api)
    simular(api, "viacep", "sucesso", cep="01310100")
    assert main([CEP, "01310100", "-s", "viacep"]) == 0
    assert capsys.readouterr().out.count("\n\nCEP: ") == 1


def test_servico_repetivel_e_estrategia(api: respx.MockRouter) -> None:
    viacep = simular(api, "viacep", "nao_encontrado")
    opencep = simular(api, "opencep", "sucesso")
    awesomeapi = simular(api, "awesomeapi", "sucesso")
    argv = [CEP, "-s", "viacep", "-s", "opencep", "-s", "awesomeapi"]
    assert main([*argv, "--estrategia", "sequencial"]) == 0
    assert (viacep.call_count, opencep.call_count, awesomeapi.call_count) == (1, 1, 0)


def test_padrao_usa_lista_padrao(api: respx.MockRouter) -> None:
    for nome in SERVICOS_PADRAO:
        simular(api, nome, "sucesso")
    assert main([CEP]) == 0


def test_timeout(api: respx.MockRouter) -> None:
    rota = simular(api, "viacep", "sucesso")
    assert main([CEP, "-s", "viacep", "--timeout", "1.5"]) == 0
    assert rota.calls.last.request.extensions["timeout"]["read"] == 1.5


@pytest.mark.parametrize("valor", ["0", "-1", "abc"])
def test_timeout_invalido(valor: str, capsys: Saida) -> None:
    with pytest.raises(SystemExit) as info:
        main([CEP, "--timeout", valor])
    assert info.value.code == 2
    assert "--timeout" in capsys.readouterr().err


def test_servico_desconhecido(capsys: Saida) -> None:
    with pytest.raises(SystemExit):
        main([CEP, "-s", "correios"])
    assert "correios" in capsys.readouterr().err


def test_version(capsys: Saida) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert capsys.readouterr().out.strip() == f"consulta-cep {__version__}"


# --- erros e códigos de saída ----------------------------------------------------


def test_nao_encontrado(api: respx.MockRouter, capsys: Saida) -> None:
    _so_viacep(api, "nao_encontrado", CEP_INEXISTENTE)
    assert main(["99999-999", "-s", "viacep"]) == 1
    saida = capsys.readouterr()
    assert saida.out == ""
    assert saida.err.strip() == "99999-999: CEP não encontrado: 99999999."


def test_cep_invalido(capsys: Saida) -> None:
    assert main(["123"]) == 2
    saida = capsys.readouterr()
    assert saida.out == ""
    assert saida.err.startswith("123: CEP inválido")


def test_indisponivel(api: respx.MockRouter, capsys: Saida) -> None:
    api.get(url("viacep")).mock(side_effect=httpx.ConnectError("recusada"))
    assert main([CEP, "-s", "viacep"]) == 3
    saida = capsys.readouterr()
    assert saida.out == ""
    assert "viacep" in saida.err
    assert "recusada" in saida.err
    assert "Traceback" not in saida.err


def test_cli_nao_imprime_logs_dos_servicos() -> None:
    codigo = (
        "import respx, httpx\n"
        "from consulta_cep.__main__ import main\n"
        "with respx.mock() as r:\n"
        "    r.get(url__regex='.*').mock(side_effect=httpx.ConnectError('x'))\n"
        "    raise SystemExit(main(['01001000']))\n"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=False
    )
    assert resultado.returncode == 3
    assert resultado.stderr.count("\n") == 1
    assert "Traceback" not in resultado.stderr


def test_erro_em_json(capsys: Saida) -> None:
    assert main(["123", "--formato", "json"]) == 2
    saida = capsys.readouterr()
    assert saida.out == ""
    erro = json.loads(saida.err)
    assert erro["cep"] == "123"
    assert erro["tipo"] == "cep_invalido"
    assert "inválido" in erro["erro"]


def test_varios_ceps_vale_o_maior_codigo(api: respx.MockRouter, capsys: Saida) -> None:
    _so_viacep(api)
    _so_viacep(api, "nao_encontrado", CEP_INEXISTENTE)
    assert main([CEP, CEP_INEXISTENTE, "-s", "viacep"]) == 1
    assert main([CEP, CEP_INEXISTENTE, "abc", "-s", "viacep"]) == 2
    api.get(url("viacep", "01310100")).respond(503)
    assert main(["abc", "01310100", "-s", "viacep"]) == 3
    saida = capsys.readouterr()
    assert "Praça da Sé" in saida.out


def test_sem_argumentos(capsys: Saida) -> None:
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2


# --- execução como programa --------------------------------------------------------


def test_importar_main_nao_executa() -> None:
    resultado = subprocess.run(
        [sys.executable, "-c", "import consulta_cep.__main__"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0
    assert resultado.stdout == resultado.stderr == ""


def test_python_m_cep_invalido() -> None:
    resultado = subprocess.run(
        [sys.executable, "-m", "consulta_cep", "123"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 2
    assert resultado.stdout == ""
    assert "CEP inválido" in resultado.stderr


def test_python_m_sem_argumentos_mostra_uso() -> None:
    resultado = subprocess.run(
        [sys.executable, "-m", "consulta_cep"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 2
    assert "usage" in resultado.stderr

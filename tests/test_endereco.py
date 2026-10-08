from __future__ import annotations

import json

import pytest

from consulta_cep import Endereco
from consulta_cep.engine_cep import UFS, numero_opcional, sigla_uf, texto_opcional


def _endereco(**campos: object) -> Endereco:
    base: dict[str, object] = {
        "servico": "teste",
        "estado": "SP",
        "cidade": "São Paulo",
        "bairro": "Sé",
        "logradouro": "Praça da Sé",
    }
    base.update(campos)
    return Endereco(**base)  # type: ignore[arg-type]


def test_ordem_dos_campos_compativel() -> None:
    endereco = Endereco("viacep", "SP", "São Paulo", "Sé", "Praça da Sé")
    assert list(endereco.to_dict()) == [
        "servico",
        "estado",
        "cidade",
        "bairro",
        "logradouro",
        "cep",
        "complemento",
        "ibge",
        "ddd",
        "latitude",
        "longitude",
    ]
    assert endereco.cep is None
    assert endereco.latitude is None


@pytest.mark.parametrize("cep", ["01001000", "01001-000", "01.001-000", " 01001000 "])
def test_cep_formatado(cep: str) -> None:
    assert _endereco(cep=cep).cep == "01001-000"


def test_cep_vazio_vira_none() -> None:
    assert _endereco(cep="").cep is None


def test_strings_vazias_viram_none() -> None:
    endereco = _endereco(bairro="", logradouro="  ", complemento="", ibge="", ddd="")
    assert endereco.bairro is None
    assert endereco.logradouro is None
    assert endereco.complemento is None
    assert endereco.ibge is None
    assert endereco.ddd is None


@pytest.mark.parametrize(
    ("estado", "sigla"),
    [
        ("SP", "SP"),
        ("sp", "SP"),
        (" rj ", "RJ"),
        ("São Paulo", "SP"),
        ("sao paulo", "SP"),
        ("ESPÍRITO SANTO", "ES"),
        ("Rio  Grande do Sul", "RS"),
    ],
)
def test_estado_vira_sigla(estado: str, sigla: str) -> None:
    assert _endereco(estado=estado).estado == sigla


@pytest.mark.parametrize("estado", ["", "XX", "Gotham"])
def test_estado_desconhecido(estado: str) -> None:
    with pytest.raises(ValueError):
        sigla_uf(estado)


def test_todas_as_ufs() -> None:
    assert len(UFS) == 27
    for sigla, nome in UFS.items():
        assert sigla_uf(nome) == sigla


def test_conversoes_opcionais() -> None:
    assert texto_opcional(None) is None
    assert texto_opcional(" ") is None
    assert texto_opcional(11) == "11"
    assert numero_opcional(None) is None
    assert numero_opcional("") is None
    assert numero_opcional(True) is None
    assert numero_opcional("-23.5") == -23.5
    assert numero_opcional(-46) == -46.0


def test_to_dict_to_json_e_str() -> None:
    endereco = _endereco(cep="01001000", latitude=-23.55, ddd="11")
    dados = endereco.to_dict()
    assert dados["cep"] == "01001-000"
    assert dados["latitude"] == -23.55
    texto = endereco.to_json()
    assert "São Paulo" in texto
    assert "Praça da Sé" in texto
    assert json.loads(texto) == dados
    assert str(endereco) == texto
    assert "\\u00e3" in endereco.to_json(ensure_ascii=True)

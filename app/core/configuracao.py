import tomllib
from pathlib import Path


with (Path(__file__).resolve().parents[2] / "pyproject.toml").open("rb") as configuracao:
    metadadosProjeto = tomllib.load(configuracao)["project"]

NOME_APLICACAO = "LiberaAI"
VERSAO_APLICACAO = metadadosProjeto["version"]
DESCRICAO_APLICACAO = metadadosProjeto["description"]

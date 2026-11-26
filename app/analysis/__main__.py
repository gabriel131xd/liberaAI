import argparse
import json
from pathlib import Path

import httpx

from app.documents.estruturas import ErroDocumento
from app.integrations.camara.cliente import ErroCamara

from .servico import analisarProposicao


def executar():
    argumentosCli = argparse.ArgumentParser(description="Análise documental com IA local")
    argumentosCli.add_argument("--id", required=True, type=int)
    argumentosCli.add_argument("--peca", help="ID principal, relacionada, movimento:N ou avulso:N")
    argumentosCli.add_argument("--inicio", type=int)
    argumentosCli.add_argument("--fim", type=int)
    argumentosCli.add_argument("--secao", help="Identificação do recorte conferida pelo avaliador")
    argumentosCli.add_argument(
        "--motivo-ementa",
        dest="motivoEmenta",
        metavar="MOTIVO_EMENTA",
        help="Registrar por que as peças alternativas consultadas são inadequadas.",
    )
    argumentosCli.add_argument("--registro", type=Path, help="Salvar JSON com fontes, respostas e métricas")
    argumentos = argumentosCli.parse_args()
    try:
        resultado = analisarProposicao(
            argumentos.id, argumentos.peca, argumentos.inicio, argumentos.fim,
            argumentos.secao, argumentos.motivoEmenta,
        )
    except (ErroDocumento, ErroCamara, httpx.HTTPError) as erro:
        argumentosCli.exit(2, f"{erro}\n")
    textoJson = json.dumps(resultado, ensure_ascii=False, indent=2)
    if argumentos.registro:
        argumentos.registro.write_text(textoJson, encoding="utf-8")
    print(textoJson)
    if resultado.get("falha") or resultado["situacao"] == "sem texto":
        argumentosCli.exit(1)


if __name__ == "__main__":
    executar()

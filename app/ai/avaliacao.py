"""Executa a amostra comparativa da Etapa 07 e preserva as saídas literais."""

import argparse
import json
from pathlib import Path

from app.ai.cliente import ErroInferencia
from app.analysis.fonte import selecionarFonte
from app.analysis.servico import analisarFonte
from app.documents.estruturas import PaginaDocumento
from app.interface.conversa import responder

CASOS_DOCUMENTAIS = (
    ("analise_411_rdf_final.json", 380852, "2418402"),
    ("analise_2597.json", 253500, "2443615"),
    ("analise_1904_final.json", 2434493, "2434493"),
)
TRECHO_FICTICIO = (
    "Art. 1º A escola poderá abrir aos domingos, desde que haja um servidor. "
    "É proibida a cobrança de entrada. A autorização não se aplica a feriados."
)


def executar():
    argumentosCli = argparse.ArgumentParser(description="Avaliar as instruções da IA local")
    argumentosCli.add_argument("--registro", required=True, type=Path, help="Arquivo JSONL de saída")
    argumentos = argumentosCli.parse_args()
    pasta = Path(__file__).resolve().parents[2] / "docs"
    with argumentos.registro.open("x", encoding="utf-8", newline="\n") as arquivo:
        def gravar(resultado):
            arquivo.write(json.dumps(resultado, ensure_ascii=False) + "\n")
            arquivo.flush()

        fonteConversa = None
        for nomeAnterior, identificador, peca in CASOS_DOCUMENTAIS:
            anterior = json.loads((pasta / nomeAnterior).read_text(encoding="utf-8-sig"))
            fonte = selecionarFonte(identificador, peca)
            if fonte[1]["sha256"] != anterior["documento"]["sha256"]:
                raise ValueError(f"O documento de {identificador} difere da versão do experimento anterior.")
            resultado = analisarFonte(fonte, *anterior["recorte"], anterior["geracoes"][0]["secao"])
            gravar({"anterior": nomeAnterior, "resposta_v2": resultado})
            print(identificador, resultado["situacao"], resultado["segundos"], flush=True)
            if peca == "2443615":
                fonteConversa = fonte

        registrosInterface = json.loads((pasta / "interface_exemplos.json").read_text(encoding="utf-8"))
        pergunta = registrosInterface["chat_atual"]["mensagens"][0]["content"]
        registro = {"anterior": "interface_exemplos.json#chat_atual", "pergunta": pergunta,
                    "peca": fonteConversa[1]["url"], "paginas": [1]}
        try:
            registro["resposta_exibida"] = responder(
                pergunta, {"dados": fonteConversa[0]}, fonteConversa, (1, 1, "Substitutivo do Senado"),
                None, [], registro=registro,
            )
        except ErroInferencia as erro:
            registro["falha"] = str(erro)
        gravar(registro)
        print("Chat", registro.get("segundos"), flush=True)

        fonteFicticia = ({}, {"identificacao": "Caso adicional fictício", "paginas": 1},
                        [PaginaDocumento(1, TRECHO_FICTICIO, TRECHO_FICTICIO, [])])
        resultado = analisarFonte(fonteFicticia, 1, 1, "Dispositivos")
        gravar({"caso_ficticio": TRECHO_FICTICIO, "resposta_v2": resultado})
        print("Fictício", resultado["situacao"], resultado["segundos"], flush=True)


if __name__ == "__main__":
    executar()

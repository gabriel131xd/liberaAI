import argparse
import sys

from app.integrations.camara.cliente import ErroCamara

from .estruturas import ErroDocumento
from .referencias import listarReferencias
from .servico import recuperarDocumento


def executar():
    argumentosCli = argparse.ArgumentParser(description="Consultar documento oficial da Câmara")
    argumentosCli.add_argument("--id", required=True, type=int)
    argumentosCli.add_argument("--pagina", type=int, help="Exibir uma página (a partir de 1)")
    argumentosCli.add_argument("--bruto", action="store_true", help="Mostrar a camada textual original")
    argumentosCli.add_argument("--referencias", action="store_true", help="Listar peças relacionadas, tramitações e avulsos")
    argumentosCli.add_argument("--limite-mib", dest="limiteMib", metavar="LIMITE_MIB", type=int, default=20)
    argumentos = argumentosCli.parse_args()
    if argumentos.id < 1 or argumentos.limiteMib < 1:
        argumentosCli.error("O ID e o limite devem ser positivos.")
    try:
        if argumentos.referencias:
            for referencia in listarReferencias(argumentos.id):
                print(referencia)
            return
        documento = recuperarDocumento(argumentos.id, limiteBytes=argumentos.limiteMib * 1024**2)
    except (ErroCamara, ErroDocumento) as erro:
        sys.exit(str(erro))
    dadosOficiais, arquivo, extracao = documento.dadosOficiais, documento.arquivo, documento.extracao
    print(f"Câmara dos Deputados · {dadosOficiais.get('siglaTipo')} {dadosOficiais.get('numero')}/{dadosOficiais.get('ano')} · ID {argumentos.id}")
    print(f"Referência: {dadosOficiais['urlInteiroTeor']}\nDestino: {arquivo.urlFinal}\nVersão: {documento.versao}")
    print(f"PDF · {arquivo.tipoConteudo} · {len(arquivo.conteudo)} bytes · {arquivo.recuperadoEm.isoformat()}\nSHA-256: {arquivo.sha256}")
    print(f"{len(extracao.paginas)} páginas · {extracao.caracteres} caracteres · {extracao.palavras} palavras")
    if not extracao.caracteres:
        print("Contexto indeterminado: documento sem texto extraível.")
        print(f"Investigue outras peças com --id {argumentos.id} --referencias antes de recorrer à ementa.")
    else:
        print(f"Estimativa para a camada textual: {extracao.tokensEstimados} tokens (4 caracteres/token).")
        if extracao.tokensEstimados > 4096:
            print("O texto provavelmente excede o contexto de 4096 tokens, mesmo antes das instruções e da resposta.")
    print(extracao.situacao, *extracao.avisos, sep="\n")
    if argumentos.pagina is not None and not 1 <= argumentos.pagina <= len(extracao.paginas):
        argumentosCli.error("Página fora do documento")
    for pagina in extracao.paginas:
        for aviso in pagina.avisos:
            print(f"Aviso na página {pagina.numero}: {aviso}")
        if argumentos.pagina is None or pagina.numero == argumentos.pagina:
            print(f"\n--- Página {pagina.numero} ---\n", pagina.textoBruto if argumentos.bruto else pagina.texto, sep="")


if __name__ == "__main__":
    executar()

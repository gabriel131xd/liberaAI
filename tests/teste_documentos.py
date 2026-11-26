"""PDFs sintéticos gerados em memória exclusivamente para testes."""
import hashlib

import httpx
import pymupdf
import pytest

from app.documents.transferencia import baixarDocumento
from app.documents.extrator import extrairTexto
from app.documents.estruturas import ErroDocumento


URL_DOCUMENTO = "https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=1"


def criarPdf(*linhas):
    with pymupdf.open() as documento:
        for linha in linhas:
            pagina = documento.new_page()
            if linha:
                pagina.insert_text((40, 60), linha)
        return documento.tobytes()


def simularDownload(resposta, **opcoes):
    return baixarDocumento(URL_DOCUMENTO, transporte=httpx.MockTransport(lambda _: resposta), **opcoes)


def responder(conteudo):
    return httpx.Response(200, content=conteudo, headers={"content-type": "application/pdf"})


def testeDownloadEPaginas():
    conteudo = criarPdf("Art. 1 - 15 dias.", "Salvo se houver recurso.")
    arquivo = simularDownload(responder(conteudo))
    assert arquivo.conteudo == conteudo and arquivo.sha256 == hashlib.sha256(conteudo).hexdigest()
    extracao = extrairTexto(arquivo.conteudo)
    assert [pagina.numero for pagina in extracao.paginas] == [1, 2]
    assert extracao.textoBruto == extracao.texto == "Art. 1 - 15 dias.\n\fSalvo se houver recurso.\n"


@pytest.mark.parametrize("codigoHttp", [404, 429, 500, 503])
def testeHttp(codigoHttp):
    with pytest.raises(ErroDocumento, match=str(codigoHttp)):
        simularDownload(httpx.Response(codigoHttp))


@pytest.mark.parametrize("tipoErro,motivo", [(httpx.ReadTimeout, "Tempo limite"), (httpx.ConnectError, "comunicação")])
def testeTransporte(tipoErro, motivo):
    def falhar(_):
        raise tipoErro("simulado")
    with pytest.raises(ErroDocumento, match=motivo):
        baixarDocumento(URL_DOCUMENTO, transporte=httpx.MockTransport(falhar))


@pytest.mark.parametrize("conteudo,motivo", [(b"", "vazio"), (b"<html>", "assinatura")])
def testeConteudo(conteudo, motivo):
    with pytest.raises(ErroDocumento, match=motivo):
        simularDownload(responder(conteudo))


def testeHtml():
    with pytest.raises(ErroDocumento, match="Formato"):
        simularDownload(httpx.Response(200, text="<html>", headers={"content-type": "text/html"}))


def testeTamanhoEfetivo():
    with pytest.raises(ErroDocumento, match="limite"):
        simularDownload(httpx.Response(200, headers={"content-type": "application/pdf"},
                             stream=httpx.ByteStream(b"%PDF-" * 50)), limiteBytes=100)


def testeDestino():
    with pytest.raises(ErroDocumento, match="autorizado"):
        baixarDocumento("file:///c:/teste", transporte=httpx.MockTransport(lambda _: pytest.falhar()))


def testeRedirecionamento():
    with pytest.raises(ErroDocumento, match="autorizado"):
        simularDownload(httpx.Response(302, headers={"location": "http://127.0.0.1/"}))


def testePdfCorrompido():
    with pytest.raises(ErroDocumento, match="corrompido"):
        extrairTexto(b"%PDF-broken")


def testePdfVazio():
    assert extrairTexto(criarPdf("")).situacao == "sem texto extraível"


def testeExtracaoParcial():
    extracao = extrairTexto(criarPdf("Art. 1", "", "Art. 3"))
    assert extracao.situacao == "extração parcial ou incerta"
    assert extracao.paginas[1].avisos and extracao.paginas[2].numero == 3

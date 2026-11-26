"""Cinco recuperações reais. Cada referência é consultada no momento do teste."""
import pytest

from app.documents.servico import recuperarDocumento


@pytest.mark.live
@pytest.mark.parametrize("identificador", [253500, 380852, 510035, 2434493, 2256735])
def testePdfDaCamara(identificador):
    documento = recuperarDocumento(identificador)
    assert documento.dadosOficiais["id"] == identificador
    assert documento.extracao.paginas
    assert documento.arquivo.conteudo.startswith(b"%PDF-")
    if documento.extracao.caracteres == 0:
        assert documento.extracao.situacao == "sem texto extraível"
        assert all(pagina.avisos for pagina in documento.extracao.paginas)
    else:
        assert any(pagina.textoBruto.strip() for pagina in documento.extracao.paginas)

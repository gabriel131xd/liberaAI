"""Todas as respostas deste módulo são simuladas."""
import httpx
import pytest

from app.integrations.camara.cliente import CamaraDeputados, ErroCamara, ErroHttpCamara


@pytest.mark.parametrize("metodo,sufixo", [
    ("obterProposicao", ""), ("obterAutores", "/autores"),
    ("obterTemas", "/temas"), ("obterTramitacoes", "/tramitacoes"),
])
def testeRecursos(metodo, sufixo):
    item = {"campo_simulado": None}
    envelope = {"dados": [item] if sufixo else item, "links": [], "extra": 1}

    def responder(requisicao):
        assert requisicao.url.path == "/api/v2/proposicoes/42" + sufixo
        assert requisicao.headers["Accept"] == "application/json"
        return httpx.Response(200, json=envelope)

    with CamaraDeputados(transporte=httpx.MockTransport(responder)) as cliente:
        assert getattr(cliente, metodo)(42) == envelope


def testePaginaVaziaEFiltros():
    envelope = {"dados": [], "links": [{"rel": "previous", "href": "https://example.test/"}]}

    def responder(requisicao):
        assert requisicao.url.path == "/api/v2/proposicoes"
        assert dict(requisicao.url.params) == dict(siglaTipo="PL", numero="4", ano="2020",
                                                pagina="2", itens="5")
        return httpx.Response(200, json=envelope)

    with CamaraDeputados(transporte=httpx.MockTransport(responder)) as cliente:
        assert cliente.listarProposicoes(numero=4, ano=2020, pagina=2, itens=5) == envelope


@pytest.mark.parametrize("codigoHttp", [400, 404, 429, 500, 503])
def testeCodigoHttp(codigoHttp):
    transporte = httpx.MockTransport(lambda _: httpx.Response(codigoHttp))
    with CamaraDeputados(transporte=transporte) as cliente, pytest.raises(ErroHttpCamara) as erro:
        cliente.listarProposicoes()
    assert erro.value.codigoHttp == codigoHttp


@pytest.mark.parametrize("envelope,mensagem", [
    (b"{", "JSON"), (b"[]", "dados"), (b'{"dados":{}}', "dados"),
    (b'{"dados":[1],"links":[]}', "dados"), (b'{"dados":[]}', "links"),
])
def testeFormato(envelope, mensagem):
    transporte = httpx.MockTransport(lambda _: httpx.Response(200, content=envelope))
    with CamaraDeputados(transporte=transporte) as cliente, pytest.raises(ErroCamara, match=mensagem):
        cliente.listarProposicoes()


@pytest.mark.parametrize("tipoErro,mensagem", [(httpx.ReadTimeout, "Tempo"), (httpx.ConnectError, "comunicação")])
def testeRede(tipoErro, mensagem):
    def falhar(requisicao):
        raise tipoErro("simulado", request=requisicao)

    with CamaraDeputados(transporte=httpx.MockTransport(falhar)) as cliente, pytest.raises(ErroCamara, match=mensagem):
        cliente.listarProposicoes()


@pytest.mark.parametrize("pagina,itens", [(0, 5), (1, 101), (1, 0)])
def testeLimites(pagina, itens):
    with CamaraDeputados(transporte=httpx.MockTransport(lambda _: pytest.fail())) as cliente:
        with pytest.raises(ValueError):
            cliente.listarProposicoes(pagina=pagina, itens=itens)

"""Descoberta sob demanda. Nenhum PDF é baixado para listar referências."""
from html.parser import HTMLParser

import httpx

from app.integrations.camara.cliente import CamaraDeputados


class LeitorLinksAvulsos(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.endereco = None
        self.rotulo = []

    def handle_starttag(self, etiqueta, atributos):
        if etiqueta == "a":
            self.endereco = dict(atributos).get("href")
            self.rotulo = []

    def handle_data(self, trecho):
        if self.endereco:
            self.rotulo.append(trecho)

    def handle_endtag(self, etiqueta):
        if etiqueta == "a" and self.endereco:
            if "".join(self.rotulo).strip().casefold() in {"avulso", "avulsos"}:
                self.urls.append(self.endereco)
            self.endereco = None


def listarReferencias(identificador: int):
    with CamaraDeputados() as cliente:
        relacionadas = cliente.obterRelacionadas(identificador)["dados"]
        movimentos = cliente.obterTramitacoes(identificador)["dados"]
    for relacionada in relacionadas:
        yield f"Relacionada {relacionada['id']} · {relacionada.get('siglaTipo')} · {relacionada.get('ementa') or ''} · {relacionada.get('uri')}"
    for movimento in movimentos:
        if movimento.get("url"):
            yield f"Movimento {movimento.get('sequencia')} · {movimento.get('dataHora')} · {movimento.get('despacho')} · {movimento['url']}"
    ficha = urlFicha(identificador)
    yield f"Ficha oficial · {ficha}"
    try:
        urls = urlsDosAvulsos(identificador)
    except httpx.HTTPError:
        yield "Ficha indisponível para verificação de avulsos."
        return
    for url in urls:
        yield f"Avulso indicado na ficha · {url}"
    if not urls:
        yield "Vínculo de avulso não localizado na ficha consultada."


def urlFicha(identificador):
    return f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={int(identificador)}"


def urlsDosAvulsos(identificador):
    resposta = httpx.get(urlFicha(identificador), timeout=20, trust_env=False)
    resposta.raise_for_status()
    leitor = LeitorLinksAvulsos()
    leitor.feed(resposta.text)
    urls = [resposta.url.join(endereco) for endereco in leitor.urls]
    return [str(urlOficial) for urlOficial in urls if urlOficial.scheme == "https" and urlOficial.host == "www.camara.leg.br"
            and not urlOficial.userinfo and urlOficial.port in (None, 443)]

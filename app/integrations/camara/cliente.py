"""Cliente síncrono para os envelopes JSON originais da Câmara."""

import httpx

URL_BASE = "https://dadosabertos.camara.leg.br/api/v2/"


class ErroCamara(Exception):
    """Falha de comunicação ou de contrato."""


class ErroHttpCamara(ErroCamara):
    def __init__(self, codigoHttp: int):
        self.codigoHttp = codigoHttp
        motivo = {
            400: "consulta inválida",
            404: "recurso ausente",
            429: "limite de requisições",
        }.get(codigoHttp, "resposta HTTP inesperada")
        if 500 <= codigoHttp <= 599:
            motivo = "falha no servidor da Câmara"
        super().__init__(f"HTTP {codigoHttp}: {motivo}")


class CamaraDeputados:
    """Consulta dados oficiais e mantém a estrutura original das respostas."""

    def __init__(self, urlBase=URL_BASE, tempoLimite=15.0, *, transporte=None):
        self._clienteHttp = httpx.Client(
            base_url=urlBase,
            timeout=tempoLimite,
            transport=transporte,
            headers={"Accept": "application/json"},
        )

    def __enter__(self):
        return self

    def __exit__(self, *argumentos):
        self.fechar()

    def fechar(self):
        self._clienteHttp.close()

    def _consultar(self, caminho, tipoEsperado=list, parametros=None):
        try:
            resposta = self._clienteHttp.get(caminho, params=parametros)
        except httpx.TimeoutException:
            raise ErroCamara("Tempo de resposta excedido") from None
        except httpx.RequestError:
            raise ErroCamara("Falha de comunicação com a Câmara") from None
        if not resposta.is_success:
            raise ErroHttpCamara(resposta.status_code)
        try:
            envelope = resposta.json()
        except ValueError:
            raise ErroCamara("JSON inválido") from None
        if not isinstance(envelope, dict) or not isinstance(envelope.get("dados"), tipoEsperado):
            raise ErroCamara("Estrutura inesperada em dados")
        if tipoEsperado is list and not all(isinstance(item, dict) for item in envelope["dados"]):
            raise ErroCamara("Registro inesperado em dados")
        referencias = envelope.get("links")
        if not isinstance(referencias, list) or not all(
            isinstance(link, dict) and isinstance(link.get("rel"), str)
            and isinstance(link.get("href"), str) for link in referencias
        ):
            raise ErroCamara("Estrutura inesperada em links")
        return envelope

    def listarProposicoes(
        self, *, siglaTipo="PL", numero=None, ano=None, pagina=1, itens=15,
        deputado=None, situacao=None,
    ):
        if pagina < 1 or not 1 <= itens <= 100:
            raise ValueError("Use página positiva e de 1 a 100 itens")
        parametros = {
            "siglaTipo": siglaTipo, "numero": numero, "ano": ano, "pagina": pagina,
            "itens": itens, "idDeputadoAutor": deputado, "codSituacao": situacao,
        }
        filtros = {chave: valor for chave, valor in parametros.items() if valor is not None}
        return self._consultar("proposicoes", parametros=filtros)

    def obterProposicao(self, identificador: int):
        return self._consultar(f"proposicoes/{int(identificador)}", dict)

    def obterAutores(self, identificador: int):
        return self._consultar(f"proposicoes/{int(identificador)}/autores")

    def obterTramitacoes(self, identificador: int):
        return self._consultar(f"proposicoes/{int(identificador)}/tramitacoes")

    def obterTemas(self, identificador: int):
        return self._consultar(f"proposicoes/{int(identificador)}/temas")

    def obterRelacionadas(self, identificador: int):
        return self._consultar(f"proposicoes/{int(identificador)}/relacionadas")

    def listarDeputados(self, nome="", ano=None, pagina=1, itens=25):
        parametros = {"pagina": pagina, "itens": itens, "ordenarPor": "nome", "ordem": "asc"}
        if nome.strip():
            parametros["nome"] = nome.strip()
        if ano:
            parametros.update(dataInicio=f"{ano}-01-01", dataFim=f"{ano}-12-31")
        return self._consultar("deputados", parametros=parametros)

    def listarVotacoes(self, identificador):
        return self._consultar(f"proposicoes/{int(identificador)}/votacoes")

    def listarSituacoes(self):
        return self._consultar("referencias/proposicoes/codSituacao")

    def listarTiposProposicao(self):
        return self._consultar("referencias/proposicoes/siglaTipo")

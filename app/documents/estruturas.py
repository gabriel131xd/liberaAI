from dataclasses import dataclass
from datetime import datetime


class ErroDocumento(Exception):
    """Falha identificada durante a obtenção ou leitura da peça."""


@dataclass
class ArquivoRecuperado:
    conteudo: bytes
    urlFinal: str
    tipoConteudo: str
    recuperadoEm: datetime
    sha256: str


@dataclass
class PaginaDocumento:
    numero: int
    textoBruto: str
    texto: str
    avisos: list[str]


@dataclass
class ExtracaoDocumental:
    paginas: list[PaginaDocumento]
    situacao: str
    avisos: list[str]

    @property
    def textoBruto(self):
        return "\f".join(pagina.textoBruto for pagina in self.paginas)

    @property
    def texto(self):
        return "\f".join(pagina.texto for pagina in self.paginas)

    @property
    def caracteres(self):
        return sum(len(pagina.textoBruto) for pagina in self.paginas)

    @property
    def palavras(self):
        return len(self.textoBruto.split())

    @property
    def tokensEstimados(self):
        return (self.caracteres + 3) // 4

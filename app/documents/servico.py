from dataclasses import dataclass

from app.integrations.camara.cliente import CamaraDeputados

from .estruturas import ArquivoRecuperado, ErroDocumento, ExtracaoDocumental
from .extrator import extrairTexto
from .transferencia import baixarDocumento


@dataclass
class DocumentoLegislativo:
    """Vincula a ficha oficial aos bytes recuperados e ao texto extraído."""

    dadosOficiais: dict
    arquivo: ArquivoRecuperado
    extracao: ExtracaoDocumental
    versao: str = "não confirmada"


def recuperarDocumento(identificador: int, *, limiteBytes=20 * 1024**2) -> DocumentoLegislativo:
    """Usa a referência de inteiro teor da ficha oficial da proposição."""
    with CamaraDeputados() as cliente:
        dadosOficiais = cliente.obterProposicao(identificador)["dados"]
    if dadosOficiais.get("id") != identificador or not dadosOficiais.get("urlInteiroTeor"):
        raise ErroDocumento("Referência oficial ausente ou incompatível")
    arquivo = baixarDocumento(dadosOficiais["urlInteiroTeor"], limiteBytes=limiteBytes)
    return DocumentoLegislativo(dadosOficiais, arquivo, extrairTexto(arquivo.conteudo))

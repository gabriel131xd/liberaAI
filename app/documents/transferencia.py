import hashlib
from datetime import UTC, datetime

import httpx

from .estruturas import ErroDocumento, ArquivoRecuperado


def baixarDocumento(url: str, *, limiteBytes=20 * 1024**2, transporte=None) -> ArquivoRecuperado:
    """Recupera uma peça da Câmara com limite de tamanho e validação da origem."""
    try:
        with httpx.Client(timeout=30, trust_env=False, transport=transporte,
                          headers={"Accept-Encoding": "identity"}) as cliente:
            destino = httpx.URL(url)
            for _ in range(5):
                # Valida também o destino de cada redirecionamento antes de acessá-lo.
                if (destino.scheme != "https" or destino.host != "www.camara.leg.br"
                        or destino.port not in (None, 443) or destino.userinfo):
                    raise ErroDocumento("Destino não autorizado")
                with cliente.stream("GET", destino) as resposta:
                    if resposta.has_redirect_location:
                        destino = destino.join(resposta.headers["location"])
                        continue
                    if resposta.status_code != 200:
                        raise ErroDocumento(f"Documento indisponível: HTTP {resposta.status_code}")
                    tipoConteudo = resposta.headers.get("content-type", "")
                    if tipoConteudo.split(";")[0].strip().lower() not in ("application/pdf", "application/octet-stream"):
                        raise ErroDocumento(f"Formato não suportado: {tipoConteudo or 'Content-Type ausente'}")
                    if resposta.headers.get("content-encoding", "identity").lower() != "identity":
                        raise ErroDocumento("Codificação de transporte não suportada")
                    tamanhoDeclarado = resposta.headers.get("content-length")
                    if tamanhoDeclarado and (not tamanhoDeclarado.isdecimal() or int(tamanhoDeclarado) > limiteBytes):
                        raise ErroDocumento("Tamanho declarado inválido ou acima do limite")
                    conteudo = bytearray()
                    for bloco in resposta.iter_bytes(chunk_size=65536):
                        if len(conteudo) + len(bloco) > limiteBytes:
                            raise ErroDocumento("Documento acima do limite")
                        conteudo.extend(bloco)
                    if not conteudo:
                        raise ErroDocumento("Arquivo vazio")
                    if not conteudo.startswith(b"%PDF-"):
                        raise ErroDocumento("Conteúdo sem assinatura PDF")
                    return ArquivoRecuperado(bytes(conteudo), str(destino), tipoConteudo, datetime.now(UTC),
                                    hashlib.sha256(conteudo).hexdigest())
            raise ErroDocumento("Limite de redirecionamentos")
    except httpx.TimeoutException:
        raise ErroDocumento("Tempo limite (timeout) excedido ao baixar o documento.") from None
    except (httpx.RequestError, httpx.InvalidURL) as erro:
        raise ErroDocumento(f"Falha de comunicação: {type(erro).__name__}") from None

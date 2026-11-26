import pymupdf

from .estruturas import ErroDocumento, ExtracaoDocumental, PaginaDocumento


def extrairTexto(conteudo: bytes) -> ExtracaoDocumental:
    """Preserva a camada textual de cada página e registra falhas de leitura."""
    paginas = []
    avisos = []
    try:
        with pymupdf.open(stream=conteudo, filetype="pdf") as pdf:
            if not pdf.is_pdf or not pdf.page_count or pdf.needs_pass:
                raise ErroDocumento("Documento inválido, vazio ou protegido")
            if pdf.is_repaired:
                avisos.append("O leitor precisou reparar a estrutura do PDF")
            for indicePagina in range(pdf.page_count):
                avisosPagina = []
                textoBruto = ""
                try:
                    textoBruto = pdf[indicePagina].get_text("text", sort=False)
                except (RuntimeError, ValueError):
                    avisosPagina.append("Falha na extração da página")
                if not textoBruto.strip():
                    avisosPagina.append("Página sem texto extraível")
                if "\ufffd" in textoBruto or any(ord(caractere) < 32 and caractere not in "\n\r\t" for caractere in textoBruto):
                    avisosPagina.append("Caracteres potencialmente ilegíveis")
                # Uniformiza finais de linha sem remover conteúdo da peça.
                textoTratado = textoBruto.replace("\r\n", "\n").replace("\r", "\n")
                paginas.append(PaginaDocumento(indicePagina + 1, textoBruto, textoTratado, avisosPagina))
    except (RuntimeError, ValueError) as erro:
        raise ErroDocumento("PDF corrompido ou ilegível") from erro
    situacao = "texto extraído; fidelidade requer conferência"
    if avisos or any(pagina.avisos for pagina in paginas):
        situacao = "extração parcial ou incerta"
    if not any(pagina.textoBruto.strip() for pagina in paginas):
        situacao = "sem texto extraível"
    return ExtracaoDocumental(paginas, situacao, avisos)

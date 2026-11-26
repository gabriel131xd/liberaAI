import re

from app.ai.cliente import ClienteIaLocal
from app.ai.instrucoes import VERSAO_ATUAL
from app.documents.estruturas import ErroDocumento

from .fonte import selecionarFonte
from .processamento import processarFonte


def analisarProposicao(identificador, peca=None, paginaInicial=None, paginaFinal=None, secao=None, motivoEmenta=None):
    return analisarFonte(selecionarFonte(identificador, peca, motivoEmenta), paginaInicial, paginaFinal, secao)


def selecionarRecorte(fonte, paginaInicial=None, paginaFinal=None, secao=None):
    """Exige um intervalo explícito quando a fonte pode reunir versões distintas."""
    _, documento, paginas = fonte
    if documento.get("exige_recorte") and (not secao or paginaInicial is None or paginaFinal is None):
        raise ErroDocumento("Para avulso ou movimento, indique --inicio, --fim e --secao da mesma peça.")
    paginaInicial = paginas[0].numero if paginaInicial is None else paginaInicial
    paginaFinal = paginas[-1].numero if paginaFinal is None else paginaFinal
    if not paginas[0].numero <= paginaInicial <= paginaFinal <= paginas[-1].numero:
        raise ErroDocumento("Intervalo de páginas inválido")
    paginasDoRecorte = [pagina for pagina in paginas if paginaInicial <= pagina.numero <= paginaFinal]
    if paginaInicial > paginas[0].numero and not secao:
        raise ErroDocumento("Recorte sem o início do documento: informe --secao após conferir a fonte.")
    marcadores = {marcador.group(1).strip() for pagina in paginasDoRecorte for marcador in re.finditer(
        r"(?im)^\s*((?:RDF|EMS|SBT)\b[^\n]{0,80}?)\s+POSSUI INTEIRO TEOR", pagina.texto)}
    if len(marcadores) > 1:
        raise ErroDocumento("O intervalo contém marcadores de peças distintas. Selecione somente uma versão.")
    return paginasDoRecorte


def analisarFonte(fonte, paginaInicial=None, paginaFinal=None, secao=None, versao=VERSAO_ATUAL):
    dadosOficiais, documento, paginas = fonte
    paginasDoRecorte = selecionarRecorte(fonte, paginaInicial, paginaFinal, secao)
    paginaInicial, paginaFinal = paginasDoRecorte[0].numero, paginasDoRecorte[-1].numero
    avisos = list(documento.get("avisos", []))
    for pagina in paginasDoRecorte:
        avisos.extend(f"Página {pagina.numero}: {aviso}" for aviso in pagina.avisos)
    resultado = {"proposicao_oficial": dadosOficiais, "documento": documento, "recorte": [paginaInicial, paginaFinal],
              "limitacoes": avisos, "paginas_fora_do_recorte": [
                  pagina.numero for pagina in paginas if not paginaInicial <= pagina.numero <= paginaFinal]}
    if resultado["paginas_fora_do_recorte"]:
        avisos.append("Recorte parcial: dispositivos podem continuar fora do intervalo.")
    if documento.get("limitacao"):
        avisos.append(documento["limitacao"])
    with ClienteIaLocal() as modelo:
        processarFonte(modelo, paginasDoRecorte, documento["identificacao"],
                       secao or ("ementa" if paginaInicial == 0 else "texto da peça"), resultado, versao)
    if any(pagina.avisos for pagina in paginasDoRecorte) or documento.get("avisos"):
        resultado["cobertura_extracao"] = "parcial ou incerta"
    else:
        resultado["cobertura_extracao"] = "camada textual do recorte; fidelidade sujeita a revisão"
    resultado["paginas_com_geracao_concluida"] = sorted({
        numeroPagina for geracao in resultado["geracoes"] if geracao["etapa"] == "parte" and "resposta" in geracao
        for numeroPagina in geracao["paginas"]})
    return resultado

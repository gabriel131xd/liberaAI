"""Sinais verificáveis de rastreabilidade para a avaliação humana."""

import json
import re
import unicodedata
from collections import defaultdict

from app.ai.cliente import ErroInferencia

MARCADOR_PAGINA = re.compile(r"(?m)^\[p\. (\d+)\][ \t]*")
REFERENCIA_RESPOSTA = re.compile(r"\[p\.\s*(\d+)\]", re.IGNORECASE)
CITACAO = re.compile(r"«([^»]+)»")
NUMERO = re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?!\w)")
CONDICAO = re.compile(r"\b(?:exceto|salvo|desde que|somente se|apenas se|ressalv\w*)\b")
ALTERNATIVA = re.compile(r"\b(?:ou|alternativ\w*|qualquer (?:um|uma))\b")
DESEMPATE = re.compile(r"\b(?:o que (?:for|ocorrer) (?:menor|maior|primeiro|por ultimo))\b")
PRAZO = re.compile(r"\b(\d+)(?:\s*\([^()]{1,70}\))?\s*(dias?|mes(?:es)?|anos?|horas?)\b")


def formatoComEvidencias(limite=6):
    """Restringe o formato pelo llama-server, mantendo a geração local."""
    ponto = {
        "type": "object", "additionalProperties": False,
        "required": ["pagina", "explicacao", "evidencia"],
        "properties": {
            "pagina": {"type": "integer"},
            "explicacao": {"type": "string", "minLength": 1, "maxLength": 240},
            "evidencia": {"type": "string", "minLength": 1, "maxLength": 215},
        },
    }
    return {"type": "json_schema", "schema": {
        "type": "object", "additionalProperties": False, "required": ["pontos"],
        "properties": {"pontos": {"type": "array", "maxItems": limite, "items": ponto}},
    }}


def apresentarPontos(resposta):
    """Produz a leitura humana sem alterar o registro bruto do modelo."""
    try:
        pontos = json.loads(resposta)["pontos"]
        if not isinstance(pontos, list):
            raise ValueError
        for ponto in pontos:
            if (type(ponto["pagina"]) is not int
                    or not all(isinstance(ponto[chave], str) and ponto[chave].strip()
                               for chave in ("explicacao", "evidencia"))):
                raise ValueError
        return "\n\n".join(
            f"[p. {ponto['pagina']}] {ponto['explicacao']}\nFonte: «{ponto['evidencia']}»"
            for ponto in pontos
        )
    except (KeyError, TypeError, ValueError):
        raise ErroInferencia("A resposta local não respeitou o formato de evidências.") from None


def normalizarEspacos(texto):
    return " ".join(unicodedata.normalize("NFKC", texto).casefold().split())


def localizarCitacao(citacao, fonte):
    if not citacao:
        return False
    inicio = r"(?<!\w)" if citacao[0].isalnum() else ""
    fim = r"(?!\w)" if citacao[-1].isalnum() else ""
    return bool(re.search(inicio + re.escape(citacao) + fim, fonte))


def separarFontes(texto):
    """Agrupa os trechos numerados que de fato entraram no contexto."""
    partes = MARCADOR_PAGINA.split(texto)
    fontes = defaultdict(list)
    for indice in range(1, len(partes), 2):
        fontes[int(partes[indice])].append(partes[indice + 1])
    return {pagina: "\n".join(trechos) for pagina, trechos in fontes.items()}


def conferirResposta(resposta, fontes, *, conferirCobertura=False):
    """Confere páginas, citações literais e números. O sentido exige revisão humana."""
    partes = REFERENCIA_RESPOSTA.split(resposta)
    paginasCitadas = set()
    evidenciasConfirmadas = 0
    pontosComEvidencia = 0
    avisos = []
    fontesNormalizadas = {pagina: normalizarEspacos(texto) for pagina, texto in fontes.items()}
    if len(partes) == 1:
        avisos.append("A resposta não apresentou evidência com indicação de página.")
    elif partes[0].strip(" \n\r\t-*"):
        avisos.append("Há texto antes do primeiro ponto com evidência.")
    for indice in range(1, len(partes), 2):
        pagina = int(partes[indice])
        paginasCitadas.add(pagina)
        trecho = partes[indice + 1]
        evidencias = [normalizarEspacos(citacao) for citacao in CITACAO.findall(trecho)]
        if pagina not in fontesNormalizadas:
            avisos.append(f"Página {pagina} citada fora do recorte usado.")
            continue
        confirmadas = [citacao for citacao in evidencias if localizarCitacao(citacao, fontesNormalizadas[pagina])]
        evidenciasConfirmadas += len(confirmadas)
        if not confirmadas or len(confirmadas) != len(evidencias):
            avisos.append(f"Evidência ausente ou não literal na página {pagina}.")
        else:
            pontosComEvidencia += 1
            afirmacao = normalizarEspacos(CITACAO.sub("", trecho))
            fonteConfirmada = " ".join(confirmadas)
            if CONDICAO.search(fonteConfirmada) and not (
                CONDICAO.search(afirmacao) or re.search(r"\b(?:se|quando|exce[cç]\w*)\b", afirmacao)
            ):
                avisos.append(f"Possível omissão de condição ou exceção na página {pagina}.")
            if ALTERNATIVA.search(fonteConfirmada) and not ALTERNATIVA.search(afirmacao):
                avisos.append(f"Confira se as alternativas da página {pagina} foram preservadas.")
            desempate = DESEMPATE.search(afirmacao)
            if desempate and desempate.group() not in fontesNormalizadas[pagina]:
                avisos.append(f"Critério de desempate sem apoio literal na página {pagina}.")
    textoSemMarcadores = REFERENCIA_RESPOSTA.sub("", CITACAO.sub("", resposta))
    textoFonte = " ".join(fontesNormalizadas.values())
    numerosFonte = set(NUMERO.findall(textoFonte))
    numerosSemFonte = sorted(set(NUMERO.findall(textoSemMarcadores)) - numerosFonte)
    if numerosSemFonte:
        avisos.append(f"Números sem correspondência literal no recorte: {', '.join(numerosSemFonte)}.")
    if conferirCobertura:
        prazosDaFonte = set(PRAZO.findall(textoFonte))
        prazosExplicados = set(PRAZO.findall(normalizarEspacos(textoSemMarcadores)))
        for prazo, unidade in sorted(prazosDaFonte - prazosExplicados):
            avisos.append(f"Confira o prazo de {prazo} {unidade} da fonte, sem correspondência literal na explicação.")
    return {
        "paginas_citadas": sorted(paginasCitadas),
        "evidencias_confirmadas": evidenciasConfirmadas,
        "pontos_com_evidencia": pontosComEvidencia,
        "avisos": list(dict.fromkeys(avisos)),
    }

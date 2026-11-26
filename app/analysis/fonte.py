"""Seleção explícita da peça dentro das referências da proposição."""
from app.documents.transferencia import baixarDocumento
from app.documents.extrator import extrairTexto
from app.documents.referencias import urlsDosAvulsos
from app.documents.estruturas import ErroDocumento, PaginaDocumento
from app.integrations.camara.cliente import CamaraDeputados


def selecionarFonte(identificador, peca=None, motivoEmenta=None):
    """Confere o vínculo da peça com a proposição antes de recuperar o texto."""
    with CamaraDeputados() as camara:
        dadosOficiais = camara.obterProposicao(identificador)["dados"]
        relacionadas = camara.obterRelacionadas(identificador)["dados"]
        if dadosOficiais.get("id") != identificador:
            raise ErroDocumento("Identificação oficial incompatível")
        dadosPeca = dadosOficiais
        if peca not in (None, str(identificador)) and peca.isdecimal():
            if not any(str(relacionada.get("id")) == peca for relacionada in relacionadas):
                raise ErroDocumento("Peça sem vínculo na lista de relacionadas")
            dadosPeca = camara.obterProposicao(int(peca))["dados"]
            if str(dadosPeca.get("id")) != peca:
                raise ErroDocumento("ID da peça incompatível")
        url = dadosPeca.get("urlInteiroTeor")
        alternativas = [(relacionada["id"], relacionada["siglaTipo"]) for relacionada in relacionadas
                        if relacionada.get("siglaTipo") in {"EMS", "RDF", "SBT", "SBE-A", "SUB"}]
        if peca is None and alternativas:
            raise ErroDocumento(f"Escolha --peca {identificador} (principal) ou ID relacionado: {alternativas}")
        if peca is None and (relacionadas or any(
            movimento.get("url") and movimento["url"] != url for movimento in camara.obterTramitacoes(identificador)["dados"]
        ) or urlsDosAvulsos(identificador)):
            raise ErroDocumento("Referências alternativas disponíveis. Consulte app.documents --referencias e selecione --peca.")
        rotulo = f"{dadosPeca.get('siglaTipo')} {dadosPeca.get('numero')}/{dadosPeca.get('ano')} · ID {dadosPeca['id']}"
        composta = False
        if peca and not peca.isdecimal():
            prefixo, separador, numero = peca.partition(":")
            if not separador or not numero.isdecimal():
                raise ErroDocumento("Use ID, movimento:sequência ou avulso:posição")
            if prefixo == "movimento":
                urls = [movimento["url"] for movimento in camara.obterTramitacoes(identificador)["dados"]
                        if str(movimento.get("sequencia")) == numero and movimento.get("url")]
            elif prefixo == "avulso":
                urls = urlsDosAvulsos(identificador)[int(numero)-1:int(numero)] if int(numero)>0 else []
            else:
                urls = []
            if len(urls) != 1:
                raise ErroDocumento("Referência ausente ou ambígua")
            url, rotulo, composta = urls[0], peca, True
        metadados = {"identificacao": rotulo, "url": url, "dados_peca": dadosPeca if not composta else None,
                "exige_recorte": composta, "versao": "identificação da peça; vigência não inferida"}
        if url:
            arquivo = baixarDocumento(url)
            extracao = extrairTexto(arquivo.conteudo)
            metadados.update(sha256=arquivo.sha256, destino=arquivo.urlFinal, paginas=len(extracao.paginas),
                        situacao=extracao.situacao, avisos=extracao.avisos)
            if any(pagina.texto.strip() for pagina in extracao.paginas):
                return dadosOficiais, metadados, extracao.paginas
        movimentos = camara.obterTramitacoes(identificador)["dados"]
        avulsos = urlsDosAvulsos(identificador)
        haAlternativas = relacionadas or any(movimento.get("url") and movimento["url"] != url for movimento in movimentos) or avulsos
        if haAlternativas and not (motivoEmenta and motivoEmenta.strip()):
            raise ErroDocumento(
                "Peça sem texto. Consulte as alternativas com app.documents --referencias e escolha outra peça."
            )
        if not dadosOficiais.get("ementa"):
            raise ErroDocumento("Nenhuma peça textual ou ementa disponível")
        return dadosOficiais, {"identificacao": "ementa", "url": dadosOficiais.get("uri"), "paginas": 0,
                          "revisao_humana_das_alternativas": motivoEmenta,
                          "referencias_consultadas": {"relacionadas": len(relacionadas), "movimentos": len(movimentos),
                                                     "avulsos": avulsos},
                          "limitacao": "Explicação limitada à ementa; nenhuma peça adequada recuperada."}, [
            PaginaDocumento(0, dadosOficiais["ementa"], dadosOficiais["ementa"], [])]

import json
from unittest.mock import MagicMock, Mock

import gradio as gr
import pytest

from app.documents.estruturas import ErroDocumento, PaginaDocumento
from app.interface import cidadao, detalhe

URL = "https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=123"


def dadosDeTeste():
    return {
        "id": 1,
        "dados": {"siglaTipo": "PL", "numero": 1, "ano": 2026, "urlInteiroTeor": URL,
                  "dataApresentacao": "2026-02-09T19:05",
                  "statusProposicao": {"descricaoSituacao": "Aguardando Encaminhamento"}},
        "autores": [{"nome": "<Autora>"}], "votações": [], "tramitações": [], "relacionadas": [],
        "avisos": [], "ficha": "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=1",
    }


def testePrincipalDifereDeReferenciasProcedimentais():
    oficial = dadosDeTeste()
    oficial["tramitações"] = [{"url": URL + "4", "despacho": "Apensação"}]
    assert cidadao.escolherPeca(oficial) == "1"
    oficial["tramitações"].append({"url": URL + "5", "descricaoTramitacao": "Recebimento - Redação Final"})
    with pytest.raises(ErroDocumento, match="versões diferentes"):
        cidadao.escolherPeca(oficial)
    oficial["relacionadas"] = [{"siglaTipo": "EMS"}]
    with pytest.raises(ErroDocumento, match="mais de uma versão"):
        cidadao.escolherPeca(oficial)


def testeConsultaIncompletaNaoEscolhePeca():
    oficial = dadosDeTeste()
    oficial["avisos"] = ["Cobertura parcial em relacionadas. Consulte a ficha oficial."]
    with pytest.raises(ErroDocumento, match="todas as referências"):
        cidadao.escolherPeca(oficial)


def testeJustificativaNaoEntraNaFonteDaConversa():
    texto = "PROJETO DE LEI\nO Congresso Nacional decreta:\nArt. 1º A regra proposta.\nJUSTIFICAÇÃO\nCitação"
    paginas = [PaginaDocumento(1, texto, texto, []), PaginaDocumento(2, "Mais citações", "Mais citações", [])]
    resultado = cidadao.separarTextoNormativo(paginas)
    assert [(pagina.numero, pagina.texto) for pagina in resultado] == [(1, "Art. 1º A regra proposta.")]
    assert paginas[0].texto == texto


def testeConferenciaOmiteCamposEConfirmacoesSemApoio():
    texto = "Art. 1º O benefício é pago por 12 meses, salvo em caso de fraude."
    campos = {
        "titulo": {"trecho": 1, "explicacao": "Prazo do benefício"},
        "proposta": {"trecho": 1, "explicacao": "O texto propõe pagar por 12 meses."},
        "mudanca": {"trecho": 1, "explicacao": "O texto propõe pagar por 30 meses."},
        "afetados": {"trecho": 2, "explicacao": "Pessoas beneficiadas."},
        "vigencia": {"trecho": 1, "explicacao": "Já está valendo."},
    }
    assert cidadao.conferirCampos(json.dumps(campos), {1: texto}, {1: (1, texto)}) == {"titulo": "Prazo do benefício"}


def testeConferenciaPreservaNaturezaDaRegraESeuPublico():
    texto = "A posse por condômino não configura intenção de dono quando decorre de relação familiar ou sucessória."
    campos = dict.fromkeys(cidadao.CAMPOS)
    campos["proposta"] = {"trecho": 1, "explicacao": "A posse não gera usucapião em relação familiar ou sucessória."}
    campos["mudanca"] = {"trecho": 1, "explicacao": "A regra proíbe a posse em relação familiar ou sucessória."}
    campos["afetados"] = {"trecho": 1, "explicacao": "Condôminos e herdeiros em relação familiar ou sucessória."}
    assert cidadao.conferirCampos(json.dumps(campos), {1: texto}, {1: (1, texto)}) == {}
    campos["afetados"]["explicacao"] = "Condôminos em relação familiar ou sucessória."
    confirmado = cidadao.conferirCampos(json.dumps(campos), {1: texto}, {1: (1, texto)})
    assert confirmado == {"afetados": "Condôminos em relação familiar ou sucessória."}


def testeTituloApresentaAssuntoSemAnteciparMudancaNaLei():
    texto = "A Lei nº 10.406 passa a vigorar acrescida do seguinte art. 1.238-A sobre usucapião."
    campos = dict.fromkeys(cidadao.CAMPOS)
    campos["titulo"] = {"trecho": 1, "explicacao": "O artigo 1.238-A foi acrescido com uma nova regra sobre usucapião."}
    campos["proposta"] = {"trecho": 1, "explicacao": "O artigo 1.238-A foi incluído na lei."}
    assert cidadao.conferirCampos(json.dumps(campos), {1: texto}, {1: (1, texto)}) == {
        "titulo": "Proposta sobre usucapião",
    }


def testeChatPreservaHistoricoERespondeSemInventar(monkeypatch):
    oficial = dadosDeTeste()
    anterior = [{"role": "user", "content": "Antes?"}, {"role": "assistant", "content": "Informação anterior."}]
    responder = Mock(return_value="Resposta conferida.")
    monkeypatch.setattr(cidadao, "responderSobreTexto", responder)
    recente, campo = cidadao.responderCidadao("E na prática?", oficial, {"fonte": True}, None, anterior)
    assert recente[:2] == anterior and recente[-1]["content"] == "Resposta conferida." and campo == ""
    assert responder.call_args.args[-1] == anterior
    semFonte, _ = cidadao.responderCidadao("Quem pode ser afetado?", oficial, {}, None, [])
    assert semFonte[-1]["content"] == cidadao.SEM_INFORMACAO
    esperando, _ = cidadao.responderCidadao("Quem pode ser afetado?", oficial, {}, ("tarefa",), [])
    assert "Aguarde" in esperando[-1]["content"]


def testeDetalheMostraOficialAntesDaGeracaoEReiniciaChat(monkeypatch):
    oficial = dadosDeTeste()
    monkeypatch.setattr(detalhe, "carregarOficial", lambda identificador: oficial)
    with gr.Blocks():
        tela = detalhe.DetalheCidadao()
    monkeypatch.setattr(tela.cache, "iniciar", lambda oficial: (1, "fonte"))
    monkeypatch.setattr(tela.cache, "consultar", lambda chave: None)
    saida = tela.abrir({"id": 1})
    assert saida[1] == (1, "fonte")
    assert "09/02/2026" in saida[4] and "&lt;Autora&gt;" in saida[4] and URL in saida[4]
    assert "Preparando a explicação" in saida[5]
    assert saida[-3:] == ([], "", {"active": True, "__type__": "update"})
    monkeypatch.setattr(tela.cache, "consultar", lambda chave: {"campos": {"titulo": "Título confirmado"}})
    resposta = tela.consultar(oficial, (1, "fonte"))
    assert "Título confirmado" in resposta[2] and "Isso já está valendo?" in resposta[3]
    assert "__type__" in tela.consultar({}, None)[0]


def testeContextoLimitaPorPaginaEInformaCobertura(monkeypatch):
    oficial = dadosDeTeste()
    paginas = [PaginaDocumento(1, "primeira", "primeira", []), PaginaDocumento(2, "segunda", "segunda", [])]
    fonte = (oficial["dados"], {"url": URL, "paginas": 2}, paginas)
    selecao = Mock(return_value=fonte)
    monkeypatch.setattr(cidadao, "selecionarFonte", selecao)
    modelo = MagicMock()
    modelo.__enter__.return_value = modelo
    modelo.requisitar.return_value = {"default_generation_settings": {"n_ctx": 720}}
    modelo.configuracao = {"LLAMA_MAX_TOKENS": "100"}
    modelo.contarTokensConversa.side_effect = lambda mensagens: 80 * mensagens[1]["content"].count("[Trecho")
    modelo.conversar.side_effect = [
        {"choices": [{"message": {"content": json.dumps(dict.fromkeys(cidadao.CAMPOS))}}]},
        {"choices": [{"message": {"content": json.dumps({
            "titulo": {"trecho": 1, "explicacao": "Título breve"}, "proposta": None,
        })}}]},
    ]
    monkeypatch.setattr(cidadao, "ClienteIaLocal", lambda: modelo)
    resultado = cidadao.prepararExplicacao(oficial)
    selecao.assert_called_once_with(1, "1")
    assert resultado["fonte"][2] == paginas[:1]
    assert "1 de 2 páginas" in resultado["aviso"]
    assert resultado["campos"] == {"titulo": "Título breve"}
    assert modelo.conversar.call_count == 2
    assert "segunda" not in modelo.conversar.call_args.args[0][1]["content"]

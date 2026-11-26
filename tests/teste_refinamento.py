from unittest.mock import MagicMock

from app.ai.cliente import GeracaoIncompleta
from app.ai.instrucoes import VERSAO_ANTERIOR, VERSAO_ATUAL
from app.analysis.conferencia import apresentarPontos, conferirResposta
from app.analysis.processamento import montarMensagens, processarFonte
from app.documents.estruturas import PaginaDocumento
from app.interface import conversa, painel


def testeConferenciaSinalizaOmissaoEInovacao():
    fontes = {1: "A cedente responde por 24 meses, salvo se houver anuência."}
    resposta = '[p. 1] A cedente responde por 30 meses. Fonte: «24 meses, salvo se houver anuência.»'
    avisos = conferirResposta(resposta, fontes)["avisos"]
    assert any("omissão" in aviso for aviso in avisos)
    assert any("30" in aviso for aviso in avisos)


def testeConferenciaDaPaginaEvidenciaELimite():
    bruto = '{"pontos":[{"pagina":2,"explicacao":"Prazo de 180 dias.","evidencia":"180 dias"}]}'
    resposta = apresentarPontos(bruto)
    assert not conferirResposta(resposta, {2: "Prazo de  180\ndias"})["avisos"]
    assert "fora do recorte" in conferirResposta(resposta, {1: "180 dias"})["avisos"][0]
    assert "não literal" in conferirResposta(resposta, {2: "30 dias"})["avisos"][0]
    assert "não literal" in conferirResposta(resposta, {2: "180 diastemas"})["avisos"][0]


def testeVerificaPrazoMesmoForaDaCitacao():
    fontes = {2: "A escola poderá abrir. A regra entra em vigor após 180 (cento e oitenta) dias."}
    resposta = "[p. 2] Permite abrir. Fonte: «A escola poderá abrir.»"
    assert conferirResposta(resposta, fontes)["avisos"] == []
    assert "180 dias" in conferirResposta(resposta, fontes, conferirCobertura=True)["avisos"][0]


def testeDatasOficiaisEConsultaDeVigencia():
    oficial = {"dados": {"dataApresentacao": "2007-12-12", "statusProposicao": {"dataHora": "2024-02-22"}},
               "ficha": "ficha"}
    assert "2007-12-12" in conversa.respostaOficial("Quando foi apresentado?", oficial)
    assert "2024-02-22" in conversa.respostaOficial("Qual a data da última movimentação?", oficial)
    assert conversa.respostaOficial("Quando entraria em vigor?", oficial) is None


def testeGeraSomenteVersaoSolicitadaEMantemTruncamento():
    modelo = MagicMock()
    modelo.configuracao = {"LLAMA_MAX_TOKENS": 30}
    modelo.requisitar.return_value = {"default_generation_settings": {"n_ctx": 200}}
    modelo.contarTokensConversa.return_value = 50
    modelo.conversar.side_effect = GeracaoIncompleta("length", {
        "choices": [{"message": {"content": "recorte bruto"}}],
    })
    resultado = {}
    pagina = PaginaDocumento(1, "São permitidas visitas.", "São permitidas visitas.", [])
    processarFonte(modelo, [pagina], "Peça", "dispositivos", resultado)
    assert resultado["versao_prompt"] == VERSAO_ATUAL
    assert resultado["geracoes"][0]["resposta_incompleta"] == "recorte bruto"
    assert resultado["situacao"] == "incompleta" and resultado["falha"]
    assert modelo.conversar.call_count == 1
    assert modelo.conversar.call_args.kwargs["formato"]["type"] == "json_schema"


def testeComparacaoUsaMesmaFonteERecorte(monkeypatch):
    analisar = MagicMock(return_value={"recorte": [1, 1], "situacao": "concluída",
                                        "segundos": 1, "geracoes": [], "limitacoes": []})
    monkeypatch.setattr(painel, "analisarFonte", analisar)
    fonte = ({}, {"identificacao": "Peça"}, [])
    _, _, metricas = painel.compararPrompts({"fonte": fonte}, "1", "1", "Dispositivos")
    assert list(metricas["versoes"]) == [VERSAO_ANTERIOR, VERSAO_ATUAL]
    assert all(chamada.args == (fonte, 1, 1, "Dispositivos") for chamada in analisar.call_args_list)
    assert [chamada.kwargs["versao"] for chamada in analisar.call_args_list] == [VERSAO_ANTERIOR, VERSAO_ATUAL]
    assert montarMensagens("Peça", "Seção", "Trecho", False, VERSAO_ANTERIOR)[1] == (
        montarMensagens("Peça", "Seção", "Trecho", False, VERSAO_ATUAL)[1]
    )


def testeChatRetemRespostaSemEvidencia(monkeypatch):
    modelo = MagicMock()
    modelo.__enter__.return_value = modelo
    modelo.configuracao = {"LLAMA_MAX_TOKENS": 30}
    modelo.requisitar.return_value = {"default_generation_settings": {"n_ctx": 200}}
    modelo.contarTokensConversa.return_value = 50
    bruto = '{"pontos":[{"pagina":5,"explicacao":"A regra permite viagens.","evidencia":"permite viagens"}]}'
    modelo.conversar.return_value = {"choices": [{"message": {"content": bruto}}]}
    monkeypatch.setattr(conversa, "ClienteIaLocal", lambda: modelo)
    pagina = PaginaDocumento(1, "A regra permite visitas.", "A regra permite visitas.", [])
    fonte = ({}, {"identificacao": "Peça", "url": "https://exemplo.test"}, [pagina])
    registro = {}
    resposta = conversa.responder("O que é permitido?", {"dados": {}}, fonte,
                                  (1, 1, None), None, [], registro=registro)
    assert "Não consegui confirmar" in resposta and "viagens" not in resposta
    assert registro["resposta_bruta"] == bruto

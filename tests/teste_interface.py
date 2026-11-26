from unittest.mock import MagicMock

import pytest

from app.integrations.camara.cliente import ErroHttpCamara
from app.interface import legislativo, navegacao, painel
from app.interface.conversa import respostaOficial


def clienteSimulado(monkeypatch, paginas):
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.listarProposicoes.side_effect = paginas
    monkeypatch.setattr(legislativo, "CamaraDeputados", lambda: cliente)
    return cliente


def pagina(identificadores, proxima=False):
    return {"dados": [{"id": identificador} for identificador in identificadores],
            "links": [{"rel": "next"}] if proxima else []}


def testeContarAutoresComIdsRepetidos(monkeypatch):
    cliente = clienteSimulado(monkeypatch, [pagina([1, 2], True), pagina([2, 3])])
    assert legislativo.contarAutor(2024, 22).startswith("3 proposições")
    assert cliente.listarProposicoes.call_args.kwargs["deputado"] == 22


def testeContagemZeroEConsultaIncompleta(monkeypatch):
    clienteSimulado(monkeypatch, [pagina([])])
    assert legislativo.contarAutor(2024, 22).startswith("0 proposições")
    clienteSimulado(monkeypatch, [pagina([1], True), ErroHttpCamara(429)])
    assert "Contagem incompleta" in legislativo.contarAutor(2024, 22)
    clienteSimulado(monkeypatch, [ErroHttpCamara(503)])
    assert painel.contar(2024, 22).startswith("Consulta sem total confirmado")


def testeChatUsaSituacaoEAutoriaOficiais():
    oficial = {"dados": {"statusProposicao": {"descricaoSituacao": "Arquivada"}},
               "autores": [{"nome": "Autor simulado"}], "votações": None, "ficha": "ficha"}
    assert "Arquivada" in respostaOficial("Qual a situação?", oficial)
    assert "Autor simulado" in respostaOficial("Quem assinou?", oficial)
    assert "indisponíveis" in respostaOficial("Foi aprovado?", oficial)


@pytest.mark.parametrize("identificador", [1, 2])
def testeAbrirReiniciaEstadoDocumental(monkeypatch, identificador):
    def carregar(identificador):
        return {"id": identificador, "dados": {"siglaTipo": "PL", "numero": identificador, "ano": 2024},
                "ficha": "simulada", "autores": [], "tramitações": [], "votações": [],
                "relacionadas": [], "avisos": []}

    monkeypatch.setattr(painel, "carregarOficial", carregar)
    monkeypatch.setattr(painel, "opcoesPecas", lambda _: [])
    oficial, documento, ficha, *_ = painel.abrir(identificador)
    assert oficial["id"] == identificador and documento == {} and f"ID {identificador}" in ficha


def testeOpcoesIncluemAvulsoETramitacao(monkeypatch):
    monkeypatch.setattr(legislativo, "urlsDosAvulsos", lambda _: ["https://www.camara.leg.br/"])
    documento = {"id": 1, "dados": {"siglaTipo": "PL", "numero": 1, "ano": 2024},
           "relacionadas": [{"id": 9, "siglaTipo": "RDF", "numero": 1, "ano": 0}],
           "tramitações": [{"sequencia": 12, "url": "exemplo", "dataHora": "2024-01-01"}]}
    assert [valor for _, valor in legislativo.opcoesPecas(documento)] == ["1", "9", "movimento:12", "avulso:1"]


def testeBlocosDaInterface():
    interface = painel.criarInterface()
    abas = [c["props"]["label"] for c in interface.config["components"] if c["type"] == "tabitem"]
    assert abas == ["Início", "Deputados", "Por ano", "Laboratório de IA"]


def testeFiltroConfereSituacaoAtual(monkeypatch):
    cliente = clienteSimulado(monkeypatch, [pagina([1, 2], True)])
    cliente.obterProposicao.side_effect = [
        {"dados": {"statusProposicao": {"codSituacao": 1140}}},
        {"dados": {"statusProposicao": {"codSituacao": 926}}},
    ]
    cliente.obterAutores.return_value = {"dados": []}
    envelope, linhas, avisos = legislativo.listarAno(2024, "PL", None, "1140", 1)
    assert [item["id"] for item in envelope["dados"]] == [1]
    assert len(linhas) == 1 and avisos == 0 and legislativo.temProxima(envelope)


def testePerguntaSobreAutorizacaoSegueParaModelo():
    assert respostaOficial("O que o projeto autoriza?", {}) is None


def testeBuscaDeputadoSemAnoNaoEnviaIntervalo(monkeypatch):
    cliente = clienteSimulado(monkeypatch, [])
    cliente.listarDeputados.return_value = {"dados": [], "links": []}
    itens, proxima, mensagem = navegacao.consultarDeputados("Nome simulado", "", 1)
    cliente.listarDeputados.assert_called_once_with("Nome simulado", None, 1, itens=10)
    assert not itens and not proxima
    assert "deputados em exercício" in mensagem


def testeAnoZeroRetornaErroEmPortugues():
    with pytest.raises(ValueError, match="o ano de exercício"):
        navegacao.consultarDeputados("Nome simulado", "0", 1)


def testeRecorteVazioOuInvalido():
    assert painel.recorteDaInterface("", "", "") == (None, None, None)
    _, _, _, aviso = painel.explicar({"fonte": True}, "0", "", "")
    assert "a primeira página" in aviso


def testeComponentesVaziosETrocaAutomatica():
    interface = painel.criarInterface()
    componentes = {item["id"]: item for item in interface.config["components"]}
    opcionais = [item for item in componentes.values()
                 if "(opcional)" in (item["props"].get("label") or "")]
    assert len(opcionais) == 4
    assert all(item["type"] == "textbox" and item["props"]["value"] == "" for item in opcionais)
    eventos = {dep["api_name"]: dep for dep in interface.config["dependencies"] if dep["api_name"]}
    for nome in ("deputadosConsultar", "proposicoesAnoConsultar"):
        assert any(evento == "select" and componentes[id]["type"] == "tabitem"
                   for id, evento in eventos[nome]["targets"])
    for nome in ("deputados", "proposicoesDeputado", "proposicoesAno"):
        assert f"{nome}Anterior" in eventos and f"{nome}Proxima" in eventos
        assert f"{nome}Selecionar1" in eventos
    assert not any(item["type"] == "number" and item["props"].get("minimum") == 1
                   and not item["props"].get("value") for item in componentes.values())

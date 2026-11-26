"""Simulações de integração. Nenhuma resposta deste módulo é evidência legislativa."""
from unittest.mock import MagicMock

import pytest

from app.ai.cliente import ErroInferencia
from app.analysis import fonte
from app.analysis.servico import analisarProposicao
from app.analysis.processamento import PassagemDocumental, percorrerPassagens, processarFonte, agruparUnidades
from app.documents.estruturas import ErroDocumento, PaginaDocumento


def criarPagina(numero, texto):
    return PaginaDocumento(numero, texto, texto, [])


def simularIa():
    modelo = MagicMock()
    modelo.configuracao = {"LLAMA_MAX_TOKENS": 30}
    modelo.requisitar.return_value = {"default_generation_settings": {"n_ctx": 100}}
    modelo.contarTokensConversa.side_effect = lambda mensagens: len(mensagens[1]["content"].split())
    modelo.conversar.return_value = {"choices": [{"message": {"content": '{"pontos":[]}'}}], "usage": {}}
    return modelo


def paginasLongas():
    return [criarPagina(i, f"Art. {i} " + "exemplo " * 34) for i in range(1, 5)]


def testeDocumentoLongoEConsolidacao():
    resultado = {}
    processarFonte(simularIa(), paginasLongas(), "Peça", "dispositivos", resultado)
    assert resultado["partes_concluidas"] == 4
    assert resultado["explicacoes"][0]["paginas"] == [1, 2, 3, 4]
    assert sum(cliente["etapa"] == "consolidação" for cliente in resultado["geracoes"]) == 3


def testeArtigoEntrePaginas():
    partes = list(agruparUnidades([PassagemDocumental("norma", 1, "Art. 1 Regra"),
                        PassagemDocumental("norma", 2, "salvo exceção.\nArt. 2 Outra regra")]))
    assert len(partes) == 2
    assert partes[0][1] == {1,2} and "salvo exceção" in partes[0][0]


def testeSecoes():
    material = [criarPagina(1,"Art. 1 Teste\nJUSTIFICAÇÃO\nO autor cita terceiro.")]
    assert [p.secao for p in percorrerPassagens(material, "dispositivos")] == ["dispositivos", "justificação"]


@pytest.mark.parametrize("falharNaChamada", [1,5])
def testeFalhaDeGeracao(falharNaChamada):
    modelo = simularIa()
    modelo.conversar.side_effect = [modelo.conversar.return_value]*(falharNaChamada-1) + [ErroInferencia("interrompida")]
    resultado = {}
    processarFonte(modelo, paginasLongas(), "Peça", "dispositivos", resultado)
    assert resultado["situacao"] == "incompleta"
    assert resultado["partes_concluidas"] == falharNaChamada-1
    assert resultado["falha"] and not resultado["explicacoes"]


def testeCoberturaParcial(monkeypatch):
    monkeypatch.setattr("app.analysis.servico.selecionarFonte", lambda *a: (
        {}, {"identificacao":"peça"}, [criarPagina(1, "Texto"), PaginaDocumento(2, "", "", ["Página ilegível"])]))
    modelo = simularIa()
    modelo.__enter__.return_value = modelo
    monkeypatch.setattr("app.analysis.servico.ClienteIaLocal", lambda: modelo)
    resultado = analisarProposicao(1)
    assert resultado["cobertura_extracao"] == "parcial ou incerta"
    assert resultado["explicacoes"][0]["paginas"] == [1]
    assert "Página ilegível" in resultado["limitacoes"][0]


def simularCamara(monkeypatch, relacionadas):
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.obterProposicao.return_value = {"dados":{"id":1,"ementa":"Ementa simulada"}}
    cliente.obterRelacionadas.return_value = {"dados":relacionadas}
    cliente.obterTramitacoes.return_value = {"dados":[]}
    monkeypatch.setattr(fonte, "CamaraDeputados", lambda:cliente)
    monkeypatch.setattr(fonte, "urlsDosAvulsos", lambda id:[])


def testeSelecaoAmbigua(monkeypatch):
    simularCamara(monkeypatch, [{"id":2,"siglaTipo":"RDF"}])
    with pytest.raises(ErroDocumento, match="Escolha"):
        fonte.selecionarFonte(1)


def testeAusenciaDeTexto(monkeypatch):
    simularCamara(monkeypatch, [])
    _, documento, paginas = fonte.selecionarFonte(1)
    assert documento["identificacao"] == "ementa" and documento["limitacao"]
    assert paginas[0].texto == "Ementa simulada"


def testeAlternativaDisponivel(monkeypatch):
    simularCamara(monkeypatch, [])
    monkeypatch.setattr(fonte, "urlsDosAvulsos", lambda id:["https://www.camara.leg.br/"])
    with pytest.raises(ErroDocumento):
        fonte.selecionarFonte(1, "1")


def testePecaSemVinculo(monkeypatch):
    simularCamara(monkeypatch, [{"id": 2, "siglaTipo": "RDF"}])
    with pytest.raises(ErroDocumento, match="sem vínculo"):
        fonte.selecionarFonte(1, "3")


def testeSeparacaoDeVersoes(monkeypatch):
    paginas = [criarPagina(1, "RDF 1 POSSUI INTEIRO TEOR"), criarPagina(2, "EMS 2 POSSUI INTEIRO TEOR")]
    monkeypatch.setattr("app.analysis.servico.selecionarFonte", lambda *a: ({}, {}, paginas))
    with pytest.raises(ErroDocumento, match="peças distintas"):
        analisarProposicao(1)

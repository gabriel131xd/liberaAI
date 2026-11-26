"""Amostragem limitada e explícita da API oficial."""
from time import sleep

import pytest

from app.integrations.camara.cliente import CamaraDeputados, ErroHttpCamara


@pytest.mark.live
def testeAmostraReal():
    with CamaraDeputados(tempoLimite=30) as cliente:
        identificadores = set()
        for pagina in (1, 2):
            envelope = cliente.listarProposicoes(ano=2024, pagina=pagina, itens=5)
            proposicoes = envelope["dados"]
            print("Página", pagina, [proposicao["id"] for proposicao in proposicoes])
            assert len(proposicoes) == 5
            assert all(proposicao["ano"] == 2024 and proposicao["siglaTipo"] == "PL" for proposicao in proposicoes)
            identificadores.update(proposicao["id"] for proposicao in proposicoes)
            if pagina == 1:
                amostra = proposicoes[:3]
        assert len(identificadores) == 10
        for proposicao in amostra:
            identificador = proposicao["id"]
            detalhe = cliente.obterProposicao(identificador)["dados"]
            assert detalhe["id"] == identificador and detalhe["numero"] == proposicao["numero"]
            print("PL", detalhe["numero"], identificador, detalhe.get("urlInteiroTeor"))
            for obter in (cliente.obterAutores, cliente.obterTramitacoes, cliente.obterTemas):
                sleep(1)  # Espaça a amostragem real para respeitar a capacidade da fonte.
                registros = obter(identificador)["dados"]
                print(obter.__name__, len(registros))
                assert isinstance(registros, list)
        primeiro = amostra[0]
        busca = cliente.listarProposicoes(numero=primeiro["numero"], ano=2024, itens=5)
        assert primeiro["id"] in [proposicao["id"] for proposicao in busca["dados"]]
        with pytest.raises(ErroHttpCamara) as erro:
            cliente.obterProposicao(2147483647)
        print("ID inexistente", erro.value.codigoHttp)
        assert erro.value.codigoHttp == 404

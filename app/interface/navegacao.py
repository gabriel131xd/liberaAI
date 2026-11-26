"""Listas em páginas pequenas com botões nativos do Gradio."""

from html import escape
from urllib.parse import urlsplit

import gradio as gr

from app.integrations.camara.cliente import ErroCamara

from .legislativo import deputados, identificacao, listarAno, pesquisar, temProxima

DEPUTADOS_POR_PAGINA = 10
LIMITE_BUSCA_DIRETA = 15


class ListaPaginada:
    """Mantém a página e as referências de clique na sessão do navegador."""

    def __init__(self, nome, quantidade, paginar=True, miniatura=False):
        self.nome = nome
        self.estado = gr.State({"pagina": 1, "itens": [], "proxima": False})
        self.cartoes = []
        self.paginar = paginar
        self.mensagem = gr.Markdown()
        for _ in range(quantidade):
            with gr.Group(visible=False) as grupo:
                if miniatura:
                    with gr.Row():
                        descricao = gr.HTML(scale=0, min_width=56, container=False)
                        botao = gr.Button()
                else:
                    botao = gr.Button()
                    descricao = gr.HTML()
            self.cartoes.append((grupo, botao, descricao))
        with gr.Row(visible=paginar):
            self.anterior = gr.Button("Anterior", interactive=False)
            self.proxima = gr.Button("Próxima", interactive=False)
        self.saidas = [
            self.estado, self.mensagem, self.anterior, self.proxima,
            *(componente for cartao in self.cartoes for componente in cartao),
        ]

    def exibir(self, itens, pagina=1, proxima=False, mensagem="", filtros=None):
        estado = {"pagina": pagina, "itens": itens, "proxima": proxima, "filtros": filtros}
        atualizacoes = [estado, mensagem, gr.update(interactive=pagina > 1), gr.update(interactive=proxima)]
        for indice in range(len(self.cartoes)):
            item = itens[indice] if indice < len(itens) else None
            atualizacoes.extend((
                gr.update(visible=item is not None),
                gr.update(value=item["titulo"] if item else ""),
                gr.update(value=item["descricao"] if item else ""),
            ))
        return atualizacoes

    def vincularConsulta(self, gatilhos, consultar, filtros, fila, limpar=None, saidasExtras=()):
        def montarConsulta(deslocamento):
            def carregar(estado, *valores):
                pagina = estado["pagina"] if estado.get("filtros") == valores else 1
                if not deslocamento:
                    pagina = 1
                elif estado.get("filtros") == valores and (
                    deslocamento < 0 and pagina > 1 or deslocamento > 0 and estado["proxima"]
                ):
                    pagina += deslocamento

                # Oculta resultados antigos enquanto a Câmara atende a nova consulta.
                extras = list(limpar()) if limpar else []
                yield [*self.exibir([], mensagem="Consultando a Câmara…"), *extras]
                try:
                    itens, proxima, mensagem = consultar(*valores, pagina)
                except (ErroCamara, ValueError) as erro:
                    itens, proxima, mensagem = [], False, f"Falha na consulta. {erro}"
                yield [
                    *self.exibir(itens, pagina, proxima, mensagem, valores),
                    *(gr.skip() for _ in saidasExtras),
                ]
            return carregar

        entradas = [self.estado, *filtros]
        saidas = [*self.saidas, *saidasExtras]
        gr.on(gatilhos, montarConsulta(0), entradas, saidas, api_name=f"{self.nome}Consultar",
              trigger_mode="always_last", **fila)
        if self.paginar:
            for nome, botao, passo in (("Anterior", self.anterior, -1), ("Proxima", self.proxima, 1)):
                botao.click(montarConsulta(passo), entradas, saidas, api_name=f"{self.nome}{nome}", **fila)

    def vincularSelecao(self, selecionar, entradas, saidas, fila, rolar=False, preparar=None):
        def montarSelecao(indice):
            def abrirItem(estado, titulo, *valores):
                itens = estado["itens"]
                item = itens[indice] if indice < len(itens) else None
                # Uma ação enfileirada pode ter vindo de uma página que já mudou.
                if item and item["titulo"] == titulo:
                    if preparar:
                        yield preparar()
                    yield selecionar(item, *valores)
                else:
                    yield [gr.skip() for _ in saidas]
            return abrirItem

        for indice, (_, botao, _) in enumerate(self.cartoes):
            evento = botao.click(
                montarSelecao(indice), [self.estado, botao, *entradas], saidas,
                api_name=f"{self.nome}Selecionar{indice + 1}", **fila,
            )
            if rolar:
                evento.then(
                    None, js="() => document.getElementById('detalhe-proposicao')?.scrollIntoView()",
                )


def consultarDeputados(nome, ano, pagina):
    envelope = deputados(nome, ano, pagina, itens=DEPUTADOS_POR_PAGINA)
    itens = []
    for deputado in envelope["dados"]:
        nomeDeputado = deputado["nome"]
        partidoUf = " · ".join(dado for dado in (deputado.get("siglaPartido"), deputado.get("siglaUf")) if dado)
        foto = deputado.get("urlFoto") or ""
        endereco = urlsplit(foto)
        imagem = ""
        if endereco.scheme == "https" and endereco.hostname == "www.camara.leg.br":
            imagem = (
                f'<img src="{escape(foto, quote=True)}" alt="Fotografia de {escape(nomeDeputado, quote=True)}" '
                'width="48" height="64" loading="lazy" style="object-fit:cover;margin-right:.6rem">'
            )
        itens.append({
            "id": deputado["id"],
            "titulo": f"{nomeDeputado} · {partidoUf}" if partidoUf else nomeDeputado,
            "descricao": imagem,
        })
    periodo = str(int(ano)) if str(ano or "").strip() else "deputados em exercício"
    mensagem = f"Página {pagina} · {periodo} · {len(itens)} parlamentar(es)"
    return itens, temProxima(envelope), mensagem


def itemProposicao(dado, data=None, autores=None, situacao=None):
    detalhes = " · ".join(
        escape(f"{rotulo}: {valor}") for rotulo, valor in (
            ("Apresentação", data), ("Autoria", autores), ("Situação", situacao),
        ) if valor
    )
    return {
        "id": dado["id"], "titulo": f"Ver detalhes de {identificacao(dado)}",
        "descricao": f"<p>{escape(dado.get('ementa') or 'Ementa indisponível.')}</p><p>{detalhes}</p>",
    }


def consultarProposicoes(ano, tipo, deputado, situacao, pagina):
    envelope, linhas, falhas = listarAno(ano, tipo or "", deputado, situacao, pagina)
    itens = [itemProposicao(dado, *linha[1:4]) for dado, linha in zip(envelope["dados"], linhas)]
    mensagem = f"Página {pagina} · {len(itens)} proposição(ões)"
    if not itens:
        mensagem += " · Nenhuma proposição encontrada nesta página com os filtros atuais."
    if falhas:
        mensagem += f" · Autoria ou detalhe indisponível em {falhas} item(ns)."
    return itens, temProxima(envelope), mensagem


def consultarProposicoesDeputado(ano, tipo, deputado, pagina):
    if not deputado:
        return [], False, "Selecione um deputado para ver suas proposições."
    return consultarProposicoes(ano, tipo, deputado, None, pagina)


def consultarBuscaDireta(tipo, numero, ano, pagina):
    dados = pesquisar(tipo, numero, ano)
    itens = [itemProposicao(dado, dado.get("dataApresentacao")) for dado in dados]
    mensagem = f"{len(itens)} resultado(s)." if itens else "Nenhuma proposição encontrada."
    return itens, False, mensagem

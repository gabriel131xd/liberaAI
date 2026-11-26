"""Apresentação compartilhada da proposta e seus dados públicos."""

from html import escape
from urllib.parse import urlsplit

import gradio as gr

from .cidadao import (
    FALHAS, SEM_INFORMACAO, ExplicacoesTemporarias, dataBrasileira, responderCidadao, respostaVigencia,
)
from .legislativo import AUSENTE, carregarOficial, formatarAutores, identificacao

PERGUNTAS = (
    "O que essa proposta muda na prática?",
    "Quem pode ser afetado?",
    "Essa proposta já foi aprovada?",
    "Pode explicar de uma maneira mais simples?",
)
ESTILO_CARTAO = """
article { padding: .3rem .2rem; }
h2 { font-size: clamp(1.35rem, 3vw, 2rem); font-weight: 650; margin: .3rem 0 1rem; }
p { line-height: 1.55; margin-bottom: .45rem; }
a { text-decoration: underline; text-underline-offset: .18em; }
"""
ESTILO_EXPLICACAO = """
.perguntas { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr)); gap: .75rem; }
section { border: 1px solid var(--border-color-primary); border-radius: .65rem; padding: .8rem 1rem; }
h3 { font-weight: 650; margin-bottom: .35rem; }
p { line-height: 1.55; margin-bottom: .4rem; }
.nota { margin-top: .75rem; }
"""


def linkOficial(url, rotulo):
    if url:
        endereco = urlsplit(url)
        if endereco.scheme == "https" and endereco.hostname in {"www.camara.leg.br", "dadosabertos.camara.leg.br"}:
            return f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(rotulo)}</a>'
    return ""


def historicoOficial(oficial):
    blocos = []
    for chave, titulo, descricao, campoData in (
        ("tramitações", "Tramitações", "despacho", "dataHora"),
        ("votações", "Votações", "descricao", "data"),
    ):
        registros = oficial[chave]
        blocos.append(f"<h3>{titulo}</h3>")
        if registros is None:
            blocos.append("<p>Esta consulta está indisponível no momento. Consulte a ficha oficial.</p>")
            continue
        if not registros:
            blocos.append("<p>A Câmara não retornou registros nesta consulta.</p>")
            continue
        if len(registros) > 15 or any(aviso.startswith(f"Cobertura parcial em {chave}") for aviso in oficial["avisos"]):
            blocos.append("<p>Veja abaixo até 15 registros recentes. Consulte a ficha oficial para o histórico.</p>")
        blocos.append("<ul>")
        for item in sorted(registros, key=lambda item: item.get(campoData) or "", reverse=True)[:15]:
            data = dataBrasileira(item.get(campoData))
            orgao = item.get("siglaOrgao")
            texto = item.get(descricao) or item.get("descricaoTramitacao") or AUSENTE
            link = linkOficial(item.get("url"), "Ver documento") or linkOficial(item.get("uri"), "Ver registro oficial")
            cabecalho = " · ".join(valor for valor in (data, orgao) if valor)
            blocos.append(f"<li><strong>{escape(cabecalho)}</strong> — {escape(texto)} {link}</li>")
        blocos.append("</ul>")
    ficha = linkOficial(oficial["ficha"], "Consultar histórico na ficha oficial")
    blocos.append(f"<p>{ficha}</p>")
    return "".join(blocos)


def cartaoOficial(oficial, resultado=None):
    dados = oficial["dados"]
    situacao = (dados.get("statusProposicao") or {}).get("descricaoSituacao") or AUSENTE
    titulo = ((resultado or {}).get("campos") or {}).get("titulo")
    urlPrincipal = dados.get("urlInteiroTeor")
    documento = linkOficial(urlPrincipal, "Abrir documento indicado pela Câmara")
    ficha = linkOficial(oficial["ficha"], "Abrir ficha oficial na Câmara")
    links = " · ".join(link for link in (documento, ficha) if link)
    tituloHtml = f"<h2>{escape(titulo)}</h2>" if titulo else ""
    autores = formatarAutores(oficial["autores"] or []) or AUSENTE
    data = dataBrasileira(dados.get("dataApresentacao"))
    return (
        f"<article><p><strong>{escape(identificacao(dados))}</strong></p>{tituloHtml}"
        f"<p><strong>Situação oficial</strong> · {escape(situacao)}</p>"
        f"<p><strong>Autores</strong> · {escape(autores)}<br><strong>Apresentação</strong> · {data}</p>"
        f"<p>{links}</p></article>"
    )


def cartaoExplicacao(oficial, resultado):
    campos = resultado.get("campos", {})
    vigencia = respostaVigencia(oficial)
    if campos.get("vigencia"):
        vigencia = f"{vigencia} {campos['vigencia']}"
    aviso = resultado.get("aviso")
    perguntas = (
        ("O que ela propõe?", campos.get("proposta", SEM_INFORMACAO)),
        ("O que pretende mudar?", campos.get("mudanca", SEM_INFORMACAO)),
        ("Quem pode ser afetado?", campos.get("afetados", SEM_INFORMACAO)),
        ("Isso já está valendo?", vigencia),
    )
    blocos = [f"<p role=\"status\"><strong>{escape(aviso)}</strong></p>"] if aviso else []
    blocos.append('<div class="perguntas">')
    blocos.extend(f"<section><h3>{pergunta}</h3><p>{escape(resposta)}</p></section>" for pergunta, resposta in perguntas)
    blocos.append("</div>")
    if campos:
        blocos.append('<p class="nota">Explicação da IA local baseada no texto oficial disponível. Consulte a fonte para conferir os detalhes.</p>')
    return "".join(blocos)


class DetalheCidadao:
    """Atualiza a tela com o trabalho associado à seleção atual da sessão."""

    def __init__(self):
        self.cache = ExplicacoesTemporarias()
        self.oficial = gr.State({})
        self.trabalho = gr.State(None)
        self.resultado = gr.State({})
        with gr.Group(visible=False) as self.grupo:
            gr.Markdown("## Detalhes da proposição", elem_id="detalhe-proposicao")
            self.cartao = gr.HTML(css_template=ESTILO_CARTAO)
            gr.Markdown("## Entenda esta proposta")
            self.explicacao = gr.HTML(css_template=ESTILO_EXPLICACAO)
            with gr.Accordion("Histórico de tramitações e votações", open=False) as self.acordeao:
                self.historico = gr.HTML()
            with gr.Group() as self.grupoConversa:
                gr.Markdown("## Pergunte sobre esta proposta")
                with gr.Row():
                    sugestoes = [gr.Button(texto, size="sm") for texto in PERGUNTAS]
                self.conversa = gr.Chatbot(label="Conversa", render_markdown=False, height=300)
                with gr.Row():
                    self.pergunta = gr.Textbox(label="O que você quer saber?", max_length=500, scale=5)
                    self.enviar = gr.Button("Enviar", variant="primary", scale=1)
        self.relogio = gr.Timer(2, active=False)
        self.saidas = [
            self.oficial, self.trabalho, self.resultado, self.grupo, self.cartao, self.explicacao,
            self.historico, self.acordeao, self.grupoConversa, self.conversa, self.pergunta, self.relogio,
        ]
        self.sugestoes = sugestoes

    def limpar(self, mensagem=""):
        aviso = f'<p role="status">{escape(mensagem)}</p>' if mensagem else ""
        return ({}, None, {}, gr.update(visible=bool(mensagem)), "", aviso, "", gr.update(visible=False, open=False),
                gr.update(visible=False), [], "", gr.update(active=False))

    def abrir(self, item):
        try:
            oficial = carregarOficial(item["id"])
        except FALHAS:
            return self.limpar("Não consegui consultar a Câmara. Tente abrir a proposta novamente.")
        chave = self.cache.iniciar(oficial)
        resultado = self.cache.consultar(chave) if chave else {
            "aviso": "A inteligência artificial está ocupada. Abra a proposta novamente em instantes.",
        }
        pendente = resultado is None
        texto = ('<p role="status" aria-live="polite">Preparando a explicação com o texto oficial…</p>'
                 if pendente else cartaoExplicacao(oficial, resultado))
        return (
            oficial, chave if pendente else None, resultado or {}, gr.update(visible=True),
            cartaoOficial(oficial, resultado), texto, historicoOficial(oficial), gr.update(visible=True, open=False),
            gr.update(visible=True), [], "", gr.update(active=pendente),
        )

    def consultar(self, oficial, chave):
        if not oficial or not chave:
            return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.update(active=False)
        resultado = self.cache.consultar(chave)
        if resultado is None:
            return tuple(gr.skip() for _ in range(5))
        return None, resultado, cartaoOficial(oficial, resultado), cartaoExplicacao(oficial, resultado), gr.update(active=False)

    def vincular(self, fila):
        filaPublica = {**fila, "show_progress": "hidden"}
        self.relogio.tick(
            self.consultar, [self.oficial, self.trabalho],
            [self.trabalho, self.resultado, self.cartao, self.explicacao, self.relogio],
            api_visibility="private", **filaPublica,
        )
        for evento in (self.enviar.click, self.pergunta.submit):
            evento(responderCidadao, [self.pergunta, self.oficial, self.resultado, self.trabalho, self.conversa],
                   [self.conversa, self.pergunta], api_visibility="private", **{**fila, "show_progress": "minimal"})
        for botao in self.sugestoes:
            botao.click(responderCidadao, [botao, self.oficial, self.resultado, self.trabalho, self.conversa],
                        [self.conversa, self.pergunta], api_visibility="private", **{**fila, "show_progress": "minimal"})

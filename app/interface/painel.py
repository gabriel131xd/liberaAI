from datetime import date
from os import getenv

import gradio as gr
import httpx

from app.ai.cliente import ErroInferencia
from app.ai.instrucoes import VERSAO_ANTERIOR, VERSAO_ATUAL
from app.analysis.servico import analisarFonte
from app.analysis.fonte import selecionarFonte
from app.documents.estruturas import ErroDocumento
from app.integrations.camara.cliente import CamaraDeputados, ErroCamara

from .conversa import responder
from .detalhe import DetalheCidadao
from .legislativo import (
    AUSENTE, ITENS, carregarOficial, contarAutor, formatarAutores, identificacao, lerInteiroPositivo, opcoesPecas,
)

from .navegacao import (
    DEPUTADOS_POR_PAGINA, LIMITE_BUSCA_DIRETA, ListaPaginada, consultarBuscaDireta,
    consultarDeputados, consultarProposicoes, consultarProposicoesDeputado,
)

FALHAS = (ErroInferencia, ErroCamara, ErroDocumento, httpx.HTTPError, ValueError)
ANO = date.today().year


def contar(ano, deputado):
    try:
        return contarAutor(ano, deputado)
    except FALHAS as erro:
        return f"Consulta sem total confirmado. {erro}"


def carregarFiltros(carregados):
    tipos, situacoes = carregados
    with CamaraDeputados() as cliente:
        if not tipos:
            try:
                dados = cliente.listarTiposProposicao()["dados"]
                nomesPorSigla = {}
                for item in dados:
                    if item.get("sigla") and item.get("nome"):
                        nomesPorSigla.setdefault(item["sigla"], item["nome"].strip())
                tipos = sorted((f"{nome} ({sigla})", sigla) for sigla, nome in nomesPorSigla.items())
            except ErroCamara as erro:
                gr.Warning(f"Tipos de proposição indisponíveis. {erro}")
        if not situacoes:
            try:
                dados = cliente.listarSituacoes()["dados"]
                situacoes = sorted((item["nome"].strip(), item["cod"]) for item in dados)
            except ErroCamara as erro:
                gr.Warning(f"Situações legislativas indisponíveis. {erro}")
    atualizacaoTipos = gr.update(choices=[("Todos os tipos", ""), *tipos]) if tipos else gr.skip()
    atualizacaoSituacoes = gr.update(choices=[("Todas as situações", ""), *situacoes]) if situacoes else gr.skip()
    return (tipos, situacoes), atualizacaoTipos, atualizacaoTipos, atualizacaoSituacoes


def abrir(identificador):
    """Troca a proposição e devolve um estado documental vazio para a sessão."""
    if not identificador:
        return {}, {}, "", "", [], [], gr.update(choices=[], value=None), "Selecione uma proposição."
    try:
        oficial = carregarOficial(identificador)
        dados = oficial["dados"]
        estado = dados.get("statusProposicao") or {}
        autoria = oficial["autores"]
        ficha = "\n".join([
            f"{identificacao(dados)} · ID {identificador}",
            f"Apresentação original: {dados.get('dataApresentacao') or AUSENTE}",
            f"Situação oficial: {estado.get('descricaoSituacao') or AUSENTE}",
            f"Autoria: {formatarAutores(autoria or []) or AUSENTE}",
            f"Ficha: {oficial['ficha']}", f"API: {dados.get('uri') or AUSENTE}",
        ])
        movimentos = [[item.get("dataHora"), item.get("siglaOrgao"), item.get("despacho"), item.get("url")]
                      for item in oficial["tramitações"] or []]
        votacoes = [[item.get("data"), item.get("siglaOrgao"), item.get("descricao"), item.get("uri")]
                    for item in oficial["votações"] or []]
        try:
            opcoes = opcoesPecas(oficial)
        except httpx.HTTPError:
            oficial["avisos"].append("Avulsos indisponíveis. Consulte a ficha após atualizar.")
            opcoes = opcoesPecas(oficial, incluirAvulsos=False)
        return oficial, {}, ficha, dados.get("ementa") or AUSENTE, movimentos, votacoes, (
            gr.update(choices=opcoes, value=None)), "\n".join(oficial["avisos"]) or "Dados oficiais carregados."
    except FALHAS as erro:
        return {}, {}, "", "", [], [], gr.update(choices=[], value=None), f"Falha ao abrir a proposição. {erro}"


def atualizar(oficial):
    return abrir(oficial.get("id"))


def limparCampos():
    return "", "", "", "", [], "", "", "", "", "", "", "", None


def abrirTela(identificador):
    return (*abrir(identificador), *limparCampos())


def atualizarTela(oficial):
    return (*atualizar(oficial), *limparCampos())


def carregarPeca(oficial, peca, motivoEmenta=None):
    if not oficial or not peca:
        return {}, "", "Selecione uma peça."
    try:
        fonte = selecionarFonte(oficial["id"], peca, motivoEmenta)
        metadadosPeca = fonte[1]
        texto = "\n\n".join(f"Página {pagina.numero}\n{pagina.texto}" for pagina in fonte[2])
        avisos = metadadosPeca.get("avisos", []) + [f"Página {pagina.numero}: {aviso}" for pagina in fonte[2] for aviso in pagina.avisos]
        mensagem = f"{metadadosPeca['identificacao']} · {metadadosPeca.get('url')}\n{metadadosPeca.get('situacao') or metadadosPeca.get('limitacao', '')}"
        if metadadosPeca.get("exige_recorte"):
            mensagem += "\nPeça composta ou anexo. Confirme início, fim e seção de uma só versão."
        return {"fonte": fonte, "selecao": peca}, texto, "\n".join([mensagem, *avisos])
    except FALHAS as erro:
        return {}, "", f"Falha ao carregar a peça. {erro}"


def carregarTela(oficial, peca, motivoEmenta):
    return (*carregarPeca(oficial, peca, motivoEmenta), "", "", [], "")


def recorteDaInterface(inicio, fim, secao):
    return (
        lerInteiroPositivo(inicio, "a primeira página", opcional=True),
        lerInteiroPositivo(fim, "a última página", opcional=True),
        (secao or "").strip() or None,
    )


def avisosDaConferencia(dados):
    return list(dict.fromkeys(
        aviso for geracao in dados["geracoes"] for aviso in geracao.get("conferencia", {}).get("avisos", [])
    ))


def compararPrompts(documento, inicio, fim, secao):
    """Executa as duas versões só quando o avaliador solicita a comparação."""
    if not documento.get("fonte"):
        return "", "", {"aviso": "Carregue uma peça antes de comparar."}
    try:
        chave = recorteDaInterface(inicio, fim, secao)
        fonte = documento["fonte"]
        respostas = []
        metricas = {"peca": fonte[1]["identificacao"], "fonte": fonte[1].get("url"),
                    "sha256": fonte[1].get("sha256"), "versoes": {}}
        for versao in (VERSAO_ANTERIOR, VERSAO_ATUAL):
            dados = analisarFonte(fonte, *chave, versao=versao)
            metricas["paginas"] = dados["recorte"]
            metricas["versoes"][versao] = {
                "situacao": dados["situacao"], "segundos": dados["segundos"],
                "inferencias": len(dados["geracoes"]), "modelo": dados.get("modelo"),
                "contexto": dados.get("contexto"), "falha": dados.get("falha"),
                "avisos": dados["limitacoes"] + avisosDaConferencia(dados),
                "uso_por_chamada": [item.get("uso") for item in dados["geracoes"]],
            }
            respostas.append("\n\n".join(
                f"{item['etapa']} · {item['secao']} · páginas {item['paginas']}\n"
                f"{item.get('resposta') or item.get('resposta_incompleta') or item.get('resposta_bruta') or 'Geração interrompida'}"
                for item in dados["geracoes"]
            ))
        return *respostas, metricas
    except FALHAS as erro:
        return "", "", {"aviso": f"Comparação indisponível. {erro}"}


def explicar(documento, inicio, fim, secao):
    if not documento.get("fonte"):
        return documento, "", "", "Carregue uma peça antes de gerar a explicação."
    try:
        chave = recorteDaInterface(inicio, fim, secao)
        # A análise cacheada só vale para o recorte e a peça da sessão.
        dados = documento.get("analise") if documento.get("recorte") == chave else None
        if dados is None:
            dados = analisarFonte(documento["fonte"], *chave)
        fonte = dados["documento"]
        metadados = (f"{fonte['identificacao']} · {fonte.get('versao') or 'Ementa'}\n"
                     f"Fonte: {fonte.get('url')}\n"
                     f"Versão das instruções: {dados['versao_prompt']}\n"
                     f"Situação da geração: {dados['situacao']} · {dados['segundos']} s\n"
                     f"Páginas com alguma geração concluída: {dados['paginas_com_geracao_concluida']}\n"
                     f"Cobertura: {dados['cobertura_extracao']}")
        avisos = list(dados["limitacoes"])
        conferencia = avisosDaConferencia(dados)
        if conferencia:
            avisos.extend(["A conferência textual sinalizou pontos para revisão humana.", *conferencia])
        if dados.get("falha"):
            avisos.append(dados["falha"])
        secoes = dados["explicacoes"]
        if dados.get("falha"):
            secoes = [*secoes, *({"secao": f"Parte disponível de {geracao['secao']}", "paginas": geracao["paginas"],
                                 "texto": geracao["resposta"]}
                                for geracao in dados["geracoes"] if geracao["etapa"] == "parte" and geracao.get("resposta"))]
        resumo = "\n\n".join(f"{secao['secao']} · páginas {secao['paginas']}\n{secao['texto']}" for secao in secoes)
        if conferencia:
            resumo = ("A conferência encontrou pontos que exigem revisão. Consulte as respostas por parte "
                      "e compare os avisos com o texto original.")
        detalhes = "\n\n".join(f"{geracao['etapa']} · {geracao['secao']} · páginas {geracao['paginas']}\n"
                               f"{geracao.get('resposta') or geracao.get('resposta_incompleta') or geracao.get('resposta_bruta') or 'Geração interrompida'}"
                               for geracao in dados["geracoes"])
        if not dados.get("falha"):
            documento = {**documento, "analise": dados, "recorte": chave}
        return documento, resumo, detalhes, "\n".join([metadados, *avisos])
    except FALHAS as erro:
        return documento, "", "", f"Análise indisponível. {erro}"


def conversar(pergunta, oficial, documento, inicio, fim, secao, historico):
    if not pergunta.strip() or not oficial:
        return historico, pergunta
    try:
        chave = recorteDaInterface(inicio, fim, secao)
        resposta = responder(pergunta.strip(), oficial, documento.get("fonte"), chave,
                             documento.get("analise") if documento.get("recorte") == chave else None, historico)
    except FALHAS as erro:
        resposta = f"Resposta indisponível. {erro}"
    return [*historico[-18:], {"role": "user", "content": pergunta}, {"role": "assistant", "content": resposta}], ""


def controlesDeputado(nomeLista, rotulo):
    with gr.Row():
        nome = gr.Textbox(label=rotulo, placeholder="Nome parlamentar")
        # Number vazio aparece como zero no navegador do Gradio 6.32.
        mandato = gr.Textbox(label="Ano de exercício (opcional)", value="",
                             placeholder="Deputados em exercício")
        botao = gr.Button("🔍 Buscar deputados")
    lista = ListaPaginada(nomeLista, DEPUTADOS_POR_PAGINA, miniatura=True)
    return nome, mandato, botao, lista


def limparDetalhe():
    return (*abrir(None)[:-1], "", *limparCampos())


def selecionarParlamentar(item):
    return item["id"], item["titulo"]


def abrirNoLaboratorio(oficial):
    return abrirTela(oficial.get("id")) if oficial else limparDetalhe()


def criarInterface():
    # As ações de detalhe usam a mesma fila para aplicar as mudanças de estado em sequência.
    fila = {"concurrency_id": "detalhe", "concurrency_limit": 1, "show_progress": "full"}
    with gr.Blocks(title="LiberaAI", analytics_enabled=False) as interface:
        oficial = gr.State({})
        documento = gr.State({}, time_to_live=900)
        gr.Markdown("# LiberaAI\nConsulte propostas e documentos oficiais da Câmara dos Deputados.")
        catalogos = gr.State(([], []))
        deputado = gr.State(None)
        autor = gr.State(None)
        tiposIniciais = [("Todos os tipos", ""), ("Projeto de Lei (PL)", "PL")]
        with gr.Tabs():
            with gr.Tab("Início") as abaInicio:
                with gr.Row():
                    tipoDireto = gr.Textbox(label="Tipo", value="PL")
                    numero = gr.Textbox(label="Número", value="")
                    anoDireto = gr.Textbox(label="Ano da numeração", value="")
                busca = gr.Button("Buscar proposição", variant="primary")
                listaDireta = ListaPaginada("buscaDireta", LIMITE_BUSCA_DIRETA, paginar=False)
            with gr.Tab("Deputados") as abaDeputados:
                with gr.Row():
                    with gr.Column():
                        nomeDeputado, mandatoDeputado, buscarDeputado, listaDeputados = controlesDeputado(
                            "deputados", "Nome do deputado",
                        )
                    with gr.Column():
                        perfil = gr.Textbox(label="Parlamentar selecionado", interactive=False)
                        with gr.Row():
                            anoDeputado = gr.Number(label="Ano da numeração", value=ANO, precision=0)
                            tipoDeputado = gr.Dropdown(label="Tipo de proposição", choices=tiposIniciais, value="PL")
                        listaDoDeputado = ListaPaginada("proposicoesDeputado", ITENS)
            with gr.Tab("Por ano") as abaAno:
                with gr.Row():
                    ano = gr.Number(label="Ano da numeração", value=ANO, precision=0)
                    tipo = gr.Dropdown(label="Tipo de proposição", choices=tiposIniciais, value="PL")
                    situacao = gr.Dropdown(label="Situação oficial", choices=[("Todas as situações", "")], value="")
                with gr.Accordion("Filtrar e contar por autor", open=False):
                    nomeAutor, mandatoAutor, buscarAutor, listaAutores = controlesDeputado("autores", "Nome do deputado")
                    with gr.Row():
                        autorSelecionado = gr.Textbox(label="Autor selecionado", interactive=False)
                        limparAutor = gr.Button("Remover filtro de autor")
                    contarBotao = gr.Button("Contar proposições do autor no ano")
                    total = gr.Textbox(label="Total oficial consultado", interactive=False)
                listaAno = ListaPaginada("proposicoesAno", ITENS)
            with gr.Tab("Laboratório de IA") as abaLaboratorio:
                gr.Markdown("## Laboratório de IA\nAbra uma proposição em uma aba de consulta e volte aqui para avaliá-la.")
                atualizarBotao = gr.Button("Atualizar dados oficiais")
                ficha = gr.Textbox(label="Identificação e situação oficial", lines=6, interactive=False)
                ementa = gr.Textbox(label="Ementa oficial", lines=4, interactive=False)
                aviso = gr.Textbox(label="Disponibilidade dos dados", interactive=False)
                with gr.Accordion("Histórico de tramitações e votações", open=False):
                    movimentos = gr.Dataframe(headers=["Data", "Órgão", "Movimentação", "Documento"],
                                              label="Tramitações oficiais", interactive=False, wrap=True)
                    votos = gr.Dataframe(headers=["Data", "Órgão", "Descrição da deliberação", "Referência API"],
                                         label="Votações oficiais", interactive=False, wrap=True)
                peca = gr.Dropdown(label="Peça legislativa", filterable=True)
                with gr.Accordion("Alternativa quando não houver peça textual utilizável", open=False):
                    motivoEmenta = gr.Textbox(label="Motivo para usar somente a ementa",
                                             placeholder="Preencha após verificar as referências alternativas")
                carregar = gr.Button("Carregar texto da peça")
                with gr.Accordion("Texto original extraído", open=False):
                    original = gr.Textbox(label="Páginas do documento", lines=12, interactive=False)
                with gr.Row():
                    inicio = gr.Textbox(label="Primeira página do recorte (opcional)", value="")
                    fim = gr.Textbox(label="Última página do recorte (opcional)", value="")
                    secao = gr.Textbox(label="Versão ou seção conferida no original")
                analisar = gr.Button("Gerar explicação local", variant="primary")
                metadados = gr.Textbox(label="Fonte, cobertura, processamento e limitações", lines=4, interactive=False)
                resumo = gr.Textbox(label="Resumo simplificado", lines=5, interactive=False)
                with gr.Accordion("Explicações detalhadas por parte", open=False):
                    detalhes = gr.Textbox(label="Respostas locais por seção e página", lines=12, interactive=False)
                with gr.Accordion("Comparação experimental de instruções", open=False):
                    comparar = gr.Button("Comparar versões na peça e no recorte atuais")
                    with gr.Row():
                        respostaAnterior = gr.Textbox(label="Resposta anterior · v1", lines=9, interactive=False)
                        respostaAtual = gr.Textbox(label="Resposta atualizada · v2", lines=9, interactive=False)
                    metricasComparacao = gr.JSON(label="Fonte, versões e métricas")
                areaConversa = gr.Chatbot(label="Conversa sobre a proposição", render_markdown=False)
                with gr.Row():
                    pergunta = gr.Textbox(label="O que você quer saber?")
                    enviar = gr.Button("Enviar")
        publico = DetalheCidadao()
        publico.vincular(fila)

        saidas = [oficial, documento, ficha, ementa, movimentos, votos, peca, aviso]
        saidasComparacao = [respostaAnterior, respostaAtual, metricasComparacao]
        campos = [original, metadados, resumo, detalhes, areaConversa, pergunta, inicio, fim, secao, motivoEmenta,
                  *saidasComparacao]
        detalheCompleto = [*saidas, *campos]
        abaLaboratorio.select(abrirNoLaboratorio, publico.oficial, detalheCompleto, **fila)
        abaLaboratorio.select(lambda: gr.update(visible=False), outputs=publico.grupo, **fila)
        abaInicio.select(lambda oficial: gr.update(visible=bool(oficial)), publico.oficial, publico.grupo, **fila)
        gr.on([abaDeputados.select, abaAno.select], carregarFiltros, catalogos,
              [catalogos, tipoDeputado, tipo, situacao], **fila)
        listaDireta.vincularConsulta(
            [busca.click, numero.submit, anoDireto.submit],
            consultarBuscaDireta, [tipoDireto, numero, anoDireto], fila, publico.limpar, publico.saidas,
        )
        listaDeputados.vincularConsulta(
            [abaDeputados.select, buscarDeputado.click, nomeDeputado.submit, mandatoDeputado.submit],
            consultarDeputados, [nomeDeputado, mandatoDeputado], fila,
            lambda: (None, "", *listaDoDeputado.exibir([], mensagem="Selecione um deputado."), *publico.limpar()),
            [deputado, perfil, *listaDoDeputado.saidas, *publico.saidas],
        )
        listaDeputados.vincularSelecao(selecionarParlamentar, [], [deputado, perfil], fila)
        listaDoDeputado.vincularConsulta(
            [deputado.change, anoDeputado.input, tipoDeputado.input],
            consultarProposicoesDeputado, [anoDeputado, tipoDeputado, deputado], fila,
            publico.limpar, publico.saidas,
        )
        listaAutores.vincularConsulta(
            [buscarAutor.click, nomeAutor.submit, mandatoAutor.submit],
            consultarDeputados, [nomeAutor, mandatoAutor], fila,
        )
        listaAutores.vincularSelecao(selecionarParlamentar, [], [autor, autorSelecionado], fila)
        limparAutor.click(lambda: (None, ""), outputs=[autor, autorSelecionado], **fila)
        contarBotao.click(contar, [ano, autor], total, **fila)
        listaAno.vincularConsulta(
            [abaAno.select, ano.input, tipo.input, situacao.input, autor.change],
            consultarProposicoes, [ano, tipo, autor, situacao], fila,
            lambda: ("", *publico.limpar()), [total, *publico.saidas],
        )
        for lista in (listaDireta, listaDoDeputado, listaAno):
            lista.vincularSelecao(
                publico.abrir, [], publico.saidas, {**fila, "show_progress": "minimal"}, rolar=True,
                preparar=lambda: publico.limpar("Consultando a Câmara…"),
            )
        atualizarBotao.click(atualizarTela, oficial, [*saidas, *campos], **fila)
        peca.input(lambda: ({}, *limparCampos()), outputs=[documento, *campos], **fila)
        carregar.click(carregarTela, [oficial, peca, motivoEmenta],
                       [documento, original, metadados, resumo, detalhes, areaConversa, pergunta], **fila).then(
                           lambda: ("", "", None), outputs=saidasComparacao, **fila)
        for campo in (inicio, fim, secao):
            campo.input(lambda: ("", "", [], "", "", "", None),
                        outputs=[resumo, detalhes, areaConversa, pergunta, *saidasComparacao], **fila)
        analisar.click(explicar, [documento, inicio, fim, secao], [documento, resumo, detalhes, metadados], **fila)
        comparar.click(compararPrompts, [documento, inicio, fim, secao], saidasComparacao, **fila)
        for evento in (enviar.click, pergunta.submit):
            evento(conversar, [pergunta, oficial, documento, inicio, fim, secao, areaConversa], [areaConversa, pergunta], **fila)
    return interface


if __name__ == "__main__":
    porta = int(getenv("LIBERAAI_GRADIO_PORT", "7860"))
    criarInterface().queue().launch(server_name="127.0.0.1", server_port=porta, share=False)

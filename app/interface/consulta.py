import gradio as gr

from app.integrations.camara.cliente import (
    CamaraDeputados,
    ErroCamara
)


# Consulta a proposição e recupera seus dados oficiais.
def buscarProjeto(numeroProjeto, anoProjeto):

    if not numeroProjeto or not anoProjeto:
        gr.Warning("Informe o número e o ano do projeto.")
        return "", "", ""

    if numeroProjeto <= 0 or anoProjeto <= 0:
        gr.Warning("Informe valores válidos.")
        return "", "", ""

    try:

        with CamaraDeputados() as cliente:

            resultado = cliente.listarProposicoes(
                siglaTipo="PL",
                numero=int(numeroProjeto),
                ano=int(anoProjeto)
            )

            projetos = resultado["dados"]

            if len(projetos) == 0:
                gr.Warning("Nenhum projeto encontrado.")
                return "", "", ""

            if len(projetos) > 1:
                gr.Warning("Mais de uma proposição encontrada.")
                return "", "", ""

            # Recupera os detalhes da proposição encontrada.
            identificador = projetos[0]["id"]

            resultadoDetalhado = cliente.obterProposicao(
                identificador
            )

            projeto = resultadoDetalhado["dados"]

            statusProjeto = projeto.get("statusProposicao") or {}

            situacao = statusProjeto.get(
                "descricaoSituacao"
            ) or "Situação não informada"

            ementa = projeto.get("ementa") or "Ementa indisponível"

            return str(identificador), situacao, ementa

    except ErroCamara as erro:

        gr.Warning(f"Falha na consulta: {erro}")

        return "", "", ""
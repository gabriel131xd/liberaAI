"""Respostas legislativas com precedência aos registros oficiais."""

import re
import unicodedata
from time import monotonic

from app.ai.cliente import MARGEM_CONTEXTO, ClienteIaLocal, ErroInferencia, GeracaoIncompleta
from app.ai.instrucoes import (
    CRITERIOS_FIDELIDADE, FORMATO_EVIDENCIA, INSTRUCOES_CONVERSA,
    INSTRUCOES_CONVERSA_ANTERIORES, VERSAO_ANTERIOR, VERSAO_ATUAL,
)
from app.analysis.conferencia import apresentarPontos, conferirResposta, formatoComEvidencias
from app.analysis.servico import selecionarRecorte

from .legislativo import AUSENTE, formatarAutores


def normalizar(texto):
    return "".join(caractere for caractere in unicodedata.normalize("NFD", texto.casefold())
                   if not unicodedata.combining(caractere))


def respostaOficial(pergunta, oficial):
    """Responde a perguntas de cadastro com os campos oficiais da Câmara."""
    texto = normalizar(pergunta)
    if re.search(r"\b(votacao|votacoes|votou|votaram|resultado da votacao|foi votad[oa]|"
                 r"foi aprovad[oa]|foi rejeitad[oa]|ja aprovaram|ja votaram)\b", texto):
        votacoes = oficial["votações"]
        if votacoes is None:
            return "Registros de votação indisponíveis. Consulte a ficha oficial após atualizar."
        estado = (oficial["dados"].get("statusProposicao") or {}).get("descricaoSituacao") or AUSENTE
        registros = "\n".join(f"{votacao.get('data') or AUSENTE} · {votacao.get('siglaOrgao') or AUSENTE} · "
                              f"{votacao.get('descricao') or AUSENTE}" for votacao in votacoes[:5])
        if registros:
            registros = f"{len(votacoes)} registros retornados. Até cinco exibidos abaixo.\n{registros}"
        else:
            registros = "A consulta não retornou votações."
        return f"Situação oficial: {estado}\n{registros}\nFicha: {oficial['ficha']}"
    if re.search(r"\b(quando (foi |se deu a )?apresentad[oa]|data (da|de) apresentacao|"
                 r"quando (foi )?protocolad[oa]|em que dia foi apresentad[oa])\b", texto):
        data = oficial["dados"].get("dataApresentacao") or AUSENTE
        return f"Apresentação original registrada pela Câmara: {data}\nFicha: {oficial['ficha']}"
    if re.search(r"\b(ultima (movimentacao|tramitacao|atualizacao)|quando (foi )?atualizad[oa])\b", texto):
        etapa = oficial["dados"].get("statusProposicao") or {}
        return (f"Data registrada na situação oficial: {etapa.get('dataHora') or AUSENTE}\n"
                f"Ficha: {oficial['ficha']}")
    if re.search(r"\b(autoria|autor|autora|autores|autoras|quem\s+(apresentou|assinou|propos|criou))\b", texto):
        autores = oficial["autores"]
        nomes = ("Consulta de autoria indisponível." if autores is None
                 else formatarAutores(autores) or "A consulta não retornou autores.")
        return f"Autoria oficial: {nomes}\nFicha: {oficial['ficha']}"
    perguntaSobreRegra = re.search(r"\b(quando (entra|entraria|passaria) em vigor|prazo de vigencia)\b", texto)
    if not perguntaSobreRegra and re.search(r"\b(situacao|status|tramit\w*|vigente|virou lei|em vigor|andamento)\b", texto):
        estado = (oficial["dados"].get("statusProposicao") or {}).get("descricaoSituacao") or AUSENTE
        return f"Situação registrada pela Câmara: {estado}\nFicha: {oficial['ficha']}"
    return None


def textoDaMensagem(mensagem):
    conteudo = mensagem["content"]
    if isinstance(conteudo, str):
        return conteudo
    return " ".join(parte["text"] for parte in conteudo if parte.get("type") == "text")


def responder(pergunta, oficial, fonte, recorte, analise, historico, *, versao=VERSAO_ATUAL, registro=None):
    direta = respostaOficial(pergunta, oficial)
    if direta is not None:
        return direta
    if fonte is None:
        return "Carregue uma peça oficial para perguntar sobre o conteúdo da proposta."
    paginas = selecionarRecorte(fonte, *recorte)
    fontes = {pagina.numero: pagina.texto for pagina in paginas if pagina.texto.strip()}
    if not fontes:
        return "O recorte não contém texto legível para responder."
    dados = oficial["dados"]
    documento = fonte[1]
    sistema = INSTRUCOES_CONVERSA_ANTERIORES
    if versao == VERSAO_ATUAL:
        sistema = f"{INSTRUCOES_CONVERSA}\n{CRITERIOS_FIDELIDADE}\n{FORMATO_EVIDENCIA}"
    contexto = (f"Peça: {documento['identificacao']} · {documento['url']}\n"
                f"Seção conferida: {recorte[2] or 'texto da peça'}\n"
                f"Identificação oficial da proposição: {dados.get('siglaTipo')} "
                f"{dados.get('numero')}/{dados.get('ano')}\n")
    texto = "\n".join(f"[Página {pagina.numero}]\n{pagina.texto}" for pagina in paginas)
    ultimas = "\n".join(f"{mensagem['role']}: {textoDaMensagem(mensagem)}" for mensagem in historico[-4:]
                        if versao == VERSAO_ANTERIOR or mensagem["role"] == "user")
    analise = analise or {}
    if versao == VERSAO_ATUAL and (
        analise.get("versao_prompt") != VERSAO_ATUAL
        or any(item.get("conferencia", {}).get("avisos") for item in analise.get("geracoes", []))
    ):
        analise = {}
    explicacoes = "\n".join(secao["texto"] for secao in analise.get("explicacoes", []))
    inicio = monotonic()
    with ClienteIaLocal() as modelo:
        limite = (
            modelo.requisitar("GET", "/props")["default_generation_settings"]["n_ctx"]
            - int(modelo.configuracao["LLAMA_MAX_TOKENS"])
            - MARGEM_CONTEXTO
        )
        mensagens = [{"role": "system", "content": sistema}, {"role": "user", "content": ""}]
        # O histórico é opcional. A fonte primária deve caber por inteiro.
        for complemento in (f"\nAnálise auxiliar: {explicacoes}\nHistórico: {ultimas}",
                            f"\nAnálise auxiliar: {explicacoes}", ""):
            mensagens[1]["content"] = f"{contexto}\nFonte primária:\n{texto}{complemento}\nPergunta: {pergunta}"
            tokens = modelo.contarTokensConversa(mensagens)
            if tokens > limite:
                continue
            formato = {"formato": formatoComEvidencias(3)} if versao == VERSAO_ATUAL else {}
            try:
                geracao = modelo.conversar(mensagens, **formato)
            except GeracaoIncompleta as erro:
                if registro is not None:
                    registro.update(versao_prompt=versao, falha=str(erro),
                                    resposta_bruta=erro.corpo["choices"][0]["message"].get("content"),
                                    segundos=round(monotonic() - inicio, 3), tokens_template=tokens,
                                    uso=erro.corpo.get("usage"), tempos=erro.corpo.get("timings"))
                raise
            respostaBruta = geracao["choices"][0]["message"]["content"]
            if registro is not None:
                registro.update(versao_prompt=versao, resposta_bruta=respostaBruta,
                                segundos=round(monotonic() - inicio, 3), tokens_template=tokens,
                                uso=geracao.get("usage"), tempos=geracao.get("timings"))
            resposta = apresentarPontos(respostaBruta) if versao == VERSAO_ATUAL else respostaBruta
            conferencia = conferirResposta(resposta, fontes) if versao == VERSAO_ATUAL else None
            if registro is not None:
                registro["conferencia"] = conferencia
            if conferencia and conferencia["avisos"]:
                return ("Não consegui confirmar a resposta com a evidência textual do recorte. "
                        f"Confira a peça em {documento['url']}.")
            return resposta
    raise ErroInferencia("O recorte excede o contexto do chat. Selecione menos páginas da mesma peça e tente novamente.")

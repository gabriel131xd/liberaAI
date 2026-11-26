from app.documents.referencias import urlsDosAvulsos, urlFicha
from app.integrations.camara.cliente import CamaraDeputados, ErroCamara

ITENS = 5
LIMITE_CONTAGEM = 20
AUSENTE = "Não informado pela Câmara"


def identificacao(dados):
    return f"{dados.get('siglaTipo')} {dados.get('numero')}/{dados.get('ano')}"


def temProxima(envelope):
    return any(link["rel"] == "next" for link in envelope["links"])


def lerInteiroPositivo(valor, rotulo, opcional=False):
    """Aceita campos vazios quando opcionais e valida antes da consulta."""
    if valor is None or isinstance(valor, str) and not valor.strip():
        if opcional:
            return None
    else:
        try:
            numero = int(valor)
            if numero > 0 and (isinstance(valor, str) or numero == valor):
                return numero
        except (ValueError, OverflowError):
            pass
    raise ValueError(f"Informe um valor inteiro positivo para {rotulo}.")


def pesquisar(tipo, numero, ano):
    if not tipo or not tipo.strip():
        raise ValueError("Informe o tipo da proposição.")
    numero = lerInteiroPositivo(numero, "o número da proposição")
    ano = lerInteiroPositivo(ano, "o ano da numeração")
    with CamaraDeputados() as cliente:
        return cliente.listarProposicoes(siglaTipo=tipo.strip().upper(), numero=numero, ano=ano)["dados"]


def deputados(nome, ano, pagina, itens=25):
    ano = lerInteiroPositivo(ano, "o ano de exercício", opcional=True)
    with CamaraDeputados() as cliente:
        return cliente.listarDeputados(nome or "", ano, int(pagina), itens=itens)


def listarAno(ano, tipo, deputado, situacao, pagina):
    if not ano or ano < 1:
        raise ValueError("Informe o ano da numeração.")
    with CamaraDeputados() as cliente:
        envelope = cliente.listarProposicoes(ano=int(ano), siglaTipo=tipo.strip().upper() or None,
                                             deputado=deputado, situacao=situacao, pagina=int(pagina),
                                             itens=ITENS)
        linhas = []
        visiveis = []
        avisos = 0
        for dado in envelope["dados"]:
            estado = dado.get("statusProposicao") or {}
            nomes = dado.get("autores")
            data = dado.get("dataApresentacao")
            try:
                detalhe = cliente.obterProposicao(dado["id"])["dados"]
                estado = detalhe.get("statusProposicao") or {}
                data = detalhe.get("dataApresentacao") or data
                if situacao and str(estado.get("codSituacao")) != str(situacao):
                    if estado.get("codSituacao") is None:
                        avisos += 1
                    continue
                nomes = formatarAutores(cliente.obterAutores(dado["id"])["dados"])
            except ErroCamara:
                avisos += 1
                nomes = None
                if situacao and str(estado.get("codSituacao")) != str(situacao):
                    continue
            visiveis.append(dado)
            linhas.append([identificacao(dado), data or AUSENTE, nomes or AUSENTE,
                           estado.get("descricaoSituacao") or AUSENTE, dado.get("ementa") or AUSENTE])
    return {**envelope, "dados": visiveis}, linhas, avisos


def contarAutor(ano, deputado):
    """Conta IDs distintos e informa se o limite ou uma falha interromper a consulta."""
    if not ano or ano < 1 or not deputado:
        raise ValueError("Informe o ano da numeração e selecione um deputado.")
    identificadores = set()
    with CamaraDeputados() as cliente:
        for pagina in range(1, LIMITE_CONTAGEM + 1):
            try:
                retorno = cliente.listarProposicoes(ano=int(ano), deputado=deputado,
                                                     siglaTipo=None, itens=100, pagina=pagina)
            except ErroCamara as erro:
                if not identificadores:
                    raise
                return f"Contagem incompleta por falha da API. {len(identificadores)} IDs distintos confirmados. {erro}"
            identificadores.update(item["id"] for item in retorno["dados"])
            if not temProxima(retorno):
                return f"{len(identificadores)} proposições distintas no ano de numeração {int(ano)} (todos os tipos e situações)."
    return f"Contagem incompleta após {LIMITE_CONTAGEM} páginas. {len(identificadores)} IDs distintos confirmados."


def formatarAutores(autores):
    return ", ".join(autor["nome"] for autor in autores if autor.get("nome"))


def carregarOficial(identificador):
    avisos = []
    with CamaraDeputados() as cliente:
        dados = cliente.obterProposicao(identificador)["dados"]
        colecoes = {}
        for nome, consultar in (("autores", cliente.obterAutores), ("tramitações", cliente.obterTramitacoes),
                                ("votações", cliente.listarVotacoes), ("relacionadas", cliente.obterRelacionadas)):
            try:
                envelope = consultar(identificador)
                colecoes[nome] = envelope["dados"]
                if temProxima(envelope):
                    avisos.append(f"Cobertura parcial em {nome}. Consulte a ficha oficial.")
            except ErroCamara as erro:
                colecoes[nome] = None
                avisos.append(f"{nome.capitalize()} indisponíveis. {erro}")
    return {"id": identificador, "dados": dados, "avisos": avisos, "ficha": urlFicha(identificador), **colecoes}


def opcoesPecas(oficial, incluirAvulsos=True):
    dados = oficial["dados"]
    opcoes = [(f"{identificacao(dados)} · documento principal", str(oficial["id"]))]
    opcoes.extend((f"{identificacao(item)} · ID {item['id']} · {(item.get('ementa') or '')[:110]}", str(item["id"]))
                  for item in oficial["relacionadas"] or [])
    opcoes.extend((f"Movimento {item['sequencia']} · {item.get('dataHora')} · "
                   f"{(item.get('despacho') or '')[:105]}", f"movimento:{item['sequencia']}")
                  for item in oficial["tramitações"] or [] if item.get("url") and item.get("sequencia"))
    opcoes.extend((f"Avulso {indice} · peça composta, selecione o recorte", f"avulso:{indice}")
                  for indice, _ in enumerate(urlsDosAvulsos(oficial["id"]) if incluirAvulsos else [], 1))
    return opcoes


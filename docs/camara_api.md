# Câmara dos Deputados · verificação de 24/11/2026

O cliente consulta uma página ou um recurso por chamada. A abordagem síncrona facilita inspeções sequenciais no Python e Jupyter. Use `with CamaraDeputados() as cliente` para compartilhar conexões e fechá-las ao sair. Em um futuro consumidor assíncrono, execute chamadas bloqueantes fora do loop de eventos. URL base e timeout (15 segundos por operação HTTP por padrão) são configuráveis.

## Contrato

Base oficial: `https://dadosabertos.camara.leg.br/api/v2/`. Todos os métodos usam GET e pedem JSON. O contrato foi conferido antes da implementação. [Swagger](https://dadosabertos.camara.leg.br/swagger/api.html) · [OpenAPI](https://dadosabertos.camara.leg.br/api/v2/api-docs) · [Paginação](https://dadosabertos.camara.leg.br/howtouse/2017-05-16-js-resultados-paginados.html)

| Caminho relativo | Conteúdo de `dados` |
|---|---|
| proposicoes | Lista de fichas resumidas. Filtros testados: siglaTipo (texto, padrão local PL), numero, ano, pagina e itens (inteiros). |
| proposicoes/{id} | Objeto com identificação, ementa, apresentação, status e referências oficiais. |
| proposicoes/{id}/autores | Lista de signatários com nome, tipo e ordem. |
| proposicoes/{id}/tramitacoes | Lista de movimentos com órgão, data, descrições e despacho. |
| proposicoes/{id}/temas | Lista de classificações oficiais. |

O envelope mantém `dados`, `links` e campos adicionais. Cada link tem `rel` e `href` textuais. A navegação depende da presença de relações como self, next, previous, first e last. O cliente recebe página a partir de 1, solicita 15 itens por padrão e aceita até 100 na listagem. O histórico individual pode ter mais de 100 registros numa resposta.

## Amostra real

A consulta de PLs com ano 2024 e cinco itens por página retornou os IDs abaixo. A segunda página trouxe cinco IDs distintos da primeira.

- Página 1: 253500, 380852, 510035, 582036, 1548579.
- Página 2: 2092056, 2416804, 2416826, 2416830, 2416861.

| Projeto e ficha | dataApresentacao | descricaoSituacao no detalhe | Autores / movimentos / temas | urlInteiroTeor |
|---|---|---|---|---|
| [PL 2597/2024 · 253500](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=253500) | 2004-05-13T14:41 | Transformado em Norma Jurídica | 1 / 325 / 2 | [PDF](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=1279376) |
| [PL 411/2024 · 380852](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=380852) | 2007-12-12T16:23 | Aguardando Apreciação pelo Senado Federal | 1 / 88 / 2 | [PDF](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=531477) |
| [PL 934/2024 · 510035](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=510035) | 2011-06-22T12:12 | Aguardando Designação de Relator(a) | 1 / 88 / 1 | [PDF](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=891953) |

A busca por PL, número 2597 e ano 2024 recuperou o ID 253500. A ficha pública confirmou número/ano, José Eduardo Cardozo, apresentação em 13/05/2004 e situação. O filtro ano seleciona o ano da identificação legislativa. A data de apresentação pode pertencer a outro ano. A situação reproduz o registro da Câmara no momento da consulta.

Nos três documentos, HEAD retornou HTTP 200 e Content-Type application/pdf. A disponibilidade foi verificada pelos cabeçalhos. O conteúdo dos PDFs ficou fora da inspeção.

## Campos e divergências

| Origem | Nomes e tipos observados em registros preenchidos |
|---|---|
| Identificação | id, numero, ano e codTipo são inteiros. uri, siglaTipo, descricaoTipo, ementa, keywords e urlInteiroTeor são strings. dataApresentacao é uma string de data e hora. |
| Detalhe | statusProposicao é objeto. texto, justificativa e urnFinal vieram nulos nos três detalhes. uriPropPosterior veio nulo nos dois primeiros. |
| Status e histórico | dataHora, siglaOrgao, uriOrgao, descricaoTramitacao, descricaoSituacao, despacho e codTipoTramitacao aparecem como strings quando preenchidos. sequencia e codSituacao são inteiros. url pode ser nula. |
| Autores | nome, uri e tipo são strings. codTipo, ordemAssinatura e proponente são inteiros nos registros examinados. |
| Temas | codTema e relevancia são inteiros. tema é string. Um item real do PL 934/2024 foi `{"codTema":56,"tema":"Saúde","relevancia":0}`. |

Comparando a maior dataHora observada com statusProposicao, as datas e sequências coincidiram nos três casos (397, 133 e 137, respectivamente). O maior horário também ocorreu ao final de cada lista consultada. A posição não é usada pelo cliente para deduzir situação ou reordenar registros. No PL 2597/2024 o campo url era nulo no status e preenchido no movimento de mesma sequência. O endereço do movimento é distinto do campo urlInteiroTeor do projeto.

Em duas verificações adicionais de autoria, o PL 1904/2024 teve 54 entradas. No PL 2630/2020 a API retornou nome “Senado Federal - Alessandro Vieira”, tipo “Órgão do Poder Legislativo” e URI de órgão. Resolver toda URI de autor como deputado perderia essa informação. [Autores do PL 1904/2024](https://dadosabertos.camara.leg.br/api/v2/proposicoes/2434493/autores) · [Autores do PL 2630/2020](https://dadosabertos.camara.leg.br/api/v2/proposicoes/2256735/autores)

## Falhas e reprodução

Uma lista vazia com envelope válido é um resultado normal. `ErroHttpCamara` expõe o código HTTP e diferencia consulta inválida (400), ausência (404), limite (429) e falha de servidor (5xx). `ErroCamara` identifica timeout, falha de transporte, JSON ilegível ou estrutura incompatível. O cliente não repete chamadas automaticamente. O ID 2147483647 retornou 404 no teste real.

O comando padrão testa respostas simuladas e o backend local. O marcador live executa 16 GETs em série contra a API, com duas páginas, três detalhes, nove coleções associadas, uma busca por número/ano e um ID inexistente. As verificações de ficha, autoria adicional e HEAD foram inspeções pontuais. Os resultados podem mudar conforme a Câmara atualiza a base.

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m pytest -m live -qs -p no:cacheprovider
```
